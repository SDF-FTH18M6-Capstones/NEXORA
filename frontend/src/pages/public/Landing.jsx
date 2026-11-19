import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Logo } from '../../components/Logo.jsx';

const LINKS = [
  ['Sign in', '/login'],
  ['Create an account', '/register'],
  ['Join with a code', '/join'],
];

const POINTS = [
  ['Savings', 'Every deposit and withdrawal is recorded against a member.'],
  ['Loans', 'Members ask, officers review, and repayments are tracked.'],
  ['Records', 'Posted entries are never edited. A correction is a new entry.'],
];

function Reveal({ children, className = '' }) {
  const ref = useRef(null);
  const [shown, setShown] = useState(() => typeof IntersectionObserver === 'undefined');

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setShown(true);
        observer.disconnect();
      }
    }, { threshold: 0.2 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const state = shown
    ? 'translate-y-0 opacity-100'
    : 'translate-y-6 opacity-0 motion-reduce:translate-y-0 motion-reduce:opacity-100';
  return (
    <div
      ref={ref}
      className={`transition duration-700 ease-out motion-reduce:transition-none ${state} ${className}`}
    >
      {children}
    </div>
  );
}

function Hero3D() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  function move(event) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const box = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    setTilt({ x: y * -12, y: x * 12 });
  }

  return (
    <div
      className="mx-auto w-full max-w-md"
      style={{ perspective: '60rem' }}
      onPointerMove={move}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
    >
      <div
        className="relative h-64 transition-transform duration-200 ease-out motion-reduce:transition-none"
        style={{
          transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
          transformStyle: 'preserve-3d',
        }}
      >
        {POINTS.map(([label, line], index) => (
          <div
            key={label}
            className="glass absolute inset-x-0 flex flex-col gap-1"
            style={{ top: `${index * 4.5}rem`, transform: `translateZ(${index * 2.5}rem)` }}
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

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-10 p-4 md:p-6">
      <header className="flex items-center justify-between gap-3">
        <a className="flex items-center gap-2" href="/" aria-label="NEXORA home">
          <Logo className="mark" />
          <span className="font-serif text-xl">NEXORA</span>
        </a>
        <button
          type="button"
          className="btn ghost small md:hidden"
          aria-expanded={menuOpen}
          aria-controls="landing-menu"
          onClick={() => setMenuOpen(open => !open)}
        >
          {menuOpen ? 'Close menu' : 'Menu'}
        </button>
        <nav
          id="landing-menu"
          aria-label="Account options"
          className={`${menuOpen ? 'flex' : 'hidden'} absolute inset-x-4 top-16 z-50 flex-col gap-2 glass md:static md:flex md:flex-row md:items-center md:gap-3 md:bg-transparent md:p-0 md:shadow-none`}
        >
          {LINKS.map(([label, to], index) => (
            <Link key={to} className={index === 1 ? 'btn' : 'btn ghost'} to={to}>{label}</Link>
          ))}
        </nav>
      </header>

      <main className="flex flex-col gap-12">
        <section className="flex flex-col items-center gap-8 md:flex-row md:justify-between">
          <div className="flex max-w-xl flex-col gap-4">
            <h1 className="font-serif text-4xl">Savings and loans for your circle.</h1>
            <p className="text-muted">
              NEXORA keeps your SACCO&rsquo;s money in one clear record. Members see their own
              balance. Staff see what their role needs.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link className="btn" to="/login">Sign in</Link>
              <Link className="btn ghost" to="/join">Join with a code</Link>
            </div>
          </div>
          <Hero3D />
        </section>

        <section className="flex flex-col gap-4" aria-label="What NEXORA does">
          {POINTS.map(([label, line]) => (
            <Reveal key={label}>
              <div className="glass flex flex-col gap-1">
                <h2 className="font-serif text-2xl">{label}</h2>
                <p className="text-muted">{line}</p>
              </div>
            </Reveal>
          ))}
        </section>
      </main>
    </div>
  );
}