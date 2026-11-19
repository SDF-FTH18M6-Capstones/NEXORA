/* appearance.js: colour theme, font and text size, saved PER PERSON.
   Key: localStorage "nexora.appearance:<person>" holding {"theme":"ocean","font":"nunito","size":"large"}.
   In this prototype a person is the role chosen in the "view as" menu; in the real app it is the signed-in user's id.
   Signing in as someone else loads THEIR look; a person's choice never changes anybody else's. Signed out = the default Cream look. */
(() => {
  const N = window.NX;
  const { $, EXT, toast, S } = N;
  const KEY = 'nexora.appearance:';
  const THEMES = [
    { id: 'cream', name: 'Cream', note: 'Warm, default', sw: ['#F6EFE2', '#0F4C47', '#27806F', '#D9663B', '#F2B441'] },
    { id: 'sage', name: 'Sage', note: 'Fresh green', sw: ['#DDEBDC', '#1D5C37', '#2F7D4D', '#B9532B', '#E3B94D'] },
    { id: 'saffron', name: 'Saffron', note: 'Sunny yellow', sw: ['#FBE6A6', '#7A4600', '#9C5F08', '#BF431C', '#F2B441'] },
    { id: 'terracotta', name: 'Terracotta', note: 'Bold red', sw: ['#F8D3C3', '#9A2814', '#C4452A', '#9A2814', '#F2B441'] },
    { id: 'teal2', name: 'Teal 2', note: 'Bright turquoise', sw: ['#CFEEE9', '#0A6667', '#0B7F7D', '#D9663B', '#F2B441'] },
    { id: 'ocean', name: 'Ocean', note: 'Clear blue', sw: ['#D5E5FA', '#123E8C', '#2C6AD2', '#DB5A3A', '#F2B441'] },
    { id: 'rose', name: 'Rose', note: 'Soft pink', sw: ['#F9D4E2', '#A0154C', '#C2306B', '#C03A1E', '#F2B441'] },
    { id: 'slate', name: 'Slate', note: 'Calm grey', sw: ['#DCE1E8', '#2A374A', '#4D5F7A', '#C9532F', '#E8B44A'] },
    { id: 'ink', name: 'Ink', note: 'Dark green', dark: true, sw: ['#111A18', '#7FD3C2', '#4FB5A3', '#F08A64', '#F2B441'] },
    { id: 'midnight', name: 'Midnight', note: 'Dark navy', dark: true, sw: ['#0A1330', '#8DBBFF', '#5B96F2', '#FF8F6B', '#FFC857'] }
  ];
  const FONTS = [
    { id: 'default', name: 'Fraunces and Inter', note: 'Default', css: '"Fraunces", Georgia, serif' },
    { id: 'dm-sans', name: 'DM Sans', note: 'Clean and even', css: '"DM Sans", system-ui, sans-serif' },
    { id: 'lora', name: 'Lora', note: 'Book style', css: '"Lora", Georgia, serif' },
    { id: 'nunito', name: 'Nunito', note: 'Round and friendly', css: '"Nunito", system-ui, sans-serif' },
    { id: 'merriweather', name: 'Merriweather', note: 'Sturdy serif', css: '"Merriweather", Georgia, serif' },
    { id: 'atkinson', name: 'Atkinson Hyperlegible', note: 'Easiest to read', css: '"Atkinson Hyperlegible", system-ui, sans-serif' }
  ];
  const SIZES = [{ id: 'small', name: 'Small' }, { id: 'normal', name: 'Normal' }, { id: 'large', name: 'Large' }];
  const DEFAULT = { theme: 'cream', font: 'default', size: 'normal' };

  const who = () => (S.authed ? S.role : null);
  const load = () => { const w = who(); if (!w) return Object.assign({}, DEFAULT); try { return Object.assign({}, DEFAULT, JSON.parse(localStorage.getItem(KEY + w) || '{}')); } catch (e) { return Object.assign({}, DEFAULT); } };
  const save = v => { const w = who(); if (!w) return; try { localStorage.setItem(KEY + w, JSON.stringify(v)); } catch (e) {} };
  function apply(v, fade) {
    const de = document.documentElement;
    if (fade && !N.reduce) { de.classList.add('theme-fade'); setTimeout(() => de.classList.remove('theme-fade'), 450); }
    const t = THEMES.find(x => x.id === v.theme) || THEMES[0];
    de.dataset.theme = t.id; de.dataset.font = v.font; de.dataset.size = v.size; de.dataset.mode = t.dark ? 'dark' : 'light';
  }
  let cur = load(), last = who();
  /* called on every page change and on every sign-in, sign-out and "view as" switch */
  function sync() {
    const w = who(); cur = load();
    const de = document.documentElement;
    const t = THEMES.find(x => x.id === cur.theme) || THEMES[0];
    if (w !== last || de.dataset.theme !== t.id || de.dataset.font !== cur.font || de.dataset.size !== cur.size) apply(cur, w !== last);
    last = w;
  }
  addEventListener('storage', e => { if (e.key && e.key.indexOf(KEY) === 0) sync(); });   /* the same person in another tab changed their look */
  N.appearance = { THEMES, FONTS, SIZES, load, save, apply, sync };
  apply(cur);

  const card = () => `<div class="glass s12 rise" id="ap-card" style="--s:200ms"><div class="card-head"><div><div class="eyebrow">Appearance</div><h3 class="serif" style="font-size:1.4rem;margin:.3rem 0 0">Colours, font and text size</h3></div><button class="btn ghost small" type="button" data-ap-reset>Reset to default</button></div>
    <p class="muted">Only you see this. It changes how NEXORA looks for <b>you</b> and nobody else, on this device. It stays after you sign out and back in.</p>
    <div class="ap-label" style="margin-top:1rem">Colour theme</div>
    <div class="ap-grid" role="radiogroup" aria-label="Colour theme">${THEMES.map(t => `<button type="button" class="ap-opt" role="radio" aria-checked="${cur.theme === t.id}" data-ap="theme" data-v="${t.id}"><span class="ap-sw">${t.sw.map(c => `<i style="background:${c}"></i>`).join('')}</span><b>${t.name}</b><small>${t.note}</small></button>`).join('')}</div>
    <div class="ap-label">Font</div>
    <div class="ap-grid" role="radiogroup" aria-label="Font">${FONTS.map(f => `<button type="button" class="ap-opt" role="radio" aria-checked="${cur.font === f.id}" data-ap="font" data-v="${f.id}"><span class="ap-font" style="font-family:${f.css}">Aa 1,250</span><b>${f.name}</b><small>${f.note}</small></button>`).join('')}</div>
    <div class="ap-label">Text size</div>
    <div class="ap-grid" role="radiogroup" aria-label="Text size">${SIZES.map(s => `<button type="button" class="ap-opt" role="radio" aria-checked="${cur.size === s.id}" data-ap="size" data-v="${s.id}"><b>${s.name}</b></button>`).join('')}</div>
    <div class="ap-label">Preview</div>
    <div class="ap-preview"><div class="eyebrow">Circle savings balance</div><div class="big">KES 186,400</div><p class="muted">Your next payment of KES 8,500 is due on 30 November.</p><div class="actions" style="margin:0"><button class="btn small" type="button" tabindex="-1">Primary</button><button class="btn ghost small" type="button" tabindex="-1">Ghost</button><span class="chip up">Confirmed</span><span class="chip warn">Pending</span><span class="chip bad">Rejected</span></div></div></div>`;

  /* a menu item of its own, for every signed-in person (members, officers, admin, platform owner) */
  N.ICONS['my-settings'] = '<circle cx="12" cy="12" r="8.5"/><circle cx="8.5" cy="10" r="1.2"/><circle cx="12" cy="7.8" r="1.2"/><circle cx="15.5" cy="10" r="1.2"/><path d="M12 20.5c-1.4 0-1.9-1.2-1.2-2.1.6-.8.1-1.9-1-1.9H8.3"/>';
  N.MENU.push({ r: 'my-settings', t: 'My settings', ok: () => true });
  N.TITLES['my-settings'] = 'My settings';
  N.APP.push('my-settings');
  EXT.pages['my-settings'] = () => {
    cur = load();
    $('#p-my-settings').innerHTML = `<div class="grid">${card()}
      <div class="glass s12 rise" style="--s:260ms"><div class="eyebrow">Account</div><h3 class="serif" style="font-size:1.3rem;margin:.3rem 0 .5rem">Photo, email, password and sessions</h3><p class="muted">Your profile and sign-in details are in Account settings.</p><div class="actions"><a class="btn ghost small" href="#account">Open account settings</a></div></div></div>`;
  };

  const repaint = () => { const old = $('#ap-card'); if (!old) return; const y = scrollY; old.outerHTML = card(); $('#ap-card').classList.remove('rise'); scrollTo(0, y); };
  document.addEventListener('click', e => {
    const o = e.target.closest('[data-ap]');
    if (o) { cur = Object.assign({}, cur, { [o.dataset.ap]: o.dataset.v }); save(cur); apply(cur, true); repaint(); const n = $(`[data-ap="${o.dataset.ap}"][data-v="${o.dataset.v}"]`); if (n) n.focus({ preventScroll: true }); return; }
    if (e.target.closest('[data-ap-reset]')) { cur = Object.assign({}, DEFAULT); save(cur); apply(cur, true); repaint(); toast('Appearance reset to the default.'); }
  });
})();
