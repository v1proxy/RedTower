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
/* Red Tower UI, part 2: the cards drawn in the round 6 design that Home Assistant has no card for.
 * rt-thermostat-card  the dial: red while heating, blue while cooling, both for Heat/Cool; minus and plus inside it, the four modes
 * rt-line-card        a chart from the history: 1 px lines, the first one's figure in red, the now dot
 * rt-weather-card     Weather: the forecast (today or the week) and the temperatures (last 24 h or 7 days)
 * rt-energy-card      Electricity: now, today, this month, the Polestar; the last 24 hours; where it goes; the loads
 * rt-io-card          In and out: what comes in and what goes out, as two treemaps either side of the house
 * rt-claude-card      Claude by room: what Claude uses of the machines that stay in a room
 * rt-camera-card      a camera, or why it can't show
 * rt-logbook-card     what happened, newest first
 * rt-remote-card      the TV remote
 */
(() => {
  const C = { ground: "#000000", raised: "#111113", rule: "#2A2C30", line: "#45474D", strong: "#C9CBCF", ink: "#F3F1EC",
    text: "#C9CBCF", muted: "#8E9096", red: "#ED1C24", redText: "#F4454B", green: "#7FD18B", cool: "#4FB0FF", amber: "#F0B454",
    tile: ["#141518", "#1B1C20", "#222328", "#2A2B31"] };
  const SANS = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif";
  const MONO = "'IBM Plex Mono', 'SFMono-Regular', Menlo, monospace";
  const HATCH = "repeating-linear-gradient(135deg, rgba(142,144,150,.30) 0 1px, transparent 1px 6px)";
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const num = s => (s && s.state !== "unavailable" && s.state !== "unknown" && s.state !== "" && isFinite(Number(s.state)) ? Number(s.state) : null);
  const fix = (v, d) => (v == null || !isFinite(v) ? "--" : Number(v).toFixed(d));
  const time = d => (d instanceof Date ? d : new Date(d)).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  const hourName = d => (d instanceof Date ? d : new Date(d)).toLocaleTimeString("en-US", { hour: "numeric" });
  const fmtE = (h, s) => { try { return h.formatEntityState(s); } catch (_) { return s.state; } };
  const cap = s => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");
  const COND = { "clear-night": "Clear", cloudy: "Cloudy", exceptional: "Exceptional", fog: "Fog", hail: "Hail", lightning: "Lightning",
    "lightning-rainy": "Thunderstorms", partlycloudy: "Partly cloudy", pouring: "Heavy rain", rainy: "Rain", snowy: "Snow",
    "snowy-rainy": "Sleet", sunny: "Sunny", windy: "Windy", "windy-variant": "Windy" };
  const compass = b => ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][Math.round(((Number(b) || 0) % 360) / 45) % 8];

  // ---- the kit: the same pieces as the canvas (kit.py) ---------------------------------------------------------------
  const KIT = `
    :host { display: block; contain: inline-size; min-width: 0; }
    * { box-sizing: border-box; }
    .lab { font: 400 11px/1.45 ${MONO}; letter-spacing: .1em; text-transform: uppercase; color: ${C.muted}; }
    .meta { font: 400 11px/1.5 ${MONO}; color: ${C.muted}; font-variant-numeric: tabular-nums; }
    .meta b { color: ${C.ink}; font-weight: 500; }
    .panel { position: relative; background: ${C.raised}; border: 1px solid ${C.rule}; padding: 14px 16px; }
    .title { font: 400 15px/1.3 ${SANS}; color: ${C.ink}; }
    .head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 22px 0 8px; min-height: 16px; }
    .head.first { margin-top: 0; }
    .seg { display: flex; }
    .seg button { flex: 1 1 0; min-width: 0; height: 36px; padding: 0 10px; border: 1px solid ${C.line}; margin: 0 0 0 -1px; position: relative;
      font: 400 13px/1 ${SANS}; color: ${C.muted}; background: ${C.ground}; cursor: pointer; white-space: nowrap; border-radius: 0; }
    .seg button:first-child { margin-left: 0; }
    .seg button[aria-pressed=true] { border-color: ${C.ink}; color: ${C.ink}; z-index: 1; }
    .btn { display: inline-flex; align-items: center; justify-content: center; height: 44px; padding: 0 14px; font: 400 14px/1 ${SANS};
      border-radius: 0; border: 1px solid ${C.line}; background: ${C.ground}; color: ${C.ink}; cursor: pointer; white-space: nowrap; margin: 0; }
    .btn.on { border-color: ${C.red}; color: ${C.redText}; background: transparent; }
    .btn:disabled { opacity: .45; cursor: default; }
    .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex: none; border: 1px solid ${C.muted}; }
    .dot.on { background: ${C.ink}; border-color: ${C.ink}; } .dot.alarm { background: ${C.red}; border-color: ${C.red}; }
    .dot.none { border-style: dashed; } .dot.warn { background: ${C.amber}; border-color: ${C.amber}; }
    .rows { border-top: 1px solid ${C.strong}; }
    .row { display: flex; align-items: center; gap: 10px; min-height: 56px; padding: 8px 0; border-bottom: 1px solid ${C.rule}; }
    .row .k { width: 84px; flex: none; padding-top: 2px; }
    .row .v { flex: 1 1 0; min-width: 0; display: grid; gap: 2px; }
    .row .vv { display: flex; align-items: center; gap: 8px; font: 400 15px/1.3 ${SANS}; color: ${C.ink}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .fig { font: 300 34px/1 ${SANS}; color: ${C.ink}; letter-spacing: -.01em; white-space: nowrap; }
    .fig .u { font-size: 15px; color: ${C.muted}; margin-left: 4px; letter-spacing: 0; }
    svg { display: block; overflow: visible; }
    .wait { padding: 18px 0; }
  `;

  class RtCard extends HTMLElement {
    setConfig(c) { this._c = Object.assign({}, this.defaults ? this.defaults() : {}, c || {}); this._sig = ""; this._schedule(); }
    set hass(h) {
      const first = !this._h; this._h = h;
      const ids = this.watch ? this.watch() : null;
      if (ids) {
        const sig = ids.map(e => { const s = h.states[e]; return s ? s.state + "|" + s.last_updated : "-"; }).join(",");
        if (!first && sig === this._sig) return;
        this._sig = sig;
      }
      this._schedule();
    }
    get hass() { return this._h; }
    connectedCallback() {
      if (!this.shadowRoot) {
        this.attachShadow({ mode: "open" });
        this.shadowRoot.innerHTML = `<style>${KIT}${this.css ? this.css() : ""}</style><div class="root"></div>`;
        this.shadowRoot.addEventListener("click", e => {
          const t = e.target.closest("[data-act]"); if (!t || !this.act) return;
          e.stopPropagation(); this.act(t.dataset.act, t.dataset.arg, t, e);
        });
      }
      if (!this._ro) {
        this._ro = new ResizeObserver(() => { const w = Math.round(this.clientWidth); if (w && w !== this._w) { this._w = w; this._schedule(); } });
        this._ro.observe(this);
      }
      if (this.attached) this.attached();
      this._schedule();
    }
    disconnectedCallback() { if (this._ro) { this._ro.disconnect(); this._ro = null; } if (this.detached) this.detached(); }
    _schedule() {
      if (this._pending) return;
      this._pending = true;
      Promise.resolve().then(() => {
        this._pending = false;
        if (!this._h || !this.shadowRoot || !this._c) return;
        if (!this._w) this._w = Math.round(this.clientWidth) || 0;
        if (!this._w) return;                                  // laid out later: the ResizeObserver comes back
        const html = this.render();
        if (html != null) this.shadowRoot.querySelector(".root").innerHTML = html;
        if (this.painted) this.painted();
      });
    }
    getCardSize() { return 4; }
    getGridOptions() { return { columns: "full" }; }
    call(domain, service, data) { return this._h.callService(domain, service, data); }
    nav(path) { history.pushState(null, "", path); window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } })); }
  }

  // ---- data: history and statistics, kept a few minutes ---------------------------------------------------------------
  const cache = new Map();
  function remember(key, ttl, make) {
    const hit = cache.get(key);
    if (hit && Date.now() - hit.t < ttl) return hit.p;
    const p = make();
    cache.set(key, { t: Date.now(), p });
    p.catch(() => cache.delete(key));
    return p;
  }
  function historyOf(h, ids, hours, attr) {
    const key = "h|" + ids.join(",") + "|" + hours + "|" + (attr || "");
    return remember(key, 4 * 60e3, () => {
      const end = new Date(), start = new Date(end - hours * 3600e3);
      return h.callWS({ type: "history/history_during_period", start_time: start.toISOString(), end_time: end.toISOString(), entity_ids: ids,
        minimal_response: !attr, no_attributes: !attr, significant_changes_only: false }).then(res => {
        const out = {};
        for (const id of ids) out[id] = (res[id] || []).map(x => ({ t: (x.lu || x.lc || 0) * 1000,
          v: attr ? Number(x.a && x.a[attr]) : Number(x.s) })).filter(p => isFinite(p.v) && p.t);
        return { start: +start, end: +end, data: out };
      });
    });
  }
  function statsOf(h, ids, days, period, types) {
    const key = "s|" + ids.join(",") + "|" + days + "|" + period + "|" + types.join(",");
    return remember(key, 10 * 60e3, () => {
      const end = new Date(), start = new Date(end - days * 86400e3);
      return h.callWS({ type: "recorder/statistics_during_period", start_time: start.toISOString(), end_time: end.toISOString(),
        statistic_ids: ids, period, types }).then(res => ({ start: +start, end: +end, data: res }));
    });
  }
  // A step function averaged into n equal buckets from t0 to t1 (null where nothing is known yet).
  function buckets(points, t0, t1, n) {
    const out = new Array(n).fill(null), dt = (t1 - t0) / n;
    let i = 0, cur = null;
    while (i < points.length && points[i].t <= t0) { cur = points[i].v; i++; }
    for (let b = 0; b < n; b++) {
      const bs = t0 + b * dt, be = bs + dt;
      let acc = 0, w = 0, t = bs;
      while (i < points.length && points[i].t < be) {
        if (cur != null) { acc += cur * (points[i].t - t); w += points[i].t - t; }
        cur = points[i].v; t = points[i].t; i++;
      }
      if (cur != null) { acc += cur * (be - t); w += be - t; }
      out[b] = w > 0 ? acc / w : null;
    }
    return out;
  }
  const niceStep = span => { const raw = span / 3, p = Math.pow(10, Math.floor(Math.log10(raw || 1))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; };
  function ticks(lo, hi, zero) {
    if (zero) lo = Math.min(0, lo);
    if (!(hi > lo)) hi = lo + 1;
    const st = niceStep(hi - lo), a = Math.floor(lo / st) * st, b = Math.ceil(hi / st) * st, out = [];
    for (let v = a; v <= b + st / 2; v += st) out.push(+v.toFixed(6));
    return out;
  }
  const tickText = v => (Math.abs(v) >= 1000 ? String(Math.round(v)) : String(+v.toFixed(2)));

  // ---- the chart: 1 px lines, no fill, mono labels (kit.line_chart and v2.multi_chart) --------------------------------
  // series: { vals: [...] spread evenly over the width, or pts: [[fraction, value], ...], color, width, dash }
  function chart({ w, h, series, ymin, ymax, yt, xl = [], vl = [], now = null, padL = 34, padB = 22, aria = "Chart" }) {
    const iw = w - padL, ih = h - padB;
    const Y = v => ih - (v - ymin) / (ymax - ymin || 1) * (ih - 6) + 3;
    const X = f => padL + f * iw;
    const g = [];
    for (const v of yt || []) {
      const y = Y(v);
      g.push(`<line x1="${padL}" y1="${y.toFixed(1)}" x2="${w}" y2="${y.toFixed(1)}" stroke="${C.rule}" stroke-width="1"/>`
        + `<text x="0" y="${(y + 4).toFixed(1)}" fill="${C.muted}" font-family="IBM Plex Mono, monospace" font-size="10">${esc(tickText(v))}</text>`);
    }
    for (const f of vl) g.push(`<line x1="${X(f).toFixed(1)}" y1="0" x2="${X(f).toFixed(1)}" y2="${ih}" stroke="${C.rule}" stroke-width="1"/>`);
    for (const s of series) {
      const pts = s.pts || (s.vals || []).map((v, i, a) => [a.length > 1 ? i / (a.length - 1) : 0, v]);
      let seg = [];
      const flush = () => { if (seg.length > 1) g.push(`<polyline points="${seg.join(" ")}" fill="none" stroke="${s.color}" stroke-width="${s.width || 1}"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""} stroke-linejoin="round"/>`); seg = []; };
      for (const [f, v] of pts) { if (v == null || !isFinite(v)) { flush(); continue; } seg.push(`${X(f).toFixed(1)},${Y(Math.max(ymin, Math.min(ymax, v))).toFixed(1)}`); }
      flush();
    }
    if (now && now[1] != null && isFinite(now[1])) g.push(`<circle cx="${X(now[0]).toFixed(1)}" cy="${Y(now[1]).toFixed(1)}" r="3.5" fill="${C.red}"/>`);
    for (const [f, t] of xl) {
      const anchor = f < 0.03 ? "start" : f > 0.97 ? "end" : "middle";
      g.push(`<text x="${X(f).toFixed(1)}" y="${h - 4}" text-anchor="${anchor}" fill="${C.muted}" font-family="IBM Plex Mono, monospace" font-size="10">${esc(t)}</text>`);
    }
    return `<svg role="img" aria-label="${esc(aria)}" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${g.join("")}</svg>`;
  }
  // Labels on round hours between t0 and t1, the right end named "Now" or by its time.
  function hourLabels(t0, t1, every, endText) {
    const out = [], span = t1 - t0, d = new Date(t0);
    d.setMinutes(0, 0, 0);
    while (+d <= t0) d.setHours(d.getHours() + 1);
    while (d.getHours() % every) d.setHours(d.getHours() + 1);
    for (; +d < t1 - span * 0.08; d.setHours(d.getHours() + every)) {
      const f = (+d - t0) / span;
      if (f < 0.06) continue;
      const day = every >= 12 && d.getHours() === 0 ? d.toLocaleDateString("en-US", { weekday: "short" }) : hourName(d);
      out.push([f, day]);
    }
    out.unshift([0, every >= 12 ? new Date(t0).toLocaleDateString("en-US", { weekday: "short" }) + " " + hourName(t0) : hourName(t0)]);
    out.push([1, endText || time(t1)]);
    return out;
  }
  const sample = (color, width = 1, dash) => `<svg aria-hidden="true" width="18" height="6" viewBox="0 0 18 6" style="flex:none"><line x1="0" y1="3" x2="18" y2="3" stroke="${color}" stroke-width="${width}"${dash ? ` stroke-dasharray="${dash}"` : ""}/></svg>`;

  // ---- squarified treemap ---------------------------------------------------------------------------------------------
  function squarify(items, x, y, w, h) {
    const out = {};
    const total = items.reduce((a, b) => a + b[1], 0) || 1;
    let rest = items.map(([n, v]) => [n, v * w * h / total]).sort((a, b) => b[1] - a[1]);
    const worst = (row, side) => { const s = row.reduce((a, b) => a + b[1], 0); const mx = Math.max(...row.map(r => r[1])), mn = Math.min(...row.map(r => r[1]));
      return Math.max(side * side * mx / (s * s), (s * s) / (side * side * mn)); };
    while (rest.length) {
      const side = Math.min(w, h);
      let row = [rest[0]], i = 1;
      while (i < rest.length && worst(row.concat([rest[i]]), side) <= worst(row, side)) { row.push(rest[i]); i++; }
      rest = rest.slice(i);
      const s = row.reduce((a, b) => a + b[1], 0);
      if (w >= h) { const cw = s / h; let cy = y; for (const [n, a] of row) { const ch = a / cw; out[n] = [x, cy, cw, ch]; cy += ch; } x += cw; w -= cw; }
      else { const ch = s / w; let cx = x; for (const [n, a] of row) { const cw = a / ch; out[n] = [cx, y, cw, ch]; cx += cw; } y += ch; h -= ch; }
    }
    return out;
  }
  const cornerTicks = (color, size = 12) => ["top:0;left:0;border-top", "top:0;right:0;border-top", "bottom:0;left:0;border-bottom", "bottom:0;right:0;border-bottom"]
    .map((p, i) => `<span aria-hidden="true" style="position:absolute;${p.split(";").slice(0, 2).join(";")};width:${size}px;height:${size}px;${p.split(";")[2]}:1px solid ${color};border-${i % 2 ? "right" : "left"}:1px solid ${color}"></span>`).join("");

  // ====================================================================================================================
  // rt-thermostat-card
  // ====================================================================================================================
  const MODE_NAMES = { off: "Off", heat: "Heat", cool: "Cool", heat_cool: "Heat/Cool", auto: "Auto", dry: "Dry", fan_only: "Fan" };
  class RtThermostat extends RtCard {
    defaults() { return { entity: null, size: null }; }
    watch() { return [this._c.entity]; }
    // Vittorio's note, Nov 24: a bigger wheel and smaller buttons, in the original relation (Home Assistant's own card:
    // the dial fills the card, minus and plus sit inside it under the figure, the modes are a slim row no wider than the dial).
    css() { return `
      .tw { position: relative; margin: 0 auto; }
      .tw svg { display: block; }
      .pm { position: absolute; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; }
      .sbtn { width: 34px; height: 34px; padding: 0; display: inline-flex; align-items: center; justify-content: center; border: 1px solid ${C.line};
        background: ${C.ground}; color: ${C.ink}; font: 300 20px/1 ${SANS}; border-radius: 0; cursor: pointer; margin: 0; }
      .sbtn:hover, .sbtn:focus-visible { border-color: ${C.strong}; }
      .dual { display: flex; gap: 18px; justify-content: center; flex-wrap: wrap; margin-top: 6px; }
      .grp { display: flex; align-items: center; gap: 6px; }
      .seg.slim { margin: 0 auto; }
      .seg.slim button { height: 30px; font-size: 12px; padding: 0 6px; }
    `; }
    _target(s) {
      const a = s.attributes, p = this._pend && Date.now() - this._pend.at < 8000 ? this._pend : {};
      return { t: p.t ?? a.temperature, lo: p.lo ?? a.target_temp_low, hi: p.hi ?? a.target_temp_high };
    }
    render() {
      const s = this._h.states[this._c.entity];
      if (!s) return `<div class="panel"><div class="meta">${esc(this._c.entity)} isn't in Home Assistant</div></div>`;
      const a = s.attributes, W = this._w, inner = W - 32;
      const mode = this._modeWant && Date.now() - this._modeAt < 8000 ? this._modeWant : s.state;
      const size = Math.round(Math.max(200, Math.min(Number(this._c.max_size) || 360, inner < 400 ? inner - 8 : inner * 0.66)));
      const k = size / 300;
      const tg = this._target(s), unit = (this._h.config && this._h.config.unit_system && this._h.config.unit_system.temperature) || "°F";
      const low = a.min_temp ?? 32, high = a.max_temp ?? 122, cur = a.current_temperature;
      const r = size * 0.44, cx = size / 2, cy = size / 2, a0 = 135, sweep = 270, sw = Math.max(2, 2.4 * k);
      const ang = v => a0 + sweep * (Math.max(low, Math.min(high, v)) - low) / (high - low);
      const pt = an => [cx + r * Math.cos(an * Math.PI / 180), cy + r * Math.sin(an * Math.PI / 180)];
      const arc = (f, t, col) => { const [x1, y1] = pt(f), [x2, y2] = pt(t); return `<path d="M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r.toFixed(1)} ${r.toFixed(1)} 0 ${t - f > 180 ? 1 : 0} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}" fill="none" stroke="${col}" stroke-width="${sw.toFixed(1)}"/>`; };
      const handle = (v, col) => { const [hx, hy] = pt(ang(v)); return `<circle cx="${hx.toFixed(1)}" cy="${hy.toFixed(1)}" r="${(8 * k).toFixed(1)}" fill="${col}" stroke="${C.raised}" stroke-width="3"/>`; };
      const [x1, y1] = pt(a0), [x2, y2] = pt(a0 + sweep);
      const p = [`<path d="M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r.toFixed(1)} ${r.toFixed(1)} 0 1 1 ${x2.toFixed(1)} ${y2.toFixed(1)}" fill="none" stroke="${C.line}" stroke-width="1"/>`];
      const ok = v => v != null && isFinite(v);
      if (mode === "heat" && ok(tg.t)) p.push(arc(a0, ang(tg.t), C.red), handle(tg.t, C.red));
      else if (mode === "cool" && ok(tg.t)) p.push(arc(ang(tg.t), a0 + sweep, C.cool), handle(tg.t, C.cool));
      else if (mode === "heat_cool" && ok(tg.lo) && ok(tg.hi)) p.push(arc(a0, ang(tg.lo), C.red), arc(ang(tg.hi), a0 + sweep, C.cool), handle(tg.lo, C.red), handle(tg.hi, C.cool));
      const mono = `font-family="IBM Plex Mono, monospace"`, act = cap(String(a.hvac_action || (mode === "off" ? "off" : "idle")).replace(/_/g, " "));
      const small = Math.max(11, Math.round(12 * k));
      p.push(`<text x="${cx}" y="${(cy - r * 0.36).toFixed(1)}" text-anchor="middle" fill="${C.muted}" ${mono} font-size="${small}" letter-spacing="1.2">${esc(act.toUpperCase())}</text>`);
      const nowT = ok(cur) ? `NOW ${Math.round(cur)} ${unit}` : "";
      if (mode === "heat_cool") {
        const fs = Math.round(size * 0.17), dx = size * 0.15;
        for (const [x, v, w_, col] of [[cx - dx, tg.lo, "HEAT", C.redText], [cx + dx, tg.hi, "COOL", C.cool]]) {
          p.push(`<text x="${x.toFixed(1)}" y="${(cy + r * 0.12).toFixed(1)}" text-anchor="middle" fill="${C.ink}" font-family="IBM Plex Sans, sans-serif" font-weight="300" font-size="${fs}">${ok(v) ? Math.round(v) : "--"}</text>`);
          p.push(`<text x="${x.toFixed(1)}" y="${(cy + r * 0.3).toFixed(1)}" text-anchor="middle" fill="${col}" ${mono} font-size="${Math.max(10, Math.round(11 * k))}" letter-spacing="1">${w_}</text>`);
        }
        p.push(`<line x1="${cx}" y1="${(cy - r * 0.18).toFixed(1)}" x2="${cx}" y2="${(cy + r * 0.3).toFixed(1)}" stroke="${C.line}" stroke-width="1"/>`);
        p.push(`<text x="${cx}" y="${(cy + r * 0.5).toFixed(1)}" text-anchor="middle" fill="${C.muted}" ${mono} font-size="${small}">${nowT}</text>`);
      } else {
        const big = mode === "off" ? "Off" : ok(tg.t) ? String(Math.round(tg.t * 10) / 10) : "--";
        const u = mode === "off" ? "" : `<tspan font-size="${Math.round(20 * k)}" fill="${C.muted}" dx="${(4 * k).toFixed(1)}" dy="${(-26 * k).toFixed(1)}">${unit}</tspan>`;
        p.push(`<text x="${cx}" y="${(cy + r * 0.16).toFixed(1)}" text-anchor="middle" fill="${C.ink}" font-family="IBM Plex Sans, sans-serif" font-weight="300" font-size="${Math.round(size * 0.24)}">${big}${u}</text>`);
        p.push(`<text x="${cx}" y="${(cy + r * 0.38).toFixed(1)}" text-anchor="middle" fill="${C.muted}" ${mono} font-size="${small}">${nowT}</text>`);
      }
      const what = mode === "heat_cool" ? `heating to ${tg.lo} and cooling to ${tg.hi}` : mode === "off" ? "off" : `${mode === "heat" ? "heating" : "cooling"} to ${tg.t}`;
      const svgH = Math.round(cy + r * 0.92);
      const dial = `<svg role="img" aria-label="${esc(a.friendly_name || "")}: ${esc(what)} ${unit}, now ${cur} ${unit}" width="${size}" height="${svgH}" viewBox="0 0 ${size} ${svgH}">${p.join("")}</svg>`;
      const pm = which => `<button class="sbtn" data-act="step" data-arg="${which}:-1" aria-label="Lower">−</button><button class="sbtn" data-act="step" data-arg="${which}:1" aria-label="Raise">+</button>`;
      // minus and plus inside the dial, under the figure (one set point); two pairs under the dial for Heat/Cool
      const inside = (mode === "heat" || mode === "cool") ? `<div class="pm" style="top:${Math.round(cy + r * 0.52)}px">${pm("t")}</div>` : "";
      const below = mode === "heat_cool" ? `<div class="dual"><div class="grp"><span class="lab" style="color:${C.redText};margin-right:2px">Heat</span>${pm("lo")}</div>`
        + `<div class="grp"><span class="lab" style="color:${C.cool};margin-right:2px">Cool</span>${pm("hi")}</div></div>` : "";
      const modes = (a.hvac_modes || ["off", "heat", "cool", "heat_cool"]).filter(m => MODE_NAMES[m]);
      const segW = Math.min(inner, Math.max(size, 260));
      const seg = `<div class="seg slim" style="width:${segW}px" role="group" aria-label="${esc(a.friendly_name || "")} mode">${modes.map(m =>
        `<button type="button" aria-pressed="${m === mode}" data-act="mode" data-arg="${m}">${MODE_NAMES[m]}</button>`).join("")}</div>`;
      const fan = a.fan_mode ? ` · fan ${esc(String(a.fan_mode).toLowerCase())}` : "";
      const m = mode === "off" ? "Off" : mode === "heat_cool" ? `Heat to <b>${tg.lo ?? "--"}</b> · cool to <b>${tg.hi ?? "--"} ${unit}</b>`
        : `${MODE_NAMES[mode] || cap(mode)} to <b>${tg.t ?? "--"} ${unit}</b>`;
      return `<div class="panel" style="padding:14px 16px 14px">`
        + `<div class="title" style="text-align:center;margin-bottom:2px">${esc(this._c.name || a.friendly_name || "")}</div>`
        + `<div class="tw" style="width:${size}px;height:${svgH}px">${dial}${inside}</div>${below}`
        + `<div style="margin-top:12px">${seg}</div>`
        + `<div class="meta" style="text-align:center;margin-top:8px">${m}${fan}</div></div>`;
    }
    act(kind, arg) {
      const s = this._h.states[this._c.entity]; if (!s) return;
      if (kind === "mode") {
        this._modeWant = arg; this._modeAt = Date.now(); this._schedule();
        this.call("climate", "set_hvac_mode", { entity_id: this._c.entity, hvac_mode: arg });
        return;
      }
      const [which, d] = arg.split(":");
      const step = s.attributes.target_temp_step || 1, tg = this._target(s);
      const base = which === "t" ? tg.t : which === "lo" ? tg.lo : tg.hi;
      if (base == null) return;
      const nv = Math.round((Number(base) + Number(d) * step) * 10) / 10;
      this._pend = Object.assign({}, this._pend && Date.now() - this._pend.at < 8000 ? this._pend : {}, { [which]: nv, at: Date.now() });
      this._schedule();
      clearTimeout(this._send);
      this._send = setTimeout(() => {
        const t = this._target(this._h.states[this._c.entity]);
        const data = which === "t" ? { temperature: t.t } : { target_temp_low: t.lo, target_temp_high: t.hi };
        this.call("climate", "set_temperature", Object.assign({ entity_id: this._c.entity }, data));
      }, 800);
    }
  }

  // ====================================================================================================================
  // rt-line-card: "Power draw, 12 h", "AC draw, 48 h"
  // ====================================================================================================================
  class RtLine extends RtCard {
    defaults() { return { title: "", hours: 12, buckets: 72, series: [], unit: "W", decimals: 1, height: null, zero: true }; }
    watch() { return this._c.series.map(s => s.entity); }
    render() {
      const c = this._c, W = this._w, iw = W - 34;
      const h = c.height || (W < 600 ? 160 : 200);
      const figs = c.series.map((s, i) => {
        const st = this._h.states[s.entity], v = num(st), unit = s.unit || c.unit || (st && st.attributes.unit_of_measurement) || "";
        const k = s.key || (i === 0 && c.key_first);
        const val = v == null ? "--" : fix(v * (s.factor || 1), s.decimals ?? c.decimals);
        return `<div style="display:grid;gap:4px;justify-items:${i === 0 ? "start" : "end"}"><div class="fig" style="color:${k ? C.red : C.ink}">${val}<span class="u">${esc(unit)}</span></div>`
          + `<div class="lab">${esc(s.name || (st && st.attributes.friendly_name) || s.entity)}</div></div>`;
      }).join("");
      if (!this._data || Date.now() - this._dataAt > 4 * 60e3) this._load();
      let body = `<div class="meta wait">Reading the history</div>`, leg = "";
      if (this._data) {
        const { t0, t1, vals } = this._data;
        const all = vals.flat().filter(v => v != null);
        const max = Math.max(...all, 0), min = c.zero ? 0 : Math.min(...all);
        const yt = ticks(min, max || 1, c.zero);
        const series = vals.map((v, i) => ({ vals: v, color: i === 0 ? C.ink : C.muted, width: 1, dash: i === 0 ? null : "4 4" }));
        const last = vals[0].length - 1;
        const every = c.hours <= 12 ? 3 : c.hours <= 24 ? 6 : W < 600 ? 24 : 12;
        body = chart({ w: iw, h, series, ymin: yt[0], ymax: yt[yt.length - 1], yt, padL: 40,
          xl: hourLabels(t0, t1, every), now: [1, vals[0][last]], aria: c.title });
        if (c.series.length > 1) leg = `<div style="display:flex;gap:18px;margin-top:8px;flex-wrap:wrap">` + c.series.map((s, i) => {
          const st = this._h.states[s.entity], v = num(st), unit = s.unit || c.unit || "";
          return `<div class="meta" style="display:flex;align-items:center;gap:6px">${sample(i ? C.muted : C.ink, 1, i ? "4 4" : null)}${esc(s.name || "")} <b>${v == null ? "--" : fix(v * (s.factor || 1), s.decimals ?? c.decimals)} ${esc(unit)}</b></div>`;
        }).join("") + `</div>`;
      }
      return `<div class="panel"><div class="title">${esc(c.title)}</div>`
        + `<div style="display:flex;justify-content:space-between;margin:12px 0 14px">${figs}</div>${body}${leg}</div>`;
    }
    _load() {
      if (this._loading) return; this._loading = true;
      const c = this._c, ids = c.series.map(s => s.entity);
      historyOf(this._h, ids, c.hours).then(r => {
        const t1 = Date.now(), t0 = t1 - c.hours * 3600e3;
        this._data = { t0, t1, vals: c.series.map(s => buckets(r.data[s.entity] || [], t0, t1, c.buckets).map(v => v == null ? null : v * (s.factor || 1))) };
        this._dataAt = Date.now(); this._loading = false; this._schedule();
      }).catch(() => { this._loading = false; });
    }
  }

  // ====================================================================================================================
  // rt-weather-card: the forecast and the temperatures, today or the week
  // ====================================================================================================================
  class RtWeather extends RtCard {
    defaults() { return { entity: "weather.forecast_home", indoor: [], top: 22, top_phone: 22 }; }
    watch() { return [this._c.entity, ...(this._c.indoor || []).map(x => x.entity)]; }
    attached() { this._fc = this._fc || {}; this._subscribe("hourly"); this._subscribe("daily"); }
    detached() { for (const k of Object.keys(this._subs || {})) { const u = this._subs[k]; Promise.resolve(u).then(f => f && f()).catch(() => {}); } this._subs = {}; }
    _subscribe(type) {
      this._subs = this._subs || {};
      if (this._subs[type] || !this._h) { if (!this._h) setTimeout(() => this._subscribe(type), 500); return; }
      this._subs[type] = this._h.connection.subscribeMessage(m => { this._fc[type] = m.forecast || []; this._schedule(); },
        { type: "weather/subscribe_forecast", forecast_type: type, entity_id: this._c.entity }).catch(() => { delete this._subs[type]; });
    }
    css() { return `
      .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
      .one { display: grid; gap: 10px; }
      .cols { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
      .wk { display: flex; align-items: center; gap: 10px; height: 41px; border-bottom: 1px solid ${C.rule}; }
      .wk:last-child { border-bottom: 0; }
      .wk .c { flex: 1 1 auto; min-width: 0; font: 400 13px/1.3 ${SANS}; color: ${C.text}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .wk .lo, .wk .hi { width: 30px; flex: none; font: 400 12px/1 ${MONO}; }
      .wk .lo { text-align: right; color: ${C.muted}; } .wk .hi { color: ${C.ink}; }
      .bar { position: relative; height: 12px; flex: none; }
      .bar i { position: absolute; left: 0; right: 0; top: 5.5px; height: 1px; background: ${C.rule}; }
      .bar b { position: absolute; top: 5px; height: 2px; background: ${C.ink}; }
      .bar s { position: absolute; top: 2.5px; width: 7px; height: 7px; border-radius: 50%; background: ${C.red}; }
      .f3 { display: grid; gap: 4px; flex: none; }
      @media (max-width: 560px) { .head.top { margin-top: var(--tp); } }
    `; }
    render() {
      const c = this._c, W = this._w, wide = W >= 900, mode = this._mode || "today";
      this._subscribe("hourly"); this._subscribe("daily");
      if (!this._hist || Date.now() - this._histAt > 5 * 60e3 || this._histMode !== mode) this._load(mode);
      const seg = `<div class="seg" role="group" aria-label="Forecast and trends, today or the week" style="width:150px;flex:none">`
        + ["today", "week"].map(o => `<button type="button" aria-pressed="${o === mode}" data-act="mode" data-arg="${o}">${o === "today" ? "Today" : "Week"}</button>`).join("") + `</div>`;
      const head = `<div class="head top" style="margin-top:${c.top}px;--tp:${c.top_phone}px"><div class="lab">Weather</div>${seg}</div>`;
      const iw = wide ? Math.floor((W - 10) / 2) - 34 : W - 34;
      const fc = this._forecastPanel(mode, iw), tr = this._trendPanel(mode, iw, wide ? 290 : 180);
      return head + (wide ? `<div class="two">${fc}${tr}</div>` : `<div class="one">${fc}${tr}</div>`);
    }
    _forecastPanel(mode, iw) {
      const s = this._h.states[this._c.entity];
      if (!s) return `<div class="panel"><div class="meta">${esc(this._c.entity)} isn't in Home Assistant</div></div>`;
      const a = s.attributes, unit = a.temperature_unit || "°F", daily = this._fc.daily || [], hourly = this._fc.hourly || [];
      const d0 = daily[0] || {}, t24 = Date.now() + 24 * 3600e3;
      const next = hourly.filter(f => { const t = +new Date(f.datetime); return t > Date.now() && t <= t24 && f.temperature != null; }).map(f => f.temperature);
      let hi = null, lo = null;
      if (next.length >= 6) { const all = next.concat(a.temperature != null ? [a.temperature] : []); hi = Math.max(...all); lo = Math.min(...all); }
      else if (d0.temperature != null) { hi = d0.temperature; lo = d0.templow ?? d0.temperature; }
      const hiLo = hi != null ? `High ${Math.round(hi)} · low ${Math.round(lo)}` : "";
      const top = `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px"><div class="title">${esc(a.friendly_name || "Forecast")}</div>`
        + `<div style="font:400 13px/1.3 ${SANS};color:${C.ink}">${esc(COND[s.state] || cap(s.state))}</div></div>`
        + `<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-top:10px">`
        + `<div style="font:300 46px/1 ${SANS};color:${C.ink};letter-spacing:-.01em">${a.temperature != null ? Math.round(a.temperature) : "--"}<span style="font-size:20px;color:${C.muted};margin-left:4px">${esc(unit)}</span></div>`
        + `<div class="lab" style="padding-bottom:4px">${esc(hiLo)}</div></div>`
        + `<div class="meta" style="margin-top:10px">Humidity <b>${a.humidity ?? "--"} %</b> · wind <b>${a.wind_speed != null ? Math.round(a.wind_speed) : "--"} ${esc(a.wind_speed_unit || "")} ${compass(a.wind_bearing)}</b> · dew point <b>${a.dew_point ?? "--"} ${esc(unit)}</b></div>`
        + `<div style="border-top:1px solid ${C.rule};margin-top:14px"></div>`;
      let area;
      if (mode === "today") {
        const now = Date.now(), t0 = now - 12 * 3600e3, t1 = now + 12 * 3600e3;
        const meas = this._hist && this._hist.out ? buckets(this._hist.out, t0, now, 48) : [];
        const mPts = meas.map((v, i) => [(i + 0.5) / 96, v]);
        if (a.temperature != null && meas.some(v => v != null)) mPts.push([0.5, a.temperature]);
        const fPts = [[0.5, a.temperature]].concat(hourly.map(f => [(new Date(f.datetime) - t0) / (t1 - t0), f.temperature]).filter(([f]) => f > 0.5 && f <= 1));
        const vals = mPts.map(p => p[1]).concat(fPts.map(p => p[1])).filter(v => v != null && isFinite(v));
        const lo = Math.floor((Math.min(...vals, a.temperature ?? 50) - 2) / 10) * 10, hi = Math.ceil((Math.max(...vals, a.temperature ?? 60) + 2) / 10) * 10;
        const yt = []; for (let v = lo; v <= hi; v += 10) yt.push(v);
        const ch = chart({ w: iw, h: 150, series: [{ pts: fPts, color: C.muted, width: 1, dash: "4 4" }, { pts: mPts, color: C.ink, width: 1.25 }],
          ymin: lo, ymax: hi, yt, padL: 28, padB: 20, now: [0.5, a.temperature],
          xl: [[0, hourName(t0)], [0.25, hourName(now - 6 * 3600e3)], [0.5, "Now"], [0.75, hourName(now + 6 * 3600e3)], [1, hourName(t1)]],
          aria: "Outside: measured the last 12 hours, forecast the next 12" });
        const slots = [3, 6, 9, 12].map(k => hourly.find(f => new Date(f.datetime) >= now + (k - 0.5) * 3600e3)).filter(Boolean);
        const cols = slots.map(f => `<div style="display:grid;gap:3px;min-width:0"><div class="lab">${esc(hourName(f.datetime))}</div>`
          + `<div style="font:300 22px/1.1 ${SANS};color:${C.ink}">${Math.round(f.temperature)}<span style="font-size:13px;color:${C.muted};margin-left:2px">${esc(unit)}</span></div>`
          + `<div style="font:400 12px/1.3 ${SANS};color:${C.muted};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(COND[f.condition] || cap(f.condition))}</div></div>`).join("");
        const leg = `<div style="display:flex;gap:16px;align-items:center;margin-top:10px"><div style="display:flex;gap:6px;align-items:center">${sample(C.ink, 1.25)}<span class="meta">Measured</span></div>`
          + `<div style="display:flex;gap:6px;align-items:center">${sample(C.muted, 1, "4 4")}<span class="meta">Forecast, met.no</span></div></div>`;
        area = ch + `<div class="cols">${cols}</div>` + leg;
      } else {
        const days = daily.slice(0, 7);
        if (!days.length) area = `<div class="meta wait">Waiting for the forecast</div>`;
        else {
          const lo_s = Math.min(...days.map(d => d.templow ?? d.temperature), a.temperature ?? 99) - 2, hi_s = Math.max(...days.map(d => d.temperature), a.temperature ?? 0) + 2;
          const bw = iw < 420 ? 96 : 250, x = v => (v - lo_s) / (hi_s - lo_s) * bw;
          area = days.map((d, i) => {
            const lo = Math.round(d.templow ?? d.temperature), hi = Math.round(d.temperature);
            const day = new Date(d.datetime).toLocaleDateString("en-US", { weekday: "short" });
            const pr = d.precipitation_probability ? `<span style="font:400 11px/1 ${MONO};color:${C.muted};margin-left:8px">${Math.round(d.precipitation_probability)} %</span>` : "";
            const nd = i === 0 && a.temperature != null ? `<s style="left:${(x(a.temperature) - 3.5).toFixed(1)}px"></s>` : "";
            return `<div class="wk"><div class="lab" style="width:56px;flex:none;${i === 0 ? `color:${C.ink}` : ""}">${esc(i === 0 ? "Today" : day)}</div>`
              + `<div class="c">${esc(COND[d.condition] || cap(d.condition))}${pr}</div><div class="lo">${lo}°</div>`
              + `<div class="bar" style="width:${bw}px"><i></i><b style="left:${x(lo).toFixed(1)}px;width:${Math.max(2, x(hi) - x(lo)).toFixed(1)}px"></b>${nd}</div><div class="hi">${hi}°</div></div>`;
          }).join("");
        }
      }
      return `<div class="panel" style="height:100%">${top}<div style="min-height:248px;margin-top:12px">${area}</div></div>`;
    }
    _trendPanel(mode, iw, chH) {
      const title = mode === "today" ? "Temperature, last 24 h" : "Temperature, last 7 days";
      const lines = [{ name: "Outdoor", color: C.ink, width: 1.25, dash: null, now: (this._h.states[this._c.entity] || {}).attributes?.temperature }]
        .concat((this._c.indoor || []).map((x, i) => ({ name: x.name, entity: x.entity, color: i ? C.muted : C.strong, width: 1, dash: i ? "1.5 2.5" : "5 3", now: num(this._h.states[x.entity]) })));
      const figs = lines.map(l => `<div class="f3"><div style="display:flex;align-items:center;gap:6px;white-space:nowrap">${sample(l.color, l.width, l.dash)}<span class="lab">${esc(l.name)}</span></div>`
        + `<div style="font:300 22px/1.1 ${SANS};color:${C.ink}">${l.now != null ? Math.round(l.now) : "--"}<span style="font-size:13px;color:${C.muted};margin-left:3px">°F</span></div></div>`).join("");
      let body = `<div class="meta wait">Reading the history</div>`;
      if (this._hist && this._histMode === mode) {
        const hours = mode === "today" ? 24 : 168, n = mode === "today" ? 96 : 168, t1 = Date.now(), t0 = t1 - hours * 3600e3;
        const vals = [buckets(this._hist.out || [], t0, t1, n)].concat((this._c.indoor || []).map(x => buckets(this._hist.ins[x.entity] || [], t0, t1, n)));
        const all = vals.flat().filter(v => v != null);
        const lo = Math.floor((Math.min(...all, 60) - 2) / 10) * 10, hi = Math.ceil((Math.max(...all, 70) + 2) / 10) * 10;
        const yt = []; for (let v = lo; v <= hi; v += 10) yt.push(v);
        const series = vals.map((v, i) => ({ vals: v, color: lines[i].color, width: lines[i].width, dash: lines[i].dash })).reverse();
        const mids = []; const d = new Date(t0); d.setHours(24, 0, 0, 0); for (; +d < t1; d.setDate(d.getDate() + 1)) mids.push((+d - t0) / (t1 - t0));
        const xl = mode === "today" ? hourLabels(t0, t1, 6, "Now") : [[0, new Date(t0).toLocaleDateString("en-US", { weekday: "short" })]]
          .concat(mids.filter(f => f > 0.06 && f < 0.94).map(f => [f + 0.5 / 7, new Date(t0 + f * (t1 - t0) + 12 * 3600e3).toLocaleDateString("en-US", { weekday: "short" })])).concat([[1, "Now"]]);
        body = chart({ w: iw, h: chH, series, ymin: lo, ymax: hi, yt, xl, vl: mids, padL: 28, padB: 20, aria: title });
      }
      return `<div class="panel" style="height:100%"><div class="title">${title}</div>`
        + `<div style="display:flex;justify-content:space-between;gap:10px;margin-top:12px">${figs}</div><div style="margin-top:14px">${body}</div></div>`;
    }
    _load(mode) {
      if (this._loading === mode) return; this._loading = mode;
      const hours = mode === "today" ? 24 : 168, ids = (this._c.indoor || []).map(x => x.entity);
      Promise.all([historyOf(this._h, [this._c.entity], hours, "temperature"), ids.length ? historyOf(this._h, ids, hours) : Promise.resolve({ data: {} })])
        .then(([o, i]) => { this._hist = { out: o.data[this._c.entity] || [], ins: i.data }; this._histMode = mode; this._histAt = Date.now(); this._loading = null; this._schedule(); })
        .catch(() => { this._loading = null; });
    }
    act(kind, arg) { if (kind === "mode") { this._mode = arg; this._schedule(); } }
  }

  // ====================================================================================================================
  // rt-energy-card: Electricity
  // ====================================================================================================================
  const CIRCUITS = [["Garage EV", "car"], ["Cooling", "ac"], ["Kitchen", "kitchen"], ["Living", "living"], ["First floor lights", "1st_floor_light"],
    ["Studio", "studio"], ["Dishwasher", "dishwasher"], ["Washer / dryer", "w_d"], ["Maag", "plants"], ["Other", "balance"]];
  class RtEnergy extends RtCard {
    defaults() { return { whole: "redmonitor", polestar: "sensor.polestar_8882", maag_power: "sensor.greenhouse_utility_cabinet_power",
      climates: ["climate.kitchen_thermostat", "climate.ground_floor_thermostat"] }; }
    watch() {
      const w = this._c.whole;
      return [`sensor.${w}_power_minute_average`, `sensor.${w}_energy_today`, `sensor.${w}_energy_this_month`, `${this._c.polestar}_charging_power`,
        `${this._c.polestar}_battery_charge_level`, `${this._c.polestar}_charging_status`, `${this._c.polestar}_charger_connection_status`,
        ...CIRCUITS.map(([, k]) => `sensor.${k}_power_minute_average`), this._c.maag_power, ...this._c.climates];
    }
    css() { return `
      .stat { display: flex; gap: 16px; border-top: 1px solid ${C.strong}; padding-top: 14px; }
      .stat > div { flex: 1 1 0; min-width: 0; display: grid; gap: 6px; align-content: start; }
      .split { display: grid; grid-template-columns: minmax(0, 760fr) minmax(0, 448fr); gap: 32px; align-items: start; }
      .tm { position: relative; }
      .tm > div { position: absolute; box-sizing: border-box; overflow: hidden; }
      .tm .n { font: 300 15px/1.1 ${SANS}; color: ${C.ink}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .tm .vv { font: 400 11px/1.4 ${MONO}; color: ${C.muted}; white-space: nowrap; }
      .tm .key .n { font-size: 28px; } .tm .key .vv { font-size: 13px; color: ${C.redText}; }
    `; }
    render() {
      const c = this._c, h = this._h, W = this._w, wide = W >= 900, P = c.polestar;
      const st = id => h.states[id], kw = id => { const v = num(st(id)); return v == null ? null : v / 1000; };
      const now = kw(`sensor.${c.whole}_power_minute_average`), today = num(st(`sensor.${c.whole}_energy_today`)), month = num(st(`sensor.${c.whole}_energy_this_month`));
      const chW = num(st(`${P}_charging_power`)), charging = chW != null && chW > 50, batt = num(st(`${P}_battery_charge_level`)), range = num(st(`${P}_range`));
      const conn = (st(`${P}_charger_connection_status`) || {}).state, full = st(`${P}_estimated_fully_charged_time`);
      const fullAt = full && full.state && !["unknown", "unavailable"].includes(full.state) ? time(full.state) : null;
      const col = (lab, v, u, m, key) => `<div><div class="lab">${esc(lab)}</div><div class="fig" style="color:${key ? C.red : C.ink}">${v}<span class="u">${esc(u)}</span></div>${m ? `<div class="meta">${m}</div>` : ""}</div>`;
      const pole = charging ? col("Polestar", fix(chW / 1000, 1), "kW", `Charging${fullAt ? ` · full at ${esc(fullAt)}` : ""}`)
        : col("Polestar", batt == null ? "--" : fix(batt, 0), "%", conn === "Connected" ? "Plugged in · not charging" : "Not charging");
      const stats = `<div class="stat">${col("Now", fix(now, 2), "kW", "", true)}${col("Today", fix(today, 1), "kWh")}${col("This month", fix(month, 0), "kWh")}${wide ? pole : ""}</div>`;
      // the last 24 hours
      if (!this._day || Date.now() - this._dayAt > 4 * 60e3) this._loadDay();
      let ch = `<div class="meta wait">Reading the history</div>`;
      if (this._day) {
        const v = this._day.vals, max = Math.max(...v.filter(x => x != null), 1), yt = ticks(0, max, true);
        ch = chart({ w: W, h: wide ? 180 : 150, series: [{ vals: v, color: C.ink, width: 1 }], ymin: 0, ymax: yt[yt.length - 1], yt, padL: 34,
          xl: hourLabels(this._day.t0, this._day.t1, 6), now: [1, v[v.length - 1]], aria: "Whole home, the last 24 hours, kW" });
      }
      const dayBlock = `<div class="head"><div class="lab">Last 24 hours</div><div class="meta">kW</div></div>${ch}`;
      // where it goes
      const per = this._per || "now";
      if (per !== "now" && (!this._tot || this._tot.per !== per || Date.now() - this._tot.at > 10 * 60e3)) this._loadTotals(per);
      let items = [];
      if (per === "now") items = CIRCUITS.map(([n, k]) => [n, kw(`sensor.${k}_power_minute_average`)]);
      else if (this._tot && this._tot.per === per) items = CIRCUITS.map(([n, k]) => [n, this._tot.v[k]]);
      items = items.filter(([, v]) => v != null && v > (per === "now" ? 0.002 : 0.05)).sort((a, b) => b[1] - a[1]);
      const tw = wide ? Math.round((W - 32) * 760 / 1208) : W, th = wide ? 296 : 250;
      const fmtV = v => per === "now" ? (v >= 0.1 ? `${v.toFixed(2)} kW` : `${Math.round(v * 1000)} W`) : `${v >= 10 ? Math.round(v) : v.toFixed(1)} kWh`;
      let tm = `<div class="meta wait" style="height:${th}px">${per === "now" ? "No circuit is drawing power" : "Reading the totals"}</div>`;
      if (items.length) {
        const rects = squarify(items.map(([n, v]) => [n, Math.sqrt(v)]), 0, 0, tw, th);
        tm = `<div class="tm" role="img" aria-label="${per === "now" ? "Where the power goes now" : per === "week" ? "The highest consumption this week" : "The highest consumption this month"}" style="width:${tw}px;height:${th}px">`
          + items.map(([n, v], i) => {
            const [x, y, rw, rh] = rects[n], key = i === 0, bg = key ? C.tile[3] : C.tile[1 + (i % 2)];
            let inner = "";
            if (rw > 56 && rh > 40) inner = `<div class="n">${esc(n)}</div><div class="vv">${fmtV(v)}</div>`;
            else if (rw > 46 && rh > 26) inner = `<div class="vv" style="font-size:10px;overflow:hidden">${esc(n)}</div>`;
            return `<div class="${key ? "key" : ""}" title="${esc(n)} ${fmtV(v)}" style="left:${(x + 1).toFixed(1)}px;top:${(y + 1).toFixed(1)}px;width:${(rw - 2).toFixed(1)}px;height:${(rh - 2).toFixed(1)}px;background:${bg};padding:${rw > 56 ? "8px 10px" : "4px"}">${inner}${key ? cornerTicks(C.red) : ""}</div>`;
          }).join("") + `</div>`;
      }
      const segT = { now: "Where it goes now", week: "Highest this week", month: "Highest this month" }[per];
      const seg = `<div class="seg" role="group" aria-label="Period" style="width:192px;flex:none">` + ["now", "week", "month"].map(o =>
        `<button type="button" aria-pressed="${o === per}" data-act="per" data-arg="${o}">${cap(o)}</button>`).join("") + `</div>`;
      const where = `<div class="head"><div class="lab">${segT}</div>${seg}</div>${tm}<div class="meta" style="margin-top:8px">Area by square root, so small loads stay readable</div>`;
      // the loads
      const mW = num(st(c.maag_power)) ?? (num(st("sensor.plants_power_minute_average"))), mToday = num(st("sensor.plants_energy_today"));
      const acW = num(st("sensor.ac_power_minute_average"));
      const zones = c.climates.map(e => st(e)).filter(Boolean).map(s => `${String(s.attributes.friendly_name || "").replace(/ Thermostat$/i, "").toLowerCase()} ${s.state === "heat_cool" ? "heat/cool" : s.state}`).join(", ");
      const rowH = (k, dot, v, m, trail) => `<div class="row"><div class="k"><div class="lab">${k}</div></div><div class="v"><div class="vv">${dot ? `<span class="dot ${dot}"></span>` : ""}<span style="overflow:hidden;text-overflow:ellipsis">${v}</span></div>${m ? `<div class="meta">${m}</div>` : ""}</div>${trail || ""}</div>`;
      const pv = charging ? `Charging ${fix(chW / 1000, 1)} kW` : conn === "Connected" ? "Plugged in" : conn && !["unknown", "unavailable"].includes(conn) ? "Unplugged" : "Not charging";
      const pm = [batt != null ? `${fix(batt, 0)} %` : null, range != null ? `${Math.round(range)} mi` : null, charging && fullAt ? `full at <b>${esc(fullAt)}</b>` : null].filter(Boolean).join(" · ");
      const loads = `<div class="head"><div class="lab">Loads</div></div><div class="rows">`
        + rowH("Polestar", charging ? "on" : "off", esc(pv), pm)
        + rowH("Maag", mW != null && mW > 5 ? "on" : "off", mW == null ? "Not reporting" : `${Math.round(mW)} W`, mToday != null ? `<b>${fix(mToday, 1)} kWh</b> today · metered cabinet` : "metered cabinet")
        + rowH("Cooling", acW != null && acW > 50 ? "on" : "off", acW == null ? "--" : acW >= 100 ? `${fix(acW / 1000, 2)} kW` : `${Math.round(acW)} W`, `Two zones${zones ? ` · ${esc(zones)}` : ""}`)
        + rowH("History", "", "Home Assistant Energy", "Days, months, costs", `<button class="btn" style="height:36px;font-size:13px;flex:none" data-act="open" data-arg="/energy">Open</button>`)
        + `</div>`;
      if (wide) return stats + dayBlock + `<div class="split" style="margin-top:4px"><div>${where}</div><div>${loads}</div></div>`;
      return stats + dayBlock + where + loads;
    }
    _loadDay() {
      if (this._dayLoading) return; this._dayLoading = true;
      const id = `sensor.${this._c.whole}_power_minute_average`;
      historyOf(this._h, [id], 24).then(r => {
        const t1 = Date.now(), t0 = t1 - 24 * 3600e3;
        this._day = { t0, t1, vals: buckets(r.data[id] || [], t0, t1, 96).map(v => v == null ? null : v / 1000) };
        this._dayAt = Date.now(); this._dayLoading = false; this._schedule();
      }).catch(() => { this._dayLoading = false; });
    }
    _loadTotals(per) {
      if (this._totLoading === per) return; this._totLoading = per;
      const h = this._h;
      if (per === "month") {
        const v = {}; for (const [, k] of CIRCUITS) v[k] = num(h.states[`sensor.${k}_energy_this_month`]);
        this._tot = { per, v, at: Date.now() }; this._totLoading = null; this._schedule(); return;
      }
      const ids = CIRCUITS.map(([, k]) => `sensor.${k}_energy_today`);
      statsOf(h, ids, 7, "day", ["change"]).then(r => {
        const v = {};
        for (const [, k] of CIRCUITS) { const rows = r.data[`sensor.${k}_energy_today`] || []; v[k] = rows.reduce((a, b) => a + (b.change > 0 ? b.change : 0), 0); }
        this._tot = { per, v, at: Date.now() }; this._totLoading = null; this._schedule();
      }).catch(() => { this._totLoading = null; });
    }
    act(kind, arg) { if (kind === "per") { this._per = arg; this._schedule(); } else if (kind === "open") this.nav(arg); }
  }

  // ====================================================================================================================
  // rt-io-card: In and out
  // ====================================================================================================================
  const MASS = `<path d="M14.8 1364.3L13.6 1365.0M13.6 1365.0L13.6 1064.1M13.6 1365.0L619.3 1714.7M13.6 1365.0L15.4 1362.9M619.8 1716.6L618.6 1717.3M1672.9 1703.8L1674.1 1704.5M618.6 1717.3L618.6 1713.1M618.6 1717.3L1135.3 2015.6M618.6 1717.3L620.2 1715.9M1674.1 1704.5L1135.3 2015.6M1674.1 1704.5L1674.1 1403.7M1674.1 1704.5L1673.0 1703.7M14.8 326.2L13.6 324.5M1156.8 366.7L1158.2 365.2M13.6 795.4L13.6 324.5M550.7 14.4L13.6 324.5M550.7 14.4L1158.2 365.2M14.8 325.2L13.6 324.5M1158.2 684.9L1158.2 365.2M1157.0 365.8L1158.2 365.2M13.6 1064.1L13.6 795.4M1673.1 983.3L1674.1 982.4M1158.0 684.4L1674.1 982.4M1674.1 1403.7L1674.1 982.4M1672.9 983.1L1674.1 982.4M619.7 676.8L621.1 675.3M621.0 673.9L621.1 675.3M621.1 675.3L14.8 325.2M622.4 676.9L621.1 675.3M620.2 996.4L619.1 995.6M621.1 995.0L621.1 675.3M618.6 1147.0L618.6 995.2M1157.4 684.1L618.6 995.2M621.1 675.3L1157.0 365.8M618.6 1713.1L618.6 1416.4M1135.3 2014.9L1135.3 1714.7M618.6 1416.4L618.6 1147.0M1134.2 1294.4L1135.3 1293.5M1135.4 1292.1L1135.3 1293.5M1135.3 1293.5L619.2 995.5M1135.3 1714.7L1135.3 1293.5M1135.3 1293.5L1672.9 983.1" fill="none" stroke="${C.ink}" stroke-width="1.2" stroke-linecap="square" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
  const MW = 1687, MH = 2029;
  class RtIO extends RtCard {
    defaults() { return { electricity: "sensor.redmonitor_power_minute_average", data: ["sensor.cgm4331com_download_speed", "sensor.cgm4331com_upload_speed"],
      compute: ["sensor.greenhouse_llm_status", "sensor.greenhouse_supervisor_status"],
      // Electricity split by circuit (Emporia), inside its square; "Other" is what no circuit meters
      circuits: [["sensor.ac_power_minute_average", "AC"], ["sensor.living_power_minute_average", "Living"], ["sensor.kitchen_power_minute_average", "Kitchen"],
        ["sensor.studio_power_minute_average", "Studio"], ["sensor.1st_floor_light_power_minute_average", "Ground floor light"], ["sensor.car_power_minute_average", "Polestar"],
        ["sensor.w_d_power_minute_average", "Washer and dryer"], ["sensor.dishwasher_power_minute_average", "Dishwasher"], ["sensor.plants_power_minute_average", "Plants"],
        ["sensor.balance_power_minute_average", "Other"]] }; }
    watch() { return [this._c.electricity, ...this._c.data, ...this._c.compute, ...this._c.circuits.map(c => c[0])]; }
    css() { return `
      .tree { position: absolute; top: 0; }
      .tree > div { position: absolute; box-sizing: border-box; display: flex; flex-direction: column; overflow: hidden; }
    `; }
    render() {
      const c = this._c, h = this._h, W = this._w, wide = W >= 900;
      const el = num(h.states[c.electricity]);
      const dl = num(h.states[c.data[0]]), ul = num(h.states[c.data[1]]);
      const comp = c.compute.map(e => h.states[e]).filter(Boolean);
      const compOn = comp.some(s => ["running", "online", "ok", "on"].includes(s.state));
      const circ = c.circuits.map(([e, n]) => ({ name: n, w: num(h.states[e]) })).filter(x => x.w != null && x.w >= 5).sort((p, q) => q.w - p.w);
      const IN = [{ name: "Electricity", value: el == null ? null : fix(el / 1000, 2), unit: "kW", src: "Emporia, whole home, by circuit", circuits: circ, weight: circ.length ? 6 : 3 },
        dl != null ? { name: "Data", value: fix((dl + (ul || 0)) * 8 / 1000, 1), unit: "Mbit/s", src: "Gateway, down and up" } : { name: "Data", src: "No meter yet (the gateway is a bridge)" },
        { name: "Water", src: "No meter yet" }, { name: "Gas", src: "No meter yet" }];
      const OUT = [{ name: "Compute", src: compOn ? "Maag's agents, running" : "Maag's agents, offline", state: compOn ? "Running" : "Offline" },
        { name: "Heat", src: "No sensor yet" }, { name: "Light", src: "No sensor yet" }];
      const [tw, th, hw, gap] = wide ? [Math.min(470, (W - 26 - 120 - 120) / 2), 250, 120, 60] : [Math.max(96, (W - 26 - 58 - 30) / 2), 176, 58, 15];
      const inner = 2 * tw + hw + 2 * gap, left = Math.max(0, (W - 26 - inner) / 2), hx = left + tw + gap, cy = th / 2, hh = hw * MH / MW;
      const tree = (items, x0, aria) => {
        const rects = squarify(items.map(it => [it.name, it.value != null ? (it.weight || 3) : 1]), 0, 0, tw, th);
        return `<div class="tree" role="img" aria-label="${aria}" style="left:${x0.toFixed(1)}px;width:${tw.toFixed(0)}px;height:${th}px">` + items.map(it => {
          const [x, y, rw, rh] = rects[it.name];
          let body, bg;
          if (it.value != null) {
            const pad = rw > 70 ? [8, 10] : [6, 7], head = wide ? 66 : 50, iw = rw - 2 - 2 * pad[1], ih = rh - 2 - 2 * pad[0] - head;
            if (it.circuits && it.circuits.length && iw > 90 && ih > 40) {
              // the circuits as a treemap inside the square, by what each draws now
              const cr = squarify(it.circuits.map(x => [x.name, x.w]), 0, 0, iw, ih);
              const cells = it.circuits.map((x, k) => { const [cx_, cy_, cw_, ch_] = cr[x.name];
                const txt = cw_ > 58 && ch_ > 30 ? `<div class="lab" style="font-size:9px;line-height:1.2;color:${C.text};white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(x.name)}</div><div style="font:300 12px/1.2 ${SANS};color:${C.ink}">${Math.round(x.w)}<span style="font-size:10px;color:${C.muted};margin-left:2px">W</span></div>`
                  : cw_ > 34 && ch_ > 16 ? `<div style="font:300 10px/1.2 ${SANS};color:${C.ink}">${Math.round(x.w)}</div>` : "";
                return `<div title="${esc(x.name)}: ${Math.round(x.w)} W" style="position:absolute;box-sizing:border-box;overflow:hidden;left:${cx_.toFixed(1)}px;top:${cy_.toFixed(1)}px;width:${Math.max(0, cw_ - 2).toFixed(1)}px;height:${Math.max(0, ch_ - 2).toFixed(1)}px;background:${C.tile[k % 2 ? 1 : 2]};padding:${cw_ > 58 && ch_ > 30 ? "4px 5px" : "2px 3px"}">${txt}</div>`; }).join("");
              body = `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px"><div class="lab" style="color:${C.ink}">${esc(it.name)}</div><div class="meta" style="font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(it.src)}</div></div>`
                + `<div style="font:300 ${wide ? 30 : 22}px/1.05 ${SANS};color:${C.ink};white-space:nowrap;margin-top:6px">${it.value}<span style="font-size:${wide ? 13 : 11}px;color:${C.muted};margin-left:3px">${esc(it.unit)}</span></div>`
                + `<div role="img" aria-label="Electricity by circuit" style="position:relative;margin-top:auto;width:${iw.toFixed(1)}px;height:${ih.toFixed(1)}px">${cells}</div>`;
            } else {
              body = `<div class="lab" style="color:${C.ink}">${esc(it.name)}</div><div style="margin-top:auto;font:300 ${wide ? 30 : 22}px/1.05 ${SANS};color:${C.ink};white-space:nowrap">${it.value}<span style="font-size:${wide ? 13 : 11}px;color:${C.muted};margin-left:3px">${esc(it.unit)}</span></div>`
                + `<div class="meta" style="font-size:10px;margin-top:4px;line-height:1.35">${esc(it.src)}</div>`;
            }
            bg = `background:${C.tile[3]}`;
          } else {
            body = `<div class="lab" style="font-size:10px;color:${C.text}">${esc(it.name)}</div>`
              + (rh > 44 && rw > 76 ? `<div class="meta" style="font-size:10px;margin-top:2px;line-height:1.3">${esc(it.state || "Not measured")}${wide && rw > 100 ? ` · ${esc(it.src)}` : ""}</div>` : "");
            bg = `background:${HATCH}, ${C.tile[1]}`;
          }
          return `<div title="${esc(it.name)}: ${esc(it.value != null ? it.value + " " + it.unit : it.state || "not measured")}" style="left:${(x + 1).toFixed(1)}px;top:${(y + 1).toFixed(1)}px;width:${(rw - 2).toFixed(1)}px;height:${(rh - 2).toFixed(1)}px;${bg};padding:${rw > 70 ? "8px 10px" : "6px 7px"}">${body}</div>`;
        }).join("") + `</div>`;
      };
      const arrow = (x1, y, x2) => `<line x1="${x1.toFixed(1)}" y1="${y}" x2="${x2.toFixed(1)}" y2="${y}" stroke="${C.ink}" stroke-width="1"/><path d="M ${(x2 - 6).toFixed(1)} ${y - 4} L ${x2.toFixed(1)} ${y} L ${(x2 - 6).toFixed(1)} ${y + 4}" fill="none" stroke="${C.ink}" stroke-width="1"/>`;
      const svgW = W - 26;
      return `<div style="padding:4px 13px 0">`
        + `<div style="display:flex;justify-content:space-between;padding:0 ${left.toFixed(0)}px 10px"><div class="lab">In</div><div class="lab">Now</div><div class="lab">Out</div></div>`
        + `<div style="position:relative;width:${svgW}px;height:${th}px">`
        + tree(IN, left, "What comes in") + tree(OUT, left + tw + gap * 2 + hw, "What goes out")
        + `<svg aria-label="Red Tower as two plain volumes" role="img" viewBox="0 0 ${MW} ${MH}" style="position:absolute;left:${hx.toFixed(1)}px;top:${(cy - hh / 2).toFixed(1)}px;width:${hw}px;height:${hh.toFixed(1)}px">${MASS}</svg>`
        + `<svg aria-hidden="true" width="${svgW}" height="${th}" style="position:absolute;left:0;top:0">${arrow(left + tw + 3, cy, hx - 3)}${arrow(hx + hw + 3, cy, hx + hw + gap - 3)}</svg>`
        + `</div><div class="meta" style="margin-top:10px">Big tiles: measured (Electricity split by circuit, by what each draws now). Hatched: no meter yet, or offline.</div></div>`;
    }
  }

  // ====================================================================================================================
  // rt-claude-card: Claude by room
  // ====================================================================================================================
  class RtClaude extends RtCard {
    defaults() { return { rooms: [{ name: "Greenhouse", sub: "Maag's agents on the Jetson", agents: "sensor.greenhouse_llm_status", host: "sensor.greenhouse_supervisor_status" }],
      idle: null }; }
    watch() { return this._c.rooms.flatMap(r => [r.agents, r.host, r.cpu, r.gpu, r.mem].filter(Boolean)); }
    render() {
      const c = this._c, h = this._h, W = this._w, wide = W >= 900, k = this._k || "cpu";
      const when = iso => { const d = new Date(iso); return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + ", " + time(d); };
      const rooms = c.rooms.map(r => {
        const ag = h.states[r.agents], ho = h.states[r.host];
        const v = { cpu: num(h.states[r.cpu]), gpu: num(h.states[r.gpu]), mem: num(h.states[r.mem]) };
        const on = ag && ["running", "online"].includes(ag.state) && (v.cpu != null || v.gpu != null || v.mem != null);
        const note = [ag ? `${ag.state === "unavailable" ? "not reporting" : ag.state} since ${when(ag.last_changed)}` : null,
          ho && ["offline", "unavailable"].includes(ho.state) ? `the Jetson offline since ${when(ho.last_changed)}` : null].filter(Boolean).join("; ");
        return Object.assign({}, r, { on, v, note });
      });
      const live = rooms.filter(r => r.on);
      const areas = Object.values(h.areas || {}).map(a => a.name).filter(n => !c.rooms.some(r => r.name.toLowerCase() === String(n).toLowerCase()) && !/floor/i.test(n));
      const big = wide ? 34 : 26;
      let tiles;
      if (!live.length) {
        const off = rooms.map(r => `${r.sub}: ${r.note}.`).join(" ");
        tiles = `<div style="background:${C.tile[1]};padding:10px 12px 12px"><div class="lab" style="font-size:10px;color:${C.text}">Claude in the house</div>`
          + `<div style="padding-top:10px;font:300 ${big}px/1.05 ${SANS};color:${C.muted}">Offline</div><div class="meta" style="font-size:10px;margin-top:4px;line-height:1.4">${esc(off)}</div></div>`;
      } else {
        const sum = key => live.reduce((a, r) => a + (r.v[key] || 0), 0);
        tiles = `<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px">` + [["Memory used by Claude", fix(sum("mem"), 1), "%"], ["CPU used by Claude", fix(sum("cpu"), 1), "%"], ["GPU used by Claude", fix(sum("gpu"), 1), "%"]]
          .map(([l, v, u]) => `<div style="background:${C.tile[3]};padding:10px 12px 12px;min-height:${wide ? 104 : 96}px;display:flex;flex-direction:column"><div class="lab" style="font-size:10px;color:${C.text};white-space:normal">${l}</div>`
            + `<div style="margin-top:auto;padding-top:10px;font:300 ${big}px/1.05 ${SANS};color:${C.ink}">${v}<span style="font-size:${wide ? 14 : 12}px;color:${C.muted};margin-left:3px">${u}</span></div></div>`).join("") + `</div>`;
      }
      const head = `<div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:12px"><div class="meta">Home Assistant · read at <b>${esc(time(new Date()))}</b></div><div class="lab" style="flex:none">By room</div></div>`;
      const size = wide ? 200 : 184, cc = size / 2, R = cc - 2, r0 = R * 0.64, name = { cpu: "CPU", gpu: "GPU", mem: "Memory" }[k];
      let ring;
      if (!live.length) {
        ring = `<circle cx="${cc}" cy="${cc}" r="${((R + r0) / 2).toFixed(1)}" fill="none" stroke="${C.line}" stroke-width="${(R - r0).toFixed(1)}" stroke-opacity=".35"/>`
          + `<circle cx="${cc}" cy="${cc}" r="${R.toFixed(1)}" fill="none" stroke="${C.line}" stroke-width="1" stroke-dasharray="3 4"/><circle cx="${cc}" cy="${cc}" r="${r0.toFixed(1)}" fill="none" stroke="${C.line}" stroke-width="1" stroke-dasharray="3 4"/>`;
      } else {
        const tot = Math.max(100, live.reduce((a, r) => a + (r.v[k] || 0), 0)); let an = 0; ring = "";
        live.forEach((r, i) => { const v = r.v[k] || 0; if (v <= 0) return; const a1 = an + v / tot * 2 * Math.PI;
          const p = (rr, a) => `${(cc + rr * Math.sin(a)).toFixed(2)} ${(cc - rr * Math.cos(a)).toFixed(2)}`, bg = a1 - an > Math.PI ? 1 : 0;
          ring += `<path d="M${p(R, an)} A${R} ${R} 0 ${bg} 1 ${p(R, a1)} L${p(r0, a1)} A${r0} ${r0} 0 ${bg} 0 ${p(r0, an)} Z" fill="${["#C9CBCF", "#8E9096", "#5D5F66"][i % 3]}" stroke="${C.raised}"/>`; an = a1; });
      }
      const centre = live.length ? `${fix(live.reduce((a, r) => a + (r.v[k] || 0), 0), 1)} %` : "Offline";
      const svg = `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" role="img" aria-label="${name}: Claude ${centre}">${ring}`
        + `<circle cx="${cc}" cy="${cc}" r="${(r0 - 7).toFixed(1)}" fill="none" stroke="${C.ink}" stroke-width="1"/>`
        + `<text x="${cc}" y="${(cc - R * 0.2).toFixed(1)}" text-anchor="middle" style="font:400 10px ${MONO};letter-spacing:.05em;fill:${C.muted}">CLAUDE</text>`
        + `<text x="${cc}" y="${(cc + R * 0.1).toFixed(1)}" text-anchor="middle" style="font:300 ${Math.round(R * (live.length ? 0.26 : 0.2))}px ${SANS};fill:${live.length ? C.ink : C.muted}">${centre}</text>`
        + `<text x="${cc}" y="${(cc + R * 0.1 + 16).toFixed(1)}" text-anchor="middle" style="font:400 10px ${MONO};letter-spacing:.05em;fill:${C.muted}">OF ${name.toUpperCase()}</text></svg>`;
      const legend = `<ul style="list-style:none;margin:0;padding:0;display:grid;gap:7px">` + rooms.map((r, i) => {
        const sw = r.on ? `<span style="width:10px;height:10px;background:${["#C9CBCF", "#8E9096", "#5D5F66"][i % 3]}"></span>` : `<span style="width:10px;height:10px;box-shadow:inset 0 0 0 1px ${C.line}"></span>`;
        const col = r.on ? C.ink : C.muted;
        return `<li style="display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:10px;align-items:center;font:400 13px/1.3 ${SANS};color:${col}">${sw}<span style="min-width:0">${esc(r.name)} <span style="color:${C.muted}">· ${esc(r.sub)}</span></span>`
          + `<span style="font:400 12px ${MONO};color:${col}">${r.on ? fix(r.v[k], 1) + " %" : "Offline"}</span></li>`;
      }).join("") + `</ul>`;
      const seg = `<div class="seg" role="group" aria-label="Show" style="width:210px;flex:none">` + [["cpu", "CPU"], ["gpu", "GPU"], ["mem", "Memory"]].map(([o, l]) =>
        `<button type="button" style="height:34px;font-size:12px" aria-pressed="${o === k}" data-act="k" data-arg="${o}">${l}</button>`).join("") + `</div>`;
      const top = `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px"><div class="lab">Usage</div>${seg}</div>`;
      const usage = wide ? `${top}<div style="display:grid;grid-template-columns:${size}px minmax(0,1fr);gap:28px;align-items:center"><div>${svg}</div><div>${legend}</div></div>`
        : `${top}<div style="display:grid;place-items:center">${svg}</div><div style="margin-top:14px">${legend}</div>`;
      const idle = `<div class="meta" style="margin-top:12px">Nothing from Claude in ${esc((c.idle || areas).join(", "))}.</div>`;
      if (wide) return `<div class="panel"><div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:40px;align-items:start"><div>${head}${tiles}${idle}</div><div>${usage}</div></div></div>`;
      return `<div class="panel">${head}${tiles}<div style="margin-top:18px">${usage}</div>${idle}</div>`;
    }
    act(kind, arg) { if (kind === "k") { this._k = arg; this._schedule(); } }
  }

  // ====================================================================================================================
  // rt-camera-card: the picture, or why there is none
  // ====================================================================================================================
  class RtCamera extends RtCard {
    defaults() { return { entity: null, name: null, height: null, camera_view: "live" }; }
    watch() { return [this._c.entity]; }
    css() { return `
      .frame { position: relative; border: 1px solid ${C.rule}; background: ${C.raised}; display: flex; flex-direction: column; height: 100%; }
      .pic { position: relative; flex: 1 1 auto; background: linear-gradient(160deg, #17191D 0%, #0B0C0E 55%, #121316 100%); overflow: hidden; }
      .why { position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); display: grid; gap: 6px; justify-items: center; text-align: center; padding: 0 16px; }
      .word { display: inline-flex; align-items: center; gap: 7px; font: 400 13px/1.3 ${SANS}; color: ${C.muted}; }
      .name { height: 40px; display: grid; place-items: center; border-top: 1px solid ${C.rule}; font: 400 14px/1 ${SANS}; color: ${C.ink}; }
      .live { position: absolute; inset: 0; } .live > * { height: 100%; }
    `; }
    render() {
      const c = this._c, s = this._h.states[c.entity], H = c.height || (this._w < 560 ? 216 : 240);
      const name = c.name || (s && s.attributes.friendly_name) || c.entity;
      const down = !s || s.state === "unavailable";
      if (!down) {
        if (this._mode !== "live") { this._mode = "live"; return `<div class="frame"><div class="pic" style="height:${H}px"><div class="live"></div></div><div class="name">${esc(name)}</div></div>`; }
        return null;
      }
      this._mode = "down";
      if (this._why == null) this._reason();
      return `<div class="frame"><div class="pic" style="height:${H}px"><div class="why"><span class="word"><span class="dot none"></span>Unavailable</span>`
        + `<div class="meta">${esc(this._why || "Home Assistant can't reach it")}</div></div>${cornerTicks(C.muted)}</div><div class="name">${esc(name)}</div></div>`;
    }
    painted() {
      if (this._mode !== "live") { this._el = null; return; }
      const box = this.shadowRoot.querySelector(".live");
      if (!box) return;
      if (!this._el || !box.contains(this._el)) {
        window.loadCardHelpers && window.loadCardHelpers().then(hp => {
          this._el = hp.createCardElement({ type: "picture-entity", entity: this._c.entity, camera_view: this._c.camera_view, show_name: false, show_state: false });
          this._el.hass = this._h; box.innerHTML = ""; box.appendChild(this._el);
        });
      } else this._el.hass = this._h;
    }
    _reason() {
      this._why = "";
      const e = (this._h.entities || {})[this._c.entity];
      if (!e || !e.platform) return;
      this._h.callWS({ type: "config_entries/get", domain: e.platform }).then(list => {
        const bad = (list || []).find(x => x.state !== "loaded");
        if (!bad) return;
        const r = String(bad.reason || bad.state || "");
        this._why = /2005|auth|token|sign/i.test(r) ? "SwitchBot needs a new sign-in" : `The integration says: ${r.replace(/_/g, " ")}`;
        this._schedule();
      }).catch(() => {});
    }
  }

  // ====================================================================================================================
  // rt-logbook-card: what happened
  // ====================================================================================================================
  class RtLogbook extends RtCard {
    defaults() { return { entities: [], hours: 24, limit: 6 }; }
    watch() { return this._c.entities; }
    css() { return `.lb { display: flex; gap: 14px; align-items: baseline; padding: 10px 0; border-bottom: 1px solid ${C.rule}; } .lb .m { font: 400 14px/1.35 ${SANS}; color: ${C.text}; }`; }
    render() {
      if (!this._ev || Date.now() - this._evAt > 60e3 || this._evSig !== this._sig) this._load();
      if (!this._ev) return `<div class="panel"><div class="meta">Reading the logbook</div></div>`;
      const ev = this._ev.slice(0, this._c.limit);
      if (!ev.length) return `<div class="panel"><div class="lab" style="color:${C.ink}">Last ${this._c.hours} hours</div><div class="meta" style="margin-top:8px">Nothing happened.</div></div>`;
      let out = "", day = "";
      for (const e of ev) {
        const d = new Date(e.when * 1000), dn = d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
        if (dn !== day) { out += `${day ? "</div>" : ""}<div class="lab" style="color:${C.ink};${day ? "margin-top:14px" : ""}">${esc(dn)}</div><div style="margin-top:8px;border-top:1px solid ${C.strong}">`; day = dn; }
        out += `<div class="lb"><div class="lab" style="width:72px;flex:none">${esc(time(d))}</div><div class="m">${esc(this._msg(e))}</div></div>`;
      }
      return `<div class="panel">${out}</div></div>`;
    }
    _msg(e) {
      const s = this._h.states[e.entity_id], a = (s && s.attributes) || {}, name = a.friendly_name || e.name || e.entity_id, dom = e.entity_id.split(".")[0], st = e.state, dc = a.device_class;
      if (e.message && !st) return `${name} ${e.message}`;
      if (dom === "person" || dom === "device_tracker") return `${name} was detected ${st === "home" ? "at home" : st === "not_home" ? "away" : "at " + st}`;
      if (dom === "binary_sensor") {
        if (["door", "window", "opening", "garage_door"].includes(dc)) return `${name} was ${st === "on" ? "opened" : "closed"}`;
        if (["motion", "occupancy", "presence"].includes(dc)) return st === "on" ? `${name} detected motion` : `${name} cleared`;
        if (dc === "sound") return `${name} ${st === "on" ? "is sounding" : "stopped"}`;
        return `${name} turned ${st}`;
      }
      if (dom === "alarm_control_panel") return `${name} changed to ${cap(String(st).replace(/_/g, " "))}`;
      if (["input_boolean", "switch", "light", "siren", "automation"].includes(dom)) return `${name} turned ${st}`;
      return `${name} changed to ${String(st).replace(/_/g, " ")}`;
    }
    _load() {
      if (this._loading) return; this._loading = true; this._evSig = this._sig;
      const end = new Date(), start = new Date(end - this._c.hours * 3600e3);
      this._h.callWS({ type: "logbook/get_events", start_time: start.toISOString(), end_time: end.toISOString(), entity_ids: this._c.entities }).then(list => {
        this._ev = (list || []).filter(e => e.state != null || e.message).sort((a, b) => b.when - a.when);
        this._evAt = Date.now(); this._loading = false; this._schedule();
      }).catch(() => { this._loading = false; });
    }
  }

  // ====================================================================================================================
  // rt-remote-card: the TV
  // ====================================================================================================================
  const arrowSvg = (dir, color, size) => `<svg aria-hidden="true" width="${size}" height="${size}" viewBox="0 0 18 18" style="transform:rotate(${{ up: 0, right: 90, down: 180, left: 270 }[dir]}deg)"><path d="M9 16 V2 M3.5 7.5 L9 2 L14.5 7.5" fill="none" stroke="${color}" stroke-width="1"/></svg>`;
  class RtRemote extends RtCard {
    defaults() { return { remote: "remote.tv1_2", media_player: "media_player.tv1_2", name: "TV1", width: null }; }
    watch() { return [this._c.remote, this._c.media_player]; }
    css() { return `
      .g { display: grid; gap: 8px; } .g .btn { width: 100%; height: 44px; font-size: 13px; padding: 0 6px; }
      .pad { position: relative; margin: 0 auto; border-radius: 50%; border: 1px solid ${C.line}; }
      .pad button { position: absolute; width: 56px; height: 56px; display: grid; place-items: center; background: none; border: 0; padding: 0; cursor: pointer; }
      .pad .ok { border-radius: 50%; border: 1px solid ${C.ink}; background: ${C.ground}; font: 400 13px/1 ${MONO}; letter-spacing: .1em; color: ${C.ink}; }
    `; }
    render() {
      const c = this._c, mp = this._h.states[c.media_player], on = mp && mp.state !== "off" && mp.state !== "unavailable";
      const W = Math.min(this._c.width || (this._w >= 700 ? 460 : this._w), this._w);
      const b = (t, k, extra = "") => `<button class="btn${extra}" data-act="key" data-arg="${k}">${t}</button>`;
      const d = Math.min(240, W - 80), r = d / 2, m = 36, inner = 80;
      const ar = (dir, x, y, k, lab) => `<button style="left:${x - 28}px;top:${y - 28}px" aria-label="${lab}" data-act="key" data-arg="${k}">${arrowSvg(dir, C.ink, 20)}</button>`;
      const pad = `<div class="pad" style="width:${d}px;height:${d}px">${ar("up", r, m, "KEY_UP", "Up")}${ar("down", r, d - m, "KEY_DOWN", "Down")}${ar("left", m, r, "KEY_LEFT", "Left")}${ar("right", d - m, r, "KEY_RIGHT", "Right")}`
        + `<button class="ok" style="left:${r - inner / 2}px;top:${r - inner / 2}px;width:${inner}px;height:${inner}px" data-act="key" data-arg="KEY_ENTER">OK</button></div>`;
      return `<div class="panel" style="padding:18px 16px 20px;width:${W}px;margin:0 auto">`
        + `<div style="font:300 22px/1 ${SANS};color:${C.ink};text-align:center">${esc(c.name)}</div>`
        + `<div class="g" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-top:18px">${b("Power", "POWER", on ? " on" : "")}${b("Source", "KEY_SOURCE")}${b("Home", "KEY_HOME")}${b("Menu", "KEY_MENU")}</div>`
        + `<div style="margin-top:22px">${pad}</div>`
        + `<div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-top:22px">${b("Back", "KEY_RETURN")}<span></span>${b("Info", "KEY_INFO")}</div>`
        + `<div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-top:10px">${b("Volume −", "KEY_VOLDOWN")}${b("Mute", "KEY_MUTE")}${b("Volume +", "KEY_VOLUP")}</div>`
        + `<div class="g" style="grid-template-columns:repeat(2,minmax(0,1fr));margin-top:10px">${b("Channel −", "KEY_CHDOWN")}${b("Channel +", "KEY_CHUP")}</div>`
        + `<div class="g" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-top:10px">${b("Rewind", "KEY_REWIND")}${b("Play", "KEY_PLAY")}${b("Forward", "KEY_FF")}</div></div>`;
    }
    act(kind, arg) {
      if (kind !== "key") return;
      if (arg === "POWER") return this.call("media_player", "toggle", { entity_id: this._c.media_player });
      return this.call("remote", "send_command", { entity_id: this._c.remote, command: arg });
    }
  }

  const defs = [["rt-thermostat-card", RtThermostat, "Red Tower thermostat"], ["rt-line-card", RtLine, "Red Tower chart"], ["rt-weather-card", RtWeather, "Red Tower weather"],
    ["rt-energy-card", RtEnergy, "Red Tower electricity"], ["rt-io-card", RtIO, "Red Tower in and out"], ["rt-claude-card", RtClaude, "Red Tower Claude by room"],
    ["rt-camera-card", RtCamera, "Red Tower camera"], ["rt-logbook-card", RtLogbook, "Red Tower logbook"], ["rt-remote-card", RtRemote, "Red Tower TV remote"]];
  window.customCards = window.customCards || [];
  for (const [tag, cls, name] of defs) {
    if (!customElements.get(tag)) customElements.define(tag, cls);
    if (!window.customCards.find(c => c.type === tag)) window.customCards.push({ type: tag, name, description: "Red Tower, in Vittorio's style" });
  }
})();
