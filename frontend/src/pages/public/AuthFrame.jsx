/* The sign-in spread leaves a wide left column. A short list of what the app
 * holds fills it, so the copy and the card read as one page instead of two
 * islands with a gap of cream between them. Hidden on a phone, where it would
 * only push the form below the fold. */
export function AuthPoints() {
  return (
    <ul className="auth-points">
      <li>
        <strong>Savings</strong>
        <span>Every deposit and withdrawal is recorded against a member.</span>
      </li>
      <li>
        <strong>Loans</strong>
        <span>Members ask, officers review, and repayments are tracked.</span>
      </li>
      <li>
        <strong>Records</strong>
        <span>Posted entries are never edited. A correction is a new entry.</span>
      </li>
    </ul>
  );
}

export default function AuthFrame({ eyebrow, heading, intro, onSubmit, extra, children }) {
  return (
    <main className="auth">
      <div className="auth-inner">
        <div className="auth-copy">
          <h1 className="serif">{heading}</h1>
          {intro && <p>{intro}</p>}
          {extra}
        </div>
        <form
          className="glass auth-card"
          noValidate
          onSubmit={onSubmit || (event => event.preventDefault())}
        >
          <div className="eyebrow">{eyebrow}</div>
          {children}
        </form>
      </div>
    </main>
  );
}