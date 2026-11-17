// Start: project overview and entry points.
'use strict';
import { S, esc, nf, t } from '../core.js';

const role = r => ({ background: t('Hintergrunddaten'), model: t('Eigene Modelle'), biosphere: t('Stoffflüsse'), empty: t('Leer') })[r];

// new projects: empty, BAFU 2026 (sentier-brightway, offered while it is not there yet) or ecoinvent (like the Activity Browser)
const newProjects = () => `<section class="card" style="display:flex;flex-direction:column;gap:10px;max-width:820px">
    <h2>${t('Neues Projekt')}</h2>
    <p class="muted">${t('Leer, oder gleich mit Hintergrunddaten: BAFU 2026 mit EF 3.1 (frei verfügbar) oder ecoinvent (mit eigenem Konto oder aus den heruntergeladenen Dateien, wie im Activity Browser). Bestehende Projekte bleiben unberührt.')}</p>
    <div class="row" style="gap:8px">
      ${S.st.bafu2026_import ? `<button class="btn primary" data-act="new-project" data-k="bafu2026">${t('BAFU 2026 importieren')}</button>` : ''}
      <button class="btn" data-act="new-project" data-k="ecoinvent-account">${t('ecoinvent importieren')}</button>
      <button class="btn" data-act="new-project">${t('Leeres Projekt')}</button>
    </div>
  </section>`;
// the open project has no databases yet (e.g. just created): fill it
const emptyProject = () => `<section class="card" style="display:flex;flex-direction:column;gap:10px">
    <h2>${t('Dieses Projekt ist noch leer')}</h2>
    <p class="muted">${t('Importiere Hintergrunddaten, um Prozesse zu suchen, eigene Modelle zu bauen und zu rechnen.')}</p>
    <div class="row" style="gap:8px">
      <button class="btn primary" data-act="import-here" data-k="bafu2026">${t('BAFU 2026 importieren')}</button>
      <button class="btn" data-act="import-here" data-k="ecoinvent-account">${t('ecoinvent mit Konto')}</button>
      <button class="btn" data-act="import-here" data-k="ecoinvent-files">${t('ecoinvent aus Dateien')}</button>
    </div>
  </section>`;

// no project open yet (first start), or the open one failed to load: choose one, or make a test copy
function vChoose() {
  const st = S.st;
  const tag = p => p.copy ? t('Arbeitskopie') : p.testcopy ? t('Testkopie') : p.legacy ? t('Activity Browser 2, nur als Kopie')
    : p.rebuild ? t('wird beim Öffnen umgebaut') : '';
  const err = st.load_error ? `<div class="warnbox"><b>${t('Das Projekt «{name}» lässt sich nicht laden.', { name: esc(st.project) })}</b><span>${esc(st.load_error)}</span><span>${t('Wähle ein anderes Projekt. Der Fehler steht auch in der Datei lca-wrench.log im Ordner von LCA Wrench.')}</span></div>` : '';
  return `${err}<section class="card" style="display:flex;flex-direction:column;gap:12px;max-width:820px">
    <h2>${t('Welches Projekt?')}</h2>
    <p class="muted">${t('LCA Wrench zeigt alle Brightway-Projekte dieses Rechners. Zum Ausprobieren mit eigenen Daten empfohlen: eine <b>Testkopie</b>. Darin lässt sich alles ändern, das Original bleibt wie es ist. Schliesse vorher den Activity Browser.')}</p>
    ${st.projects.length ? `<div class="reslist">${st.projects.map(p => `<div class="row" style="justify-content:space-between;gap:8px">
      <span>${esc(p.name)}${tag(p) ? ` <span class="muted">· ${tag(p)}</span>` : ''}</span>
      <span class="row" style="gap:6px">${p.legacy || p.name === st.project ? '' : `<button class="btn small" data-act="open-project" data-k="${esc(p.name)}">${t('Öffnen')}</button>`}<button class="btn small primary" data-act="copy-project" data-k="${esc(p.name)}">${t('Testkopie anlegen')}</button></span></div>`).join('')}</div>`
    : `<p class="empty">${t('Auf diesem Rechner gibt es noch kein Brightway-Projekt.')}</p>`}
  </section>${newProjects()}`;
}

// which background databases the calculation uses: one, several combined, or all process data (automatic)
const kindName = k => ({ lci: t('Prozessdaten'), scenario: t('Szenario (premise)'), mrio: t('Input-Output (EXIOBASE)') })[k] || k;
function backgroundCard() {
  const bg = S.st.background;
  if (!bg || !S.st.databases.some(d => d.role === 'background')) return '';
  if (!S.bgForm) S.bgForm = { mode: bg.mode, single: bg.mode === 'single' ? bg.databases[0] : bg.options[0]?.name, multi: new Set(bg.mode === 'auto' ? [] : bg.databases) };
  const f = S.bgForm;
  const radio = (v, label) => `<label class="row" style="gap:6px"><input type="radio" name="bgMode" value="${v}" ${f.mode === v ? 'checked' : ''}> ${label}</label>`;
  const notes = [];
  if (bg.substituted) notes.push(t('{n} Inputs der Modelle kommen aus dem gewählten Hintergrund statt aus der Datenbank, mit der sie verknüpft sind (gleicher Datensatz dort).', { n: bg.substituted }));
  if (bg.pulled.length) notes.push(t('Für Inputs ohne Gegenstück wird zusätzlich gerechnet mit: {list}.', { list: esc(bg.pulled.join(', ')) }));
  return `<section class="card" id="bgCard" style="display:flex;flex-direction:column;gap:12px">
    <h2>${t('Hintergrunddaten für die Rechnung')}</h2>
    <p class="muted">${t('Ein Projekt kann mehrere Hintergrund-Datenbanken haben: BAFU, ecoinvent, Zukunftsszenarien von premise oder EXIOBASE. Mit <b>einer Datenbank</b> rechnen die Modelle auf genau dieser; Inputs aus einer anderen werden durch denselben Datensatz dort ersetzt (z.B. ecoinvent heute → Szenario 2040). <b>Kombiniert</b> rechnet mit mehreren zugleich, etwa ecoinvent für Material und EXIOBASE für Dienstleistungen in Euro (hybride Ökobilanz).')}</p>
    <div class="row" style="gap:16px;flex-wrap:wrap;font-size:14px">${radio('single', t('Eine Datenbank'))}${radio('combined', t('Mehrere kombinieren'))}${radio('auto', t('Automatisch: alle Prozessdaten'))}</div>
    ${f.mode === 'single' ? `<label class="f" style="max-width:520px">${t('Datenbank')}<select id="bgSingle">${bg.options.map(o => `<option value="${esc(o.name)}" ${o.name === f.single ? 'selected' : ''}>${esc(o.name)} · ${kindName(o.kind)}</option>`).join('')}</select></label>`
      : f.mode === 'combined' ? `<div class="reslist">${bg.options.map(o => `<label class="row" style="gap:6px;font-size:14px"><input type="checkbox" data-bgdb="${esc(o.name)}" ${f.multi.has(o.name) ? 'checked' : ''}> ${esc(o.name)} <span class="muted">· ${kindName(o.kind)}</span></label>`).join('')}</div>`
      : `<p class="muted" style="font-size:13.5px">${t('Alle Prozessdaten zusammen, ohne Szenarien und Input-Output-Tabellen (so rechnete LCA Wrench bisher).')}</p>`}
    <div class="row" style="gap:10px;align-items:center"><button class="btn primary" data-act="bg-apply">${t('Übernehmen')}</button>
      <span class="muted" style="font-size:13px">${t('Jetzt gerechnet mit: {list}', { list: esc(bg.used.join(', ')) })}</span></div>
    ${notes.length ? `<p class="muted" style="font-size:13px">${notes.join(' ')}</p>` : ''}
    <div><div class="eyebrow" style="margin:6px 0 8px">${t('Datenbank hinzufügen')}</div>
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <button class="btn small" data-act="add-db" data-k="ecoinvent-account">${t('ecoinvent mit Konto')}</button>
        <button class="btn small" data-act="add-db" data-k="ecoinvent-files">${t('ecoinvent aus Dateien')}</button>
        ${S.st.databases.some(d => d.name.startsWith('bafu-2026')) ? '' : `<button class="btn small" data-act="add-db" data-k="bafu2026">${t('BAFU 2026')}</button>`}
        <button class="btn small" data-act="add-db" data-k="premise">${t('Zukunftsszenario (premise)')}</button>
        <button class="btn small" data-act="add-db" data-k="exiobase">${t('EXIOBASE')}</button>
      </div></div>
    ${bg.options.some(o => o.removable) ? `<div><div class="eyebrow" style="margin:6px 0 8px">${t('Hinzugefügte Datenbank entfernen')}</div>
      <div class="reslist">${bg.options.filter(o => o.removable).map(o => `<div class="row" style="justify-content:space-between;gap:8px;font-size:14px">
        <span>${esc(o.name)} <span class="muted">· ${kindName(o.kind)}</span></span><button class="btn small" data-act="bg-remove" data-k="${esc(o.name)}">${t('Entfernen')}</button></div>`).join('')}</div></div>` : ''}
  </section>`;
}

export function vStart() {
  const st = S.st;
  if (!st.project || st.load_error) return vChoose();
  const groups = ['model', 'background', 'biosphere', 'empty'].map(r => [r, st.databases.filter(d => d.role === r)]).filter(([, l]) => l.length);
  const hasModels = st.databases.some(d => d.role === 'model');
  const steps = [['daten', t('Daten'), t('Prozesse suchen, Inputs und Emissionen ansehen')], ['modell', t('Modellieren'), t('Eigene Produkte aus Hintergrunddaten bauen')],
    ['rechnen', t('Rechnen'), t('Mehrere Produkte × mehrere Methoden')], ['ergebnis', t('Ergebnis'), t('Beiträge, Sankey, Lieferkette, Inventar')]];
  // a machine with only Activity Browser 2 projects: LCA Wrench starts in an empty project and offers copies
  const older = st.projects.filter(p => p.legacy);
  const offer = older.length && !st.databases.length ? `<section class="card" style="display:flex;flex-direction:column;gap:10px">
      <h2>${t('Projekte aus dem Activity Browser 2')}</h2>
      <p class="muted">${t('Diese Projekte haben das ältere Format von Brightway 2. LCA Wrench öffnet sie nur als Kopie; das Original und der Activity Browser 2 bleiben unberührt.')}</p>
      <div class="reslist">${older.map(p => `<div class="row" style="justify-content:space-between"><span>${esc(p.name)}</span><button class="btn small primary" data-act="copy-older" data-k="${esc(p.name)}">${t('Kopie für LCA Wrench anlegen')}</button></div>`).join('')}</div>
    </section>` : '';
  return `${offer}${st.databases.length ? '' : emptyProject()}<section class="hero">
    <div class="card" style="display:flex;flex-direction:column;gap:14px;padding:24px">
      <span class="eyebrow">${t('Ökobilanz · Life Cycle Assessment · Brightway')}</span>
      <h1>${t('Modellieren und rechnen, ohne zu warten')}</h1>
      <p class="lead">${t('Baue eigene Produktmodelle auf echten Hintergrunddaten, rechne mehrere Produkte und Methoden auf einmal und sieh sofort, was jede Änderung bewirkt.')}</p>
      <div class="row">
        ${st.example_available ? `<button class="btn primary" data-act="example-model">${hasModels ? t('Beispielmodell nochmals anlegen') : t('Beispielmodell anlegen (E-Bike)')}</button>` : ''}
        <button class="btn ${st.example_available ? '' : 'primary'}" data-act="view" data-k="modell">${hasModels ? t('Eigene Modelle öffnen') : t('Leeres Modell anlegen')}</button>
        <button class="btn" data-act="view" data-k="daten">${t('Daten durchsuchen')}</button>
      </div>
      ${st.examples.length ? `<div><div class="eyebrow" style="margin-bottom:8px">${t('Oder direkt einen Datensatz ansehen')}</div><div class="row" style="gap:8px">${st.examples.map(e => `<button class="btn small" data-act="open" data-k="${e.id}" data-db="${esc(e.database)}">${esc(e.name)} · ${esc(e.location)}</button>`).join('')}</div></div>` : ''}
    </div>
    <div class="card" style="display:flex;flex-direction:column;gap:10px;padding:24px">
      <span class="eyebrow">${t('Aktuelles Projekt')}</span>
      <h2>${esc(st.project)}</h2>
      ${st.is_copy || st.is_testcopy ? '' : `<div class="row" style="gap:8px;align-items:center"><button class="btn small" data-act="copy-project" data-k="${esc(st.project)}">${t('Testkopie anlegen')}</button><span class="muted" style="font-size:13px">${t('zum gefahrlosen Ausprobieren, das Original bleibt wie es ist')}</span></div>`}
      <table class="tbl"><tbody>
        ${groups.map(([r, l]) => `<tr><td colspan="2" class="eyebrow" style="padding-top:12px">${role(r)}</td></tr>` + l.map(d => `<tr><td>${d.role === 'model' ? `<button class="linkbtn" data-act="open-db" data-k="${esc(d.name)}">${esc(d.name)}</button>` : esc(d.name)}</td><td class="num nw" style="text-align:right">${nf(d.count)} ${d.role === 'biosphere' ? t('Stoffflüsse') : t('Prozesse')}</td></tr>`).join('')).join('')}
        <tr><td colspan="2" class="eyebrow" style="padding-top:12px">${t('Weiteres')}</td></tr>
        <tr><td>${t('Wirkungsmethoden')}</td><td class="num" style="text-align:right">${st.methods.length}</td></tr>
        <tr><td>${t('Gespeicherte Rechnungen')}</td><td class="num" style="text-align:right">${st.setups.length}</td></tr>
      </tbody></table>
    </div>
  </section>${backgroundCard()}
  <section class="flow" aria-label="${t('Ablauf')}">
    ${steps.map((c, i) =>
      `<button class="card" data-act="view" data-k="${c[0]}"><span class="k">${i + 1}</span><h3>${c[1]}</h3><span class="muted" style="font-size:13.5px">${c[2]}</span></button>`).join('')}
  </section>
  <section class="card truth">
    <div><h3>${t('Anders als im Activity Browser')}</h3><ul>
      <li>${t('<b>Live:</b> Jede Änderung am Modell ist in Millisekunden gerechnet und sofort im Datenblatt sichtbar')}</li>
      <li>${t('<b>Rückgängig:</b> Jeder Schritt lässt sich zurücknehmen (⌘Z / Ctrl+Z)')}</li>
      <li>${t('<b>Gegenprobe:</b> Ergebnisse werden auf Knopfdruck mit bw2calc nachgerechnet')}</li>
      <li>${t('<b>Kompatibel:</b> Modelle und Rechnungen sind normale Brightway-Daten, der Activity Browser öffnet sie auch')}</li></ul></div>
    <div><h3>${t('Was hier echt ist')}</h3><ul>
      <li>${t('Daten: {list}', { list: st.databases.filter(d => d.role === 'background').map(d => esc(d.name)).join(', ') || t('keine Hintergrunddaten') })}</li>
      <li>${t('Rechnung: Brightway (bw2calc) als Unterbau, eigener Rechenkern für die Modelle, gegengeprüft')}</li>
      <li>${t('Hintergrunddaten bleiben unverändert. Geändert wird nur in eigenen Modellen oder in einer Arbeitskopie')}</li>
      <li>${t('Alles läuft lokal auf diesem Rechner (127.0.0.1)')}</li></ul></div>
  </section>${newProjects()}`;
}
