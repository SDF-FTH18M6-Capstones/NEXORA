import { lazy, Suspense, useMemo, useRef } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom';
import ErrorPage from './components/ErrorPage.jsx';
import { ROLES, ROUTES, homeFor } from './lib/perms.js';
import { SessionContext } from './lib/session.jsx';
import RequireAuth from './shell/RequireAuth.jsx';
import { PAGE_IMPORTS } from './shell/pages.js';

function Placeholder({ title }) {
  return (
    <div className="glass grid min-h-[30vh] content-center gap-2 p-6 text-center">
      <h1 className="font-serif">{title}</h1>
      <p className="text-muted">This page is being built.</p>
    </div>
  );
}

function makeLazyPage(path, title) {
  return lazy(async () => {
    const loader = PAGE_IMPORTS[path];
    if (!loader) return { default: () => <Placeholder title={title} /> };
    try {
      return await loader();
    } catch {
      return { default: () => <Placeholder title={title} /> };
    }
  });
}

function PublicPlaceholder({ title }) {
  return (
    <main className="mx-auto max-w-2xl p-6">
      <Placeholder title={title} />
    </main>
  );
}

function AppRouter() {
  const routerNavigate = useNavigate();
  const openRef = useRef('');
  const role = 'admin';
  const perms = ROLES[role].perms;

  const session = useMemo(() => ({
    user: {
      id: 'ryan-r3',
      email: 'admin@nexora.local',
      name: 'R3 preview',
      initials: 'R3',
    },
    role,
    perms,
    can: permission => perms.includes(permission),
    saccoId: 1,
    sacco: { id: 1, name: 'Preview SACCO', status: 'active' },
    navigate: (to, options = {}) => {
      openRef.current = options.open || '';
      routerNavigate(to);
    },
    takeOpen: kind => {
      const open = openRef.current;
      if (open.startsWith(kind + ':')) {
        openRef.current = '';
        return open.slice(kind.length + 1);
      }
      return null;
    },
    toast: () => {},
  }), [routerNavigate, role, perms]);

  const publicRoutes = [
    ['login', 'Sign in'],
    ['register', 'Create an account'],
    ['verify', 'Verify your email'],
    ['forgot', 'Forgot password'],
    ['reset', 'Reset password'],
  ];
  const protectedExtras = [
    { path: 'join', title: 'Join a SACCO', checkPermission: false },
    { path: 'enter', title: 'Enter your SACCO', checkPermission: false },
    { path: 'account', title: 'Account settings', checkPermission: true },
    'styleguide',
  ];

  return (
    <SessionContext.Provider value={session}>
      <Suspense fallback={<div className="glass p-6 text-muted">Loading...</div>}>
        <Routes>
          <Route path="/" element={<Navigate to={'/' + homeFor(perms)} replace />} />

          {publicRoutes.map(([path, title]) => (
            <Route
              key={path}
              path={'/' + path}
              element={<PublicPlaceholder title={title} />}
            />
          ))}

          {ROUTES.map(route => {
            const Page = makeLazyPage(route.path, route.title);
            return (
              <Route
                key={route.path}
                path={'/' + route.path}
                element={
                  <RequireAuth path={route.path} title={route.title}>
                    <Page />
                  </RequireAuth>
                }
              />
            );
          })}

          {protectedExtras.map(extra => {
            if (typeof extra === 'string') {
              const Page = makeLazyPage(extra, 'Style guide');
              return (
                <Route
                  key={extra}
                  path={'/' + extra}
                  element={
                    <RequireAuth path={extra} title="Style guide">
                      <Page />
                    </RequireAuth>
                  }
                />
              );
            }
            const Page = makeLazyPage(extra.path, extra.title);
            return (
              <Route
                key={extra.path}
                path={'/' + extra.path}
                element={
                  <RequireAuth
                    path={extra.path}
                    title={extra.title}
                    checkPermission={extra.checkPermission}
                  >
                    <Page />
                  </RequireAuth>
                }
              />
            );
          })}

          <Route
            path="*"
            element={
              <RequireAuth path={null} title="">
                <ErrorPage
                  code="404"
                  onAction={action => {
                    if (action === 'home') session.navigate('/' + homeFor(perms));
                    if (action === 'back') session.navigate(-1);
                  }}
                />
              </RequireAuth>
            }
          />
        </Routes>
      </Suspense>
    </SessionContext.Provider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}
