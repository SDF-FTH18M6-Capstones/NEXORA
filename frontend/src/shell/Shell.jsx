/* Shell: fixed sidebar + sticky top bar + scrolling content. The router (R3) passes `path` and the page as children.
 * LogoDefs is NOT rendered here: render it once in App.jsx (the harness already does). */
import { useSession } from '../lib/session.jsx';
import { menuFor } from '../lib/perms.js';
import Sidebar from './Sidebar.jsx';
import Topbar from './Topbar.jsx';

export default function Shell({ path, title, children, ...topbarActions }) {
  const { perms } = useSession();
  const current = menuFor(perms).find(r => r.path === path);
  return (
    <div className="app on">
      <Sidebar path={path} />
      <div className="content">
        <Topbar title={title || (current ? current.title : '')} {...topbarActions} />
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}