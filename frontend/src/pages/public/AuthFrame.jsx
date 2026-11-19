export default function AuthFrame({ eyebrow, heading, intro, onSubmit, children }) {
  return (
    <main className="auth">
      <div className="auth-inner">
        <div className="auth-copy">
          <h1 className="serif">{heading}</h1>
          {intro && <p>{intro}</p>}
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