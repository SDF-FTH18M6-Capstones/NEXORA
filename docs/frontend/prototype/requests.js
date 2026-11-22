/* requests.js: member Deposit and Withdraw pages (M-Pesa or Bank) and the officer Requests queue.
   Nothing here posts money by itself. A member sends a request, an officer confirms it, and only then does the ledger change. */
(() => {
  const N = window.NX;
  const { $, $$, S, can, kes, toast, EXT, accts, acctData, ledger, uuid } = N;
  const ME = 'Jordan Mwangi';

  /* sample requests; the real ones come from GET /savings/requests/me and GET /savings/saccos/<id>/requests */
  const RQ = N.RQ = [
    { id: 1, who: ME, kind: 'deposit', method: 'mpesa', amt: 5000, detail: '0712 345 678', st: 'Confirmed', when: '12 Nov 09:20' },
    { id: 2, who: ME, kind: 'deposit', method: 'bank', amt: 20000, detail: 'Equity Bank, ref TRF-88213', st: 'Pending', when: '17 Nov 16:05' },
    { id: 3, who: ME, kind: 'withdrawal', method: 'mpesa', amt: 3000, detail: '0712 345 678', st: 'Rejected', why: 'The phone number does not match your member record.', when: '10 Nov 11:40' },
    { id: 4, who: 'Member 3', kind: 'deposit', method: 'mpesa', amt: 12000, detail: '0722 111 540', st: 'Pending', when: '18 Nov 08:15' },
    { id: 5, who: 'Member 5', kind: 'withdrawal', method: 'bank', amt: 60000, detail: 'KCB, account 1234567890', st: 'Pending', when: '18 Nov 10:02' },
    { id: 6, who: 'Member 7', kind: 'withdrawal', method: 'mpesa', amt: 8000, detail: '0745 222 261', st: 'Pending', when: '18 Nov 11:30' },
    { id: 7, who: ME, kind: 'withdrawal', method: 'bank', amt: 15000, detail: 'Equity Bank, account 0123456789', st: 'Pending', when: '18 Nov 12:10' }
  ];
  let nextId = 8;

  /* the pay-in details a member sees. Sample values: real ones come from the SACCO. */
  const PAYIN = { paybill: '400200', account: 'A-0011', bank: 'Equity Bank', bankAcct: '0123456789', bankName: 'Alpha SACCO savings' };

  const chip = s => `<span class="chip ${s === 'Confirmed' ? 'up' : s === 'Rejected' ? 'bad' : 'warn'}">${s}</span>`;
  const METHOD = { mpesa: 'M-Pesa', bank: 'Bank' };
  const PHONE = /^(?:\+254|254|0)([17]\d{8})$/;
  const cleanPhone = v => v.replace(/[\s-]/g, '');
  const prettyPhone = v => { const m = PHONE.exec(cleanPhone(v)); return m ? '0' + m[1].slice(0, 3) + ' ' + m[1].slice(3, 6) + ' ' + m[1].slice(6) : v; };
  const money = v => +String(v).replace(/[^\d]/g, '');
  const balanceOf = who => { const a = accts.find(r => r[0] === who); return a ? a[2] : 0; };

  /* one form state per kind: chosen method, the reference for this submit, the banner after a send */
  const F = { deposit: { method: 'mpesa', ref: uuid(), banner: null }, withdrawal: { method: 'mpesa', ref: uuid(), banner: null } };

  const seg = (kind, m) => `<div class="seg" role="tablist" aria-label="Method" data-seg="${kind}">${['mpesa', 'bank'].map(k => `<button type="button" role="tab" data-rq-method="${k}" data-kind="${kind}" aria-selected="${m === k}">${METHOD[k]}</button>`).join('')}</div>`;

  function history(kind, host) {
    const rows = RQ.filter(r => r.who === ME && r.kind === kind);
    return `<div class="glass s12 rise" style="--s:140ms"><div class="card-head"><div><div class="eyebrow">History</div><h3 class="serif">My ${kind} requests</h3></div><span class="chip">${rows.filter(r => r.st === 'Pending').length} pending</span></div>
      <div class="table-wrap"><table><thead><tr><th>When</th><th>Method</th><th class="r">Amount</th><th>Details</th><th>Status</th></tr></thead><tbody>${rows.map(r => `<tr><td>${r.when}</td><td>${METHOD[r.method]}</td><td class="r">${kes(r.amt)}</td><td>${r.detail}${r.why ? `<br><small class="muted">Reason: ${r.why}</small>` : ''}</td><td>${chip(r.st)}</td></tr>`).join('') || `<tr><td colspan="5">You have not sent a ${kind} request yet.</td></tr>`}</tbody></table></div></div>`;
  }

  function instructions(kind, m) {
    if (kind === 'deposit') {
      return m === 'mpesa'
        ? `<ol class="steps-list"><li>Open M-Pesa on your phone and choose Lipa na M-Pesa, then Pay Bill.</li><li>Business number <b>${PAYIN.paybill}</b>. Account number <b>${PAYIN.account}</b>.</li><li>Enter the amount and your M-Pesa PIN.</li><li>Come back here. Enter the same amount and the phone number you paid from, then send the request.</li></ol>`
        : `<ol class="steps-list"><li>Pay into <b>${PAYIN.bank}</b>, account name <b>${PAYIN.bankName}</b>, account number <b>${PAYIN.bankAcct}</b>.</li><li>Use <b>${PAYIN.account}</b> as the payment reference.</li><li>Come back here. Enter the amount, the bank you paid from and the reference on your receipt, then send the request.</li></ol>`;
    }
    return m === 'mpesa'
      ? `<ol class="steps-list"><li>Enter the amount and the Safaricom number that should receive the money.</li><li>An officer checks your balance and sends the money by M-Pesa.</li><li>The status below changes to Confirmed or Rejected. A rejection always shows a reason.</li></ol>`
      : `<ol class="steps-list"><li>Enter the amount, your bank and your account number.</li><li>An officer checks your balance and sends the money by bank transfer.</li><li>The status below changes to Confirmed or Rejected. A rejection always shows a reason.</li></ol>`;
  }

  function memberPage(kind) {
    const f = F[kind], dep = kind === 'deposit', host = $(dep ? '#p-deposit' : '#p-withdraw');
    const bal = acctData.alpha.bal, banner = f.banner;
    const id = dep ? 'dp' : 'wd';
    host.innerHTML = `${banner ? `<div class="banner ${banner.k}" role="status">${banner.t}</div>` : ''}
      <div class="grid">
        <form class="glass s7 rise" id="${id}-form" novalidate data-kind="${kind}">
          <div class="card-head"><div><div class="eyebrow">New request</div><h3 class="serif" style="font-size:1.5rem">${dep ? 'Deposit to my savings' : 'Withdraw from my savings'}</h3></div><span class="chip lock">savings.request</span></div>
          ${dep ? '' : `<div class="kv" style="margin-bottom:1rem"><div><span>Available balance</span><b>${kes(bal)}</b></div></div>`}
          <div class="field"><span class="ap-label" id="${id}-m-l">${dep ? 'How will you pay?' : 'Where should the money go?'}</span>${seg(kind, f.method)}</div>
          <div class="field"><label for="${id}-amt">Amount (KES)</label><input id="${id}-amt" inputmode="numeric" autocomplete="off" placeholder="5,000"></div>
          <div data-grp="mpesa" ${f.method === 'mpesa' ? '' : 'hidden'}><div class="field"><label for="${id}-phone">${dep ? 'M-Pesa phone number you paid from' : 'M-Pesa phone number to receive the money'}</label><input id="${id}-phone" inputmode="tel" autocomplete="tel" placeholder="0712 345 678"></div></div>
          <div data-grp="bank" ${f.method === 'bank' ? '' : 'hidden'}><div class="field"><label for="${id}-bank">Bank name</label><input id="${id}-bank" autocomplete="off" placeholder="Equity Bank"></div><div class="field"><label for="${id}-acct">${dep ? 'Reference on your bank receipt' : 'Account number'}</label><input id="${id}-acct" inputmode="${dep ? 'text' : 'numeric'}" autocomplete="off" placeholder="${dep ? 'TRF-88213' : '0123456789'}"></div></div>
          <div class="actions"><button class="btn" type="submit">${dep ? 'Send deposit request' : 'Send withdrawal request'}</button></div>
          <p class="note">This sends a request only. Your balance changes after an officer confirms it. Each request has its own reference, so a retry never sends it twice.</p>
        </form>
        <div class="glass s5 rise" style="--s:80ms"><div class="eyebrow">${dep ? 'How to pay' : 'What happens next'}</div><h3 class="serif" style="font-size:1.3rem;margin:.3rem 0 .6rem">${dep ? (f.method === 'mpesa' ? 'Pay by M-Pesa' : 'Pay by bank transfer') : 'An officer sends it'}</h3><div id="${id}-help">${instructions(kind, f.method)}</div>${dep ? '<p class="note">Pay-in details shown here are sample values until the SACCO sets its own.</p>' : ''}</div>
        ${history(kind)}
      </div>`;
  }
  EXT.pages.deposit = () => memberPage('deposit');
  EXT.pages.withdraw = () => memberPage('withdrawal');

  document.addEventListener('click', e => {
    const b = e.target.closest('[data-rq-method]'); if (!b) return;
    const kind = b.dataset.kind, m = b.dataset.rqMethod; F[kind].method = m;
    const form = b.closest('form'); $$('[data-rq-method]', form).forEach(x => x.setAttribute('aria-selected', String(x === b)));
    $$('[data-grp]', form).forEach(g => { g.hidden = g.dataset.grp !== m; });
    const id = kind === 'deposit' ? 'dp' : 'wd'; $('#' + id + '-help').innerHTML = instructions(kind, m);
    const t = $('#' + id + '-help').parentElement.querySelector('h3'); if (kind === 'deposit') t.textContent = m === 'mpesa' ? 'Pay by M-Pesa' : 'Pay by bank transfer';
    $$('.field.err input', form).forEach(i => N.clearField(i));
  });

  document.addEventListener('submit', e => {
    const form = e.target.closest('#dp-form, #wd-form'); if (!form) return;
    e.preventDefault(); e.stopPropagation();
    const kind = form.dataset.kind, dep = kind === 'deposit', id = dep ? 'dp' : 'wd', f = F[kind], fe = N.fieldError;
    const amtEl = $('#' + id + '-amt'), amt = money(amtEl.value);
    if (!amt) return fe(amtEl, 'Enter an amount greater than zero.');
    if (!dep && amt > acctData.alpha.bal) return fe(amtEl, `You can withdraw up to ${kes(acctData.alpha.bal)}.`);
    let detail;
    if (f.method === 'mpesa') {
      const p = $('#' + id + '-phone'); if (!PHONE.test(cleanPhone(p.value))) return fe(p, 'Enter a Safaricom number like 0712 345 678 or +254 712 345 678.');
      detail = prettyPhone(p.value);
    } else {
      const bk = $('#' + id + '-bank'), ac = $('#' + id + '-acct');
      if (bk.value.trim().length < 2) return fe(bk, 'Enter the name of the bank.');
      if (dep ? ac.value.trim().length < 3 : !/^\d{6,20}$/.test(ac.value.replace(/\s/g, ''))) return fe(ac, dep ? 'Enter the reference from your bank receipt.' : 'Enter your account number, 6 to 20 digits.');
      detail = `${bk.value.trim()}, ${dep ? 'ref' : 'account'} ${ac.value.trim()}`;
    }
    RQ.unshift({ id: nextId++, who: ME, kind, method: f.method, amt, detail, st: 'Pending', when: '18 Nov ' + new Date().toTimeString().slice(0, 5), ref: f.ref });
    f.ref = uuid();
    f.banner = { k: 'ok', t: dep ? 'Deposit request sent. An officer will confirm it and it shows in My savings.' : 'Withdrawal request sent. An officer will confirm it and it shows in My savings.' };
    memberPage(kind); scrollTo({ top: 0, behavior: 'smooth' });
  }, true);

  /* ---------- the officer queue ---------- */
  let tab = 'Pending', rejecting = null, qBanner = null;
  EXT.pages.requests = () => {
    const host = $('#p-requests');
    const pend = RQ.filter(r => r.st === 'Pending'), rows = tab === 'Pending' ? pend : RQ.filter(r => r.st !== 'Pending');
    const own = r => r.who === ME;
    const line = r => `<tr><td>${r.who}</td><td><span class="chip ${r.kind === 'deposit' ? 'up' : 'warn'}">${r.kind === 'deposit' ? 'Deposit' : 'Withdrawal'}</span></td><td>${METHOD[r.method]}</td><td class="r">${kes(r.amt)}</td><td>${r.detail}</td><td>${r.when}</td><td>${r.st === 'Pending'
      ? (own(r) ? '<span class="chip lock">You cannot decide your own request</span>' : `<div class="actions" style="margin:0;flex-wrap:nowrap"><button class="btn small" type="button" data-rq="confirm" data-id="${r.id}">Confirm</button><button class="btn warn small" type="button" data-rq="reject-open" data-id="${r.id}">Reject</button></div>`)
      : `${chip(r.st)}${r.why ? `<br><small class="muted">${r.why}</small>` : ''}`}</td></tr>${rejecting === r.id ? `<tr><td colspan="7"><div class="actions" style="align-items:flex-end;margin:0"><div class="field" style="margin:0;flex:1;min-width:14rem"><label for="rq-why">Reason the member will see</label><input id="rq-why" autocomplete="off" placeholder="Amount does not match the payment"></div><button class="btn warn small" type="button" data-rq="reject-go" data-id="${r.id}">Reject request</button><button class="btn ghost small" type="button" data-rq="reject-cancel">Cancel</button></div></td></tr>` : ''}`;
    host.innerHTML = `${qBanner ? `<div class="banner ${qBanner.k}" role="status">${qBanner.t}</div>` : ''}
      <div class="glass rise"><div class="card-head"><div><div class="eyebrow">savings.post</div><h3 class="serif">Member deposit and withdrawal requests</h3></div>
        <div class="seg" role="tablist" aria-label="Queue">${['Pending', 'Decided'].map(k => `<button type="button" role="tab" data-rq-tab="${k}" aria-selected="${tab === k}">${k}${k === 'Pending' ? ` (${pend.length})` : ''}</button>`).join('')}</div></div>
        <div class="table-wrap"><table><thead><tr><th>Member</th><th>Type</th><th>Method</th><th class="r">Amount</th><th>Details</th><th>Requested</th><th>${tab === 'Pending' ? 'Decision' : 'Status'}</th></tr></thead><tbody>${rows.map(line).join('') || `<tr><td colspan="7">${tab === 'Pending' ? 'No requests are waiting. New member requests appear here.' : 'No decided requests yet.'}</td></tr>`}</tbody></table></div>
        <div class="rules"><span>Confirming a request posts the real ledger entry. Rejecting needs a reason.</span><span>Nobody decides their own request.</span><span>A withdrawal above the member's balance cannot be confirmed.</span></div></div>`;
  };
  document.addEventListener('click', e => {
    const t = e.target.closest('[data-rq],[data-rq-tab]'); if (!t) return;
    if (t.dataset.rqTab) { tab = t.dataset.rqTab; rejecting = null; return EXT.pages.requests(); }
    const id = +t.dataset.id, r = RQ.find(x => x.id === id), a = t.dataset.rq;
    if (a === 'reject-open') { rejecting = id; EXT.pages.requests(); const w = $('#rq-why'); if (w) w.focus(); return; }
    if (a === 'reject-cancel') { rejecting = null; return EXT.pages.requests(); }
    if (a === 'reject-go') {
      const w = $('#rq-why'); if (!w.value.trim()) { N.fieldError(w, 'Write a reason before you reject this request.'); return; }
      r.st = 'Rejected'; r.why = w.value.trim(); rejecting = null; qBanner = { k: 'ok', t: `Request from ${r.who} rejected. They can see your reason.` }; return EXT.pages.requests();
    }
    if (a === 'confirm') {
      const row = accts.find(x => x[0] === r.who);
      if (r.kind === 'withdrawal' && (!row || r.amt > row[2])) { qBanner = { k: 'err', t: `${r.who} has ${kes(row ? row[2] : 0)}, which is less than ${kes(r.amt)}. Reject this request and tell them why.` }; return EXT.pages.requests(); }
      if (row) row[2] += r.kind === 'deposit' ? r.amt : -r.amt;
      ledger.unshift({ id: Date.now(), who: r.who, type: r.kind === 'deposit' ? 'Deposit' : 'Withdrawal', amt: r.amt, st: 'posted' });
      r.st = 'Confirmed'; qBanner = { k: 'ok', t: `${r.kind === 'deposit' ? 'Deposit' : 'Withdrawal'} of ${kes(r.amt)} confirmed and posted to ${r.who}'s account.` };
      EXT.pages.requests();
    }
  });
})();
