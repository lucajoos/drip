const MAX_SCHEDULES = 16;
  const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const ZONES = ["herbs", "beds"];

  const STRINGS = {
    de: {
      title: "Gießpläne",
      add: "Plan hinzufügen",
      empty: "Noch keine Gießpläne",
      emptyHint: "Lege den ersten Plan an, damit automatisch gegossen wird.",
      missing: "Kein Drip-Schedule-Sensor gefunden. Entity in der Kartenkonfiguration setzen.",
      newTitle: "Neuer Plan",
      editTitle: "Plan bearbeiten",
      zone: "Zone",
      herbs: "Kräuter",
      beds: "Beete",
      time: "Uhrzeit",
      duration: "Dauer",
      minutes: "min",
      rhythm: "Rhythmus",
      daily: "Täglich",
      everyNDays: "Alle n Tage",
      weekdays: "Wochentage",
      interval: "Intervall",
      everyN: (n) => "alle " + n + " Tage",
      intervalHint: (n) =>
        "Beginnt heute und wiederholt sich alle " + n + " Tage.",
      rainSkip: "Bei Regen überspringen",
      threshold: "Schwellwert",
      rainHint:
        "Übersprungen wird, wenn Regen der letzten 24 Stunden plus Vorhersage der nächsten 12 Stunden über dem Schwellwert liegt. Ist die Wetter-API nicht erreichbar, wird trotzdem gegossen.",
      enabled: "Aktiv",
      save: "Sichern",
      cancel: "Abbrechen",
      delete: "Löschen",
      deleteConfirm: "Diesen Plan wirklich löschen?",
      full: "Maximale Anzahl Pläne erreicht (16).",
      weekdaysHint: "Mindestens einen Wochentag wählen.",
      nextRun: "nächster Lauf",
      mm: "mm",
      fromMm: (v) => "ab " + formatMm(v) + " mm",
      sun: "Sonntag",
      mon: "Montag",
      tue: "Dienstag",
      wed: "Mittwoch",
      thu: "Donnerstag",
      fri: "Freitag",
      sat: "Samstag",
      sunShort: "So",
      monShort: "Mo",
      tueShort: "Di",
      wedShort: "Mi",
      thuShort: "Do",
      friShort: "Fr",
      satShort: "Sa",
    },
    en: {
      title: "Schedules",
      add: "Add schedule",
      empty: "No watering schedules yet",
      emptyHint: "Create the first schedule so watering runs automatically.",
      missing: "No Drip schedules sensor found. Set the entity in the card config.",
      newTitle: "New schedule",
      editTitle: "Edit schedule",
      zone: "Zone",
      herbs: "Herbs",
      beds: "Beds",
      time: "Time",
      duration: "Duration",
      minutes: "min",
      rhythm: "Repeat",
      daily: "Daily",
      everyNDays: "Every n days",
      weekdays: "Weekdays",
      interval: "Interval",
      everyN: (n) => "every " + n + " days",
      intervalHint: (n) => "Starts today and repeats every " + n + " days.",
      rainSkip: "Skip when raining",
      threshold: "Threshold",
      rainHint:
        "Skipped when rain in the last 24 hours plus the next 12 hours exceeds the threshold. If weather is unreachable, watering still runs.",
      enabled: "Enabled",
      save: "Save",
      cancel: "Cancel",
      delete: "Delete",
      deleteConfirm: "Delete this schedule?",
      full: "Maximum number of schedules reached (16).",
      weekdaysHint: "Pick at least one weekday.",
      nextRun: "next run",
      mm: "mm",
      fromMm: (v) => "from " + formatMm(v) + " mm",
      sun: "Sunday",
      mon: "Monday",
      tue: "Tuesday",
      wed: "Wednesday",
      thu: "Thursday",
      fri: "Friday",
      sat: "Saturday",
      sunShort: "Su",
      monShort: "Mo",
      tueShort: "Tu",
      wedShort: "We",
      thuShort: "Th",
      friShort: "Fr",
      satShort: "Sa",
    },
  };

  function t(hass) {
    const lang = ((hass && hass.language) || "en").toLowerCase();
    return lang.startsWith("de") ? STRINGS.de : STRINGS.en;
  }

  function formatMm(value) {
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return n % 1 === 0 ? String(n) : n.toFixed(1);
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function findSchedulesEntity(hass, configured) {
    if (configured && hass.states[configured]) return configured;
    if (!hass || !hass.states) return configured || null;
    const match = Object.keys(hass.states).find((id) => {
      if (!id.startsWith("sensor.")) return false;
      return Array.isArray(hass.states[id].attributes.schedules);
    });
    return match || configured || null;
  }

  function rhythmSummary(schedule, s) {
    if (schedule.rhythm === "every_n_days") {
      return s.everyN(schedule.n || 1);
    }
    if (schedule.rhythm === "weekdays") {
      const days = WEEKDAYS.filter((d) => (schedule.weekdays || []).includes(d));
      return days.map((d) => s[d + "Short"]).join(", ") || s.weekdays;
    }
    return s.daily;
  }

  function formatNextRun(iso, hass) {
    if (!iso) return "";
    const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    if (!m) return iso;
    const dt = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
    const lang = (hass && hass.locale && hass.locale.language) || (hass && hass.language) || undefined;
    return dt.toLocaleString(lang, {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function defaultForm() {
    return {
      zone: "herbs",
      time: "06:00",
      duration_min: 10,
      rhythm: "daily",
      n: 2,
      weekdays: [],
      rain_skip_enabled: false,
      rain_skip_threshold_mm: 5,
      enabled: true,
    };
  }

  function formFromSchedule(schedule) {
    const rain = schedule.rainSkip || {};
    return {
      zone: schedule.zone || "herbs",
      time: String(schedule.time || "06:00").slice(0, 5),
      duration_min: Number(schedule.durationMin) || 10,
      rhythm: schedule.rhythm || "daily",
      n: Number(schedule.n) || 2,
      weekdays: Array.isArray(schedule.weekdays) ? schedule.weekdays.slice() : [],
      rain_skip_enabled: Boolean(rain.enabled),
      rain_skip_threshold_mm: Number(rain.thresholdMm) || 5,
      enabled: schedule.enabled !== false,
    };
  }

  function normalizeTime(value) {
    const m = String(value || "").match(/^(\d{1,2}):(\d{2})/);
    if (!m) return "06:00";
    const h = Math.min(23, Number(m[1]));
    const min = Math.min(59, Number(m[2]));
    return String(h).padStart(2, "0") + ":" + String(min).padStart(2, "0");
  }

  function servicePayload(form) {
    const data = {
      zone: form.zone,
      time: normalizeTime(form.time),
      duration_min: Number(form.duration_min),
      rhythm: form.rhythm,
      enabled: Boolean(form.enabled),
      rain_skip_enabled: Boolean(form.rain_skip_enabled),
      rain_skip_threshold_mm: Number(form.rain_skip_threshold_mm),
    };
    if (form.rhythm === "every_n_days") data.n = Number(form.n) || 1;
    if (form.rhythm === "weekdays") data.weekdays = form.weekdays.slice();
    return data;
  }

  const CSS = `
    :host { display: block; }
    ha-card { overflow: hidden; }
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 16px 8px;
      font-size: 18px;
      font-weight: 500;
    }
    .body { padding: 0 0 8px; }
    .section-title {
      padding: 12px 16px 4px;
      font-size: 12px;
      font-weight: 500;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--secondary-text-color);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 16px;
      cursor: pointer;
    }
    .row:hover { background: var(--secondary-background-color, rgba(0,0,0,0.04)); }
    .row.disabled { opacity: 0.55; }
    .row-main { flex: 1; min-width: 0; }
    .time {
      font-size: 22px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
      line-height: 1.2;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 6px;
      margin-top: 3px;
      color: var(--secondary-text-color);
      font-size: 13px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 1px 7px;
      border-radius: 999px;
      background: rgba(0, 150, 136, 0.16);
      color: #00897b;
      font-size: 12px;
      font-weight: 500;
    }
    .switch { position: relative; display: inline-block; width: 36px; height: 22px; flex-shrink: 0; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; inset: 0;
      background: var(--switch-unchecked-button-color, #9e9e9e);
      border-radius: 22px;
      cursor: pointer;
      transition: 0.15s;
    }
    .slider:before {
      content: "";
      position: absolute;
      height: 18px; width: 18px;
      left: 2px; bottom: 2px;
      background: white;
      border-radius: 50%;
      transition: 0.15s;
    }
    .switch input:checked + .slider { background: var(--switch-checked-button-color, var(--primary-color)); }
    .switch input:checked + .slider:before { transform: translateX(14px); }
    .empty { padding: 24px 16px 16px; text-align: center; color: var(--secondary-text-color); }
    .empty h3 { margin: 0 0 6px; color: var(--primary-text-color); font-weight: 500; }
    .empty p { margin: 0 0 16px; font-size: 14px; }
    .footer { padding: 4px 12px 12px; }
    button.action, button.link, button.seg, button.day, button.danger {
      font: inherit;
      cursor: pointer;
    }
    button.action {
      width: 100%;
      border: none;
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-radius: 8px;
      padding: 10px 14px;
      font-weight: 500;
    }
    button.action[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.link {
      border: none;
      background: transparent;
      color: var(--primary-color);
      padding: 8px 12px;
    }
    button.danger {
      border: none;
      background: transparent;
      color: var(--error-color, #db4437);
      padding: 8px 12px;
    }
    .overlay {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 10000;
      background: rgba(0,0,0,0.45);
      align-items: flex-end;
      justify-content: center;
    }
    .overlay.open { display: flex; }
    .dialog {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      width: min(520px, 100%);
      max-height: 92vh;
      overflow: auto;
      border-radius: 12px 12px 0 0;
      box-shadow: 0 -8px 32px rgba(0,0,0,0.25);
    }
    @media (min-width: 600px) {
      .overlay { align-items: center; }
      .dialog { border-radius: 12px; max-height: 86vh; }
    }
    .dlg-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 16px;
      border-bottom: 1px solid var(--divider-color);
      font-weight: 500;
      font-size: 16px;
    }
    .dlg-body { padding: 8px 16px 20px; }
    .field { margin: 14px 0; }
    .field label.lbl {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-bottom: 6px;
    }
    .field input[type="time"],
    .field input[type="number"] {
      width: 100%;
      box-sizing: border-box;
      font: inherit;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color);
      color: var(--primary-text-color);
    }
    .seg {
      display: flex;
      gap: 4px;
      background: var(--secondary-background-color, rgba(0,0,0,0.06));
      padding: 3px;
      border-radius: 10px;
    }
    button.seg {
      flex: 1;
      border: none;
      background: transparent;
      color: var(--primary-text-color);
      border-radius: 8px;
      padding: 8px 6px;
      font-size: 13px;
    }
    button.seg.active {
      background: var(--card-background-color, #fff);
      box-shadow: 0 1px 3px rgba(0,0,0,0.15);
      font-weight: 500;
    }
    .days { display: flex; flex-direction: column; gap: 2px; }
    button.day {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      border: none;
      background: transparent;
      color: var(--primary-text-color);
      padding: 8px 4px;
      text-align: left;
    }
    button.day .check { color: var(--primary-color); font-weight: 700; }
    .hint { font-size: 12px; color: var(--secondary-text-color); margin-top: 6px; }
    .error { color: var(--error-color, #db4437); font-size: 13px; margin: 8px 0; }
    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .dlg-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
    }
    .dlg-actions .right { display: flex; gap: 4px; }
  `;

  class DripSchedulesCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._hass = null;
      this._config = {};
      this._entity = null;
      this._schedulesJson = null;
      this._dialog = null;
      this._form = defaultForm();
      this._saving = false;
      this._error = null;
      this._confirmDelete = false;
      this._built = false;
    }

    static getStubConfig(hass) {
      const entity = findSchedulesEntity(hass);
      return entity ? { entity } : {};
    }

    setConfig(config) {
      this._config = config || {};
      this._entity = this._config.entity || null;
      this._schedulesJson = null;
      if (this._hass) this._ensureDom();
    }

    set hass(hass) {
      this._hass = hass;
      const entity = findSchedulesEntity(hass, this._config.entity);
      this._entity = entity;
      const schedules = (entity && hass.states[entity] && hass.states[entity].attributes.schedules) || [];
      const json = JSON.stringify(schedules);
      this._ensureDom();
      if (json !== this._schedulesJson) {
        this._schedulesJson = json;
        this._renderList();
      }
    }

    getCardSize() {
      const n = this._schedules().length;
      return Math.max(3, 2 + n);
    }

    _schedules() {
      if (!this._hass || !this._entity) return [];
      const state = this._hass.states[this._entity];
      return (state && Array.isArray(state.attributes.schedules) && state.attributes.schedules) || [];
    }

    _serviceData(extra) {
      const data = Object.assign({}, extra);
      if (this._config.entry_id) data.entry_id = this._config.entry_id;
      return data;
    }

    _ensureDom() {
      if (this._built) return;
      this._built = true;
      this.shadowRoot.innerHTML =
        "<style>" + CSS + "</style>" +
        "<ha-card>" +
        '  <div class="header"><span class="title"></span></div>' +
        '  <div class="body"></div>' +
        '  <div class="footer"></div>' +
        "</ha-card>" +
        '<div class="overlay" part="overlay"></div>';

      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
      this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
      this.shadowRoot.addEventListener("input", (ev) => this._onInput(ev));
      this._renderList();
    }

    _onClick(ev) {
      if (ev.target.closest(".switch")) return;
      const actionEl = ev.target.closest("[data-action]");
      if (!actionEl) {
        if (ev.target.classList && ev.target.classList.contains("overlay")) this._closeDialog();
        return;
      }
      const action = actionEl.dataset.action;
      if (action === "add") this._openDialog("create");
      else if (action === "edit") this._openDialog("edit", Number(actionEl.dataset.id));
      else if (action === "close") this._closeDialog();
      else if (action === "save") this._save();
      else if (action === "delete") this._delete();
      else if (action === "zone") this._setForm("zone", actionEl.dataset.value);
      else if (action === "rhythm") this._setForm("rhythm", actionEl.dataset.value);
      else if (action === "day") this._toggleDay(actionEl.dataset.value);
    }

    _onChange(ev) {
      const el = ev.target;
      if (el.dataset.field === "enabled_row") {
        ev.stopPropagation();
        this._toggleEnabled(Number(el.dataset.id), el.checked);
        return;
      }
      this._readFormField(el);
    }

    _onInput(ev) {
      this._readFormField(ev.target);
    }

    _readFormField(el) {
      if (!el || !el.dataset.field || !this._dialog) return;
      const field = el.dataset.field;
      if (field === "enabled_row") return;
      if (el.type === "checkbox") this._form[field] = el.checked;
      else if (el.type === "number") this._form[field] = Number(el.value);
      else this._form[field] = el.value;
      if (field === "rhythm" || field === "rain_skip_enabled") this._renderDialog();
    }

    _setForm(field, value) {
      this._form[field] = value;
      this._renderDialog();
    }

    _toggleDay(day) {
      const set = new Set(this._form.weekdays);
      if (set.has(day)) set.delete(day);
      else set.add(day);
      this._form.weekdays = WEEKDAYS.filter((d) => set.has(d));
      this._renderDialog();
    }

    _openDialog(mode, id) {
      const s = this._schedules();
      if (mode === "create") {
        this._form = defaultForm();
        this._dialog = { mode: "create" };
      } else {
        const schedule = s.find((item) => item.id === id);
        if (!schedule) return;
        this._form = formFromSchedule(schedule);
        this._dialog = { mode: "edit", id: schedule.id };
      }
      this._error = null;
      this._confirmDelete = false;
      this._saving = false;
      this._renderDialog();
    }

    _closeDialog() {
      this._dialog = null;
      this._error = null;
      this._confirmDelete = false;
      this._renderDialog();
    }

    async _toggleEnabled(id, enabled) {
      if (!this._hass) return;
      try {
        await this._hass.callService(
          "drip",
          "set_schedule_enabled",
          this._serviceData({ schedule_id: id, enabled: enabled })
        );
      } catch (err) {
        this._schedulesJson = null;
        this._renderList();
      }
    }

    async _save() {
      if (!this._hass || !this._dialog || this._saving) return;
      const s = t(this._hass);
      if (this._form.rhythm === "weekdays" && this._form.weekdays.length === 0) {
        this._error = s.weekdaysHint;
        this._renderDialog();
        return;
      }
      this._saving = true;
      this._error = null;
      this._renderDialog();
      const payload = servicePayload(this._form);
      try {
        if (this._dialog.mode === "edit") {
          await this._hass.callService(
            "drip",
            "update_schedule",
            this._serviceData(Object.assign({ schedule_id: this._dialog.id }, payload))
          );
        } else {
          await this._hass.callService(
            "drip",
            "create_schedule",
            this._serviceData(payload)
          );
        }
        this._closeDialog();
      } catch (err) {
        this._error = (err && (err.message || err.body && err.body.message)) || String(err);
        this._saving = false;
        this._renderDialog();
      }
    }

    async _delete() {
      if (!this._hass || !this._dialog || this._dialog.mode !== "edit") return;
      if (!this._confirmDelete) {
        this._confirmDelete = true;
        this._renderDialog();
        return;
      }
      this._saving = true;
      this._error = null;
      this._renderDialog();
      try {
        await this._hass.callService(
          "drip",
          "delete_schedule",
          this._serviceData({ schedule_id: this._dialog.id })
        );
        this._closeDialog();
      } catch (err) {
        this._error = (err && (err.message || err.body && err.body.message)) || String(err);
        this._saving = false;
        this._renderDialog();
      }
    }

    _renderList() {
      if (!this._built) return;
      const s = t(this._hass);
      this.shadowRoot.querySelector(".title").textContent = s.title;
      const body = this.shadowRoot.querySelector(".body");
      const footer = this.shadowRoot.querySelector(".footer");
      const schedules = this._schedules();

      if (!this._entity) {
        body.innerHTML = '<div class="empty"><p>' + escapeHtml(s.missing) + "</p></div>";
        footer.innerHTML = "";
        return;
      }

      if (schedules.length === 0) {
        body.innerHTML =
          '<div class="empty"><h3>' +
          escapeHtml(s.empty) +
          "</h3><p>" +
          escapeHtml(s.emptyHint) +
          "</p></div>";
      } else {
        let html = "";
        ZONES.forEach((zone) => {
          const items = schedules.filter((item) => item.zone === zone);
          if (!items.length) return;
          html += '<div class="section-title">' + escapeHtml(s[zone]) + "</div>";
          items.forEach((item) => {
            const parts = [rhythmSummary(item, s), item.durationMin + " " + s.minutes];
            if (item.enabled && item.nextRun) {
              parts.push(s.nextRun + " " + formatNextRun(item.nextRun, this._hass));
            }
            const rain = item.rainSkip || {};
            html +=
              '<div class="row' +
              (item.enabled ? "" : " disabled") +
              '" data-action="edit" data-id="' +
              escapeHtml(item.id) +
              '">' +
              '<div class="row-main">' +
              '<div class="time">' +
              escapeHtml(item.time) +
              "</div>" +
              '<div class="meta"><span>' +
              escapeHtml(parts.join(" · ")) +
              "</span>" +
              (rain.enabled
                ? '<span class="badge">' + escapeHtml(s.fromMm(rain.thresholdMm)) + "</span>"
                : "") +
              "</div></div>" +
              '<label class="switch" onclick="event.stopPropagation()">' +
              '<input type="checkbox" data-field="enabled_row" data-id="' +
              escapeHtml(item.id) +
              '"' +
              (item.enabled ? " checked" : "") +
              " />" +
              '<span class="slider"></span></label></div>';
          });
        });
        body.innerHTML = html;
      }

      const full = schedules.length >= MAX_SCHEDULES;
      footer.innerHTML =
        '<button class="action" data-action="add"' +
        (full ? " disabled" : "") +
        " title=\"" +
        escapeHtml(full ? s.full : s.add) +
        '">' +
        escapeHtml(s.add) +
        "</button>";
    }

    _renderDialog() {
      const overlay = this.shadowRoot.querySelector(".overlay");
      if (!overlay) return;
      if (!this._dialog) {
        overlay.classList.remove("open");
        overlay.innerHTML = "";
        return;
      }
      const s = t(this._hass);
      const f = this._form;
      const editing = this._dialog.mode === "edit";
      const title = editing ? s.editTitle : s.newTitle;

      const seg = (action, value, label, current) =>
        '<button type="button" class="seg' +
        (current === value ? " active" : "") +
        '" data-action="' +
        action +
        '" data-value="' +
        value +
        '">' +
        escapeHtml(label) +
        "</button>";

      let extra = "";
      if (f.rhythm === "every_n_days") {
        extra +=
          '<div class="field"><label class="lbl">' +
          escapeHtml(s.interval) +
          '</label><input type="number" min="1" max="30" data-field="n" value="' +
          escapeHtml(f.n) +
          '" /><div class="hint">' +
          escapeHtml(s.intervalHint(f.n || 2)) +
          "</div></div>";
      }
      if (f.rhythm === "weekdays") {
        extra += '<div class="field"><label class="lbl">' + escapeHtml(s.weekdays) + '</label><div class="days">';
        WEEKDAYS.forEach((day) => {
          const on = f.weekdays.includes(day);
          extra +=
            '<button type="button" class="day" data-action="day" data-value="' +
            day +
            '"><span>' +
            escapeHtml(s[day]) +
            "</span><span class=\"check\">" +
            (on ? "✓" : "") +
            "</span></button>";
        });
        extra += "</div></div>";
      }

      overlay.innerHTML =
        '<div class="dialog" role="dialog" aria-modal="true">' +
        '<div class="dlg-head"><span>' +
        escapeHtml(title) +
        '</span><button type="button" class="link" data-action="close">' +
        escapeHtml(s.cancel) +
        "</button></div>" +
        '<div class="dlg-body">' +
        '<div class="field"><label class="lbl">' +
        escapeHtml(s.zone) +
        '</label><div class="seg">' +
        seg("zone", "herbs", s.herbs, f.zone) +
        seg("zone", "beds", s.beds, f.zone) +
        "</div></div>" +
        '<div class="field"><label class="lbl">' +
        escapeHtml(s.time) +
        '</label><input type="time" data-field="time" value="' +
        escapeHtml(normalizeTime(f.time)) +
        '" /></div>' +
        '<div class="field"><label class="lbl">' +
        escapeHtml(s.duration) +
        '</label><input type="number" min="1" max="45" data-field="duration_min" value="' +
        escapeHtml(f.duration_min) +
        '" />' +
        '<div class="hint">' +
        escapeHtml("1–45 " + s.minutes) +
        "</div></div>" +
        '<div class="field"><label class="lbl">' +
        escapeHtml(s.rhythm) +
        '</label><div class="seg">' +
        seg("rhythm", "daily", s.daily, f.rhythm) +
        seg("rhythm", "every_n_days", s.everyNDays, f.rhythm) +
        seg("rhythm", "weekdays", s.weekdays, f.rhythm) +
        "</div></div>" +
        extra +
        '<div class="field"><div class="toggle-row"><span>' +
        escapeHtml(s.rainSkip) +
        '</span><label class="switch"><input type="checkbox" data-field="rain_skip_enabled"' +
        (f.rain_skip_enabled ? " checked" : "") +
        ' /><span class="slider"></span></label></div>' +
        (f.rain_skip_enabled
          ? '<div class="field"><label class="lbl">' +
            escapeHtml(s.threshold) +
            '</label><input type="number" min="0.1" max="100" step="0.5" data-field="rain_skip_threshold_mm" value="' +
            escapeHtml(f.rain_skip_threshold_mm) +
            '" /><div class="hint">' +
            escapeHtml(s.rainHint) +
            "</div></div>"
          : '<div class="hint">' + escapeHtml(s.rainHint) + "</div>") +
        "</div>" +
        (editing
          ? '<div class="field"><div class="toggle-row"><span>' +
            escapeHtml(s.enabled) +
            '</span><label class="switch"><input type="checkbox" data-field="enabled"' +
            (f.enabled ? " checked" : "") +
            ' /><span class="slider"></span></label></div></div>'
          : "") +
        (this._error ? '<div class="error">' + escapeHtml(this._error) + "</div>" : "") +
        '<div class="dlg-actions">' +
        (editing
          ? '<button type="button" class="danger" data-action="delete">' +
            escapeHtml(this._confirmDelete ? s.deleteConfirm : s.delete) +
            "</button>"
          : "<span></span>") +
        '<div class="right"><button type="button" class="action" data-action="save"' +
        (this._saving ? " disabled" : "") +
        ">" +
        escapeHtml(s.save) +
        "</button></div></div></div></div>";
      overlay.classList.add("open");
    }
  }

  if (!customElements.get("drip-schedules-card")) {
    customElements.define("drip-schedules-card", DripSchedulesCard);
  }

  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === "drip-schedules-card")) {
    window.customCards.push({
      type: "drip-schedules-card",
      name: "Drip Gießpläne",
      description: "Pläne anlegen, bearbeiten, ein-/ausschalten und löschen",
      preview: false,
    });
  }
