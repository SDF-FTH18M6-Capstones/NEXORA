import { Link } from 'react-router-dom';
import AppearanceCard from '../../components/AppearanceCard.jsx';

export default function MySettings() {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-muted">Choose how Nexora looks for you.</p>
      </header>

      <AppearanceCard />

      <section className="glass flex flex-col gap-3 p-6">
        <h2 className="font-serif">Account</h2>
        <p className="text-muted">Change your password or sign out everywhere.</p>
        <div>
          <Link className="btn" to="/account">Open account settings</Link>
        </div>
      </section>
    </div>
  );
}