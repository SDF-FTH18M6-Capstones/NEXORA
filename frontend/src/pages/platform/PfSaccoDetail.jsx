import '../../styles/neo.css';
import { useState } from 'react';
import { useSession } from '../../lib/session.jsx';
import { useAsync } from '../../lib/useAsync.js';
import {
  getSacco,
  listSaccoAdmins,
  inviteFirstAdmin,
  inviteFirstAdminByEmail,
  setSaccoActive,
} from '../../api/platform.js';
import ErrorBanner from '../../components/ErrorBanner.jsx';
import Field from '../../components/Field.jsx';
import StatusChip from '../../components/StatusChip.jsx';
import { Body, Confirm } from '../people/shared.jsx';
import { when } from '../people/data.js';
import { describe } from '../../lib/errors.js';

const ADMIN_STATUS = {
  active: 'Active',
  invited: 'Invited',
  declined: 'Declined',
  inactive: 'Inactive',
};

export default function PfSaccoDetail({ saccoId, onBack }) {
  const { toast } = useSession();
  const { status, data, error, reload } = useAsync(() => getSacco(saccoId), [saccoId]);
  // A SACCO may already hold an admin, or still hold none: ask before offering.
  const admins = useAsync(() => listSaccoAdmins(saccoId), [saccoId], {
    isEmpty: () => false,
  });
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [adminChannel, setAdminChannel] = useState('phone');
  const [adminPhone, setAdminPhone] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminResult, setAdminResult] = useState(null);
  const [adminError, setAdminError] = useState(null);

  async function flip() {
    const turningOff = data.status === 'active';
    setAsking(false);
    setBusy(true);
    setNotice(null);
    try {
      await setSaccoActive(data.id, !turningOff);
      toast(turningOff ? 'SACCO suspended' : 'SACCO activated');
      reload();
    } catch (e) {
      setNotice(describe(e, { context: 'settings' }).text);
    } finally {
      setBusy(false);
    }
  }

  async function inviteAdmin(event) {
    event.preventDefault();
    setAdminError(null);
    setAdminResult(null);
    setBusy(true);
    try {
      // By phone the owner hands the code over; by email NEXORA mails it, so the
      // response carries no code and nobody types someone else's invitation.
      const made = adminChannel === 'phone'
        ? await inviteFirstAdmin(saccoId, adminPhone)
        : await inviteFirstAdminByEmail(saccoId, adminEmail.trim());
      setAdminResult(made);
      setAdminPhone('');
      setAdminEmail('');
      admins.reload();
    } catch (e) {
      setAdminError(describe(e, { context: 'member' }).text);
    } finally {
      setBusy(false);
    }
  }

  const adminInviteReady = adminChannel === 'phone'
    ? Boolean(adminPhone.trim())
    : Boolean(adminEmail.trim());

  const knownAdmins = (admins.data && admins.data.admins) || [];

  return (
    <section className="glass neo-stack">
      <button type="button" className="back" onClick={onBack}>← Back to SACCOs</button>
      <Body
        status={status}
        error={error}
        reload={reload}
        emptyTitle="This SACCO is gone."
        emptyHint="Go back to the list."
      >
        {data && (
          <>
            <div className="neo-search">
              <div className="grow">
                <div className="eyebrow">SACCO</div>
                <h2 className="font-serif text-xl">{data.name}</h2>
                <p className="muted text-sm">
                  {data.member_count} member{data.member_count === 1 ? '' : 's'} · {data.currency} · created {when(data.created_at)}
                </p>
              </div>
              <StatusChip status={data.status === 'active' ? 'Active' : 'Suspended'} />
            </div>
            {notice && <ErrorBanner>{notice}</ErrorBanner>}

            <div className="neo-stack tight">
              <b>SACCO admin</b>
              {knownAdmins.length === 0 ? (
                <p className="muted text-sm">
                  {admins.status === 'error'
                    ? 'The admin list could not be read. Try again below.'
                    : 'No admin yet. Nobody in this SACCO can add members or set titles until you invite one — and you can do it now, whenever the SACCO was created.'}
                </p>
              ) : (
                knownAdmins.map(admin => (
                  <p key={admin.id} className="text-sm flex flex-wrap items-center gap-2">
                    <StatusChip status={ADMIN_STATUS[admin.status] || 'Inactive'} />
                    <span>{admin.email || admin.phone}</span>
                    <span className="muted">
                      {admin.status === 'invited'
                        ? `invited ${when(admin.created_at)} · code not used yet`
                        : admin.status === 'declined'
                          ? `declined the invitation ${when(admin.created_at)}`
                          : `since ${when(admin.created_at)}`}
                    </span>
                  </p>
                ))
              )}
              <form className="neo-stack tight" onSubmit={inviteAdmin}>
                <div className="neo-stack tight">
                  <b className="lb-s">Invite by</b>
                  <div className="seg seg-fit" role="group" aria-label="Invite by">
                    <button
                      type="button"
                      aria-pressed={adminChannel === 'phone'}
                      disabled={busy}
                      onClick={() => setAdminChannel('phone')}
                    >
                      Phone
                    </button>
                    <button
                      type="button"
                      aria-pressed={adminChannel === 'email'}
                      disabled={busy}
                      onClick={() => setAdminChannel('email')}
                    >
                      Email
                    </button>
                  </div>
                  <p className="muted text-sm">
                    {adminChannel === 'phone'
                      ? 'You get a code to hand over in person.'
                      : 'NEXORA emails them a one-time code.'}
                  </p>
                </div>
                {adminChannel === 'phone' ? (
                  <Field id="sacco-admin-phone" label="Their phone number" error={adminError}>
                    <input
                      id="sacco-admin-phone"
                      inputMode="tel"
                      value={adminPhone}
                      onChange={e => setAdminPhone(e.target.value)}
                      placeholder="0712 345 678"
                      disabled={busy}
                    />
                  </Field>
                ) : (
                  <>
                    <Field id="sacco-admin-email" label="Their email" error={adminError}>
                      <input
                        id="sacco-admin-email"
                        type="email"
                        autoComplete="off"
                        value={adminEmail}
                        onChange={e => setAdminEmail(e.target.value)}
                        placeholder="name@sacco.co.ke"
                        disabled={busy}
                      />
                    </Field>
                    <p className="muted text-sm">
                      They need a NEXORA account whose email they have already confirmed.
                    </p>
                  </>
                )}
                <div>
                  <button
                    type="submit"
                    className="btn small"
                    disabled={busy || !adminInviteReady}
                  >
                    {busy
                      ? 'Making the code…'
                      : adminChannel === 'phone'
                        ? 'Make their join code'
                        : 'Email them a join code'}
                  </button>
                </div>
              </form>
              {adminResult && adminResult.join_code && (
                <>
                  <div className="neo-code">{adminResult.join_code}</div>
                  <ErrorBanner kind="info">
                    Send this to {adminResult.phone} as SACCO admin. It works once and lasts 15 minutes.
                  </ErrorBanner>
                </>
              )}
              {adminResult && !adminResult.join_code && (
                <ErrorBanner kind="info">
                  An invitation email with a one-time code was sent to {adminResult.email}. It works
                  once and lasts 15 minutes.
                </ErrorBanner>
              )}
            </div>

            <div>
              <button type="button" className="btn" disabled={busy} onClick={() => setAsking(true)}>
                {data.status === 'active' ? 'Deactivate' : 'Activate'}
              </button>
              {asking && (
                <Confirm
                  question={data.status === 'active'
                    ? "This locks the SACCO's records for all its members."
                    : 'This lets the members back in with their existing PINs.'}
                  yes={data.status === 'active' ? 'Deactivate it' : 'Activate it'}
                  no={data.status === 'active' ? 'Keep it active' : 'Leave it suspended'}
                  busy={busy}
                  onNo={() => setAsking(false)}
                  onYes={flip}
                />
              )}
            </div>
            <p className="muted text-sm">
              You never see this SACCO's money. Balances, accounts and loans stay with its own staff.
            </p>
          </>
        )}
      </Body>
    </section>
  );
}
