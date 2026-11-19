// Modèle de l'étude de cas « EnR et investissement », pour l'outil interactif (OJS).
//
// Port de pyelec/case_study.py, qui reste la référence : tests/test_modele_js.py
// vérifie que les deux donnent les mêmes résultats. Toute modification se fait des
// deux côtés.
//
// Unités : GW, €/MWh, coûts fixes en €/MW/an, résultats annuels en TWh, M€ et MtCO₂,
// rente inframarginale et profit par MW en k€/MW/an.

export const SOLAR = "solaire";
export const THERMAL = ["nucleaire", "ccg", "tac"];
export const TECHS = [SOLAR, ...THERMAL];
const EPS = 1e-9;

export function annuityFactor(rate, lifetime) {
  return rate === 0 ? 1 / lifetime : rate / (1 - (1 + rate) ** -lifetime);
}

/** Coût fixe annuel (€/MW/an) d'une filière : annuité et exploitation fixe. */
export function fixedCost(t) {
  return t.investissement * 1000 * annuityFactor(t.taux_actualisation, t.duree_vie)
    + t.exploitation_fixe * 1000;
}

/** Coût variable (€/MWh) d'une filière aux prix du CO₂ `co2` (€/t) et du gaz `gaz`
 *  (€/MWh PCS). */
export function variableCost(t, co2, gaz) {
  return "gaz_par_mwh" in t ? t.gaz_par_mwh * gaz + t.co2_par_tonne * co2 + t.vom : t.cout_variable;
}

/** Cas étudié, à partir des données exportées par pyelec.case_study.tool_data.
 *  params : co2 (€/t), gaz (€/MWh PCS), coutFixe ({filière: €/MW/an}, remplace le
 *  coût calculé), profil ("reel" ou "constant"). */
export function buildCase(data, params = {}) {
  const co2 = params.co2 ?? data.prix_co2;
  const gaz = params.gaz ?? data.prix_gaz;
  const options = {};
  for (const f of TECHS) {
    const t = data.filieres[f];
    options[f] = {
      cout_fixe: params.coutFixe?.[f] ?? fixedCost(t),
      cout_variable: variableCost(t, co2, gaz),
      // Émissions directes (tCO₂/MWh) : gaz brûlé par les CCG et les TAC, nulles sinon.
      emission: t.co2_par_tonne ?? 0,
    };
  }
  let solarCf = Float64Array.from(data.facteur_charge_solaire);
  if (params.profil === "constant") solarCf = solarCf.fill(mean(solarCf));
  return { options, load: Float64Array.from(data.consommation), solarCf, voll: data.voll, co2, gaz };
}

export function mean(a) {
  let s = 0;
  for (const x of a) s += x;
  return s / a.length;
}

function sum(a) {
  let s = 0;
  for (const x of a) s += x;
  return s;
}

function thermalOrder(c) {
  return [...THERMAL].sort((a, b) => c.options[a].cout_variable - c.options[b].cout_variable);
}

/** Fonctionnement heure par heure d'un parc (capacités en GW par filière). */
export function dispatch(c, caps) {
  const n = c.load.length;
  const out = { consommation: c.load };
  const available = new Float64Array(n);
  const solar = new Float64Array(n);
  const residual = new Float64Array(n);
  const price = new Float64Array(n).fill(NaN);
  const s = caps[SOLAR] ?? 0;
  for (let i = 0; i < n; i++) {
    available[i] = c.solarCf[i] * s;
    solar[i] = Math.min(available[i], c.load[i]);
    residual[i] = c.load[i] - solar[i];
    if (solar[i] < available[i]) price[i] = c.options[SOLAR].cout_variable;
  }
  out.solaire_dispo = available;
  out[SOLAR] = solar;
  const remaining = Float64Array.from(residual);
  const order = thermalOrder(c);
  for (const f of order) {
    const cap = caps[f] ?? 0;
    const cv = c.options[f].cout_variable;
    const produced = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      produced[i] = Math.min(remaining[i], cap);
      remaining[i] -= produced[i];
      if (Number.isNaN(price[i]) && produced[i] > 0 && remaining[i] <= EPS && produced[i] < cap) {
        price[i] = cv;
      }
    }
    out[f] = produced;
  }
  const curtailed = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    curtailed[i] = available[i] - solar[i];
    if (remaining[i] > EPS) price[i] = c.voll;
    if (Number.isNaN(price[i])) {
      // Production pile égale à une capacité : coût de la dernière filière en production.
      let last = NaN;
      for (const f of order) if (out[f][i] > 0) last = c.options[f].cout_variable;
      price[i] = Number.isNaN(last) ? 0 : last;
    }
  }
  out.ecretement = curtailed;
  out.delestage = remaining;
  out.residuelle = residual;
  out.prix = price;
  return out;
}

/** Indicateurs annuels d'un parc (mêmes clés que pyelec.case_study.summary). */
export function summary(c, caps, hourly = dispatch(c, caps)) {
  const n = c.load.length;
  const per = (fn) => Object.fromEntries(TECHS.map((f) => [f, fn(f)]));
  const cap = per((f) => caps[f] ?? 0);
  const energy = per((f) => sum(hourly[f]) / 1000);
  const variable = per((f) => energy[f] * c.options[f].cout_variable);
  const fixed = per((f) => (cap[f] * c.options[f].cout_fixe) / 1000);
  const margin = per((f) => {
    const cv = c.options[f].cout_variable;
    let m = 0;
    for (let i = 0; i < n; i++) m += (hourly.prix[i] - cv) * hourly[f][i];
    return m / 1000;
  });
  const shed = sum(hourly.delestage) / 1000;
  let shedHours = 0;
  let pv = 0;
  for (let i = 0; i < n; i++) {
    if (hourly.delestage[i] > EPS) shedHours++;
    pv += hourly.prix[i] * hourly[SOLAR][i];
  }
  const profit = per((f) => (cap[f] > 0 ? (margin[f] - fixed[f]) / cap[f] : NaN));
  const total = sum(Object.values(variable)) + sum(Object.values(fixed)) + shed * c.voll;
  const emissions = per((f) => energy[f] * c.options[f].emission); // MtCO₂
  return {
    capacite: cap,
    energie: energy,
    facteur_charge: per((f) => (cap[f] ? (energy[f] * 1000) / (cap[f] * 8760) : NaN)),
    ecretement: sum(hourly.ecretement) / 1000,
    delestage: shed,
    heures_delestage: shedHours,
    cout_variable: variable,
    cout_fixe: fixed,
    cout_delestage: shed * c.voll,
    cout_total: total,
    rente_inframarginale: per((f) => (cap[f] > 0 ? margin[f] / cap[f] : NaN)),
    profit,
    emissions,
    emissions_totales: sum(Object.values(emissions)),
    prix_moyen: mean(hourly.prix),
    valeur_solaire: energy[SOLAR] > 0 ? pv / sum(hourly[SOLAR]) : NaN,
    // Contrat pour différence, prix garanti = coût complet : > 0 versé, < 0 reversé.
    cfd_solaire: cap[SOLAR] > 0 ? -profit[SOLAR] * cap[SOLAR] : 0,
  };
}

// ---------------------------------------------------------------------------
// Screening curves et parc optimal

/** Filières thermiques et délestage (coût fixe nul, coût variable = VOLL). */
export function thermalOptions(c) {
  const o = { delestage: { cout_fixe: 0, cout_variable: c.voll } };
  for (const f of THERMAL) o[f] = c.options[f];
  return o;
}

/** Enveloppe inférieure des coûts totaux : [{filiere, start, end}] (heures par an). */
export function envelope(options, horizon = 8760) {
  const names = Object.keys(options);
  let current = [...names].sort(
    (a, b) => options[a].cout_fixe - options[b].cout_fixe
      || options[a].cout_variable - options[b].cout_variable,
  )[0];
  let start = 0;
  const segments = [];
  for (;;) {
    const row = options[current];
    let next = null;
    let best = Infinity;
    for (const f of names) {
      const o = options[f];
      if (!(o.cout_variable < row.cout_variable)) continue;
      const x = (o.cout_fixe - row.cout_fixe) / (row.cout_variable - o.cout_variable);
      if (x > start && x < best) [best, next] = [x, f];
    }
    if (next === null || best >= horizon) {
      segments.push({ filiere: current, start, end: horizon });
      return segments;
    }
    segments.push({ filiere: current, start, end: best });
    [current, start] = [next, best];
  }
}

/** Monotone : valeurs classées par ordre décroissant. */
export function durationCurve(values) {
  return Float64Array.from(values).sort().reverse();
}

/** Puissance dépassée pendant `hours` heures (interpolation, comme numpy.interp). */
export function level(ldc, hours) {
  const n = ldc.length;
  const x = hours - 0.5;
  if (x <= 0) return ldc[0];
  if (x >= n - 1) return ldc[n - 1];
  const i = Math.floor(x);
  return ldc[i] + (ldc[i + 1] - ldc[i]) * (x - i);
}

/** Parc optimal par les screening curves face à une monotone : [{filiere, debut, fin,
 *  bas, haut, capacite}] (heures, GW). */
export function screeningFleet(options, ldc) {
  const n = ldc.length;
  return envelope(options, n).map((s) => {
    const high = s.start > 0 ? level(ldc, s.start) : ldc[0];
    const low = s.end < n ? level(ldc, s.end) : 0;
    return { filiere: s.filiere, debut: s.start, fin: s.end, bas: low, haut: high, capacite: high - low };
  });
}

/** Consommation résiduelle (GW, bornée à 0) avec `solar` GW de solaire. */
export function residualLoad(c, solar) {
  return c.load.map((x, i) => Math.max(x - c.solarCf[i] * solar, 0));
}

function fleetFor(c, s) {
  const rows = screeningFleet(thermalOptions(c), durationCurve(residualLoad(c, s)));
  const caps = { [SOLAR]: s };
  for (const f of THERMAL) caps[f] = rows.find((r) => r.filiere === f)?.capacite ?? 0;
  return caps;
}

/** Parc optimal. `solar` fixe la capacité solaire (GW) ; null la laisse choisir
 *  (section dorée sur le coût total, convexe en capacité solaire). */
export function optimalFleet(c, solar = 0, solarMax = 1000) {
  if (solar !== null) return fleetFor(c, solar);
  const cost = (s) => summary(c, fleetFor(c, s)).cout_total;
  let [a, b] = [0, solarMax];
  const ratio = (Math.sqrt(5) - 1) / 2;
  let c1 = b - ratio * (b - a);
  let d1 = a + ratio * (b - a);
  let fc = cost(c1);
  let fd = cost(d1);
  while (b - a > 0.05) {
    if (fc < fd) {
      [b, d1, fd] = [d1, c1, fc];
      c1 = b - ratio * (b - a);
      fc = cost(c1);
    } else {
      [a, c1, fc] = [c1, d1, fd];
      d1 = a + ratio * (b - a);
      fd = cost(d1);
    }
  }
  const best = (a + b) / 2;
  return fleetFor(c, cost(best) < cost(0) ? best : 0);
}
