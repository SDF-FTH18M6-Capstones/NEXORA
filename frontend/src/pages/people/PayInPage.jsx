import '../../styles/neo.css';
import { useState } from 'react';
import { useSession } from '../../lib/session.jsx';
import { useAsync } from '../../lib/useAsync.js';
import { approvePayIn, getPayIn, proposePayIn } from '../../api/payin.js';
import ErrorBanner from '../../components/ErrorBanner.jsx';
import PayInForm from '../../components/PayInForm.jsx';
import PayInView from '../../components/PayInView.jsx';
import { describe } from '../../lib/errors.js';
import { dTime } from '../../lib/format.js';
import { checkPayIn, emptyPayIn, payInBody, payInToForm } from '../../lib/payin.js';
import { Body } from './shared.jsx';

const never = () => false;

export default function PayInPage() {
  const { saccoId, user, toast } = useSession();
  const payIn = useAsync(() => getPayIn(saccoId), [saccoId], { isEmpty: never });
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  async function run(action, done) {
    setNotice(null);
    setBusy(true);
    try {
      await action();
      toast(done);
      payIn.reload();
    } catch (e) {
      if (e.fields) setErrors(e.fields);
      setNotice(e.status === 403 && e.code === 'PAYIN_SAME_OFFICER' ? e.message : describe(e).text);
    } finally {
      setBusy(false);
    }
  }

  function send() {
    const found = checkPayIn(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    run(async () => { await proposePayIn(saccoId, payInBody(form)); setForm(null); }, 'Change sent for approval');
  }

  const live = payIn.data && payIn.data.details;
  const pending = payIn.data && payIn.data.pending;
  const mine = pending && user && pending.proposed_by === user.id;

  return (
    <section className="glass neo-stack loose">
      <div>
        <h2 className="font-serif text-xl">Pay-in details</h2>
        <p className="muted text-sm">Where members pay in. A change goes live only after a second officer approves it, so one person alone cannot point members at a new account.</p>
      </div>
      {notice && <ErrorBanner>{notice}</ErrorBanner>}
      <Body status={payIn.status} error={payIn.error} reload={payIn.reload}>
        {live ? <PayInView details={live} /> : <ErrorBanner kind="info">Pay-in details not set. Members cannot send deposit or withdrawal requests until two officers set them.</ErrorBanner>}

        {pending && (
          <div className="neo-stack">
            <h3 className="font-serif text-lg">A change is waiting for approval</h3>
            <PayInView details={pending.values} showDate={false} />
            <p className="muted text-sm">Proposed {dTime(pending.proposed_at)}.</p>
            {mine ? (
              <p className="muted text-sm">You proposed this change. A different officer must approve it. Until then members still see the details above.</p>
            ) : (
              <div>
                <button type="button" className="btn" disabled={busy} onClick={() => run(() => approvePayIn(saccoId, pending.id), 'Pay-in details are now live')}>
                  Check the numbers, then approve
                </button>
              </div>
            )}
          </div>
        )}

        {!form && <div><button type="button" className="btn ghost" onClick={() => { setErrors({}); setForm(live ? payInToForm(live) : emptyPayIn()); }}>{live ? 'Propose a change' : 'Set the pay-in details'}</button></div>}
        {form && (
          <form className="neo-stack" noValidate onSubmit={event => { event.preventDefault(); send(); }}>
            {pending && <p className="muted text-sm">Sending a new change replaces the one waiting for approval.</p>}
            {errors._ && <div className="field-msg" role="alert">{errors._}</div>}
            <PayInForm value={form} onChange={value => { setForm(value); setErrors({}); }} errors={errors} disabled={busy} />
            <div className="flex flex-wrap gap-2">
              <button className="btn" type="submit" disabled={busy}>Send for a second officer's approval</button>
              <button className="btn ghost" type="button" disabled={busy} onClick={() => setForm(null)}>Cancel</button>
            </div>
          </form>
        )}
      </Body>
    </section>
  );
}
