// Proxy: Planet A hybrid / geo-proxy search (separate from Daten keyword search).
'use strict';
import { S, esc, explain, spellingNote, t } from '../core.js';
import { sheet } from '../sheet.js';
import { locList } from './daten.js';

export function vProxy() {
  const rows = S.proxy.results || [];
  const list = rows.length
    ? spellingNote(rows) + rows.map(r => `<button class="res" data-act="open-proxy" data-k="${r.id}" aria-current="${r.id === S.proxy.sel}"${r.comment || r.why ? ` title="${esc(r.comment || r.why)}"` : ''}><span>${esc(r.name)}</span><span class="meta">${esc(r.location)}${r.why ? ` <span class="chip" title="${esc(r.why)}">${t('Proxy')}</span>` : r.region ? ` <span class="chip">${t('statt {loc}', { loc: esc(r.region) })}</span>` : ''} · ${esc(r.unit || '')}${r.database ? ' · ' + esc(r.database) : ''}</span></button>`).join('')
    : `<p class="empty">${S.proxy.q ? t('Kein Proxy-Treffer. Versuch einen anderen Begriff oder Ort.') : t('Proxy-Suche: Planet-A Hybrid (Embeddings + Geo-Proxy). Zuerst unter Daten die Wrench-Suche nutzen; bei keinem exakten Orts-Treffer hierher.')}</p>`;
  const detail = S.proxy.act ? sheet(S.proxy.act, S) : `<section class="card"><p class="empty">${t('Wähle links einen Prozess.')}</p></section>`;
  const err = S.proxy.error ? `<p class="empty" role="alert">${esc(S.proxy.error)}</p>` : '';
  return `${explain(t('Eigene Schiene für Proxy-Suche (Planet A). Die Daten-Suche bleibt die Wrench-Stichwortsuche. Kein Mischen der Trefferlisten.'))}
  <div class="dataview">
    <aside class="card plist" aria-label="${t('Proxy-Suche')}">
      <form id="proxySearchForm" class="reslist" style="gap:6px">
        <input type="search" id="pq" placeholder="${t('z.B. steel production')}" value="${esc(S.proxy.q)}" aria-label="${t('Prozess suchen')}">
        <input type="text" id="ploc" list="proxyLocList" value="${esc(S.proxy.loc)}" placeholder="${t('Ort, z.B. DE')}" aria-label="${t('Ort')}" autocomplete="off">${locList('proxyLocList')}
        <button class="btn primary" type="submit">${t('Proxy suchen')}</button>
      </form>
      ${err}
      <div class="reslist" style="margin-top:8px">${list}</div>
    </aside>
    <div style="display:flex;flex-direction:column;gap:18px;min-width:0">${detail}</div>
  </div>`;
}
