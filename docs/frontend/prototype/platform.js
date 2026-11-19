/* platform.js: platform owner pages, and the public account pages (register, verify, forgot, reset) */
(() => {
  const N = window.NX;
  const { $, $$, S, can, kes, toast, EXT, M, mount, renderLine, renderDonut, fAx, DB, auditAll, msg } = N;
  const chip = (t, k) => `<span class="chip ${k || ''}">${t}</span>`;
  const st = s => chip(s, s === 'Active' || s === 'Approved' ? 'up' : s === 'Suspended' || s === 'Denied' || s === 'Revoked' ? 'bad' : 'warn');
  const back = (label, attr) => `<div class="page-back"><button type="button" class="back" ${attr}>← ${label}</button></div>`;
  const log = (action, target) => DB.events.unshift(['Just now', 'Platform owner one', action, target]);
  /* where a platform event leads: SACCO events open that SACCO, access events the access page, owner events the owners */
  const evGo = e => {
    const a = e[2], t = e[3];
    if (/^sacco\./.test(a)) return ['pf-saccos', 'sacco:' + t];
    if (/^settings\./.test(a)) return ['pf-saccos', 'sacco:' + t.replace(/ loan rules$/, '')];
    if (/^support\./.test(a)) return ['pf-access', ''];
    if (/^owner\./.test(a)) return ['pf-owners', ''];
    return ['pf-audit', ''];
  };
  const evAttrs = e => { const [p, o] = evGo(e); return `data-go="${p}" data-open="${o}" tabindex="0" role="link"`; };

  /* ---------- platform overview: counts and health, never SACCO money ---------- */
  const saccoGrowth = [1, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4];
  const memberGrowth = [120, 140, 160, 170, 210, 230, 250, 270, 290, 300, 320, 338];
  EXT.pages['pf-overview'] = () => {
    const active = DB.saccos.filter(s => s.status === 'Active').length, sus = DB.saccos.length - active, pend = DB.access.filter(a => a.status === 'pending').length;
    $('#p-pf-overview').innerHTML = `<div class="needs">
        <a class="need ${pend ? 'hot' : ''}" href="#pf-access"><span class="n">${pend}</span><span><b>Access requests pending</b><small>Waiting for a SACCO admin</small></span></a>
        <a class="need ${sus ? 'hot' : ''}" href="#pf-saccos"><span class="n">${sus}</span><span><b>Suspended SACCO</b><small>Locked until you reopen it</small></span></a>
        <a class="need" href="#pf-owners"><span class="n">${DB.owners.length}</span><span><b>Platform owners</b><small>At least two always remain</small></span></a></div>
      <div class="grid">
        <div class="glass tilt s8 rise"><div class="card-head"><div><div class="eyebrow">Members across all SACCOs</div><div class="big hero-num" data-count="338">338</div></div><div class="delta"><span class="chip up">+18 this month</span></div></div><div class="chart" id="pf-g2" role="img" aria-label="Members across the platform"></div></div>
        <div class="glass tilt s4 rise" style="--s:80ms"><div class="eyebrow">SACCOs</div><h3 class="serif" style="font-size:1.5rem;margin:.3rem 0 1rem">${DB.saccos.length} on the platform</h3><div class="donut-wrap"><div class="chart" id="pf-donut" role="img" aria-label="SACCOs by status" style="min-height:0"></div><div class="leg-list"><div><span><i style="background:var(--teal)"></i>Active</span><b>${active}</b></div><div><span><i style="background:var(--terra)"></i>Suspended</span><b>${sus}</b></div></div></div></div>
        <div class="glass s7 rise" style="--s:120ms"><div class="card-head"><div><div class="eyebrow">Growth</div><h3 class="serif">SACCOs on the platform</h3></div></div><div class="chart" id="pf-g1" role="img" aria-label="SACCOs over twelve months"></div></div>
        <div class="glass s5 rise" style="--s:160ms"><div class="card-head"><div><div class="eyebrow">Latest</div><h3 class="serif">Platform activity</h3></div><a class="btn ghost small" href="#pf-audit">Platform audit</a></div><div class="list">${DB.events.slice(0, 4).map(e => `<div class="row" ${evAttrs(e)}><div class="ico" style="background:var(--teal)">${e[2][0].toUpperCase()}</div><div><div class="title">${e[2]}</div><div class="sub">${e[3]} · ${e[0]}</div></div><span class="btn ghost small" aria-hidden="true">Open</span></div>`).join('')}</div></div>
        <div class="glass s12 rise" style="--s:200ms"><b>Platform owners cannot read SACCO money.</b> <span class="muted">Balances, accounts and loans stay hidden. To read a SACCO's records you ask for access, and that SACCO's admin must approve.</span></div></div>`;
  };
  EXT.after['pf-overview'] = [() => {
    mount('#pf-g2', (el, s) => renderLine(el, { values: memberGrowth, labels: M, color: 'var(--teal)', fmtAxis: v => Math.round(v), fmtTip: v => Math.round(v) + ' members' }, s));
    mount('#pf-g1', (el, s) => renderLine(el, { values: saccoGrowth, labels: M, color: 'var(--terra)', fmtAxis: v => Math.round(v), fmtTip: v => Math.round(v) + ' SACCOs' }, s));
    const a = DB.saccos.filter(x => x.status === 'Active').length;
    mount('#pf-donut', (el, s) => renderDonut(el, [{ value: a, color: 'var(--teal)' }, { value: Math.max(DB.saccos.length - a, .0001), color: 'var(--terra)' }], String(DB.saccos.length), 'SACCOs', s));
    N.runCounts();
  }];

  /* ---------- SACCOs: list, create, and a detail page behind each ---------- */
  let sSel = null, sBan = null, confirmSus = false;
  EXT.pages['pf-saccos'] = () => {
    const host = $('#p-pf-saccos');
    const o = N.open || ''; if (o.startsWith('sacco:')) { N.open = ''; const s = DB.saccos.find(x => x.name === o.slice(6)); if (s) { sSel = s.id; sBan = null; confirmSus = false; } }
    if (sSel) return saccoDetail(host);
    host.innerHTML = `${sBan ? `<div class="banner ${sBan.k}" role="status">${sBan.t}</div>` : ''}<div class="grid"><div class="glass s8 rise"><div class="card-head"><div><div class="eyebrow">${DB.saccos.length} SACCOs</div><h3 class="serif">All SACCOs</h3></div></div><div class="table-wrap"><table><thead><tr><th>Name</th><th>Status</th><th class="r">Members</th><th>Admin</th><th></th></tr></thead><tbody>${DB.saccos.map(s => `<tr><td>${s.name}</td><td>${st(s.status)}</td><td class="r">${s.members}</td><td>${s.admin}</td><td><button class="btn ghost small" data-sac="${s.id}">Open</button></td></tr>`).join('')}</tbody></table></div></div>
      <form class="glass s4 rise" id="sac-new" style="--s:80ms"><div class="eyebrow">sacco.manage</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0">Create a SACCO</h3><div class="field"><label for="sn-name">Name</label><input id="sn-name" placeholder="Epsilon SACCO"></div><div class="field"><label for="sn-admin">First admin's email</label><input id="sn-admin" type="email" placeholder="admin@example.com"></div><button class="btn small" type="submit" style="margin-top:1rem">Create SACCO</button></form></div>`;
  };
  function saccoDetail(host) {
    const s = DB.saccos.find(x => x.id === sSel), sus = s.status === 'Suspended';
    host.innerHTML = `${back('Back to SACCOs', 'data-sac-back')}${sBan ? `<div class="banner ${sBan.k}" role="status">${sBan.t}</div>` : ''}<div class="grid">
      <div class="glass s7 rise"><div class="detail-head"><div><div class="eyebrow">SACCO</div><h3 class="serif" style="font-size:1.8rem">${s.name}</h3></div>${st(s.status)}</div><div class="kv"><div><span>Members</span><b>${s.members}</b></div><div><span>Admin</span><b>${s.admin}</b></div><div><span>Created</span><b>${s.created}</b></div><div><span>Currency</span><b>KES</b></div></div>
        <div class="actions"><button class="btn ${sus ? '' : 'warn'} small" data-sac-status>${confirmSus ? 'Click again to confirm' : sus ? 'Reopen this SACCO' : 'Suspend this SACCO'}</button><button class="btn ghost small" data-sac-admin>Replace the admin</button></div>
        <p class="note">${sus ? 'Every screen for this SACCO answers that it is suspended. Sign-in still works for its members.' : 'Suspending locks every screen of this SACCO for its members until you reopen it.'}</p></div>
      <form class="glass s5 rise" id="sac-rules" style="--s:80ms"><div class="eyebrow">Loan rules</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0">Set for this SACCO</h3><div class="field"><label for="lr-ap">Approvals above the cap</label><select id="lr-ap"><option ${s.approvals === 1 ? 'selected' : ''}>1</option><option ${s.approvals === 2 ? 'selected' : ''}>2</option></select></div><div class="field"><label for="lr-cap">Loan cap (KES)</label><input id="lr-cap" inputmode="numeric" value="${s.cap}"></div><div class="field"><label for="lr-mult">Savings multiple</label><input id="lr-mult" inputmode="numeric" value="${s.mult}"></div><div class="field"><label for="lr-ttl">Join code lasts (minutes)</label><input id="lr-ttl" inputmode="numeric" value="${s.ttl || 15}"></div><button class="btn small" type="submit" style="margin-top:1rem">Save rules</button></form></div>`;
  }

  /* ---------- owners ---------- */
  let oBan = null;
  EXT.pages['pf-owners'] = () => {
    $('#p-pf-owners').innerHTML = `${oBan ? `<div class="banner ${oBan.k}" role="status">${oBan.t}</div>` : ''}<div class="grid"><div class="glass s8 rise"><div class="card-head"><div><div class="eyebrow">${DB.owners.length} owners</div><h3 class="serif">Platform owners</h3></div></div><div class="list">${DB.owners.map((o, i) => `<div class="row" style="grid-template-columns:auto minmax(0,1fr) auto"><div class="ico" style="background:var(--teal)">${o.name.split(' ').pop()[0].toUpperCase()}</div><div><div class="title">${o.name}${o.me ? ' (you)' : ''}</div><div class="sub">${o.email}</div></div><button class="btn warn small" data-own="${i}" ${o.me ? 'disabled title="Nobody revokes themselves"' : ''}>Revoke</button></div>`).join('')}</div><p class="note">At least two owners always remain, and nobody revokes themselves.</p></div>
      <form class="glass s4 rise" id="own-new" style="--s:80ms"><div class="eyebrow">admin.manage</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0">Add an owner</h3><div class="field"><label for="ow-email">Email</label><input id="ow-email" type="email" placeholder="name@example.com"></div><button class="btn small" type="submit" style="margin-top:1rem">Add owner</button></form></div>`;
  };

  /* ---------- access to SACCOs: ask, wait for consent, read what was approved ---------- */
  let aSel = null, aBan = null;
  EXT.pages['pf-access'] = () => {
    const host = $('#p-pf-access');
    if (aSel) {
      const a = DB.access.find(x => x.id === aSel);
      host.innerHTML = `${back('Back to access', 'data-pa-back')}<div class="glass rise"><div class="detail-head"><div><div class="eyebrow">Read only · ${a.sacco}</div><h3 class="serif" style="font-size:1.6rem">Audit entries you may read</h3></div>${chip('Until ' + a.expires, 'warn')}</div><div class="table-wrap"><table><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Target</th></tr></thead><tbody>${auditAll.slice(0, 5).map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${chip(r[2])}</td><td>${r[3]}</td></tr>`).join('')}</tbody></table></div><p class="note">Only the areas the admin approved are shown. Balances and loans stay hidden.</p></div>`;
      return;
    }
    host.innerHTML = `${aBan ? `<div class="banner ${aBan.k}" role="status">${aBan.t}</div>` : ''}<div class="grid"><form class="glass s5 rise" id="pa-new"><div class="eyebrow">Ask for access</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0">Read a SACCO's records</h3><div class="field"><label for="pa-sacco">SACCO</label><select id="pa-sacco">${DB.saccos.map(s => `<option>${s.name}</option>`).join('')}</select></div><div class="field"><span class="lb-s">What you need to read</span><div class="checks">${['audit', 'members', 'savings', 'loans'].map(x => `<label><input type="checkbox" name="scope" value="${x}" ${x === 'audit' ? 'checked' : ''}>${x}</label>`).join('')}</div></div><div class="field"><label for="pa-why">Why</label><input id="pa-why" placeholder="One sentence the admin can read"></div><button class="btn small" type="submit" style="margin-top:1rem">Send request</button></form>
      <div class="glass s7 rise" style="--s:80ms"><div class="card-head"><div><div class="eyebrow">${DB.access.length} requests</div><h3 class="serif">Your requests</h3></div></div><div class="list">${DB.access.map(a => `<div class="row" style="grid-template-columns:minmax(0,1fr) auto"><div><div class="title">${a.sacco} ${st(a.status[0].toUpperCase() + a.status.slice(1))}</div><div class="sub">${a.scopes.join(', ')} · ${a.reason}${a.expires ? ' · until ' + a.expires : ''}</div></div><div class="actions" style="margin:0">${a.status === 'approved' && a.scopes.includes('audit') ? `<button class="btn small" data-pa="${a.id}">Read audit</button>` : ''}</div></div>`).join('')}</div></div></div>`;
  };

  /* ---------- platform audit ---------- */
  let pq = '';
  EXT.pages['pf-audit'] = () => {
    const rows = DB.events.filter(r => r.join(' ').toLowerCase().includes(pq.toLowerCase()));
    $('#p-pf-audit').innerHTML = `<div class="glass rise"><div class="card-head"><div><div class="eyebrow">Read only</div><h3 class="serif">Platform audit</h3></div><span class="chip lock">No edit or delete</span></div><div class="actions" style="margin:0 0 1rem"><input id="pf-q" class="chip" placeholder="Search the log" value="${pq}" aria-label="Search the log" style="min-height:2.3rem;min-width:14rem"></div><div class="table-wrap"><table><thead><tr><th>When</th><th>Who</th><th>Action</th><th>Target</th></tr></thead><tbody>${rows.map(r => `<tr ${evAttrs(r)}><td>${r[0]}</td><td>${r[1]}</td><td>${chip(r[2])}</td><td>${r[3]}</td></tr>`).join('') || '<tr><td colspan="4">No entries match your search.</td></tr>'}</tbody></table></div></div>`;
  };

  /* ---------- events for the platform pages ---------- */
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-sac],[data-sac-back],[data-sac-status],[data-sac-admin],[data-own],[data-pa],[data-pa-back],[data-pa-rev],[data-join-back]'); if (!t) return; const d = t.dataset;
    if (d.sac) { sSel = +d.sac; sBan = null; confirmSus = false; EXT.pages['pf-saccos'](); scrollTo(0, 0); }
    else if ('sacBack' in d) { sSel = null; sBan = null; confirmSus = false; EXT.pages['pf-saccos'](); }
    else if ('sacStatus' in d) { const s = DB.saccos.find(x => x.id === sSel); if (!confirmSus) { confirmSus = true; sBan = { k: 'info', t: s.status === 'Active' ? 'Suspending locks this SACCO for all its members. Click again to confirm.' : 'Reopening gives the members their screens back. Click again to confirm.' }; } else { s.status = s.status === 'Active' ? 'Suspended' : 'Active'; confirmSus = false; log(s.status === 'Suspended' ? 'sacco.deactivate' : 'sacco.activate', s.name); sBan = { k: 'ok', t: `${s.name} is now ${s.status.toLowerCase()}.` }; } EXT.pages['pf-saccos'](); }
    else if ('sacAdmin' in d) toast('Enter the new admin\'s email in the next step (not part of this prototype).');
    else if (d.own !== undefined) { if (DB.owners.length <= 2) { oBan = { k: 'err', t: 'At least two platform owners must remain, so this owner cannot be revoked.' }; } else { const o = DB.owners.splice(+d.own, 1)[0]; log('owner.revoke', o.email); oBan = { k: 'ok', t: `${o.name} is no longer a platform owner.` }; } EXT.pages['pf-owners'](); }
    else if (d.pa) { aSel = +d.pa; EXT.pages['pf-access'](); scrollTo(0, 0); }
    else if ('paBack' in d) { aSel = null; EXT.pages['pf-access'](); }
    else if (d.paRev) { const a = DB.access.find(x => x.id === +d.paRev); a.status = 'revoked'; a.expires = ''; log('support.revoke', a.sacco); aBan = { k: 'ok', t: 'Access revoked. It stopped at once.' }; EXT.pages['pf-access'](); }
    else if ('joinBack' in d) { $('#join-2').hidden = true; $('#join-1').hidden = false; }
  });
  document.addEventListener('input', e => { if (e.target.id === 'pf-q') { pq = e.target.value; EXT.pages['pf-audit'](); const q = $('#pf-q'); q.focus(); q.setSelectionRange(q.value.length, q.value.length); } });
  document.addEventListener('submit', e => {
    const f = e.target.id;
    if (f === 'sac-new') { e.preventDefault(); const n = $('#sn-name').value.trim(), a = $('#sn-admin').value.trim(); if (!n || !a) { sBan = { k: 'err', t: 'Give the SACCO a name and its first admin\'s email.' }; } else { DB.saccos.push({ id: DB.saccos.length + 1, name: n, status: 'Active', members: 0, admin: a, approvals: 1, cap: 50000, mult: 3, created: 'Today' }); log('sacco.create', n); sBan = { k: 'ok', t: `${n} was created. ${a} will get a join code.` }; } EXT.pages['pf-saccos'](); }
    if (f === 'sac-rules') { e.preventDefault(); const s = DB.saccos.find(x => x.id === sSel); s.approvals = +$('#lr-ap').value; s.cap = +$('#lr-cap').value.replace(/\D/g, '') || s.cap; s.mult = +$('#lr-mult').value.replace(/\D/g, '') || s.mult; s.ttl = +$('#lr-ttl').value.replace(/\D/g, '') || s.ttl || 15; log('settings.update', s.name + ' loan rules'); sBan = { k: 'ok', t: 'Loan rules saved for this SACCO.' }; EXT.pages['pf-saccos'](); }
    if (f === 'own-new') { e.preventDefault(); const v = $('#ow-email').value.trim(); if (!/^\S+@\S+\.\S+$/.test(v)) { oBan = { k: 'err', t: 'Enter a valid email address.' }; } else { DB.owners.push({ name: 'New platform owner', email: v }); log('owner.add', v); oBan = { k: 'ok', t: `${v} is now a platform owner.` }; } EXT.pages['pf-owners'](); }
    if (f === 'pa-new') { e.preventDefault(); const sc = $$('input[name="scope"]:checked').map(x => x.value), why = $('#pa-why').value.trim(); if (!sc.length || !why) { aBan = { k: 'err', t: 'Choose what you need to read and say why.' }; } else { DB.access.unshift({ id: Date.now(), sacco: $('#pa-sacco').value, scopes: sc, reason: why, status: 'pending', expires: '' }); log('support.request', $('#pa-sacco').value); aBan = { k: 'ok', t: 'Request sent. The SACCO admin must approve it before you can read anything.' }; } EXT.pages['pf-access'](); }
  }, true);

  /* ---------- public account pages ---------- */
  const rules = pw => `<div class="rules"><span class="${pw.length >= 8 ? 'ok' : ''}">8 to 128 characters</span><span class="${pw && !pw.includes('@') ? 'ok' : ''}">Cannot contain your email address</span></div>`;
  let regStep = 0, regMail = '';
  function paintReg() {
    const c = $('#reg-card');
    c.innerHTML = regStep === 0 ? `<form id="reg-form"><div class="eyebrow">Create account</div><h2 class="serif">Your details</h2><div id="reg-msg" role="alert" hidden style="margin-top:1rem"></div><div class="field"><label for="rg-mail">Email</label><input id="rg-mail" type="email" placeholder="you@example.com" autocomplete="email"></div><div class="field"><label for="rg-pw">Password</label><input id="rg-pw" type="password" autocomplete="new-password"></div>${rules('')}<button class="btn" type="submit">Create account</button><div class="auth-links"><a class="link-btn" href="#login">I already have an account</a></div></form>`
      : `<div class="eyebrow">Almost there</div><h2 class="serif">Check your email</h2><p class="muted" style="margin:.6rem 0 1rem">We sent a link to <b>${regMail}</b>. Registering does not sign you in.</p><div class="actions" style="margin:0"><button class="btn small" id="reg-open">Open the verification link</button><button class="back" type="button" id="reg-back">← Use a different email</button></div><p class="note">Prototype: the button stands in for the link in your email.</p>`;
  }
  let fStep = 0, fMail = '';
  function paintForgot() {
    const c = $('#forgot-card');
    c.innerHTML = fStep === 0 ? `<form id="fg-form"><div class="eyebrow">Forgot password</div><h2 class="serif">Send me a link</h2><div class="field"><label for="fg-mail">Email</label><input id="fg-mail" type="email" placeholder="you@example.com" autocomplete="email"></div><button class="btn" type="submit">Send reset link</button></form>`
      : fStep === 1 ? `<button class="back" type="button" id="fg-back">← Back</button><div class="eyebrow" style="margin-top:.8rem">Sent</div><h2 class="serif">Check your email</h2><p class="muted" style="margin:.6rem 0 1rem">If <b>${fMail}</b> is registered, a reset link is on its way. This message is the same either way.</p><button class="btn small" id="fg-open">Open the reset link</button><p class="note">Prototype: the button stands in for the link.</p>`
      : fStep === 2 ? `<form id="fg-reset"><button class="back" type="button" id="fg-back2">← Back</button><div class="eyebrow" style="margin-top:.8rem">New password</div><h2 class="serif">Choose a new one</h2><div id="fg-msg" role="alert" hidden style="margin-top:1rem"></div><div class="field"><label for="fg-pw">New password</label><input id="fg-pw" type="password" autocomplete="new-password"></div>${rules('')}<button class="btn" type="submit">Save password</button></form>`
      : `<div class="eyebrow">Done</div><h2 class="serif">Password changed</h2><p class="muted" style="margin:.6rem 0 1rem">Every other device was signed out.</p><a class="btn" href="#login">Sign in</a>`;
  }
  function paintVer() {
    const c = $('#ver-card'); c.innerHTML = '<div class="eyebrow">Verifying</div><h2 class="serif">One moment</h2>';
    setTimeout(() => { c.innerHTML = '<div class="eyebrow">Verified</div><h2 class="serif">Your email is confirmed</h2><p class="muted" style="margin:.6rem 0 1rem">You can sign in now. To join a SACCO, ask its admin for a join code.</p><div class="actions" style="margin:0"><a class="btn" href="#login">Sign in</a><a class="btn ghost" href="#join">Join with a code</a></div>'; }, 900);
  }
  EXT.after.register = [paintReg]; EXT.after.verify = [paintVer]; EXT.after.forgot = [paintForgot];
  const origShow = N.show;
  /* public routes have no app page, so paint them when they appear */
  new MutationObserver(() => {
    if ($('#register').classList.contains('on') && !$('#reg-card').firstChild) paintReg();
    if ($('#forgot').classList.contains('on') && !$('#forgot-card').firstChild) paintForgot();
    if ($('#verify').classList.contains('on') && !$('#ver-card').firstChild) paintVer();
  }).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['class'] });
  document.addEventListener('submit', e => {
    if (e.target.id === 'reg-form') { e.preventDefault(); const m = $('#rg-mail').value.trim(), p = $('#rg-pw').value, box = $('#reg-msg'); if (!/^\S+@\S+\.\S+$/.test(m)) { msg(box, 'err', 'Enter a valid email address.'); N.fieldError($('#rg-mail'), 'Use an address like name@example.com.'); return; } if (p.length < 8 || p.length > 128 || p.toLowerCase().includes(m.split('@')[0].toLowerCase())) { msg(box, 'err', 'Your password needs 8 to 128 characters and cannot contain your email address.'); N.fieldError($('#rg-pw'), 'Use 8 to 128 characters without your email address.'); return; } regMail = m; regStep = 1; paintReg(); }
    if (e.target.id === 'fg-form') { e.preventDefault(); fMail = $('#fg-mail').value.trim() || 'your address'; fStep = 1; paintForgot(); }
    if (e.target.id === 'fg-reset') { e.preventDefault(); const p = $('#fg-pw').value; if (p.length < 8) { msg($('#fg-msg'), 'err', 'Your new password needs at least 8 characters.'); return; } fStep = 3; paintForgot(); }
  }, true);
  document.addEventListener('click', e => {
    const id = e.target.id;
    if (id === 'reg-open') { regStep = 0; $('#reg-card').innerHTML = ''; location.hash = 'verify'; }
    if (id === 'reg-back') { regStep = 0; paintReg(); }
    if (id === 'fg-back') { fStep = 0; paintForgot(); }
    if (id === 'fg-open') { fStep = 2; paintForgot(); }
    if (id === 'fg-back2') { fStep = 1; paintForgot(); }
  });
})();
