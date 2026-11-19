import { useState } from 'react';
import ErrorBanner from '../../components/ErrorBanner.jsx';
import ErrorPage from '../../components/ErrorPage.jsx';
import Field from '../../components/Field.jsx';
import { ROLES } from '../../lib/perms.js';
import { useSession } from '../../lib/session.jsx';
import { describe } from '../../lib/errors.js';
import { MOCK } from '../../lib/http.js';

export default function Login() {
  const { login, sessionEnded, clearSessionEnded } = useSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('member');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setSending(true);
    try {
      await login(email.trim(), password, role);
    } catch (failure) {
      setError(describe(failure, { context: 'login' }).text);
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="auth">
      <div className="auth-inner">
        <div className="auth-copy">
          <h1 className="serif">Welcome <em>back.</em></h1>
          <p>Sign in to continue to your SACCO.</p>
        </div>
        <form className="glass auth-card" onSubmit={submit}>
          <div className="eyebrow">Sign in</div>
          {sessionEnded && (
            <ErrorPage code="401" onAction={action => {
              if (action === 'login') clearSessionEnded();
            }} />
          )}
          <h2 className="serif">Your SACCO awaits</h2>
          {error && <ErrorBanner>{error}</ErrorBanner>}
          <Field id="login-email" label="Email">
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={event => setEmail(event.target.value)}
            />
          </Field>
          <Field id="login-password" label="Password">
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={event => setPassword(event.target.value)}
            />
          </Field>
          {MOCK && (
            <Field id="login-role" label="Test role">
              <select value={role} onChange={event => setRole(event.target.value)}>
                {Object.entries(ROLES).map(([key, item]) => (
                  <option key={key} value={key}>{item.label}</option>
                ))}
              </select>
            </Field>
          )}
          <button className="btn" type="submit" disabled={sending}>
            {sending ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </main>
  );
}
