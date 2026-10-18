"""Module manifests. A module is a folder under modules/ holding manifest.yaml.
Dropping a folder in adds the module; removing it removes the module."""
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .topics import LAYERS

NAME = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


class ManifestError(ValueError):
    pass


@dataclass
class Manifest:
    name: str
    title: str
    layer: str
    version: str = "0.1.0"
    description: str = ""
    depends: list = field(default_factory=list)
    requests: list = field(default_factory=list)   # actuators this module may ask the governor for
    default_enabled: bool = True
    installed: bool = True                         # false: declared, code not built yet
    stub: bool = False                             # true: runs, but has no hardware behind it
    cycle_minutes: int = 0                         # agents with a fixed cycle: used by the watchdog
    config: dict = field(default_factory=dict)

    @property
    def always_on(self):
        return self.layer == "core"


def parse(data: dict, source="manifest") -> Manifest:
    if not isinstance(data, dict):
        raise ManifestError(f"{source}: not a mapping")
    known = Manifest.__dataclass_fields__.keys()
    extra = set(data) - set(known)
    if extra:
        raise ManifestError(f"{source}: unknown keys {sorted(extra)}")
    for key in ("name", "title", "layer"):
        if not data.get(key):
            raise ManifestError(f"{source}: missing '{key}'")
    m = Manifest(**data)
    if not NAME.match(m.name):
        raise ManifestError(f"{source}: bad module name '{m.name}'")
    if m.layer not in LAYERS:
        raise ManifestError(f"{source}: layer must be one of {LAYERS}")
    if m.name in m.depends:
        raise ManifestError(f"{source}: module depends on itself")
    return m


def validate_set(manifests: dict) -> list:
    """Check dependencies across all manifests and return names in start order."""
    for m in manifests.values():
        for dep in m.depends:
            if dep not in manifests:
                raise ManifestError(f"{m.name}: depends on unknown module '{dep}'")
            if m.layer == "core" and manifests[dep].layer != "core":
                raise ManifestError(f"{m.name}: core modules may only depend on core")
    order, state = [], {}

    def visit(name, trail):
        if state.get(name) == "done":
            return
        if state.get(name) == "open":
            raise ManifestError("dependency cycle: " + " -> ".join(trail + [name]))
        state[name] = "open"
        for dep in manifests[name].depends:
            visit(dep, trail + [name])
        state[name] = "done"
        order.append(name)

    for name in sorted(manifests, key=lambda n: (LAYERS.index(manifests[n].layer), n)):
        visit(name, [])
    return order


def load_dir(root) -> dict:
    out = {}
    for path in sorted(Path(root).glob("*/manifest.yaml")):
        m = parse(yaml.safe_load(path.read_text()), str(path))
        if m.name != path.parent.name:
            raise ManifestError(f"{path}: folder name must equal module name '{m.name}'")
        out[m.name] = m
    validate_set(out)
    return out
