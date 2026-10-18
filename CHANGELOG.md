# Changelog

This repository is a buildable design, so it is versioned like one. The version
in `VERSION` describes the *design*, not the code, and every generated artifact
is stamped with it.

- **MAJOR** — a change that makes an already-built unit wrong: a frame dimension,
  a pin reassignment, a part that is not a drop-in for the one it replaces.
- **MINOR** — a new module, a new size preset, a new capability. Existing builds
  stay valid.
- **PATCH** — corrections, better documentation, a part substitution that is a
  genuine drop-in, generator fixes that change no output.

Anyone who built against an older version should be able to read down to their
version and see exactly what would have to change.

## 0.1.0 — 2026-10-17

First parametric release. Up to here the repository described exactly one
greenhouse, 1397 × 457 × 1829 mm, and every dimension was a constant somebody
had typed into `brackets.py`.

### Added
- `design/params.py` — one `Envelope` describing the space you have, plus five
  presets spanning 600 mm to 3000 mm of wall.
- `design/solve.py` — derives the whole design from the envelope: bay count and
  intermediate uprights, shelf levels and headroom, the pot grid, probe and ADC
  allocation, LED wattage from a PPFD target, zone flow rates, reservoir size,
  node count and switch selection, and the arm's reach geometry.
- Module system. Core is sensing, lighting and irrigation, and every size has
  it. `gantry`, `arm` and `climate` are optional; the solver enforces that `arm`
  requires `gantry`, and reports what each one costs in depth and headroom.
- Hard limits that the solver refuses to violate rather than silently produce a
  design that cannot be built: shelf span before ponding, the four ADS1115
  addresses, PoE port budget, gantry corridor, pot fit in the tray.

### Found while building it
- **The arm's reach is the binding constraint on depth.** With a 280 mm myCobot
  on a C-Beam carriage, joint 1 ends up 359 mm behind the front face in the
  reference build, and its reach stops 79 mm short of it. The pots have to sit
  against the *back* of the tray. At the reference size the margin is +3 mm. Go
  deeper than about 460 mm and the arm can no longer reach the front of its own
  pot row, which is why `l` at 560 mm deep reports a 17 mm shortfall.
- **Four PoE ports is a design limit, not a detail.** Any build with more than
  three tiers needs a bigger switch than the TL-SG108PE in the BOM.
- **Sixteen probes per tier is the ceiling.** Four ADS1115 on four addresses.
  A 3 m wall fits 22 pots per tier, so that size needs two nodes per tier or
  zone-level moisture for the surplus.

### Unresolved, carried forward
- The LED line. The Kingbrite listing in BOM Rev E (G016) now 404s, and the
  HLG QB120 V2 alternate (G017) is both unavailable as a 4-pack and electrically
  incompatible: its minimum drive current is 1050 mA and the specified drivers
  are 700 mA. See `docs/05-electrical.md`.
- `greenhouse/` still holds the hand-written reference build. The generators in
  it are not yet driven by `design/`. That is the 0.2.0 work.
