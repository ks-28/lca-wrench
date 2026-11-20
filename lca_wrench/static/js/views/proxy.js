// Proxy: Planet A hybrid / geo-proxy search (separate from Daten keyword search).
'use strict';
import { S, esc, explain, spellingNote, t } from '../core.js';
import { sheet } from '../sheet.js';

function resultRow(r) {
  const why = r.why || r.comment || '';
  const kind = r.why_kind === 'geo_proxy' ? t('Geo-Proxy')
    : r.why_kind === 'related_family' ? t('Verwandte Familie')
    : t('Hybrid');
  const fam = r.family_label ? `<span class="chip">${esc(r.family_label)}</span>` : '';
  return `<button class="res" data-act="open-proxy" data-k="${r.id}" aria-current="${r.id === S.proxy.sel}" type="button">
    <span>${esc(r.name)}</span>
    <span class="meta">${esc(r.location || '—')}${r.product ? ` · ${esc(r.product)}` : ''} · ${esc(r.unit || '')}<span class="chip">${esc(kind)}</span>${fam}</span>
    ${why ? `<span class="rdesc">${esc(why)}</span>` : ''}
  </button>`;
}

function relatedSection(related) {
  if (!related || !related.length) return '';
  // Group by family_label for a clear explore list under the primary family
  const byFam = new Map();
  for (const r of related) {
    const k = r.family_label || t('Andere Familie');
    if (!byFam.has(k)) byFam.set(k, []);
    byFam.get(k).push(r);
  }
  const blocks = [...byFam.entries()].map(([label, rows]) =>
    `<div class="proxy-related-fam"><div class="grp">${esc(label)}</div>${rows.map(resultRow).join('')}</div>`
  ).join('');
  return `<div class="proxy-related" role="region" aria-label="${t('Verwandte Familien')}">
    <div class="proxy-related-sep" role="separator"></div>
    <p class="grp" style="padding-top:8px">${t('Verwandte Familien')} <span class="muted" style="font-weight:400;letter-spacing:0;text-transform:none">— ${t('nicht die gesperrte Primärfamilie; zum Erkunden')}</span></p>
    ${blocks}
  </div>`;
}

function progressBlock() {
  if (!S.proxy.loading) return '';
  const deep = !!S.proxy.deep;
  const elapsed = Math.max(0, Date.now() - (S.proxy.loadStarted || Date.now()));
  const expect = S.proxy.loadExpectMs || (deep ? 180000 : 35000);
  // Asymptotic fill — honest wait cue (server has no % yet)
  const pct = Math.min(92, Math.round((1 - Math.exp(-elapsed / expect)) * 100));
  const left = Math.max(0, Math.round((expect - elapsed) / 1000));
  const elapsedSec = Math.round(elapsed / 1000);
  const label = deep
    ? t('Deep Search · oft 2–5 Min')
    : t('Proxy-Suche · oft 10–40 s');
  const eta = left > 0
    ? t('ca. {n} s verbleibend · {e} s vergangen', { n: left, e: elapsedSec })
    : t('noch etwas länger · {e} s vergangen', { e: elapsedSec });
  return `<div class="proxy-progress${deep ? ' deep' : ''}" id="proxyProgress" role="status" aria-live="polite">
    <div class="proxy-progress-meta"><span>${label}</span><span class="num" id="proxyProgressEta">${eta}</span></div>
    <div class="proxy-progress-bar" aria-hidden="true"><i id="proxyProgressFill" style="width:${pct}%"></i></div>
    <p class="muted" style="font-size:11px;margin:0">${t('Fortschritt geschätzt — Server meldet kein Prozent.')}</p>
  </div>`;
}

/** Deep only after a finished normal Proxy run — never on first look. */
function deepAction() {
  const loading = !!S.proxy.loading;
  if (loading) return '';
  // Need at least one completed search this session (results, empty, or error all count)
  if (!S.proxy.searched) return '';
  if (S.proxy.deep_used) {
    return `<p class="muted" style="font-size:12px;margin:0">${t('Deep Search wurde für diese Abfrage genutzt.')}
      <button class="linkbtn" type="button" data-act="proxy-deep-search" style="margin-left:6px">${t('Nochmal Deep Search')}</button></p>`;
  }
  return `<button class="btn hot proxy-deep-btn" type="button" data-act="proxy-deep-search"
      title="${t('Langsamer LLM-Baumsuche — oft mehrere Minuten')}">${t('Deep Search versuchen')}</button>
    <p class="muted" style="font-size:11px;margin:0">${t('Wenn die Treffer nicht passen: Deep Search läuft den ecoinvent-Baum per LLM (wie MCP deep=true).')}</p>`;
}

export function vProxy() {
  const rows = S.proxy.results || [];
  const related = S.proxy.related_results || [];
  const loading = !!S.proxy.loading;
  const list = loading
    ? `<p class="muted" role="status">${S.proxy.deep
      ? t('Deep Search läuft … oft mehrere Minuten (LLM-Baum). Bitte warten.')
      : t('Proxy-Suche läuft … oft 10–40 Sekunden (Embeddings). Bitte warten.')}</p>`
    : rows.length || related.length
      ? spellingNote(rows) + rows.map(resultRow).join('') + relatedSection(related)
      : `<p class="empty">${S.proxy.q
        ? t('Kein Proxy-Treffer für «{q}». Versuch ecoinvent-Englisch (z.B. «steel production», «reinforcing steel») oder Ort weglassen.', { q: esc(S.proxy.q) })
        : t('Freitext: was du brauchst (Englisch, ecoinvent-nah). Ort = Code oder Ländername (CH, India, Indai…). Begründung kommt von der Suche — nicht von Chat.')}</p>`;

  const notices = (S.proxy.ui_notices || []).slice(0, 6)
    .map(n => `<li>${esc(n)}</li>`).join('');
  const status = loading
    ? ''
    : (S.proxy.summary || notices)
      ? `<div class="card" style="padding:12px 14px">
          ${S.proxy.summary ? `<p style="margin:0 0 6px;font-size:14px"><b>${t('Warum diese Treffer')}</b> — ${esc(S.proxy.summary)}</p>` : ''}
          ${notices ? `<ul style="margin:0;padding-left:1.2em;font-size:13px;color:var(--muted)">${notices}</ul>` : ''}
          <p class="muted" style="margin:8px 0 0;font-size:12px">${t('Begründung = Hybrid-/Geo-Regeln im Code (deterministisch). Claude/Agent kann zusätzlich erklären, ersetzt das hier nicht.')}</p>
        </div>`
      : '';

  const detail = S.proxy.act
    ? sheet(S.proxy.act, S)
    : `<section class="card">
        <h3 style="margin:0 0 8px;font-size:15px">${t('Prozess-Datenblatt')}</h3>
        <p class="empty" style="margin:0">${t('Rechts bleibt leer, bis du links einen Treffer wählst. Dann siehst du Inputs, Emissionen und Wirkungsanteile — wie unter Daten.')}</p>
      </section>`;

  const err = S.proxy.error ? `<p class="empty" role="alert">${esc(S.proxy.error)}</p>` : '';

  // No <datalist>: Chromium misplaces native suggestions under sticky/grid ancestors
  // (floating list in the middle of the page). Free text + regions.resolve is enough.
  return `${explain(t('Proxy = strukturierte Suche (Text + Ort), keine Chat-Box. Agent soll query + location aufrufen; UI zeigt Code-Begründungen.'))}
  ${status}
  <div class="dataview proxyview">
    <aside class="card proxy-aside" aria-label="${t('Proxy-Suche')}">
      <form id="proxySearchForm" class="proxy-form reslist" style="gap:6px">
        <label class="f" style="margin:0"><span>${t('Was suchst du?')}</span>
          <input type="text" id="pq" value="${esc(S.proxy.q)}" placeholder="${t('z.B. section bar rolling, steel')}" aria-label="${t('Freitext Prozess/Produkt')}" autocomplete="off" ${loading ? 'disabled' : ''}>
        </label>
        <label class="f" style="margin:0"><span>${t('Ort')}</span>
          <input type="text" id="ploc" value="${esc(S.proxy.loc)}" placeholder="${t('Ort, z.B. CH oder Germany')}" aria-label="${t('Ort')}" autocomplete="off" ${loading ? 'disabled' : ''}>
        </label>
        <p class="muted" style="font-size:12px;margin:0">${t('Wie unter Daten: Code oder Ländername; leichte Tippfehler ok (Indai → IN).')}</p>
        <div class="proxy-actions">
          <button class="btn ${S.proxy.searched && !loading ? 'proxy-search-btn' : 'primary'}" type="submit" ${loading ? 'disabled' : ''}>${loading && !S.proxy.deep ? t('Suche …') : t('Proxy suchen')}</button>
          ${deepAction()}
        </div>
        ${progressBlock()}
      </form>
      ${err}
      <div class="proxy-results reslist">${list}</div>
    </aside>
    <div style="display:flex;flex-direction:column;gap:18px;min-width:0">${detail}</div>
  </div>`;
}
