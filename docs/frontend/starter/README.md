# Starter kit

Shared files every person copies into `frontend/` in the Common setup Step 3. **Nobody edits them on their own branch.** Collins owns this folder.

The frontend is **React 19 (JavaScript) with Tailwind CSS v4**, built with Vite.

| Folder / file | What it is |
|---|---|
| `lib/http.js` | the only thing that talks to the network; token, one refresh, `ApiError`, mock switch (`MOCK`, `mockDelay`) |
| `lib/errors.js` | `describe(err, {mode, context})`: failure to sentence and error-page code |
| `lib/session.jsx` | `SessionContext` and `useSession()` |
| `lib/useAsync.js` | `{status, data, error, reload}` with loading, ready, empty, error |
| `lib/perms.js` | roles, permissions, routes (including `deposit`, `withdraw`, `requests`), `menuFor`, `guardRoute`, `homeFor` |
| `lib/format.js` | money (`kesFromMinor`, `toMinor`, `newReference`), dates, `countUp` |
| `lib/charts.js` | `renderLine/Bars/Donut/Ring` (no chart library) |
| `lib/appearance.js` | colour theme, font and text size: load, save, apply (localStorage key `nexora.appearance`) |
| `components/` | `ErrorBanner`, `ErrorPage` (no logo), `Field`, `BackButton`, `States` (`Loading`, `Empty`), `ChartBox`, `StatusChip`, `Logo` (sidebar and public pages only), `AppearanceCard` |
| `mocks/data.js` | sample data for the harness, including `paymentRequests`, `payIn`, `myBalance` |
| `styles/nexora.css`, `nexora-2.css` | the prototype's CSS: shared classes (`.glass`, `.btn`, `.chip`, `.field`, `.banner`) and the Appearance themes (bottom of `nexora-2.css`) |
| `styles/tailwind.css` | Tailwind v4 with the NEXORA colours and fonts as theme tokens (`bg-cream`, `text-ink`, `font-serif`) |
| `vite.config.js` | Vite config with the Tailwind plugin (Collins commits it to the `frontend` branch) |
| `dev.html`, `dev/` | the dev harness; add only `dev/registry.<yourname>.js` |