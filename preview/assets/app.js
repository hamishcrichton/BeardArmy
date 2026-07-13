/* Shared data + helpers for the BeardMeatsFood stats site.
 *
 * Contract used by every page:
 *   BMF.COLORS                      -> { success, failure, unknown } hex marks
 *                                      (CVD-validated on #f3ecdd paper and #fbf7ee card,
 *                                       worst pair ΔE 21.1 deutan; see app.css notes)
 *   await BMF.loadData()            -> { rows, features, stats }  (cached after first call)
 *   BMF.stats(rows)                 -> { wins, losses, decided, longest, current, countries, total }
 *   BMF.esc(s) BMF.yt(id) BMF.cleanTitle(t) BMF.fmt(n)
 *   BMF.nav('map')                  -> injects the top nav, marking the given page active
 *   BMF.tooltip(el, html)           -> shared fixed-position tooltip helpers: show(evt, html), hide()
 */
window.BMF = (() => {
  const COLORS = { success: '#2e8551', failure: '#9e2f23', unknown: '#857b6c' };
  const PAGES = [
    ['index', 'Overview', 'index.html'],
    ['map', 'Map & Tours', 'map.html'],
    ['analytics', 'Analytics', 'analytics.html'],
    ['records', 'Records', 'records.html'],
  ];

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const yt = id => `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
  const cleanTitle = t => String(t || '').replace(/\s*\|\s*BeardMeatsFood\s*$/i, '');
  const fmt = n => n == null ? '–' : Number(n).toLocaleString('en-GB');

  function stats(rows) {
    const dated = rows.filter(r => r.date_attempted).sort((a, b) => a.date_attempted.localeCompare(b.date_attempted));
    const wins = rows.filter(r => r.result === 'success').length;
    const losses = rows.filter(r => r.result === 'failure').length;
    const decided = dated.filter(r => r.result === 'success' || r.result === 'failure');
    let longest = 0, run = 0;
    for (const r of decided) { run = r.result === 'success' ? run + 1 : 0; longest = Math.max(longest, run); }
    let current = 0;
    for (let i = decided.length - 1; i >= 0; i--) { if (decided[i].result === 'success') current++; else break; }
    const countries = new Set(rows.map(r => r.country_code).filter(Boolean)).size;
    return { wins, losses, decided, longest, current, countries, total: rows.length };
  }

  let _cache = null;
  async function loadData() {
    if (_cache) return _cache;
    const [geoResp, tableResp] = await Promise.all([
      fetch('../public/data/challenges.geojson'),
      fetch('../public/data/table.json'),
    ]);
    const rows = tableResp.ok ? ((await tableResp.json()).rows || []) : [];
    const features = geoResp.ok ? ((await geoResp.json()).features || []) : [];
    _cache = { rows, features, stats: stats(rows) };
    return _cache;
  }

  function nav(active) {
    // Masthead: CSS roundel homage to the channel's butcher-stamp logo + top nav.
    const el = document.createElement('header');
    el.className = 'masthead';
    el.innerHTML = `
      <a class="roundel" href="index.html" aria-label="BeardMeatsFood — overview">
        <span class="r-x">&#10005;</span><span class="r-w">BEARD</span><span class="r-w">MEATS</span><span class="r-w">FOOD</span><span class="r-x">&#9733;</span>
      </a>
      <nav class="nav">${PAGES.map(([key, label, href]) =>
        `<a href="${href}" class="${key === active ? 'active' : ''}">${label}</a>`).join('')}</nav>`;
    const wrap = document.querySelector('.wrap') || document.body;
    wrap.insertAdjacentElement('afterbegin', el);
  }

  const tooltip = (() => {
    let el = null;
    function ensure() {
      if (!el) { el = document.createElement('div'); el.className = 'tip'; document.body.appendChild(el); }
      return el;
    }
    return {
      show(evt, html) {
        const t = ensure();
        t.innerHTML = html;
        t.style.display = 'block';
        const x = Math.min(evt.clientX + 14, window.innerWidth - 300);
        t.style.left = `${x}px`;
        t.style.top = `${evt.clientY + 14}px`;
      },
      hide() { if (el) el.style.display = 'none'; },
    };
  })();

  return { COLORS, esc, yt, cleanTitle, fmt, stats, loadData, nav, tooltip };
})();
