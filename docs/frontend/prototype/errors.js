/* errors.js: error pages, field errors, the offline notice, and the style guide page */
(() => {
  const N = window.NX;
  const { $, $$, S, can, toast, EXT, TITLES, APP, MENU, logoSvg } = N;

  /* ---------- one place that says what every failure looks like and what the user can do about it ---------- */
  const ERRORS = {
    '404': { n: '404', t: 'We could not find that page', s: 'The address may be mistyped, or the page was moved. Nothing was changed.', a: ['Go to my start page', 'home'], b: ['Go back', 'back'] },
    '403': { n: '403', t: 'You do not have access to this page', s: 'Your role does not include it. If you think it should, ask your SACCO admin.', a: ['Go to my start page', 'home'], b: ['Go back', 'back'] },
    '401': { n: '401', t: 'Your session ended', s: 'Sign in again to carry on. Nothing you were doing was saved or sent.', a: ['Sign in', 'login'], b: ['Back to home', 'landing'] },
    '423': { n: '423', t: 'This SACCO is suspended', s: 'Its records are locked until the platform owner reopens it. You can still change your account settings or pick another SACCO.', a: ['Choose another SACCO', 'switcher'], b: ['Account settings', 'account'] },
    '429': { n: '429', t: 'Too many requests', s: 'Please wait before trying again. The button turns on when the wait is over.', a: ['Try again', 'retry'], b: ['Go to my start page', 'home'], wait: 30 },
    '500': { n: '500', t: 'Something went wrong on our side', s: 'We recorded it. Try again in a moment. If it keeps happening, tell your admin the reference below.', a: ['Try again', 'retry'], b: ['Go to my start page', 'home'], ref: true },
    'offline': { n: '', t: 'You are offline', s: 'Check your connection. Nothing was lost, and this page reloads by itself when you are back.', a: ['Try again', 'retry'], b: ['Go to my start page', 'home'] }
  };
  const key = c => 'e-' + c;
  Object.keys(ERRORS).forEach(c => { APP.push(key(c)); TITLES[key(c)] = ERRORS[c].t; });
  APP.push('styleguide'); TITLES.styleguide = 'Style guide';

  let timer = 0;
  function render(code, host) {
    const e = ERRORS[code], id = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now())).slice(0, 8);
    clearInterval(timer);
    /* nothing decorative: the code (or the word Offline), the title, one sentence, the buttons */
    host.innerHTML = `<div class="errpage"><div class="err-num ${e.n ? '' : 'word'}" aria-hidden="true">${e.n || 'Offline'}</div>
      <div class="err-card" role="alert" aria-live="assertive"><h2 class="serif">${e.t}</h2><p class="muted">${e.s}</p>
        <div class="actions"><button class="btn" type="button" data-err="${e.a[1]}" ${e.wait ? 'disabled' : ''} id="err-main">${e.a[0]}${e.wait ? ` (<span id="err-wait">${e.wait}</span>s)` : ''}</button><button class="btn ghost" type="button" data-err="${e.b[1]}">${e.b[0]}</button></div>
        ${e.ref ? `<p class="note">Reference <code>${id}</code> <button class="link-btn" type="button" data-copy="${id}">Copy</button></p>` : ''}</div></div>`;
    if (e.wait) {
      let left = e.wait; timer = setInterval(() => { left -= 1; const w = $('#err-wait'); if (w) w.textContent = left; if (left <= 0) { clearInterval(timer); const b = $('#err-main'); if (b) { b.disabled = false; b.textContent = e.a[0]; } } }, 1000);
    }
  }
  Object.keys(ERRORS).forEach(c => { EXT.pages[key(c)] = () => render(c, $('#p-' + key(c))); });
  EXT.errorPage = (code, k) => render(code, $('#p-' + k));
  /* a suspended SACCO answers 423 on every SACCO screen, except account settings and the style guide */
  EXT.guard = k => (S.suspended && !can('platform') && !/^(e-|account|styleguide)/.test(k)) ? '423' : null;

  document.addEventListener('click', e => {
    const b = e.target.closest('[data-err],[data-copy]'); if (!b) return;
    if (b.dataset.copy) { (navigator.clipboard ? navigator.clipboard.writeText(b.dataset.copy) : Promise.reject()).then(() => toast('Reference copied.'), () => toast('Select the reference and copy it.', 'err')); return; }
    const a = b.dataset.err, home = can('platform') ? 'pf-overview' : 'overview';
    if (a === 'home') location.hash = home;
    else if (a === 'back') { if (S.prev && S.prev.indexOf('e-') !== 0 && APP.concat(N.PUBLIC).includes(S.prev)) location.hash = S.prev; else location.hash = home; }
    else if (a === 'switcher') { $('#switcher-menu').hidden = false; $('#switcher-btn').setAttribute('aria-expanded', 'true'); }
    else if (a === 'retry') toast('Trying again…');
    else location.hash = a;
  });

  /* ---------- the offline notice ---------- */
  const net = $('#net-banner');
  const sync = () => { net.hidden = navigator.onLine; };
  addEventListener('offline', sync);
  addEventListener('online', () => { sync(); toast('You are back online.'); });
  sync();

  /* ---------- field errors: show the problem next to the field it belongs to ---------- */
  N.fieldError = (input, text) => {
    if (!input) return; const f = input.closest('.field'); if (!f) return;
    clearField(input); f.classList.add('err'); input.setAttribute('aria-invalid', 'true');
    const m = document.createElement('div'); m.className = 'field-msg'; m.id = 'fm-' + (input.id || Math.random().toString(36).slice(2, 7)); m.setAttribute('role', 'alert'); m.textContent = text;
    f.appendChild(m); input.setAttribute('aria-describedby', m.id); input.focus();
    input.addEventListener('input', () => clearField(input), { once: true });
  };
  function clearField(input) { const f = input.closest('.field'); if (!f) return; f.classList.remove('err'); input.removeAttribute('aria-invalid'); input.removeAttribute('aria-describedby'); $$('.field-msg', f).forEach(x => x.remove()); }
  N.clearField = clearField;

  /* ---------- style guide: the exact look of every shared piece ---------- */
  const sw = (n, v, d) => `<div class="swatch"><i style="background:${v}"></i><b>${n}</b><span>${v}</span><small>${d}</small></div>`;
  EXT.pages.styleguide = () => {
    $('#p-styleguide').innerHTML = `<div class="stack">
      <div class="glass rise"><div class="eyebrow">Colour</div><h3 class="serif">Cream field, three colour fields, one ink</h3><div class="swatches">
        ${sw('Cream', '#F6EFE2', 'page ground')}${sw('Ink', '#1B2826', 'text')}${sw('Muted', '#5A6A65', 'secondary text')}${sw('Teal', '#0F4C47', 'primary, brand')}${sw('Teal 2', '#2F8A7B', 'hover, charts')}${sw('Terracotta', '#D9663B', 'errors, accent')}${sw('Saffron', '#F2B441', 'warnings, highlights')}${sw('Sage', '#8DB39A', 'quiet accent')}</div><p class="note">These are the default Cream theme. Each person can pick another colour theme, font and text size in Account settings, under Appearance.</p></div>
      <div class="glass rise"><div class="eyebrow">Buttons</div><div class="actions"><button class="btn">Primary</button><button class="btn ghost">Ghost</button><button class="btn warn">Warning</button><button class="btn small">Small</button><button class="btn" disabled>Disabled</button><button class="back" type="button">← Back</button></div>
        <div class="actions"><span class="chip up">Posted</span><span class="chip warn">Waiting</span><span class="chip bad">Reversed</span><span class="chip">Neutral</span><span class="chip lock">Read only</span></div></div>
      <div class="glass rise"><div class="eyebrow">Messages</div><h3 class="serif">Banners: errors are loud, everything else is calm</h3>
        <div class="banner err" role="alert">That code is not right. Check the 6 digits and try again.</div>
        <div class="banner warn" role="status">Suspending locks this SACCO for all its members. Click again to confirm.</div>
        <div class="banner info" role="status">This request was already recorded. Nothing was posted twice.</div>
        <div class="banner ok" role="status">Entry posted. Each submit uses its own reference, so a retry never posts twice.</div>
        <div class="actions"><button class="btn small ghost" data-toast="ok">Show a success toast</button><button class="btn small warn" data-toast="err">Show an error toast</button></div></div>
      <div class="grid"><div class="glass s6 rise"><div class="eyebrow">Fields</div><div class="field"><label for="sg-a">Normal</label><input id="sg-a" placeholder="Amount"></div><div class="field err"><label for="sg-b">With an error</label><input id="sg-b" value="abc" aria-invalid="true"><div class="field-msg" role="alert">Enter an amount greater than zero.</div></div></div>
        <div class="glass s6 rise" style="--s:80ms"><div class="eyebrow">Loading, empty, failed</div><div class="sk" style="height:1.2rem;width:60%"></div><div class="sk" style="height:5rem;margin:.7rem 0"></div><div class="sk" style="height:.9rem;width:80%"></div>
          <div class="empty"><div class="empty-ic" aria-hidden="true">0</div><b>No loans are waiting for a decision.</b><span class="muted">When a member requests a loan it appears here.</span></div>
          <div class="banner err" role="alert">We could not load the loans. Check your connection and try again. <button class="btn small ghost" type="button" style="margin-left:.4rem">Try again</button></div></div></div>
      <div class="glass rise"><div class="eyebrow">Error pages</div><h3 class="serif">Full-page failures</h3><div class="actions">${Object.keys(ERRORS).map(c => `<a class="btn small ghost" href="#e-${c}">${c === 'offline' ? 'Offline' : c}</a>`).join('')}</div></div></div>`;
  };
  document.addEventListener('click', e => { const b = e.target.closest('[data-toast]'); if (b && $('#p-styleguide') && !$('#p-styleguide').hidden) toast(b.dataset.toast === 'err' ? 'We could not save that. Try again in a moment.' : 'Saved.', b.dataset.toast === 'err' ? 'err' : ''); });
})();
