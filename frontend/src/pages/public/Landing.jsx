import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Logo } from '../../components/Logo.jsx';

const LINKS = [
  ['Sign in', '/login'],
  ['Create an account', '/register'],
  // Joining needs a signed-in account (the API ties the code to it), so this
  // goes to sign-in and carries the destination: the login route returns here.
  ['Join with a code', '/login', { from: '/join' }],
];

const POINTS = [
  ['Savings', 'Every deposit and withdrawal is recorded against a member.'],
  ['Loans', 'Members ask, officers review, and repayments are tracked.'],
  ['Records', 'Posted entries are never edited. A correction is a new entry.'],
];

function Hero3D() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const stackRef = useRef(null);

  /* The cards are absolutely positioned so they can overlap, which leaves the
   * box with no height of its own: it has to grow with them. Otherwise the
   * second and third cards sit on top of the menu and the list below. */
  useEffect(() => {
    const stack = stackRef.current;
    if (!stack) return undefined;
    const fit = () => {
      const cards = Array.from(stack.children);
      const last = cards[cards.length - 1];
      if (!last) return;
      // Each card covers the foot of the one behind it. The overlap stays inside
      // the bottom padding, so it reads as depth without ever hiding a line of
      // text once the card wraps to three lines on a phone.
      const padding = parseFloat(getComputedStyle(cards[0]).paddingBottom) || 16;
      const overlap = Math.max(8, Math.round(padding * 0.85));
      let top = 0;
      cards.forEach((card, index) => {
        card.style.top = `${top}px`;
        if (index < cards.length - 1) top += card.offsetHeight - overlap;
      });
      let height = last.offsetTop + last.offsetHeight;
      stack.style.height = `${height}px`;
      // The cards are pushed toward the viewer, so the last one paints a little
      // taller than its layout box: grow by whatever still hangs over the edge.
      for (let pass = 0; pass < 4; pass += 1) {
        const over = last.getBoundingClientRect().bottom - stack.getBoundingClientRect().bottom;
        if (over <= 0.5) break;
        height += Math.ceil(over);
        stack.style.height = `${height}px`;
      }
    };
    let active = true;
    const safeFit = () => { if (active) fit(); };
    safeFit();
    // The cards wrap differently once the webfonts land, and the first fit runs
    // before that: measure again on the next frame and when the fonts are ready.
    const frame = requestAnimationFrame(safeFit);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(safeFit).catch(() => {});
    // Offsets are in rem, so a width change moves the cards even when the card
    // boxes themselves keep their size: watch both the cards and the window.
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(safeFit);
    if (observer) Array.from(stack.children).forEach(card => observer.observe(card));
    window.addEventListener('resize', safeFit);
    return () => {
      active = false;
      cancelAnimationFrame(frame);
      if (observer) observer.disconnect();
      window.removeEventListener('resize', safeFit);
    };
  }, []);

  function move(event) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const box = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    setTilt({ x: y * -12, y: x * 12 });
  }

  return (
    <div
      className="mx-auto w-full max-w-lg"
      style={{ perspective: '60rem' }}
      onPointerMove={move}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
    >
      <div
        ref={stackRef}
        className="relative h-64 transition-transform duration-200 ease-out motion-reduce:transition-none"
        style={{
          transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
          transformStyle: 'preserve-3d',
        }}
      >
        {POINTS.map(([label, line], index) => (
          <div
            key={label}
            className="glass flex flex-col gap-1"
            style={{
              // .glass sets position: relative and, being unlayered CSS, it beats
              // Tailwind's `absolute`. Inline wins, so the cards really stack.
              position: 'absolute',
              left: 0,
              right: 0,
              transform: `translateZ(${index * 2.5}rem)`,
            }}
          >
            <span className="font-serif text-xl">{label}</span>
            <span className="text-muted">{line}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Landing() {
  const [menuOpen, setMenuOpen] = useState(false);
  const barRef = useRef(null);

  /* The phone menu covers the headline, so a tap anywhere else has to close it.
   * Without this the only way back to the page was the Menu button again. */
  useEffect(() => {
    if (!menuOpen) return undefined;
    function onPointerDown(event) {
      if (barRef.current && !barRef.current.contains(event.target)) setMenuOpen(false);
    }
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [menuOpen]);

  return (
    <div className="flex w-full flex-col gap-8 pb-10">
      {/* The bar's own classes (.lnav, .lnav-cta, .lnav-burger, .lnav-pop) decide
        * what a phone shows. Tailwind's md: rules cannot do it here: .btn and
        * .glass sit outside @layer, so they beat those utilities and the panel
        * stayed on screen, laid over the hero and swallowing its clicks. */}
      <header className="lnav glass" ref={barRef}>
        <a className="flex items-center gap-2" href="/" aria-label="NEXORA home">
          <Logo className="mark" />
          <span className="font-serif text-xl">NEXORA</span>
        </a>
        <div className="lnav-cta ml-auto">
          <Link className="btn ghost small lnav-join" to="/login" state={{ from: '/join' }}>Join with a code</Link>
          <Link className="btn small" to="/login">Sign in</Link>
          <button
            type="button"
            className="btn ghost small lnav-burger"
            aria-expanded={menuOpen}
            aria-controls="lnav-pop"
            onClick={() => setMenuOpen(open => !open)}
          >
            {menuOpen ? 'Close' : 'Menu'}
          </button>
        </div>
        {menuOpen && (
          <div className="lnav-pop" id="lnav-pop">
            {LINKS.map(([label, to, state]) => (
              <Link key={label} to={to} state={state}>{label}</Link>
            ))}
          </div>
        )}
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-4 md:px-6">
        <section className="flex flex-col items-center gap-8 md:flex-row md:items-center md:justify-between md:gap-12">
          <div className="flex max-w-xl flex-col gap-4">
            <h1 className="font-serif text-[clamp(2.25rem,4.2vw,3.4rem)] leading-[1.05]">Savings and loans for your circle.</h1>
            <p className="text-muted md:text-lg">
              NEXORA keeps your SACCO&rsquo;s money in one clear record. Members see their own
              balance. Staff see what their role needs.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link className="btn" to="/login">Sign in</Link>
              <Link className="btn ghost" to="/login" state={{ from: '/join' }}>
                Join with a code
              </Link>
            </div>
          </div>
          <Hero3D />
        </section>

        <section className="glass cta-band" aria-label="Get started">
          <h2 className="serif">Bring your SACCO in.</h2>
          <p className="text-muted">
            Sign in if you already have an account, or join with the code you were sent.
          </p>
          <div className="cta">
            <Link className="btn" to="/login">Sign in</Link>
            <Link className="btn ghost" to="/login" state={{ from: '/join' }}>
              Join with a code
            </Link>
          </div>
        </section>
      </main>

      <footer className="lfoot mx-auto w-full max-w-6xl px-4 md:px-6">
        NEXORA · Savings and loans for your circle.
      </footer>
    </div>
  );
}