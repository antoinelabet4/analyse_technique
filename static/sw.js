// Service worker minimal : satisfait le critère d'installabilité PWA
// (requis par Chrome/Android ; Safari iOS 16.4+ n'en a pas besoin mais
// le tolère). Pas de mise en cache hors-ligne pour l'instant — prévu
// pour une phase ultérieure ("dernière analyse en cache, recalcul en
// arrière-plan", brief d'origine), volontairement pas encore implémenté
// pour ne pas risquer de servir une donnée de marché périmée sans le
// signaler.

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  self.clients.claim();
});

self.addEventListener("fetch", () => {
  // Laisse passer toutes les requêtes au réseau sans interception :
  // aucune mise en cache hors-ligne pour l'instant.
});
