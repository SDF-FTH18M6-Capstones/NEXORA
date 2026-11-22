(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canHover = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del(k) { try { localStorage.removeItem(k); } catch (e) {} }
  };

  /* LOGO SLOT: one place to swap the NEXORA logo for every .brand on every screen. */
  const EXT = { pages: {}, after: {} };
  const logoSvg = cls => `<svg class="${cls}" viewBox="0 0 100 100" aria-hidden="true"><circle cx="50" cy="50" r="46" fill="url(#lg-disc)"/><circle cx="50" cy="50" r="46" fill="none" stroke="url(#lg-ring)" stroke-width="3.2"/><g filter="url(#lg-sh)"><path d="M29 71V29h11v42z" fill="url(#lg-face)"/><path d="M29 29h11l31 42H60z" fill="url(#lg-diag)"/><path d="M60 29h11v42H60z" fill="url(#lg-face)"/></g><path d="M40 29l8.5 11.5H40z" fill="#000" opacity=".2"/><ellipse cx="38" cy="26" rx="27" ry="14" fill="url(#lg-gloss)" transform="rotate(-20 38 26)"/><g class="orbit"><circle cx="50" cy="4" r="4.4" fill="var(--saffron)"/></g></svg>`;
  const BRAND = logoSvg('mark') + '<span class="brand-text">NEXORA</span>';
  $$('.brand').forEach(e => { e.innerHTML = BRAND; });

  /* ---------- roles and permissions (names from backend/app/security/permissions.py) ---------- */
  const ROLES = {
    admin: { label: 'SACCO admin', perms: ['dashboard.view', 'sacco.view', 'member.view', 'member.manage', 'savings.view', 'savings.view_all', 'savings.post', 'savings.reverse', 'loan.view', 'report.view'] },
    secretary: { label: 'Secretary', perms: ['dashboard.view', 'sacco.view', 'member.view', 'savings.view', 'savings.view_all', 'loan.view', 'audit.view', 'report.view'] },
    finance: { label: 'Finance officer', perms: ['dashboard.view', 'sacco.view', 'savings.view', 'savings.view_all', 'savings.post', 'savings.reverse', 'loan.view', 'loan.disburse', 'loan.repay', 'report.view'] },
    loans: { label: 'Loans officer', perms: ['dashboard.view', 'sacco.view', 'member.view', 'savings.view', 'loan.view', 'loan.approve', 'report.view'] },
    member: { label: 'Member', perms: ['dashboard.view', 'sacco.view', 'savings.view', 'savings.request', 'loan.request', 'loan.repay'] }
  };
  const S = { role: store.get('nexora.role') || 'admin', authed: !!store.get('nexora.session'), route: null, ov: 'sacco', busy: false, queued: false };
  const can = p => (ROLES[S.role] || ROLES.admin).perms.includes(p);

  const ICONS = {
    overview: '<path d="M4 4h7v9H4zM13 4h7v5h-7zM13 11h7v9h-7zM4 15h7v5H4z"/>',
    money: '<path d="M12 3v18M17 7.5c0-1.9-2.2-3-5-3s-5 1.1-5 3 2.2 3 5 3 5 1.1 5 3-2.2 3-5 3-5-1.1-5-3"/>',
    loans: '<path d="M3 7h18v10H3z"/><circle cx="12" cy="12" r="2.6"/>',
    members: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.7 0 4.5 1.8 4.5 4.5"/>',
    reports: '<path d="M5 20V11M11 20V4M17 20v-6M3 20h18"/>',
    audit: '<path d="M12 3l8 3v6c0 4.5-3.2 7.8-8 9-4.8-1.2-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    savings: '<path d="M4 8h16v11H4z"/><path d="M4 8l11-4v4"/><circle cx="16.5" cy="13.5" r="1.2"/>',
    accounts: '<path d="M5 4h14v16H5z"/><path d="M9 9h6M9 13h6M9 17h4"/>'
  };
  const MENU = [
    { r: 'overview', t: 'Overview', ok: () => can('dashboard.view') },
    { r: 'savings', t: 'My savings', ok: () => can('savings.view') },
    { r: 'accounts', t: 'Accounts', ok: () => can('savings.view_all') },
    { r: 'money', t: 'Post money', ok: () => can('savings.post') },
    { r: 'loans', t: 'Loans', ok: () => can('loan.view') || can('loan.request') },
    { r: 'members', t: 'Members', ok: () => can('member.view') },
    { r: 'reports', t: 'Reports', ok: () => can('report.view') },
    { r: 'audit', t: 'Audit log', ok: () => can('audit.view') }
  ];
  const TITLES = { overview: 'Overview', 'my-account': 'Overview', savings: 'My savings', accounts: 'Accounts', money: 'Post money', loans: 'Loans', members: 'Members', reports: 'Reports', audit: 'Audit log' };
  const PUBLIC = ['landing', 'login', 'join'];
  const APP = ['overview', 'my-account', 'savings', 'accounts', 'money', 'loans', 'members', 'reports', 'audit'];
  const allowed = r => { const m = MENU.find(x => x.r === (r === 'my-account' ? 'overview' : r)); return !m || m.ok(); };

  function buildMenu() {
    $('#side-nav').innerHTML = MENU.filter(m => m.ok()).map(m =>
      `<a href="#${m.r}" data-route="${m.r}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[m.r]}</svg>${m.t}</a>`).join('');
    $('#profile-role').textContent = ROLES[S.role].label;
    buildRoleMenu();
  }
  const ROLE_DESC = { admin: 'Adds members, posts money, reads reports', secretary: 'Reads everything, changes nothing', finance: 'Posts money, disburses approved loans', loans: 'Approves or rejects loan steps', member: 'Own savings and loans only' };
  function buildRoleMenu() {
    $('#role-menu').innerHTML = Object.keys(ROLES).map(k => `<button type="button" role="menuitemradio" aria-checked="${k === S.role}" data-role="${k}"><span><b>${ROLES[k].label}</b><small>${ROLE_DESC[k]}</small></span><span class="tick">${k === S.role ? '✓' : ''}</span></button>`).join('');
    $('#role-btn-label').textContent = ROLES[S.role].label;
  }

  /* ---------- pointer: spotlight, parallax, tilt ---------- */
  addEventListener('pointermove', e => {
    const x = e.clientX / innerWidth, y = e.clientY / innerHeight, r = document.documentElement.style;
    r.setProperty('--mx', (x * 100) + '%'); r.setProperty('--my', (y * 100) + '%');
    r.setProperty('--px', (x - .5).toFixed(3)); r.setProperty('--py', (y - .5).toFixed(3));
  }, { passive: true });
  function bindTilt(el) {
    if (!canHover || reduce || el._tilt) return; el._tilt = true;
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      el.style.setProperty('--rx', (-y * 5).toFixed(2) + 'deg'); el.style.setProperty('--ry', (x * 5).toFixed(2) + 'deg');
      el.style.setProperty('--gx', ((x + .5) * 100) + '%'); el.style.setProperty('--gy', ((y + .5) * 100) + '%');
    });
    el.addEventListener('pointerleave', () => { el.style.setProperty('--rx', '0deg'); el.style.setProperty('--ry', '0deg'); });
  }
  const tilts = () => $$('.tilt').forEach(bindTilt);

  let tt;
  function toast(msg, kind) { const t = $('#toast'); t.textContent = msg; t.classList.toggle('err', kind === 'err'); t.classList.add('show'); clearTimeout(tt); tt = setTimeout(() => t.classList.remove('show'), 3000); }
  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 3 | 8)).toString(16); }));
  const kes = n => 'KES ' + n.toLocaleString('en-KE');

  /* ---------- sample data ---------- */
  const M = ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'];
  const savings = [8.2, 8.6, 8.9, 9.4, 9.8, 10.1, 10.7, 11.0, 11.6, 12.0, 12.1, 12.4];
  const deposits = [0.9, 1.1, 0.8, 1.2, 1.0, 1.3, 1.4, 1.1, 1.5, 1.3, 1.2, 1.4];
  const withdrawals = [0.4, 0.6, 0.5, 0.7, 0.5, 0.6, 0.7, 0.6, 0.7, 0.5, 0.6, 0.5];
  const balance = [120, 128, 131, 140, 146, 152, 160, 164, 171, 177, 181, 186.4];
  const contrib = [5.5, 6, 6, 7, 6, 6.5, 7, 6, 6, 7.5, 6, 6.5];
  const membersTrend = [131, 133, 136, 138, 139, 141, 142, 143, 144, 145, 142, 148];
  const repayTrend = [91, 92, 90, 93, 94, 92, 95, 93, 96, 95, 94, 96];

  /* ---------- charts: drawn once on arrival; a resize redraws still, with no replay ---------- */
  const smooth = p => {
    let d = `M${p[0][0]},${p[0][1]}`;
    for (let i = 0; i < p.length - 1; i++) {
      const p0 = p[i - 1] || p[i], p1 = p[i], p2 = p[i + 1], p3 = p[i + 2] || p2;
      d += ` C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
    }
    return d;
  };
  const uid = () => 'g' + Math.random().toString(36).slice(2, 9);
  const autoH = W => Math.round(Math.min(280, Math.max(180, W * .36)));

  function renderLine(el, o, still) {
    const W = el.clientWidth; if (!W) return;
    const H = o.h || autoH(W), axis = o.axis !== false;
    const pl = axis ? 44 : 4, pr = 8, pt = 14, pb = axis ? 28 : 4;
    const v = o.values, n = v.length, max = Math.max(...v) * 1.12;
    const X = i => pl + i * (W - pl - pr) / (n - 1), Y = a => pt + (H - pt - pb) * (1 - a / max);
    const line = smooth(v.map((a, i) => [X(i), Y(a)])), base = H - pb, id = uid();
    let s = `<div class="plot"><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${o.color}" stop-opacity=".36"/><stop offset="1" stop-color="${o.color}" stop-opacity="0"/></linearGradient></defs>`;
    if (axis) {
      for (let k = 0; k <= 4; k++) { const a = max * k / 4, y = Y(a); s += `<line class="gl" x1="${pl}" x2="${W - pr}" y1="${y}" y2="${y}"/><text class="ax" x="${pl - 8}" y="${y + 4}" text-anchor="end">${o.fmtAxis(a)}</text>`; }
      const every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor((W - pl) / 54))));
      v.forEach((_, i) => { if (i % every === 0 || i === n - 1) s += `<text class="ax" x="${X(i)}" y="${H - 8}" text-anchor="middle">${o.labels[i]}</text>`; });
    }
    s += `<path d="${line} L${X(n - 1)},${base} L${X(0)},${base} Z" fill="url(#${id})"/><path d="${line}" fill="none" stroke="${o.color}" stroke-width="${o.sw || 2.8}" stroke-linecap="round"/>`;
    if (!o.static) s += `<line id="${id}g" y1="${pt}" y2="${base}" stroke="${o.color}" stroke-opacity=".4" stroke-dasharray="3 4" opacity="0"/><circle id="${id}d" r="6" fill="${o.color}" stroke="#fff" stroke-width="2.5" opacity="0"/><rect x="${pl}" y="0" width="${W - pl - pr}" height="${H}" fill="transparent"/>`;
    el.className = el.className.replace(/\bstill\b/g, '').trim() + (still ? ' still' : '');
    el.innerHTML = s + `</svg></div>` + (o.static ? '' : `<div class="tip" hidden></div>`);
    if (o.static) return;
    const svg = el.querySelector('svg'), tip = el.querySelector('.tip'), g = svg.querySelector('#' + id + 'g'), d = svg.querySelector('#' + id + 'd');
    svg.addEventListener('pointermove', e => {
      const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
      let i = Math.round((px - pl) / (W - pl - pr) * (n - 1)); i = Math.max(0, Math.min(n - 1, i));
      g.setAttribute('x1', X(i)); g.setAttribute('x2', X(i)); g.setAttribute('opacity', 1);
      d.setAttribute('cx', X(i)); d.setAttribute('cy', Y(v[i])); d.setAttribute('opacity', 1);
      tip.hidden = false; tip.textContent = o.labels[i] + ' · ' + o.fmtTip(v[i]);
      tip.style.left = (X(i) / W * r.width) + 'px'; tip.style.top = (Y(v[i]) / H * r.height) + 'px';
    });
    svg.addEventListener('pointerleave', () => { g.setAttribute('opacity', 0); d.setAttribute('opacity', 0); tip.hidden = true; });
  }

  function renderBars(el, o, still) {
    const W = el.clientWidth; if (!W) return;
    const H = o.h || autoH(W), pl = 44, pr = 8, pt = 14, pb = 28;
    const max = Math.max(...o.series.flatMap(x => x.values)) * 1.15, n = o.labels.length, gw = (W - pl - pr) / n, bw = Math.max(4, Math.min(16, gw * .26));
    const Y = a => pt + (H - pt - pb) * (1 - a / max);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true">`;
    for (let k = 0; k <= 4; k++) { const a = max * k / 4, y = Y(a); s += `<line class="gl" x1="${pl}" x2="${W - pr}" y1="${y}" y2="${y}"/><text class="ax" x="${pl - 8}" y="${y + 4}" text-anchor="end">${o.fmtAxis(a)}</text>`; }
    const every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor((W - pl) / 40))));
    o.labels.forEach((lab, i) => {
      const cx = pl + gw * i + gw / 2;
      o.series.forEach((se, j) => {
        const a = se.values[i], two = o.series.length > 1, x = two ? cx + (j === 0 ? -bw - 2 : 2) : cx - bw / 2, y = Y(a);
        s += `<rect class="bar" x="${x}" y="${y}" width="${bw}" height="${H - pb - y}" rx="${Math.min(6, bw / 2)}" fill="${se.color}" style="--d:${i * 40}ms"><title>${lab} ${se.name}: ${o.fmtTip(a)}</title></rect>`;
      });
      if (i % every === 0 || i === n - 1) s += `<text class="ax" x="${cx}" y="${H - 8}" text-anchor="middle">${lab}</text>`;
    });
    el.className = el.className.replace(/\bstill\b/g, '').trim() + (still ? ' still' : '');
    el.innerHTML = s + '</svg>';
  }

  function renderDonut(el, parts, top, sub, still) {
    const r = 72, sw = 20, C = 2 * Math.PI * r, total = parts.reduce((a, p) => a + p.value, 0); let off = 0;
    let s = `<svg viewBox="0 0 200 200" aria-hidden="true"><circle cx="100" cy="100" r="${r}" fill="none" stroke="color-mix(in srgb, var(--ink) 8%, transparent)" stroke-width="${sw}"/>`;
    parts.forEach(p => { const len = C * p.value / total; s += `<circle class="arc" style="--c:${C}" cx="100" cy="100" r="${r}" fill="none" stroke="${p.color}" stroke-width="${sw}" stroke-dasharray="${len - 2} ${C - len + 2}" stroke-dashoffset="${-off}" transform="rotate(-90 100 100)"/>`; off += len; });
    el.className = el.className.replace(/\bstill\b/g, '').trim() + (still ? ' still' : '');
    el.innerHTML = s + `<text class="donut-top" x="100" y="100" text-anchor="middle">${top}</text><text class="donut-sub" x="100" y="120" text-anchor="middle">${sub}</text></svg>`;
  }
  function renderRing(el, pct, still) {
    const r = 62, sw = 14, C = 2 * Math.PI * r;
    el.className = el.className.replace(/\bstill\b/g, '').trim() + (still ? ' still' : '');
    el.innerHTML = `<svg viewBox="0 0 160 160" aria-hidden="true"><defs><linearGradient id="ringg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="var(--saffron)"/><stop offset=".55" stop-color="var(--teal-2)"/><stop offset="1" stop-color="var(--teal)"/></linearGradient></defs><circle cx="80" cy="80" r="${r}" fill="none" stroke="color-mix(in srgb, var(--ink) 10%, transparent)" stroke-width="${sw}"/><circle class="arc" style="--c:${C}" cx="80" cy="80" r="${r}" fill="none" stroke="url(#ringg)" stroke-width="${sw}" stroke-linecap="round" stroke-dasharray="${C * pct / 100} ${C}" transform="rotate(-90 80 80)"/><text class="ring-label" x="80" y="88" text-anchor="middle">${pct}%</text><text class="ring-cap" x="80" y="108" text-anchor="middle">repaid</text></svg>`;
  }

  const dirty = new Set(); let rt;
  const ro = new ResizeObserver(es => {
    es.forEach(e => dirty.add(e.target)); clearTimeout(rt);
    rt = setTimeout(() => { dirty.forEach(el => { const w = el.clientWidth; if (w && el._fn && Math.abs(w - el._w) > 16) { el._w = w; el._fn(el, true); } }); dirty.clear(); }, 200);
  });
  function mount(sel, fn) { const el = typeof sel === 'string' ? $(sel) : sel; if (!el || !el.clientWidth) return; el._fn = fn; el._w = el.clientWidth; fn(el, false); ro.observe(el); }

  const fAx = u => a => a.toFixed(a >= 10 ? 0 : 1) + u;
  const fTipM = a => 'KES ' + a.toFixed(1) + 'M', fTipK = a => 'KES ' + a.toFixed(1) + 'K';
  const sparkOpt = (vals, color) => ({ values: vals, labels: M, color, axis: false, static: true, sw: 2, h: 56 });

  function drawLanding() {
    mount('#lp-chart', (el, st) => renderLine(el, { values: savings, labels: M, color: 'var(--teal)', h: 150, axis: false, fmtAxis: fAx('M'), fmtTip: fTipM }, st));
  }
  function drawSacco() {
    mount('#c-savings', (el, st) => renderLine(el, { values: savings, labels: M, color: 'var(--teal)', fmtAxis: fAx('M'), fmtTip: fTipM }, st));
    mount('#c-donut', (el, st) => renderDonut(el, [{ value: 3.5, color: 'var(--teal)' }, { value: .4, color: 'var(--saffron)' }, { value: .2, color: 'var(--terra)' }], '4.1M', 'KES total', st));
    mount('#c-flow', (el, st) => renderBars(el, { labels: M, fmtAxis: a => a.toFixed(1), fmtTip: fTipM, series: [{ name: 'deposits', values: deposits, color: 'var(--teal)' }, { name: 'withdrawals', values: withdrawals, color: 'var(--terra)' }] }, st));
    [['#s-members', membersTrend, 'var(--teal-2)'], ['#s-dep', deposits, 'var(--teal-2)'], ['#s-wd', withdrawals, 'var(--terra)'], ['#s-rep', repayTrend, 'var(--saffron)']].forEach(([id, v, c]) =>
      mount(id, (el, st) => renderLine(el, sparkOpt(v, c), st)));
  }
  function drawMember() {
    mount('#c-balance', (el, st) => renderLine(el, { values: balance, labels: M, color: 'var(--teal)', fmtAxis: fAx('K'), fmtTip: fTipK }, st));
    mount('#c-contrib', (el, st) => renderBars(el, { labels: M, fmtAxis: fAx('K'), fmtTip: fTipK, series: [{ name: 'contributions', values: contrib, color: 'var(--saffron)' }] }, st));
    mount('#c-ring', (el, st) => renderRing(el, 62, st));
  }
  function drawReports() {
    mount('#r-savings', (el, st) => renderLine(el, { values: savings, labels: M, color: 'var(--teal-2)', fmtAxis: fAx('M'), fmtTip: fTipM }, st));
    mount('#r-flow', (el, st) => renderBars(el, { labels: M, fmtAxis: a => a.toFixed(1), fmtTip: fTipM, series: [{ name: 'deposits', values: deposits, color: 'var(--teal)' }, { name: 'withdrawals', values: withdrawals, color: 'var(--terra)' }] }, st));
  }

  function countUp(el) {
    if (reduce) return;
    const to = parseFloat(el.dataset.count), dec = +(el.dataset.dec || 0), pre = el.dataset.pre || '', suf = el.dataset.suf || '', t0 = performance.now();
    const step = t => { const p = Math.min(1, (t - t0) / 1700), e = 1 - Math.pow(1 - p, 3); el.textContent = pre + (to * e).toLocaleString('en-KE', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf; if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }
  const runCounts = () => $$('[data-count]').filter(e => e.offsetParent !== null).forEach(countUp);

  /* ---------- page markup: overview ---------- */
  const OVERVIEW = `
  <section id="ov-sacco" class="stack">
    <div class="grid">
      <div class="glass s8 rise"><div class="card-head"><div><div class="eyebrow">Total SACCO savings</div><div class="big hero-num" data-count="12.4" data-dec="1" data-pre="KES " data-suf="M">KES 12.4M</div></div><div class="delta"><span class="chip up">+4.2% since Jun</span><span class="chip">Dec to Nov</span></div></div><div class="chart" id="c-savings" role="img" aria-label="SACCO savings over 12 months"></div></div>
      <div class="glass tilt s4 rise" style="--s:80ms"><div class="eyebrow">Loan book</div><h3 class="serif" style="font-size:1.5rem;margin:.3rem 0 1rem">38 open loans</h3><div class="donut-wrap"><div class="chart" id="c-donut" role="img" aria-label="Loan book by status" style="min-height:0"></div><div class="leg-list"><div><span><i style="background:var(--teal)"></i>Current</span><b>KES 3.5M</b></div><div><span><i style="background:var(--saffron)"></i>Watch</span><b>KES 0.4M</b></div><div><span><i style="background:var(--terra)"></i>In arrears</span><b>KES 0.2M</b></div></div></div></div>
      <div class="glass tilt s3 rise" style="--s:120ms"><div class="kpi"><div class="eyebrow">Members</div><div class="big" data-count="148">148</div><div class="delta"><span class="chip up">+6 this month</span></div><div class="spark chart" id="s-members" aria-hidden="true" style="min-height:0"></div></div></div>
      <div class="glass tilt s3 rise" style="--s:160ms"><div class="kpi"><div class="eyebrow">Deposits, Nov</div><div class="big" data-count="1.4" data-dec="1" data-pre="KES " data-suf="M">KES 1.4M</div><div class="delta"><span class="chip up">+KES 0.2M vs Oct</span></div><div class="spark chart" id="s-dep" aria-hidden="true" style="min-height:0"></div></div></div>
      <div class="glass tilt s3 rise" style="--s:200ms"><div class="kpi"><div class="eyebrow">Withdrawals, Nov</div><div class="big" data-count="0.5" data-dec="1" data-pre="KES " data-suf="M">KES 0.5M</div><div class="delta"><span class="chip">Within normal range</span></div><div class="spark chart" id="s-wd" aria-hidden="true" style="min-height:0"></div></div></div>
      <div class="glass tilt s3 rise" style="--s:240ms"><div class="kpi"><div class="eyebrow">On-time repayment</div><div class="big" data-count="96" data-suf="%">96%</div><div class="delta"><span class="chip up">Target 90%</span></div><div class="spark chart" id="s-rep" aria-hidden="true" style="min-height:0"></div></div></div>
      <div class="glass s7 rise" style="--s:100ms"><div class="card-head"><div><div class="eyebrow">Money in and out</div><h3 class="serif">Deposits against withdrawals</h3></div></div><div class="chart" id="c-flow" role="img" aria-label="Monthly deposits and withdrawals"></div><div class="legend"><span><i style="background:var(--teal)"></i>Deposits (KES M)</span><span><i style="background:var(--terra)"></i>Withdrawals (KES M)</span></div></div>
      <div class="glass s5 rise" style="--s:160ms"><div class="card-head"><div><div class="eyebrow">Waiting for a decision</div><h3 class="serif">Loans to review</h3></div><a class="btn ghost small" href="#loans">Open queue</a></div><div class="list">
        <div class="row"><div class="ico" style="background:var(--teal)">2</div><div><div class="title">Loan #2045 · KES 150,000</div><div class="sub">Step 2 waiting · 12 months</div></div><span class="chip">Open</span></div>
        <div class="row"><div class="ico" style="background:var(--terra)">5</div><div><div class="title">Loan #2051 · KES 40,000</div><div class="sub">1 approval needed · 6 months</div></div><span class="chip">Open</span></div>
        <div class="row"><div class="ico" style="background:var(--teal-2)">8</div><div><div class="title">Loan #2058 · KES 200,000</div><div class="sub">Step 2 waiting · 18 months</div></div><span class="chip">Open</span></div></div></div>
      <div class="glass s12 rise" style="--s:200ms"><div class="card-head"><div><div class="eyebrow">Latest movements</div><h3 class="serif">Recent transactions</h3></div></div><div class="table-wrap"><table><thead><tr><th>Date</th><th>Member</th><th>Type</th><th class="r">Amount</th><th>Status</th></tr></thead><tbody>
        <tr><td>17 Nov</td><td>Member 3</td><td>Deposit</td><td class="r">KES 12,000</td><td><span class="chip up">Posted</span></td></tr>
        <tr><td>17 Nov</td><td>Member 9</td><td>Loan repayment</td><td class="r">KES 8,500</td><td><span class="chip up">Posted</span></td></tr>
        <tr><td>16 Nov</td><td>Member 7</td><td>Withdrawal</td><td class="r">KES 4,000</td><td><span class="chip">Posted</span></td></tr>
        <tr><td>16 Nov</td><td>Member 1</td><td>Deposit</td><td class="r">KES 20,000</td><td><span class="chip bad">Reversed</span></td></tr></tbody></table></div></div>
    </div>
  </section>
  <section id="ov-member" class="stack" hidden>
    <div class="grid">
      <div class="glass s8 rise"><div class="card-head"><div><div class="eyebrow">My savings balance</div><div class="big hero-num" data-count="186400" data-pre="KES ">KES 186,400</div></div><div class="delta"><span class="chip up">+KES 5,200 this month</span><span class="chip">Since Dec</span></div></div><div class="chart" id="c-balance" role="img" aria-label="My balance over 12 months"></div></div>
      <div class="glass tilt s4 rise" style="--s:80ms"><div class="eyebrow">My loan · #2019</div><h3 class="serif" style="font-size:1.5rem;margin:.3rem 0 .2rem">KES 100,000</h3><div class="muted" style="font-size:.9rem">12-month loan, approved in Sep</div><div class="ring-wrap"><div class="chart" id="c-ring" role="img" aria-label="62 percent repaid" style="min-height:0"></div></div><div class="muted" style="font-size:.88rem;text-align:center">Repaid KES 62,000 · next payment KES 8,500 on 30 Nov</div><div class="actions" style="justify-content:center"><a class="btn small" href="#loans">Repay</a><a class="btn ghost small" href="#loans">Request a loan</a></div></div>
      <div class="glass s6 rise" style="--s:120ms"><div class="card-head"><div><div class="eyebrow">Contributions</div><h3 class="serif">Monthly savings</h3></div></div><div class="chart" id="c-contrib" role="img" aria-label="Monthly contributions in KES thousands"></div><div class="legend"><span><i style="background:var(--saffron)"></i>Contributions (KES thousands)</span></div></div>
      <div class="glass s6 rise" style="--s:180ms"><div class="card-head"><div><div class="eyebrow">Activity</div><h3 class="serif">My transactions</h3></div></div><div class="list">
        <div class="row"><div class="ico" style="background:var(--teal)">+</div><div><div class="title">Deposit</div><div class="sub">17 Nov · Posted</div></div><div class="amt">KES 8,500</div></div>
        <div class="row"><div class="ico" style="background:var(--terra)">−</div><div><div class="title">Loan repayment</div><div class="sub">30 Oct · Posted</div></div><div class="amt">KES 8,500</div></div>
        <div class="row"><div class="ico" style="background:var(--teal-2)">+</div><div><div class="title">Deposit</div><div class="sub">12 Oct · Posted</div></div><div class="amt">KES 6,000</div></div>
        <div class="row"><div class="ico" style="background:var(--saffron)">↺</div><div><div class="title">Deposit reversed</div><div class="sub">4 Oct · Reversed by the officer</div></div><div class="amt">KES 2,000</div></div></div></div>
    </div>
  </section>`;

  /* ---------- loans ---------- */
  const loans = [
    { id: 2045, who: 'Member 3', amount: 150000, term: 12, need: 2, date: '14 Nov', steps: [{ by: 'me' }, null], status: 'open' },
    { id: 2051, who: 'Member 7', amount: 40000, term: 6, need: 1, date: '16 Nov', steps: [null], status: 'open' },
    { id: 2058, who: 'Member 5', amount: 200000, term: 18, need: 2, date: '17 Nov', steps: [{ by: 'other' }, null], status: 'open' },
    { id: 2039, who: 'Member 4', amount: 60000, term: 6, need: 1, date: '9 Nov', steps: [{ by: 'other' }], status: 'approved' }
  ];
  let rejecting = null, loanBanner = '';
  const stepIdx = l => l.steps.findIndex(x => x === null);
  function loanCard(l) {
    const idx = stepIdx(l), canApprove = can('loan.approve') && l.status === 'open';
    const mine = idx > 0 && l.steps.slice(0, idx).some(x => x && x.by === 'me');
    const pill = l.status === 'approved' ? '<span class="chip up">Approved</span>' : l.status === 'rejected' ? '<span class="chip bad">Rejected</span>' : l.status === 'disbursed' ? '<span class="chip up">Disbursed</span>' : '<span class="chip warn">Open</span>';
    const stepHtml = l.steps.map((s, i) => {
      let st, txt;
      if (s) { st = '<span class="chip up">Approved</span>'; txt = s.by === 'me' ? 'You decided this step.' : 'Decided by another officer.'; }
      else if (l.status === 'rejected') { st = '<span class="chip bad">Stopped</span>'; txt = 'The loan was rejected.'; }
      else if (i === idx) { st = '<span class="chip warn">Waiting</span>'; txt = canApprove && !mine ? 'Your decision is needed.' : 'Waiting for a loans officer.'; }
      else { st = '<span class="chip">Not started</span>'; txt = 'Opens after the earlier step.'; }
      return `<div class="step"><h4>Step ${i + 1}</h4>${st}<p>${txt}</p></div>`;
    }).join('');
    let act = '';
    if (canApprove) {
      if (mine) act = `<div class="banner info" style="margin:1rem 0 0">You already decided step ${idx}. A different officer must decide step ${idx + 1}.</div>`;
      else act = `<div class="actions"><button class="btn small" data-act="approve" data-id="${l.id}">Approve</button><button class="btn warn small" data-act="reject-open" data-id="${l.id}">Reject</button></div>` +
        (rejecting === l.id ? `<textarea class="reason" id="reason-${l.id}" placeholder="Write the reason for rejecting this loan."></textarea><div class="actions"><button class="btn warn small" data-act="reject-go" data-id="${l.id}">Confirm rejection</button><button class="btn ghost small" data-act="reject-cancel">Cancel</button></div>` : '');
    }
    return `<article class="glass rise"><div class="loan-head"><div><h3 class="serif">Loan #${l.id}</h3><div class="muted" style="font-size:.88rem">Requested by ${l.who} · ${l.date} ${pill}</div></div><div class="amount">${kes(l.amount)}<small>${l.term} months · ${l.need} approval${l.need > 1 ? 's' : ''} needed</small></div></div><div class="steps">${stepHtml}</div>${act}</article>`;
  }
  function renderLoans() {
    if (EXT.pages.loans) { EXT.pages.loans(); return; }
    let h = loanBanner ? `<div class="banner ${loanBanner.k}" role="status">${loanBanner.t}</div>` : '';
    if (can('loan.view')) {
      const q = loans.filter(l => l.status === 'open');
      h += `<div class="eyebrow" style="margin-bottom:.6rem">${can('loan.approve') ? 'Waiting for a decision' : 'Loan queue (read only)'}</div><div class="stack">` + (q.length ? q.map(loanCard).join('') : `<div class="glass">No loans are waiting for a decision.</div>`) + '</div>';
    }
    if (can('loan.disburse')) {
      const a = loans.filter(l => l.status === 'approved');
      h += `<div class="eyebrow" style="margin:1.6rem 0 .6rem">Approved, ready to disburse</div><div class="stack">` + (a.length ? a.map(l => `<article class="glass rise"><div class="loan-head"><div><h3 class="serif">Loan #${l.id}</h3><div class="muted" style="font-size:.88rem">${l.who} · ${l.term} months</div></div><div class="amount">${kes(l.amount)}</div></div><div class="actions"><button class="btn small" data-act="disburse" data-id="${l.id}">Disburse</button></div></article>`).join('') : `<div class="glass">No approved loans are waiting to be disbursed.</div>`) + '</div>';
    }
    if (can('loan.request')) {
      h += `<div class="grid"><div class="glass s7 rise"><div class="card-head"><div><div class="eyebrow">My loan · #2019</div><h3 class="serif" style="font-size:1.6rem;margin-top:.3rem">KES 100,000</h3></div><span class="chip up">Disbursed in Sep</span></div>
          <div class="bar-track" role="img" aria-label="62 percent repaid"><i style="width:62%"></i></div><div class="muted" style="font-size:.88rem;margin:.5rem 0 1rem">Repaid KES 62,000 of 100,000</div>
          <div class="table-wrap"><table><thead><tr><th>Due</th><th class="r">Amount</th><th>Status</th></tr></thead><tbody><tr><td>30 Oct</td><td class="r">KES 8,500</td><td><span class="chip up">Paid</span></td></tr><tr><td>30 Nov</td><td class="r">KES 8,500</td><td><span class="chip warn">Next</span></td></tr><tr><td>30 Dec</td><td class="r">KES 8,500</td><td><span class="chip">Upcoming</span></td></tr></tbody></table></div>
          <div class="actions"><button class="btn small" data-act="repay">Repay KES 8,500</button></div></div>
        <form class="glass s5 rise" id="req-form"><div class="eyebrow">Request a loan</div><div class="field"><label for="rq-amt">Amount (KES)</label><input id="rq-amt" inputmode="numeric" placeholder="50,000"></div><div class="field"><label for="rq-term">Term</label><select id="rq-term"><option>6 months</option><option>12 months</option><option>18 months</option></select></div><button class="btn small" type="submit" style="margin-top:1rem">Send request</button></form></div>`;
    }
    $('#p-loans').innerHTML = h;
  }

  /* ---------- money ---------- */
  const ledger = [
    { id: 1, who: 'Member 3', type: 'Deposit', amt: 12000, st: 'posted' },
    { id: 2, who: 'Member 7', type: 'Withdrawal', amt: 4000, st: 'posted' },
    { id: 3, who: 'Member 1', type: 'Deposit', amt: 20000, st: 'reversed' }
  ];
  let ref = uuid(), lastPost = null, moneyBanner = '';
  function renderMoney() {
    $('#p-money').innerHTML = `${moneyBanner ? `<div class="banner ${moneyBanner.k}" role="status">${moneyBanner.t}</div>` : ''}
    <div class="grid"><form class="glass s5 rise" id="post-form"><div class="eyebrow">New entry</div><h3 class="serif" style="font-size:1.4rem;margin-top:.3rem">Post a deposit or withdrawal</h3>
      <div class="field"><label for="m-who">Member account</label><select id="m-who"><option>Member 1</option><option>Member 3</option><option>Member 5</option><option>Member 7</option></select></div>
      <div class="field"><label for="m-type">Type</label><select id="m-type"><option>Deposit</option><option>Withdrawal</option><option>Interest</option><option>Fee</option></select></div>
      <div class="field"><label for="m-amt">Amount (KES)</label><input id="m-amt" inputmode="numeric" placeholder="10,000"></div>
      <div class="field"><label for="m-ref">Reference (one per submit)</label><input id="m-ref" value="${ref}" readonly></div>
      <div class="actions"><button class="btn small" type="submit">Post entry</button><button class="btn ghost small" type="button" data-act="retry" ${lastPost ? '' : 'disabled'}>Retry last request</button></div></form>
      <div class="glass s7 rise" style="--s:80ms"><div class="card-head"><div><div class="eyebrow">Ledger</div><h3 class="serif">Latest entries</h3></div></div><div class="list">${ledger.map(e => `<div class="row"><div class="ico" style="background:${e.type === 'Deposit' ? 'var(--teal)' : 'var(--terra)'}">${e.type === 'Deposit' ? '+' : '−'}</div><div><div class="title">${e.type} · ${e.who}</div><div class="sub">${e.st === 'reversed' ? 'Reversed' : 'Posted'}</div></div><div class="amt">${kes(e.amt)} <button class="btn ghost small" data-act="reverse" data-id="${e.id}">${e.st === 'reversed' ? 'Reverse again' : 'Reverse'}</button></div></div>`).join('')}</div></div></div>`;
  }

  /* ---------- members ---------- */
  const mem = [['Member 1', '0712 ••• 118', 'Active', 'member'], ['Member 3', '0722 ••• 540', 'Active', 'loans'], ['Member 5', '0733 ••• 902', 'Active', 'member'], ['Member 7', '0745 ••• 261', 'Active', 'finance'], ['Member 9', '0758 ••• 077', 'Invited', 'member']];
  let joinCode = null, joinEnd = 0, joinTimer = null;
  const roleOpts = sel => ['member', 'secretary', 'finance', 'loans'].map(r => `<option value="${r}" ${r === sel ? 'selected' : ''}>${ROLES[r].label}</option>`).join('');
  function renderMembers() {
    if (EXT.pages.members) { EXT.pages.members(); return; }
    const manage = can('member.manage');
    $('#p-members').innerHTML = `<div class="grid">
      <div class="glass ${manage ? 's7' : 's12'} rise"><div class="card-head"><div><div class="eyebrow">${mem.length} members</div><h3 class="serif">Members and roles</h3></div></div><div class="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Status</th><th>Role</th></tr></thead><tbody>${mem.map((m, i) => `<tr><td>${m[0]}</td><td>${m[1]}</td><td><span class="chip ${m[2] === 'Active' ? 'up' : 'warn'}">${m[2]}</span></td><td>${manage ? `<select aria-label="Role for ${m[0]}" data-act="setrole" data-i="${i}" class="chip" style="min-height:2rem">${roleOpts(m[3])}</select>` : ROLES[m[3]].label}</td></tr>`).join('')}</tbody></table></div></div>
      ${manage ? `<div class="glass s5 rise" style="--s:80ms"><div class="eyebrow">Add a member</div><h3 class="serif" style="font-size:1.4rem;margin-top:.3rem">Invite by phone</h3><form id="add-form"><div class="field"><label for="a-phone">Phone number</label><input id="a-phone" inputmode="tel" placeholder="+254 712 345 678"></div><button class="btn small" type="submit" style="margin-top:1rem">Add member</button></form><div id="code-area"></div></div>` : ''}</div>`;
    paintCode();
  }
  function paintCode() {
    const a = $('#code-area'); if (!a) return;
    if (!joinCode) { a.innerHTML = ''; return; }
    const left = Math.max(0, joinEnd - Date.now()), mm = String(Math.floor(left / 60000)).padStart(2, '0'), ss = String(Math.floor(left / 1000) % 60).padStart(2, '0');
    a.innerHTML = left ? `<div class="banner info" style="margin-top:1rem">Share this code once. It lasts 15 minutes and works one time.</div><div class="code-box" id="code-val">${joinCode}</div><div class="actions" style="justify-content:center"><button class="btn small" data-act="copycode">Copy code</button><span class="chip warn num" id="count">Expires in ${mm}:${ss}</span></div>` : `<div class="banner err" style="margin-top:1rem">The code expired. Add the member again to get a new one.</div>`;
  }

  /* ---------- audit ---------- */
  const auditAll = [['17 Nov 14:02', 'Officer B', 'loan.approve', 'Loan #2058 step 1'], ['17 Nov 11:40', 'Jordan M.', 'savings.post', 'Deposit KES 12,000, Member 3'], ['16 Nov 16:22', 'Jordan M.', 'savings.reverse', 'Deposit KES 20,000, Member 1'], ['16 Nov 09:15', 'Admin', 'member.add', 'Member 9 invited'], ['15 Nov 15:48', 'Jordan M.', 'loan.disburse', 'Loan #2031'], ['15 Nov 10:05', 'Officer A', 'loan.approve', 'Loan #2045 step 1'], ['14 Nov 13:30', 'Member 3', 'loan.request', 'Loan #2045'], ['13 Nov 08:50', 'Admin', 'role.set', 'Member 7: finance officer'], ['12 Nov 17:12', 'Jordan M.', 'savings.post', 'Withdrawal KES 4,000, Member 7'], ['11 Nov 09:01', 'Officer B', 'loan.reject', 'Loan #2027']];
  let auditPage = 0, auditFilter = 'all', auditQ = '';
  function renderAudit() {
    const rows = auditAll.filter(r => (auditFilter === 'all' || r[2].startsWith(auditFilter)) && (r.join(' ').toLowerCase().includes(auditQ.toLowerCase())));
    const pages = Math.max(1, Math.ceil(rows.length / 4)); auditPage = Math.min(auditPage, pages - 1);
    $('#p-audit').innerHTML = `<div class="glass rise"><div class="card-head"><div><div class="eyebrow">Read only</div><h3 class="serif">SACCO audit log</h3></div><span class="chip lock">No edit or delete</span></div>
      <div class="actions" style="margin:0 0 1rem"><select id="au-f" class="chip" aria-label="Filter by action" style="min-height:2.3rem"><option value="all">All actions</option>${['loan', 'savings', 'member', 'role'].map(x => `<option value="${x}" ${auditFilter === x ? 'selected' : ''}>${x}</option>`).join('')}</select><input id="au-q" class="chip" placeholder="Search the log" value="${auditQ}" aria-label="Search the log" style="min-height:2.3rem;min-width:12rem"></div>
      <div class="table-wrap"><table><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Target</th></tr></thead><tbody>${rows.slice(auditPage * 4, auditPage * 4 + 4).map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td><span class="chip">${r[2]}</span></td><td>${r[3]}</td></tr>`).join('') || '<tr><td colspan="4">No entries match these filters.</td></tr>'}</tbody></table></div>
      <div class="actions" style="justify-content:space-between;align-items:center"><button class="btn ghost small" data-act="au-prev" ${auditPage === 0 ? 'disabled' : ''}>Previous</button><span class="muted num">Page ${auditPage + 1} of ${pages}</span><button class="btn ghost small" data-act="au-next" ${auditPage >= pages - 1 ? 'disabled' : ''}>Next</button></div></div>`;
  }

  const REPORTS = `<div class="grid"><div class="glass s7 rise"><div class="card-head"><div><div class="eyebrow">Savings</div><h3 class="serif">Growth over 12 months</h3></div></div><div class="chart" id="r-savings" role="img" aria-label="Savings growth"></div></div>
    <div class="glass s5 rise" style="--s:80ms"><div class="card-head"><div><div class="eyebrow">Last 6 months</div><h3 class="serif">Net movement</h3></div></div><div class="table-wrap"><table><thead><tr><th>Month</th><th class="r">In</th><th class="r">Out</th><th class="r">Net</th></tr></thead><tbody>${M.slice(6).map((m, i) => { const d = deposits[6 + i], w = withdrawals[6 + i]; return `<tr><td>${m}</td><td class="r">${d.toFixed(1)}M</td><td class="r">${w.toFixed(1)}M</td><td class="r">${(d - w).toFixed(1)}M</td></tr>`; }).join('')}</tbody></table></div></div>
    <div class="glass s12 rise" style="--s:120ms"><div class="card-head"><div><div class="eyebrow">Money in and out</div><h3 class="serif">Deposits against withdrawals</h3></div></div><div class="chart" id="r-flow" role="img" aria-label="Deposits and withdrawals"></div></div>
    <div class="glass s12 rise" style="--s:160ms"><div class="card-head"><div><div class="eyebrow">Member activity</div><h3 class="serif">Who saved and who withdrew</h3></div></div><div class="table-wrap"><table><thead><tr><th>Member</th><th class="r">Deposits</th><th class="r">Withdrawals</th><th class="r">Net</th><th>Last activity</th></tr></thead><tbody><tr><td>Member 1</td><td class="r">KES 62,000</td><td class="r">KES 8,000</td><td class="r">KES 54,000</td><td>17 Nov</td></tr><tr><td>Member 3</td><td class="r">KES 48,500</td><td class="r">KES 12,000</td><td class="r">KES 36,500</td><td>17 Nov</td></tr><tr><td>Member 7</td><td class="r">KES 30,000</td><td class="r">KES 4,000</td><td class="r">KES 26,000</td><td>16 Nov</td></tr></tbody></table></div></div></div>`;

  /* ---------- my savings (every member) ---------- */
  const acctData = {
    alpha: { name: 'Alpha SACCO', bal: 186400, series: balance },
    beta: { name: 'Beta SACCO', bal: 42800, series: [30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42.8] }
  };
  const svTx = [
    { d: '17 Nov', t: 'Deposit', a: 8500, st: 'Posted' }, { d: '30 Oct', t: 'Loan repayment', a: 8500, st: 'Posted' },
    { d: '12 Oct', t: 'Deposit', a: 6000, st: 'Posted' }, { d: '4 Oct', t: 'Deposit', a: 2000, st: 'Reversed' },
    { d: '18 Sep', t: 'Interest', a: 1240, st: 'Posted' }, { d: '12 Sep', t: 'Withdrawal', a: 5000, st: 'Posted' }
  ];
  let svAcct = 'alpha', svFilter = 'all', svMode = 'deposit', svBanner = null, svPending = [];
  function renderSavings() {
    const a = acctData[svAcct];
    const rows = [...svPending, ...svTx].filter(r => svFilter === 'all' || r.t.toLowerCase().startsWith(svFilter));
    const chip = st => `<span class="chip ${st === 'Posted' ? 'up' : st === 'Reversed' ? 'bad' : 'warn'}">${st}</span>`;
    $('#p-savings').innerHTML = `${svBanner ? `<div class="banner ${svBanner.k}" role="status">${svBanner.t}</div>` : ''}
    <div class="actions" style="margin:0 0 .2rem">${Object.entries(acctData).map(([k, v]) => `<button type="button" class="chip pick" data-act="sv-acct" data-k="${k}" aria-pressed="${k === svAcct}">${v.name} account</button>`).join('')}</div>
    <div class="grid">
      <div class="glass s8 rise"><div class="card-head"><div><div class="eyebrow">My savings balance · ${a.name}</div><div class="big hero-num">${kes(a.bal)}</div></div><div class="delta"><span class="chip up">+KES 5,200 this month</span><span class="chip">Dec to Nov</span></div></div><div class="chart" id="sv-chart" role="img" aria-label="My balance over 12 months"></div></div>
      <div class="glass s4 rise" style="--s:80ms"><div class="eyebrow">Add or take out money</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0 .6rem">Send a request</h3><p class="muted">Choose M-Pesa or Bank. An officer confirms it, then it shows in this ledger.</p><div class="actions"><a class="btn small" href="#deposit">Deposit</a><a class="btn ghost small" href="#withdraw">Withdraw</a></div></div>
      <div class="glass s12 rise" style="--s:140ms"><div class="card-head"><div><div class="eyebrow">Ledger</div><h3 class="serif">My transactions</h3></div><div class="actions" style="margin:0">${['all', 'deposit', 'withdrawal', 'interest'].map(f => `<button type="button" class="chip pick" data-act="sv-filter" data-f="${f}" aria-pressed="${f === svFilter}">${f === 'all' ? 'All' : f[0].toUpperCase() + f.slice(1)}</button>`).join('')}</div></div>
        <div class="table-wrap"><table><thead><tr><th>Date</th><th>Type</th><th class="r">Amount</th><th>Status</th></tr></thead><tbody>${rows.map(r => `<tr><td>${r.d}</td><td>${r.t}</td><td class="r">${kes(r.a)}</td><td>${chip(r.st)}</td></tr>`).join('') || '<tr><td colspan="4">No transactions match this filter.</td></tr>'}</tbody></table></div></div>
    </div>`;
  }
  function drawSavings() {
    const a = acctData[svAcct];
    mount('#sv-chart', (el, st) => renderLine(el, { values: a.series, labels: M, color: 'var(--teal)', fmtAxis: fAx('K'), fmtTip: fTipK }, st));
  }

  /* ---------- accounts (savings.view_all) ---------- */
  const accts = [['Member 1', 'A-0001', 186400, '17 Nov', 'Active'], ['Member 3', 'A-0003', 92500, '17 Nov', 'Active'], ['Member 5', 'A-0005', 41800, '12 Nov', 'Active'], ['Member 7', 'A-0007', 150200, '16 Nov', 'Active'], ['Member 9', 'A-0009', 0, 'None yet', 'Invited'], ['Jordan Mwangi', 'A-0011', 186400, '17 Nov', 'Active']];
  let acQ = '', acSel = null;
  function renderAccounts() {
    if (EXT.pages.accounts) { EXT.pages.accounts(); return; }
    const rows = accts.filter(r => r.join(' ').toLowerCase().includes(acQ.toLowerCase()));
    const sel = accts.find(r => r[1] === acSel);
    $('#p-accounts').innerHTML = `<div class="grid">
      <div class="glass s12 rise"><div class="card-head"><div><div class="eyebrow">${accts.length} accounts · total ${kes(accts.reduce((s, r) => s + r[2], 0))}</div><h3 class="serif">All member accounts</h3></div><span class="chip lock">savings.view_all</span></div>
        <div class="actions" style="margin:0 0 1rem"><input id="ac-q" class="chip" placeholder="Search by name or account" value="${acQ}" aria-label="Search accounts" style="min-height:2.4rem;min-width:15rem"></div>
        <div class="table-wrap"><table><thead><tr><th>Member</th><th>Account</th><th class="r">Balance</th><th>Last activity</th><th>Status</th><th></th></tr></thead><tbody>${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="r">${kes(r[2])}</td><td>${r[3]}</td><td><span class="chip ${r[4] === 'Active' ? 'up' : 'warn'}">${r[4]}</span></td><td><button class="btn ghost small" data-act="ac-view" data-k="${r[1]}">View ledger</button></td></tr>`).join('') || '<tr><td colspan="6">No accounts match your search.</td></tr>'}</tbody></table></div></div>
      ${sel ? `<div class="glass s12 rise"><div class="card-head"><div><div class="eyebrow">${sel[1]} · ${sel[0]}</div><h3 class="serif">Ledger</h3></div><div class="actions" style="margin:0">${can('savings.post') ? '<a class="btn small" href="#money">Post money</a>' : ''}<button class="btn ghost small" data-act="ac-close">Close</button></div></div>
        <div class="list">${svTx.slice(0, 4).map(r => `<div class="row"><div class="ico" style="background:${r.t === 'Withdrawal' || r.t === 'Loan repayment' ? 'var(--terra)' : 'var(--teal)'}">${r.t === 'Withdrawal' || r.t === 'Loan repayment' ? '−' : '+'}</div><div><div class="title">${r.t}</div><div class="sub">${r.d} · ${r.st}</div></div><div class="amt">${kes(r.a)}</div></div>`).join('')}</div></div>` : ''}
    </div>`;
  }

  /* ---------- build the app stage once ---------- */
  $('#stage').innerHTML = `<div id="p-overview">${OVERVIEW}</div><div id="p-savings" hidden></div><div id="p-accounts" hidden></div><div id="p-money" hidden></div><div id="p-loans" hidden></div><div id="p-members" hidden></div><div id="p-reports" hidden>${REPORTS}</div><div id="p-audit" hidden></div>`;

  /* ---------- routing with the wave transition ---------- */
  const curtain = $('#curtain'), sigWrap = $('#sig-wrap');
  const wait = ms => new Promise(r => setTimeout(r, ms));
  function show(route) {
    S.prev = S.route; S.route = route;
    if (window.NX && NX.appearance) NX.appearance.sync();   /* each person has their own look: load it for whoever is signed in now (or the default when signed out) */
    document.body.dataset.route = route;
    $$('.page').forEach(p => p.classList.remove('on'));
    $('#app').classList.remove('on', 'open');
    $('#menu-btn').setAttribute('aria-expanded', 'false');
    scrollTo(0, 0);
    if (PUBLIC.includes(route)) {
      $('#' + route).classList.add('on');
      if (route === 'landing') requestAnimationFrame(drawLanding);
      requestAnimationFrame(() => { tilts(); });
      return;
    }
    $('#app').classList.add('on');
    buildMenu();
    $$('#side-nav a').forEach(a => a.removeAttribute('aria-current'));
    const key = route === 'my-account' ? 'overview' : route;
    const link = $(`#side-nav a[data-route="${key}"]`); if (link) link.setAttribute('aria-current', 'page');
    $('#page-title').textContent = TITLES[route] || route;
    ensureStage(key);
    $$('#stage > div').forEach(d => { d.hidden = d.id !== 'p-' + key; });
    paintAvatars();
    $('#sacco-wrap').hidden = can('platform');
    const isOv = key === 'overview';
    $('#ov-seg').hidden = true;   /* staff see the circle's overview only; a member sees their own. Nobody switches between the two. */
    if (isOv) { S.ov = S.role === 'member' ? 'member' : 'sacco'; ovSwitch(S.ov, true); }
    const bad = EXT.guard && EXT.guard(key);
    if (bad) EXT.errorPage(bad, key);
    else if (EXT.pages[key]) EXT.pages[key]();
    else {
      if (key === 'money') renderMoney();
      if (key === 'loans') renderLoans();
      if (key === 'members') renderMembers();
      if (key === 'audit') renderAudit();
      if (key === 'savings') renderSavings();
      if (key === 'accounts') renderAccounts();
    }
    requestAnimationFrame(() => { if (key === 'reports') drawReports(); if (key === 'savings') drawSavings(); (EXT.after[key] || []).forEach(f => f()); tilts(); });
  }
  function ensureStage(key) { if (!$('#p-' + key)) { const d = document.createElement('div'); d.id = 'p-' + key; d.hidden = true; $('#stage').appendChild(d); } }
  function ovSwitch(v, silent) {
    S.ov = v;
    $$('#ov-seg button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.ov === v)));
    $('#ov-sacco').hidden = v !== 'sacco'; $('#ov-member').hidden = v !== 'member';
    requestAnimationFrame(() => { v === 'sacco' ? drawSacco() : drawMember(); tilts(); if (!silent) runCounts(); });
  }

  /* the pen: a thick traced path per stroke reveals the real letters, in writing order */
  const STROKES = [
    [[112, 205], [118, 160], [150, 120], [192, 106], [186, 140], [160, 260], [125, 370], [96, 460]],
    [[206, 172], [240, 330], [278, 458], [292, 420], [322, 290], [352, 180], [384, 100]],
    [[392, 385], [440, 372], [490, 340], [500, 298], [470, 268], [425, 285], [375, 340], [362, 400], [385, 440], [430, 448], [480, 425], [520, 380]],
    [[520, 378], [538, 343], [555, 310], [582, 294], [605, 296], [626, 313], [636, 351], [643, 387], [655, 413], [673, 417], [696, 404], [719, 372], [734, 354]],
    [[542, 451], [567, 419], [605, 376], [637, 346], [673, 310], [705, 284]],
    [[822, 272], [772, 299], [734, 337], [715, 378], [714, 410], [728, 434], [752, 442], [778, 431], [802, 404], [816, 381]],
    [[846, 272], [853, 293], [844, 325], [841, 357], [851, 373], [875, 377], [898, 363], [916, 328], [931, 299], [942, 266]],
    [[942, 260], [953, 292], [956, 318], [945, 357], [942, 396], [949, 424], [978, 437], [1009, 430], [1040, 407], [1062, 379], [1075, 355]],
    [[945, 284], [973, 298], [994, 318], [997, 340], [987, 368], [980, 396], [980, 416], [990, 418]],
    [[1214, 311], [1205, 292], [1176, 281], [1130, 295], [1090, 332], [1062, 374], [1050, 407], [1062, 438], [1085, 446], [1116, 432], [1146, 404], [1169, 374], [1194, 337], [1202, 351], [1195, 374], [1187, 396], [1191, 421], [1211, 434], [1236, 418], [1264, 382], [1278, 355]]
  ];
  const TIMES = [[0, .10], [.10, .255], [.255, .35], [.35, .43], [.44, .49], [.50, .59], [.59, .675], [.675, .77], [.77, .82], [.82, 1]];
  (function buildPen() {
    const g = $('#pen-g'); if (!g || g.children.length) return; /* normally baked into the page so it starts at first paint */
    g.innerHTML = STROKES.map((pts, i) => {
      const [a, b] = TIMES[i], T0 = .3, SP = .62;
      return `<path pathLength="1" d="${smooth(pts)}" style="--s:calc(var(--sig-dur) * ${(T0 + SP * a).toFixed(3)});--d:calc(var(--sig-dur) * ${(SP * (b - a)).toFixed(3)})"/>`;
    }).join('');
  })();
  { const cs = $('#coin-stage'); if (cs && !cs.firstChild) cs.innerHTML = logoSvg('logo-big'); }
  function startSig() { sigWrap.classList.remove('go'); void sigWrap.offsetWidth; sigWrap.classList.add('go'); }
  async function transition(swap, intro) {
    if (reduce) { swap(); curtain.classList.remove('cover'); return; }
    S.busy = true; document.body.classList.add('hold');
    /* Timing by feel: the wave takes about a second to cover the screen (long enough to read as a motion, short enough not to feel like waiting),
       the pen gets the time a hand needs to write seven letters, and the lift is slower than the rise so the new page arrives calmly. */
    const D = intro ? 4.8 : 1.7;
    if (intro) {
      /* the signature has been writing since the first paint (it is baked into the page), so do not restart it:
         only work out how much of it is left, and swap the page in behind the curtain near the end */
      const fp = (performance.getEntriesByName('first-paint')[0] || performance.getEntriesByName('first-contentful-paint')[0] || { startTime: 0 }).startTime;
      const el = () => performance.now() - fp;
      await wait(Math.max(0, D * 850 - el()));
      swap();
      await wait(Math.max(350, D * 1000 + 600 - el()));
    } else {
      curtain.style.setProperty('--sig-dur', D + 's');
      curtain.classList.add('run'); void curtain.offsetWidth; curtain.classList.add('cover');
      startSig();                                  /* writes while the wave rises: no dead pause before it starts */
      await wait(900); swap();
      await wait(D * 1000 - 900 + 350);
    }
    document.body.classList.remove('hold');
    curtain.classList.add('run'); void curtain.offsetWidth;
    curtain.classList.remove('cover'); curtain.classList.add('exit');
    runCounts();
    await wait(1150);
    curtain.classList.add('reset'); curtain.classList.remove('run', 'exit', 'cover'); void curtain.offsetWidth; curtain.classList.remove('reset');
    S.busy = false;
    if (S.queued) { S.queued = false; handle(); }
  }
  function resolve(soft) {
    let h = location.hash.slice(1);
    const home = S.authed ? (can('platform') ? 'pf-overview' : 'overview') : 'landing';
    if (!h) h = home;
    else if (!PUBLIC.includes(h) && !APP.includes(h)) h = S.authed ? 'e-404' : 'landing';
    if (APP.includes(h) && !S.authed) h = 'login';
    if (S.authed && ['login', 'join', 'register', 'verify', 'forgot'].includes(h)) h = home;
    if (APP.includes(h) && !allowed(h)) h = soft ? home : 'e-403';
    return h;
  }
  function handle(first) {
    if (S.busy) { S.queued = true; return; }
    const r = resolve();
    if ('#' + r !== location.hash) history.replaceState(null, '', '#' + r);
    if (r === S.route) return;
    transition(() => show(r), !!first);
  }
  addEventListener('hashchange', () => handle(false));

  /* ---------- events ---------- */
  $$('[data-scroll]').forEach(b => b.addEventListener('click', () => { const t = $('#' + b.dataset.scroll); if (t) t.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' }); }));
  $('#menu-btn').addEventListener('click', () => { const o = $('#app').classList.toggle('open'); $('#menu-btn').setAttribute('aria-expanded', String(o)); });
  $('#scrim').addEventListener('click', () => { $('#app').classList.remove('open'); $('#menu-btn').setAttribute('aria-expanded', 'false'); });
  addEventListener('keydown', e => { if (e.key === 'Escape') { $('#app').classList.remove('open'); $('#switcher-menu').hidden = true; } });
  $('#side-nav').addEventListener('click', e => { if (e.target.closest('a')) $('#app').classList.remove('open'); });

  $('#switcher-btn').addEventListener('click', () => { const m = $('#switcher-menu'); m.hidden = !m.hidden; $('#switcher-btn').setAttribute('aria-expanded', String(!m.hidden)); });
  $$('[data-sacco]').forEach(b => b.addEventListener('click', () => {
    S.suspended = b.getAttribute('aria-disabled') === 'true';
    $('#sacco-name').textContent = b.dataset.sacco; $('#switcher-menu').hidden = true;
    if (S.route && APP.includes(S.route) && !S.busy) transition(() => show(S.route), false);
  }));
  $$('#ov-seg button').forEach(b => b.addEventListener('click', () => ovSwitch(b.dataset.ov)));

  function signIn(role) { S.role = role; S.authed = true; store.set('nexora.session', '1'); store.set('nexora.role', role); location.hash = role === 'platform' ? 'pf-overview' : 'overview'; handle(false); }
  $('#login-form').addEventListener('submit', e => { e.preventDefault(); signIn($('#role-pick').value); });
  $('#logout').addEventListener('click', () => { S.authed = false; store.del('nexora.session'); store.del('nexora.role'); location.hash = 'landing'; handle(false); });
  $('#role-btn').addEventListener('click', e => { e.stopPropagation(); const m = $('#role-menu'); m.hidden = !m.hidden; $('#role-btn').setAttribute('aria-expanded', String(!m.hidden)); });
  $('#role-menu').addEventListener('click', e => {
    const b = e.target.closest('[data-role]'); if (!b) return;
    S.role = b.dataset.role; store.set('nexora.role', S.role); $('#role-menu').hidden = true; buildMenu();
    const r = resolve(true); if ('#' + r !== location.hash) { location.hash = r; handle(false); } else { show(r); }
  });
  addEventListener('click', e => {
    if (!e.target.closest('.role-wrap')) $('#role-menu').hidden = true;
    if (!e.target.closest('.switcher-wrap')) { $('#switcher-menu').hidden = true; $('#switcher-btn').setAttribute('aria-expanded', 'false'); }
  });

  /* profile photo: choose, crop to a square, keep on this device, view big */
  const PHOTO_KEY = 'nexora.photo';
  function paintAvatars() {
    const p = store.get(PHOTO_KEY);
    $$('.avatar').forEach(a => { a.style.backgroundImage = p ? `url("${p}")` : ''; a.classList.toggle('has-photo', !!p); a.textContent = p ? '' : 'JM'; });
    const big = $('#photo-big'); big.style.backgroundImage = p ? `url("${p}")` : ''; big.textContent = p ? '' : 'JM';
    $('#photo-remove').hidden = !p;
  }
  function openPhoto() { $('#photo-modal').hidden = false; $('#photo-close').focus(); }
  function closePhoto() { $('#photo-modal').hidden = true; }
  $$('.avatar').forEach(a => a.addEventListener('click', openPhoto));
  $('#photo-close').addEventListener('click', closePhoto);
  $('#photo-modal').addEventListener('click', e => { if (e.target.id === 'photo-modal') closePhoto(); });
  addEventListener('keydown', e => { if (e.key === 'Escape') closePhoto(); });
  $('#photo-remove').addEventListener('click', () => { store.del(PHOTO_KEY); paintAvatars(); toast('Profile photo removed.'); });
  $('#photo-file').addEventListener('change', e => {
    const f = e.target.files[0]; if (!f) return;
    if (!/^image\//.test(f.type)) { toast('Choose an image file.'); return; }
    if (f.size > 8 * 1024 * 1024) { toast('That photo is too large. Choose one under 8 MB.'); return; }
    const img = new Image(), url = URL.createObjectURL(f);
    img.onload = () => {
      const s = Math.min(img.width, img.height), c = document.createElement('canvas'); c.width = c.height = 640;
      c.getContext('2d').drawImage(img, (img.width - s) / 2, (img.height - s) / 2, s, s, 0, 0, 640, 640);
      store.set(PHOTO_KEY, c.toDataURL('image/jpeg', .85)); URL.revokeObjectURL(url); paintAvatars(); toast('Profile photo updated.');
    };
    img.onerror = () => toast('We could not read that image. Try another one.');
    img.src = url; e.target.value = '';
  });
  paintAvatars();

  /* savings and accounts interactions */
  $('#stage').addEventListener('click', e => {
    const b = e.target.closest('[data-act]'); if (!b) return; const act = b.dataset.act;
    if (act === 'sv-acct') { svAcct = b.dataset.k; renderSavings(); requestAnimationFrame(() => { drawSavings(); tilts(); }); }
    if (act === 'sv-filter') { svFilter = b.dataset.f; renderSavings(); requestAnimationFrame(() => { drawSavings(); }); }
    if (act === 'sv-mode') { svMode = b.dataset.m; svBanner = null; renderSavings(); requestAnimationFrame(() => { drawSavings(); }); }
    if (act === 'ac-view') { acSel = b.dataset.k; renderAccounts(); }
    if (act === 'ac-close') { acSel = null; renderAccounts(); }
  });
  $('#stage').addEventListener('input', e => { if (e.target.id === 'ac-q') { acQ = e.target.value; renderAccounts(); const q = $('#ac-q'); q.focus(); q.setSelectionRange(q.value.length, q.value.length); } });


  /* join: code, then PIN */
  const CODE_ERR = { '000000': 'This code has expired. Ask your admin to add you again for a new one.', '111111': 'This code was already used. Sign in instead, or ask your admin for a new code.', '222222': 'This code is locked after too many wrong tries. Ask your admin to add you again.' };
  function msg(el, kind, text) { el.hidden = false; el.className = 'banner ' + kind; el.textContent = text; }
  $('#join-1').addEventListener('submit', e => {
    e.preventDefault();
    const m = $('#join-msg'), phone = $('#j-phone').value.trim(), code = $('#j-code').value.trim();
    if (!phone || code.length !== 6) { msg(m, 'err', 'Enter your phone number and the 6-digit code.'); NX.fieldError(!phone ? $('#j-phone') : $('#j-code'), !phone ? 'Enter the phone number your admin used.' : 'The code has 6 digits.'); return; }
    if (CODE_ERR[code]) { msg(m, 'err', CODE_ERR[code]); NX.fieldError($('#j-code'), 'This code cannot be used.'); return; }
    if (code !== '123456') { msg(m, 'err', 'That code is not right. Check the 6 digits and try again.'); NX.fieldError($('#j-code'), 'Check the 6 digits.'); return; }
    m.hidden = true; $('#join-1').hidden = true; $('#join-2').hidden = false; $('#pin1').focus();
  });
  $('#join-2').addEventListener('submit', e => {
    e.preventDefault();
    const a = $('#pin1').value, b = $('#pin2').value, m = $('#pin-msg');
    if (!/^\d{4}$/.test(a)) { msg(m, 'err', 'Your PIN needs exactly 4 digits.'); return; }
    if (a !== b) { msg(m, 'err', 'The two PINs do not match.'); return; }
    signIn('member');
  });

  /* delegated actions for the app pages */
  $('#stage').addEventListener('click', e => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    const act = b.dataset.act, id = +b.dataset.id, l = loans.find(x => x.id === id);
    if (act === 'approve') { const i = stepIdx(l); l.steps[i] = { by: 'me' }; if (stepIdx(l) === -1) { l.status = 'approved'; loanBanner = { k: 'ok', t: `Loan #${l.id} is fully approved and now waits for a finance officer to disburse it.` }; } else loanBanner = { k: 'ok', t: `Step ${i + 1} of loan #${l.id} approved. A different officer decides the next step.` }; rejecting = null; renderLoans(); requestAnimationFrame(tilts); }
    if (act === 'reject-open') { rejecting = id; renderLoans(); }
    if (act === 'reject-cancel') { rejecting = null; renderLoans(); }
    if (act === 'reject-go') { const r = $('#reason-' + id); if (!r.value.trim()) { loanBanner = { k: 'err', t: 'Write a reason before you reject this loan.' }; renderLoans(); return; } l.status = 'rejected'; rejecting = null; loanBanner = { k: 'ok', t: `Loan #${id} rejected. The member can see your reason.` }; renderLoans(); }
    if (act === 'disburse') { l.status = 'disbursed'; loanBanner = { k: 'ok', t: `Loan #${id} disbursed. ${kes(l.amount)} was posted to ${l.who}'s account.` }; renderLoans(); }
    if (act === 'repay') toast('Repayment recorded for this month.');
    if (act === 'retry') { moneyBanner = { k: 'info', t: 'This request was already recorded. Nothing was posted twice.' }; renderMoney(); }
    if (act === 'reverse') { const e2 = ledger.find(x => x.id === id); if (e2.st === 'reversed') moneyBanner = { k: 'err', t: 'This entry was already reversed, so nothing changed.' }; else { e2.st = 'reversed'; moneyBanner = { k: 'ok', t: 'Entry reversed. The original stays in the ledger.' }; } renderMoney(); }
    if (act === 'copycode') { const t = joinCode; (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(() => toast('Code copied.'), () => { const r = document.createRange(); r.selectNodeContents($('#code-val')); const s = getSelection(); s.removeAllRanges(); s.addRange(r); toast('Press copy to take the code.'); }); }
    if (act === 'au-prev') { auditPage--; renderAudit(); }
    if (act === 'au-next') { auditPage++; renderAudit(); }
  });
  $('#stage').addEventListener('change', e => {
    if (e.target.dataset.act === 'setrole') { mem[+e.target.dataset.i][3] = e.target.value; toast('Role updated.'); }
    if (e.target.id === 'au-f') { auditFilter = e.target.value; auditPage = 0; renderAudit(); }
  });
  $('#stage').addEventListener('input', e => { if (e.target.id === 'au-q') { auditQ = e.target.value; auditPage = 0; renderAudit(); const q = $('#au-q'); q.focus(); q.setSelectionRange(q.value.length, q.value.length); } });
  $('#stage').addEventListener('submit', e => {
    e.preventDefault();
    if (e.target.id === 'post-form') {
      const amt = +($('#m-amt').value.replace(/[^\d]/g, ''));
      if (!amt) { moneyBanner = { k: 'err', t: 'Enter an amount greater than zero.' }; renderMoney(); NX.fieldError($('#m-amt'), 'Enter an amount greater than zero.'); return; }
      ledger.unshift({ id: Date.now(), who: $('#m-who').value, type: $('#m-type').value, amt, st: 'posted' });
      lastPost = ref; ref = uuid(); moneyBanner = { k: 'ok', t: 'Entry posted. Each submit uses its own reference, so a retry never posts twice.' }; renderMoney();
    }
    if (e.target.id === 'req-form') { loanBanner = { k: 'err', t: 'You already have an open loan. Finish repaying loan #2019 before you request another.' }; renderLoans(); }
    if (e.target.id === 'add-form') {
      if (!$('#a-phone').value.trim()) { toast('Enter the phone number first.'); return; }
      joinCode = String(Math.floor(100000 + Math.random() * 900000)); joinEnd = Date.now() + 15 * 60000;
      mem.push(['New member', $('#a-phone').value.trim().slice(0, 4) + ' ••• ' + $('#a-phone').value.trim().slice(-3), 'Invited', 'member']);
      renderMembers(); clearInterval(joinTimer);
      joinTimer = setInterval(() => { if (!$('#count')) { clearInterval(joinTimer); return; } if (Date.now() >= joinEnd) { clearInterval(joinTimer); } paintCode(); }, 1000);
    }
  });

  /* ---------- go ---------- */
  document.body.dataset.route = '';
  window.NX = { $, $$, S, ROLES, ROLE_DESC, can, store, kes, toast, uuid, M, savings, deposits, withdrawals, balance, contrib, membersTrend, repayTrend, renderLine, renderBars, renderDonut, renderRing, mount, fAx, fTipM, fTipK, tilts, runCounts, countUp, loans, loanCard, stepIdx, mem, accts, svTx, ledger, auditAll, acctData, MENU, ICONS, TITLES, PUBLIC, APP, EXT, handle, show, resolve, signIn, paintAvatars, msg, openPhoto, buildMenu, reduce, logoSvg, drawSacco, drawMember, ovSwitch, smooth, paintCode };
  window.NX.start = () => { if (!ROLES[S.role]) S.role = 'admin'; handle(true); };
})();
