/* ECE:4880 Lab 1 -- PC user interface.
 *
 * Polls the server once a second, paints the two large readouts and the
 * 300-second chart recorder, and edits the alert settings.
 *
 * Unit handling: the server speaks Celsius and only Celsius. Every conversion
 * to Fahrenheit happens here, on the way to the screen, and every value typed
 * in Fahrenheit is converted back before it is sent. One canonical unit on the
 * wire is the cheapest defence against unit-mixing bugs.
 */

// ---------------------------------------------------------------------------
// Constants -- Requirement 5c.i fixes the graph limits, so they are not options.
// ---------------------------------------------------------------------------
const Y_MIN_C = 10;
const Y_MAX_C = 50;
const WINDOW_S = 300;
const POLL_MS = 1000;

const COLORS = {
  s1: '#4aa3ff',
  s2: '#ffb454',
  grid: '#2c3742',
  axis: '#8b98a5',
  missing: '#4a5560',
  offscale: '#f85149',
};

let unit = localStorage.getItem('unit') === 'F' ? 'F' : 'C';
let latestSeries = null;
let latestLive = null;

const canvas = document.getElementById('chart');
const ctx = canvas.getContext('2d');

// ---------------------------------------------------------------------------
// Unit helpers
// ---------------------------------------------------------------------------
const toDisplay = (c) => (unit === 'F' ? c * 9 / 5 + 32 : c);
const toCelsius = (v) => (unit === 'F' ? (v - 32) * 5 / 9 : v);
const unitSuffix = () => (unit === 'F' ? '°F' : '°C');

function setUnit(next) {
  unit = next;
  localStorage.setItem('unit', next);
  document.querySelectorAll('.unit').forEach((b) => {
    b.classList.toggle('active', b.dataset.unit === next);
  });
  document.querySelectorAll('.unit-label').forEach((el) => {
    el.textContent = unitSuffix();
  });
  renderLive();
  drawChart();
  loadSettings(); // re-render the threshold inputs in the new unit
}

document.querySelectorAll('.unit').forEach((b) => {
  b.addEventListener('click', () => setUnit(b.dataset.unit));
});

// ---------------------------------------------------------------------------
// Live readouts -- Requirement 5a
// ---------------------------------------------------------------------------
function renderLive() {
  if (!latestLive) return;
  const online = latestLive.box_online;

  const pill = document.getElementById('box-status');
  pill.textContent = online ? 'third box online' : 'third box offline';
  pill.className = 'pill ' + (online ? 'pill-ok' : 'pill-bad');

  for (const sensor of latestLive.sensors) {
    const card = document.querySelector(`.card[data-sensor="${sensor.id}"]`);
    if (!card) continue;

    const reading = card.querySelector('[data-role="reading"]');
    const substatus = card.querySelector('[data-role="substatus"]');
    const vbutton = card.querySelector('.vbutton');

    if (!online) {
      // Req 5a.ii -- the box switch is off, or we cannot reach it.
      reading.textContent = 'no data available';
      reading.classList.add('error');
      substatus.textContent = latestLive.box_error || 'third box is not responding';
    } else if (!sensor.present) {
      // Req 5a.i -- the probe is unplugged or not answering.
      reading.textContent = 'unplugged sensor';
      reading.classList.add('error');
      substatus.textContent = 'plug the probe back in; it will recover on its own';
    } else {
      reading.textContent = `${toDisplay(sensor.temp_c).toFixed(1)}${unitSuffix()}`;
      reading.classList.remove('error');
      substatus.textContent = `updated ${new Date().toLocaleTimeString()}`;
    }

    vbutton.disabled = !online;
    vbutton.setAttribute('aria-pressed', String(!!sensor.display_on));
    vbutton.querySelector('.vbutton-state').textContent = sensor.display_on ? 'on' : 'off';
  }
}

// Requirement 5b -- virtually press a button on the third box.
document.querySelectorAll('.vbutton').forEach((btn) => {
  btn.addEventListener('click', async () => {
    btn.disabled = true;
    try {
      const id = btn.dataset.sensor;
      const res = await fetch(`/api/button/${id}?state=toggle`, { method: 'POST' });
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const body = await res.json();
      btn.setAttribute('aria-pressed', String(!!body.display_on));
      btn.querySelector('.vbutton-state').textContent = body.display_on ? 'on' : 'off';
    } catch (err) {
      console.error('virtual button failed', err);
    } finally {
      btn.disabled = false;
    }
  });
});

// ---------------------------------------------------------------------------
// Chart recorder -- Requirement 5c
// ---------------------------------------------------------------------------
function fitCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.parentElement.clientWidth;
  const cssHeight = Math.max(260, Math.round(cssWidth * 0.33));
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  canvas.style.height = `${cssHeight}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { w: cssWidth, h: cssHeight };
}

function drawChart() {
  const { w, h } = fitCanvas();
  const left = 56;
  const right = w - 12;
  const top = 14;
  const bottom = h - 30;
  const plotW = right - left;
  const plotH = bottom - top;

  ctx.clearRect(0, 0, w, h);

  // Y position for a Celsius value, clamped to the fixed axis.
  const yOf = (c) => {
    const t = (Math.min(Y_MAX_C, Math.max(Y_MIN_C, c)) - Y_MIN_C) / (Y_MAX_C - Y_MIN_C);
    return bottom - t * plotH;
  };
  // X position for "this many seconds ago".
  const xOf = (secondsAgo) => left + (1 - secondsAgo / WINDOW_S) * plotW;

  // --- grid and axes ---
  ctx.font = '11px system-ui, sans-serif';
  ctx.strokeStyle = COLORS.grid;
  ctx.fillStyle = COLORS.axis;
  ctx.lineWidth = 1;

  // Horizontal gridlines. The ends are pinned at 10/50 C (50/122 F) by Req 5c.i;
  // in between we pick ticks that are round numbers in whichever unit is shown.
  const ticks = unit === 'F'
    ? [50, 60, 70, 80, 90, 100, 110, 120, 122].map((f) => ({ c: (f - 32) * 5 / 9, label: f }))
    : [10, 15, 20, 25, 30, 35, 40, 45, 50].map((c) => ({ c, label: c }));

  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (const tick of ticks) {
    const y = yOf(tick.c);
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(right, y);
    ctx.stroke();
    ctx.fillText(`${tick.label}${unitSuffix()}`, left - 8, y);
  }

  // Vertical gridlines, labelled "seconds ago from now" (Req 5c.iii).
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (let s = WINDOW_S; s >= 0; s -= 60) {
    const x = xOf(s);
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.stroke();
    ctx.fillText(String(s), x, bottom + 8);
  }
  ctx.fillText('seconds ago', (left + right) / 2, bottom + 20);

  if (!latestSeries) return;

  // --- per sensor ---
  latestSeries.sensors.forEach((sensor, index) => {
    const values = sensor.values_c;
    const n = values.length;
    if (!n) return;
    const color = index === 0 ? COLORS.s1 : COLORS.s2;
    const xAt = (i) => xOf(n - 1 - i);

    // Missing data first, underneath the traces. Req 5c.iv wants a gap to be
    // unmistakably different from a value pinned to the top or bottom of the
    // scale, so a gap gets its own hatched band rather than just a break.
    ctx.save();
    ctx.beginPath();
    ctx.rect(left, top, plotW, plotH);
    ctx.clip();
    let runStart = null;
    for (let i = 0; i <= n; i++) {
      const missing = i < n && values[i] === null;
      if (missing && runStart === null) runStart = i;
      if (!missing && runStart !== null) {
        drawGapBand(xAt(runStart), xAt(i - 1), top, plotH, index);
        runStart = null;
      }
    }
    ctx.restore();

    // Trace, broken wherever data is missing.
    ctx.save();
    ctx.beginPath();
    ctx.rect(left, top, plotW, plotH);
    ctx.clip();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.setLineDash(index === 1 ? [6, 3] : []); // dashed second trace: readable without colour
    ctx.beginPath();
    let drawing = false;
    for (let i = 0; i < n; i++) {
      const v = values[i];
      if (v === null) { drawing = false; continue; }
      const x = xAt(i);
      const y = yOf(v);
      if (!drawing) { ctx.moveTo(x, y); drawing = true; } else { ctx.lineTo(x, y); }
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();

    // Off-scale markers: a reading outside 10-50 C is clamped onto the axis, so
    // without a marker it would be indistinguishable from a reading that really
    // sat at the limit. Thinned to one marker per 8 px to stay legible.
    ctx.fillStyle = COLORS.offscale;
    let lastMarkerX = -Infinity;
    for (let i = 0; i < n; i++) {
      const v = values[i];
      if (v === null || (v >= Y_MIN_C && v <= Y_MAX_C)) continue;
      const x = xAt(i);
      if (x - lastMarkerX < 8) continue;
      lastMarkerX = x;
      const high = v > Y_MAX_C;
      ctx.beginPath();
      if (high) {
        ctx.moveTo(x, top + 1); ctx.lineTo(x - 4, top + 8); ctx.lineTo(x + 4, top + 8);
      } else {
        ctx.moveTo(x, bottom - 1); ctx.lineTo(x - 4, bottom - 8); ctx.lineTo(x + 4, bottom - 8);
      }
      ctx.closePath();
      ctx.fill();
    }
  });

  // Frame last, so traces clipped at the edge do not sit on top of it.
  ctx.strokeStyle = COLORS.axis;
  ctx.lineWidth = 1;
  ctx.strokeRect(left, top, plotW, plotH);
}

function drawGapBand(x0, x1, top, plotH, sensorIndex) {
  // A one-sample gap still needs to be visible, hence the minimum width.
  const xa = Math.min(x0, x1);
  const xb = Math.max(x0, x1);
  const width = Math.max(2, xb - xa);
  // Offset the two sensors vertically so overlapping gaps stay distinguishable.
  const bandTop = top + (sensorIndex === 0 ? 0 : plotH / 2);
  const bandH = plotH / 2;

  ctx.fillStyle = 'rgba(74, 85, 96, 0.28)';
  ctx.fillRect(xa, bandTop, width, bandH);

  ctx.save();
  ctx.beginPath();
  ctx.rect(xa, bandTop, width, bandH);
  ctx.clip();
  ctx.strokeStyle = COLORS.missing;
  ctx.lineWidth = 1;
  for (let d = -bandH; d < width; d += 6) {
    ctx.beginPath();
    ctx.moveTo(xa + d, bandTop + bandH);
    ctx.lineTo(xa + d + bandH, bandTop);
    ctx.stroke();
  }
  ctx.restore();
}

window.addEventListener('resize', () => drawChart());

// ---------------------------------------------------------------------------
// Alert settings -- Requirement 7
// ---------------------------------------------------------------------------
const form = document.getElementById('alert-form');
const feedback = document.getElementById('alert-feedback');

function say(message, ok = true) {
  feedback.textContent = message;
  feedback.className = 'feedback ' + (ok ? 'ok' : 'bad');
  if (message) setTimeout(() => { feedback.textContent = ''; }, 6000);
}

async function loadSettings() {
  try {
    const cfg = await (await fetch('/api/settings')).json();
    document.getElementById('alert-enabled').checked = cfg.enabled;
    document.getElementById('min').value = toDisplay(cfg.min_c).toFixed(1);
    document.getElementById('max').value = toDisplay(cfg.max_c).toFixed(1);
    document.getElementById('cooldown').value = cfg.cooldown_s;
    document.getElementById('recipient').value = cfg.recipient;
    document.getElementById('msg-low').value = cfg.message_low;
    document.getElementById('msg-high').value = cfg.message_high;
  } catch (err) {
    console.error('could not load settings', err);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const body = {
    enabled: document.getElementById('alert-enabled').checked,
    min_c: toCelsius(parseFloat(document.getElementById('min').value)),
    max_c: toCelsius(parseFloat(document.getElementById('max').value)),
    cooldown_s: parseInt(document.getElementById('cooldown').value, 10),
    recipient: document.getElementById('recipient').value.trim(),
    message_low: document.getElementById('msg-low').value,
    message_high: document.getElementById('msg-high').value,
  };
  try {
    const res = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    say('Saved.');
  } catch (err) {
    say(`Could not save: ${err.message}`, false);
  }
});

document.getElementById('test-alert').addEventListener('click', async () => {
  say('Sending...');
  try {
    const res = await fetch('/api/alerts/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient: document.getElementById('recipient').value.trim() }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    say('Test message sent.');
  } catch (err) {
    say(`Could not send: ${err.message}`, false);
  }
});

// ---------------------------------------------------------------------------
// Poll loop
// ---------------------------------------------------------------------------
async function poll() {
  try {
    const [live, series] = await Promise.all([
      fetch('/api/live').then((r) => r.json()),
      fetch('/api/series').then((r) => r.json()),
    ]);
    latestLive = live;
    latestSeries = series;
    renderLive();
    drawChart();
  } catch (err) {
    console.error('poll failed', err);
  }
}

setUnit(unit);
loadSettings();
poll();
setInterval(poll, POLL_MS);
