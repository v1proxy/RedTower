/* Greenhouse view for Home Assistant. One custom card, no build step.
 * Reads the entities published by the Jetson's HA bridge and by the ESPHome nodes.
 * Every command the user gives goes to the safety governor, never straight to a device.
 * Card option  demo: true  runs the whole view on simulated data.
 * No network calls of its own: IBM Plex is used if the device has it, else the system font. */
const CARD_VERSION = '0.8.0';
const C = { bg: '#14181a', panel: '#1d2326', line: '#2c3539', line2: '#4a565b', text: '#e6ebe8', mute: '#9aa6a0',
  soft: '#c9d1cd', green: '#7fd18b', greenBg: '#24362a', greenFg: '#a6e3b0', greenLine: '#3f7a4c',
  red: '#ff8f85', redBg: '#3d1c19', redFg: '#ffb8b0', redLine: '#b0483d', yellow: '#f2d86a', yellowBg: '#38320f',
  yellowLine: '#8f7a1e', amber: '#f0b454', blue: '#9cc3ff' };
const LAYERS = [['agent', 'Layer 3, agents'], ['service', 'Layer 2, services'], ['driver', 'Layer 1, drivers'], ['core', 'Layer 0, core']];
const MODES = [['off', 'Off', 'Everything above the core is stopped. ESPHome failsafes still hold.'],
  ['manual', 'Manual', 'You drive every device from this page. No automatic control.'],
  ['auto', 'Auto', 'Deterministic services run the greenhouse. Agents are paused.'],
  ['proposes', 'Agent proposes', 'Services run. Agents suggest actions and wait for your approval.'],
  ['autonomous', 'Agent autonomous', 'Agents act inside the governor limits. Cutting still needs approval.']];
const STATE_LOOK = { running: ['Running', C.green], stub: ['Stub, no hardware', C.blue], degraded: ['Degraded', C.amber],
  disabled: ['Disabled', C.red], halted: ['Halted', C.red], fault: ['Fault', C.red], offline: ['Offline', C.red],
  paused: ['Paused', C.mute], stopped: ['Stopped', C.mute], missing: ['Not built yet', C.mute] };
const MODE_LABEL = { auto: 'Auto', manual: 'Manual', off: 'Off', paused: 'Paused', proposes: 'Proposes', autonomous: 'Autonomous' };
const TIERS = ['c', 'b', 'a'];
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const num = (s) => (s && s.state !== 'unavailable' && s.state !== 'unknown' && s.state !== '' && !isNaN(Number(s.state)) ? Number(s.state) : null);
const fmt = (v, d = 0) => (v === null || v === undefined ? '--' : Number(v).toFixed(d));

const CSS = `
:host{display:block;container-type:inline-size;background:${C.bg};color:${C.text};font-family:'IBM Plex Sans',system-ui,sans-serif;min-height:100%}
*{box-sizing:border-box} .mono{font-family:'IBM Plex Mono',ui-monospace,monospace}
.root{max-width:1320px;margin:0 auto;padding:24px;display:flex;flex-direction:column;gap:28px}
@container (max-width:700px){.root{padding:16px}} @container (max-width:480px){.root{padding:12px}}
h1{margin:0;font-size:30px;font-weight:600} h2{margin:0;font-size:20px;font-weight:600}
section{display:flex;flex-direction:column;gap:12px} .row{display:flex;flex-wrap:wrap;gap:12px} .mute{color:${C.mute}} .sm{font-size:13px}
.card{background:${C.panel};border:1px solid ${C.line};border-radius:8px;padding:14px;display:flex;flex-direction:column;gap:8px;min-width:0}
button{font-family:inherit;cursor:pointer;min-height:44px;border-radius:6px;border:1px solid ${C.line2};background:${C.panel};color:${C.text};font-size:15px;font-weight:500;padding:0 14px}
button:focus-visible,input:focus-visible{outline:2px solid ${C.blue};outline-offset:2px}
button.on{background:${C.greenBg};color:${C.greenFg};border-color:${C.greenLine}} button.off{background:${C.redBg};color:${C.redFg};border-color:${C.redLine}}
button.sel{background:${C.text};color:${C.bg};border-color:${C.text}} button.go{background:${C.green};color:#0f1a12;border-color:${C.green};font-weight:600}
.tile{flex:1 1 160px} .stat{flex:1 1 150px} .big{font-size:28px;font-weight:500}
.dot{width:10px;height:10px;border-radius:50%;flex:none} .banner{border:1px solid ${C.redLine};background:${C.redBg};color:${C.redFg};border-radius:8px;padding:12px 14px}
.pill{font-size:13px;color:${C.bg};background:${C.amber};padding:6px 10px;border-radius:4px}
.cell{flex:1 1 44px;min-width:44px;padding:0;border-width:2px;font-size:13px}
.ph{border:1px dashed ${C.line2};border-radius:6px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:10px;text-align:center;aspect-ratio:4/3}
img.photo{width:100%;border-radius:6px;display:block;aspect-ratio:4/3;object-fit:cover;background:#0d1011}
.backdrop{position:fixed;inset:0;z-index:10;border:0;border-radius:0;background:rgba(8,10,11,.78);min-height:0;padding:0}
.overlay{position:fixed;top:16px;left:16px;right:16px;bottom:16px;margin:0 auto;max-width:1100px;z-index:20;overflow:auto;padding:20px;border-color:${C.line2}}
input[type=text]{min-height:44px;width:100%;padding:0 12px;border-radius:6px;border:1px solid ${C.line2};background:${C.bg};color:${C.text};font-family:inherit;font-size:16px}
.two{display:flex;flex-wrap:wrap;gap:28px} .two>section{flex:1 1 420px;min-width:0}
.bar{height:8px;border-radius:3px;background:${C.line}} .bar>div{height:8px;border-radius:3px;background:${C.green}}
`;

class GreenhousePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.ui = { plant: null, expanded: false, replacing: false, draft: '', draftError: false, powerOpen: false, annotated: false };
    this.history = null; this.historyAt = 0; this.sig = '';
    this.shadowRoot.addEventListener('click', (e) => this.onClick(e));
    this.shadowRoot.addEventListener('input', (e) => { if (e.target.id === 'plant-type') { this.ui.draft = e.target.value; this.ui.draftError = false; } });
  }
  setConfig(config) { this.config = config || {}; if (this.config.demo) { this.demo = makeDemo(() => this.update()); this.update(); } }
  set hass(h) { this._hass = h; if (!this.config || !this.config.demo) this.update(); }
  get h() { return this.demo || this._hass; }
  getCardSize() { return 30; }
  s(id) { return this.h.states[id]; }

  // ---------- commands. All go to the governor or the store, never to a device.
  mqtt(topic, payload) { return this.h.callService('mqtt', 'publish', { topic, payload: typeof payload === 'string' ? payload : JSON.stringify(payload) }); }
  ask(actuator, action, value, position) { return this.mqtt('greenhouse/safety/request/ui', { id: 'ui-' + Date.now(), source: 'ui', actuator, action, value: value ?? null, position: position ?? null }); }
  onClick(e) {
    const el = e.target.closest('[data-act]'); if (!el) return;
    const [act, arg, arg2] = el.dataset.act.split(':'); const u = this.ui; const h = this.h;
    if (act === 'auth') h.callService('select', 'select_option', { entity_id: 'select.greenhouse_authority', option: arg });
    else if (act === 'kill') h.callService('switch', 'toggle', { entity_id: 'switch.greenhouse_kill' });
    else if (act === 'mod') h.callService('switch', 'toggle', { entity_id: `switch.greenhouse_${arg}_enabled` });
    else if (act === 'light') this.ask(`light_${arg}`, arg2 === 'on' ? 'off' : 'schedule_on');
    else if (act === 'humid') arg === 'on' ? this.ask('humidifier', 'off') : this.ask('humidifier', 'on', 5);
    else if (act === 'water') this.ask(`water_${arg}`, 'run', num(this.s(`input_number.gh_run_${arg}`)) ?? 60);
    else if (act === 'stopwater') this.ask('water', 'stop');
    else if (act === 'jog') this.ask('gantry', arg, Number(arg2));
    else if (act === 'home') this.ask('gantry', 'home');
    else if (act === 'plant') Object.assign(u, { plant: arg, replacing: false, draft: '', draftError: false, annotated: false });
    else if (act === 'expand') u.expanded = !u.expanded;
    else if (act === 'annot') u.annotated = !u.annotated;
    else if (act === 'power') u.powerOpen = !u.powerOpen;
    else if (act === 'replace') Object.assign(u, { replacing: true, draft: '', draftError: false });
    else if (act === 'cancel') Object.assign(u, { replacing: false, draft: '', draftError: false });
    else if (act === 'confirm') {
      const type = u.draft.trim();
      if (!type) u.draftError = true;
      else { this.mqtt('greenhouse/store/cmd/ui', { op: 'replace_plant', position: u.plant, type }); Object.assign(u, { replacing: false, draft: '' }); }
    } else if (act === 'dead') this.mqtt('greenhouse/store/cmd/ui', { op: 'mark', position: u.plant, status: 'dead' });
    else if (act === 'shoot') this.mqtt('greenhouse/motion/cmd', { op: 'visit', position: u.plant });
    else if (act === 'decide') this.mqtt(`greenhouse/proposal/${arg}/decision`, arg2);
    this.sig = ''; this.update();
  }

  // ---------- data
  model() {
    const st = this.h.states; const m = {};
    m.up = this.s('binary_sensor.greenhouse_supervisor_alive')?.state === 'on';
    m.known = !!this.s('select.greenhouse_authority');
    m.authority = this.s('select.greenhouse_authority')?.state; m.kill = this.s('switch.greenhouse_kill')?.state === 'on';
    m.modules = Object.keys(st).map((id) => /^sensor\.greenhouse_([a-z0-9]+)_status$/.exec(id)).filter(Boolean).map(([id, name]) => {
      const a = st[id].attributes || {};
      return { name, title: a.title || name, layer: a.layer, state: m.up || a.layer === undefined ? st[id].state : 'offline', mode: a.mode, detail: a.detail,
        version: a.version, on: this.s(`switch.greenhouse_${name}_enabled`)?.state !== 'off' };
    }).filter((x) => x.layer);
    const tier = (t, k) => num(this.s(`sensor.greenhouse_tier_${t}_${k}`));
    const mean = (k) => { const v = TIERS.map((t) => tier(t, k)).filter((x) => x !== null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
    const unit = (k, d) => this.s(`sensor.greenhouse_tier_a_${k}`)?.attributes?.unit_of_measurement || d;
    const per = (k, d) => TIERS.slice().reverse().map((t) => `${t.toUpperCase()} ${fmt(tier(t, k), d)}`).join('  ');
    const delta = TIERS.map((t) => { const c = tier(t, 'canopy_temperature'), a = tier(t, 'air_temperature'); return c === null || a === null ? null : c - a; }).filter((x) => x !== null);
    m.env = [['Air temperature', fmt(mean('air_temperature'), 1), unit('air_temperature', '°C'), per('air_temperature', 1)],
      ['Humidity', fmt(mean('air_humidity'), 0), '%', per('air_humidity', 0)], ['VPD', fmt(mean('vpd'), 2), 'kPa', per('vpd', 2)],
      ['Soil moisture', fmt(mean('median_moisture'), 0), '%', per('median_moisture', 0)],
      ['CO2', fmt(num(this.s('sensor.greenhouse_tier_c_co2')), 0), 'ppm', 'Top tier'],
      ['Leaf delta', fmt(delta.length ? delta.reduce((a, b) => a + b, 0) / delta.length : null, 1), unit('air_temperature', '°C').replace('°', 'Δ°'), 'Leaf minus air']];
    m.lights = TIERS.slice().reverse().map((t) => [t, this.s(`light.greenhouse_tier_${t}_grow_light`)?.state]);
    m.humid = this.s('switch.greenhouse_utility_humidifier')?.state; m.watering = this.s('binary_sensor.greenhouse_utility_watering_active')?.state;
    m.exhaust = this.s('fan.greenhouse_tier_c_exhaust_fans')?.attributes?.percentage;
    m.reservoir = num(this.s('sensor.greenhouse_utility_reservoir_level'));
    const dec = this.s('sensor.greenhouse_last_decision'); m.decision = dec && dec.attributes && dec.attributes.actuator ? dec.attributes : null;
    const w = num(this.s('sensor.greenhouse_utility_cabinet_power')), amp = num(this.s('sensor.greenhouse_utility_cabinet_current'));
    const volt = num(this.s('sensor.greenhouse_utility_cabinet_voltage'));
    m.power = { w, amp: amp ?? (w !== null && volt ? w / volt : null), volt, day: num(this.s('sensor.greenhouse_energy_today')), month: num(this.s('sensor.greenhouse_energy_this_month')) };
    m.loads = Object.keys(st).filter((id) => id.startsWith('sensor.greenhouse_power_')).map((id) => [(st[id].attributes.friendly_name || id).replace(/^Greenhouse power /i, ''), num(st[id])])
      .filter((x) => x[1] !== null).sort((a, b) => b[1] - a[1]);
    m.plants = {};
    Object.keys(st).forEach((id) => { const r = /^sensor\.greenhouse_plant_([abc]\d\d)$/.exec(id); if (r) m.plants[r[1].toUpperCase()] = Object.assign({ status: st[id].state }, st[id].attributes); });
    m.proposals = this.s('sensor.greenhouse_proposals')?.attributes?.items || [];
    m.env_out = this.s('sensor.greenhouse_envagent_output')?.attributes; m.tender_out = this.s('sensor.greenhouse_tender_output')?.attributes;
    m.busy = this.s('binary_sensor.greenhouse_robot_busy')?.state === 'on';
    return m;
  }
  loadHistory() {
    if (Date.now() - this.historyAt < 300000) return;
    this.historyAt = Date.now();
    const end = new Date(), start = new Date(end - 86400000), id = 'sensor.greenhouse_utility_cabinet_power';
    const done = (rows) => { this.history = (rows || []).map((r) => [(r.lu ?? r.lc ?? 0) * 1000, Number(r.s)]).filter((p) => !isNaN(p[1])); this.sig = ''; this.update(); };
    if (this.demo) return done(this.demo.history());
    this._hass.callWS({ type: 'history/history_during_period', start_time: start.toISOString(), end_time: end.toISOString(), entity_ids: [id], minimal_response: true, no_attributes: true })
      .then((r) => done(r[id]), () => done([]));
  }

  update() {
    if (!this.h || !this.config) return;
    this.loadHistory();
    const m = this.model();
    const sig = JSON.stringify([m, this.ui, this.history && this.history.length]);
    if (sig === this.sig) return;
    if (this.shadowRoot.activeElement && this.shadowRoot.activeElement.id === 'plant-type' && this.ui.replacing) { this.pending = true; return; }
    this.sig = sig;
    this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="root">${this.view(m)}</div>`;
  }

  // ---------- rendering
  view(m) {
    if (!m.known) return `<header><div class="mono sm mute">Red Tower / Greenhouse</div><h1>Maag</h1></header>
      <div class="banner">The greenhouse stack has not reported to Home Assistant yet. This view fills in once the Jetson core is running.</div>`;
    const plantIds = Object.keys(m.plants).sort();
    if (!this.ui.plant || !m.plants[this.ui.plant]) this.ui.plant = plantIds.find((p) => m.plants[p].status === 'attention') || plantIds[0];
    return `${this.header(m)}${m.up ? '' : '<div class="banner">The Jetson is not answering, so its modules are shown as offline. The ESPHome nodes keep lights, fans and their own safety limits running.</div>'}
      ${this.authority(m)}${this.modules(m)}${this.environment(m)}${this.power(m)}<div class="two">${this.plants(m)}${this.console(m)}</div>`;
  }
  header(m) {
    return `<header class="row" style="justify-content:space-between;align-items:center"><div><div class="mono sm mute">Red Tower / Greenhouse</div><h1>Maag</h1></div>
      <div class="row" style="align-items:center">${this.config.demo ? '<div class="pill mono">Simulated data</div>' : ''}
      <button data-act="kill" aria-pressed="${m.kill}" style="font-weight:600;${m.kill ? `background:${C.red};color:#2a0f09;border-color:${C.red}` : `color:${C.redFg};border-color:#a5574a`}">${m.kill ? 'Agents halted, tap to release' : 'Agent kill switch'}</button></div></header>`;
  }
  authority(m) {
    const help = (MODES.find((x) => x[0] === m.authority) || [])[2] || '';
    return `<section><h2 style="font-size:14px;font-weight:500" class="mute">Authority ceiling</h2><div class="row" style="gap:8px">
      ${MODES.map(([id, label]) => `<button data-act="auth:${id}" aria-pressed="${m.authority === id}" class="${m.authority === id ? 'sel' : ''}">${label}</button>`).join('')}</div>
      <div class="sm mute" style="font-size:14px">${esc(help)}</div></section>`;
  }
  modules(m) {
    const tile = (x) => {
      const [label, color] = STATE_LOOK[x.state] || [x.state, C.mute]; const core = x.layer === 'core';
      return `<div class="card tile" style="justify-content:space-between;gap:10px;${x.state === 'disabled' ? `border-color:#8a3a32` : ''}">
        <div class="row" style="justify-content:space-between;gap:8px;flex-wrap:nowrap"><div style="min-width:0"><div style="font-size:16px;font-weight:600">${esc(x.title)}</div>
        <div class="sm mute" title="${esc(x.detail)}">${esc(x.detail || '')}</div></div><div class="mono mute" style="font-size:12px">${core ? '' : 'v' + esc(x.version)}</div></div>
        <div class="row" style="align-items:center;gap:8px"><div class="dot" style="background:${color}"></div><div style="font-size:14px;font-weight:500;color:${color}">${esc(label)}</div>
        <div class="sm mute" style="margin-left:auto">${esc(MODE_LABEL[x.mode] || '')}</div></div>
        ${core ? `<div class="mute" style="min-height:44px;display:flex;align-items:center;justify-content:center;border:1px dashed ${C.line2};border-radius:6px;font-size:14px">Always on</div>`
    : `<button data-act="mod:${x.name}" aria-pressed="${x.on}" aria-label="${esc(x.title)}, ${x.on ? 'enabled' : 'disabled'}" class="${x.on ? 'on' : 'off'}" style="font-weight:600">${x.on ? 'Enabled' : 'Disabled'}</button>`}</div>`;
    };
    return `<section style="gap:16px"><h2>Modules</h2>${LAYERS.map(([layer, label]) => `<div style="display:flex;flex-direction:column;gap:8px"><div class="mono sm mute">${label}</div>
      <div class="row">${m.modules.filter((x) => x.layer === layer).sort((a, b) => a.title.localeCompare(b.title)).map(tile).join('')}</div></div>`).join('')}</section>`;
  }
  environment(m) {
    const d = m.decision; const dc = d ? (d.result === 'approved' ? C.green : d.result === 'proposed' ? C.yellow : C.red) : C.mute;
    const chip = (act, label, on) => `<button data-act="${act}" aria-pressed="${on}" class="${on ? 'on' : ''}">${label}</button>`;
    return `<section><h2>Environment</h2><div class="row">${m.env.map(([l, v, u, sub]) => `<div class="card stat" style="gap:6px"><div class="sm mute">${l}</div>
      <div style="display:flex;align-items:baseline;gap:6px"><div class="mono big">${v}</div><div class="mute" style="font-size:14px">${esc(u)}</div></div><div class="sm mute mono" style="font-size:12px">${esc(sub)}</div></div>`).join('')}</div>
      <div class="row" style="gap:8px">${m.lights.map(([t, s]) => chip(`light:${t}:${s === 'on' ? 'on' : 'off'}`, `Lights ${t.toUpperCase()}: ${s === 'on' ? 'on' : 'off'}`, s === 'on')).join('')}
      ${chip(`humid:${m.humid === 'on' ? 'on' : 'off'}`, `Humidifier: ${m.humid === 'on' ? 'on' : 'off'}`, m.humid === 'on')}
      ${['a', 'b', 'c'].map((t) => `<button data-act="water:${t}">Water ${t.toUpperCase()}</button>`).join('')}<button data-act="stopwater">Stop watering</button></div>
      <div class="sm mute">Pump: ${m.watering === 'on' ? 'running' : 'idle'}. Exhaust: ${fmt(m.exhaust ?? null)} %. Reservoir: ${fmt(m.reservoir)} %. These buttons are manual overrides and still pass through the safety governor.</div>
      ${d ? `<div class="sm" style="color:${dc}">Last request: ${esc(d.source)} asked ${esc(d.actuator)} ${esc(d.action)}${d.value !== null && d.value !== undefined ? ' ' + esc(d.value) : ''}: ${esc(d.result)}${d.reason ? ', ' + esc(d.reason) : ''}.</div>` : ''}</section>`;
  }
  power(m) {
    const p = m.power; const pts = this.history || [];
    const peak = pts.length ? Math.max(...pts.map((x) => x[1])) : null;
    const top = Math.max(100, Math.ceil(((peak ?? p.w ?? 100) * 1.1) / 80) * 80);
    const t1 = Date.now(), t0 = t1 - 86400000; const seg = []; let prevY = null;
    pts.forEach(([t, w]) => { const x = ((Math.max(t, t0) - t0) / 864e5 * 240).toFixed(1), y = (150 - Math.min(w, top) / top * 150).toFixed(1);
      if (prevY !== null) seg.push(`${x},${prevY}`); seg.push(`${x},${y}`); prevY = y; });
    if (prevY !== null) seg.push(`240,${prevY}`);
    const line = seg.join(' ');
    const tiles = [['Draw now', fmt(p.w), 'W', p.amp !== null ? `${fmt(p.amp, 1)} A${p.volt ? ' at ' + fmt(p.volt) + ' V' : ''}` : 'Metered at the cabinet inlet'],
      ['Peak, last 24 hours', fmt(peak), 'W', 'From the metered history'], ['Energy today', fmt(p.day, 2), 'kWh', 'Since midnight'], ['Energy this month', fmt(p.month, 1), 'kWh', 'Metered']];
    const maxLoad = Math.max(1, ...m.loads.map((x) => x[1]));
    const hours = [0, 6, 12, 18, 24].map((h) => { const d = new Date(t0 + h * 36e5); return `<div>${String(d.getHours()).padStart(2, '0')}:00</div>`; }).join('');
    return `<section><div class="row" style="justify-content:space-between;align-items:baseline;gap:8px"><h2>Power</h2><div class="sm mute">Whole cabinet, metered at the inlet.</div></div>
      <div class="row">${tiles.map(([l, v, u, sub]) => `<div class="card stat" style="gap:6px"><div class="sm mute">${l}</div><div style="display:flex;align-items:baseline;gap:6px"><div class="mono big">${v}</div><div class="mute" style="font-size:14px">${u}</div></div><div class="sm mute">${esc(sub)}</div></div>`).join('')}</div>
      <div class="row"><div class="card" style="flex:3 1 320px;gap:10px"><div class="row" style="justify-content:space-between;align-items:center;gap:8px"><div style="font-size:14px;font-weight:500">Whole system draw over 24 hours, watts</div>
      <button data-act="power" aria-expanded="${this.ui.powerOpen}">${this.ui.powerOpen ? 'Hide by subsystem' : 'Show by subsystem'}</button></div>
      <div style="display:flex;gap:8px"><div class="mono mute" style="display:flex;flex-direction:column;justify-content:space-between;height:150px;font-size:12px;text-align:right"><div>${top}</div><div>${top / 2}</div><div>0</div></div>
      <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:6px"><div style="height:150px;border-bottom:1px solid ${C.line2}">
      ${pts.length ? `<svg viewBox="0 0 240 150" preserveAspectRatio="none" role="img" aria-label="Cabinet power over the last 24 hours, peak ${fmt(peak)} watts" style="display:block;width:100%;height:150px;overflow:visible">
        <line x1="0" y1="75" x2="240" y2="75" style="stroke:${C.line};stroke-width:1;vector-effect:non-scaling-stroke"></line>
        <polyline points="${line}" style="fill:none;stroke:${C.green};stroke-width:2;stroke-linejoin:round;vector-effect:non-scaling-stroke"></polyline></svg>`
    : `<div class="mute sm" style="height:150px;display:flex;align-items:center;justify-content:center">No power history yet.</div>`}</div>
      <div class="mono mute" style="display:flex;justify-content:space-between;font-size:12px">${hours}</div></div></div></div>
      ${this.ui.powerOpen ? `<div class="card" style="flex:2 1 260px;gap:10px"><div style="font-size:14px;font-weight:500">Draw now by subsystem</div>
        ${m.loads.length ? m.loads.map(([l, w]) => `<div style="display:flex;flex-direction:column;gap:4px"><div style="display:flex;justify-content:space-between;gap:8px;font-size:14px"><div style="text-transform:capitalize">${esc(l)}</div><div class="mono">${fmt(w)} W</div></div>
        <div class="bar"><div style="width:${Math.max(2, Math.round(w / maxLoad * 100))}%"></div></div></div>`).join('') : '<div class="sm mute">No subsystem sensors yet.</div>'}
        <div class="sm mute">Subsystem values are computed from device state and rated power. Only the total is metered.</div></div>` : ''}</div></section>`;
  }
  plants(m) {
    const look = (p, sel) => { const s = p.status; const t = s === 'dead' ? [C.redBg, C.redFg, C.redLine] : s === 'attention' ? [C.yellowBg, C.yellow, C.yellowLine] : s === 'ready' ? [C.greenBg, C.greenFg, C.greenLine] : [C.panel, s === 'empty' ? C.mute : C.soft, C.line];
      return `background:${t[0]};color:${t[1]};border-color:${sel ? C.text : t[2]};${s === 'empty' ? 'border-style:dashed;' : ''}`; };
    const legend = [[C.green, 'Ready to pick'], [C.yellow, 'Needs attention or a decision'], [C.red, 'Dead, to be replaced']].map(([c, l]) => `<div style="display:flex;align-items:center;gap:6px"><div style="width:12px;height:12px;border-radius:3px;background:${c}"></div><div>${l}</div></div>`).join('');
    return `<section><h2>Plants</h2><div class="row sm" style="gap:14px;color:${C.soft}">${legend}</div>
      ${TIERS.map((t) => `<div style="display:flex;flex-direction:column;gap:6px"><div class="mono sm mute">Tier ${t.toUpperCase()}</div><div class="row" style="gap:6px">
        ${Object.keys(m.plants).filter((p) => p[0] === t.toUpperCase()).sort().map((p) => `<button class="cell mono" data-act="plant:${p}" aria-pressed="${p === this.ui.plant}" aria-label="Plant ${p}, ${esc(m.plants[p].status)}" style="${look(m.plants[p], p === this.ui.plant)}">${p.slice(1)}</button>`).join('')}</div></div>`).join('')}
      ${this.plantCard(m)}</section>`;
  }
  plantCard(m) {
    const u = this.ui, pos = u.plant, p = m.plants[pos]; if (!p) return '';
    const id = pos.toLowerCase(), t = id[0];
    const cam = this.s(`camera.greenhouse_${u.annotated ? 'annotated' : 'photo'}_${id}`), hist = this.s(`camera.greenhouse_history_${id}`);
    const pic = (c) => (c && c.attributes && c.attributes.entity_picture && c.state !== 'unavailable' ? `${c.attributes.entity_picture}&t=${encodeURIComponent(c.last_updated || '')}` : null);
    const obs = this.s(`sensor.greenhouse_observation_${id}`)?.attributes || {};
    const inch = this.h.config && this.h.config.unit_system && this.h.config.unit_system.length === 'mi';
    const len = (mm) => (mm === null || mm === undefined ? '--' : inch ? `${(mm / 25.4).toFixed(1)} in` : `${(mm / 10).toFixed(1)} cm`);
    const moist = num(this.s(`sensor.greenhouse_tier_${t}_${id}_moisture`));
    const days = p.planted ? Math.max(0, Math.floor((Date.now() / 1000 - p.planted) / 86400)) : null;
    const ms = p.milestones || [], stage = p.stage || 0, empty = p.status === 'empty';
    const status = { dead: ['Dead, replace this plant', C.red], attention: ['Needs your attention', C.yellow], ready: ['Ready to pick', C.green], empty: ['Empty position', C.mute] }[p.status]
      || [ms[stage + 1] ? 'Next: ' + ms[stage + 1] : 'Growing', C.mute];
    const note = m.tender_out && m.tender_out.position === pos ? m.tender_out.note : '';
    const src = pic(cam);
    return `${u.expanded ? '<button class="backdrop" data-act="expand" aria-label="Close plant card"></button>' : ''}
      <div class="card ${u.expanded ? 'overlay' : ''}" style="gap:14px">
      <div class="row" style="justify-content:space-between;align-items:center;gap:8px"><div class="mute" style="font-size:14px;font-weight:500">Plant card</div><button data-act="expand">${u.expanded ? 'Close' : 'Expand'}</button></div>
      <div class="row" style="gap:14px"><div style="flex:1 1 150px;min-width:0;display:flex;flex-direction:column;gap:6px">
        ${src ? `<img class="photo" src="${esc(src)}" alt="Latest photo of plant ${pos}">` : `<div class="ph"><div style="font-size:14px;font-weight:500">Daily photo</div><div class="sm mute">No capture yet</div></div>`}
        <div class="row" style="gap:6px"><button data-act="annot" aria-pressed="${u.annotated}" class="${u.annotated ? 'sel' : ''}" style="flex:1">Candidates</button><button data-act="shoot" style="flex:1" ${empty ? 'disabled' : ''}>Photo now</button></div></div>
      <div style="flex:2 1 220px;min-width:0;display:flex;flex-direction:column;gap:10px"><div><div class="mono sm mute">Tier ${pos[0]}, position ${Number(pos.slice(1))}</div>
        <div style="font-size:18px;font-weight:600">${esc(empty ? 'Empty' : p.common || p.type)}</div><div class="mute" style="font-size:14px;font-style:italic">${esc(p.scientific || (empty ? '' : p.profile === 'pending' ? 'Care profile pending' : ''))}</div></div>
        <div class="row" style="gap:8px">${[['Soil moisture', moist === null ? '--' : fmt(moist) + ' %'], ['Height', len(obs.height_mm)], ['Width', len(obs.width_mm)], ['Days planted', days === null ? '--' : String(days)]]
    .map(([l, v]) => `<div style="flex:1 1 90px;min-width:0;border:1px solid ${C.line};border-radius:6px;padding:8px"><div class="mute" style="font-size:12px">${l}</div><div class="mono" style="font-size:16px">${v}</div></div>`).join('')}</div>
        <div class="sm mute">${esc(note || (empty ? 'Use Replace plant to register what you put here.' : ''))}</div></div></div>
      ${empty ? '' : `<div style="display:flex;flex-direction:column;gap:8px"><div class="row" style="justify-content:space-between;gap:8px;align-items:baseline"><div style="font-size:14px;font-weight:500">Growth</div><div style="font-size:14px;font-weight:600;color:${status[1]}">${esc(status[0])}</div></div>
        <div style="display:flex;gap:4px">${ms.map((l, i) => `<div style="flex:1 1 0;min-width:0;display:flex;flex-direction:column;gap:6px"><div style="height:10px;border-radius:3px;background:${i <= stage ? C.green : C.line}"></div><div style="font-size:12px;color:${i === stage ? C.text : C.mute};overflow-wrap:anywhere">${esc(l)}</div></div>`).join('')}</div>
        <div class="sm mute">Stage is assessed by the plant tender from each daily photo and the depth measurements.</div></div>`}
      ${u.expanded ? `<div style="display:flex;flex-direction:column;gap:8px"><div style="font-size:14px;font-weight:500">Photo history, newest first</div>
        ${pic(hist) ? `<img src="${esc(pic(hist))}" alt="Photo history of plant ${pos}" style="max-width:100%;border-radius:6px">` : '<div class="sm mute">No history yet.</div>'}</div>` : ''}
      ${u.replacing ? `<div style="border:1px solid ${C.line2};border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:10px">
        <label for="plant-type" style="font-size:14px;font-weight:500">New plant type for this position</label>
        <input id="plant-type" type="text" value="${esc(u.draft)}" placeholder="For example: thyme">
        ${u.draftError ? `<div class="sm" style="color:${C.red}">Enter a plant type first.</div>` : ''}
        <div class="sm mute">Your entry is the record. Confirming resets the growth bar and loads the care profile for the new type.</div>
        <div class="row" style="gap:8px"><button class="go" data-act="confirm" style="flex:1">Confirm</button><button data-act="cancel" style="flex:1">Cancel</button></div></div>`
    : `<div class="row" style="gap:8px"><button data-act="replace" style="flex:1">Replace plant</button>${empty || p.status === 'dead' ? '' : '<button data-act="dead" style="flex:1">Mark as dead</button>'}</div>`}</div>`;
  }
  console(m) {
    const o = m.env_out; const when = (ts) => (ts ? new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '');
    const live = this.s('camera.greenhouse_live_d405'); const src = live && live.attributes.entity_picture && live.state !== 'unavailable' ? `${live.attributes.entity_picture}&t=${encodeURIComponent(live.last_updated || '')}` : null;
    return `<section><h2>Agent console</h2><div class="card"><div class="sm mute">Latest output, environment agent</div>
      <div style="font-size:15px;line-height:1.55;${o && o.failed ? `color:${C.redFg}` : ''}">${esc(o ? o.text : 'No cycle has run yet.')}</div>
      ${o && o.actions && o.actions.length ? `<div class="sm mute">${o.actions.map((a) => `${esc(a.type)}${a.tier ? ' ' + esc(a.tier.toUpperCase()) : ''}${a.value !== null && a.value !== undefined ? ' ' + esc(a.value) : ''}: ${esc(a.result)}`).join(' · ')}</div>` : ''}
      <div class="mono mute" style="font-size:12px">${o ? 'At ' + when(o.ts) : ''}</div></div>
      <div class="mute" style="font-size:14px;font-weight:500">Approval queue</div>
      ${m.proposals.length ? m.proposals.map((q) => `<div class="card" style="gap:10px"><div><div class="mono sm mute">${esc(q.source)}${q.position ? ' · ' + esc(q.position) : ''} · ${when(q.created)}</div>
        <div style="font-size:15px">${esc(q.actuator)} ${esc(q.action)}${q.value !== null && q.value !== undefined ? ' ' + esc(q.value) : ''}</div><div class="sm mute">${esc(q.reason_given || '')}</div></div>
        <div class="row" style="gap:8px"><button class="go" data-act="decide:${esc(q.id)}:approve" style="flex:1">Approve</button><button data-act="decide:${esc(q.id)}:reject" style="flex:1">Reject</button></div></div>`).join('')
    : `<div class="sm mute" style="border:1px dashed ${C.line2};border-radius:8px;padding:18px;font-size:14px">Nothing waiting for approval.</div>`}
      ${src ? `<img class="photo" src="${esc(src)}" alt="Live view from the arm camera">` : `<div class="ph" style="aspect-ratio:auto;min-height:200px"><div style="font-size:15px;font-weight:500">Live view</div><div class="sm mute">Arm camera stream appears here when the depth camera module is running.</div></div>`}
      <div class="sm mute">Robot: ${m.busy ? 'moving' : 'idle'}</div>
      <div class="row" style="gap:8px">${[['jog:jog_x:-20', 'X -'], ['jog:jog_x:20', 'X +'], ['jog:jog_z:-20', 'Z -'], ['jog:jog_z:20', 'Z +'], ['home', 'Home']].map(([a, l]) => `<button data-act="${a}" style="flex:1 1 70px">${l}</button>`).join('')}</div></section>`;
  }
}

// ------------------------------------------------------------------ simulated data
function makeDemo(changed) {
  const now = () => Date.now() / 1000; const S = {};
  const put = (id, state, attributes = {}) => { S[id] = { entity_id: id, state: String(state), attributes, last_updated: new Date().toISOString() }; };
  const mods = [['envagent', 'Environment agent', 'agent', ['climate', 'llm']], ['tender', 'Plant tender', 'agent', ['perception', 'motion', 'llm']], ['llm', 'LLM gateway', 'agent', []],
    ['climate', 'Climate', 'service', ['esphome']], ['irrigation', 'Irrigation', 'service', ['esphome']], ['nutrients', 'Nutrients', 'service', ['esphome']],
    ['perception', 'Perception', 'service', ['d405']], ['motion', 'Motion', 'service', ['arm', 'gantry']], ['arm', 'Arm', 'driver', []], ['gantry', 'Gantry', 'driver', []],
    ['d405', 'Depth camera', 'driver', []], ['widecam', 'Overview camera', 'driver', []], ['esphome', 'ESPHome link', 'driver', []],
    ['supervisor', 'Supervisor', 'core', []], ['safety', 'Safety governor', 'core', []], ['store', 'State store', 'core', []], ['bridge', 'HA bridge', 'core', []]];
  const stubs = { nutrients: 1, arm: 1, gantry: 1 }; const enabled = Object.fromEntries(mods.map((m) => [m[0], m[0] !== 'nutrients']));
  let authority = 'proposes', kill = false;
  const details = { climate: 'VPD 1.08 kPa, target 1.00', irrigation: 'A 41%, B 47%, C 52%', llm: '18400 of 400000 tokens used today', widecam: '' };
  const recompute = () => {
    const out = {};
    mods.slice().reverse().forEach(() => {});
    const order = ['supervisor', 'safety', 'store', 'bridge', 'arm', 'gantry', 'd405', 'widecam', 'esphome', 'climate', 'irrigation', 'nutrients', 'perception', 'motion', 'llm', 'envagent', 'tender'];
    order.forEach((n) => {
      const [, title, layer, deps] = mods.find((m) => m[0] === n); const agentOn = ['proposes', 'autonomous'].includes(authority);
      let state = 'running';
      if (layer !== 'core') {
        if (n === 'widecam') state = 'missing'; else if (authority === 'off') state = 'stopped'; else if (!enabled[n]) state = 'disabled';
        else if (layer === 'agent' && kill) state = 'halted'; else if (layer === 'agent' && !agentOn) state = 'paused';
        else if (deps.some((d) => !['running', 'stub'].includes(out[d]))) state = 'degraded'; else if (stubs[n]) state = 'stub';
      }
      out[n] = state;
      const mode = layer === 'service' ? (authority === 'off' ? 'off' : authority === 'manual' ? 'manual' : 'auto') : layer === 'agent' ? (agentOn ? authority : authority === 'off' ? 'off' : 'paused') : '';
      put(`sensor.greenhouse_${n}_status`, state, { title, layer, mode, version: '0.1.0', detail: state === 'degraded' ? 'waiting on ' + deps.filter((d) => !['running', 'stub'].includes(out[d])).join(', ') : state === 'running' ? details[n] || '' : '' });
      if (layer !== 'core') put(`switch.greenhouse_${n}_enabled`, enabled[n] ? 'on' : 'off');
    });
    put('select.greenhouse_authority', authority, { options: MODES.map((m) => m[0]) }); put('switch.greenhouse_kill', kill ? 'on' : 'off');
  };
  put('binary_sensor.greenhouse_supervisor_alive', 'on');
  [['a', 24.6, 57, 1.12, 41, 23.4], ['b', 24.1, 60, 1.03, 47, 23.2], ['c', 25.3, 55, 1.21, 52, 24.4]].forEach(([t, temp, rh, vpd, moist, canopy]) => {
    put(`sensor.greenhouse_tier_${t}_air_temperature`, temp, { unit_of_measurement: '°C' }); put(`sensor.greenhouse_tier_${t}_air_humidity`, rh);
    put(`sensor.greenhouse_tier_${t}_vpd`, vpd); put(`sensor.greenhouse_tier_${t}_median_moisture`, moist); put(`sensor.greenhouse_tier_${t}_canopy_temperature`, canopy);
    put(`light.greenhouse_tier_${t}_grow_light`, 'on');
  });
  put('sensor.greenhouse_tier_c_co2', 612); put('switch.greenhouse_utility_humidifier', 'off'); put('binary_sensor.greenhouse_utility_watering_active', 'off');
  put('fan.greenhouse_tier_c_exhaust_fans', 'on', { percentage: 35 }); put('sensor.greenhouse_utility_reservoir_level', 78);
  put('sensor.greenhouse_utility_cabinet_power', 203); put('sensor.greenhouse_utility_cabinet_current', 1.7); put('sensor.greenhouse_utility_cabinet_voltage', 120);
  put('sensor.greenhouse_energy_today', 2.41); put('sensor.greenhouse_energy_this_month', 9.8);
  [['lights', 158], ['compute', 17], ['nodes and network', 13], ['robot', 5], ['fans', 4], ['water', 0], ['unaccounted', 6]].forEach(([n, w]) => put(`sensor.greenhouse_power_${n.replace(/ /g, '_')}`, w, { friendly_name: 'Greenhouse power ' + n }));
  const lib = { pepper: ['Compact pepper', 'Capsicum annuum', ['Seedling', 'Vegetative', 'Flowering', 'Fruit set', 'Ripe']], basil: ['Basil', 'Ocimum basilicum', ['Seedling', 'Established', 'Bushy', 'Ready to cut']],
    parsley: ['Parsley', 'Petroselinum crispum', ['Seedling', 'Established', 'Bushy', 'Ready to cut']], thyme: ['Thyme', 'Thymus vulgaris', ['Seedling', 'Established', 'Bushy', 'Ready to cut']] };
  const plant = (pos, type, stage, status) => {
    const L = lib[type.toLowerCase()];
    put(`sensor.greenhouse_plant_${pos.toLowerCase()}`, status, type ? { position: pos, type, type_confirmed: true, common: L ? L[0] : type, scientific: L ? L[1] : null, profile: L ? 'ready' : 'pending',
      milestones: L ? L[2] : ['Seedling', 'Established', 'Mature', 'Ready'], stage, planted: now() - (12 + stage * 17) * 86400 } : { position: pos, type: null, milestones: [], stage: 0 });
    if (type) { put(`sensor.greenhouse_tier_${pos[0].toLowerCase()}_${pos.toLowerCase()}_moisture`, 34 + (pos.charCodeAt(2) * 7) % 22); put(`sensor.greenhouse_observation_${pos.toLowerCase()}`, 40 + stage * 38, { height_mm: 40 + stage * 38, width_mm: 80 + stage * 20 }); }
  };
  for (let n = 1; n <= 7; n++) plant('A0' + n, 'pepper', n % 5, n % 5 === 4 ? 'ready' : 'ok');
  for (let n = 1; n <= 10; n++) plant('B' + String(n).padStart(2, '0'), n % 2 ? 'basil' : 'parsley', n % 4, n % 4 === 3 ? 'ready' : 'ok');
  for (let n = 1; n <= 10; n++) plant('C' + String(n).padStart(2, '0'), n % 3 ? 'thyme' : 'basil', (n + 1) % 4, (n + 1) % 4 === 3 ? 'ready' : 'ok');
  plant('A04', 'pepper', 1, 'attention'); plant('B07', 'parsley', 2, 'attention'); plant('C05', 'thyme', 1, 'dead'); plant('C09', '', 0, 'empty');
  let proposals = [{ id: 'p1', source: 'tender', actuator: 'robot', action: 'tend', value: 'pinch C3', position: 'A04', created: now() - 900, reason_given: 'pinch at C3: growth tip is leggy, pinching will make the plant bushier' },
    { id: 'p2', source: 'tender', actuator: 'robot', action: 'tend', value: 'remove_leaf C1', position: 'B07', created: now() - 600, reason_given: 'remove_leaf at C1: one yellowed lower leaf' }];
  const pubProps = () => { put('sensor.greenhouse_proposals', proposals.length, { items: proposals }); };
  put('sensor.greenhouse_envagent_output', 'x', { ts: now() - 480, failed: false, text: 'VPD is holding inside the target band on all three tiers. Tier A soil moisture is trending down, so the next watering stays as scheduled. No setpoint change this cycle.', actions: [] });
  put('sensor.greenhouse_tender_output', 'x', { position: 'A04', note: 'Healthy, but the main stem is stretching toward the light.' });
  put('binary_sensor.greenhouse_robot_busy', 'off');
  recompute(); pubProps();
  const decision = (r) => put('sensor.greenhouse_last_decision', r.result, r);
  return { states: S, config: { unit_system: { length: 'mi' } },
    history() { const out = []; const t1 = Date.now(); for (let h = 24; h >= 0; h--) { const d = new Date(t1 - h * 36e5); const hr = d.getHours(); out.push({ lu: d / 1000, s: hr === 9 ? 300 : hr >= 6 && hr < 22 ? 203 : 45 }); } return out; },
    callService(domain, service, data) {
      if (domain === 'select') authority = data.option;
      else if (domain === 'switch' && data.entity_id === 'switch.greenhouse_kill') kill = !kill;
      else if (domain === 'switch') { const n = /greenhouse_(.+)_enabled/.exec(data.entity_id)[1]; enabled[n] = !enabled[n]; }
      else if (domain === 'mqtt') {
        const p = JSON.parse(data.payload && data.payload[0] === '{' ? data.payload : '{}');
        if (data.topic.includes('/proposal/')) { proposals = proposals.filter((q) => !data.topic.includes('/' + q.id + '/')); pubProps(); }
        else if (data.topic.endsWith('store/cmd/ui') && p.op === 'replace_plant') plant(p.position, p.type, 0, 'ok');
        else if (data.topic.endsWith('store/cmd/ui') && p.op === 'mark') { const e = S[`sensor.greenhouse_plant_${p.position.toLowerCase()}`]; put(e.entity_id, p.status, e.attributes); }
        else if (data.topic.endsWith('request/ui')) {
          const denied = authority === 'off' && !['off', 'stop'].includes(p.action);
          decision({ source: 'ui', actuator: p.actuator, action: p.action, value: p.value, result: denied ? 'denied' : 'approved', reason: denied ? 'authority is off' : 'within limits' });
          if (!denied && p.actuator.startsWith('light_')) put(`light.greenhouse_tier_${p.actuator.slice(-1)}_grow_light`, p.action === 'off' ? 'off' : 'on');
          if (!denied && p.actuator === 'humidifier') put('switch.greenhouse_utility_humidifier', p.action === 'on' ? 'on' : 'off');
        }
      }
      recompute(); changed(); return Promise.resolve();
    } };
}

if (!customElements.get('greenhouse-panel')) customElements.define('greenhouse-panel', GreenhousePanel);
window.customCards = window.customCards || [];
window.customCards.push({ type: 'greenhouse-panel', name: 'Greenhouse panel', description: 'Maag: the full greenhouse control view' });
console.info(`%c MAAG GREENHOUSE PANEL %c ${CARD_VERSION} `, 'color:#14181a;background:#7fd18b;font-weight:600', 'color:#7fd18b;background:#1d2326');
