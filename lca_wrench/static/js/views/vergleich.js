// Vergleich: products across projects, original against working copy.
'use strict';
import { S, esc, nf, U, explain, methodInfo, methodLabel, t } from '../core.js';

export function vVergleich() {
  const res = S.cmpRes || [];
  const ok = res.filter(r => !r.error && r.coverage !== 'missing');  // a method without factors for a product gives 0
  const max = Math.max(...ok.map(r => Math.abs(r.score)), 1e-15);  // bars start at zero: absolute scores, not differences
  const rows = res.map((r, i) => r.error
    ? `<div class="cmp"><span>${esc(S.cmp[i]?.label || r.id)}</span><span class="muted">${esc(r.error)}</span><span></span><button class="iconbtn" data-act="cmp-del" data-k="${i}" aria-label="${t('Entfernen')}">×</button></div>`
    : `<div class="cmp"><span title="${esc(r.project)}">${esc(r.name)} <span class="muted">${esc(r.location)} · ${nf(r.amount)} ${esc(r.unit)}</span><br><span class="chip ${r.copy ? 'hot' : ''}">${esc(r.project)}</span>${r.used && (S.st.background?.options.length || 0) > 1 ? ` <span class="chip ${r.background ? 'acc' : ''}" title="${t('Hintergrunddaten dieser Rechnung (unter Start wählen)')}">${esc(r.used.join(' + '))}</span>` : ''}${coverChip(r)}</span>
      <span class="t"><i class="${r.copy ? 'copy' : ''}" style="width:${r.coverage === 'missing' ? 0 : Math.max(0, Math.abs(r.score) / max * 100)}%"></i></span>
      <span class="num ${r.coverage === 'missing' ? 'muted' : ''}" style="text-align:right">${r.coverage === 'missing' ? '–' : nf(r.score)}<br><span class="muted" style="font-size:12px">${esc(U())}</span></span>
      <button class="iconbtn" data-act="cmp-del" data-k="${i}" aria-label="${t('Entfernen')}">×</button></div>`).join('');
  const ch = S.st.changes;
  const changes = S.st.is_copy ? `<section class="card" style="display:flex;flex-direction:column;gap:10px">
      <h3>${t('Änderungen an Hintergrunddaten in dieser Arbeitskopie')}</h3>
      ${ch.length ? `<div class="tblwrap"><table class="tbl"><thead><tr><th>${t('Prozess')}</th><th>${t('Input')}</th><th>${t('vorher')}</th><th>${t('neu')}</th><th></th></tr></thead><tbody>
      ${ch.map(c => `<tr><td><button class="linkbtn" data-act="open" data-k="${c.activity_id}">${esc(c.activity)}</button> <span class="muted">${esc(c.location)}</span></td><td>${esc(c.input)}</td><td class="num nw">${nf(c.old)} ${esc(c.unit)}</td><td class="num nw">${nf(c.new)} ${esc(c.unit)}</td><td><button class="btn small" data-act="undo-copy" data-k="${c.exchange}">${t('Rückgängig')}</button></td></tr>`).join('')}
      </tbody></table></div>` : `<p class="empty">${t('Noch keine Änderungen. Ändere im Datenblatt eine Menge.')}</p>`}
      ${S.fu ? `<div><button class="btn primary" data-act="cmp-orig-copy">${t('«{name}»: Original gegen Arbeitskopie vergleichen', { name: esc(S.fu.name) })}</button></div>` : ''}
    </section>` : '';
  return `${explain(t('Hier vergleichst du Produkte über Projekte hinweg, zum Beispiel dasselbe Produkt im Original und in einer Arbeitskopie mit geänderten Hintergrunddaten. Für Vergleiche innerhalb eines Projekts mit mehreren Methoden ist «Rechnen» bequemer.'))}
  <section class="card" style="display:flex;flex-direction:column;gap:14px">
    <div class="row" style="justify-content:space-between"><h3>${t('Vergleich · {method} ({unit})', { method: esc(methodLabel(methodInfo())), unit: esc(U()) })}</h3>${S.cmp.length ? `<span class="row" style="gap:6px">${(S.st.background?.options.length || 0) > 1 ? `<button class="btn small" data-act="cmp-each-bg" title="${t('Das letzte Produkt im Vergleich nochmals mit jeder Hintergrund-Datenbank (Prozessdaten und Szenarien) rechnen, z.B. heute gegen 2050')}">${t('Mit jedem Hintergrund')}</button>` : ''}<button class="btn small" data-act="cmp-clear">${t('Alle entfernen')}</button></span>` : ''}</div>
    ${coverNote(res)}
    ${S.cmp.length ? `<div class="stack">${rows}</div>` : `<p class="empty">${t('Noch nichts im Vergleich. Füge Prozesse über «Zum Vergleich» im Datenblatt oder beim Ergebnis hinzu.')}</p>`}
    ${flowmapSwitch()}
  </section>${changes}`;
}

// whether the method has factors for the elementary flows of each product: its own, or partly through the flow mapping
function coverChip(r) {
  if (r.completed) return ` <span class="chip acc" title="${t('Ein Teil der Faktoren ist für Subkompartimente ergänzt (Schalter und Liste unter Ergebnis).')}">${t('mit ergänzten Faktoren')}</span>`;
  if (r.coverage === 'mapped') return ` <span class="chip acc" title="${t('Ein Teil der Faktoren kommt über die Flusszuordnung: {src}', { src: esc(S.st.flowmap?.source || '') })}">${t('≈ über Flusszuordnung')}</span>`;
  if (r.coverage === 'missing') return ` <span class="chip hot" title="${t('Die Methode hat keine Faktoren für diese Elementarflüsse; das Ergebnis wäre 0.')}">${t('keine Faktoren für {lists}', { lists: esc((r.missing || []).join(', ')) })}</span>`;
  return '';
}

function coverNote(res) {
  if (!S.cmpCover || !res.some(r => r.coverage === 'missing')) return '';
  const what = S.cmpCover.size
    ? t('Oben stehen hier nur die {n} Methoden mit Faktoren für alle Produkte im Vergleich (≈: teils über die Flusszuordnung).', { n: S.cmpCover.size })
    : t('Keine Methode hat Faktoren für alle Produkte hier.') + (S.st.flowmap?.links?.length && !S.st.flowmap.enabled ? ' ' + t('Die Flusszuordnung unten kann fehlende Faktoren ergänzen.') : '');
  return `<div class="warnbox"><span><b>${t('Diese Methode deckt nicht alle Produkte ab.')}</b> ${what}</span></div>`;
}

function flowmapSwitch() {
  const fm = S.st.flowmap;
  if (!fm || !fm.links?.length) return '';
  return `<div style="display:flex;flex-direction:column;gap:4px">
    <label class="row" style="gap:6px;font-size:13.5px"><input type="checkbox" id="flowmapChk" ${fm.enabled ? 'checked' : ''}> ${t('Fehlende Faktoren über die Flusszuordnung ergänzen ({lists})', { lists: esc(fm.links.map(l => l.join(' ↔ ')).join(', ')) })}</label>
    <p class="muted" style="font-size:12.5px">${t('Eine Methode für die eine Liste von Elementarflüssen bekommt Faktoren für die zugeordneten Flüsse der anderen. Nur wo geprüft: Klima, Versauerung, Eutrophierung, Sommersmog, ionisierende Strahlung und Landnutzung; Ozonabbau nur für ecoinvent-Flüsse, Mineralien nur für EF-Flüsse. Nie für Feinstaub, Toxizität, Wasser und Energieressourcen. Gilt für alle Rechnungen. Quelle: {src}.', { src: esc(fm.source) })}</p>
  </div>`;
}
