// Unsicherheit: coupled Monte-Carlo for a calculation setup (box plots and "A better than B").
'use strict';
import { S, esc, nf, pct, explain, methodInfo, methodLabel, t } from '../core.js';

export const MC_N = [100, 250, 500, 1000, 2000, 5000, 10000];

const trunc = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;
const sig = () => JSON.stringify([S.setup.fus.map(f => [f.id, f.amount]), S.setup.methods]);
const range = (a, b) => `<span class="nw">${nf(a)} – ${nf(b)}</span>`;
const note = text => `<div class="warnbox"><b>${t('Hinweis')}</b><span>${esc(text)}</span></div>`;

export const mcSignature = sig;

export function mcSection() {
  const mc = S.mc, running = mc.job && mc.job.state === 'läuft';
  const can = S.setup.fus.length && S.setup.methods.length;
  const head = `<div class="row" style="justify-content:space-between;align-items:flex-end">
      <div style="flex:1 1 320px"><h3>${t('Unsicherheit')}</h3><span class="muted" style="font-size:13px">${t('Wie sicher sind die Ergebnisse? Die Datenbank-Unsicherheiten werden n-mal zufällig gezogen.')}</span></div>
      <div class="row"><label class="f">${t('Ziehungen')}<select id="mcN" ${running ? 'disabled' : ''}>${MC_N.map(n => `<option value="${n}" ${n === mc.n ? 'selected' : ''}>${nf(n)}</option>`).join('')}</select></label>
      <button class="btn primary" data-act="mc-start" ${can && !running ? '' : 'disabled'}>${mc.res ? t('Neu ziehen') : t('Unsicherheit berechnen')}</button></div></div>
    ${mc.n >= 5000 && !running ? `<p class="muted" style="font-size:13px">${t('{n} Ziehungen dauern einige Minuten, bei ecoinvent auch länger. Die Rechnung läuft im Hintergrund, du kannst weiterarbeiten.', { n: nf(mc.n) })}</p>` : ''}`;
  let body = '';
  if (mc.error) body = note(mc.error);
  else if (running) {
    const j = mc.job, p = j.n ? j.done / j.n : 0;
    body = `<div role="progressbar" aria-valuemin="0" aria-valuemax="${j.n}" aria-valuenow="${j.done}" aria-label="${t('Fortschritt')}"><div class="share"><div class="t"><i style="width:${p * 100}%"></i></div><span>${nf(j.done)} / ${nf(j.n)}</span></div></div>
      <p class="muted" style="font-size:13px">${t('Läuft im Hintergrund auf mehreren Prozessorkernen, {s} s bisher. Du kannst weiterarbeiten.', { s: nf(j.seconds) })}</p>`;
  } else if (mc.res) body = results(mc.res);
  return `<section class="card" id="mcCard" style="display:flex;flex-direction:column;gap:12px">${head}${body}</section>`;
}

function results(r) {
  const stale = S.mc.sig !== sig() ? `<div class="warnbox"><b>${t('Veraltet')}</b><span>${t('Die Rechnung wurde seither geändert. Zeigt die Ziehung von vorher; «Neu ziehen» rechnet sie neu.')}</span></div>` : '';
  const k = Math.min(S.mc.k, r.methods.length - 1), m = r.methods[k], mi = methodInfo(m.id);
  const seg = r.methods.length > 1 ? `<div class="seg" role="group" aria-label="${t('Methode')}">${r.methods.map((x, i) => `<button data-act="mc-method" data-k="${i}" aria-pressed="${i === k}">${esc(methodLabel(methodInfo(x.id)))}</button>`).join('')}</div>` : '';
  const rows = r.fus.map((f, j) => {
    const med = r.median[k][j], cv = r.mean[k][j] ? r.std[k][j] / Math.abs(r.mean[k][j]) : 0;
    return `<tr><td>${esc(f.name)} <span class="muted">${esc(f.location || '')}</span></td><td class="num">${nf(r.reference[k][j])}</td><td class="num">${nf(med)}</td><td class="num">${range(r.p5[k][j], r.p95[k][j])}</td><td class="num">${pct(cv)}</td></tr>`;
  }).join('');
  return `${stale}${explain(t('<b>Boxplot:</b> Der Kasten umfasst die mittleren 50 % der Ziehungen, der Strich darin ist der Median, die Linien reichen von 5 % bis 95 %. Die Raute ist das normale Ergebnis ohne Zufall. <b>Gekoppelt:</b> In jeder Ziehung gelten für alle Produkte dieselben Datenwerte. Darum sagt «A besser als B» etwas über den echten Unterschied und nicht über Rauschen.'))}
    <div class="row" style="justify-content:space-between"><span class="muted" style="font-size:13px">${t('{n} Ziehungen, {s} s, Startwert {seed}, {w} Kerne', { n: nf(r.n), s: nf(r.seconds ?? S.mc.job.seconds), seed: r.seed, w: r.workers })}</span>${seg}</div>
    <div class="gwrap">${boxplot(r, k)}</div>
    <div class="tblwrap"><table class="tbl restbl"><thead><tr><th>${t('Produkt')}</th><th>${t('Ohne Zufall')}<br><span class="muted" style="font-weight:400">${esc(m.unit)}</span></th><th>${t('Median')}</th><th>${t('5 % bis 95 %')}</th><th title="${t('Standardabweichung geteilt durch Mittelwert')}">${t('Streuung')}</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${r.fus.length > 1 ? `<h3 style="margin-top:6px">${t('Wie oft ist A besser als B?')}</h3><p class="muted" style="font-size:13px">${t('Anteil der Ziehungen, in denen das Produkt in der Zeile eine kleinere Wirkung hat als das Produkt in der Spalte ({method}, kleiner = besser).', { method: esc(methodLabel(mi)) })}</p>${betterTable(r, k)}` : ''}`;
}

function boxplot(r, k) {
  const n = r.fus.length, W = 760, L = 220, R = 24, RH = 38, T = 12, B = 34, H = T + n * RH + B;
  const all = [...r.p5[k], ...r.p95[k], ...r.reference[k]];
  // wide spread between products: logarithmic axis so that small products stay readable
  const log = Math.min(...all) > 0 && Math.max(...all) / Math.min(...all) > 30;
  const lo = log ? Math.min(...all) / 1.3 : Math.min(0, ...all), hi = Math.max(...all) * (log ? 1.3 : 1.04) || 1;
  const sc = log ? Math.log : (v => v);
  const X = v => L + (sc(v) - sc(lo)) / (sc(hi) - sc(lo) || 1) * (W - L - R);
  const ticks = Array.from({ length: 5 }, (_, i) => log ? Math.exp(sc(lo) + (sc(hi) - sc(lo)) * i / 4) : lo + (hi - lo) * i / 4);
  const grid = ticks.map(v => `<line class="mc-grid" x1="${X(v)}" x2="${X(v)}" y1="${T}" y2="${H - B}"/><text class="m" x="${X(v)}" y="${H - B + 16}" text-anchor="middle" font-size="11">${nf(v)}</text>`).join('');
  const rows = r.fus.map((f, j) => {
    const y = T + j * RH + RH / 2;
    return `<text x="${L - 10}" y="${y + 4}" text-anchor="end" font-size="12.5"><title>${esc(f.name)}</title>${esc(trunc(f.name, 32))}</text>
      <line class="mc-whisk" x1="${X(r.p5[k][j])}" x2="${X(r.p95[k][j])}" y1="${y}" y2="${y}"/>
      <rect class="mc-box" x="${X(r.p25[k][j])}" y="${y - 9}" width="${Math.max(1, X(r.p75[k][j]) - X(r.p25[k][j]))}" height="18" rx="3"/>
      <line class="mc-med" x1="${X(r.median[k][j])}" x2="${X(r.median[k][j])}" y1="${y - 9}" y2="${y + 9}"/>
      <path class="mc-ref" d="M${X(r.reference[k][j])} ${y - 6}l5 6-5 6-5-6z"><title>${t('Ohne Zufall: {v}', { v: nf(r.reference[k][j]) })}</title></path>`;
  }).join('');
  // scales down with the card, never above its natural size
  return `<svg class="fit" style="max-width:${W}px" viewBox="0 0 ${W} ${H}" role="img" aria-label="${t('Boxplot der Ziehungen')}">${grid}${rows}<text class="m" x="${W - R}" y="${H - 4}" text-anchor="end" font-size="11">${esc(r.methods[k].unit)}${log ? t(', logarithmische Achse') : ''}</text></svg>`;
}

function betterTable(r, k) {
  const b = r.better[k];
  const cell = v => {
    if (v === null) return '<td class="muted" style="text-align:center">–</td>';
    const cls = v >= 0.95 ? 'mc-yes' : v <= 0.05 ? 'mc-no' : '';
    return `<td class="num mc-cell ${cls}" style="text-align:center">${pct(v)}</td>`;
  };
  return `<div class="tblwrap"><table class="tbl"><thead><tr><th></th>${r.fus.map(f => `<th title="${esc(f.name)}">${esc(trunc(f.name, 22))}</th>`).join('')}</tr></thead><tbody>
    ${r.fus.map((f, i) => `<tr><td title="${esc(f.name)}">${esc(trunc(f.name, 32))}</td>${b[i].map(cell).join('')}</tr>`).join('')}</tbody></table></div>`;
}

// ---------- which data drive the spread ----------

export const SENS_N = [300, 1000, 3000];

export function sensSection() {
  const sn = S.sens, running = sn.job && sn.job.state === 'läuft';
  const cs = S.setup, k = Math.min(S.mc.k, cs.methods.length - 1), mi = methodInfo(cs.methods[k]);
  const j = Math.min(sn.j, cs.fus.length - 1);
  const head = `<div class="row" style="justify-content:space-between;align-items:flex-end">
      <div style="flex:1 1 320px"><h3>${t('Was treibt die Streuung?')}</h3><span class="muted" style="font-size:13px">${t('Welche unsicheren Datenwerte bestimmen, ob das Ergebnis eher hoch oder tief ausfällt: Rangkorrelation, Beitrag zur Varianz (CTV) und Sobol-Indizes.')}</span></div>
      <div class="row"><label class="f">${t('Produkt')}<select id="sensFu" ${running ? 'disabled' : ''}>${cs.fus.map((f, i) => `<option value="${i}" ${i === j ? 'selected' : ''}>${esc(trunc(f.name, 40))}</option>`).join('')}</select></label>
      <label class="f">${t('Ziehungen')}<select id="sensN" ${running ? 'disabled' : ''}>${SENS_N.map(n => `<option value="${n}" ${n === sn.n ? 'selected' : ''}>${nf(n)}</option>`).join('')}</select></label>
      <button class="btn primary" data-act="sens-start" ${running ? 'disabled' : ''}>${sn.res ? t('Neu analysieren') : t('Analysieren')}</button></div></div>
    <p class="muted" style="font-size:12.5px">${t('Methode: {method} (wie oben gewählt). Dauert etwa so lange wie eine Unsicherheitsrechnung mit gleich vielen Ziehungen. Für Sobol-Indizes sind 1000 Ziehungen oder mehr gut.', { method: esc(methodLabel(mi)) })}</p>`;
  let body = '';
  if (sn.error) body = note(sn.error);
  else if (running) body = `<p class="busy" role="status">${esc(sn.job.phase || t('Läuft …'))} (${nf(sn.job.seconds)} s)</p>`;
  else if (sn.res) body = sensResults(sn.res);
  return `<section class="card" id="sensCard" style="display:flex;flex-direction:column;gap:12px">${head}${body}</section>`;
}

const idx = (v, lo, hi) => `<span class="num">${Math.max(v, 0).toFixed(2)}</span><br><span class="muted nw" style="font-size:11.5px">${Math.max(lo, 0).toFixed(2)}–${Math.max(hi, 0).toFixed(2)}</span>`;

function sensRow(e, i, max) {
  const vars = { supplier: esc(e.supplier.name), consumer: `${esc(e.consumer.name)}${e.consumer.location ? ` <span class="muted">${esc(e.consumer.location)}</span>` : ''}`, categories: e.supplier.categories ? esc(e.supplier.categories) + ', ' : '' };
  const what = e.kind === 'input' ? t('<b>{supplier}</b> <span class="muted">als Input von</span> {consumer}', vars) : t('<b>{supplier}</b> <span class="muted">{categories}Emission von</span> {consumer}', vars);
  const dir = e.rho > 0 ? t('höher → Ergebnis höher') : t('höher → Ergebnis tiefer');
  const so = e.sobol;
  return `<tr><td class="num">${i + 1}</td><td>${what}${e.significant ? '' : ` <span class="chip">${t('nicht eindeutig')}</span>`}</td>
    <td><div class="share" title="${t('Rangkorrelation (Spearman) zwischen dem Datenwert und dem Ergebnis')}"><div class="t"><i class="${e.rho < 0 ? 'neg' : ''}" style="width:${Math.abs(e.rho) / max * 100}%"></i></div><span class="num">${e.rho > 0 ? '+' : '−'}${Math.abs(e.rho).toFixed(2)}</span></div></td>
    <td class="num" style="text-align:right">${pct(e.ctv)}</td>
    <td style="text-align:right">${so ? idx(so.s1, so.s1_lo, so.s1_hi) : '<span class="muted">–</span>'}</td>
    <td style="text-align:right">${so ? idx(so.st, so.st_lo, so.st_hi) : '<span class="muted">–</span>'}</td>
    <td class="muted nw" style="font-size:13px">${dir}<br>${t('Streuung des Werts ±{v}', { v: pct(e.rel_sd) })}</td></tr>`;
}

function sensResults(r) {
  const main = r.entries.filter(e => !e.extra), extra = r.entries.filter(e => e.extra);
  const max = Math.max(...r.entries.map(e => Math.abs(e.rho)), 1e-9);
  const rows = main.map((e, i) => sensRow(e, i, max)).join('')
    + (extra.length ? `<tr><td colspan="7" class="muted" style="font-size:13px;padding-top:14px">${t('Stark nach Sobol, aber schwach korreliert (nicht gleichförmige Wirkung oder Wechselwirkung):')}</td></tr>`
      + extra.map((e, i) => sensRow(e, main.length + i, max)).join('') : '');
  const sob = r.sobol;
  const sums = [
    r.linear_share != null ? t('Die linearen Beiträge (CTV) zusammen ergeben {v} der Varianz aus den Ziehungen; nahe 100 % heisst, das Ergebnis verhält sich fast linear.', { v: pct(r.linear_share) }) : '',
    t('Die {k} Datenwerte oben tragen linear {v} der Varianz bei.', { k: nf(main.length), v: pct(r.ctv_top) }),
    sob ? t('Sobol für die {k} wichtigsten Datenwerte aus {pairs} Paaren von Ziehungen: allein zusammen S₁ = {s1}, mit Wechselwirkungen S_T = {st}.', { k: nf(sob.k), pairs: nf(sob.pairs), s1: Math.max(sob.s1_sum, 0).toFixed(2), st: sob.st_sum.toFixed(2) }) : '',
  ].filter(Boolean).join(' ');
  return `${explain(t('<b>Rangkorrelation</b> (−1 bis +1): Je weiter weg von 0, desto stärker bestimmt dieser Datenwert, ob das Ergebnis in einer Ziehung hoch oder tief ausfällt. Werte unter {floor} sind bei dieser Zahl Ziehungen nicht von Zufall zu unterscheiden. <b>CTV</b> (Beitrag zur Varianz): Ableitung des Ergebnisses im Quadrat mal Varianz des Datenwerts, als Anteil an der Summe über alle Datenwerte; genau für kleine Streuungen, ohne zusätzliche Ziehungen. <b>Sobol S₁</b>: Anteil der Varianz, der allein von diesem Datenwert kommt. <b>Sobol S_T</b>: inklusive Wechselwirkungen mit anderen Datenwerten; S_T deutlich über S₁ heisst Wechselwirkung. Darunter das 95-%-Intervall. <b>Vorgehen:</b> Aus allen Datenwerten werden die {k} mit dem grössten möglichen Beitrag ausgewählt und in {n} Ziehungen mitgeschrieben.', { k: nf(r.candidates), n: nf(r.n), floor: (2 / Math.sqrt(r.n)).toFixed(2) }))}
    <p class="muted" style="font-size:13px">${t('{name}: {median} im Median, 5 % bis 95 %: {range}.', { name: esc(r.fu.name), median: `${nf(r.score.median)} ${esc(r.method.unit)}`, range: range(r.score.p5, r.score.p95) })} ${sums}</p>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>#</th><th>${t('Datenwert')}</th><th>${t('Korrelation')}</th><th style="text-align:right">CTV</th><th style="text-align:right">Sobol S₁</th><th style="text-align:right">Sobol S_T</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
