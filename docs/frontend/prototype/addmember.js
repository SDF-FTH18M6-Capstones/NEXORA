/* addmember.js: "Add a member", a section of its own (permission member.manage, the SACCO admin).
   The admin types a phone number and picks a role; NEXORA makes a 6-digit join code that works once and lasts 15 minutes.
   The person then signs in to their own account, opens "Join with a code", enters this phone number and code, and sets their circle PIN. */
(() => {
  const N = window.NX;
  const { $, $$, can, toast, EXT, mem, ROLES } = N;
  const PHONE = /^(?:\+254|254|0)([17]\d{8})$/;
  const clean = v => v.replace(/[\s-]/g, '');
  const pretty = v => { const m = PHONE.exec(clean(v)); return m ? '0' + m[1].slice(0, 3) + ' ' + m[1].slice(3, 6) + ' ' + m[1].slice(6) : v; };
  const mask = v => { const p = pretty(v); return p.slice(0, 4) + ' ••• ' + p.slice(-3); };
  const ROLE_OPTS = [['member', 'Member'], ['secretary', 'Secretary'], ['finance', 'Finance officer'], ['loans', 'Loans officer']];

  let code = null, end = 0, who = '', role = 'member', banner = null, timer = 0;
  const newCode = () => String(Math.floor(100000 + Math.random() * 900000));

  N.ICONS['add-member'] = '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M19 8v6M16 11h6"/>';
  const at = N.MENU.findIndex(m => m.r === 'members');
  N.MENU.splice(at + 1, 0, { r: 'add-member', t: 'Add a member', ok: () => !can('platform') && can('member.manage') });
  N.TITLES['add-member'] = 'Add a member';
  N.APP.push('add-member');

  function countdown() {
    clearInterval(timer);
    timer = setInterval(() => {
      const el = $('#ad-count'); if (!el) { clearInterval(timer); return; }
      const left = Math.max(0, end - Date.now());
      if (!left) { clearInterval(timer); EXT.pages['add-member'](); return; }
      el.textContent = 'Expires in ' + String(Math.floor(left / 60000)).padStart(2, '0') + ':' + String(Math.floor(left / 1000) % 60).padStart(2, '0');
    }, 1000);
  }

  EXT.pages['add-member'] = () => {
    const invited = mem.map((m, i) => [m, i]).filter(([m]) => m[2] === 'Invited');
    const left = Math.max(0, end - Date.now());
    $('#p-add-member').innerHTML = `${banner ? `<div class="banner ${banner.k}" role="status">${banner.t}</div>` : ''}
      <div class="grid">
        <form class="glass s7 rise" id="ad-form" novalidate>
          <div class="card-head"><div><div class="eyebrow">New member</div><h3 class="serif" style="font-size:1.5rem">Add a member to this SACCO</h3></div><span class="chip lock">member.manage</span></div>
          <div class="field"><label for="ad-phone">Phone number</label><input id="ad-phone" inputmode="tel" autocomplete="off" placeholder="0712 345 678" value="${who}"></div>
          <div class="field"><label for="ad-role">Role</label><select id="ad-role">${ROLE_OPTS.map(([k, l]) => `<option value="${k}" ${k === role ? 'selected' : ''}>${l}</option>`).join('')}</select></div>
          <div class="actions"><button class="btn" type="submit">Make a join code</button></div>
          <p class="note">The person needs a NEXORA account. If they have none, they create one on the landing page first. This code gives them a place in this SACCO only after they set their PIN.</p>
          ${code && left ? `<div class="banner info" style="margin-top:1rem">Give this code to the person now. It works once. It is shown only on this screen.</div><div class="code-box" id="ad-code">${code}</div><div class="actions" style="justify-content:center"><button class="btn small" type="button" data-ad="copy">Copy code</button><span class="chip warn num" id="ad-count">Expires in 15:00</span></div>` : code ? '<div class="banner err" style="margin-top:1rem">That code expired. Make a new one.</div>' : ''}
        </form>
        <div class="glass s5 rise" style="--s:80ms"><div class="eyebrow">How a member joins</div><h3 class="serif" style="font-size:1.3rem;margin:.3rem 0 .6rem">Four steps</h3>
          <ol class="steps-list"><li>You type their phone number and choose their role, then make the code.</li><li>You give them the 6-digit code in person or by a call. NEXORA does not send it.</li><li>They sign in to their own account, open <b>Join with a code</b>, and enter the same phone number and the code.</li><li>They choose a 4-digit PIN. From then on they type that PIN to enter this SACCO.</li></ol>
          <p class="note">A wrong guess counts against the code. After too many wrong tries it is locked and you make a new one.</p></div>
        <div class="glass s12 rise" style="--s:140ms"><div class="card-head"><div><div class="eyebrow">Waiting to join</div><h3 class="serif">Invited, not joined yet</h3></div><span class="chip">${invited.length} invited</span></div>
          <div class="table-wrap"><table><thead><tr><th>Phone</th><th>Role</th><th>Status</th><th></th></tr></thead><tbody>${invited.map(([m, i]) => `<tr><td>${m[1]}</td><td>${ROLES[m[3]].label}</td><td><span class="chip warn">Invited</span></td><td><button class="btn ghost small" type="button" data-ad="renew" data-i="${i}">Make a new code</button></td></tr>`).join('') || '<tr><td colspan="4">Nobody is waiting. People you add appear here until they join.</td></tr>'}</tbody></table></div></div>
      </div>`;
    if (code && left) countdown();
  };

  document.addEventListener('submit', e => {
    if (e.target.id !== 'ad-form') return;
    e.preventDefault(); e.stopPropagation();
    const p = $('#ad-phone'); who = p.value; role = $('#ad-role').value;
    if (!PHONE.test(clean(p.value))) return N.fieldError(p, 'Enter a Safaricom number like 0712 345 678 or +254 712 345 678.');
    const m = mask(p.value), found = mem.find(x => x[1].slice(0, 4) === m.slice(0, 4) && x[1].slice(-3) === m.slice(-3));
    if (found && found[2] === 'Active') return N.fieldError(p, 'This number is already a member.');
    if (found && found[2] === 'Invited') { found[3] = role; banner = { k: 'info', t: 'This number was already invited. A new code was made and the old one stopped working.' }; }
    else { mem.push(['New member', m, 'Invited', role]); banner = { k: 'ok', t: `Join code made for ${pretty(p.value)} as ${ROLES[role].label}.` }; }
    code = newCode(); end = Date.now() + 15 * 60000; who = '';
    EXT.pages['add-member'](); scrollTo({ top: 0, behavior: 'smooth' });
  }, true);

  document.addEventListener('click', e => {
    const b = e.target.closest('[data-ad]'); if (!b) return;
    if (b.dataset.ad === 'copy') { (navigator.clipboard ? navigator.clipboard.writeText(code) : Promise.reject()).then(() => toast('Code copied.'), () => toast('Select the code and copy it.', 'err')); }
    if (b.dataset.ad === 'renew') { const m = mem[+b.dataset.i]; code = newCode(); end = Date.now() + 15 * 60000; banner = { k: 'ok', t: `A new code was made for ${m[1]}. The old one stopped working.` }; EXT.pages['add-member'](); scrollTo({ top: 0, behavior: 'smooth' }); }
  });
})();
