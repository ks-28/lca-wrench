// First-run tour: highlights the main areas one after another and explains them.
'use strict';
import { S, esc, savePref, t } from './core.js';

const KEY = 'wb-tour';

// target: CSS selectors, the first visible one is highlighted (several in a group are joined)
const steps = () => [
  {
    title: t('Willkommen bei LCA Wrench'),
    text: t('Eine neue Oberfläche für Brightway 2.5 mit eigenem Rechenkern. Sie läuft nur auf diesem Rechner und arbeitet mit normalen Brightway-Projekten. Der Rundgang zeigt in zehn kurzen Schritten, wo was ist.'),
  },
  {
    target: [['label:has(#projSel)', 'label:has(#methSel)']],
    title: t('Projekt und Wirkungsmethode'),
    text: t('Gelten für alle Ansichten. Hier erscheint jedes Brightway-Projekt im Standardordner, auch eines mit ecoinvent. Dessen Datenbanken liest LCA Wrench nur, sie verändert sie nie.'),
  },
  {
    target: ['#rail'],
    title: t('Sieben Ansichten'),
    text: t('Von oben nach unten im Arbeitsablauf: Daten durchsuchen, eigene Produkte modellieren, Parameter für Formeln festlegen, mehrere Produkte und Methoden rechnen, ein Ergebnis im Detail ansehen, Projekte vergleichen.'),
  },
  {
    view: 'start', target: ['.hero .card:nth-child(2)'],
    title: t('Datenbanken nach Rolle'),
    text: t('<b>Hintergrunddaten</b> sind die selbständigen Datenbanken wie BAFU oder ecoinvent; sie bleiben schreibgeschützt. <b>Eigene Modelle</b> sind Vordergrund-Datenbanken, die direkt bearbeitet werden. Beides sind normale Brightway-Datenbanken; der Activity Browser sieht sie auch.'),
  },
  {
    view: 'daten', prepare: 'sheet', target: ['.plist', '.dataview'],
    title: t('Daten'),
    text: t('Suche über alle Datenbanken. Das Datenblatt zeigt für jeden Input den Anteil an der Wirkung, inklusive der ganzen Lieferkette dahinter. Ein Hintergrundprozess lässt sich mit einem Klick in ein eigenes Modell kopieren und dort anpassen.'),
  },
  {
    view: 'modell', prepare: 'editor', target: ['.sheethead .kpi', 'main .card'],
    title: t('Modellieren, live gerechnet'),
    text: t('Jede geänderte Menge ist in Millisekunden gerechnet; die grosse Zahl und die Anteile aktualisieren sich sofort. Vorder- und Hintergrund werden getrennt gelöst, die Zerlegung der Hintergrundmatrix wird wiederverwendet. Das Ergebnis ist exakt, nicht angenähert. Inputs lassen sich als Gutschrift markieren.'),
  },
  {
    view: 'modell', target: ['#undoBtn', '.journal'],
    title: t('Jeder Schritt lässt sich zurücknehmen'),
    text: t('«Rückgängig» oder ⌘Z / Ctrl+Z nimmt den letzten Schritt zurück. Der Verlauf unter der Prozessliste springt auf Wunsch mehrere Schritte zurück.'),
  },
  {
    view: 'rechnen', prepare: 'setup', target: ['.restbl', '.plist'],
    title: t('Rechnen: Produkte × Methoden'),
    text: t('Eine Rechnung fasst mehrere Produkte und Methoden zusammen. Sie wird im Projekt als <i>calculation setup</i> gespeichert, im Format des Activity Browsers. «Gegenprobe mit bw2calc» rechnet jede Zahl unabhängig nach.'),
  },
  {
    view: 'ergebnis', prepare: 'result', target: ['.tabs', 'main .card'],
    title: t('Ergebnis im Detail'),
    text: t('Für ein Produkt: Beiträge nach Prozess oder Stoff, Sankey (jeder Prozess einmal, Rückkopplungen erkannt), Lieferkettenbaum, Inventar mit CSV-Export und das Umweltprofil nach ökologischer Knappheit.'),
  },
  {
    view: 'start', target: [['#tourBtn', '#explainBtn']],
    title: t('Hilfe bleibt erreichbar'),
    text: t('Die grünen Erklärkästen lassen sich hier ausblenden. Diesen Rundgang startet «Rundgang» jederzeit wieder.'),
    last: true,
  },
];

let ctx = null;

export function shouldAutoStart() {
  try { return localStorage.getItem(KEY) !== 'done'; } catch (_) { return false; }
}

export async function startTour(hooks) {
  ctx = { i: 0, hooks };
  mount();
  await show();
}

export function positionTour() { if (ctx) place(); }

export function tourKey(ev) {
  if (!ctx) return false;
  if (ev.key === 'Escape') { end(); return true; }
  if (ev.key === 'ArrowRight') { step(1); return true; }
  if (ev.key === 'ArrowLeft') { step(-1); return true; }
  return false;
}

function mount() {
  if (document.getElementById('tourCard')) return;
  document.body.insertAdjacentHTML('beforeend', '<div id="tourBlock"></div><div id="tourDim"></div><div id="tourSpot"></div><div id="tourCard" role="dialog" aria-modal="true" aria-labelledby="tourTitle"></div>');
  document.getElementById('tourCard').addEventListener('click', ev => {
    const b = ev.target.closest('[data-tour]'); if (!b) return;
    const a = b.dataset.tour;
    if (a === 'next') step(1); else if (a === 'back') step(-1); else if (a === 'skip') end();
    else if (a === 'example') { const h = ctx.hooks; end(); h.example(); }
  });
}

async function step(d) {
  const n = ctx.i + d;
  if (n < 0) return;
  if (n >= steps().length) { end(); return; }
  ctx.i = n;
  await show();
}

async function show() {
  const all = steps(), st = all[ctx.i];
  const card = document.getElementById('tourCard');
  card.classList.add('busy-tour');
  try {
    if (st.view && S.view !== st.view) await ctx.hooks.go(st.view);
    if (st.prepare) await ctx.hooks.prepare(st.prepare);
  } catch (e) { console.error(e); }
  card.classList.remove('busy-tour');
  const offerExample = st.last && S.st.example_available && !S.st.databases.some(d => d.role === 'model');
  card.innerHTML = `<div class="tstep">${ctx.i + 1} / ${all.length}</div>
    <h3 id="tourTitle">${esc(st.title)}</h3><p>${st.text}</p>
    <div class="tbtns"><button class="linkbtn" data-tour="skip">${st.last ? t('Schliessen') : t('Rundgang beenden')}</button>
      <span class="row" style="gap:8px">${ctx.i ? `<button class="btn" data-tour="back">${t('Zurück')}</button>` : ''}
      ${offerExample ? `<button class="btn primary" data-tour="example">${t('Beispielmodell anlegen')}</button>` : `<button class="btn primary" data-tour="next">${st.last ? t('Los geht’s') : ctx.i ? t('Weiter') : t('Rundgang starten')}</button>`}</span></div>`;
  place(true);
  card.querySelector('.btn.primary')?.focus();
}

function visible(el) { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !el.hidden; }

function findTarget(target) {
  for (const t of target || []) {
    const els = (Array.isArray(t) ? t : [t]).map(sel => document.querySelector(sel)).filter(el => el && visible(el));
    if (els.length) return els;
  }
  return null;
}

function place(scroll) {
  const st = steps()[ctx.i];
  const spot = document.getElementById('tourSpot'), card = document.getElementById('tourCard');
  const dim = document.getElementById('tourDim');
  const els = findTarget(st.target);
  const vw = window.innerWidth, vh = window.innerHeight, pad = 8, gap = 14;
  if (!els) {
    dim.style.clipPath = 'none';
    spot.style.cssText = `left:${vw / 2}px;top:${vh / 2}px;width:0;height:0;opacity:0`;
    card.style.left = `${Math.max(16, (vw - card.offsetWidth) / 2)}px`;
    card.style.top = `${Math.max(16, (vh - card.offsetHeight) / 2)}px`;
    return;
  }
  if (scroll) {
    const r0 = els[0].getBoundingClientRect();
    if (r0.top < 70 || r0.top > vh * 0.6) window.scrollBy({ top: r0.top - 90 });
  }
  const rs = els.map(el => el.getBoundingClientRect());
  const r = { left: Math.min(...rs.map(x => x.left)), top: Math.min(...rs.map(x => x.top)), right: Math.max(...rs.map(x => x.right)), bottom: Math.max(...rs.map(x => x.bottom)) };
  const top = Math.max(4, r.top - pad), bottom = Math.min(vh - 4, r.bottom + pad);
  const L = r.left - pad, R = r.right + pad;
  spot.style.cssText = `left:${L}px;top:${top}px;width:${R - L}px;height:${Math.max(0, bottom - top)}px`;
  // dim everything except the highlighted box (even-odd hole in a full-screen layer)
  dim.style.clipPath = `polygon(evenodd, 0 0, ${vw}px 0, ${vw}px ${vh}px, 0 ${vh}px, 0 0, ${L}px ${top}px, ${R}px ${top}px, ${R}px ${bottom}px, ${L}px ${bottom}px, ${L}px ${top}px)`;
  const cw = card.offsetWidth, ch = card.offsetHeight;
  let left, y;
  if (vh - bottom >= ch + gap) { y = bottom + gap; left = r.left; }
  else if (top >= ch + gap) { y = top - gap - ch; left = r.left; }
  else if (vw - r.right >= cw + gap) { left = r.right + pad + gap; y = Math.max(16, Math.min(vh - ch - 16, top)); }
  else if (r.left >= cw + gap) { left = r.left - pad - gap - cw; y = Math.max(16, Math.min(vh - ch - 16, top)); }
  else { left = (vw - cw) / 2; y = vh - ch - 16; }
  card.style.left = `${Math.max(16, Math.min(vw - cw - 16, left))}px`;
  card.style.top = `${Math.max(16, Math.min(vh - ch - 16, y))}px`;
}

function end() {
  savePref(KEY, 'done');
  ctx = null;
  for (const id of ['tourBlock', 'tourDim', 'tourSpot', 'tourCard']) document.getElementById(id)?.remove();
}
