import { Navigate, useLocation } from 'react-router-dom';
import ErrorPage from '../components/ErrorPage.jsx';
import { guardRoute, homeFor } from '../lib/perms.js';
import { useSession } from '../lib/session.jsx';
import Shell from './Shell.jsx';

export default function RequireAuth({ path, title, children, checkPermission = true }) {
  const location = useLocation();
  const { user, perms, navigate } = useSession();

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  }

  const denied = path && checkPermission ? guardRoute(perms, path) : (path ? null : '404');

  function onAction(action) {
    if (action === 'home') navigate('/' + homeFor(perms));
    else if (action === 'back') navigate(-1);
    else if (action === 'login') navigate('/login');
    else if (action === 'landing') navigate('/');
    else if (action === 'account') navigate('/account');
  }

  return (
    <Shell path={path} title={title}>
      {denied ? <ErrorPage code={denied} onAction={onAction} /> : children}
    </Shell>
  );
}
