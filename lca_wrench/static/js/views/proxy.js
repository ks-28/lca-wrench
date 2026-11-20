// Proxy: Planet A hybrid / geo-proxy search (separate from Daten keyword search).
'use strict';
import { S, esc, explain, spellingNote, t } from '../core.js';
import { sheet } from '../sheet.js';
import { locList } from './daten.js';

function resultRow(r) {
  const why = r.why || r.comment || '';
  const kind = r.why_kind === 'geo_proxy' ? t('Geo-Proxy') : t('Hybrid');
  return `<button class="res" data-act="open-proxy" data-k="${r.id}" aria-current="${r.id === S.proxy.sel}" type="button">
    <span>${esc(r.name)}</span>
    <span class="meta">${esc(r.location || '—')}${r.product ? ` · ${esc(r.product)}` : ''} · ${esc(r.unit || '')}<span class="chip">${esc(kind)}</span></span>
    ${why ? `<span class="rdesc">${esc(why)}</span>` : ''}
  </button>`;
}

export function vProxy() {
  const rows = S.proxy.results || [];
  const loading = !!S.proxy.loading;
  const list = loading
    ? `<p class="muted" role="status">${t('Proxy-Suche läuft … oft 10–40 Sekunden (Embeddings). Bitte warten.')}</p>`
    : rows.length
      ? spellingNote(rows) + rows.map(resultRow).join('')
      : `<p class="empty">${S.proxy.q
        ? t('Kein Proxy-Treffer für «{q}». Versuch ecoinvent-Englisch (z.B. «steel production», «reinforcing steel») oder Ort weglassen.', { q: esc(S.proxy.q) })
        : t('Oben suchen: Planet-A Hybrid (Embeddings + Geo-Proxy). Treffer links; rechts öffnet sich das Prozess-Datenblatt wenn du einen Treffer anklickst.')}</p>`;

  const notices = (S.proxy.ui_notices || []).slice(0, 6)
    .map(n => `<li>${esc(n)}</li>`).join('');
  const status = loading
    ? `<div class="explain" role="status"><span class="i" aria-hidden="true">…</span><p>${t('Suche kann länger dauern — kein Fehler. Ergebnisse und Begründungen erscheinen danach.')}</p></div>`
    : (S.proxy.summary || notices)
      ? `<div class="card" style="padding:12px 14px">
          ${S.proxy.summary ? `<p style="margin:0 0 6px;font-size:14px"><b>${t('Warum diese Treffer')}</b> — ${esc(S.proxy.summary)}</p>` : ''}
          ${notices ? `<ul style="margin:0;padding-left:1.2em;font-size:13px;color:var(--muted)">${notices}</ul>` : ''}
        </div>`
      : '';

  const detail = S.proxy.act
    ? sheet(S.proxy.act, S)
    : `<section class="card">
        <h3 style="margin:0 0 8px;font-size:15px">${t('Prozess-Datenblatt')}</h3>
        <p class="empty" style="margin:0">${t('Rechts bleibt leer, bis du links einen Treffer wählst. Dann siehst du Inputs, Emissionen und Wirkungsanteile — wie unter Daten.')}</p>
      </section>`;

  const err = S.proxy.error ? `<p class="empty" role="alert">${esc(S.proxy.error)}</p>` : '';

  return `${explain(t('Proxy-Suche (Planet A) ist getrennt von der Wrench-Stichwortsuche unter Daten. Links: Treffer + Begründung. Rechts: Datenblatt nach Klick.'))}
  ${status}
  <div class="dataview proxyview">
    <aside class="card plist" aria-label="${t('Proxy-Suche')}">
      <form id="proxySearchForm" class="reslist" style="gap:6px">
        <input type="search" id="pq" placeholder="${t('z.B. steel production, reinforcing steel')}" value="${esc(S.proxy.q)}" aria-label="${t('Prozess suchen')}" ${loading ? 'disabled' : ''}>
        <input type="text" id="ploc" list="proxyLocList" value="${esc(S.proxy.loc)}" placeholder="${t('Ort, z.B. DE (optional)')}" aria-label="${t('Ort')}" autocomplete="off" ${loading ? 'disabled' : ''}>${locList('proxyLocList')}
        <button class="btn primary" type="submit" ${loading ? 'disabled' : ''}>${loading ? t('Suche …') : t('Proxy suchen')}</button>
      </form>
      ${err}
      <div class="reslist" style="margin-top:8px">${list}</div>
    </aside>
    <div style="display:flex;flex-direction:column;gap:18px;min-width:0">${detail}</div>
  </div>`;
}
