/* shared.jsx: the four states of a card, in one place for Neo's pages. */
import { Loading, Empty } from '../../components/States.jsx';
import ErrorBanner from '../../components/ErrorBanner.jsx';
import ErrorPage from '../../components/ErrorPage.jsx';
import { describe } from '../../lib/errors.js';

export function Body({ status, error, reload, emptyTitle, emptyHint, children }) {
  if (status === 'loading') return <Loading lines={4} />;
  if (status === 'error') {
    const shown = describe(error, { mode: 'page' });
    if (shown.page) return <ErrorPage code={shown.page} />;
    return <ErrorBanner onRetry={reload}>{shown.text}</ErrorBanner>;
  }
  if (status === 'empty') return <Empty title={emptyTitle} hint={emptyHint} />;
  return children;
}
