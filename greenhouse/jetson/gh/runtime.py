"""How the supervisor starts and stops module containers."""


class NullRuntime:
    """Records what would have been done. Used in tests and dry runs."""

    def __init__(self):
        self.running = {}

    def want(self, name, run):
        self.running[name] = run


class DockerRuntime:
    """Each module is a compose service whose container is named gh-<module>.
    The supervisor only starts and stops containers that compose already created."""

    def __init__(self):
        import docker
        self._d = docker.from_env()
        self._last = {}

    def want(self, name, run):
        if self._last.get(name) == run:
            return
        import docker
        try:
            c = self._d.containers.get(f"gh-{name}")
            if run and c.status != "running":
                c.start()
            elif not run and c.status == "running":
                c.stop(timeout=10)
            self._last[name] = run
        except docker.errors.NotFound:
            self._last[name] = run          # declared but not built yet
        except docker.errors.APIError as exc:
            print(f"runtime: {name}: {exc}", flush=True)
