(function () {
  function detectBasePath() {
    if (location.hostname.endsWith("github.io")) {
      const match = location.pathname.match(/^\/([^/]+)\//);
      if (match) return `/${match[1]}/`;
    }
    return "/";
  }

  const params = new URLSearchParams(location.search);
  const basePath = detectBasePath();
  const publicCfg = window.LeadHunterPublicConfig || {};
  const remoteApi = (publicCfg.apiBase || "").trim().replace(/\/$/, "");

  const isDemo =
    (location.hostname.endsWith("github.io") && !remoteApi) ||
    (params.get("demo") === "1" && !remoteApi);

  function asset(path) {
    const clean = path.replace(/^\//, "");
    return basePath === "/" ? clean : basePath + clean;
  }

  function page(path) {
    return asset(path);
  }

  window.LeadHunterSite = { basePath, isDemo, remoteApi, asset, page };

  if (isDemo && !document.getElementById("demo-banner")) {
    document.addEventListener("DOMContentLoaded", () => {
      const bar = document.createElement("div");
      bar.id = "demo-banner";
      bar.className = "alert alert-warning text-center mb-0 rounded-0";
      bar.textContent =
        "Демо-режим: примерные данные без backend. Полная версия — Render (см. docs/cloud-deploy.md) или Docker локально.";
      document.body.prepend(bar);
    });
  }
})();
