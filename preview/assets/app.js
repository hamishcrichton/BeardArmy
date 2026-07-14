/* Shared data + helpers for the BeardMeatsFood stats site.
 *
 * Contract used by every page:
 *   BMF.COLORS                      -> { success, failure, unknown } hex marks
 *                                      (CVD-validated on #1a1a1a body and #242424 card,
 *                                       worst pair ΔE 24.8 deutan; see app.css notes)
 *   await BMF.loadData()            -> { rows, features, stats }  (cached after first call)
 *   BMF.stats(rows)                 -> { wins, losses, decided, longest, current, countries, total }
 *                                      (computed over TRUE CHALLENGES only — kind==='special'
 *                                       rows are excluded before counting)
 *   BMF.isChallenge(r)              -> false for kind==='special' rows (music videos, Q&As, tours…)
 *   BMF.esc(s) BMF.yt(id) BMF.cleanTitle(t) BMF.fmt(n)
 *   BMF.fmtDate(iso)                -> "13 July 2026" (site-wide date format)
 *   BMF.countryName(cc)             -> display name for an alpha-2 code (falls back to the code)
 *   BMF.cuisineLabel(key)           -> humorous display label for a cuisine bucket (falls back to key)
 *   BMF.openmojiUrl(cp)             -> OpenMoji colour-SVG CDN URL for a codepoint sequence
 *   BMF.flagUrl(cc)                 -> OpenMoji flag SVG URL for an alpha-2 country code
 *   BMF.nav('map')                  -> injects the top nav, marking the given page active
 *   BMF.tooltip(el, html)           -> shared fixed-position tooltip helpers: show(evt, html), hide()
 */
window.BMF = (() => {
  const COLORS = { success: '#00d084', failure: '#ff4d4f', unknown: '#9ca3af' };
  const PAGES = [
    ['index', 'Overview', 'index.html'],
    ['challenges', 'All Challenges', 'challenges.html'],
    ['analytics', 'Analytics', 'analytics.html'],
    ['collabs', 'Collaborators', 'collaborators.html'],
    ['calendar', 'Calendar', 'calendar.html'],
    ['map', 'Map', 'map.html'],
    ['tours', 'Tours & Series', 'tours.html'],
    ['shame', 'Wall of Shame', 'shame.html'],
  ];

  // Specials (music videos, Q&As, cheat days, food tours, milestones) are not
  // competitive bouts: they never carry a verdict and stay out of the stats.
  const isChallenge = r => (r && r.kind) !== 'special';

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const yt = id => `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
  const cleanTitle = t => String(t || '').replace(/\s*\|\s*BeardMeatsFood\s*$/i, '');
  const fmt = n => n == null ? '–' : Number(n).toLocaleString('en-GB');

  // Site-wide date format: "13 July 2026".
  const fmtDate = (iso) => {
    const s = String(iso || '').slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return '–';
    const d = new Date(`${s}T00:00:00Z`);
    return isNaN(d) ? '–' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
  };

  // Display names for every alpha-2 code in the data (plus likely next stops);
  // falls back to the raw code so a new country never breaks rendering.
  const COUNTRY_NAMES = {
    GB: 'United Kingdom', US: 'United States', CA: 'Canada', DE: 'Germany',
    SG: 'Singapore', DK: 'Denmark', IT: 'Italy', PT: 'Portugal', BE: 'Belgium',
    NO: 'Norway', SE: 'Sweden', FI: 'Finland', CZ: 'Czechia', NL: 'Netherlands',
    IS: 'Iceland', FR: 'France', AT: 'Austria', DO: 'Dominican Republic',
    IE: 'Ireland', ES: 'Spain', AU: 'Australia', NZ: 'New Zealand', CH: 'Switzerland',
    PL: 'Poland', MX: 'Mexico', JP: 'Japan', AE: 'United Arab Emirates', TH: 'Thailand',
  };
  const countryName = cc => COUNTRY_NAMES[cc] || cc || '–';

  // OpenMoji colour SVGs (CC BY-SA 4.0), hotlinked from jsDelivr — no binaries in
  // the repo. Flags are regional-indicator pairs (GB -> 1F1EC-1F1E7.svg).
  const openmojiUrl = cp => `https://cdn.jsdelivr.net/npm/openmoji@15.1.0/color/svg/${cp}.svg`;
  const flagUrl = cc => openmojiUrl(String(cc || '').toUpperCase().split('')
    .map(c => (0x1F1E6 + c.charCodeAt(0) - 65).toString(16).toUpperCase()).join('-'));

  // Display labels for cuisine buckets, in the channel's voice (data keys unchanged).
  const CUISINE_LABEL = {
    'burger': 'Burger Off!',
    'breakfast': 'The Full English',
    'pizza': 'Pizza the Action',
    'dessert & sweet': 'Do You Have Any Desserts?',
    'wings & chicken': 'Winging It',
    'sandwich & sub': 'Sub-mission',
    'mexican': "Mexican or Mexican't?",
    'steak & grill': 'Raising the Steaks',
    'curry & asian': 'Keep Calm and Curry On',
    'bbq & ribs': 'Rib Ticklers',
    'hot dog': 'Hot Dawg!',
    'fish & chips': 'The Codfather',
    'pasta & italian': 'Pasta La Vista',
    'roast dinner': 'Sunday Service',
    'other': 'Mixed Bag',
  };
  const cuisineLabel = k => CUISINE_LABEL[k] || k || '–';

  function stats(allRows) {
    const rows = allRows.filter(isChallenge);
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

  return { COLORS, esc, yt, cleanTitle, fmt, fmtDate, countryName, cuisineLabel, openmojiUrl, flagUrl, isChallenge, stats, loadData, nav, tooltip };
})();
