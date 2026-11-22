import { Suspense, useEffect, useRef, useState } from 'react';
import Intro from '../pages/public/Intro.jsx';
import { useLocation, useOutlet } from 'react-router-dom';

const INTRO_MS = 4800;
const LIFT_MS = 1100;
const FADE_MS = 160;
const INTRO_KEY = 'nexora.intro-seen';

// The signature intro is a first-visit piece: replaying it on every reload made
// the app feel slow, so it plays once per browser session.
function introSeen() {
  try { return window.sessionStorage.getItem(INTRO_KEY) === '1'; } catch { return false; }
}

export default function RouteTransition() {
  const outlet = useOutlet();
  const location = useLocation();
  const [reducedMotion] = useState(() => (
    typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ));
  const [skipIntro] = useState(() => reducedMotion || introSeen());
  const initialPhase = skipIntro ? 'idle' : 'intro';
  const [phase, setPhaseState] = useState(initialPhase);
  const [visibleOutlet, setVisibleOutlet] = useState(outlet);
  const [sequence] = useState(0);
  const outletRef = useRef(outlet);
  const phaseRef = useRef(initialPhase);
  const locationKeyRef = useRef(location.key);
  const curtainRef = useRef(null);

  function setPhase(next) {
    phaseRef.current = next;
    setPhaseState(next);
  }

  useEffect(() => {
    outletRef.current = outlet;
    // A new route is swapped in by the fade below; this only follows the same
    // route's own updates (a lazy page finishing loading) and the intro.
    const sameRoute = locationKeyRef.current === location.key;
    if (phaseRef.current === 'intro' || (phaseRef.current === 'idle' && sameRoute)) setVisibleOutlet(outlet);
  }, [outlet, location.key]);

  useEffect(() => {
    if (skipIntro) return undefined;
    try { window.sessionStorage.setItem(INTRO_KEY, '1'); } catch { /* private mode: it just plays again next time */ }
    const exitTimer = window.setTimeout(() => setPhase('exit'), INTRO_MS - LIFT_MS);
    const finishTimer = window.setTimeout(() => setPhase('idle'), INTRO_MS);
    return () => {
      window.clearTimeout(exitTimer);
      window.clearTimeout(finishTimer);
    };
  }, [skipIntro]);

  useEffect(() => {
    if (locationKeyRef.current === location.key) return undefined;
    locationKeyRef.current = location.key;

    if (phaseRef.current === 'intro') {
      setVisibleOutlet(outlet);
      return undefined;
    }

    // Fade the old page out, swap, fade the new one in. No full-screen curtain.
    let cancelled = false;
    const timers = [];
    const schedule = (callback, delay) => {
      timers.push(window.setTimeout(callback, delay));
    };
    setPhase('fade-out');
    schedule(() => {
      if (cancelled) return;
      setVisibleOutlet(outletRef.current);
      window.scrollTo(0, 0);
      setPhase('idle');
    }, FADE_MS);

    return () => {
      cancelled = true;
      timers.forEach(window.clearTimeout);
    };
  }, [location.key, outlet]);

  return (
    <>
      <div
        className="route-content"
        style={{
          opacity: phase === 'fade-out' ? 0 : 1,
          transition: `opacity ${FADE_MS}ms ease`,
        }}
      >
        <Suspense fallback={<div className="glass p-6 text-muted">Loading...</div>}>
          {visibleOutlet}
        </Suspense>
      </div>
      <Intro phase={phase} sequence={sequence} curtainRef={curtainRef} />
    </>
  );
}
