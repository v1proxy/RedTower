/*
 * greenhouse-panel-card  (FIRST GENERATION, superseded in design 0.8.0)
 * Use greenhouse/ha/www/greenhouse/greenhouse-panel.js instead: this card drives the
 * input_boolean.gh_kill and input_select.gh_authority helpers, which the Jetson supervisor
 * does not read. Kept for the history of the interface. Guide: docs/07-home-assistant.md
 *
 * Maag control interface for Home Assistant.
 *
 * Port of the approved interface baseline (Baseline 1, 2026-10-03, mockup v7).
 * One custom card, shown in panel mode as the Greenhouse view of the Red Tower
 * dashboard. Keeps the mockup palette, not the Home Assistant theme.
 *
 * Sections, top to bottom:
 *   1 header + agent kill switch     5 plants, 27 positions in three tiers
 *   2 authority ceiling              6 plant card (expands to overlay)
 *   3 modules by layer               7 agent console
 *   4 environment / power
 *
 * Hardware that is not online yet renders as a dimmed "not online" tile rather
 * than disappearing, so the page is the build checklist as well as the control.
 *
 * Install: /config/www/greenhouse-panel.js, registered as a Lovelace module
 * resource at /local/greenhouse-panel.js
 */

const C = {
  ground: '#14181a',
  tile: '#1d2326',
  line: '#2c3539',
  edge: '#4a565b',
  dim: '#3a454a',
  text: '#e6ebe8',
  muted: '#9aa6a0',
  soft: '#c9d1cd',
  green: '#7fd18b',
  amber: '#f0b454',
  red: '#ff8f85',
  blue: '#9cc3ff',
  inkOnGreen: '#0f1a12',
};

const MODES = [
  ['Off', 'Nothing actuates. Sensors keep reporting.'],
  ['Manual', 'You drive everything from this page. No loop acts on its own.'],
  ['Auto', 'Deterministic services run climate and irrigation. No agent acts.'],
  ['Agent proposes', 'Agents may propose; anything touching the arm waits for your approval.'],
  ['Agent autonomous', 'Agents act inside the safety governor limits without asking.'],
];

// Layer 0 is always on. Everything else can be switched if its toggle exists.
const LAYERS = [
  {
    label: 'Layer 0, core',
    locked: true,
    mods: [
      { id: 'supervisor', name: 'Supervisor', sub: 'Module lifecycle', probe: 'sensor.greenhouse_supervisor_status' },
      { id: 'governor', name: 'Safety governor', sub: 'Every actuator command', probe: 'binary_sensor.greenhouse_robot_clear_to_run' },
      { id: 'store', name: 'State store', sub: 'SQLite', probe: 'sensor.greenhouse_store_status' },
      { id: 'bridge', name: 'HA bridge', sub: 'MQTT discovery', probe: 'sensor.greenhouse_bridge_status' },
    ],
  },
  {
    label: 'Layer 1, drivers',
    mods: [
      { id: 'arm', name: 'Arm', sub: 'myCobot 280 Pi', probe: 'sensor.greenhouse_arm_state' },
      { id: 'gantry', name: 'Gantry', sub: 'FluidNC X and Z', probe: 'sensor.greenhouse_gantry_state' },
      { id: 'd405', name: 'D405', sub: 'Close-up depth camera', probe: 'camera.greenhouse_d405' },
      { id: 'overview', name: 'Overview camera', sub: '160 deg, top corner', probe: 'camera.greenhouse_overview' },
      { id: 'esphome', name: 'ESPHome link', sub: 'Three tiers and utility', probe: 'sensor.greenhouse_tier_a_air_temperature' },
    ],
  },
  {
    label: 'Layer 2, services',
    mods: [
      { id: 'climate', name: 'Climate', sub: 'VPD, CO2, exhaust', probe: 'sensor.greenhouse_tier_a_vpd' },
      { id: 'irrigation', name: 'Irrigation', sub: 'Three zones, drip', probe: 'binary_sensor.greenhouse_utility_watering_active' },
      { id: 'nutrients', name: 'Nutrients', sub: 'Stub, no hardware', stub: true },
      { id: 'perception', name: 'Perception', sub: 'Leaf metrics, candidates', probe: 'sensor.greenhouse_perception_status' },
      { id: 'motion', name: 'Motion', sub: 'Planned paths to the arm', probe: 'sensor.greenhouse_motion_status' },
    ],
  },
  {
    label: 'Layer 3, agents',
    mods: [
      { id: 'envagent', name: 'Environment agent', sub: 'Hourly climate loop', probe: 'sensor.greenhouse_claude_cost' },
      { id: 'tender', name: 'Plant tender', sub: 'Per-plant care', probe: 'sensor.greenhouse_tender_status' },
      { id: 'llm', name: 'LLM gateway', sub: 'Claude API, budget cap', probe: 'sensor.greenhouse_claude_cache_hit' },
    ],
  },
];

const SENSORS = [
  { label: 'Air temperature', id: 'sensor.greenhouse_tier_b_air_temperature', unit: '°C', dec: 1, target: 'Band 15 to 33' },
  { label: 'Humidity', id: 'sensor.greenhouse_tier_b_air_humidity', unit: '%', dec: 0, target: 'Band 30 to 90' },
  { label: 'VPD', id: 'sensor.greenhouse_tier_b_vpd', unit: 'kPa', dec: 2, target: 'Band 0.4 to 2.0' },
  { label: 'Soil moisture, median', id: null, unit: '%', dec: 0, target: 'Band 25 to 75', median: true },
  { label: 'CO2', id: 'sensor.greenhouse_utility_co2', unit: 'ppm', dec: 0, target: 'Floor 350' },
  { label: 'Leaf to air delta', id: 'sensor.greenhouse_tier_b_leaf_to_air_delta', unit: '°C', dec: 1, target: 'Ceiling 2.5' },
];

const DEVICES = [
  { label: 'Grow lights', id: 'light.greenhouse_tier_a_grow_light' },
  { label: 'Circulation', id: 'fan.greenhouse_tier_a_circulation_fan' },
  { label: 'Exhaust', id: 'fan.greenhouse_utility_exhaust_fans' },
  { label: 'Humidifier', id: 'switch.greenhouse_utility_humidifier' },
];

const LOADS = [
  ['Grow lights', 158], ['Jetson', 12], ['ESP32 nodes', 8], ['Fans', 6],
  ['PoE switch', 6], ['Arm idle', 5], ['Cameras', 3],
];

const TIERS = [
  { key: 'a', label: 'Tier A, top shelf, 7 peppers', n: 7 },
  { key: 'b', label: 'Tier B, middle shelf, 10 herbs', n: 10 },
  { key: 'c', label: 'Tier C, lower shelf, 10 herbs', n: 10 },
];

const MILESTONES = ['Seedling', 'Established', 'Bulking', 'Mature', 'Ready'];

const num = (v, d) => (v === null || v === undefined || v === '' || isNaN(Number(v)) ? null : Number(v).toFixed(d));

class GreenhousePanelCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._sel = 'B01';
    this._powerOpen = false;
    this._expanded = false;
    this._replacing = false;
    this._draft = '';
    this._draftError = false;
    this._hist = null;
    this._histAt = 0;
    this._sig = '';
    this._built = false;
  }

  setConfig(config) {
    this._config = Object.assign({ title: 'Maag', power_entity: 'sensor.greenhouse_utility_cabinet_power' }, config || {});
  }

  getCardSize() { return 40; }

  set hass(hass) {
    this._hass = hass;
    const sig = this._signature();
    if (sig !== this._sig) { this._sig = sig; this._render(); }
    this._maybeHistory();
  }

  // ---------- helpers ----------

  _st(id) { return id && this._hass && this._hass.states[id] ? this._hass.states[id] : null; }
  _val(id) { const s = this._st(id); return s && s.state !== 'unavailable' && s.state !== 'unknown' ? s.state : null; }
  _on(id) { return this._val(id) === 'on'; }
  _live(id) { return this._val(id) !== null; }

  _plantIds() {
    const out = [];
    TIERS.forEach(t => { for (let i = 1; i <= t.n; i++) out.push(t.key.toUpperCase() + String(i).padStart(2, '0')); });
    return out;
  }

  _moisture(label) {
    return this._val('sensor.greenhouse_tier_' + label[0].toLowerCase() + '_' + label.toLowerCase() + '_moisture');
  }

  _medianSoil() {
    const vals = this._plantIds().map(l => this._moisture(l)).filter(v => v !== null).map(Number).sort((a, b) => a - b);
    if (!vals.length) return null;
    const m = Math.floor(vals.length / 2);
    return vals.length % 2 ? vals[m] : (vals[m - 1] + vals[m]) / 2;
  }

  // Tender publishes the verdict when it is online. Until then, fall back to
  // the moisture band so the grid still means something, and say so.
  _plantState(label) {
    const explicit = this._val('sensor.greenhouse_plant_' + label.toLowerCase() + '_state');
    if (explicit) return explicit;
    const m = this._moisture(label);
    if (m === null) return 'nodata';
    const thr = Number(this._val('input_number.gh_threshold_' + label[0].toLowerCase()) || 35);
    return Number(m) < thr ? 'attention' : 'normal';
  }

  _plantColor(s) {
    return s === 'ready' ? C.green : s === 'attention' ? C.amber : s === 'dead' ? C.red : null;
  }

  _signature() {
    if (!this._hass) return '';
    const keys = ['input_select.gh_authority', 'input_boolean.gh_kill', 'input_boolean.gh_claude_autonomy',
      'input_boolean.gh_auto_water', 'input_text.gh_proposal_plant', 'input_text.gh_proposal_action',
      this._config.power_entity];
    LAYERS.forEach(l => l.mods.forEach(m => keys.push(m.probe, 'input_boolean.gh_mod_' + m.id)));
    SENSORS.forEach(s => keys.push(s.id));
    DEVICES.forEach(d => keys.push(d.id));
    this._plantIds().forEach(l => {
      keys.push('sensor.greenhouse_tier_' + l[0].toLowerCase() + '_' + l.toLowerCase() + '_moisture');
      keys.push('sensor.greenhouse_plant_' + l.toLowerCase() + '_state');
    });
    const parts = keys.map(k => (k && this._hass.states[k] ? this._hass.states[k].state : '-'));
    parts.push(this._sel, this._powerOpen, this._expanded, this._replacing, this._draftError, this._draft, this._hist ? this._hist.length : 0);
    return parts.join('|');
  }

  async _maybeHistory() {
    const id = this._config.power_entity;
    if (!this._hass || !this._hass.states[id]) return;
    if (Date.now() - this._histAt < 300000) return;
    this._histAt = Date.now();
    try {
      const end = new Date();
      const start = new Date(end.getTime() - 24 * 3600 * 1000);
      const r = await this._hass.callWS({
        type: 'history/history_during_period',
        start_time: start.toISOString(), end_time: end.toISOString(),
        entity_ids: [id], minimal_response: true, no_attributes: true,
      });
      const rows = (r && r[id]) || [];
      this._hist = rows.map(p => ({ t: p.lu * 1000, v: Number(p.s) })).filter(p => !isNaN(p.v));
      this._sig = ''; this._render();
    } catch (e) { this._hist = []; }
  }

  _points() {
    if (!this._hist || this._hist.length < 2) return null;
    const t0 = this._hist[0].t, t1 = this._hist[this._hist.length - 1].t;
    const span = Math.max(1, t1 - t0);
    const max = Math.max(50, ...this._hist.map(p => p.v));
    return {
      max,
      d: this._hist.map(p => `${((p.t - t0) / span * 240).toFixed(1)},${(150 - p.v / max * 150).toFixed(1)}`).join(' '),
    };
  }

  // ---------- actions ----------

  _call(domain, service, data) { this._hass.callService(domain, service, data); }

  _act(what, arg) {
    switch (what) {
      case 'kill':
        if (this._live('input_boolean.gh_kill')) this._call('input_boolean', 'toggle', { entity_id: 'input_boolean.gh_kill' });
        break;
      case 'mode':
        if (this._live('input_select.gh_authority')) this._call('input_select', 'select_option', { entity_id: 'input_select.gh_authority', option: arg });
        break;
      case 'mod': {
        const e = 'input_boolean.gh_mod_' + arg;
        if (this._live(e)) this._call('input_boolean', 'toggle', { entity_id: e });
        break;
      }
      case 'dev': {
        const d = arg.split('.')[0];
        this._call(d === 'light' ? 'light' : d === 'fan' ? 'fan' : 'switch', 'toggle', { entity_id: arg });
        break;
      }
      case 'power': this._powerOpen = !this._powerOpen; break;
      case 'plant': this._sel = arg; this._replacing = false; break;
      case 'expand': this._expanded = !this._expanded; break;
      case 'replace': this._replacing = true; this._draft = ''; this._draftError = false; break;
      case 'cancel': this._replacing = false; this._draftError = false; break;
      case 'confirm':
        if (!this._draft.trim()) { this._draftError = true; break; }
        this._replacing = false; this._draftError = false;
        if (this._live('input_text.gh_replace_plant')) {
          this._call('input_text', 'set_value', { entity_id: 'input_text.gh_replace_plant', value: this._sel + ' ' + this._draft.trim() });
        }
        break;
      case 'approve':
        if (this._hass.services.script && this._hass.services.script.gh_tender_approve) this._call('script', 'gh_tender_approve', {});
        break;
      case 'reject':
        if (this._live('input_text.gh_proposal_action')) {
          this._call('input_text', 'set_value', { entity_id: 'input_text.gh_proposal_action', value: '' });
          this._call('input_text', 'set_value', { entity_id: 'input_text.gh_proposal_plant', value: '' });
        }
        break;
      case 'jog':
        if (this._hass.services.script && this._hass.services.script.gh_robot_task) this._call('script', 'gh_robot_task', { task: arg });
        break;
      case 'water':
        this._call('script', 'gh_robot_task', { task: 'water_' + arg });
        break;
    }
    this._sig = '';
    this._render();
  }

  // ---------- render ----------

  _btn(label, opts) {
    const o = opts || {};
    const bg = o.active ? (o.danger ? C.red : C.green) : C.tile;
    const fg = o.active ? C.inkOnGreen : o.disabled ? C.muted : C.text;
    const bd = o.active ? (o.danger ? C.red : C.green) : o.disabled ? C.dim : C.edge;
    return `<button class="b" ${o.act ? `data-act="${o.act}"` : ''} ${o.arg ? `data-arg="${o.arg}"` : ''}
      ${o.disabled ? 'disabled' : ''} ${o.aria ? `aria-label="${o.aria}"` : ''}
      aria-pressed="${!!o.active}"
      style="background:${bg};color:${fg};border-color:${bd};${o.grow ? 'flex:1;' : ''}${o.pad ? `padding:0 ${o.pad}px;` : ''}">${label}</button>`;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const h = this._hass;

    // -- header
    const killOn = this._on('input_boolean.gh_kill');
    const killLive = this._live('input_boolean.gh_kill');
    const mode = this._val('input_select.gh_authority');
    const modeLive = mode !== null;

    // -- module tiles
    const layers = LAYERS.map(L => {
      const mods = L.mods.map(m => {
        const stub = !!m.stub;
        const live = !stub && this._live(m.probe);
        const tog = 'input_boolean.gh_mod_' + m.id;
        const hasTog = this._live(tog);
        const on = hasTog ? this._on(tog) : live;
        const color = stub ? C.red : !live ? C.muted : on ? C.green : C.amber;
        const status = stub ? 'Disabled, stub' : !live ? 'Not online' : on ? 'Running' : 'Stopped';
        const modeTxt = L.locked ? 'always on' : stub ? 'no hardware' : live ? (mode || 'auto') : 'pending build';
        return `<div class="tile mod" style="border-color:${stub ? C.red : live ? C.line : C.dim};${live ? '' : 'opacity:.62;'}">
          <div class="row top">
            <div class="col gap2 min0">
              <div class="mname">${m.name}</div>
              <div class="sub">${m.sub}</div>
            </div>
          </div>
          <div class="row wrap center gap8">
            <span class="dot" style="background:${color}"></span>
            <span class="stat" style="color:${color}">${status}</span>
            <span class="sub auto">${modeTxt}</span>
          </div>
          ${L.locked
            ? `<div class="locked">Always on</div>`
            : hasTog
              ? this._btn(on ? 'Enabled' : 'Disabled', { act: 'mod', arg: m.id, active: on, aria: m.name })
              : `<div class="locked" style="border-style:dashed">${stub ? 'No hardware' : 'No toggle yet'}</div>`}
        </div>`;
      }).join('');
      return `<div class="col gap8"><div class="lname">${L.label}</div><div class="row wrap gap12">${mods}</div></div>`;
    }).join('');

    // -- environment
    const sensors = SENSORS.map(s => {
      let v = s.median ? this._medianSoil() : this._val(s.id);
      const shown = v === null ? '--' : num(v, s.dec);
      return `<div class="tile" style="${v === null ? 'opacity:.62;' : ''}">
        <div class="sub">${s.label}</div>
        <div class="row baseline gap6"><div class="big">${shown}</div><div class="sub">${s.unit}</div></div>
        <div class="sub">${v === null ? 'Not online' : s.target}</div>
      </div>`;
    }).join('');

    const devices = DEVICES.map(d => {
      const live = this._live(d.id);
      return this._btn(d.label, { act: 'dev', arg: d.id, active: live && this._on(d.id), disabled: !live, pad: 14 });
    }).join('');

    // -- power
    const pw = this._val(this._config.power_entity);
    const pts = this._points();
    const peak = this._hist && this._hist.length ? Math.max(...this._hist.map(p => p.v)) : null;
    const kwh = this._val('sensor.greenhouse_utility_cabinet_energy');
    const powerTiles = [
      ['Draw now', pw === null ? '--' : num(pw, 0), 'W', pw === null ? 'Not online' : 'Metered at the inlet'],
      ['Peak, 24 h', peak === null ? '--' : num(peak, 0), 'W', peak === null ? 'No history yet' : 'From the meter'],
      ['Energy today', kwh === null ? '--' : num(kwh, 2), 'kWh', 'Shelly PM Mini'],
      ['Design estimate', '3.63', 'kWh/day', '$0.56 a day at 15.55 c'],
    ].map(t => `<div class="tile"><div class="sub">${t[0]}</div>
      <div class="row baseline gap6"><div class="big">${t[1]}</div><div class="sub">${t[2]}</div></div>
      <div class="sub">${t[3]}</div></div>`).join('');

    const chart = pts
      ? `<svg viewBox="0 0 240 150" preserveAspectRatio="none" aria-hidden="true" class="spark">
           <line x1="0" y1="75" x2="240" y2="75" class="grid"></line>
           <polyline points="${pts.d}" class="pl"></polyline></svg>`
      : `<div class="empty" style="height:150px">No meter history yet</div>`;

    const loadTotal = LOADS.reduce((a, b) => a + b[1], 0);
    const loads = LOADS.map(l => `<div class="col gap4">
      <div class="row between gap8 s14"><div>${l[0]}</div><div class="mono">${l[1]} W</div></div>
      <div class="bar"><div class="fill" style="width:${(l[1] / loadTotal * 100).toFixed(0)}%"></div></div></div>`).join('');

    // -- plants
    const tiers = TIERS.map(t => {
      const cells = [];
      for (let i = 1; i <= t.n; i++) {
        const label = t.key.toUpperCase() + String(i).padStart(2, '0');
        const st = this._plantState(label);
        const col = this._plantColor(st);
        const sel = this._sel === label;
        cells.push(`<button class="cell${sel ? ' sel' : ''}" data-act="plant" data-arg="${label}"
          aria-pressed="${sel}" aria-label="Position ${label}, ${st === 'nodata' ? 'no data' : st}"
          style="border-color:${sel ? C.blue : col || C.edge};background:${col ? col + '22' : 'transparent'};color:${col || C.soft}">${i}</button>`);
      }
      return `<div class="col gap6"><div class="lname">${t.label}</div><div class="row wrap gap6">${cells.join('')}</div></div>`;
    }).join('');

    const selState = this._plantState(this._sel);
    const selMoist = this._moisture(this._sel);
    const readyText = selState === 'ready' ? 'Ready to pick' : selState === 'attention' ? 'Needs a decision'
      : selState === 'dead' ? 'To be replaced' : selState === 'nodata' ? 'No data yet' : 'Growing normally';
    const readyColor = this._plantColor(selState) || C.muted;
    const stageIdx = selState === 'ready' ? 4 : selState === 'nodata' ? -1 : 1;
    const milestones = MILESTONES.map((m, i) => `<div class="col gap6" style="flex:1 1 0;min-width:0">
      <div class="ms" style="background:${i <= stageIdx ? C.green : C.line}"></div>
      <div class="sub" style="font-size:12px;color:${i <= stageIdx ? C.soft : C.muted}">${m}</div></div>`).join('');

    const levels = [
      ['Moisture', selMoist === null ? '--' : num(selMoist, 0) + ' %'],
      ['Threshold', (this._val('input_number.gh_threshold_' + this._sel[0].toLowerCase()) || '--') + ' %'],
      ['Tier', this._sel[0]],
    ].map(l => `<div class="lv"><div class="sub" style="font-size:12px">${l[0]}</div><div class="mono" style="font-size:16px">${l[1]}</div></div>`).join('');

    const cardBody = `
      <div class="row between center gap8">
        <div class="sub s14">Plant card</div>
        ${this._btn(this._expanded ? 'Close' : 'Expand', { act: 'expand', pad: 14 })}
      </div>
      <div class="row wrap gap14">
        <div class="col gap6" style="flex:1 1 150px;min-width:0">
          <div class="photo"><div class="s14 b500">Daily photo</div><div class="sub">Arm camera, once a day</div></div>
          <div class="mono sub" style="font-size:12px">No capture yet</div>
        </div>
        <div class="col gap10" style="flex:2 1 220px;min-width:0">
          <div class="col gap2">
            <div class="mono sub" style="font-size:13px">${this._sel}</div>
            <div class="pname">Position ${this._sel}</div>
            <div class="sub ital">Species set when you plant it</div>
          </div>
          <div class="row wrap gap8">${levels}</div>
          <div class="sub">Your entry is the record. The camera only suggests a type.</div>
        </div>
      </div>
      <div class="col gap8">
        <div class="row wrap between gap8 baseline">
          <div class="s14 b500">Growth</div>
          <div class="s14 b600" style="color:${readyColor}">${readyText}</div>
        </div>
        <div class="row gap4">${milestones}</div>
        <div class="sub">Stage is assessed by the plant tender from each daily photo and the depth measurements.</div>
      </div>
      ${this._expanded ? `<div class="col gap8"><div class="s14 b500">Photo history</div>
        <div class="row wrap gap8">${[...Array(7)].map((_, i) => `<div class="hist">D-${7 - i}</div>`).join('')}</div></div>` : ''}
      ${this._replacing ? `
        <div class="replace col gap10">
          <label for="pt" class="s14 b500">New plant type for this position</label>
          <input id="pt" type="text" value="${this._draft.replace(/"/g, '&quot;')}" placeholder="For example: thyme">
          ${this._draftError ? `<div class="s13" style="color:${C.red}">Enter a plant type first.</div>` : ''}
          <div class="sub">Confirming resets the growth bar and loads the care profile for the new type.</div>
          <div class="row gap8">
            ${this._btn('Confirm', { act: 'confirm', active: true, grow: true })}
            ${this._btn('Cancel', { act: 'cancel', grow: true })}
          </div>
        </div>`
        : this._btn('Replace plant', { act: 'replace' })}`;

    // -- agent console
    const cost = this._val('sensor.greenhouse_claude_cost');
    const hit = this._val('sensor.greenhouse_claude_cache_hit');
    const pPlant = this._val('input_text.gh_proposal_plant');
    const pAction = this._val('input_text.gh_proposal_action');
    const hasProposal = !!(pPlant && pAction);
    const autonomy = this._on('input_boolean.gh_claude_autonomy');

    const queue = hasProposal
      ? `<div class="tile col gap10">
           <div class="col gap2">
             <div class="mono sub" style="font-size:13px">${pPlant}</div>
             <div class="s15">${pAction}</div>
             <div class="sub">Cutting stays locked until you approve.</div>
           </div>
           <div class="row gap8">
             ${this._btn('Approve', { act: 'approve', active: true, grow: true })}
             ${this._btn('Reject', { act: 'reject', grow: true })}
           </div>
         </div>`
      : `<div class="empty">Nothing waiting for approval.</div>`;

    const jog = ['x_minus', 'x_plus', 'z_minus', 'z_plus', 'home']
      .map((t, i) => this._btn(['X -', 'X +', 'Z -', 'Z +', 'Home'][i], { act: 'jog', arg: t, disabled: !(h.services.script && h.services.script.gh_robot_task) }))
      .join('');

    // -- assemble
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;background:${C.ground};color:${C.text};
          font-family:system-ui,-apple-system,'Segoe UI',sans-serif;}
        .page{box-sizing:border-box;max-width:1320px;margin:0 auto;padding:24px;
          display:flex;flex-direction:column;gap:28px}
        h1{margin:0;font-size:30px;font-weight:600}
        h2{margin:0;font-size:20px;font-weight:600}
        .crumb{font-family:ui-monospace,monospace;font-size:13px;color:${C.muted}}
        .row{display:flex}.col{display:flex;flex-direction:column}
        .row.wrap,.legend{flex-wrap:wrap}
        .center{align-items:center}.baseline{align-items:baseline}
        .between{justify-content:space-between}.min0{min-width:0}
        .gap2{gap:2px}.gap4{gap:4px}.gap6{gap:6px}.gap8{gap:8px}.gap10{gap:10px}
        .gap12{gap:12px}.gap14{gap:14px}.gap16{gap:16px}
        .auto{margin-left:auto}
        .sub{font-size:13px;color:${C.muted}}
        .s13{font-size:13px}.s14{font-size:14px}.s15{font-size:15px}
        .b500{font-weight:500}.b600{font-weight:600}
        .ital{font-style:italic}
        .mono{font-family:ui-monospace,'SF Mono',monospace}
        .tile{box-sizing:border-box;background:${C.tile};border:1px solid ${C.line};
          border-radius:8px;padding:14px;display:flex;flex-direction:column;gap:10px;
          flex:1 1 150px;min-width:0}
        .mod{flex:1 1 170px;justify-content:space-between;padding:12px}
        .mname{font-size:16px;font-weight:600}
        .lname{font-family:ui-monospace,monospace;font-size:13px;color:${C.muted}}
        .stat{font-size:14px;font-weight:500}
        .dot{width:10px;height:10px;border-radius:50%;flex:none}
        .big{font-family:ui-monospace,monospace;font-size:28px;font-weight:500}
        button.b{min-height:44px;padding:0 16px;border-radius:6px;border:1px solid ${C.edge};
          background:${C.tile};color:${C.text};font-size:15px;font-weight:500;
          font-family:inherit;cursor:pointer}
        button.b[disabled]{cursor:not-allowed}
        button.b:focus-visible,.cell:focus-visible{outline:2px solid ${C.blue};outline-offset:2px}
        .locked{min-height:44px;display:flex;align-items:center;justify-content:center;
          border-radius:6px;border:1px dashed ${C.dim};font-size:14px;color:${C.muted}}
        .empty{border:1px dashed ${C.dim};border-radius:8px;padding:18px;font-size:14px;
          color:${C.muted};display:flex;align-items:center;justify-content:center;text-align:center}
        .spark{display:block;width:100%;height:150px;overflow:visible}
        .grid{stroke:${C.line};stroke-width:1;vector-effect:non-scaling-stroke}
        .pl{fill:none;stroke:${C.green};stroke-width:2;stroke-linejoin:round;vector-effect:non-scaling-stroke}
        .bar{height:8px;border-radius:3px;background:${C.line}}
        .fill{height:8px;border-radius:3px;background:${C.green}}
        .cell{flex:1 1 44px;min-width:44px;min-height:44px;padding:0;border-radius:6px;
          border:2px solid ${C.edge};background:transparent;color:${C.soft};
          font-family:ui-monospace,monospace;font-size:13px;cursor:pointer}
        .cell.sel{border-width:2px}
        .legend{display:flex;flex-wrap:wrap;gap:14px;font-size:13px;color:${C.soft}}
        .sw{width:12px;height:12px;border-radius:3px}
        .photo{aspect-ratio:1/1;border:1px dashed ${C.edge};border-radius:6px;display:flex;
          flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:10px;text-align:center}
        .hist{flex:1 1 80px;min-width:0;aspect-ratio:1/1;border:1px dashed ${C.edge};border-radius:6px;
          display:flex;align-items:center;justify-content:center;font-family:ui-monospace,monospace;
          font-size:12px;color:${C.muted}}
        .lv{flex:1 1 90px;min-width:0;border:1px solid ${C.line};border-radius:6px;padding:8px;
          display:flex;flex-direction:column;gap:2px}
        .ms{height:10px;border-radius:3px}
        .pname{font-size:18px;font-weight:600}
        .replace{border:1px solid ${C.edge};border-radius:6px;padding:12px}
        .replace input{min-height:44px;box-sizing:border-box;width:100%;padding:0 12px;border-radius:6px;
          border:1px solid ${C.edge};background:${C.ground};color:${C.text};font-family:inherit;font-size:16px}
        .pill{font-family:ui-monospace,monospace;font-size:13px;color:${C.ground};
          background:${C.amber};padding:6px 10px;border-radius:4px}
        .plantcard{background:${C.tile};border:1px solid ${C.line};border-radius:8px;padding:14px;
          display:flex;flex-direction:column;gap:14px}
        .plantcard.exp{position:fixed;inset:24px;z-index:11;overflow:auto;max-width:900px;margin:auto;height:fit-content;max-height:calc(100% - 48px)}
        .scrim{position:fixed;inset:0;z-index:10;border:0;padding:0;background:rgba(8,10,11,.78)}
        .two{display:flex;flex-wrap:wrap;gap:28px}
        .two>section{flex:1 1 420px;min-width:0;display:flex;flex-direction:column;gap:12px}
        @media (max-width:760px){.page{padding:16px;gap:22px}h1{font-size:24px}.big{font-size:24px}}
        @media (max-width:430px){.page{padding:12px}.tile{flex:1 1 100%}.mod{flex:1 1 100%}}
      </style>

      <div class="page">

        <header class="row wrap gap16 center between">
          <div class="col gap4">
            <div class="crumb">Red Tower / Greenhouse</div>
            <h1>${this._config.title}</h1>
          </div>
          <div class="row wrap gap12 center">
            ${killLive ? '' : `<div class="pill">Kill switch entity missing</div>`}
            ${this._btn(killOn ? 'Agents stopped' : 'Stop all agents',
              { act: 'kill', active: killOn, danger: true, disabled: !killLive, pad: 18 })}
          </div>
        </header>

        <section class="col gap10">
          <h2 style="font-size:14px;font-weight:500;color:${C.muted}">Authority ceiling</h2>
          <div class="row wrap gap8">
            ${MODES.map(m => this._btn(m[0], { act: 'mode', arg: m[0], active: mode === m[0], disabled: !modeLive })).join('')}
          </div>
          <div class="sub">${modeLive ? (MODES.find(m => m[0] === mode) || MODES[2])[1] : 'Add input_select.gh_authority to the greenhouse package to arm this.'}</div>
        </section>

        <section class="col gap16">
          <h2>Modules</h2>
          ${layers}
        </section>

        <section class="col gap12">
          <h2>Environment</h2>
          <div class="row wrap gap12">${sensors}</div>
          <div class="row wrap gap8">${devices}</div>
          <div class="sub">Device buttons are manual overrides. Every command still passes through the safety governor.</div>
        </section>

        <section class="col gap12">
          <div class="row wrap gap8 baseline between">
            <h2>Power</h2>
            <div class="sub">Whole unit, metered at the inlet. Per-load values are computed.</div>
          </div>
          <div class="row wrap gap12">${powerTiles}</div>
          <div class="row wrap gap12">
            <div class="tile" style="flex:3 1 320px">
              <div class="row wrap gap8 center between">
                <div class="s14 b500">Whole system draw over 24 hours, watts</div>
                ${this._btn(this._powerOpen ? 'Hide breakdown' : 'By subsystem', { act: 'power', pad: 14 })}
              </div>
              <div class="row gap8">
                <div class="col between mono" style="height:150px;font-size:12px;color:${C.muted};text-align:right">
                  <div>${pts ? Math.round(pts.max) : 320}</div><div>${pts ? Math.round(pts.max / 2) : 160}</div><div>0</div>
                </div>
                <div class="col gap6" style="flex:1;min-width:0">
                  <div style="height:150px;border-bottom:1px solid ${C.edge}">${chart}</div>
                  <div class="row between mono" style="font-size:12px;color:${C.muted}">
                    <div>-24 h</div><div>-18 h</div><div>-12 h</div><div>-6 h</div><div>now</div>
                  </div>
                </div>
              </div>
              <div class="sub">Lights run 16 h at about 158 W. Night baseline about 45 W.</div>
            </div>
            ${this._powerOpen ? `<div class="tile col gap10" style="flex:2 1 260px">
              <div class="s14 b500">Daytime draw by subsystem</div>${loads}
              <div class="sub">Computed from device state and rated power. Only the total is metered.</div></div>` : ''}
          </div>
        </section>

        <div class="two">
          <section>
            <h2>Plants</h2>
            <div class="legend">
              <div class="row center gap6"><div class="sw" style="background:${C.green}"></div><div>Ready to pick</div></div>
              <div class="row center gap6"><div class="sw" style="background:${C.amber}"></div><div>Needs attention or a decision</div></div>
              <div class="row center gap6"><div class="sw" style="background:${C.red}"></div><div>Dead, to be replaced</div></div>
              <div class="row center gap6"><div class="sw" style="border:1px solid ${C.edge};box-sizing:border-box"></div><div>Growing normally</div></div>
            </div>
            ${tiers}
            ${this._expanded ? `<button class="scrim" data-act="expand" aria-label="Close plant card"></button>` : ''}
            <div class="plantcard${this._expanded ? ' exp' : ''}">${cardBody}</div>
          </section>

          <section>
            <h2>Agent console</h2>
            <div class="tile">
              <div class="sub">Latest output, environment agent</div>
              <div class="s15" style="line-height:1.55">${
                cost === null
                  ? 'The gardener is not reporting yet. Nothing has run on the Jetson.'
                  : `Running. ${autonomy ? 'Autonomy is on, so it acts inside the configured limits.' : 'Autonomy is off, so it reports but does not actuate.'}`
              }</div>
              <div class="row wrap gap12 mono sub" style="font-size:12px">
                <div>Spend ${cost === null ? '--' : '$' + num(cost, 2)}</div>
                <div>Cache hit ${hit === null ? '--' : num(hit, 0) + ' %'}</div>
                <div>Wakes hourly, or early on escalation</div>
              </div>
            </div>
            <div class="s14 b500 sub">Approval queue</div>
            ${queue}
            <div class="empty" style="min-height:200px;flex-direction:column;gap:6px">
              <div class="s15 b500">Live view</div>
              <div class="sub">D405 stream with candidate overlay, served by the Jetson</div>
            </div>
            <div class="row wrap gap8">${jog}</div>
          </section>
        </div>

      </div>`;

    if (!this._bound) {
      this.shadowRoot.addEventListener('click', e => {
        const t = e.target.closest('[data-act]');
        if (!t || t.disabled) return;
        this._act(t.dataset.act, t.dataset.arg);
      });
      this.shadowRoot.addEventListener('input', e => {
        if (e.target.id === 'pt') this._draft = e.target.value;
      });
      this._bound = true;
    }
  }
}

customElements.define('greenhouse-panel-card', GreenhousePanelCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'greenhouse-panel-card',
  name: 'Greenhouse panel',
  description: 'Maag control interface, one card in panel mode',
  preview: false,
});

console.info('%c GREENHOUSE-PANEL-CARD %c baseline 1 ', 'background:#7fd18b;color:#0f1a12', 'background:#1d2326;color:#e6ebe8');
