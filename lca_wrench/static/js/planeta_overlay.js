// Planet A overlay — keep upstream core.js / views list clean.
// After merging lca-wrench upstream: re-check this file + one import in main.js
// + additive /api/search/proxy (see docs/agents/wrench-planeta-overlay.md).
'use strict';
import { t, esc, $ } from './core.js';

const THEME_KEY = 'wb-theme';

/** Exact loc match for Daten→Proxy handoff (empty loc = any hit wins). */
export const hasExactLocMatch = (rows, loc) => {
  const list = rows || [];
  const want = (loc || '').trim();
  if (!want) return list.length > 0;
  const key = want.toLowerCase();
  return list.some(r => String(r.location || '').toLowerCase() === key);
};

/** Effective dark? Honours data-theme, else OS preference. */
export function themeIsDark() {
  const forced = document.documentElement.getAttribute('data-theme');
  if (forced === 'dark') return true;
  if (forced === 'light') return false;
  return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
}

/** Persist explicit light|dark (CSS already supports data-theme). */
export function applyTheme(mode) {
  const next = mode === 'light' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem(THEME_KEY, next); } catch (_) { /* ignore */ }
  syncThemeToggle();
}

export function toggleTheme() {
  applyTheme(themeIsDark() ? 'light' : 'dark');
}

/** Sync rail button label/icons after lang or theme change. */
export function syncThemeToggle() {
  const dark = themeIsDark();
  const btn = $('themeToggle');
  const lab = $('themeToggleLabel');
  const moon = $('themeIconMoon');
  const sun = $('themeIconSun');
  // Label + icon = destination (dark → Light/sun; light → Dark/moon)
  if (lab) lab.textContent = dark ? t('Hell') : t('Dunkel');
  if (btn) {
    btn.title = dark ? t('Zu hellem Modus wechseln') : t('Zu dunklem Modus wechseln');
    btn.setAttribute('aria-label', btn.title);
    btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
  }
  if (moon) moon.hidden = dark;
  if (sun) sun.hidden = !dark;
}

const PROXY_ICON = '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/><path d="M11 8v6M8 11h6"/>';

/** Appended after stock Wrench rail views — separator then Proxy search. */
export const planetaRailTail = () => [
  ['__sep__', ''],
  ['proxy', t('Proxy-Suche')],
];

export function planetaIconSvg(k) {
  if (k !== 'proxy') return null;
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${PROXY_ICON}</svg>`;
}

/** Build left-rail HTML: stock views + Planet A separator + Proxy. */
export function renderPlanetaRail(stockViews, stockIcon, currentView) {
  const items = [...stockViews, ...planetaRailTail()];
  return items.map(([k, l]) => {
    if (k === '__sep__') {
      return `<hr class="nav-sep" role="separator" title="${esc(t('Planet A — nicht Teil von Upstream-Wrench'))}" aria-label="${esc(t('Planet A'))}">`;
    }
    const svg = planetaIconSvg(k) || stockIcon(k);
    return `<button class="nav${k === 'proxy' ? ' nav-planeta' : ''}" data-act="view" data-k="${k}" ${currentView === k ? 'aria-current="page"' : ''}>${svg}<span>${l}</span></button>`;
  }).join('');
}
