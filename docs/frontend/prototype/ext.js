/* ext.js: roles, menu, overview extras, live feed, search palette, notifications */
(() => {
  const N = window.NX;
  const { $, $$, S, ROLES, ROLE_DESC, can, kes, toast, EXT, MENU, ICONS, TITLES, PUBLIC, APP, M, savings, deposits, withdrawals, mount, fAx, fTipM, loans, mem, accts, stepIdx, reduce, logoSvg } = N;

  /* ---------- the platform owner role, and what the SACCO admin also does ---------- */
  ROLES.platform = { label: 'Platform owner', perms: ['platform', 'dashboard.view', 'admin.manage', 'sacco.manage', 'sacco.update'] };
  ROLE_DESC.platform = 'Runs SACCOs and owners. Cannot read SACCO money';
  ROLES.admin.perms.push('sacco.update', 'support.approve');

  /* ---------- shared sample state used by the platform pages and the admin's access requests ---------- */
  const DB = N.DB = {
    saccos: [
      { id: 1, name: 'Alpha SACCO', status: 'Active', members: 148, admin: 'Jordan Mwangi', approvals: 2, cap: 150000, mult: 3, created: '12 Mar 2024' },
      { id: 2, name: 'Beta SACCO', status: 'Active', members: 92, admin: 'Faith Njeri', approvals: 1, cap: 80000, mult: 3, created: '2 Jun 2024' },
      { id: 3, name: 'Gamma SACCO', status: 'Suspended', members: 41, admin: 'Peter Otieno', approvals: 2, cap: 100000, mult: 2, created: '19 Sep 2024' },
      { id: 4, name: 'Delta SACCO', status: 'Active', members: 57, admin: 'Amina Yusuf', approvals: 1, cap: 60000, mult: 3, created: '4 Jan 2025' }
    ],
    owners: [{ name: 'Platform owner one', email: 'owner1@example.com', me: true }, { name: 'Platform owner two', email: 'owner2@example.com' }, { name: 'Platform owner three', email: 'owner3@example.com' }],
    access: [
      { id: 1, sacco: 'Alpha SACCO', scopes: ['audit'], reason: 'Look into a reported sign-in problem', status: 'pending', expires: '' },
      { id: 2, sacco: 'Beta SACCO', scopes: ['members', 'loans'], reason: 'Help the admin fix a stuck loan', status: 'approved', expires: 'Tomorrow, 14:00' }
    ],
    events: [
      ['18 Nov 15:12', 'Platform owner one', 'sacco.deactivate', 'Gamma SACCO'], ['17 Nov 09:40', 'Platform owner two', 'support.request', 'Alpha SACCO (audit)'],
      ['16 Nov 16:05', 'Platform owner one', 'owner.add', 'owner3@example.com'], ['14 Nov 11:20', 'Platform owner two', 'settings.update', 'Beta SACCO loan rules'],
      ['12 Nov 08:30', 'Platform owner one', 'sacco.create', 'Delta SACCO'], ['10 Nov 13:15', 'Platform owner two', 'support.revoke', 'Gamma SACCO']
    ]
  };

  /* ---------- menu, icons, titles, routes ---------- */
  const set = (k, p) => { ICONS[k] = p; };
  set('pf-overview', ICONS.overview);
  set('pf-saccos', '<path d="M4 20V8l8-4 8 4v12"/><path d="M9 20v-6h6v6"/>');
  set('pf-owners', '<circle cx="8" cy="12" r="3.5"/><path d="M11.5 12H21M17 12v3M20 12v2"/>');
  set('pf-access', '<path d="M10 14a4 4 0 010-6l2-2a4 4 0 016 6l-1 1"/><path d="M14 10a4 4 0 010 6l-2 2a4 4 0 01-6-6l1-1"/>');
  set('pf-audit', ICONS.audit);
  set('deposit', '<path d="M12 4v10M8 10l4 4 4-4M5 19h14"/>');
  set('withdraw', '<path d="M12 14V4M8 8l4-4 4 4M5 19h14"/>');
  set('requests', '<path d="M5 4h14v16H5z"/><path d="M9 9l2 2 4-4M9 15h6"/>');
  set('access', '<circle cx="8" cy="12" r="3.5"/><path d="M11.5 12H21M17 12v3M20 12v2"/>');
  set('settings', '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/>');
  const sacco = () => !can('platform');
  MENU.length = 0;
  MENU.push(
    { r: 'pf-overview', t: 'Platform overview', ok: () => can('platform') },
    { r: 'pf-saccos', t: 'SACCOs', ok: () => can('platform') },
    { r: 'pf-owners', t: 'Owners', ok: () => can('platform') },
    { r: 'pf-access', t: 'Access to SACCOs', ok: () => can('platform') },
    { r: 'pf-audit', t: 'Platform audit', ok: () => can('platform') },
    { r: 'overview', t: 'Overview', ok: () => sacco() && can('dashboard.view') },
    { r: 'savings', t: 'My savings', ok: () => sacco() && can('savings.request') },
    { r: 'deposit', t: 'Deposit', ok: () => sacco() && can('savings.request') },
    { r: 'withdraw', t: 'Withdraw', ok: () => sacco() && can('savings.request') },
    { r: 'accounts', t: 'Accounts', ok: () => sacco() && can('savings.view_all') },
    { r: 'money', t: 'Post money', ok: () => sacco() && can('savings.post') },
    { r: 'requests', t: 'Requests', ok: () => sacco() && can('savings.post') },
    { r: 'loans', t: 'Loans', ok: () => sacco() && (can('loan.view') || can('loan.request')) },
    { r: 'members', t: 'Members', ok: () => sacco() && can('member.view') },
    { r: 'reports', t: 'Reports', ok: () => sacco() && can('report.view') },
    { r: 'audit', t: 'Audit log', ok: () => sacco() && can('audit.view') },
    { r: 'access', t: 'Access requests', ok: () => sacco() && can('support.approve') },
    { r: 'settings', t: 'SACCO settings', ok: () => sacco() && can('sacco.update') }
  );
  Object.assign(TITLES, { deposit: 'Deposit', withdraw: 'Withdraw', requests: 'Deposit and withdrawal requests', 'pf-overview': 'Platform overview', 'pf-saccos': 'SACCOs', 'pf-owners': 'Platform owners', 'pf-access': 'Access to SACCOs', 'pf-audit': 'Platform audit', access: 'Access requests', settings: 'SACCO settings', account: 'My account settings' });
  PUBLIC.push('register', 'verify', 'forgot');
  APP.push('deposit', 'withdraw', 'requests', 'pf-overview', 'pf-saccos', 'pf-owners', 'pf-access', 'pf-audit', 'access', 'settings', 'account');

  /* ---------- what needs each role right now ---------- */
  const pendingAccess = () => DB.access.filter(a => a.status === 'pending' && a.sacco === 'Alpha SACCO').length;
  const waitingForMe = () => loans.filter(l => l.status === 'open' && stepIdx(l) >= 0 && !(stepIdx(l) > 0 && l.steps.slice(0, stepIdx(l)).some(x => x && x.by === 'me'))).length;
  const toDisburse = () => loans.filter(l => l.status === 'approved').length;
  const pendingReq = () => (N.RQ || []).filter(r => r.st === 'Pending').length;
  const invited = () => mem.filter(m => m[2] === 'Invited').length;
  function needs() {
    switch (S.role) {
      case 'loans': return [{ n: waitingForMe(), t: 'Loans need your decision', s: 'Open the queue', go: 'loans', hot: true }, { n: loans.filter(l => l.status === 'open').length, t: 'Open loans in total', s: 'See every step', go: 'loans' }, { n: 148, t: 'Members', s: 'Check a borrower', go: 'members' }];
      case 'finance': return [{ n: toDisburse(), t: 'Approved loans to disburse', s: 'Pay them out', go: 'money', hot: true }, { n: pendingReq(), t: 'Member requests waiting', s: 'Confirm or reject', go: 'requests', hot: pendingReq() > 0 }, { n: 1, t: 'Reversed entry', s: 'Read why', go: 'accounts' }];
      case 'secretary': return [{ n: 4, t: 'Audit entries today', s: 'Read the log', go: 'audit' }, { n: loans.filter(l => l.status === 'open').length, t: 'Open loans', s: 'Read the queue', go: 'loans' }, { n: invited(), t: 'Members invited, not joined', s: 'See members', go: 'members' }];
      case 'admin': return [{ n: pendingAccess(), t: 'Platform access requests', s: 'Approve or deny', go: 'access', hot: pendingAccess() > 0 }, { n: pendingReq(), t: 'Member requests waiting', s: 'Confirm or reject', go: 'requests', hot: pendingReq() > 0 }, { n: invited(), t: 'Members waiting to join', s: 'Share a join code', go: 'members' }];
      default: return [];
    }
  }
  const needsHtml = list => list.length ? `<div class="needs">${list.map(x => `<a class="need ${x.hot ? 'hot' : ''}" href="#${x.go}"><span class="n">${x.n}</span><span><b>${x.t}</b><small>${x.s}</small></span></a>`).join('')}</div>` : '';
  const memberNeeds = () => [
    { n: 1, t: 'Payment due 30 Nov', s: 'KES 8,500 on loan #2019', go: 'loans', hot: true },
    { n: 62, t: 'Percent of your loan repaid', s: 'See the schedule', go: 'loans' },
    { n: 2, t: 'SACCO accounts', s: 'Alpha and Beta', go: 'savings' }
  ];

  /* ---------- live activity ---------- */
  /* every item knows where it leads: [mark, title, detail, colour, page, what to open there] */
  const POOL = [
    ['+', 'Deposit posted', 'Member 5 · KES 6,000', 'var(--teal)', 'accounts', 'acct:A-0005'], ['−', 'Withdrawal posted', 'Member 7 · KES 3,500', 'var(--terra)', 'accounts', 'acct:A-0007'],
    ['2', 'Loan #2058 requested', 'Member 5 · KES 200,000', 'var(--teal-2)', 'loans', 'loan:2058'], ['✓', 'Loan #2051 approved', 'Step 1 of 1', 'var(--teal)', 'loans', 'loan:2051'],
    ['+', 'Deposit posted', 'Member 3 · KES 4,200', 'var(--teal)', 'accounts', 'acct:A-0003'], ['↺', 'Entry reversed', 'Member 1 · KES 2,000', 'var(--saffron)', 'accounts', 'acct:A-0001']
  ];
  let feed = POOL.slice(0, 4).map((p, i) => ({ p, t: `${i * 3 + 2} min ago` }));
  const reach = page => MENU.some(m => m.r === page && m.ok());
  const goAttrs = (page, open) => reach(page) ? `data-go="${page}" data-open="${open || ''}" tabindex="0" role="link"` : '';
  const feedRow = (x, cls) => `<div class="row ${cls || ''}" ${goAttrs(x.p[4], x.p[5])}><div class="ico" style="background:${x.p[3]}">${x.p[0]}</div><div><div class="title">${x.p[1]}</div><div class="sub">${x.p[2]}</div></div><span class="sub">${x.t}</span></div>`;
  let pi = 4;
  setInterval(() => {
    const list = $('#live-feed'); if (!list || reduce || document.hidden || document.body.classList.contains('hold') || list.closest('[hidden]')) return;
    feed.unshift({ p: POOL[pi++ % POOL.length], t: 'just now' }); feed = feed.slice(0, 5);
    list.innerHTML = feed.map((x, i) => feedRow(x, i === 0 ? 'new' : '')).join('');
  }, 6500);

  /* ---------- overview enhancements ---------- */
  let range = 12;
  function drawRange() {
    const n = range;
    mount('#c-savings', (el, st) => N.renderLine(el, { values: savings.slice(-n), labels: M.slice(-n), color: 'var(--teal)', fmtAxis: fAx('M'), fmtTip: fTipM }, st));
    mount('#c-flow', (el, st) => N.renderBars(el, { labels: M.slice(-n), fmtAxis: a => a.toFixed(1), fmtTip: fTipM, series: [{ name: 'deposits', values: deposits.slice(-n), color: 'var(--teal)' }, { name: 'withdrawals', values: withdrawals.slice(-n), color: 'var(--terra)' }] }, st));
  }
  function enhanceOverview() {
    const sa = $('#ov-sacco'), me = $('#ov-member');
    $$('.needs, .live-card').forEach(e => e.remove());
    if (sa && !can('platform')) {
      sa.insertAdjacentHTML('afterbegin', needsHtml(needs()));
      sa.insertAdjacentHTML('beforeend', `<div class="glass live-card rise"><div class="card-head"><div><div class="eyebrow"><span class="live-dot"></span>Live activity</div><h3 class="serif">What is happening now</h3></div><a class="btn ghost small" href="#audit-or-reports" data-go-role>See reports</a></div><div class="feed" id="live-feed">${feed.map(x => feedRow(x)).join('')}</div></div>`);
      const link = sa.querySelector('[data-go-role]'); if (link) { link.setAttribute('href', can('audit.view') ? '#audit' : '#reports'); link.textContent = can('audit.view') ? 'Open audit log' : 'See reports'; }
      const head = $('#c-savings') && $('#c-savings').parentElement.querySelector('.delta');
      if (head && !head.querySelector('.seg')) head.insertAdjacentHTML('beforeend', `<div class="seg small" role="group" aria-label="Range">${[3, 6, 12].map(n => `<button type="button" data-range="${n}" aria-selected="${n === range}">${n}M</button>`).join('')}</div>`);
      [['#s-members', 'members'], ['#s-dep', 'reports'], ['#s-wd', 'reports'], ['#s-rep', 'loans']].forEach(([id, go]) => { const c = $(id) && $(id).closest('.glass'); if (c) { c.dataset.go = go; c.tabIndex = 0; c.setAttribute('role', 'link'); } });
      const dw = $('#c-donut') && $('#c-donut').closest('.donut-wrap');
      if (dw && !dw._hl) {
        dw._hl = true;
        $$('.leg-list > div', dw).forEach((d, i) => {
          d.addEventListener('pointerenter', () => { dw.classList.add('hl'); const arcs = $$('.arc', dw); arcs.forEach((a, j) => a.classList.toggle('on', j === i)); });
          d.addEventListener('pointerleave', () => { dw.classList.remove('hl'); $$('.arc', dw).forEach(a => a.classList.remove('on')); });
        });
      }
      if (range !== 12) drawRange();
      linkRows(sa);
    }
    if (me) { me.insertAdjacentHTML('afterbegin', needsHtml(memberNeeds())); linkRows(me); }
  }
  /* rows and table lines on the dashboards lead somewhere real */
  function linkRows(root) {
    $$('.row, tbody tr', root).forEach(r => {
      if (r.dataset.go) return;
      const t = r.textContent, loan = /Loan #(\d+)/.exec(t);
      let page = '', open = '';
      if (loan && reach('loans')) { page = 'loans'; open = 'loan:' + loan[1]; }
      else if (/Member \d+/.test(t) && r.tagName === 'TR' && reach('accounts')) { const m = /Member \d+/.exec(t)[0], a = accts.find(x => x[0] === m); page = 'accounts'; open = a ? 'acct:' + a[1] : ''; }
      else if (root.id === 'ov-member' && reach('savings')) page = 'savings';
      if (page) { r.dataset.go = page; r.dataset.open = open; r.tabIndex = 0; r.setAttribute('role', 'link'); }
    });
    /* a pill that says Open is a button, so make it one */
    $$('.row .chip', root).forEach(c => { if (c.textContent.trim() === 'Open' && c.closest('.row').dataset.go) { const b = document.createElement('span'); b.className = 'btn ghost small'; b.textContent = 'Open'; b.setAttribute('aria-hidden', 'true'); c.replaceWith(b); } });
  }
  N.reach = reach; N.goAttrs = goAttrs;
  EXT.after.overview = [enhanceOverview];

  document.addEventListener('click', e => {
    const r = e.target.closest('[data-range]');
    if (r) { range = +r.dataset.range; $$('[data-range]').forEach(b => b.setAttribute('aria-selected', String(b === r))); drawRange(); return; }
    const g = e.target.closest('[data-go]'); if (g && !e.target.closest('a,button')) go(g);
  });
  function go(g) { N.open = g.dataset.open || ''; if (location.hash === '#' + g.dataset.go) N.show(g.dataset.go); else location.hash = g.dataset.go; }
  document.addEventListener('keydown', e => { if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset && e.target.dataset.go) { e.preventDefault(); go(e.target); } });

  /* ---------- notifications ---------- */
  function bellItems() {
    const list = S.role === 'member' ? memberNeeds().slice(0, 1) : S.role === 'platform' ? [{ n: DB.access.filter(a => a.status === 'approved').length, t: 'Access grants active', s: 'Open access', go: 'pf-access' }, { n: 1, t: 'Suspended SACCO', s: 'Gamma SACCO is locked', go: 'pf-saccos' }] : needs();
    return list.filter(x => x.n > 0);
  }
  function paintBell() {
    const items = bellItems(); $('#bell-dot').hidden = !items.length;
    $('#bell-menu').innerHTML = `<div class="bm-head">Needs your attention</div>` + (items.length ? items.map(x => `<a href="#${x.go}"><b>${x.n} · ${x.t}</b><small>${x.s}</small></a>`).join('') : '<div class="bm-head" style="text-transform:none;letter-spacing:0;font-weight:500">You are all caught up.</div>');
  }
  $('#bell-btn').addEventListener('click', e => { e.stopPropagation(); paintBell(); const m = $('#bell-menu'); m.hidden = !m.hidden; $('#bell-btn').setAttribute('aria-expanded', String(!m.hidden)); });
  document.addEventListener('click', e => { if (!e.target.closest('#bell-wrap')) $('#bell-menu').hidden = true; });
  EXT.after.overview.push(paintBell);
  setInterval(paintBell, 4000);

  /* ---------- search and jump (Ctrl or Cmd + K) ---------- */
  let sel = 0, results = [];
  function palItems(q) {
    const pages = MENU.filter(m => m.ok()).map(m => ({ t: m.t, s: 'Page', go: m.r }));
    const people = sacco() ? [...mem.map(m => ({ t: m[0], s: 'Member', go: 'members' })), ...accts.map(a => ({ t: `${a[1]} · ${a[0]}`, s: 'Account', go: 'accounts' }))].filter(() => can('member.view') || can('savings.view_all')) : [];
    const extras = [{ t: 'My account settings', s: 'Page', go: 'account' }, { t: 'Log out', s: 'Action', go: '#logout' }];
    return [...pages, ...extras, ...people].filter(x => x.t.toLowerCase().includes(q.toLowerCase())).slice(0, 9);
  }
  function paintPal() { $('#pal-list').innerHTML = results.map((r, i) => `<button class="pal-item" role="option" aria-selected="${i === sel}" data-i="${i}"><span>${r.t}</span><small>${r.s}</small></button>`).join('') || '<div class="pal-item"><small>Nothing matches. Try a page or a member name.</small></div>'; }
  function openPal() { if (!S.authed) return; $('#palette').hidden = false; $('#pal-q').value = ''; sel = 0; results = palItems(''); paintPal(); $('#pal-q').focus(); }
  function closePal() { $('#palette').hidden = true; }
  function pick(i) { const r = results[i]; if (!r) return; closePal(); if (r.go === '#logout') $('#logout').click(); else location.hash = r.go; }
  $('#search-btn').addEventListener('click', openPal);
  $('#pal-q').addEventListener('input', e => { sel = 0; results = palItems(e.target.value); paintPal(); });
  $('#pal-list').addEventListener('click', e => { const b = e.target.closest('[data-i]'); if (b) pick(+b.dataset.i); });
  $('#palette').addEventListener('click', e => { if (e.target.id === 'palette') closePal(); });
  addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); $('#palette').hidden ? openPal() : closePal(); return; }
    if ($('#palette').hidden) return;
    if (e.key === 'Escape') closePal();
    if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(results.length - 1, sel + 1); paintPal(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(0, sel - 1); paintPal(); }
    if (e.key === 'Enter') { e.preventDefault(); pick(sel); }
  });

  /* ---------- landing: the lit coin that follows the cursor ---------- */
  const hl = $('#hero-logo'); if (hl) hl.innerHTML = logoSvg('');
  /* ---------- landing: menu for small screens, and sections that rise into view ---------- */
  const burger = $('#lnav-burger'), pop = $('#lnav-pop');
  burger.addEventListener('click', e => { e.stopPropagation(); pop.hidden = !pop.hidden; burger.setAttribute('aria-expanded', String(!pop.hidden)); });
  pop.addEventListener('click', () => { pop.hidden = true; burger.setAttribute('aria-expanded', 'false'); });
  document.addEventListener('click', e => { if (!e.target.closest('.lnav')) { pop.hidden = true; burger.setAttribute('aria-expanded', 'false'); } });
  const io = 'IntersectionObserver' in window && !reduce ? new IntersectionObserver(es => es.forEach(en => {
    if (!en.isIntersecting) return; const el = en.target; io.unobserve(el); el.dataset.r = 'in'; setTimeout(() => { delete el.dataset.r; }, 1500);
  }), { threshold: .12 }) : null;
  function armReveal() {
    if (!io) return;
    $$('#landing .sec .glass, #landing .cta-band').forEach(el => { if (el.dataset.r || el.getBoundingClientRect().top < innerHeight * .9) return; el.dataset.r = 'pre'; io.observe(el); });
  }
  new MutationObserver(() => { if ($('#landing').classList.contains('on')) armReveal(); }).observe($('#landing'), { attributes: true, attributeFilter: ['class'] });
  N.back = (label, attr) => `<div class="page-back"><button type="button" class="back" ${attr}>← ${label}</button></div>`;
})();
