const DATA_URL = "data/news.json";
const VISIBLES_INICIALES = 3;

const estado = { datos: null, chip: "Todas", tab: "acciones", q: "" };

/* ── Utilidades ─────────────────────────────────────────────────────── */

function haceCuanto(iso) {
  if (!iso) return "sin fecha";
  const min = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (min < 1) return "ahora";
  if (min < 60) return `hace ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.floor(h / 24);
  return d === 1 ? "ayer" : `hace ${d} d`;
}

function horasDesde(iso) {
  if (!iso) return Infinity;
  return (Date.now() - new Date(iso).getTime()) / 3600000;
}

function esMexicana(t) {
  return /\.MX$/.test(t.ticker) || /BMV|Estatal/.test(t.exchange || "");
}

/* Construye nodos con textContent en vez de innerHTML: los títulos vienen de
   feeds de terceros y no deben interpretarse como HTML. */
function el(tag, className, texto) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (texto != null) n.textContent = texto;
  return n;
}

function enlaceNota(nota, conResumen) {
  const a = el("a");
  a.href = nota.link;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.appendChild(el("p", "news-title", nota.title));

  if (conResumen && nota.summary) a.appendChild(el("p", "resumen", nota.summary));

  const sub = el("div", "news-sub");
  sub.appendChild(el("span", "src", nota.source_short));
  sub.appendChild(el("span", null, haceCuanto(nota.published)));
  a.appendChild(sub);
  return a;
}

/* ── Tarjetas por acción ────────────────────────────────────────────── */

function tarjeta(t) {
  const card = el("article", "card");

  const head = el("div", "card-head");
  const h = horasDesde(t.news[0].published);
  const dot = el("span", "dot" + (h < 6 ? " fresh" : h < 24 ? " warm" : ""));
  head.appendChild(dot);

  const txt = el("div", "head-text");
  const fila = el("div", "ticker-row");
  fila.appendChild(el("span", "ticker", t.ticker));
  if (t.news.length > 1) fila.appendChild(el("span", "n-notas", `${t.news.length} notas`));
  txt.appendChild(fila);
  const detalle = [t.name, t.sector].filter(Boolean).join(" · ");
  txt.appendChild(el("div", "company", detalle));
  head.appendChild(txt);

  head.appendChild(el("span", "market" + (esMexicana(t) ? " mx" : ""), t.exchange || ""));
  card.appendChild(head);

  const lista = el("div", "news");
  t.news.forEach((n, i) => {
    const a = enlaceNota(n, false);
    if (i >= VISIBLES_INICIALES) a.hidden = true;
    lista.appendChild(a);
  });
  card.appendChild(lista);

  const ocultas = t.news.length - VISIBLES_INICIALES;
  if (ocultas > 0) {
    const btn = el("button", "mas", `Ver ${ocultas} nota${ocultas > 1 ? "s" : ""} más`);
    btn.addEventListener("click", () => {
      const abierto = btn.dataset.abierto === "1";
      Array.from(lista.children).forEach((a, i) => {
        if (i >= VISIBLES_INICIALES) a.hidden = abierto;
      });
      btn.dataset.abierto = abierto ? "0" : "1";
      btn.textContent = abierto ? `Ver ${ocultas} nota${ocultas > 1 ? "s" : ""} más` : "Ver menos";
    });
    card.appendChild(btn);
  }
  return card;
}

/* ── Filtros ────────────────────────────────────────────────────────── */

function pasaChip(t) {
  if (estado.chip === "Todas") return true;
  if (estado.chip === "México") return esMexicana(t);
  if (estado.chip === "Global") return !esMexicana(t);
  return t.sector === estado.chip;
}

function pasaBusqueda(texto) {
  return !estado.q || texto.toLowerCase().includes(estado.q);
}

function render() {
  const { tickers, sin_accion } = estado.datos;

  const grid = document.getElementById("grid-acciones");
  grid.textContent = "";
  const visibles = tickers.filter(
    (t) => pasaChip(t) && pasaBusqueda(`${t.ticker} ${t.name} ${t.sector || ""} ${t.news.map((n) => n.title).join(" ")}`)
  );
  visibles.forEach((t) => grid.appendChild(tarjeta(t)));
  document.getElementById("vacio-acciones").hidden = visibles.length > 0;

  const feed = document.getElementById("lista-general");
  feed.textContent = "";
  const generales = sin_accion.filter((n) => pasaBusqueda(`${n.title} ${n.summary}`));
  generales.forEach((n) => feed.appendChild(enlaceNota(n, true)));
  document.getElementById("vacio-general").hidden = generales.length > 0;

  document.getElementById("count-acciones").textContent = visibles.length;
  document.getElementById("count-general").textContent = generales.length;
}

function construirChips() {
  const cont = document.getElementById("chips");
  const porSector = {};
  estado.datos.tickers.forEach((t) => {
    if (t.sector) porSector[t.sector] = (porSector[t.sector] || 0) + 1;
  });
  const sectores = Object.keys(porSector).sort((a, b) => porSector[b] - porSector[a]);

  ["Todas", "México", "Global", ...sectores].forEach((nombre) => {
    const b = el("button", "chip" + (nombre === estado.chip ? " is-active" : ""), nombre);
    b.addEventListener("click", () => {
      estado.chip = nombre;
      cont.querySelectorAll(".chip").forEach((c) => c.classList.toggle("is-active", c === b));
      render();
    });
    cont.appendChild(b);
  });
}

function cambiarTab(cual) {
  estado.tab = cual;
  const esAcciones = cual === "acciones";
  document.getElementById("tab-acciones").classList.toggle("is-active", esAcciones);
  document.getElementById("tab-general").classList.toggle("is-active", !esAcciones);
  document.getElementById("tab-acciones").setAttribute("aria-selected", String(esAcciones));
  document.getElementById("tab-general").setAttribute("aria-selected", String(!esAcciones));
  document.getElementById("panel-acciones").hidden = !esAcciones;
  document.getElementById("panel-general").hidden = esAcciones;
}

/* ── Arranque ───────────────────────────────────────────────────────── */

async function init() {
  const meta = document.getElementById("hero-meta");
  try {
    const res = await fetch(DATA_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    estado.datos = await res.json();

    meta.textContent = `Actualizado ${haceCuanto(estado.datos.generated_at)}`;

    const tot = estado.datos.totales || {};
    document.getElementById("stat-acciones").textContent = tot.acciones_con_noticias ?? "—";
    document.getElementById("stat-notas").textContent = tot.articulos ?? "—";
    document.getElementById("stat-fuentes").textContent = estado.datos.sources.length;
    document.getElementById("stats").hidden = false;

    document.getElementById("fuentes-pie").textContent =
      "Fuentes: " + estado.datos.sources.map((s) => s.name).join(" · ");

    construirChips();
    render();

    document.getElementById("buscador").addEventListener("input", (e) => {
      estado.q = e.target.value.trim().toLowerCase();
      render();
    });
    document.getElementById("tab-acciones").addEventListener("click", () => cambiarTab("acciones"));
    document.getElementById("tab-general").addEventListener("click", () => cambiarTab("general"));
  } catch (err) {
    meta.textContent = "No se pudieron cargar las noticias. Intenta más tarde.";
    console.error(err);
  }
}

init();
