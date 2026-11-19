/* Top bar: page title, search, bell, SACCO switcher. Shared classes: .topbar .switcher .icon-btn .kbd. Sticky, z-index 50 (nexora-2.css).
 * onSearch / onBell / onSwitcher are wired in R6; until then the buttons do nothing. */
import { useSession } from '../lib/session.jsx';
import Icon from './Icon.jsx';

const none = () => {};

export default function Topbar({ title, onSearch = none, onBell = none, onSwitcher = none }) {
  const { sacco } = useSession();
  return (
    <header className="topbar glass">
      <h1 className="page-title min-w-0 flex-1 truncate">{title}</h1>

      <button type="button" className="switcher" onClick={onSearch} aria-label="Search">
        <Icon name="search" className="size-4 shrink-0" />
        <span className="hidden md:inline">Search</span>
        <span className="hidden lg:inline"><kbd className="kbd">Ctrl K</kbd></span>
      </button>

      <button type="button" className="icon-btn" onClick={onBell} aria-label="Notifications">
        <Icon name="bell" />
      </button>

      {sacco && (
        <div className="switcher-wrap">
          <button type="button" className="switcher" onClick={onSwitcher} aria-haspopup="menu" aria-label={`Circle: ${sacco.name}. Switch circle`}>
            <span className="max-w-40 truncate">{sacco.name}</span>
            <Icon name="chevron" className="size-4 shrink-0" />
          </button>
        </div>
      )}
    </header>
  );
}