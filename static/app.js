const ETAT = { actif: "BTC", timeframe: "1d" };
let chart, series;
let derniereRequeteId = 0;

function initChart() {
  chart = LightweightCharts.createChart(document.getElementById("chart"), {
    layout: { background: { color: "#0d1117" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
    timeScale: { borderColor: "#30363d" },
    rightPriceScale: { borderColor: "#30363d" },
    handleScroll: true,
    handleScale: true,
  });
  series = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: "#3fb950",
    downColor: "#f85149",
    borderVisible: false,
    wickUpColor: "#3fb950",
    wickDownColor: "#f85149",
  });
  window.addEventListener("resize", () => {
    const el = document.getElementById("chart");
    chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
  });
}

function formatNombre(n) {
  if (n === null || n === undefined) return "n.d.";
  return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

function viderLignesDePrix() {
  if (series._lignesDePrix) {
    for (const ligne of series._lignesDePrix) series.removePriceLine(ligne);
  }
  series._lignesDePrix = [];
}

function ajouterLigneDePrix(prix, titre, couleur) {
  if (prix === null || prix === undefined) return;
  const ligne = series.createPriceLine({
    price: prix,
    color: couleur,
    lineWidth: 1,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: true,
    title: titre,
  });
  series._lignesDePrix.push(ligne);
}

function afficherSource(data) {
  const el = document.getElementById("source-badge");
  const perime = data.perime ? " (pérîmé)" : "";
  el.textContent = `Source : ${data.source}${perime} · à jour le ${new Date(data.a_jour_le).toLocaleString("fr-FR")}`;
  el.classList.toggle("perime", !!data.perime);
}

function afficherResume(data) {
  const el = document.getElementById("resume");
  const mm = Object.entries(data.moyennes_mobiles)
    .map(([k, v]) => `${k.toUpperCase()} : ${formatNombre(v)}`)
    .join(" · ");

  const niveaux = data.niveaux
    .map((n) => `${n.type === "nuage" ? "Nuage Ichimoku" : "Zone"} ${formatNombre(n.prix_bas)}–${formatNombre(n.prix_haut)}${n.touches ? ` (${n.touches} touches)` : ""}${n.role_inverse ? " · rôle inversé" : ""}`)
    .join("<br>");

  const scenarios = data.scenarios
    .map((s) => `<strong>${s.type}</strong> : ${s.condition_cloture}${s.cible !== null ? ` · cible ${formatNombre(s.cible)}` : ""}${s.invalidation !== null ? ` · invalidation ${formatNombre(s.invalidation)} (${s.source_invalidation})` : ""}`)
    .join("<br>");

  const forceRelative = data.force_relative_btc
    ? `Force relative vs BTC : ${data.force_relative_btc.tendance} (${formatNombre(data.force_relative_btc.variation_pct_periode)}% sur 30 bougies)`
    : "";

  el.innerHTML = `
    <details open>
      <summary>Prix et moyennes mobiles</summary>
      <p>Prix actuel : ${formatNombre(data.prix_actuel)}<br>${mm}<br>RSI14 : ${formatNombre(data.rsi14)} · ATR14 : ${formatNombre(data.atr14)}</p>
    </details>
    <details open>
      <summary>Ichimoku</summary>
      <p>Prix vs nuage : ${data.ichimoku.prix_vs_nuage} · Couleur du nuage : ${data.ichimoku.couleur_nuage}<br>
      Tenkan ${formatNombre(data.ichimoku.tenkan)} · Kijun ${formatNombre(data.ichimoku.kijun)}<br>
      Nuage ${formatNombre(data.ichimoku.nuage_bas)}–${formatNombre(data.ichimoku.nuage_haut)}<br>
      Tenkan/Kijun : ${data.ichimoku.tenkan_vs_kijun} · Chikou vs prix historique : ${data.ichimoku.chikou_vs_prix_historique}</p>
    </details>
    <details>
      <summary>Niveaux</summary>
      <p>${niveaux || "Aucun niveau détecté"}</p>
    </details>
    <details open>
      <summary>Scénarios</summary>
      <p>${scenarios}</p>
    </details>
    ${forceRelative ? `<p class="force-relative">${forceRelative}</p>` : ""}
    <p class="disclaimer">Lecture directe des chiffres calculés, pas encore de texte explicatif généré (phase suivante). Régime : prix ${data.regime.prix_vs_mm_longue} de la moyenne mobile longue (pente ${data.regime.pente_mm_longue}), structure ${data.regime.structure}.</p>
  `;
}

async function chargerAnalyse() {
  const idRequete = ++derniereRequeteId;
  const actifDemande = ETAT.actif;
  const timeframeDemande = ETAT.timeframe;
  document.getElementById("source-badge").textContent = "Chargement…";
  try {
    const res = await fetch(`/api/analysis/${actifDemande}/${timeframeDemande}`);
    // Une requête plus récente (autre clic entre-temps) a déjà répondu :
    // ignorer cette réponse périmée pour ne jamais écraser un affichage
    // plus récent avec des données obsolètes.
    if (idRequete !== derniereRequeteId) return;

    if (!res.ok) {
      const erreur = await res.json().catch(() => ({ detail: res.statusText }));
      document.getElementById("source-badge").textContent = `Source indisponible : ${erreur.detail || res.statusText}`;
      document.getElementById("source-badge").classList.add("perime");
      return;
    }
    const data = await res.json();
    if (idRequete !== derniereRequeteId) return;

    series.setData(data.candles);
    chart.timeScale().fitContent();

    viderLignesDePrix();
    for (const [nom, valeur] of Object.entries(data.moyennes_mobiles)) {
      ajouterLigneDePrix(valeur, nom.toUpperCase(), "#58a6ff");
    }
    ajouterLigneDePrix(data.ichimoku.nuage_haut, "Nuage haut", "#d29922");
    ajouterLigneDePrix(data.ichimoku.nuage_bas, "Nuage bas", "#d29922");
    for (const n of data.niveaux) {
      ajouterLigneDePrix(n.prix_haut, n.type === "nuage" ? "Nuage" : "Niveau", "#8b949e");
    }

    afficherSource(data);
    afficherResume(data);
  } catch (err) {
    document.getElementById("source-badge").textContent = `Erreur : ${err}`;
    document.getElementById("source-badge").classList.add("perime");
  }
}

function initControles() {
  document.querySelectorAll("[data-actif]").forEach((bouton) => {
    bouton.addEventListener("click", () => {
      ETAT.actif = bouton.dataset.actif;
      document.querySelectorAll("[data-actif]").forEach((b) => b.classList.toggle("actif", b === bouton));
      chargerAnalyse();
    });
  });
  document.querySelectorAll("[data-timeframe]").forEach((bouton) => {
    bouton.addEventListener("click", () => {
      ETAT.timeframe = bouton.dataset.timeframe;
      document.querySelectorAll("[data-timeframe]").forEach((b) => b.classList.toggle("actif", b === bouton));
      chargerAnalyse();
    });
  });
}

async function main() {
  initChart();
  initControles();
  await chargerAnalyse();
}

main();
