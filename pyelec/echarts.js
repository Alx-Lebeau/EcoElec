// Graphiques ECharts des slides : initialisation dans reveal.js.
// Inséré une fois par document par pyelec.echarts.chart (avec la bibliothèque).
//
// Chaque graphique est un <div class="echart"> qui contient son option en JSON
// (<script type="application/json">). Un graphique est dessiné quand sa slide
// s'affiche (reveal masque les autres : dimensions nulles), puis redessiné à
// chaque retour sur la slide pour rejouer l'animation. En mode impression
// (?print-pdf) ou sous decktape, sans animation.
//
// Fonctions de mise en forme : une chaîne "fn:<nom>" dans l'option est remplacée
// par la fonction FORMATTERS[<nom>] (le JSON ne transporte pas de fonctions).
(function () {
  if (window.EcoElecCharts) return;

  const NBSP = " ";
  const fr = (v, digits) =>
    Number(v).toLocaleString("fr-FR", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  const FONT = '"Helvetica Neue", Helvetica, Arial, sans-serif';

  const FORMATTERS = {
    // valeur entière (étiquettes de barres)
    entier: (p) => fr(Array.isArray(p.value) ? p.value[1] : p.value, 0),
    // nom de la série et part (segments de barres empilées)
    "serie-pourcent": (p) => p.seriesName + "\n" + fr(p.value * 100, 0) + NBSP + "%",
    "serie-pourcent-ligne": (p) => "<b>" + p.seriesName + "</b> : " + fr(p.value * 100, 0) + NBSP + "%",
    // infobulle préparée en Python (champ `tip` de la donnée)
    tip: (p) => (Array.isArray(p) ? p[0] : p).data.tip,
    // première lettre en capitale (« lundi 12 h » → « L »)
    initiale: (v) => v.charAt(0).toUpperCase(),
    // axe de 168 heures : une étiquette par jour, à midi
    midi: (i) => i % 24 === 12,
    "gw-1": (v) => (v == null ? "" : fr(v, 1) + NBSP + "GW"),
    // point [température, GW, jj/mm]
    "point-temperature": (p) =>
      p.value[2] + " (" + p.seriesName + ")<br>" + fr(p.value[0], 1) + NBSP + "°C, " + fr(p.value[1], 1) + NBSP + "GW",
    // accolade au-dessus de segments de barre : data [début, fin, demi-épaisseur de la barre (px)],
    // libellé = nom de la série
    accolade: (params, api) => {
      const x0 = api.coord([api.value(0), 0])[0];
      const x1 = api.coord([api.value(1), 0])[0];
      const y = api.coord([0, 0])[1] - api.value(2) - 10;
      const h = 8;
      return {
        type: "group",
        children: [
          {
            type: "polyline",
            shape: { points: [[x0 + 2, y], [x0 + 2, y - h], [x1 - 2, y - h], [x1 - 2, y]] },
            style: { stroke: "#64748b", lineWidth: 1.5, fill: null },
          },
          {
            type: "text",
            x: (x0 + x1) / 2,
            y: y - h - 4,
            style: {
              text: params.seriesName,
              align: "center",
              verticalAlign: "bottom",
              fill: "#334155",
              font: "bold 20px " + FONT,
            },
          },
        ],
      };
    },
  };

  function revive(node) {
    if (Array.isArray(node)) return node.map(revive);
    if (node && typeof node === "object") {
      for (const k of Object.keys(node)) node[k] = revive(node[k]);
      return node;
    }
    if (typeof node === "string" && node.startsWith("fn:")) {
      const f = FORMATTERS[node.slice(3)];
      if (!f) console.warn("pyelec.echarts : formateur inconnu", node);
      return f || node;
    }
    return node;
  }

  const charts = new Map();
  // impression reveal (?print-pdf) ou navigateur piloté (decktape, via puppeteer)
  const printing = () => /print-pdf/.test(window.location.search) || navigator.webdriver === true;

  function draw(el) {
    let chart = charts.get(el);
    const option = revive(JSON.parse(el.querySelector("script[type='application/json']").textContent));
    if (printing()) option.animation = false;
    if (!chart) {
      chart = echarts.init(el.querySelector(".echart-canvas"), null, {
        renderer: "svg",
        locale: "FR",
      });
      charts.set(el, chart);
    } else {
      chart.clear();
      chart.resize();
    }
    chart.setOption(option);
  }

  function drawIn(slide) {
    if (slide) slide.querySelectorAll(".echart").forEach(draw);
  }

  function start() {
    const R = window.Reveal;
    if (!R || !R.on) {
      document.querySelectorAll(".echart").forEach(draw);
      return;
    }
    const first = () => {
      if (printing()) document.querySelectorAll(".echart").forEach(draw);
      else drawIn(R.getCurrentSlide());
    };
    if (R.isReady()) first();
    else R.on("ready", first);
    R.on("slidechanged", (e) => drawIn(e.currentSlide));
    R.on("resize", () => charts.forEach((c) => c.resize()));
  }

  window.EcoElecCharts = { FORMATTERS, charts };
  if (document.readyState === "complete") start();
  else window.addEventListener("load", start);
})();
