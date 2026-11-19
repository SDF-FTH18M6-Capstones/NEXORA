import { lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import ErrorPage from './components/ErrorPage.jsx';
import { LogoDefs } from './components/Logo.jsx';
import { describe } from './lib/errors.js';
import { can as canPermission, homeFor, ROUTES } from './lib/perms.js';
import { clearTokens, onSessionEnded } from './lib/http.js';
import { SessionContext, useSession } from './lib/session.jsx';
import { restoreSession, selectSacco, signIn, signOut } from './api/session.js';
import RequireAuth from './shell/RequireAuth.jsx';
import RouteTransition from './shell/RouteTransition.jsx';
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

function StartRoute() {
  const { user, perms } = useSession();
  return <Navigate to={user ? '/' + homeFor(perms) : '/login'} replace />;
}

function LogoutRoute() {
  const { logout } = useSession();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void logout();
  }, [logout]);

  return <main className="p-6 text-muted">Signing out...</main>;
}

function NotFoundRoute() {
  const { navigate, perms } = useSession();
  return (
    <RequireAuth path={null} title="">
      <ErrorPage
        code="404"
        onAction={action => {
          if (action === 'home') navigate('/' + homeFor(perms));
          if (action === 'back') navigate(-1);
        }}
      />
    </RequireAuth>
  );
}

function SessionProvider({ children }) {
  const routerNavigate = useNavigate();
  const location = useLocation();
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);
  const [restoreError, setRestoreError] = useState(null);
  const [sessionEnded, setSessionEnded] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [panelRequest, setPanelRequest] = useState('');
  const openRef = useRef('');
  const toastTimer = useRef(null);
  const routerNavigateRef = useRef(routerNavigate);
  const pendingReturnToRef = useRef('');

  useEffect(() => {
    routerNavigateRef.current = routerNavigate;
  }, [routerNavigate]);

  useEffect(() => {
    if (session) {
      pendingReturnToRef.current = '';
      return;
    }

    if (!['/', '/login', '/register', '/verify', '/forgot', '/reset', '/logout'].includes(location.pathname)) {
      pendingReturnToRef.current = location.pathname + location.search;
    }
  }, [location.pathname, location.search, session]);

  const navigate = useCallback((to, options = {}) => {
    if (typeof to === 'number') {
      routerNavigate(to);
      return;
    }
    const { open, ...navigationOptions } = options;
    openRef.current = open || '';
    setPanelRequest(open || '');
    routerNavigate(to, navigationOptions);
  }, [routerNavigate]);

  const login = useCallback(async (email, password, selectedRole) => {
    const nextSession = await signIn(email, password, selectedRole);
    setSession(nextSession);
    setSessionEnded(false);
    setRestoreError(null);
    const stateTarget = location.state && location.state.from;
    const target = typeof stateTarget === 'string' && stateTarget !== '/login'
      ? stateTarget
      : pendingReturnToRef.current;
    pendingReturnToRef.current = '';
    navigate(
      typeof target === 'string' ? target : '/' + homeFor(nextSession.perms),
      { replace: true },
    );
  }, [location.state, navigate]);

  const logout = useCallback(async () => {
    await signOut();
    setSession(null);
    setSessionEnded(false);
    pendingReturnToRef.current = '';
    navigate('/login', { replace: true });
  }, [navigate]);

  const switchSacco = useCallback(async saccoId => {
    const nextSession = await selectSacco(session, saccoId);
    setSession(nextSession);
    navigate('/overview');
  }, [session, navigate]);

  const clearSessionEnded = useCallback(() => setSessionEnded(false), []);
  const clearPanelRequest = useCallback(() => {
    openRef.current = '';
    setPanelRequest('');
  }, []);
  const takeOpen = useCallback(kind => {
    const value = openRef.current;
    if (value.startsWith(kind + ':')) {
      openRef.current = '';
      return value.slice(kind.length + 1);
    }
    return null;
  }, []);
  const toast = useCallback((text, kind) => {
    setToastMessage({ text, kind });
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToastMessage(null), 2800);
  }, []);

  useEffect(() => {
    let active = true;
    onSessionEnded(() => {
      clearTokens();
      if (!active) return;
      setSession(null);
      setSessionEnded(true);
      setReady(true);
      routerNavigateRef.current('/login', { replace: true });
    });

    restoreSession()
      .then(restored => {
        if (!active) return;
        setSession(restored);
        setReady(true);
      })
      .catch(error => {
        if (!active) return;
        if (error && error.status === 401) {
          clearTokens();
          setSessionEnded(true);
          routerNavigateRef.current('/login', { replace: true });
        } else {
          setRestoreError(error);
        }
        setReady(true);
      });

    return () => {
      active = false;
      onSessionEnded(() => {});
      window.clearTimeout(toastTimer.current);
    };
  }, []);

  const can = useCallback(permission => (
    session ? canPermission(session.perms, permission) : false
  ), [session]);
  const value = useMemo(() => ({
    user: session ? session.user : null,
    role: session ? session.role : null,
    perms: session ? session.perms : [],
    can,
    saccoId: session ? session.saccoId : null,
    sacco: session ? session.sacco : null,
    saccos: session ? session.saccos : [],
    panelRequest,
    clearPanelRequest,
    navigate,
    switchSacco,
    takeOpen,
    toast,
    login,
    logout,
    sessionEnded,
    clearSessionEnded,
  }), [session, can, navigate, switchSacco, takeOpen, toast, login, logout, sessionEnded, clearSessionEnded, panelRequest, clearPanelRequest]);

  return (
    <SessionContext.Provider value={value}>
      <LogoDefs />
      {ready
        ? restoreError
          ? <ErrorPage code={describe(restoreError, { mode: 'page' }).page || '500'} onAction={action => {
            if (action === 'retry') window.location.reload();
            if (action === 'login') navigate('/login');
          }} />
          : children
        : <main className="p-6 text-muted">Restoring your session...</main>}
      <div
        className={`toast${toastMessage ? ' show' : ''}${toastMessage && toastMessage.kind === 'err' ? ' err' : ''}`}
        role="status"
      >
        {toastMessage ? toastMessage.text : ''}
      </div>
    </SessionContext.Provider>
  );
}

function AppRouter() {
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
  const LoginPage = makeLazyPage('login', 'Sign in');

  return (
    <SessionProvider>
      <Routes>
        <Route element={<RouteTransition />}>
          <Route path="/" element={<StartRoute />} />
          <Route path="/logout" element={<LogoutRoute />} />

          {publicRoutes.map(([path, title]) => (
            <Route
              key={path}
              path={'/' + path}
              element={path === 'login' ? <LoginPage /> : <PublicPlaceholder title={title} />}
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

          <Route path="*" element={<NotFoundRoute />} />
        </Route>
      </Routes>
    </SessionProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRouter />
    </BrowserRouter>
  );
}
