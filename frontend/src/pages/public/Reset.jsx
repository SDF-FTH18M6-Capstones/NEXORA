import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ErrorBanner from '../../components/ErrorBanner.jsx';
import Field from '../../components/Field.jsx';
import { describe } from '../../lib/errors.js';
import { useSession } from '../../lib/session.jsx';
import { resetPasswordRequest } from '../../api/auth.js';
import AuthFrame from './AuthFrame.jsx';

export default function Reset() {
  const { navigate, toast } = useSession();
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [password, setPassword] = useState('');
  const [again, setAgain] = useState('');
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const next = {};
    if (password.length < 8) next.password = 'Use at least 8 characters.';
    if (again !== password) next.again = 'The two passwords do not match.';
    setErrors(next);
    setError('');
    if (Object.keys(next).length > 0) return;
    setSending(true);
    try {
      await resetPasswordRequest(token, password);
      toast('Password changed. Sign in with the new one.');
      navigate('/login', { replace: true });
    } catch (failure) {
      setError(describe(failure).text);
      setSending(false);
    }
  }

  if (!token) {
    return (
      <AuthFrame eyebrow="Reset password" heading="This link is not complete">
        <ErrorBanner>Open the link from your email again, or ask for a new one.</ErrorBanner>
        <Link className="btn" to="/forgot">Ask for a new link</Link>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame
      eyebrow="Reset password"
      heading="Choose a new password"
      intro="Use at least 8 characters."
      onSubmit={submit}
    >
      {error && (
        <ErrorBanner>
          {error} <Link className="link-btn" to="/forgot">Ask for a new link</Link>
        </ErrorBanner>
      )}
      <Field id="reset-password" label="New password" error={errors.password}>
        <input type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} />
      </Field>
      <Field id="reset-again" label="New password again" error={errors.again}>
        <input type="password" autoComplete="new-password" value={again} onChange={event => setAgain(event.target.value)} />
      </Field>
      <button className="btn" type="submit" disabled={sending}>
        {sending ? 'Saving...' : 'Save new password'}
      </button>
    </AuthFrame>
  );
}