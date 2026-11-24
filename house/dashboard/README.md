# The Red Tower dashboard

Red Tower's Home Assistant dashboard, redrawn in Vittorio's graphic style: a black ground, IBM Plex, 1 px lines,
square corners, and red only for security and emergencies. It is the house's default dashboard, **Red Tower**
(`red-tower-new`), with six tabs: Home, Digital Twin, RedSec, Consumption, Greenhouse and Remote.

Everything here is one JavaScript module (`redtower-ui.js`, 2.1.2 in RedTower 0.13.0), a generator that draws
the house in lines from the same 3D model the Digital Twin tab shows, and the two automations that turn an alarm
into a picture on the phone and the right sound on the siren.

## 1. What is here

```
house/dashboard/
  README.md                     this guide
  build.py                      joins the two parts into www/redtower-ui/redtower-ui.js (--check: is it current?)
  src/
    redtower-ui.js              part A: the look, the house in lines (custom:rt-house-card), helpers for button-card
    rt-cards.js                 part B: the other cards (below)
  www/redtower-ui/
    redtower-ui.js              the built module Home Assistant loads
  generator/
    glb.py                      a minimal GLB reader
    axo2.py                     the camera, hidden lines, floors, room boxes, openings, anchors (eight views)
    axo3.py                     the lean lines: each boundary between surfaces drawn once and straightened
    assets_lean.py              the card's drawings: axo-v0..7.svg and axo-layout.json
    drawings_plain.py           the plain views (no state) and the massing, for the notification pictures
    redsec_pics.py              the alarm notification pictures
  ha/
    redsec_automations.yaml     RedSec: the alarm notification and the siren
```

## 2. Install

1. HACS, Frontend: **button-card**, **layout-card**, **card-mod** and **auto-entities**. The Digital Twin tab
   uses the patched floor plan card from [`../floorplan`](../floorplan/README.md), the Greenhouse tab the panel from
   [`greenhouse/ha`](../../greenhouse/ha).
2. Copy `www/redtower-ui/` to `/config/www/redtower-ui/`, then add the drawings made in section 6
   (`axo-v0..7.svg`, `axo-layout.json`) beside `redtower-ui.js`.
3. Fonts: IBM Plex (SIL Open Font License) in `/config/www/redtower-ui/fonts/`, as `IBMPlexSans-Light`,
   `-Regular`, `-Medium`, `-SemiBold` and `IBMPlexMono-Regular`, `-Medium`, all `.woff2`.
4. Settings > Dashboards > Resources: `/local/redtower-ui/redtower-ui.js?v=2.1.2`, JavaScript module. Bump `?v=`
   on every change; a phone picks up a new resource on a full reload (pull down to refresh).
5. Build the views with layout-card grids (four columns, two at 1000 px or less) and button-card templates; the
   templates call `window.rt` (`kind`, `dim`, `value`, `sub`, `actionSub`, `arrow`) for the dot, the dimming and
   the figures, so every tile reads the same.

After editing `src/`, run `python build.py`; `python build.py --check` fails while `www/` is behind its sources.

## 3. The look

Only while a page of `/red-tower-new` is open, the module sets the theme variables on the page: black ground,
`#111113` cards with a `#2A2C30` line, square corners, no shadows, IBM Plex Sans and Mono. Every other dashboard
keeps its own look. On wide screens the top bar's icons read as words (Add, Search, Assist, Edit), each pressing the
icon it stands for. The greenhouse panel gets the dashboard's ground and type; its own palette stays.

- Red only for security and emergencies: alarms, RedSec and X-Sense controls while on, what is not nominal.
- Heating red, cooling blue `#4FB0FF`, always named. Green `#7FD18B` only for "everything nominal" and "no alarm".
- Pictures and maps sit on the page's black without a frame (the house on Home and RedSec, the 3D model, In and
  out); charts and tiles sit on the grey cards.

## 4. The house in lines (`custom:rt-house-card`)

The house drawn in lines from the 3D model, in eight views 45 degrees apart; dragging sideways or the arrows turn
it, and a vertical swipe still scrolls the page.

- `mode: health` (Home): a floor with a device Home Assistant can't reach is outlined red and every line on it
  turns red, with a label on the floor. Everything nominal: only the house's outline, in green. Tap a label for its
  note, tap again to close it; hold it to open a new Claude chat in the project `claude_project`, titled
  "(INT) <what>", with the note typed in.
- `mode: alarm` (RedSec): every entity in `binary_sensor.red_tower_alarm` shows as its room, a translucent red
  box, and its window or door as a solid red outline (`security_objects` maps a sensor to an opening in the
  drawing); the drawing turns to face where the alarm started. No alarm: the green outline and "No alarm".
- Size: `fit: true` makes the drawing as big as the first screen allows (`fit_reserve`, px kept for what follows);
  `fill`, `scale` and `max_height` are the older ways.
- Other options: `exclude` (devices that never count as not nominal), `names`, `rename`, `device_anchor`,
  `alarm_entity`, `panel`, `shield`, `siren_entity`, `base` (where the drawings are).

## 5. The other cards (`src/rt-cards.js`)

| Card | What it shows |
|---|---|
| `rt-thermostat-card` | the dial: red while heating, blue while cooling, both for Heat/Cool; minus and plus inside it, the four modes |
| `rt-line-card` | a chart from the history: 1 px lines, the first line's figure in red, the now dot |
| `rt-weather-card` | the forecast (today or the week) and the temperatures (last 24 h or 7 days) |
| `rt-energy-card` | electricity now, today, this month, the car; the last 24 hours; where it goes, as a treemap; the loads |
| `rt-io-card` | In and out: what comes into the house and what goes out, two treemaps either side of a plain house |
| `rt-claude-card` | Claude by room: what Claude uses of the machines that stay in a room |
| `rt-camera-card` | a camera, or why it can't show (a sign-in to renew, offline) |
| `rt-logbook-card` | what happened, newest first, by day |
| `rt-remote-card` | the TV remote |

On a phone the Digital Twin tab is all 3D model, and the model takes every touch, so there is no room left to
scroll: a small down arrow at the bottom centre of the model (phones only, 600 px wide or less, or a phone on its
side) scrolls the page so the floors' tiles sit under the header.

## 6. Drawing the house

From the same `redtower.glb` the Digital Twin card loads ([`../floorplan`](../floorplan/README.md)). Needs numpy,
scipy and scikit-image; the pictures also need Playwright with Chromium.

```
python -I generator/axo3.py redtower.glb views.json         # the eight views
python -I generator/axo2.py --massing massing.json          # the house as two plain volumes
python -I generator/assets_lean.py views.json www/redtower-ui    # the card's drawings
python -I generator/drawings_plain.py views.json massing.json drawings
python generator/redsec_pics.py drawings pictures fonts     # the notification pictures, 1800 x 900
```

How the lines are found (`axo3.py`): the camera is the card's own isometric one turned around the vertical axis;
hidden lines go with a z-buffer. Each visible pixel takes a surface: walls and cladding by the way they face
(about 20 degree buckets), a window or door (frame, its depth and the glass) as one surface, metal, the skylight
and watched objects by object. Specks under 36 px and strips thinner than 2.6 px join their neighbours, so grooves,
trims and mullions go. A line runs where two surfaces meet or the depth jumps (12 cm on walls; a profile line over
40 cm or against the sky), and each boundary is drawn once and straightened (Douglas-Peucker, 1.3 px). Each line
takes its floor from its height, so a floor can turn red on its own. The house-specific numbers (floor levels,
the tower's footprint, the watched windows) are at the top of `axo2.py`.

## 7. RedSec: the alarm notification and the siren

What counts as an alarm is `binary_sensor.red_tower_alarm` ([`../floorplan/ha`](../floorplan/ha)): smoke, CO,
gas, heat and water; doors, windows and openings while the house is armed; CO2 at 1500 ppm; a triggered panel;
anything labelled **Alarm**. `ha/redsec_automations.yaml` has the two automations that act on it:

- **RedSec - alarm notification**: on every new alarm, a picture notification to both phones and the siren by
  kind. It also runs when a new alarm joins one that is already on, so nothing goes unannounced.
- **RedSec - silence the siren when disarmed**: every siren endpoint off when the house is disarmed (Red Shield
  off or RedAlert disarmed) or when **Silence siren** is pressed on a notification.

The siren is an Aeotec Indoor Siren 6 on Z-Wave JS, one `siren` entity per endpoint:

| Alarm | Endpoint | Tone | How long |
|---|---|---|---|
| Fire or smoke (smoke and heat sensors) | 8, Emergency | 09 Smoke Alarm 1 | until disarmed or silenced |
| CO2 and every other non-security alarm | 6, Environment | 12 CO Alarm | until disarmed or silenced |
| A break-in (doors, windows, openings, a triggered panel) | 2, Tamper | 17 Alarm | 5 seconds, once |

The most urgent kind wins: a new alarm sounds only if it is more urgent than what is playing. When the house is not
armed there is nothing to disarm, which is why the notifications for the repeating sounds carry the Silence
siren button.

The notification itself is the script `script.redsec_alarm_notify` (fields `entity`, `test`, `silence`), which is
not in the repository yet. It picks the picture (the sensor's own, else its room's by area, else the whole
house), writes the title ("Alarm: Backyard window open", or smoke, CO, gas, heat, water, CO2, "triggered" for a
panel) and a line on where, when, whether the house was armed, the siren, what else is open and who is home, and
sends it to both phones in parallel: the Android phone on the `alarm_stream` channel, the iPhone as a critical
alert, both opening RedSec; with `silence`, both carry the Silence siren button (`REDSEC_SILENCE`).

## 8. Not in the repository

- The drawings and the notification pictures of Red Tower. Like `redtower.glb` they come from the house's own
  model; section 6 makes them from yours.
- The dashboard's own configuration, which lives in Home Assistant (storage mode), and the notification script.
