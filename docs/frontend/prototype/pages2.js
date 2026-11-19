/* pages2.js: accounts, members, loan details, SACCO settings, access requests, account settings */
(() => {
  const N = window.NX;
  const { $, $$, S, ROLES, can, kes, toast, EXT, APP, loans, mem, accts, svTx, stepIdx, loanCard, DB, store } = N;
  const chip = (t, k) => `<span class="chip ${k || ''}">${t}</span>`;
  const st = s => chip(s, s === 'Active' || s === 'Posted' || s === 'Approved' || s === 'Paid' ? 'up' : s === 'Reversed' || s === 'Suspended' || s === 'Denied' || s === 'Inactive' ? 'bad' : 'warn');
  const back = (label, attr) => `<div class="page-back"><button type="button" class="back" ${attr}>← ${label}</button></div>`;

  /* ---------- accounts, with a ledger page behind each row ---------- */
  let acQ = '', acSel = null, acBanner = null;
  const reversed = new Set(['4 Oct Deposit']);
  /* a dashboard row can ask a page to open a specific record (N.open = 'kind:id') */
  const take = kind => { const o = N.open || ''; if (o.startsWith(kind + ':')) { N.open = ''; return o.slice(kind.length + 1); } return null; };
  EXT.pages.accounts = () => {
    const host = $('#p-accounts');
    const want = take('acct'); if (want) { acSel = want; acBanner = null; }
    if (acSel) return accountDetail(host);
    const rows = accts.filter(r => r.join(' ').toLowerCase().includes(acQ.toLowerCase()));
    host.innerHTML = `<div class="glass rise"><div class="card-head"><div><div class="eyebrow">${accts.length} accounts · total ${kes(accts.reduce((s, r) => s + r[2], 0))}</div><h3 class="serif">All member accounts</h3></div><span class="chip lock">savings.view_all</span></div>
      <div class="actions" style="margin:0 0 1rem"><input id="ac-q" class="chip" placeholder="Search by name or account" value="${acQ}" aria-label="Search accounts" style="min-height:2.4rem;min-width:15rem"></div>
      <div class="table-wrap"><table><thead><tr><th>Member</th><th>Account</th><th class="r">Balance</th><th>Last activity</th><th>Status</th><th></th></tr></thead><tbody>${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="r">${kes(r[2])}</td><td>${r[3]}</td><td>${st(r[4])}</td><td><button class="btn ghost small" data-ac="${r[1]}">View ledger</button></td></tr>`).join('') || '<tr><td colspan="6">No accounts match your search.</td></tr>'}</tbody></table></div></div>`;
  };
  function accountDetail(host) {
    const a = accts.find(r => r[1] === acSel), own = a[0] === 'Jordan Mwangi';
    host.innerHTML = `${back('Back to accounts', 'data-ac-back')}${acBanner ? `<div class="banner ${acBanner.k}" role="status">${acBanner.t}</div>` : ''}
      <div class="glass rise"><div class="detail-head"><div><div class="eyebrow">${a[1]}</div><h3 class="serif" style="font-size:1.8rem">${a[0]}</h3></div><div class="actions" style="margin:0">${can('savings.post') && !own ? '<a class="btn small" href="#money">Post money</a>' : ''}${own && can('savings.post') ? '<span class="chip lock">You cannot post to your own account</span>' : ''}</div></div>
        <div class="kv"><div><span>Balance</span><b>${kes(a[2])}</b></div><div><span>Last activity</span><b>${a[3]}</b></div><div><span>Status</span><b>${a[4]}</b></div><div><span>Opened</span><b>Mar 2024</b></div></div></div>
      <div class="glass rise" style="margin-top:var(--gap)"><div class="card-head"><div><div class="eyebrow">Ledger</div><h3 class="serif">Entries, newest first</h3></div></div><div class="list">${svTx.map((r, i) => { const key = `${r.d} ${r.t}`, rev = r.st === 'Reversed' || reversed.has(key); return `<div class="row"><div class="ico" style="background:${r.t === 'Withdrawal' || r.t === 'Loan repayment' ? 'var(--terra)' : 'var(--teal)'}">${r.t === 'Withdrawal' || r.t === 'Loan repayment' ? '−' : '+'}</div><div><div class="title">${r.t}</div><div class="sub">${r.d} · ${rev ? 'Reversed' : 'Posted'}</div></div><div class="amt">${kes(r.a)} ${can('savings.reverse') && !own && r.t !== 'Interest' ? `<button class="btn ghost small" data-ac-rev="${i}">${rev ? 'Reverse again' : 'Reverse'}</button>` : ''}</div></div>`; }).join('')}</div></div>`;
  }

  /* ---------- members, with a profile page behind each row ---------- */
  let mSel = null, mBanner = null;
  const roleOpts = sel => ['member', 'secretary', 'finance', 'loans'].map(r => `<option value="${r}" ${r === sel ? 'selected' : ''}>${ROLES[r].label}</option>`).join('');
  EXT.pages.members = () => {
    const host = $('#p-members'), manage = can('member.manage');
    const wm = take('member'); if (wm) { const i = mem.findIndex(m => m[0] === wm); if (i >= 0) { mSel = i; mBanner = null; } }
    if (mSel !== null) return memberDetail(host, manage);
    host.innerHTML = `<div class="grid">
      <div class="glass s12 rise"><div class="card-head"><div><div class="eyebrow">${mem.length} members</div><h3 class="serif">Members and roles</h3></div>${manage ? '<a class="btn small" href="#add-member">Add a member</a>' : ''}</div><div class="table-wrap"><table><thead><tr><th>Name</th><th>Phone</th><th>Status</th><th>Role</th><th></th></tr></thead><tbody>${mem.map((m, i) => `<tr><td>${m[0]}</td><td>${m[1]}</td><td>${st(m[2])}</td><td>${ROLES[m[3]].label}</td><td><button class="btn ghost small" data-m="${i}">Open</button></td></tr>`).join('')}</tbody></table></div></div>
    </div>`;
    if (N.paintCode) N.paintCode();
  };
  function memberDetail(host, manage) {
    const m = mem[mSel], acct = accts.find(a => a[0] === m[0]);
    host.innerHTML = `${back('Back to members', 'data-m-back')}${mBanner ? `<div class="banner ${mBanner.k}" role="status">${mBanner.t}</div>` : ''}
      <div class="grid"><div class="glass s8 rise"><div class="detail-head"><div><div class="eyebrow">Member profile</div><h3 class="serif" style="font-size:1.8rem">${m[0]}</h3></div>${st(m[2])}</div>
        <div class="kv"><div><span>Phone</span><b>${m[1]}</b></div><div><span>Role</span><b>${ROLES[m[3]].label}</b></div><div><span>Account</span><b>${acct ? acct[1] : 'Not opened'}</b></div><div><span>Balance</span><b>${acct ? kes(acct[2]) : 'KES 0'}</b></div><div><span>Joined</span><b>${m[2] === 'Invited' ? 'Not yet' : 'Mar 2024'}</b></div></div>
        ${manage ? `<div class="field"><label for="m-role">Change role</label><select id="m-role" data-m-role>${roleOpts(m[3])}</select></div>` : ''}</div>
        <div class="glass s4 rise" style="--s:80ms"><div class="eyebrow">Membership</div><div class="actions" style="flex-direction:column;align-items:stretch">${manage ? (m[2] === 'Active' ? '<button class="btn warn small" data-m-status="Inactive">Deactivate member</button>' : m[2] === 'Inactive' ? '<button class="btn small" data-m-status="Invited">Re-add with a new code</button>' : '<button class="btn small" data-m-status="Invited">Send a new code</button>') : '<span class="chip lock">Only the SACCO admin changes membership</span>'}</div>
        <div class="rules"><span>An invited member becomes active only by joining with a code and setting a PIN.</span><span>An active member can be deactivated. A deactivated member can be added again.</span><span>Nobody changes their own role.</span></div></div></div>`;
  }

  /* ---------- loans: a details page behind each card, and repayments for the finance officer ---------- */
  EXT.after.loans = [() => {
    const host = $('#p-loans'); if (!host || $('#loan-detail-host')) return;
    $$('article.glass', host).forEach(a => {
      const m = /Loan #(\d+)/.exec(a.textContent); if (!m || a.querySelector('[data-loan-detail]')) return;
      a.insertAdjacentHTML('beforeend', `<div class="actions"><button class="btn ghost small" data-loan-detail="${m[1]}">Details</button></div>`);
    });
    if (can('loan.repay') && !can('loan.request') && !$('#repay-form')) host.insertAdjacentHTML('beforeend', `<form class="glass rise" id="repay-form" style="margin-top:var(--gap)"><div class="eyebrow">Record a repayment</div><div class="actions" style="align-items:flex-end;margin-top:.6rem"><div class="field" style="margin:0;flex:1;min-width:10rem"><label for="rp-loan">Loan</label><select id="rp-loan"><option>Loan #2019 · Member 1</option><option>Loan #2031 · Member 5</option></select></div><div class="field" style="margin:0;flex:1;min-width:8rem"><label for="rp-amt">Amount (KES)</label><input id="rp-amt" inputmode="numeric" placeholder="8,500"></div><button class="btn small" type="submit">Record</button></div></form>`);
  }];
  /* the Details buttons come back after any approve, reject or disburse re-draws the list */
  let lt = 0;
  new MutationObserver(() => { cancelAnimationFrame(lt); lt = requestAnimationFrame(() => { const h = $('#p-loans'); if (h && !h.hidden) EXT.after.loans[0](); const au = $('#p-audit'); if (au && !au.hidden && EXT.after.audit) EXT.after.audit[0](); }); }).observe($('#stage'), { subtree: true, childList: true });
  EXT.after.account = [() => N.paintAvatars()];
  EXT.after.loans.push(() => { const id = take('loan'); if (id) { loanDetail(+id); scrollTo(0, 0); } });
  /* audit lines lead to what they describe */
  EXT.after.audit = [() => {
    $$('#p-audit tbody tr').forEach(r => {
      const t = r.textContent; let page = '', open = '';
      const loan = /Loan #(\d+)/.exec(t), mm = /Member (\d+)/.exec(t);
      if (loan && N.reach('loans')) { page = 'loans'; open = 'loan:' + loan[1]; }
      else if (/member\.add|role\.set/.test(t) && mm && N.reach('members')) { page = 'members'; open = 'member:Member ' + mm[1]; }
      else if (mm && N.reach('accounts')) { const a = accts.find(x => x[0] === 'Member ' + mm[1]); page = 'accounts'; open = a ? 'acct:' + a[1] : ''; }
      if (page && !r.dataset.go) { r.dataset.go = page; r.dataset.open = open; r.tabIndex = 0; r.setAttribute('role', 'link'); }
    });
  }];
  function loanDetail(id) {
    const l = loans.find(x => x.id === id), host = $('#p-loans');
    const idx = stepIdx(l);
    const steps = l.steps.map((s, i) => `<div class="${s ? '' : 'wait'}"><b>Step ${i + 1}: ${s ? 'Approved' : l.status === 'rejected' ? 'Stopped' : 'Waiting'}</b><small>${s ? (s.by === 'me' ? 'Decided by you' : 'Decided by another loans officer') : 'A loans officer who has not decided an earlier step'}</small></div>`).join('');
    host.innerHTML = `${back('Back to loans', 'data-loan-back')}<div id="loan-detail-host" class="stack">${loanCard(l)}
      <div class="grid"><div class="glass s6 rise"><div class="eyebrow">Borrower</div><div class="kv" style="margin-top:.6rem"><div><span>Member</span><b>${l.who}</b></div><div><span>Requested</span><b>${l.date}</b></div><div><span>Savings</span><b>${kes(l.who === 'Member 5' ? 41800 : 92500)}</b></div><div><span>Within savings multiple</span><b>${l.amount <= 150000 ? 'Yes' : 'No'}</b></div></div></div>
      <div class="glass s6 rise" style="--s:80ms"><div class="eyebrow">How this loan moved</div><div class="timeline" style="margin-top:.8rem"><div><b>Requested</b><small>${l.date} by ${l.who}</small></div>${steps}<div class="${l.status === 'disbursed' ? '' : 'wait'}"><b>Disbursed: ${l.status === 'disbursed' ? 'Yes' : 'Not yet'}</b><small>A finance officer who approved none of the steps</small></div></div></div></div></div>`;
    N.tilts();
  }

  /* ---------- SACCO settings and platform access requests (SACCO admin) ---------- */
  EXT.pages.settings = () => {
    const s = DB.saccos[0];
    $('#p-settings').innerHTML = `<div class="grid"><form class="glass s6 rise" id="set-form"><div class="eyebrow">sacco.update</div><h3 class="serif" style="font-size:1.4rem;margin-top:.3rem">Name your SACCO</h3><div class="field"><label for="set-name">SACCO name</label><input id="set-name" value="${s.name}"></div><button class="btn small" type="submit" style="margin-top:1rem">Save name</button></form>
      <div class="glass s6 rise" style="--s:80ms"><div class="eyebrow">Loan rules</div><h3 class="serif" style="font-size:1.4rem;margin-top:.3rem">Set by the platform owner</h3><div class="kv" style="margin-top:.8rem"><div><span>Approvals above the cap</span><b>${s.approvals}</b></div><div><span>Loan cap</span><b>${kes(s.cap)}</b></div><div><span>Savings multiple</span><b>${s.mult}x</b></div><div><span>Join code lasts</span><b>${s.ttl || 15} min</b></div></div><p class="note">You see these rules but cannot change them. Ask a platform owner.</p></div></div>`;
  };
  let acc = null;
  EXT.pages.access = () => {
    const list = DB.access.filter(a => a.sacco === $('#sacco-name').textContent);
    $('#p-access').innerHTML = `${acc ? `<div class="banner ${acc.k}" role="status">${acc.t}</div>` : ''}<div class="glass rise"><div class="card-head"><div><div class="eyebrow">support.approve</div><h3 class="serif">Platform access to your records</h3></div></div><p class="muted" style="margin-bottom:1rem">A platform owner can read your SACCO's records only after you approve. Each approval is limited to the areas they asked for and ends on its own.</p><div class="list">${list.map(a => `<div class="row" style="grid-template-columns:minmax(0,1fr) auto"><div><div class="title">${a.scopes.map(x => chip(x)).join(' ')} ${st(a.status[0].toUpperCase() + a.status.slice(1))}</div><div class="sub">${a.reason}${a.expires ? ' · until ' + a.expires : ''}</div></div><div class="actions" style="margin:0">${a.status === 'pending' ? `<button class="btn small" data-acc="approve" data-id="${a.id}">Approve for 1 day</button><button class="btn warn small" data-acc="deny" data-id="${a.id}">Deny</button>` : a.status === 'approved' ? `<button class="btn warn small" data-acc="revoke" data-id="${a.id}">Revoke now</button>` : ''}</div></div>`).join('') || '<div class="banner">No requests for this SACCO.</div>'}</div></div>`;
  };

  /* ---------- account settings (everyone) ---------- */
  let pwBanner = null;
  EXT.pages.account = () => {
    const to = S.prev && APP.includes(S.prev) && S.prev !== 'account' ? S.prev : (can('platform') ? 'pf-overview' : 'overview');
    $('#p-account').innerHTML = `${back('Back', 'data-acct-back="' + to + '"')}${pwBanner ? `<div class="banner ${pwBanner.k}" role="status">${pwBanner.t}</div>` : ''}<div class="grid">
      <div class="glass s6 rise"><div class="eyebrow">Profile</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0 1rem">Photo and email</h3><div class="actions" style="margin:0 0 1rem;align-items:center"><button type="button" class="avatar" data-open-photo aria-label="Change profile photo" style="width:4.2rem;height:4.2rem">JM</button><button class="btn ghost small" type="button" data-open-photo>Change photo</button></div><div class="kv"><div><span>Email</span><b>jordan@example.com</b></div><div><span>Status</span><b>Verified</b></div></div><div class="actions"><button class="btn ghost small" type="button" data-resend>Resend verification email</button></div></div>
      <form class="glass s6 rise" id="pw-form" style="--s:80ms"><div class="eyebrow">Password</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0">Change password</h3><div class="field"><label for="pw-cur">Current password</label><input id="pw-cur" type="password" autocomplete="current-password"></div><div class="field"><label for="pw-new">New password</label><input id="pw-new" type="password" autocomplete="new-password"></div><div class="rules"><span>8 to 128 characters</span><span>Cannot contain your email address</span></div><button class="btn small" type="submit" style="margin-top:1rem">Change password</button></form>
      <div class="glass s12 rise" style="--s:140ms"><div class="eyebrow">Sessions</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0 .4rem">Where you are signed in</h3><p class="muted" style="margin-bottom:1rem">You stay signed in on this device until you log out. Changing your password signs out every other device.</p><div class="actions" style="margin:0"><button class="btn ghost small" type="button" data-logout>Log out of this device</button><button class="btn warn small" type="button" data-logout-all>Log out everywhere</button></div></div></div>`;
  };

  /* ---------- events ---------- */
  const rerender = () => N.show(S.route);
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-ac],[data-ac-back],[data-ac-rev],[data-m],[data-m-back],[data-m-status],[data-loan-detail],[data-loan-back],[data-acc],[data-acct-back],[data-open-photo],[data-resend],[data-logout],[data-logout-all]');
    if (!t) return;
    const d = t.dataset;
    if (d.ac) { acSel = d.ac; acBanner = null; EXT.pages.accounts(); scrollTo(0, 0); }
    else if ('acBack' in d) { acSel = null; EXT.pages.accounts(); }
    else if (d.acRev !== undefined) { const r = svTx[+d.acRev], key = `${r.d} ${r.t}`; if (r.st === 'Reversed' || reversed.has(key)) acBanner = { k: 'err', t: 'This entry was already reversed, so nothing changed.' }; else { reversed.add(key); acBanner = { k: 'ok', t: 'Entry reversed. The original stays in the ledger.' }; } EXT.pages.accounts(); }
    else if (d.m !== undefined) { mSel = +d.m; mBanner = null; EXT.pages.members(); scrollTo(0, 0); }
    else if ('mBack' in d) { mSel = null; EXT.pages.members(); }
    else if (d.mStatus) { mem[mSel][2] = d.mStatus; mBanner = { k: 'ok', t: d.mStatus === 'Inactive' ? `${mem[mSel][0]} was deactivated.` : `A new join code was created for ${mem[mSel][0]}. It lasts 15 minutes.` }; EXT.pages.members(); }
    else if (d.loanDetail) { loanDetail(+d.loanDetail); scrollTo(0, 0); }
    else if ('loanBack' in d) { N.show('loans'); }
    else if (d.acc) { const a = DB.access.find(x => x.id === +d.id); a.status = d.acc === 'approve' ? 'approved' : d.acc === 'deny' ? 'denied' : 'revoked'; a.expires = d.acc === 'approve' ? 'Tomorrow, 14:00' : ''; acc = { k: 'ok', t: d.acc === 'approve' ? 'Access approved for one day. It ends on its own.' : d.acc === 'deny' ? 'Request denied. The platform owner is told.' : 'Access revoked. It stopped at once.' }; EXT.pages.access(); }
    else if (d.acctBack) { location.hash = d.acctBack; }
    else if ('openPhoto' in d) N.openPhoto();
    else if ('resend' in d) toast('If that address is registered, a new link is on its way.');
    else if ('logout' in d) $('#logout').click();
    else if ('logoutAll' in d) { toast('Signed out on every device.'); $('#logout').click(); }
  });
  document.addEventListener('change', e => { if (e.target.matches('[data-m-role]')) { mem[mSel][3] = e.target.value; mBanner = { k: 'ok', t: 'Role updated.' }; EXT.pages.members(); } });
  document.addEventListener('input', e => { if (e.target.id === 'ac-q') { acQ = e.target.value; EXT.pages.accounts(); const q = $('#ac-q'); q.focus(); q.setSelectionRange(q.value.length, q.value.length); } });
  document.addEventListener('submit', e => {
    const f = e.target.id;
    if (f === 'set-form') { e.preventDefault(); const v = $('#set-name').value.trim(); if (!v) { toast('A SACCO name cannot be empty.'); return; } DB.saccos[0].name = v; $('#sacco-name').textContent = v; $$('[data-sacco="Alpha SACCO"] span:first-child').forEach(s => { s.textContent = v; }); toast('SACCO renamed.'); }
    if (f === 'repay-form') { e.preventDefault(); const a = +$('#rp-amt').value.replace(/[^\d]/g, ''); if (!a) { toast('Enter an amount greater than zero.'); return; } toast(`Repayment of ${kes(a)} recorded.`); $('#rp-amt').value = ''; }
    if (f === 'pw-form') {
      e.preventDefault(); const n = $('#pw-new').value, c = $('#pw-cur').value;
      pwBanner = !c ? { k: 'err', t: 'Enter your current password.' } : n.length < 8 || n.length > 128 ? { k: 'err', t: 'Your new password needs 8 to 128 characters.' } : n.toLowerCase().includes('jordan@example.com') ? { k: 'err', t: 'Your new password cannot contain your email address.' } : { k: 'ok', t: 'Password changed. Every other device was signed out.' };
      EXT.pages.account();
    }
  }, true);
})();
