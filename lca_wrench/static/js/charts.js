// Supply chain charts: tree (each visit a node) and Sankey (each process once).
'use strict';
import { S, esc, nf, pct, U, t } from './core.js';

const trunc = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;

export function treeSvg(g) {
  const nodes = g.nodes.map(n => ({ ...n, kids: [] }));
  nodes.forEach(n => { if (n.parent !== null) nodes[n.parent].kids.push(n); });
  let leaf = 0, maxD = 0;
  (function lay(n) { maxD = Math.max(maxD, n.depth); if (!n.kids.length) n.y = leaf++; else { n.kids.forEach(lay); n.y = (n.kids[0].y + n.kids[n.kids.length - 1].y) / 2; } })(nodes[0]);
  const W = 224, H = 48, GX = 60, GY = 14, X = d => 12 + d * (W + GX), Y = y => 12 + y * (H + GY);
  const width = X(maxD) + W + 12, height = Y(Math.max(leaf - 1, 0)) + H + 12;
  const edges = nodes.slice(1).map(k => {
    const p = nodes[k.parent], x1 = X(p.depth) + W, y1 = Y(p.y) + H / 2, x2 = X(k.depth), y2 = Y(k.y) + H / 2, mx = (x1 + x2) / 2;
    return `<path class="gedge ${k.share >= 0.25 ? 'hot' : k.share < 0 ? 'neg' : ''}" d="M${x1} ${y1}C${mx} ${y1},${mx} ${y2},${x2} ${y2}" stroke-width="${Math.max(1.5, Math.min(30, Math.abs(k.share) * 30))}"/>`;
  }).join('');
  const svgNodes = nodes.map(n => `<g class="gnode ${n.depth === 0 ? 'root' : ''} ${n.share >= 0.25 && n.depth > 0 ? 'hot' : ''} ${n.share < 0 ? 'neg' : ''} ${S.gsel === n.i ? 'sel' : ''}" data-act="gsel" data-k="${n.i}" tabindex="0" role="button" aria-label="${esc(n.name)}, ${pct(n.share)}"><title>${esc(n.name)} (${esc(n.location)})</title><rect x="${X(n.depth)}" y="${Y(n.y)}" width="${W}" height="${H}" rx="7"/><text x="${X(n.depth) + 10}" y="${Y(n.y) + 19}" font-size="12.5">${esc(trunc(n.name, 30))}</text><text class="m" x="${X(n.depth) + 10}" y="${Y(n.y) + 37}">${esc(n.location)} · ${nf(n.amount)} ${esc(n.unit)} · ${pct(n.share)}</text></g>`).join('');
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${t('Lieferketten-Baum')}">${edges}${svgNodes}</svg>`;
}

// Sankey: product on the right, suppliers to the left. Node height = cumulative impact (mode 'cum') or the
// activity's own direct emissions (mode 'own'); in 'own' the links only show who supplies whom, at a fixed width.
export function sankeySvg(sk, mode = 'cum') {
  const own = mode === 'own';
  const nodes = sk.nodes.map(n => ({ ...n, v: own ? n.direct : n.value, inL: [], outL: [] }));
  const byKey = new Map(nodes.map(n => [n.key, n]));
  const links = sk.links.filter(l => !l.loop).map(l => ({ ...l, s: byKey.get(l.source), t: byKey.get(l.target) }));
  links.forEach(l => { l.s.outL.push(l); l.t.inL.push(l); });
  const maxL = Math.max(0, ...nodes.map(n => n.layer));
  const cols = Array.from({ length: maxL + 1 }, (_, i) => nodes.filter(n => n.layer === i));
  const H = Math.max(360, Math.min(760, 70 + 34 * Math.max(...cols.map(c => c.length)))), GAP = 10, NW = 14, COLW = 230, PADL = 16, PADT = 14;
  const k = Math.min(...cols.filter(c => c.length).map(c => (H - GAP * (c.length - 1)) / Math.max(c.reduce((a, n) => a + Math.abs(n.v), 0), 1e-300)));
  const width = PADL + maxL * COLW + NW + 230;
  const x = n => PADL + (maxL - n.layer) * COLW;
  // place columns from the product leftwards, ordering each by where its links go
  cols.forEach((col, li) => {
    if (li > 0) col.forEach(n => { const w = n.outL.reduce((a, l) => a + Math.abs(l.value), 0) || 1; n.bc = n.outL.reduce((a, l) => a + (l.t.y + l.t.h / 2) * Math.abs(l.value), 0) / w; });
    col.sort((a, b) => li === 0 ? 0 : (a.bc ?? 0) - (b.bc ?? 0));
    let y = PADT + (H - (col.reduce((a, n) => a + Math.max(2, Math.abs(n.v) * k), 0) + GAP * (col.length - 1))) / 2;
    col.forEach(n => { n.h = Math.max(2, Math.abs(n.v) * k); n.y = y; y += n.h + GAP; });
  });
  nodes.forEach(n => {
    n.outL.sort((a, b) => a.t.y - b.t.y); n.inL.sort((a, b) => a.s.y - b.s.y);
    if (own) {  // spread the thin links evenly over the bar
      n.outL.forEach((l, j) => { l.w = 1.5; l.y0 = n.y + n.h * (j + 0.5) / n.outL.length; });
      n.inL.forEach((l, j) => { l.y1 = n.y + n.h * (j + 0.5) / n.inL.length; });
      return;
    }
    let o = n.y; n.outL.forEach(l => { l.w = Math.max(1, Math.abs(l.value) * k); l.y0 = o + l.w / 2; o += l.w; });
    let i = n.y; n.inL.forEach(l => { l.y1 = i + Math.max(1, Math.abs(l.value) * k) / 2; i += Math.max(1, Math.abs(l.value) * k); });
  });
  const tot = Math.abs(sk.total) || 1;
  const paths = links.map(l => {
    const x0 = x(l.s) + NW, x1 = x(l.t), mx = (x0 + x1) / 2;
    const cls = own ? '' : l.value < 0 ? 'neg' : Math.abs(l.value) / tot >= 0.25 ? 'hot' : '';
    return `<path class="sk-link ${cls}" d="M${x0} ${l.y0}C${mx} ${l.y0},${mx} ${l.y1},${x1} ${l.y1}" stroke-width="${l.w}"><title>${esc(l.s.name)} → ${esc(l.t.name)}: ${nf(l.value)} ${esc(U())} (${pct(l.value / tot)}), ${nf(l.amount)} ${esc(l.s.unit)}</title></path>`;
  }).join('');
  const rects = nodes.map(n => {
    const share = n.v / tot, lx = x(n) + NW + 6, ty = n.y + Math.min(n.h / 2, 14);
    return `<g class="sk-node ${n.layer === 0 ? 'root' : ''} ${share >= 0.25 && n.layer ? 'hot' : ''} ${n.v < 0 ? 'neg' : ''} ${S.sksel === n.key ? 'sel' : ''}" data-act="sksel" data-k="${n.key}" tabindex="0" role="button" aria-label="${esc(n.name)}, ${pct(share)}">
      <title>${esc(n.name)} (${esc(n.location)})\n${t('kumuliert {v} ({p})', { v: `${nf(n.value)} ${esc(U())}`, p: pct(n.value / tot) })}\n${t('direkt {v} ({p})', { v: `${nf(n.direct)} ${esc(U())}`, p: pct(n.direct / tot) })}</title>
      <rect x="${x(n)}" y="${n.y}" width="${NW}" height="${n.h}" rx="2"/>
      <text x="${lx}" y="${ty}" font-size="12">${esc(trunc(n.name, n.layer === 0 ? 34 : 28))}</text>
      <text class="m" x="${lx}" y="${ty + 14}">${esc(n.location || '')} · ${pct(share)}</text></g>`;
  }).join('');
  const height = PADT * 2 + H;
  return { svg: `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${t('Sankey-Diagramm der Lieferkette')}">${paths}${rects}</svg>`, loops: sk.links.length - links.length };
}
