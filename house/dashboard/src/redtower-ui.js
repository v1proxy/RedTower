/* Red Tower UI (redtower-ui.js), Vittorio's graphic style for the red-tower-new dashboard.
 * 1. While a page of /red-tower-new is open: black ground, IBM Plex, 1 px lines, square corners, red only for
 *    security; every other dashboard keeps its own look.
 * 2. custom:rt-house-card, the house in lines from the 3D model (eight views, drag or the arrows turn it).
 *    mode: health  (Home)   a floor with a device that Home Assistant can't reach is outlined red and all its lines
 *                           turn red, its label on the floor; everything nominal: the house's outline in green.
 *    mode: alarm   (RedSec) every alarm in binary_sensor.red_tower_alarm: its room a translucent red box, its window or
 *                           door a solid red outline; the drawing turns to face where it started. No alarm: green outline.
 *    Tap a label for its note, tap again to close it. Home: hold a label to open a new Claude chat in RedTower with the
 *    note typed in, titled "(INT) <what>"; say the rest with Claude's microphone and send.
 * 3. The top bar's actions as words (Add, Search, Assist, Edit) on wide screens; Maag (Greenhouse) in the dashboard's
 *    type and ground; the helpers the button-card templates call (window.rt).
 * Files beside it: axo-v0..7.svg (lines grouped by floor and kind), axo-layout.json (outlines, rooms, openings).
 * 2.1.0 (Nov 24): the lean drawings (each boundary between surfaces drawn once and straightened, no artifacts); the
 *    house fits the first screen (fit); the thermostat's dial bigger, its buttons smaller and inside the dial.
 * 2.1.1 (Nov 24): In and out splits Electricity by circuit inside its square.
 * 2.1.2 (Nov 24): the house on Home sits on the page's black, no outline (the other cards keep the grey); Digital
 *    Twin, on phones only: a small down arrow at the bottom centre of the 3D model scrolls the page to the rest,
 *    since the model takes every touch there.
 */
(() => {
  const VERSION = "2.1.2";
  const DASH = "/red-tower-new";
  const BASE = "/local/redtower-ui/";
  const C = { ground: "#000000", raised: "#111113", rule: "#2A2C30", line: "#45474D", strong: "#C9CBCF", ink: "#F3F1EC",
    text: "#C9CBCF", muted: "#8E9096", red: "#ED1C24", redText: "#F4454B", green: "#7FD18B", cool: "#4FB0FF", amber: "#F0B454" };
  const SANS = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif";
  const MONO = "'IBM Plex Mono', 'SFMono-Regular', Menlo, monospace";

  // ---- 1. the look, only on /red-tower-new --------------------------------------------------------------------
  const VARS = {
    "--primary-background-color": C.ground, "--secondary-background-color": C.raised, "--lovelace-background": C.ground,
    "--view-background": C.ground, "--card-background-color": C.raised, "--ha-card-background": C.raised,
    "--ha-card-border-color": C.rule, "--ha-card-border-width": "1px", "--ha-card-border-radius": "0px", "--ha-card-box-shadow": "none",
    "--primary-text-color": C.ink, "--secondary-text-color": C.muted, "--disabled-text-color": "#5D5F66", "--divider-color": C.rule,
    "--primary-color": C.strong, "--accent-color": C.red, "--state-icon-color": C.muted, "--state-icon-active-color": C.ink,
    "--app-header-background-color": C.ground, "--app-header-text-color": C.ink, "--app-header-selection-bar-color": C.ink,
    "--app-header-border-bottom": "1px solid " + C.line, "--sidebar-background-color": C.ground, "--sidebar-text-color": C.text,
    "--sidebar-selected-text-color": C.ink, "--sidebar-selected-icon-color": C.ink, "--sidebar-icon-color": C.muted,
    "--mdc-theme-primary": C.strong, "--switch-checked-color": C.ink, "--switch-checked-button-color": C.ink, "--switch-checked-track-color": C.line,
    "--input-fill-color": C.raised, "--mdc-text-field-fill-color": C.raised, "--code-editor-background-color": C.raised,
    "--state-climate-heat-color": C.red, "--state-climate-cool-color": C.cool, "--state-climate-heat_cool-color": C.amber,
    "--state-alarm_control_panel-triggered-color": C.red, "--state-alarm_control_panel-armed_away-color": C.red,
    "--ha-font-family-body": SANS, "--ha-font-family-heading": SANS, "--ha-font-family-code": MONO,
    "--paper-font-common-base_-_font-family": SANS, "--paper-font-common-code_-_font-family": MONO, "--mdc-typography-font-family": SANS,
    "--primary-font-family": SANS, "--ha-dialog-surface-background": C.raised, "--mdc-dialog-heading-ink-color": C.ink,
    "--ha-card-header-font-family": SANS, "--material-body-text-color": C.ink, "--table-row-background-color": C.raised,
    "--table-row-alternative-background-color": C.ground, "--data-table-background-color": C.raised,
    "--masonry-view-card-margin": "0px",
  };
  function loadFonts() {
    if (document.getElementById("rt-plex")) return;
    const f = (fam, w, file) => `@font-face{font-family:'${fam}';font-weight:${w};font-style:normal;font-display:swap;src:url('${BASE}fonts/${file}.woff2') format('woff2')}`;
    const st = document.createElement("style");
    st.id = "rt-plex";
    st.textContent = [f("IBM Plex Sans", 300, "IBMPlexSans-Light"), f("IBM Plex Sans", 400, "IBMPlexSans-Regular"), f("IBM Plex Sans", 500, "IBMPlexSans-Medium"),
      f("IBM Plex Sans", 600, "IBMPlexSans-SemiBold"), f("IBM Plex Mono", 400, "IBMPlexMono-Regular"), f("IBM Plex Mono", 500, "IBMPlexMono-Medium")].join("");
    document.head.appendChild(st);
  }
  const ROOT_CSS = `
    ha-tab-group-tab::part(base) { font: 400 15px/1 ${SANS}; color: ${C.muted}; letter-spacing: 0; }
    ha-tab-group-tab[active]::part(base) { color: ${C.ink}; }
    .rt-words { display: none; gap: 22px; align-items: center; padding: 0 20px 0 12px; height: 100%; }
    .rt-words button { background: none; border: 0; padding: 0; margin: 0; font: 400 11px/1 ${MONO}; letter-spacing: .1em; text-transform: uppercase;
      color: ${C.muted}; cursor: pointer; white-space: nowrap; }
    .rt-words button:hover, .rt-words button:focus-visible { color: ${C.ink}; }
    @media (min-width: 871px) {
      .action-items > :not(.rt-words), .action-items > ha-dropdown > [slot="trigger"] { position: absolute !important; width: 1px !important; height: 1px !important; overflow: hidden !important;
        clip: rect(0 0 0 0) !important; opacity: 0 !important; pointer-events: none !important; }
      .action-items > .rt-words { display: flex; }
    }
  `;
  // The top bar's icons as words, each word pressing the icon it stands for.
  function words(root) {
    const ai = root.shadowRoot.querySelector(".action-items");
    if (!ai) return;
    const items = [];
    for (const el of ai.children) {
      if (el.classList.contains("rt-words") || el.tagName === "HA-TOOLTIP") continue;
      let target = el, label = "";
      if (el.tagName === "HA-DROPDOWN") { target = el.querySelector("[slot=trigger]") || el; label = "Add"; }
      else {
        const tip = el.nextElementSibling && el.nextElementSibling.tagName === "HA-TOOLTIP" ? el.nextElementSibling.textContent.trim() : "";
        label = el.label || el.getAttribute("label") || el.getAttribute("title") || tip || "";
        label = /search/i.test(label) ? "Search" : /assist/i.test(label) ? "Assist" : /edit/i.test(label) ? "Edit" : /done/i.test(label) ? "Done" : label.split(" ")[0];
      }
      if (label) items.push([label, target]);
    }
    const sig = items.map(i => i[0]).join("|");
    let box = ai.querySelector(":scope > .rt-words");
    if (box && box.dataset.sig === sig) { box.__targets = items.map(i => i[1]); return; }
    if (!box) { box = document.createElement("div"); box.className = "rt-words"; ai.appendChild(box); }
    box.dataset.sig = sig; box.__targets = items.map(i => i[1]);
    box.innerHTML = items.map(([l], i) => `<button type="button" data-i="${i}">${l}</button>`).join("");
    box.onclick = e => { const b = e.target.closest("button[data-i]"); if (!b) return; const t = box.__targets[+b.dataset.i]; if (t) t.click(); };
  }
  // Maag in the dashboard's type and ground: the card keeps its own palette otherwise (Vittorio, round 3).
  const GH_TYPE = `:host{font-family:${SANS} !important} h1,h2{font-weight:300 !important} .mname,.pname,.b600,.b500,.stat{font-weight:400 !important}
    button{font-weight:400 !important} .big{font-family:${SANS} !important;font-weight:300 !important;letter-spacing:-.01em}
    .crumb,.lname{font-family:${MONO} !important;font-size:11px !important;text-transform:uppercase;letter-spacing:.1em}`;
  const ghSwap = t => String(t).replace(/#14181a/gi, "#000000").replace(/#1d2326/gi, "#111113")
    .replace(/system-ui,\s*-apple-system,\s*'Segoe UI',\s*sans-serif/g, SANS)
    .replace(/ui-monospace,\s*'SF Mono',\s*monospace|ui-monospace,\s*monospace/g, MONO);
  function fixGreenhouse(el) {
    const sr = el.shadowRoot;
    if (!sr) return;
    sr.querySelectorAll("style:not([data-rt])").forEach(st => { st.textContent = ghSwap(st.textContent); st.dataset.rt = "1"; });
    try {
      if (sr.adoptedStyleSheets && sr.adoptedStyleSheets.length && !el.__rtSheets) {
        el.__rtSheets = true;
        sr.adoptedStyleSheets = sr.adoptedStyleSheets.map(sh => { const n = new CSSStyleSheet(); n.replaceSync(ghSwap([...sh.cssRules].map(r => r.cssText).join("\n"))); return n; });
      }
    } catch (_) { /* leave the sheets */ }
    sr.querySelectorAll('[style*="#1d2326" i],[style*="#14181a" i]').forEach(n => n.setAttribute("style", ghSwap(n.getAttribute("style"))));
    if (!sr.getElementById("rt-gh")) { const st = document.createElement("style"); st.id = "rt-gh"; st.dataset.rt = "1"; st.textContent = GH_TYPE; sr.appendChild(st); }
    if (!el.__rtObs) { el.__rtObs = new MutationObserver(() => fixGreenhouse(el)); el.__rtObs.observe(sr, { childList: true, subtree: true }); }
  }
  const deepFind = (root, tag, depth = 0) => {
    if (!root || depth > 12) return null;
    const hit = root.querySelector(tag);
    if (hit) return hit;
    for (const n of root.querySelectorAll("*")) if (n.shadowRoot) { const f = deepFind(n.shadowRoot, tag, depth + 1); if (f) return f; }
    return null;
  };
  // Digital Twin: the 3D model fills the screen and takes every touch, so a small arrow under it scrolls to the rest.
  const DOWN_CSS = `.rt-down { position: absolute; left: 50%; bottom: calc(4px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); z-index: 6;
      width: 56px; height: 40px; padding: 0; margin: 0; border: 0; background: none; cursor: pointer; display: none; place-items: center;
      touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
    @media (max-width: 600px), (pointer: coarse) and (max-height: 500px) { .rt-down { display: grid; } }
    .rt-down i { display: block; width: 12px; height: 12px; margin-top: -8px; box-sizing: border-box; border-right: 1.5px solid ${C.strong};
      border-bottom: 1.5px solid ${C.strong}; transform: rotate(45deg); filter: drop-shadow(0 0 2px #000); }
    .rt-down:hover i, .rt-down:focus-visible i { border-color: ${C.ink}; }`;
  const scrollerOf = el => {
    for (let n = el; n; n = n.parentElement || (n.getRootNode && n.getRootNode().host) || null) {
      if (n === document.documentElement || n === document.body) break;
      const cs = getComputedStyle(n);
      if (/(auto|scroll)/.test(cs.overflowY) && n.scrollHeight > n.clientHeight + 4) return n;
    }
    return null;
  };
  function twinHint(el) {
    const sr = el.shadowRoot, card = sr && sr.querySelector("ha-card");
    if (!card || card.querySelector(":scope > .rt-down")) return;
    if (!sr.getElementById("rt-down-css")) { const st = document.createElement("style"); st.id = "rt-down-css"; st.textContent = DOWN_CSS; sr.appendChild(st); }
    const b = document.createElement("button");
    b.type = "button"; b.className = "rt-down"; b.title = "The rest of the page"; b.setAttribute("aria-label", "Scroll to the rest of the page");
    b.innerHTML = "<i></i>";
    const stop = e => e.stopPropagation();
    for (const t of ["pointerdown", "pointerup", "pointermove", "mousedown", "mouseup", "touchstart", "touchmove", "touchend", "wheel", "dblclick"]) b.addEventListener(t, stop, { passive: true });
    b.addEventListener("click", e => {
      e.stopPropagation(); e.preventDefault();
      // the model is the view's first card: land the content under it where the model's top sits at rest
      const r = card.getBoundingClientRect(), sc = scrollerOf(card), top = Math.round(r.height + 10);
      if (sc) sc.scrollTo({ top, behavior: "smooth" }); else window.scrollTo({ top, behavior: "smooth" });
    });
    card.appendChild(b);
  }
  let ghEl = null, twinEl = null;
  function styleRoot() {
    try {
      const ha = document.querySelector("home-assistant");
      const main = ha && ha.shadowRoot && ha.shadowRoot.querySelector("home-assistant-main");
      const ppr = main && main.shadowRoot && main.shadowRoot.querySelector("partial-panel-resolver");
      const pl = ppr && ppr.querySelector("ha-panel-lovelace");
      const root = pl && pl.shadowRoot && pl.shadowRoot.querySelector("hui-root");
      if (!root || !root.shadowRoot) return;
      if (!root.shadowRoot.getElementById("rt-root")) {
        const st = document.createElement("style");
        st.id = "rt-root"; st.textContent = ROOT_CSS;
        root.shadowRoot.appendChild(st);
      }
      words(root);
      if (/\/greenhouse$/.test(location.pathname)) {
        if (!ghEl || !ghEl.isConnected) ghEl = deepFind(root.shadowRoot, "greenhouse-panel-card");
        if (ghEl) fixGreenhouse(ghEl);
      }
      if (/\/model$/.test(location.pathname)) {
        if (!twinEl || !twinEl.isConnected) twinEl = deepFind(root.shadowRoot, "floor3dpro-axo-card");
        if (twinEl) twinHint(twinEl);
      }
    } catch (_) { /* the page is still building */ }
  }
  let themed = null;
  function applyLook() {
    const ha = document.querySelector("home-assistant");
    if (!ha) return;
    const on = location.pathname === DASH || location.pathname.startsWith(DASH + "/");
    if (on) styleRoot();
    if (on === themed) return;
    themed = on;
    loadFonts();
    for (const [k, v] of Object.entries(VARS)) on ? ha.style.setProperty(k, v) : ha.style.removeProperty(k);
  }
  window.addEventListener("location-changed", () => setTimeout(applyLook, 0));
  window.addEventListener("popstate", () => setTimeout(applyLook, 0));
  setInterval(applyLook, 1500);
  applyLook();

  const esc0 = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  // ---- 3. helpers for the dashboard's button-card templates (rt_base, rt_metric, rt_metric_hot, rt_alert, rt_action) ----
  // kind: the dot. off = ring, on = filled (ink), alarm = red (security, on), none = dashed ring (unavailable).
  const ALERT_ON = ["on", "open", "opening", "triggered", "detected", "unlocked", "armed_away", "armed_home", "armed_night", "armed_vacation", "armed_custom_bypass"];
  const IS_ON = ["on", "home", "cleaning", "charging", "playing", "returning", "heat", "cool", "heat_cool"];
  const fmt = (hass, e) => { try { return hass && hass.formatEntityState ? hass.formatEntityState(e) : e.state; } catch (_) { return e.state; } };
  window.rt = Object.assign(window.rt || {}, {
    version: VERSION,
    kind(entity, v) {
      v = v || {};
      if (v.kind) return v.kind;
      if (!entity) return "off";
      const s = entity.state;
      if (s === "unavailable") return "none";
      if (v.alert && ALERT_ON.includes(s)) return "alarm";
      if (v.hot != null) return parseFloat(s) > v.hot ? "on" : "off";
      return IS_ON.includes(s) ? "on" : "off";
    },
    dim(entity, v) {
      v = v || {};
      if (v.dim) return true;
      return !!entity && (entity.state === "unavailable" || (entity.state === "unknown" && !!v.unknown_text));
    },
    value(hass, entity, v) {
      v = v || {};
      if (v.value != null) return esc0(v.value);
      if (!entity) return "";
      if (entity.state === "unknown" && v.unknown_text) return esc0(v.unknown_text);
      const s = String(fmt(hass, entity)), u = entity.attributes && entity.attributes.unit_of_measurement;
      if (u && s.endsWith(u)) return `${esc0(s.slice(0, -u.length).trim())}<span class="u">${esc0(u)}</span>`;
      return esc0(s);
    },
    sub(hass, v) {
      v = v || {};
      if (v.sub_entity) { const e = hass && hass.states[v.sub_entity]; return e ? esc0((v.sub_prefix || "") + fmt(hass, e)) : ""; }
      return v.sub ? esc0(v.sub) : "";
    },
    actionSub(entity, v) {
      v = v || {};
      if (entity && entity.state === "unavailable") return "Unavailable";
      return esc0(v.sub || "");
    },
    arrow(dir) {
      const rot = { up: 0, right: 90, down: 180, left: 270 }[dir] || 0;
      return `<svg aria-hidden="true" width="16" height="16" viewBox="0 0 18 18" style="transform: rotate(${rot}deg)"><path d="M9 16 V2 M3.5 7.5 L9 2 L14.5 7.5" fill="none" stroke="#8E9096" stroke-width="1"/></svg>`;
    },
  });

  // ---- 2. the house in lines ------------------------------------------------------------------------------------
  const FROM = ["south-east", "south", "south-west", "west", "north-west", "north", "north-east", "east"];
  const FLOOR_NAME = { 1: "Ground floor", 2: "Second floor", 3: "Third floor" };
  const AREA_ROOM = { bedroom: "bedroom", kitchen: "kitchen", living_room: "living_room", guest_room: "guest_room", studio: "studio", garage: "garage" };
  const ROOM_VIEW = { guest_room: 2, bedroom: 2, kitchen: 4, studio: 4, living_room: 0, garage: 0, office: 2, entry: 2, hall_l2: 4 };
  const OPEN_VIEW = { window_guest_room: 2, door_balcony: 2 };
  const KIND = { door: "Open", window: "Open", opening: "Open", garage_door: "Open", smoke: "Smoke", carbon_monoxide: "Carbon monoxide",
    gas: "Gas", heat: "Heat", moisture: "Water", carbon_dioxide: "CO2" };
  const files = {};
  const fetchOnce = (url, kind) => files[url] || (files[url] = fetch(url, { cache: "force-cache" }).then(r => { if (!r.ok) throw new Error(r.status); return kind === "json" ? r.json() : r.text(); }));
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const time = iso => { const d = new Date(iso); return isNaN(d) ? "" : d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }); };
  const when = iso => {
    const d = new Date(iso); if (isNaN(d)) return "";
    const today = new Date(); const same = d.toDateString() === today.toDateString();
    if (same) return "today at " + time(iso);
    return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }) + ", " + time(iso);
  };
  const list = a => a.length < 2 ? (a[0] || "") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1];
  const ago = (a, b) => { const m = Math.round(Math.abs(new Date(b) - new Date(a)) / 60000); return m < 1 ? "seconds" : m === 1 ? "a minute" : m < 60 ? m + " minutes" : Math.round(m / 60) === 1 ? "an hour" : Math.round(m / 60) + " hours"; };
  const loopsD = (loops, s, ox, oy) => (loops || []).map(pts => "M" + pts.map(([x, y]) => `${(x * s + ox).toFixed(1)} ${(y * s + oy).toFixed(1)}`).join("L") + "Z").join("");
  const segsD = (segs, s, ox, oy) => (segs || []).map(([a, b, c, d]) => `M${(a * s + ox).toFixed(1)} ${(b * s + oy).toFixed(1)}L${(c * s + ox).toFixed(1)} ${(d * s + oy).toFixed(1)}`).join("");
  const centroid = loops => { let x = 0, y = 0, n = 0; for (const pts of loops || []) for (const [a, b] of pts) { x += a; y += b; n++; } return n ? [x / n, y / n] : null; };

  const CSS = `
    :host { display: block; }
    ha-card { display: block; border-radius: 0; box-shadow: none; overflow: hidden; box-sizing: border-box; }
    ha-card.health { background: transparent; border: none; padding: 12px 12px 0; }
    ha-card.alarm { background: transparent; border: none; padding: 4px 0 0; }
    .head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding: 0 2px 8px; white-space: nowrap; }
    .lab { font: 400 11px/1.45 ${MONO}; letter-spacing: .1em; text-transform: uppercase; color: ${C.muted}; }
    .lab.red { color: ${C.redText}; } .lab.green { color: ${C.green}; }
    .stage { position: relative; touch-action: pan-y; cursor: grab; user-select: none; -webkit-user-select: none; overflow: hidden; min-height: 120px; }
    .draw { position: absolute; pointer-events: none; }
    .draw svg { width: 100%; height: 100%; display: block; overflow: visible; }
    .draw path { stroke-linejoin: round; }
    .draw .c { stroke: #8E9096; stroke-width: .8; }
    .draw .p { stroke: #E6E4DE; stroke-width: 1.1; }
    .r1 .draw .f1, .r2 .draw .f2, .r3 .draw .f3 { stroke: ${C.red}; }
    .r1 .draw .c.f1, .r2 .draw .c.f2, .r3 .draw .c.f3 { stroke-opacity: .72; }
    svg.over { position: absolute; left: 0; top: 0; pointer-events: none; overflow: visible; }
    button.chip { position: absolute; box-sizing: border-box; padding: 5px 8px; background: ${C.ground}; border: 1px solid ${C.red}; border-radius: 0;
      display: grid; align-content: center; gap: 2px; text-align: left; cursor: pointer; z-index: 3; color: ${C.redText}; margin: 0; }
    button.chip span { font: 500 10px/1.15 ${MONO}; letter-spacing: .08em; text-transform: uppercase; white-space: nowrap; }
    button.chip span + span { font-weight: 400; }
    button.turn { position: absolute; bottom: 4px; width: 40px; height: 36px; border: 1px solid ${C.line}; background: ${C.ground}; border-radius: 0;
      display: grid; place-items: center; cursor: pointer; z-index: 2; color: ${C.ink}; padding: 0; margin: 0; }
    .cap { position: absolute; left: 50%; bottom: 15px; transform: translateX(-50%); white-space: nowrap; pointer-events: none; }
    .note { position: absolute; left: 8px; right: 8px; bottom: 8px; z-index: 4; box-sizing: border-box; background: ${C.raised}; border: 1px solid ${C.red}; padding: 12px 14px; }
    .note .row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
    .note .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; box-sizing: border-box; flex: none; background: ${C.red}; border: 1px solid ${C.red}; }
    .note .t { font: 400 15px/1.3 ${SANS}; color: ${C.ink}; }
    .note .n { font: 400 13px/1.45 ${SANS}; color: ${C.text}; margin-top: 6px; }
    .note .m { font: 400 11px/1.5 ${MONO}; color: ${C.muted}; margin-top: 10px; }
    .note .m b { color: ${C.ink}; font-weight: 500; }
    .note.sent { border-color: ${C.line}; }
    .wait { position: absolute; inset: 0; display: grid; place-items: center; }
  `;

  class RtHouseCard extends HTMLElement {
    static getStubConfig() { return { mode: "health" }; }
    setConfig(c) {
      this._c = Object.assign({ mode: "health", base: "/local/redtower-ui/", max_height: null, fit: false, fit_reserve: null, fill: null, scale: null,
        exclude: ["CGM4331", "Xfinity", "Spotify"], alarm_entity: "binary_sensor.red_tower_alarm",
        panel: "alarm_control_panel.redalert", shield: "input_boolean.red_shield",
        security_objects: { "binary_sensor.backyard_window": "window_guest_room", "binary_sensor.third_reality_inc_3rds17bz": "door_balcony" },
        device_anchor: { "vacuum.asimov": "asimov" }, claude_project: "019dd1de-a045-742b-8952-e7b9cad9eded", siren_entity: "binary_sensor.indoor_siren_6_siren_active_2",
        names: { "binary_sensor.third_reality_inc_3rds17bz": "Balcony window", "binary_sensor.backyard_window": "Backyard window" },
        rename: { "Red sentry IN": "Red Sentry IN", "Jalapenos 2": "Jalapeños 2", "Jalapenos 3": "Jalapeños 3" } }, c || {});
      this._v = null; this._pop = ""; this._sig = "";
      this.setAttribute("data-mode", this._c.mode === "alarm" ? "alarm" : "health");
    }
    getCardSize() { return 9; }
    getGridOptions() { return { columns: "full" }; }
    set hass(h) { this._h = h; this._update(); }
    connectedCallback() {
      if (!this.shadowRoot) {
        const r = this.attachShadow({ mode: "open" });
        r.innerHTML = `<style>${CSS}</style><ha-card class="${this._c && this._c.mode === "alarm" ? "alarm" : "health"}"><div class="head"></div><div class="stage"><div class="wait lab">Drawing the house</div></div></ha-card>`;
        const st = r.querySelector(".stage");
        let g = null;
        st.addEventListener("pointerdown", e => { if (e.target.closest("button")) return; g = { x: e.clientX }; });
        st.addEventListener("pointermove", e => { if (!g) return; const dx = e.clientX - g.x; if (Math.abs(dx) >= 36) { g.x = e.clientX; this._turn(dx > 0 ? -1 : 1); } });
        const up = () => { g = null; };
        st.addEventListener("pointerup", up); st.addEventListener("pointerleave", up); st.addEventListener("pointercancel", up);
      }
      // Home Assistant moves cards around while it builds a view: watch the width again on every connection
      if (!this._ro) {
        const st = this.shadowRoot.querySelector(".stage");
        this._ro = new ResizeObserver(() => { const w = Math.round(st.clientWidth); if (w && w !== this._w) { this._w = w; this._draw(true); } });
        this._ro.observe(st);
      }
      if (!this._onWin) {
        this._onWin = () => { if (!this._c || !(this._c.fit || Number(this._c.fill) > 0)) return; const hh = window.innerHeight; if (hh !== this._wh) { this._wh = hh; this._draw(true); } };
        this._wh = window.innerHeight; window.addEventListener("resize", this._onWin);
      }
      this._update();
    }
    disconnectedCallback() { if (this._ro) { this._ro.disconnect(); this._ro = null; } if (this._onWin) { window.removeEventListener("resize", this._onWin); this._onWin = null; } }
    _chatTitle(it) { return `(INT) ${it.name} ${String(it.state).toLowerCase()}`; }
    _claude(id) {
      const it = (this._items_ || []).find(i => i.id === id);
      if (!it) return;
      const text = `${this._chatTitle(it)}\n\n${it.where}. ${it.title}. ${it.note}\n\n`;
      const url = `https://claude.ai/new?q=${encodeURIComponent(text)}&project=${encodeURIComponent(this._c.claude_project)}`;
      this._sent = { id, at: Date.now() }; this._pop = ""; this._draw(true);
      clearTimeout(this._sentT);
      this._sentT = setTimeout(() => { this._sent = null; this._draw(true); }, 4000);
      try { if (navigator.vibrate) navigator.vibrate(30); } catch (_) {}
      window.open(url, "_blank", "noopener");
    }
    _turn(d) { this._v = (((this._view() + d) % 8) + 8) % 8; this._pop = ""; this._manual = this._items().map(i => i.id).join(","); this._draw(true); }
    _view() {
      if (this._v !== null) return this._v;
      return 0;
    }

    // what to draw: devices Home Assistant can't reach (health) or the alarms (alarm)
    _items() {
      const h = this._h; if (!h) return [];
      return this._c.mode === "alarm" ? this._alarms(h) : this._issues(h);
    }
    _issues(h) {
      const ents = h.entities || {}, devs = h.devices || {}, areas = h.areas || {}, floors = h.floors || {};
      const byDev = {};
      for (const [eid, e] of Object.entries(ents)) {
        if (!e || !e.device_id || !h.states[eid]) continue;
        (byDev[e.device_id] = byDev[e.device_id] || []).push(eid);
      }
      const ex = (this._c.exclude || []).map(x => String(x).toLowerCase());
      const byArea = {};
      for (const [did, list] of Object.entries(byDev)) {
        const d = devs[did]; if (!d) continue;
        const name0 = d.name_by_user || d.name || "", name = (this._c.rename || {})[name0] || name0;
        if (ex.some(x => name.toLowerCase().includes(x) || (d.model || "").toLowerCase().includes(x))) continue;
        const sts = list.map(e => h.states[e]);
        if (!sts.every(s => s.state === "unavailable")) continue;
        const aid = d.area_id || (ents[list[0]] && ents[list[0]].area_id);
        const area = areas[aid], fl = area && floors[area.floor_id];
        const lvl = fl && fl.level;
        if (![1, 2, 3].includes(lvl)) continue;
        const since = sts.map(s => s.last_changed).sort()[0];
        const anchor = Object.entries(this._c.device_anchor || {}).find(([e]) => list.includes(e));
        (byArea[aid] = byArea[aid] || []).push({ did, name, lvl, aid, areaName: area.name, since, anchor: anchor && anchor[1] });
      }
      const out = [];
      for (const [aid, group] of Object.entries(byArea)) {
        const own = group.filter(x => x.anchor), rest = group.filter(x => !x.anchor);
        const x0 = group[0], area = (x0.areaName || "").toLowerCase(), placed = !!AREA_ROOM[aid];
        const where = `${FLOOR_NAME[x0.lvl]} · ${placed ? area : "not placed in the model yet"}`;
        for (const x of own) out.push({ id: x.did, name: x.name, state: "Unavailable", lvl: x.lvl, anchor: x.anchor, area: aid,
          where: `${FLOOR_NAME[x.lvl]} · ${area}`, title: `${x.name} is unavailable`, note: `Home Assistant hasn't reached it since ${when(x.since)}.` });
        if (!rest.length) continue;
        const since = when(rest.map(r => r.since).sort()[0]);
        const unplaced = placed ? "" : ` ${x0.areaName} isn't placed in the model yet, so it shows on its floor.`;
        if (rest.length === 1 && placed) {
          const x = rest[0];
          out.push({ id: x.did, name: x.name, state: "Unavailable", lvl: x.lvl, area: aid, where,
            title: `${x.name} is unavailable`, note: `Home Assistant hasn't reached it since ${since}.` });
        } else {
          out.push({ id: "area-" + aid, name: x0.areaName, state: "Offline", lvl: x0.lvl, area: aid, where,
            title: `The ${area} is offline`, note: `${rest.length > 1 ? "Its devices" : "Its device"} (${list(rest.map(r => r.name).sort())}) stopped reporting; Home Assistant hasn't reached ${rest.length > 1 ? "them" : "it"} since ${since}.${unplaced}` });
        }
      }
      return out.sort((a, b) => b.lvl - a.lvl || a.name.localeCompare(b.name));
    }
    _alarms(h) {
      const s = h.states[this._c.alarm_entity];
      const list = (s && s.state === "on" && Array.isArray(s.attributes.entities)) ? s.attributes.entities : [];
      const ents = h.entities || {}, devs = h.devices || {}, areas = h.areas || {}, floors = h.floors || {};
      const armed = (h.states[this._c.shield] || {}).state === "on";
      const siren = (h.states[this._c.siren_entity] || {}).state === "on";
      const first = list.find(e => h.states[e]);
      const firstName = first && ((this._c.names || {})[first] || h.states[first].attributes.friendly_name || first);
      return list.filter(e => h.states[e]).map((eid, i) => {
        const st = h.states[eid], e = ents[eid] || {}, d = devs[e.device_id] || {};
        const aid = e.area_id || d.area_id, area = areas[aid] || {}, fl = floors[area.floor_id] || {};
        const dc = st.attributes.device_class || "", kind = eid.startsWith("alarm_control_panel.") ? "Triggered" : (KIND[dc] || "Alarm");
        const name = (this._c.names || {})[eid] || st.attributes.friendly_name || eid;
        const t = time(st.last_changed);
        const note = i === 0
          ? `At ${t}${armed ? ", while Red Shield was on" : ""}.${siren ? " The siren is sounding." : ""}`
          : `At ${t}, ${ago(h.states[first].last_changed, st.last_changed)} after the ${String(firstName).toLowerCase()}.`;
        return { id: eid, name, state: `${kind} · ${t}`, opening: this._c.security_objects[eid], room: AREA_ROOM[aid], area: aid,
          lvl: fl.level, where: [FLOOR_NAME[fl.level], (area.name || "").toLowerCase()].filter(Boolean).join(" · ") || "Place not known",
          title: kind === "Open" ? `The ${name.toLowerCase()} opened` : `${name}: ${kind.toLowerCase()}`, note, first: i === 0 };
      });
    }
    _update() {
      if (!this._h || !this.shadowRoot || !this._c) return;
      const items = this._items();
      const extra = this._c.mode === "alarm" ? ((this._h.states[this._c.panel] || {}).state || "") : "";
      const sig = JSON.stringify(items.map(i => [i.id, i.state, i.lvl])) + extra;
      if (sig === this._sig) return;
      this._sig = sig; this._items_ = items;
      if (this._c.mode === "alarm" && items.length && this._manual !== items.map(i => i.id).join(",")) {
        const a = items[0]; this._v = OPEN_VIEW[a.opening] ?? ROOM_VIEW[a.room] ?? 0;
      }
      if (!items.find(i => i.id === this._pop)) this._pop = "";
      this._draw(false);
    }

    async _draw(force) {
      const r = this.shadowRoot; if (!r || !this._c || !this._h) return;
      const card = r.querySelector("ha-card"); card.className = this._c.mode === "alarm" ? "alarm" : "health";
      const W = this._w || Math.round(r.querySelector(".stage").clientWidth);
      if (!W) return;                                   // not laid out yet: the ResizeObserver draws it
      const base = this._c.base, k = this._view(), seq = (this._seq = (this._seq || 0) + 1);
      let lay, svg;
      try { [lay, svg] = await Promise.all([fetchOnce(base + "axo-layout.json?v=" + VERSION, "json"), fetchOnce(base + `axo-v${k}.svg?v=${VERSION}`, "text")]); }
      catch (e) { r.querySelector(".stage").innerHTML = `<div class="wait lab">The drawing didn't load (${esc(e.message)})</div>`; return; }
      if (seq !== this._seq) return;
      for (let j = 1; j <= 2; j++) fetchOnce(base + `axo-v${(k + j) % 8}.svg?v=${VERSION}`, "text").catch(() => {});
      const items = this._items_ || [], view = lay.views[k], [CW, CH] = lay.crop;
      // fit (Home and RedSec, Vittorio's note, Nov 24: "now too big"): as big as the first screen allows, the whole house
      // and the turn arrows in view without scrolling; on a phone the width decides. scale: that share of the card's width;
      // fill: that share of the screen's height. Every way, the building is centred in the card.
      const fit = !!this._c.fit, fill = Number(this._c.fill) || 0, scale = Number(this._c.scale) || 0, natural = Math.round(W * CH / CW), ctl = 44;
      const room = Math.max(280, window.innerHeight - (Number(this._c.fit_reserve) || 214) - ctl);
      const drawH = fit ? Math.min(natural, room)
        : scale && W >= 600 ? Math.round(natural * scale)
        : fill ? Math.min(natural, Math.max(260, Math.round(window.innerHeight * fill)))
        : Math.min(this._c.max_height || (W < 600 ? 400 : 430), natural), H = drawH + ctl;
      const s = Math.min(W / CW, drawH / CH);
      let ox = (W - CW * s) / 2, oy = (drawH - CH * s) / 2;
      if ((fit || fill || scale) && view.bbox) { const [b0, b1, b2, b3] = view.bbox; ox = W / 2 - s * (b0 + b2) / 2; oy = drawH / 2 - s * (b1 + b3) / 2; }
      const alarm = this._c.mode === "alarm";
      // head
      let left, right;
      if (alarm) {
        const p = (this._h.states[this._c.panel] || {}).state || "";
        left = items.length ? `<span class="lab red">Alarm · started ${esc(items[0].state.split("· ").pop())}</span>` : `<span class="lab green">No alarm</span>`;
        right = items.length ? `<span class="lab red">${items.length} open</span>` : `<span class="lab">${esc(p.replace(/_/g, " ").replace(/^./, c => c.toUpperCase()))}</span>`;
      } else {
        left = items.length ? `<span class="lab red">${items.length} not nominal</span>` : `<span class="lab green">Everything nominal</span>`;
        right = `<span class="lab">Lines from the 3D model</span>`;
      }
      r.querySelector(".head").innerHTML = left + right;
      // overlays
      const g = [];
      const redFloors = alarm ? [] : [...new Set(items.map(i => i.lvl))];
      if (alarm && items.length) {
        for (const a of items) { const b = view.boxes[a.room]; if (b) g.push(`<path d="${loopsD(b.fill, s, ox, oy)}" fill="${C.red}" fill-opacity=".2"/><path d="${segsD(b.edges, s, ox, oy)}" stroke="${C.red}" stroke-opacity=".6" stroke-width="1" fill="none"/>`); }
        for (const a of items) { const o = view.openings[a.opening]; if (o) g.push(`<path d="${segsD(o.hidden, s, ox, oy)}" stroke="${C.red}" stroke-width="1.4" stroke-dasharray="3 3" fill="none"/><path d="${segsD(o.seen, s, ox, oy)}" stroke="${C.red}" stroke-width="2.2" fill="none"/>`); }
      } else if (!alarm && items.length) {
        for (const f of redFloors) g.push(`<path d="${loopsD(view.floors[String(f)], s, ox, oy)}" stroke="${C.red}" stroke-width="1.8" stroke-linejoin="round" fill="none"/>`);
      } else {
        g.push(`<path d="${loopsD(view.floors.all, s, ox, oy)}" stroke="${C.green}" stroke-width="1.8" stroke-linejoin="round" fill="none"/>`);
      }
      // labels with leaders
      const [bx0, , bx1] = view.bbox.map(v => v * s);
      const mid = ox + (bx0 + bx1) / 2, sides = { l: [], r: [] };
      for (const it of items) {
        let a = null;
        if (alarm) { const o = view.openings[it.opening], b = view.boxes[it.room]; a = (o && o.anchor) || (b && b.anchor); }
        else { a = (it.anchor && view.anchors[it.anchor]) || view.anchors[AREA_ROOM[it.area]] || centroid(view.floors[String(it.lvl)]); }
        if (!a) a = view.anchors.asimov || [CW / 2, CH / 2];
        const ax = a[0] * s + ox, ay = a[1] * s + oy;
        sides[ax <= mid ? "l" : "r"].push([ay, ax, it]);
      }
      const chips = [];
      for (const [side, list] of Object.entries(sides)) {
        list.sort((p, q) => p[0] - q[0]);
        let prev = -1e9;
        for (const [ay, ax, it] of list) {
          const cw = Math.round(Math.max(it.name.length, it.state.length) * 7.0 + 22), ch = 38;
          let y = Math.max(6, ay - ch / 2, prev + ch + 8); y = Math.min(y, H - ctl - ch - 4); prev = y;
          const x = side === "l" ? Math.max(6, ox + bx0 - cw - 18) : Math.min(W - 6 - cw, ox + bx1 + 18);
          const lx = side === "l" ? x + cw : x;
          g.push(`<line x1="${lx.toFixed(1)}" y1="${(y + ch / 2).toFixed(1)}" x2="${ax.toFixed(1)}" y2="${ay.toFixed(1)}" stroke="${C.red}" stroke-width="1"/><circle cx="${ax.toFixed(1)}" cy="${ay.toFixed(1)}" r="3.2" fill="${C.red}"/>`);
          chips.push(`<button class="chip" data-id="${esc(it.id)}" aria-label="${esc(it.name)}, ${esc(it.state)}. Tap for the note" style="left:${x.toFixed(0)}px;top:${y.toFixed(0)}px;width:${cw.toFixed(0)}px;height:${ch}px"><span>${esc(it.name)}</span><span>${esc(it.state)}</span></button>`);
        }
      }
      const pop = items.find(i => i.id === this._pop);
      const sent = this._sent && items.find(i => i.id === this._sent.id);
      const note = sent ? `<div class="note sent" role="status"><div class="lab" style="color:${C.ink}">Opening Claude</div><div class="m" style="margin-top:6px">RedTower · <b>${esc(this._chatTitle(sent))}</b></div><div class="m" style="margin-top:4px">Say the note with Claude's microphone, then send</div></div>`
        : pop ? `<div class="note" role="status"><div class="lab">${esc(pop.where)}</div><div class="row"><span class="dot" aria-hidden="true"></span><span class="t">${esc(pop.title)}</span></div><div class="n">${esc(pop.note)}</div><div class="m">${alarm ? "Tap the label again to close" : "Tap the label again to close · hold it to tell Claude, filed as (INT)"}</div></div>` : "";
      const arrow = d => `<svg width="14" height="14" viewBox="0 0 18 18" aria-hidden="true" style="transform: rotate(${d === "l" ? 270 : 90}deg)"><path d="M9 16 V2 M3.5 7.5 L9 2 L14.5 7.5" stroke="currentColor" stroke-width="1" fill="none"/></svg>`;
      const stage = r.querySelector(".stage");
      stage.style.height = H + "px";
      stage.className = "stage " + redFloors.map(f => "r" + f).join(" ");
      stage.innerHTML =
        `<div class="draw" style="left:${ox.toFixed(1)}px;top:${oy.toFixed(1)}px;width:${(CW * s).toFixed(1)}px;height:${(CH * s).toFixed(1)}px">${svg}</div>` +
        `<svg class="over" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${g.join("")}</svg>` + chips.join("") +
        `<button class="turn" data-turn="-1" aria-label="Turn left" style="left:4px">${arrow("l")}</button>` +
        `<button class="turn" data-turn="1" aria-label="Turn right" style="right:4px">${arrow("r")}</button>` +
        `<div class="cap lab">From the ${FROM[k]} · drag to turn</div>` + note;
      stage.querySelectorAll("button.turn").forEach(b => b.addEventListener("click", ev => { ev.stopPropagation(); this._turn(+b.dataset.turn); }));
      stage.querySelectorAll("button.chip").forEach(b => {
        const hold = !alarm;
        if (hold) {
          b.addEventListener("pointerdown", ev => { ev.stopPropagation(); clearTimeout(this._holdT); this._held = false;
            this._holdT = setTimeout(() => { this._held = true; this._claude(b.dataset.id); }, 550); });
          const cancel = () => clearTimeout(this._holdT);
          b.addEventListener("pointerup", cancel); b.addEventListener("pointerleave", cancel); b.addEventListener("pointercancel", cancel);
          b.addEventListener("contextmenu", ev => ev.preventDefault());
        }
        b.addEventListener("click", ev => { ev.stopPropagation(); if (this._held) { this._held = false; return; }
          this._pop = this._pop === b.dataset.id ? "" : b.dataset.id; this._sent = null; this._draw(true); });
      });
    }
  }
  if (!customElements.get("rt-house-card")) customElements.define("rt-house-card", RtHouseCard);
  window.customCards = window.customCards || [];
  if (!window.customCards.find(c => c.type === "rt-house-card"))
    window.customCards.push({ type: "rt-house-card", name: "Red Tower in lines", description: "The house from the 3D model, in lines: what is not nominal, or the alarms, in red." });
  console.info(`%c redtower-ui ${VERSION} `, "background:#ED1C24;color:#fff");
})();
