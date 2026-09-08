const DATA_URL = "data/news.json";

function formatDate(iso) {
  if (!iso) return "fecha desconocida";
  const d = new Date(iso);
  return d.toLocaleString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function relativeTime(iso) {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} d`;
}

function renderLatest(items) {
  const el = document.getElementById("latest-list");
  el.innerHTML = "";
  items.forEach((item) => {
    const div = document.createElement("div");
    div.className = "latest-item";
    div.dataset.search = [item.title, item.summary, ...(item.tickers || [])].join(" ").toLowerCase();

    const tags = (item.tickers || [])
      .map((t) => `<span class="tag">${t}</span>`)
      .join("");

    div.innerHTML = `
      <a href="${item.link}" target="_blank" rel="noopener">${item.title}</a>
      <div class="item-meta">${item.source_name} · ${formatDate(item.published)} (${relativeTime(item.published)})</div>
      ${tags ? `<div class="tag-row">${tags}</div>` : ""}
    `;
    el.appendChild(div);
  });
}

function renderTickers(tickers) {
  const grid = document.getElementById("tickers-grid");
  grid.innerHTML = "";
  tickers.forEach((ticker) => {
    const card = document.createElement("div");
    card.className = "ticker-card";
    card.dataset.search = [ticker.ticker, ticker.name].join(" ").toLowerCase();

    const newsHtml = ticker.news
      .map(
        (n) => `
        <div class="news-entry">
          <a href="${n.link}" target="_blank" rel="noopener">${n.title}</a>
          <p class="summary">${n.summary || ""}</p>
          <div class="item-meta">${n.source_name} · ${formatDate(n.published)} (${relativeTime(n.published)})</div>
        </div>`
      )
      .join("");

    card.innerHTML = `
      <h3>${ticker.ticker}</h3>
      <p class="company-name">${ticker.name} · ${ticker.exchange}</p>
      ${newsHtml}
    `;
    grid.appendChild(card);
  });
}

function applyFilter(query) {
  const q = query.trim().toLowerCase();
  let anyVisible = false;
  document.querySelectorAll("#latest-list .latest-item, #tickers-grid .ticker-card").forEach((el) => {
    const visible = !q || el.dataset.search.includes(q);
    el.hidden = !visible;
    if (visible) anyVisible = true;
  });
  document.getElementById("empty-state").hidden = anyVisible;
}

async function init() {
  const metaEl = document.getElementById("meta-info");
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    metaEl.textContent = `Última actualización: ${formatDate(data.generated_at)} (${relativeTime(data.generated_at)})`;
    document.getElementById("sources-list").textContent = data.sources
      .map((s) => s.name)
      .join(", ");

    renderLatest(data.latest || []);
    renderTickers(data.tickers || []);

    document.getElementById("filter-input").addEventListener("input", (e) => {
      applyFilter(e.target.value);
    });
  } catch (err) {
    metaEl.textContent = "No se pudieron cargar las noticias. Intenta más tarde.";
    console.error(err);
  }
}

init();
