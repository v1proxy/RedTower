# 1. Choose your size

The only input to this design is the space you have. Everything else is derived.

## Measure three numbers

Measure the **outside** envelope the frame may occupy, not the inside of the
cabinet. The solver subtracts the extrusion for you.

- **Width** — 600 to 3000 mm. Beyond about 1500 mm on 4040 (900 mm on 2020) a
  loaded shelf sags enough to pond water in the tray, so the solver adds an
  interior upright. That upright costs you its own width in pot space.
- **Depth** — 300 to 760 mm. If you want the gantry, 254 mm of this is corridor
  and never grows anything. A 400 mm cabinet with a gantry has a 146 mm tray,
  which is too shallow for a 4.5 in pot, and the solver will say so.
- **Height** — 900 to 2600 mm. Pick something whose top tier you can still reach
  into, because you will be reaching into it.

## Run it

```bash
cd design
python3 solve.py m
```

Or describe your own envelope and call `solve()`. The report tells you the shelf
heights, the pot grid, and every constraint you are close to.

## What drives tier count

A tier needs `pot height + canopy + 70 mm` of light stack. For a 4.5 in pot and a
190 mm herb canopy that is 387 mm. Divide your height, minus the base bay and the
top plenum, by that number and you have your tier ceiling.

The base bay is the services space under the bottom shelf: reservoir, pump,
manifold, electronics enclosure. Below about 180 mm it stops being workable.

`tall_bottom_tier` hands the leftover height to tier A so it can take a bigger
pot, which is what makes a pepper possible under a shelf of basil.

## What drives the modules

| if your depth is | you can have |
|---|---|
| under 400 mm | core only. No corridor to put a gantry in. |
| 400 to 460 mm | gantry and arm, with the pots hard against the back of the tray |
| over 460 mm | gantry and arm, but check the reach margin: past about 460 mm the arm can no longer reach the front of its own pot row |

That last row is counterintuitive and worth sitting with. A **deeper** cabinet
makes the arm's job **harder**, because the corridor sits behind the tray and a
deeper tray pushes the pots further from the arm. Depth beyond roughly 460 mm
buys you growing area that the robot cannot service.

## Sanity checks the solver makes

It refuses outright if the tiers do not fit, if no pot fits the clear span, if a
gantry would leave less than 150 mm of tray, or if you ask for `arm` without
`gantry`.

It warns, but proceeds, if you exceed 16 probes on a tier (four ADS1115 is the
ceiling), if you need more PoE ports than the specified switch has, if the arm's
reach margin goes negative, or if a tier has less headroom than the arm is tall
when folded.
