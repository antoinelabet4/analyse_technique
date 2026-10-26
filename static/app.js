const ETAT = { actif: "BTC", timeframe: "1d", periode: "tout" };
const PERIODES_EN_JOURS = { "1m": 30, "3m": 90, "6m": 180, "1y": 365 };
let chart, series;
let derniereRequeteId = 0;
let bandes = { niveaux: [] }; // niveaux -> tableau des divs DOM des bandes de niveaux
let lignesMM = {}; // nom (mm50/mm200/ema200) -> série LightweightCharts
const COULEURS_MM = { mm50: "#58a6ff", mm200: "#f0b429", ema200: "#f0b429" };
let serieRSI = null;
let ligneRSI30 = null, ligneRSI70 = null;
let serieMACDLigne = null, serieMACDSignal = null, serieMACDHistogramme = null;
const PANE_RSI = 1;
const PANE_MACD = 2;

function chargerIndicateursVisibles() {
  const defaut = { mm: true, nuage: true, zones: true, rsi: true, macd: true };
  try {
    const sauvegarde = localStorage.getItem("indicateursVisibles");
    return sauvegarde ? { ...defaut, ...JSON.parse(sauvegarde) } : defaut;
  } catch (err) {
    return defaut; // localStorage indisponible (navigation privée, etc.)
  }
}

const INDICATEURS_VISIBLES = chargerIndicateursVisibles();

// Demande explicite du propriétaire (25/10/2026) : le LLM calcule un
// signal technique pur (haussier/baissier/neutre, jamais "acheter" ou
// "vendre" — il ne sait pas si on détient l'actif). Le réglage "je
// détiens / je ne détiens pas", par actif, mémorisé sur l'appareil,
// permet de traduire ce signal en action pertinente côté client, sans
// aucun nouvel appel réseau.
function chargerPositionsDetenues() {
  try {
    const sauvegarde = localStorage.getItem("positionsDetenues");
    return sauvegarde ? JSON.parse(sauvegarde) : {};
  } catch (err) {
    return {};
  }
}

let POSITIONS_DETENUES = chargerPositionsDetenues();

function sauvegarderPositionsDetenues() {
  try {
    localStorage.setItem("positionsDetenues", JSON.stringify(POSITIONS_DETENUES));
  } catch (err) {
    // Tant pis, préférence non mémorisée pour la prochaine visite.
  }
}

function sauvegarderIndicateursVisibles() {
  try {
    localStorage.setItem("indicateursVisibles", JSON.stringify(INDICATEURS_VISIBLES));
  } catch (err) {
    // Tant pis, préférence non mémorisée pour la prochaine visite.
  }
}

function viderBandesNiveaux() {
  for (const div of bandes.niveaux) div.remove();
  bandes.niveaux = [];
}

function positionnerBandeDiv(div, prixHaut, prixBas) {
  const yHaut = series.priceToCoordinate(Math.max(prixHaut, prixBas));
  const yBas = series.priceToCoordinate(Math.min(prixHaut, prixBas));
  if (yHaut === null || yBas === null) {
    div.style.display = "none";
    return;
  }
  const largeurEchelle = chart.priceScale("right").width();
  div.style.display = "block";
  div.style.top = `${yHaut}px`;
  div.style.height = `${Math.max(2, yBas - yHaut)}px`;
  div.style.right = `${largeurEchelle}px`;
}

// Une zone n'est "opportunité" (vert) ou "risque" (rouge) que relativement
// à une position : si je ne détiens pas l'actif, je ne peux qu'acheter,
// donc un support est une opportunité d'entrée et une résistance un
// risque de payer trop cher ; si je détiens déjà, c'est l'inverse, une
// résistance devient l'opportunité de prise de profit et un support le
// risque de voir la position perdre de la valeur. Avant ce correctif
// (25/10/2026), le support était toujours vert et la résistance toujours
// rouge, sans jamais tenir compte du réglage "Je détiens" — signalé par
// le propriétaire ("zone de risque n'est pas clair... si ça monte c'est
// bien si je détiens").
function estZoneOpportunite(estSupport, detient) {
  return detient ? !estSupport : estSupport;
}

// Une bande colorée par niveau de pivot proche du prix, à la place des
// lignes "Niveau" pointillées d'origine : demande explicite du
// propriétaire (25/10/2026), plus lisible qu'une ligne fine avec une
// étiquette, dans le même esprit visuel que le nuage Ichimoku. Remplace
// aussi l'ancienne bande unique dérivée des scénarios.
function dessinerZonesNiveaux() {
  viderBandesNiveaux();
  if (!INDICATEURS_VISIBLES.zones || !DERNIERES_DONNEES) return;
  const prixActuel = DERNIERES_DONNEES.prix_actuel;
  const detient = !!POSITIONS_DETENUES[ETAT.actif];
  const conteneur = document.getElementById("chart-overlay");
  for (const n of DERNIERES_DONNEES.niveaux) {
    if (n.type !== "pivot") continue;
    const estSupport = n.prix_haut <= prixActuel;
    const estResistance = n.prix_bas >= prixActuel;
    if (!estSupport && !estResistance) continue; // prix à l'intérieur du niveau, cas rare, ignoré
    const div = document.createElement("div");
    div.className = `bande ${estZoneOpportunite(estSupport, detient) ? "bande-opportunite" : "bande-risque"}`;
    conteneur.appendChild(div);
    positionnerBandeDiv(div, n.prix_haut, n.prix_bas);
    bandes.niveaux.push(div);
  }
}

const SVG_NS = "http://www.w3.org/2000/svg";

function dessinerNuage() {
  const svg = document.getElementById("nuage-svg");
  svg.innerHTML = "";
  if (!INDICATEURS_VISIBLES.nuage) return;
  const serie = DERNIERES_DONNEES?.ichimoku?.nuage_serie;
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
  dessinerZonesNiveaux();
}

function viderCourbesMM() {
  for (const serie of Object.values(lignesMM)) {
    chart.removeSeries(serie);
  }
  lignesMM = {};
}

// La liste des cryptos disponibles est passée de 5 à 22 (25/10/2026),
// avec des prix d'ordres de grandeur très différents (BTC ~80000, SHIB
// ~0,000005) : la précision fixe par défaut de Lightweight Charts (2
// décimales) affichait "0.00" partout pour les actifs à très faible
// valeur unitaire, rendant les étiquettes de prix inutilisables. La
// précision est maintenant calculée dynamiquement à partir du prix
// actuel de l'actif chargé.
function precisionPourPrix(prix) {
  const abs = Math.abs(prix ?? 0);
  if (abs === 0) return 2;
  if (abs >= 1) return 2;
  if (abs >= 0.01) return 4;
  if (abs >= 0.0001) return 6;
  return 8;
}

function formatDePrix(prix) {
  const precision = precisionPourPrix(prix);
  return { type: "price", precision, minMove: Math.pow(10, -precision) };
}

function dessinerCourbesMM() {
  viderCourbesMM();
  if (!INDICATEURS_VISIBLES.mm || !DERNIERES_DONNEES?.moyennes_mobiles_serie) return;
  const priceFormat = formatDePrix(DERNIERES_DONNEES.prix_actuel);
  for (const [nom, points] of Object.entries(DERNIERES_DONNEES.moyennes_mobiles_serie)) {
    if (!points.length) continue;
    const ligneSerie = chart.addSeries(LightweightCharts.LineSeries, {
      color: COULEURS_MM[nom] || "#8b949e",
      lineWidth: 1,
      title: nom.toUpperCase(),
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      lastValueVisible: true,
      priceFormat,
    });
    ligneSerie.setData(points.map((p) => ({ time: p.time, value: p.valeur })));
    lignesMM[nom] = ligneSerie;
  }
}

function dessinerRSI() {
  if (!serieRSI) return;
  const visible = INDICATEURS_VISIBLES.rsi;
  serieRSI.applyOptions({ visible });
  if (!visible || !DERNIERES_DONNEES) return;
  serieRSI.setData((DERNIERES_DONNEES.rsi_serie || []).map((p) => ({ time: p.time, value: p.valeur })));
}

function dessinerMACD() {
  if (!serieMACDLigne) return;
  const visible = INDICATEURS_VISIBLES.macd;
  serieMACDLigne.applyOptions({ visible });
  serieMACDSignal.applyOptions({ visible });
  serieMACDHistogramme.applyOptions({ visible });
  if (!visible || !DERNIERES_DONNEES) return;
  const priceFormat = formatDePrix(DERNIERES_DONNEES.prix_actuel);
  serieMACDLigne.applyOptions({ priceFormat });
  serieMACDSignal.applyOptions({ priceFormat });
  serieMACDHistogramme.applyOptions({ priceFormat });
  const points = DERNIERES_DONNEES.macd?.serie || [];
  serieMACDLigne.setData(points.map((p) => ({ time: p.time, value: p.ligne })));
  serieMACDSignal.setData(points.map((p) => ({ time: p.time, value: p.signal })));
  serieMACDHistogramme.setData(
    points.map((p) => ({
      time: p.time,
      value: p.histogramme,
      color: p.histogramme >= 0 ? "rgba(34,197,94,0.6)" : "rgba(239,68,68,0.6)",
    }))
  );
}

function redessinerIndicateurs() {
  if (!DERNIERES_DONNEES) return;
  viderLignesDePrix();
  dessinerCourbesMM();
  dessinerRSI();
  dessinerMACD();
  repositionnerToutesLesBandes();
}

let DERNIERES_DONNEES = null;

function initChart() {
  chart = LightweightCharts.createChart(document.getElementById("chart"), {
    layout: { background: { color: "#0d1117" }, textColor: "#e6edf3" },
    grid: { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
    timeScale: { borderColor: "#30363d" },
    rightPriceScale: { borderColor: "#30363d" },
    handleScroll: true,
    // Le glissé sur l'axe des prix (à droite, juste sous les étiquettes
    // MM/Niveau) rescale manuellement l'échelle et désactive l'ajustement
    // automatique : un toucher accidentel dessus sur mobile peut laisser
    // le graphique coincé sur une échelle absurde (ex. -25000 à 250000),
    // bien après que les données affichées restent normales (bug constaté
    // le 25/10/2026). Le glissé sur l'axe du temps reste autorisé (en plus
    // des boutons de durée dédiés) ; pincer pour zoomer aussi.
    handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: { time: true, price: false }, axisDoubleClickReset: true },
  });
  series = chart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: "#3fb950",
    downColor: "#f85149",
    borderVisible: false,
    wickUpColor: "#3fb950",
    wickDownColor: "#f85149",
  });

  // Sous-graphiques RSI et MACD, demande explicite du propriétaire
  // (25/10/2026) : séries créées une seule fois (contrairement aux
  // moyennes mobiles, leur nombre ne change jamais selon le timeframe),
  // seules les données sont remplacées à chaque rechargement.
  serieRSI = chart.addSeries(
    LightweightCharts.LineSeries,
    { color: "#a78bfa", lineWidth: 1, title: "RSI14", priceLineVisible: false, lastValueVisible: true },
    PANE_RSI
  );
  ligneRSI30 = serieRSI.createPriceLine({ price: 30, color: "#8b949e", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true, title: "30" });
  ligneRSI70 = serieRSI.createPriceLine({ price: 70, color: "#8b949e", lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted, axisLabelVisible: true, title: "70" });

  serieMACDHistogramme = chart.addSeries(
    LightweightCharts.HistogramSeries,
    { title: "MACD hist.", priceLineVisible: false, lastValueVisible: false },
    PANE_MACD
  );
  serieMACDLigne = chart.addSeries(
    LightweightCharts.LineSeries,
    { color: "#58a6ff", lineWidth: 1, title: "MACD", priceLineVisible: false, lastValueVisible: true },
    PANE_MACD
  );
  serieMACDSignal = chart.addSeries(
    LightweightCharts.LineSeries,
    { color: "#f0b429", lineWidth: 1, title: "Signal", priceLineVisible: false, lastValueVisible: true },
    PANE_MACD
  );

  const panneaux = chart.panes();
  if (panneaux[PANE_RSI]) panneaux[PANE_RSI].setHeight(90);
  if (panneaux[PANE_MACD]) panneaux[PANE_MACD].setHeight(90);

  chart.timeScale().subscribeVisibleTimeRangeChange(repositionnerToutesLesBandes);

  window.addEventListener("resize", () => redimensionnerChart());

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
  // Même correctif que pour le graphique (25/10/2026, liste étendue à 22
  // actifs dont certains à très faible valeur unitaire, ex. SHIB) :
  // 2 décimales fixes affichait "0" pour ces prix, perdant toute
  // précision utile dans le résumé texte aussi.
  const abs = Math.abs(n);
  let maximumFractionDigits = 2;
  if (abs > 0 && abs < 1) {
    if (abs >= 0.01) maximumFractionDigits = 4;
    else if (abs >= 0.0001) maximumFractionDigits = 6;
    else maximumFractionDigits = 8;
  }
  return n.toLocaleString("fr-FR", { maximumFractionDigits });
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

  const contexte = [];
  const fo = data.derives.funding_oi;
  contexte.push(
    fo.disponible
      ? `Funding rate : ${(fo.funding_rate * 100).toFixed(4)}% · Open interest : ${formatNombre(fo.open_interest)}`
      : `Funding rate / Open interest : indisponible${fo.raison ? ` (${fo.raison})` : ""}`
  );
  const opt = data.derives.options;
  contexte.push(
    opt.disponible
      ? `Options (Deribit) : ratio put/call (OI) ${formatNombre(opt.put_call_ratio_oi)} sur ${opt.nb_instruments} instruments`
      : `Options (Deribit) : indisponible${opt.raison ? ` (${opt.raison})` : ""}`
  );
  const fg = data.macro.fear_greed;
  contexte.push(
    fg.disponible ? `Fear & Greed : ${fg.valeur} (${fg.classification})` : `Fear & Greed : indisponible`
  );
  const dom = data.macro.dominance_btc;
  contexte.push(
    dom.disponible ? `Dominance BTC : ${formatNombre(dom.btc_pct)}%` : `Dominance BTC : indisponible`
  );
  const sp = data.macro.sp500;
  contexte.push(
    sp.disponible
      ? `S&P 500 : ${formatNombre(sp.valeur)}${sp.source_croisee ? ` (croisé ${sp.source_croisee} : ${formatNombre(sp.valeur_croisee)}${sp.ecart_anormal ? " · écart anormal" : ""})` : ""}`
      : `S&P 500 : indisponible`
  );
  const dxy = data.macro.dxy;
  contexte.push(
    dxy.disponible
      ? `DXY : ${formatNombre(dxy.valeur)}${dxy.source_croisee ? ` (contexte ${dxy.source_croisee} : ${formatNombre(dxy.valeur_croisee)})` : ""}`
      : `DXY : indisponible`
  );

  // Une entrée par niveau de pivot proche du prix (plus la seule zone la
  // plus proche de chaque côté comme avant le 25/10/2026), toujours
  // affichées même quand aucune n'est identifiée : le dire explicitement
  // plutôt que de masquer la section en silence (demande du propriétaire,
  // 24/10/2026, étendue le 25/10/2026 aux niveaux désormais multiples).
  // Le libellé opportunité/risque dépend de la position (voir
  // estZoneOpportunite) : un support n'est une opportunité que si on ne
  // détient pas déjà l'actif.
  const detientActif = !!POSITIONS_DETENUES[data.actif];
  const niveauxPivot = data.niveaux.filter((n) => n.type === "pivot");
  const zonesSupport = niveauxPivot.filter((n) => n.prix_haut <= data.prix_actuel);
  const zonesResistance = niveauxPivot.filter((n) => n.prix_bas >= data.prix_actuel);
  const zonesOpportunite = estZoneOpportunite(true, detientActif) ? zonesSupport : zonesResistance;
  const zonesRisque = estZoneOpportunite(true, detientActif) ? zonesResistance : zonesSupport;
  const formaterZone = (n, classeCss, libelle) =>
    `<span class="pastille ${classeCss}"></span> ${libelle} : ${formatNombre(n.prix_bas)}–${formatNombre(n.prix_haut)}${n.touches ? ` (${n.touches} touches)` : ""}`;
  const zones = [
    zonesOpportunite.length
      ? zonesOpportunite.map((n) => formaterZone(n, "pastille-opportunite", "Zone d'opportunité")).join("<br>")
      : `<span class="pastille pastille-opportunite"></span> Zone d'opportunité : aucune identifiée`,
    zonesRisque.length
      ? zonesRisque.map((n) => formaterZone(n, "pastille-risque", "Zone de risque")).join("<br>")
      : `<span class="pastille pastille-risque"></span> Zone de risque : aucune identifiée`,
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
    <details>
      <summary>Contexte macro et dérivés</summary>
      <p>${contexte.join("<br>")}</p>
      ${dxy.disponible && dxy.note ? `<p class="disclaimer">${dxy.note}</p>` : ""}
    </details>
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

    // Vider les lignes de prix de l'actif précédent AVANT de charger les
    // nouvelles données : sinon elles restent attachées à la série au
    // moment du setData() et faussent le calcul de l'échelle automatique
    // (bug trouvé le 24/10/2026 : l'échelle restait bloquée sur celle de
    // l'actif précédent, ex. BTC, après un changement d'actif vers ETH).
    viderLignesDePrix();
    viderCourbesMM();
    DERNIERES_DONNEES = data;
    series.applyOptions({ priceFormat: formatDePrix(data.prix_actuel) });
    series.setData(data.candles);
    // Filet de sécurité : si l'échelle des prix a été laissée en mode
    // manuel (glissé accidentel sur l'axe, voir correctif du 25/10/2026),
    // la remettre en ajustement automatique à chaque rechargement plutôt
    // que de rester bloquée sur une plage qui ne correspond plus aux
    // données affichées.
    chart.priceScale("right").applyOptions({ autoScale: true });
    // Applique la durée affichée déjà sélectionnée (1M/3M/.../Tout) : un
    // changement d'actif ou de timeframe ne doit pas réinitialiser le
    // zoom choisi par le propriétaire.
    definirPeriodeAffichee(ETAT.periode);

    redessinerIndicateurs();
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

let DERNIER_RESULTAT_LLM = null;

function reinitialiserBoutonAnalyse() {
  const bouton = document.getElementById("bouton-analyse");
  bouton.textContent = "Lancer l'analyse";
  bouton.className = "bouton-analyse";
  bouton.disabled = false;
  document.getElementById("analyse-llm").innerHTML = "";
  DERNIER_RESULTAT_LLM = null;
}

// Demande explicite du propriétaire (25/10/2026) : le LLM calcule un
// signal technique pur (haussier/baissier/neutre), jamais directement
// "acheter" ou "vendre" — il ne sait pas si l'utilisateur détient déjà
// l'actif, et "vendre" n'a pas de sens si ce n'est pas le cas. Le badge
// traduit ce signal en action selon la position choisie (case à cocher
// "Je détiens", par actif) : un même signal technique peut vouloir dire
// "achète" (pas détenu) ou "conserve" (déjà détenu).
function calculerLibelleVerdict(signal, detient) {
  if (signal === "haussier") {
    return detient ? { label: "Conserver", classe: "verdict-conserver" } : { label: "Acheter", classe: "verdict-acheter" };
  }
  if (signal === "baissier") {
    return detient ? { label: "Vendre", classe: "verdict-vendre" } : { label: "Attendre", classe: "verdict-attendre" };
  }
  if (signal === "neutre") {
    return { label: "Attendre", classe: "verdict-attendre" };
  }
  return null;
}

function afficherTexteAnalyse(resultat) {
  DERNIER_RESULTAT_LLM = resultat;
  const el = document.getElementById("analyse-llm");
  const t = resultat.texte;
  const origine = resultat.source_cache ? "servi depuis le cache (même bougie)" : "généré à l'instant";
  const detient = !!POSITIONS_DETENUES[ETAT.actif];
  const verdict = calculerLibelleVerdict(t.verdict, detient);
  el.innerHTML = `
    <div class="carte-analyse">
      <h2>Analyse</h2>
      ${verdict ? `<div class="badge-verdict ${verdict.classe}">${verdict.label}</div>` : ""}
      <h3>Tendance</h3><p>${t.tendance}</p>
      <h3>Niveaux à surveiller</h3><p>${t.niveaux}</p>
      <h3>Scénarios</h3><p>${t.scenarios}</p>
      <h3>Ce qui changerait l'analyse</h3><p>${t.ce_qui_changerait}</p>
      <h3>Risques</h3><p>${t.risques}</p>
      <p class="meta">Analyse générée automatiquement par IA, à usage strictement personnel. Le verdict peut se tromper : à vérifier par soi-même avant toute décision. ${origine}, le ${new Date(resultat.genere_le).toLocaleString("fr-FR")}.</p>
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

function initMenuIndicateurs() {
  const menu = document.getElementById("menu-indicateurs");
  menu.querySelectorAll("input[data-indicateur]").forEach((case_) => {
    case_.checked = INDICATEURS_VISIBLES[case_.dataset.indicateur];
    case_.addEventListener("change", () => {
      INDICATEURS_VISIBLES[case_.dataset.indicateur] = case_.checked;
      sauvegarderIndicateursVisibles();
      redessinerIndicateurs();
    });
  });
  // Ferme le menu si on touche ailleurs sur l'écran.
  document.addEventListener("click", (e) => {
    if (menu.open && !menu.contains(e.target)) menu.open = false;
  });
}

function redimensionnerChart() {
  const el = document.getElementById("chart");
  chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
  repositionnerToutesLesBandes();
}

function initPleinEcran() {
  const boutonOuvrir = document.getElementById("bouton-plein-ecran");
  const boutonFermer = document.getElementById("bouton-fermer-plein-ecran");
  const wrapper = document.getElementById("chart-wrapper");

  function ouvrir() {
    document.body.classList.add("plein-ecran-graphique");
    // Tentative best-effort de la vraie API Fullscreen (fonctionne sur
    // Chrome/Android ; Safari iOS l'ignore silencieusement pour un
    // élément hors <video>, le mode CSS ci-dessus reste le filet de
    // sécurité qui marche partout).
    wrapper.requestFullscreen?.().catch(() => {});
    setTimeout(redimensionnerChart, 50);
  }

  function fermer() {
    document.body.classList.remove("plein-ecran-graphique");
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    setTimeout(redimensionnerChart, 50);
  }

  boutonOuvrir.addEventListener("click", ouvrir);
  boutonFermer.addEventListener("click", fermer);
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) fermer();
  });
}

function definirPeriodeAffichee(periode) {
  if (!chart) return;
  if (periode === "tout") {
    chart.timeScale().fitContent();
    return;
  }
  // Zoom purement côté client sur les bougies déjà chargées (jusqu'à 1000
  // par appel, voir build_facts) : aucun nouvel appel réseau par clic.
  if (!DERNIERES_DONNEES || !DERNIERES_DONNEES.candles.length) return;
  const candles = DERNIERES_DONNEES.candles;
  const premiere = candles[0].time;
  const to = candles[candles.length - 1].time;
  const dateTo = new Date(`${to}T00:00:00Z`);
  let dateFrom;
  if (periode === "ytd") {
    dateFrom = new Date(Date.UTC(dateTo.getUTCFullYear(), 0, 1));
  } else {
    const jours = PERIODES_EN_JOURS[periode];
    if (!jours) return; // valeur inconnue, ne jamais deviner une plage
    dateFrom = new Date(dateTo);
    dateFrom.setUTCDate(dateFrom.getUTCDate() - jours);
  }
  const from = dateFrom.toISOString().slice(0, 10);
  chart.timeScale().setVisibleRange({ from: from < premiere ? premiere : from, to });
}

function initPeriodeAffichee() {
  document.querySelectorAll("[data-periode]").forEach((bouton) => {
    bouton.addEventListener("click", () => {
      ETAT.periode = bouton.dataset.periode;
      document.querySelectorAll("[data-periode]").forEach((b) => b.classList.toggle("actif", b === bouton));
      definirPeriodeAffichee(ETAT.periode);
    });
  });
}

function mettreAJourToggleDetention() {
  document.getElementById("label-actif-detention").textContent = ETAT.actif;
  document.getElementById("case-detention").checked = !!POSITIONS_DETENUES[ETAT.actif];
}

function initPositionDetenue() {
  mettreAJourToggleDetention();
  document.getElementById("case-detention").addEventListener("change", (e) => {
    POSITIONS_DETENUES[ETAT.actif] = e.target.checked;
    sauvegarderPositionsDetenues();
    // Recalcule immédiatement tout ce qui dépend de la position, sans
    // nouvel appel réseau : le badge verdict (signal -> action), les
    // zones du graphique et du résumé (opportunité/risque dépend de si
    // on détient déjà, voir estZoneOpportunite — signalé par le
    // propriétaire le 25/10/2026, les zones restaient identiques quelle
    // que soit la position).
    if (DERNIER_RESULTAT_LLM) afficherTexteAnalyse(DERNIER_RESULTAT_LLM);
    if (DERNIERES_DONNEES) {
      dessinerZonesNiveaux();
      afficherResume(DERNIERES_DONNEES);
    }
  });
}

function initControles() {
  document.getElementById("bouton-analyse").addEventListener("click", lancerAnalyseLLM);
  document.getElementById("selecteur-actif").addEventListener("change", (e) => {
    ETAT.actif = e.target.value;
    mettreAJourToggleDetention();
    chargerAnalyse();
  });
  document.querySelectorAll("[data-timeframe]").forEach((bouton) => {
    bouton.addEventListener("click", () => {
      ETAT.timeframe = bouton.dataset.timeframe;
      document.querySelectorAll("[data-timeframe]").forEach((b) => b.classList.toggle("actif", b === bouton));
      chargerAnalyse();
    });
  });
  initMenuIndicateurs();
  initPleinEcran();
  initPeriodeAffichee();
  initPositionDetenue();
  window.addEventListener("orientationchange", () => setTimeout(redimensionnerChart, 100));
}

async function chargerListeActifs() {
  const res = await fetch("/api/assets");
  const actifs = await res.json();
  const select = document.getElementById("selecteur-actif");
  select.innerHTML = actifs.map((a) => `<option value="${a}">${a}</option>`).join("");
  select.value = ETAT.actif;
}

function enregistrerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Installabilité PWA en moins sur ce navigateur, pas bloquant pour
      // le reste de l'app (ex. Safari iOS avant 16.4, ou contexte non
      // sécurisé en développement local).
    });
  }
}

async function main() {
  enregistrerServiceWorker();
  initChart();
  await chargerListeActifs();
  initControles();
  await chargerAnalyse();
}

main();
