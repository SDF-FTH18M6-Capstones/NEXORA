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

  function move(event) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const box = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    setTilt({ x: y * -10, y: x * 10 });
  }

  return (
    <div
      className="w-full max-w-[36rem] lg:max-w-[28rem] xl:max-w-[36rem]"
      style={{ perspective: '90rem' }}
      onPointerMove={move}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
    >
      <div
        className="flex flex-col gap-[0.65rem] transition-transform duration-200 ease-out motion-reduce:transition-none"
        style={{
          transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
          transformStyle: 'preserve-3d',
        }}
      >
        {/* The cards are normal flow items separated by a small gap: the stack
          * is a group, not three boxes glued together. translateZ gives the
          * depth and layout gives the height, so nothing has to be measured. */}
        {POINTS.map(([label, line], index) => (
          <div
            key={label}
            className="glass flex flex-col gap-2"
            style={{ transform: `translateZ(${index * 1.6}rem)` }}
          >
            <span className="font-serif text-[1.6rem]">{label}</span>
            <span className="text-[1.05rem] text-muted">{line}</span>
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
    <div className="flex w-full flex-col gap-10 pb-10">
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
          <Link className="btn ghost small" to="/login">Sign in</Link>
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

      {/* The hero uses the screen a laptop actually has: 100rem at the top, which
        * leaves a working margin instead of a third of the display in cream. */}
      <main className="mx-auto flex w-full max-w-[100rem] flex-col px-5 md:px-8">
        {/* Side by side from 1024 up: a 1024 laptop is a desktop, and stacking it
          * there left the hero as a narrow phone column. The copy narrows and
          * the gap tightens below xl so both columns still fit. */}
        <section className="flex flex-col items-start gap-12 lg:min-h-[calc(100vh-18.5rem)] lg:flex-row lg:items-center lg:justify-between lg:gap-10 xl:gap-20">
          <div className="flex max-w-[46rem] flex-col gap-6 lg:max-w-[28rem] xl:max-w-[46rem]">
            <h1 className="font-serif text-[clamp(2.5rem,4.4vw,5rem)] leading-[1.04]">Savings and loans for your circle.</h1>
            <p className="text-muted lg:text-lg xl:text-xl">
              NEXORA keeps your SACCO&rsquo;s money in one clear record. Members see their own
              balance. Staff see what their role needs.
            </p>
            <div className="flex flex-wrap gap-3 pt-1">
              <Link className="btn" to="/login">Sign in</Link>
              <Link className="btn ghost" to="/login" state={{ from: '/join' }}>
                Join with a code
              </Link>
            </div>
          </div>
          <Hero3D />
        </section>
      </main>

      <footer className="lfoot mx-auto w-full max-w-[100rem] px-5 md:px-8">
        NEXORA · Savings and loans for your circle.
      </footer>
    </div>
  );
}
