const ETAT = { actif: "BTC", timeframe: "1d" };
let chart, series;
let derniereRequeteId = 0;
let bandes = {}; // nom -> élément DOM de la bande colorée

function creerBande(nom, classeCss) {
  const conteneur = document.getElementById("chart-overlay");
  const div = document.createElement("div");
  div.className = `bande ${classeCss}`;
  div.style.display = "none";
  conteneur.appendChild(div);
  bandes[nom] = div;
}

function positionnerBande(nom, prixHaut, prixBas) {
  const div = bandes[nom];
  if (prixHaut === null || prixHaut === undefined || prixBas === null || prixBas === undefined) {
    div.style.display = "none";
    return;
  }
  const yHaut = series.priceToCoordinate(Math.max(prixHaut, prixBas));
  const yBas = series.priceToCoordinate(Math.min(prixHaut, prixBas));
  if (yHaut === null || yBas === null) {
    div.style.display = "none";
    return;
  }
  const largeurEchelle = chart.priceScale("right").width();
  div.style.display = "block";
  div.style.top = `${yHaut}px`;
  div.style.height = `${Math.max(1, yBas - yHaut)}px`;
  div.style.right = `${largeurEchelle}px`;
}

const SVG_NS = "http://www.w3.org/2000/svg";

function dessinerNuage() {
  const svg = document.getElementById("nuage-svg");
  const serie = DERNIERES_DONNEES?.ichimoku?.nuage_serie;
  svg.innerHTML = "";
  if (!serie || serie.length < 2) return;

  // Projette chaque point en pixels, avec le haut/bas réel du nuage à cet
  // instant (senkou_a vs senkou_b peuvent s'inverser).
  const points = serie
    .map((p) => {
      const x = chart.timeScale().timeToCoordinate(p.time);
      const yA = series.priceToCoordinate(p.senkou_a);
      const yB = series.priceToCoordinate(p.senkou_b);
      if (x === null || yA === null || yB === null) return null;
      return { x, yHaut: Math.min(yA, yB), yBas: Math.max(yA, yB), haussier: p.senkou_a >= p.senkou_b };
    })
    .filter(Boolean);
  if (points.length < 2) return;

  // Un seul polygone par tronçon de couleur constante (plutôt qu'un
  // quadrilatère par paire de bougies) : évite les liserés
  // d'anti-aliasing entre des centaines de polygones adjacents d'un
  // pixel de large, et reproduit un vrai ruban continu comme sur
  // TradingView/Binance Academy.
  let troncon = [points[0]];
  function dessinerTroncon(troncon) {
    if (troncon.length < 2) return;
    const haut = troncon.map((p) => `${p.x},${p.yHaut}`).join(" ");
    const bas = troncon.slice().reverse().map((p) => `${p.x},${p.yBas}`).join(" ");
    const polygone = document.createElementNS(SVG_NS, "polygon");
    polygone.setAttribute("points", `${haut} ${bas}`);
    const haussier = troncon[0].haussier;
    polygone.setAttribute("fill", haussier ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)");
    polygone.setAttribute("stroke", haussier ? "rgba(34,197,94,0.6)" : "rgba(239,68,68,0.6)");
    polygone.setAttribute("stroke-width", "1");
    svg.appendChild(polygone);
  }

  for (let i = 1; i < points.length; i++) {
    if (points[i].haussier !== troncon[troncon.length - 1].haussier) {
      troncon.push(points[i]); // point de jonction partagé pour ne pas laisser de trou
      dessinerTroncon(troncon);
      troncon = [points[i]];
    } else {
      troncon.push(points[i]);
    }
  }
  dessinerTroncon(troncon);
}

function repositionnerToutesLesBandes() {
  if (!DERNIERES_DONNEES) return;
  dessinerNuage();
  positionnerBande("opportunite", DERNIERES_DONNEES.zone_opportunite?.haut, DERNIERES_DONNEES.zone_opportunite?.bas);
  positionnerBande("risque", DERNIERES_DONNEES.zone_risque?.haut, DERNIERES_DONNEES.zone_risque?.bas);
}

let DERNIERES_DONNEES = null;

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

  creerBande("opportunite", "bande-opportunite");
  creerBande("risque", "bande-risque");

  chart.timeScale().subscribeVisibleTimeRangeChange(repositionnerToutesLesBandes);

  window.addEventListener("resize", () => {
    const el = document.getElementById("chart");
    chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    repositionnerToutesLesBandes();
  });

  // Filet de sécurité : certains gestes tactiles (pinch/pan sur Safari iOS)
  // ne déclenchent pas toujours subscribeVisibleTimeRangeChange de façon
  // fiable. Boucle légère qui garde les bandes alignées en continu.
  function boucleRepositionnement() {
    repositionnerToutesLesBandes();
    requestAnimationFrame(boucleRepositionnement);
  }
  requestAnimationFrame(boucleRepositionnement);
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
  const perime = data.perime ? " (périmé)" : "";
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

  // Toujours afficher les deux zones, y compris quand aucune n'est
  // identifiée : le dire explicitement plutôt que de masquer la section
  // en silence (demande explicite du propriétaire, 24/10/2026).
  const zones = [
    data.zone_opportunite
      ? `<span class="pastille pastille-opportunite"></span> Zone d'opportunité : ${formatNombre(data.zone_opportunite.bas)}–${formatNombre(data.zone_opportunite.haut)}`
      : `<span class="pastille pastille-opportunite"></span> Zone d'opportunité : aucune résistance identifiée au-dessus du prix actuel`,
    data.zone_risque
      ? `<span class="pastille pastille-risque"></span> Zone de risque : ${formatNombre(data.zone_risque.bas)}–${formatNombre(data.zone_risque.haut)}`
      : `<span class="pastille pastille-risque"></span> Zone de risque : aucun support identifié en dessous du prix actuel`,
  ];

  el.innerHTML = `
    <details open>
      <summary>Prix et moyennes mobiles</summary>
      <p>Prix actuel : ${formatNombre(data.prix_actuel)}<br>${mm}<br>RSI14 : ${formatNombre(data.rsi14)} · ATR14 : ${formatNombre(data.atr14)}</p>
    </details>
    <details open><summary>Zones</summary><p>${zones.join("<br>")}</p></details>
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
    <p class="disclaimer">Analyse technique automatisée, pas un conseil financier. Lecture directe des chiffres calculés, pas encore de texte explicatif généré (phase suivante). Régime : prix ${data.regime.prix_vs_mm_longue} de la moyenne mobile longue (pente ${data.regime.pente_mm_longue}), structure ${data.regime.structure}.</p>
  `;
}

function basculerChargement(enCours) {
  document.getElementById("chart").classList.toggle("chargement", enCours);
  document.getElementById("resume").classList.toggle("chargement", enCours);
}

async function chargerAnalyse() {
  const idRequete = ++derniereRequeteId;
  const actifDemande = ETAT.actif;
  const timeframeDemande = ETAT.timeframe;
  document.getElementById("source-badge").textContent = `Chargement de ${actifDemande}…`;
  document.getElementById("source-badge").classList.remove("perime");
  basculerChargement(true);
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

    // Zones dérivées des scénarios déjà calculés par le moteur (mêmes
    // chiffres que la section "Scénarios"), jamais une donnée inventée.
    const haussier = data.scenarios.find((s) => s.type === "haussier");
    const baissier = data.scenarios.find((s) => s.type === "baissier");
    data.zone_opportunite = haussier && haussier.cible !== null ? { haut: haussier.cible, bas: data.prix_actuel } : null;
    data.zone_risque = baissier && baissier.cible !== null ? { haut: data.prix_actuel, bas: baissier.cible } : null;

    // Vider les lignes de prix de l'actif précédent AVANT de charger les
    // nouvelles données : sinon elles restent attachées à la série au
    // moment du setData() et faussent le calcul de l'échelle automatique
    // (bug trouvé le 24/10/2026 : l'échelle restait bloquée sur celle de
    // l'actif précédent, ex. BTC, après un changement d'actif vers ETH).
    viderLignesDePrix();
    DERNIERES_DONNEES = data;
    series.setData(data.candles);
    chart.timeScale().fitContent();

    for (const [nom, valeur] of Object.entries(data.moyennes_mobiles)) {
      ajouterLigneDePrix(valeur, nom.toUpperCase(), "#58a6ff");
    }
    for (const n of data.niveaux) {
      if (n.type !== "nuage") ajouterLigneDePrix(n.prix_haut, "Niveau", "#8b949e");
    }

    repositionnerToutesLesBandes();
    afficherSource(data);
    reinitialiserBoutonAnalyse();
    afficherResume(data);
  } catch (err) {
    document.getElementById("source-badge").textContent = `Erreur : ${err}`;
    document.getElementById("source-badge").classList.add("perime");
  } finally {
    if (idRequete === derniereRequeteId) basculerChargement(false);
  }
}

function reinitialiserBoutonAnalyse() {
  const bouton = document.getElementById("bouton-analyse");
  bouton.textContent = "Lancer l'analyse";
  bouton.className = "bouton-analyse";
  bouton.disabled = false;
  document.getElementById("analyse-llm").innerHTML = "";
}

function afficherTexteAnalyse(resultat) {
  const el = document.getElementById("analyse-llm");
  const t = resultat.texte;
  const origine = resultat.source_cache ? "servi depuis le cache (même bougie)" : "généré à l'instant";
  el.innerHTML = `
    <div class="carte-analyse">
      <h2>Analyse</h2>
      <h3>Tendance</h3><p>${t.tendance}</p>
      <h3>Niveaux à surveiller</h3><p>${t.niveaux}</p>
      <h3>Scénarios</h3><p>${t.scenarios}</p>
      <h3>Ce qui changerait l'analyse</h3><p>${t.ce_qui_changerait}</p>
      <h3>Risques</h3><p>${t.risques}</p>
      <p class="meta">Analyse technique automatisée, générée automatiquement. Ce n'est pas un conseil financier. ${origine}, le ${new Date(resultat.genere_le).toLocaleString("fr-FR")}.</p>
    </div>
  `;
}

async function lancerAnalyseLLM() {
  const bouton = document.getElementById("bouton-analyse");
  const actif = ETAT.actif;
  const timeframe = ETAT.timeframe;
  bouton.disabled = true;
  bouton.className = "bouton-analyse chargement-llm";
  bouton.textContent = "Analyse en cours…";
  try {
    const res = await fetch(`/api/analysis-llm/${actif}/${timeframe}`, { method: "POST" });
    // Un changement d'actif/timeframe entre-temps a déjà réinitialisé le
    // bouton : ne pas écraser son état avec une réponse devenue obsolète.
    if (actif !== ETAT.actif || timeframe !== ETAT.timeframe) return;

    if (!res.ok) {
      const erreur = await res.json().catch(() => ({ detail: res.statusText }));
      bouton.className = "bouton-analyse erreur";
      bouton.textContent = erreur.detail || "Erreur";
      bouton.disabled = false;
      return;
    }
    const resultat = await res.json();
    bouton.className = "bouton-analyse ok";
    bouton.textContent = resultat.source_cache ? "Analyse à jour" : "Analyse terminée";
    afficherTexteAnalyse(resultat);
  } catch (err) {
    bouton.className = "bouton-analyse erreur";
    bouton.textContent = "Erreur réseau";
    bouton.disabled = false;
  }
}

function initControles() {
  document.getElementById("bouton-analyse").addEventListener("click", lancerAnalyseLLM);
  document.getElementById("selecteur-actif").addEventListener("change", (e) => {
    ETAT.actif = e.target.value;
    chargerAnalyse();
  });
  document.querySelectorAll("[data-timeframe]").forEach((bouton) => {
    bouton.addEventListener("click", () => {
      ETAT.timeframe = bouton.dataset.timeframe;
      document.querySelectorAll("[data-timeframe]").forEach((b) => b.classList.toggle("actif", b === bouton));
      chargerAnalyse();
    });
  });
}

async function chargerListeActifs() {
  const res = await fetch("/api/assets");
  const actifs = await res.json();
  const select = document.getElementById("selecteur-actif");
  select.innerHTML = actifs.map((a) => `<option value="${a}">${a}</option>`).join("");
  select.value = ETAT.actif;
}

async function main() {
  initChart();
  await chargerListeActifs();
  initControles();
  await chargerAnalyse();
}

main();
