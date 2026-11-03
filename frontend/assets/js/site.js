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
  const isDemo =
    location.hostname.endsWith("github.io") || params.get("demo") === "1";

  function asset(path) {
    const clean = path.replace(/^\//, "");
    return basePath === "/" ? clean : basePath + clean;
  }

  function page(path) {
    return asset(path);
  }

  window.LeadHunterSite = { basePath, isDemo, asset, page };

  if (isDemo && !document.getElementById("demo-banner")) {
    document.addEventListener("DOMContentLoaded", () => {
      const bar = document.createElement("div");
      bar.id = "demo-banner";
      bar.className = "alert alert-warning text-center mb-0 rounded-0";
      bar.textContent =
        "Демо-режим (GitHub Pages): интерфейс с примерными данными, без backend. Полная версия — через Docker или облачный деплой.";
      document.body.prepend(bar);
    });
  }
})();
