const REFRESH_MS = 60_000;
const grid = document.getElementById("grid");
const status = document.getElementById("status");
let previous = {}; // symbol -> last, to flash cells that changed

const fmt = (value, decimals, signed = false) => {
  if (value === null || value === undefined) return "–";
  const s = value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return signed && value > 0 ? `+${s}` : s;
};

const direction = (v) => (v > 0 ? "up" : v < 0 ? "down" : "");

function groupHeader(state, group, colspan) {
  if (!group || group === state.group) return "";
  state.group = group;
  return `<tr class="group"><td colspan="${colspan}">${group}</td></tr>`;
}

function renderQuotes(panel, today) {
  const isYield = panel.kind === "yield";
  const state = { group: null };
  const rows = panel.rows.map((r) => {
    const move = isYield ? r.change : r.pct_change;
    const changed = previous[r.symbol] !== undefined && previous[r.symbol] !== r.last;
    const stale = r.as_of && r.as_of !== today ? `stale" title="last close ${r.as_of}` : "";
    return `${groupHeader(state, r.group, 4)}<tr>
      <td>${r.label}</td>
      <td class="${changed ? "flash" : ""} ${stale}">${fmt(r.last, r.decimals)}</td>
      <td class="${direction(r.change)}">${fmt(r.change, isYield ? 1 : r.decimals, true)}</td>
      <td class="${direction(move)}">${isYield ? "bp" : fmt(move, 2, true) + "%"}</td>
    </tr>`;
  });
  return `<table>
      <thead><tr><th>Name</th><th>Last</th><th>Chg</th><th>${isYield ? "" : "%Chg"}</th></tr></thead>
      <tbody>${rows.join("")}</tbody>
    </table>`;
}

function renderCell(c, column) {
  const text = typeof c.v === "string" ? c.v : fmt(c.v, c.d, c.sign);
  const classes = [c.cls, c.color && typeof c.v === "number" ? direction(c.v) : "", column.align];
  return `<td class="${classes.join(" ").trim()}">${text}${c.v !== null && c.suffix ? c.suffix : ""}</td>`;
}

function renderTable(panel) {
  const colspan = panel.columns.length + 1;
  const state = { group: null };
  const rows = panel.rows.map((r) => {
    const cells = r.cells.map((c, i) => renderCell(c, panel.columns[i])).join("");
    return `${groupHeader(state, r.group, colspan)}<tr><td>${r.label}</td>${cells}</tr>`;
  });
  const head = panel.columns.map((c) => `<th class="${c.align || ""}">${c.label}</th>`).join("");
  const note = panel.note ? `<p class="note">${panel.note}</p>` : "";
  return `<table>
      <thead><tr><th></th>${head}</tr></thead>
      <tbody>${rows.join("")}</tbody>
    </table>${note}`;
}

// --- yield curve chart ---------------------------------------------------------------

const CURVE_COLORS = { US: "#4ea1ff", DE: "#f5c542", FR: "#c77dff", IT: "#2ec4b6", "US-REAL": "#ff8c42" };
const CURVE_STATE_KEY = "launchpad.curves";
const curveState = { selected: ["US", "DE"], showPrev: false, open: false };
let curvePanel = null;
let curveChart = null;

try {
  Object.assign(curveState, JSON.parse(localStorage.getItem(CURVE_STATE_KEY)) || {}, { open: false });
} catch {}

function saveCurveState() {
  try {
    localStorage.setItem(CURVE_STATE_KEY, JSON.stringify({ selected: curveState.selected, showPrev: curveState.showPrev }));
  } catch {}
}

function renderCurves(panel) {
  curvePanel = panel;
  const options = panel.curves
    .map((c) => {
      const checked = curveState.selected.includes(c.id) ? "checked" : "";
      const color = CURVE_COLORS[c.id] || "#ccc";
      return `<label><input type="checkbox" data-curve="${c.id}" ${checked}>
        <span class="swatch" style="background:${color}"></span>${c.label}</label>`;
    })
    .join("");
  return `<div class="curve-controls">
      <div class="dropdown${curveState.open ? " open" : ""}">
        <button type="button" class="dropdown-toggle">Curves (${curveState.selected.length}) ▾</button>
        <div class="dropdown-menu">
          ${options}
          <hr>
          <label><input type="checkbox" data-prev ${curveState.showPrev ? "checked" : ""}> Previous close (dashed)</label>
        </div>
      </div>
    </div>
    <div class="chart-box"><canvas id="curve-chart"></canvas></div>
    <p class="note">${panel.note}</p>`;
}

function curveDatasets(panel, tenors) {
  const datasets = [];
  for (const c of panel.curves.filter((c) => curveState.selected.includes(c.id))) {
    const color = CURVE_COLORS[c.id] || "#ccc";
    const line = { borderColor: color, backgroundColor: color, tension: 0.3, spanGaps: true };
    const prev = tenors.map((t) => c.points[t]?.prev ?? null);
    datasets.push({ ...line, label: c.label, data: tenors.map((t) => c.points[t]?.y ?? null), prev, pointRadius: 3 });
    if (curveState.showPrev) {
      datasets.push({ ...line, label: `${c.label} (prev)`, data: prev, borderDash: [4, 4], borderWidth: 1, pointRadius: 0 });
    }
  }
  return datasets;
}

function drawCurves() {
  const canvas = document.getElementById("curve-chart");
  if (!canvas || !curvePanel) return;
  if (!window.Chart) {
    canvas.replaceWith(Object.assign(document.createElement("p"), { className: "note error", textContent: "chart library failed to load" }));
    return;
  }
  if (curveChart) curveChart.destroy();
  const selected = curvePanel.curves.filter((c) => curveState.selected.includes(c.id));
  // Only tenors at least one selected curve has, e.g. no 9M column unless France is shown.
  const tenors = curvePanel.tenors.filter((t) => selected.some((c) => c.points[t]));
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted").trim();
  const grid = css.getPropertyValue("--border").trim();
  Chart.defaults.font.family = css.getPropertyValue("--mono").trim();
  curveChart = new Chart(canvas, {
    type: "line",
    data: { labels: tenors, datasets: curveDatasets(curvePanel, tenors) },
    options: {
      animation: false,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { color: muted }, grid: { color: grid } },
        y: { ticks: { color: muted, callback: (v) => `${v.toFixed(2)}%` }, grid: { color: grid } },
      },
      plugins: {
        // Dashed previous-close lines share their curve's color, so they don't need a legend entry.
        legend: { labels: { color: muted, boxWidth: 12, filter: (item) => !item.text.endsWith("(prev)") } },
        tooltip: {
          filter: (item) => !item.dataset.label.endsWith("(prev)"), // the bp change already covers it
          callbacks: {
            label: (ctx) => {
              const y = ctx.parsed.y;
              const prev = ctx.dataset.prev?.[ctx.dataIndex];
              const chg = prev != null ? ` (${fmt((y - prev) * 100, 1, true)} bp)` : "";
              return `${ctx.dataset.label}: ${y.toFixed(3)}%${chg}`;
            },
          },
        },
      },
    },
  });
}

document.addEventListener("click", (e) => {
  const dropdown = document.querySelector(".curve-controls .dropdown");
  if (!dropdown) return;
  if (e.target.closest(".dropdown-toggle")) {
    curveState.open = !curveState.open;
  } else if (!e.target.closest(".dropdown-menu")) {
    curveState.open = false;
  }
  dropdown.classList.toggle("open", curveState.open);
});

document.addEventListener("change", (e) => {
  const input = e.target;
  if (input.dataset.curve) {
    const others = curveState.selected.filter((id) => id !== input.dataset.curve);
    curveState.selected = input.checked ? [...others, input.dataset.curve] : others;
    document.querySelector(".dropdown-toggle").textContent = `Curves (${curveState.selected.length}) ▾`;
  } else if (input.dataset.prev !== undefined) {
    curveState.showPrev = input.checked;
  } else {
    return;
  }
  saveCurveState();
  drawCurves();
});

const RENDERERS = {
  quotes: renderQuotes,
  table: renderTable,
  curves: renderCurves,
  error: (panel) => `<p class="note error">data unavailable: ${panel.error}</p>`,
};

function renderPanel(panel, today) {
  return `<section class="panel${panel.wide ? " wide" : ""}">
    <h2>${panel.title}</h2>
    ${RENDERERS[panel.type](panel, today)}
  </section>`;
}

async function refresh() {
  try {
    const res = await fetch("/api/panels");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const today = new Date().toISOString().slice(0, 10);
    grid.innerHTML = data.panels.map((p) => renderPanel(p, today)).join("");
    drawCurves();
    previous = Object.fromEntries(
      data.panels.filter((p) => p.type === "quotes").flatMap((p) => p.rows.map((r) => [r.symbol, r.last]))
    );
    status.textContent = `updated ${new Date(data.updated).toLocaleTimeString()}`;
  } catch (err) {
    status.textContent = `update failed: ${err.message}`;
  }
}

function tick() {
  document.getElementById("clock").textContent = new Date().toLocaleString("en-GB", {
    weekday: "short", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

refresh();
setInterval(refresh, REFRESH_MS);
tick();
setInterval(tick, 1000);
