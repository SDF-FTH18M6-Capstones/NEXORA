/* TEMPORARY: shows the Shell inside the dev harness. Delete in R3 when the real router exists.
 * The transform makes the fixed sidebar sit inside this box instead of covering the harness bar. */
import { useState } from 'react';
import { SessionContext, useSession } from '../lib/session.jsx';
import { homeFor } from '../lib/perms.js';
import Shell from './Shell.jsx';

export default function ShellPreview() {
  const session = useSession();
  const [path, setPath] = useState(homeFor(session.perms));
  const local = { ...session, navigate: to => setPath(to.replace(/^\//, '')) };
  return (
    <SessionContext.Provider value={local}>
      <div style={{ transform: 'translateZ(0)', position: 'relative', minHeight: '46rem' }}>
        <Shell path={path}>
          <section className="glass">
            <p className="muted">Page area for: {path}</p>
          </section>
        </Shell>
      </div>
    </SessionContext.Provider>
  );
}