# NEXORA frontend work

Status: **proposal, awaiting approval** (2026-11-18). No feature code is written yet. Visual direction and two screens are in review; the rest waits for sign-off.

The backend is the source of truth for every permission. The UI hides or shows items by permission name from the permissions endpoint, never by job title or role name.

---

## 1. Visual direction

- **Brand colour:** one teal-green, `#0E6B5C` (dark mode `#5CC2AE`). It is used for the primary button, the active menu item and the wordmark. Status colours are separate: green for done, amber for waiting, blue for information, red for errors.
- **Wordmark:** text only, `NEXORA`, bold, letter-spaced, in the brand colour. No logo file.
- **Type:** Inter, with the system UI stack as fallback. Body 15px, titles 22 to 24px, money figures tabular.
- **Spacing:** 4px base, 16px page gutter, 8px and 12px radii on controls and cards.
- **Surfaces:** warm off-white page, white cards with a 1px border, no shadows.
- **Dark mode:** tokens on `:root`, overridden for `prefers-color-scheme` and `data-theme="dark"`.
- **Layout:** top bar (wordmark, SACCO switcher, user, logout), left menu on desktop, top scrolling menu on phones.

Screenshots (review copies, not shipped code):
- `mockups/login-screen.png` (login, with the error banner state)
- `mockups/loans-officer-screen.png` (loan queue, showing the "already decided" message and the reject reason field)

---

## 2. Team split

| Owner | Scope |
|---|---|
| Ryan | Scaffold (shared files), login, SACCO switcher, join and PIN gate, member dashboard |
| Neo | Backend first (permissions endpoint, roles on member items, loan status filter, `Retry-After` in CORS exposed headers, `sacco-login` rename). Then admin members and join code, then secretary audit |
| Sam | Finance officer screens (accounts, post and reverse, disbursement) and loans officer approvals |
| Stretch | Platform owner screen (`/platform`) |
| Collins | No building. Reviews, runs the role-by-screen test, demo walkthrough, lock |

Each owner adds only their own pages and their own API module.

---

## 3. Shared-file rule

**Shared files belong to the scaffold owner (Ryan).** Everyone else must not edit them directly; they ask Ryan, who makes the change in a small PR.

Shared files:
- `frontend/package.json`, lock file, `vite.config.js`, `eslint.config.js`
- `frontend/src/main.jsx` and the router in `frontend/src/App.jsx`
- `frontend/src/shell/**` (top bar, switcher, menu, layout)
- `frontend/src/lib/api.js` (request wrapper, token refresh, error mapping, `Retry-After` handling)
- `frontend/src/lib/permissions.js` (the permission hook and menu filter)
- `frontend/src/styles/tokens.css` and global CSS

Everyone else owns:
- `frontend/src/pages/<area>/**` (their pages only)
- `frontend/src/api/<area>.js` (their own API module, calling `lib/api.js`)

---

## 4. Routes

Route guards use the **permission names** from `backend/app/security/permissions.py`. Where the first draft named a permission that does not exist, the real one is used.

| Route | Who can open it | Guard (permission) | Owner |
|---|---|---|---|
| `/login` | public | none | Ryan |
| `/join` | public (signed-in users too) | none | Ryan |
| `/join/pin` | after a valid join code | none (UI gate) | Ryan |
| `/saccos` | any signed-in user with a membership | none | Ryan |
| `/s/:saccoId/dashboard` | every active member | `dashboard.view` | Ryan |
| `/s/:saccoId/finance` | finance officer, SACCO admin | `savings.post` | Sam |
| `/s/:saccoId/loans` | loan queue: loans officer, secretary, finance officer, SACCO admin | `loan.view` (decide buttons need `loan.approve`) | Sam |
| `/s/:saccoId/loans/disburse` | finance officer | `loan.disburse` | Sam |
| `/s/:saccoId/members` | secretary, SACCO admin, loans officer (list) | `member.view` (add and titles need `member.manage`) | Neo |
| `/s/:saccoId/audit` | secretary | `audit.view` | Neo |
| `/s/:saccoId/reports` | anyone with `report.view` | `report.view` | Sam |
| `/platform` | platform owner | platform owner flag (no membership) | Stretch |

Notes:
- The first draft used `savings.view_own`, `members.manage`, `audit.view_sacco`, and `loans.approve or loans.review`. None of those exist. `loans.review` is not a permission; the queue uses `loan.view`.
- A member's own loan and repayment screens sit under the dashboard (`loan.request`, `loan.repay`).
- The menu shows an item only if the user holds its permission. A route the user cannot open shows a plain "You do not have access to this page" message, never a blank screen.

---

## 5. Role-by-screen matrix (test spec)

This is the test specification. Collins runs it screen by screen. A cell says what the user **sees**. "Own" means only their own records.

Job titles are the backend's (see `docs/roles-permissions.md` section 5): SACCO admin = `circle_admin`, secretary = `secretary`, finance officer = `finance_officer`, loans officer = `loans_officer`, member = `member`. A platform owner has no membership.

| Screen / action | Permission | SACCO admin | Secretary | Finance officer | Loans officer | Member | Platform owner |
|---|---|---|---|---|---|---|---|
| Own dashboard (balance, transactions, my loans) | `dashboard.view` | yes | yes | yes | yes | yes (own) | no |
| Accounts list (every account) | `savings.view_all` | yes | yes | yes | no | no | no (needs support grant) |
| Post deposit / withdrawal | `savings.post` | yes | no | yes | no | no | no |
| Reverse a savings entry | `savings.reverse` | yes | no | yes | no | no | no |
| Loan queue (read) | `loan.view` | yes | yes | yes | yes | no | no (needs support grant) |
| Approve or reject a loan step | `loan.approve` | **never** | no | no | yes | no | no |
| Disburse an approved loan | `loan.disburse` | **never** | no | yes | no | no | no |
| Request a loan | `loan.request` | no | no | no | no | yes | no |
| Repay a loan | `loan.repay` | no | no | yes | no | yes (own loan) | no |
| Member list | `member.view` | yes | yes | no | yes | no | no |
| Add member by phone, join code, set titles | `member.manage` | yes | no | no | no | no | no |
| Reports | `report.view` | yes | yes | yes | yes | no | no |
| SACCO name and settings | `sacco.view` | yes | yes | yes | yes | yes | yes |
| Rename SACCO | `sacco.update` | yes | no | no | no | no | no |
| SACCO audit log | `audit.view` | **never** | yes | no | no | no | no (needs support grant) |
| Platform: SACCOs, owners, platform audit | platform owner | no | no | no | no | no | yes |

Rules the test must confirm:
1. The SACCO admin never sees Approve, Disburse, or the audit log, even though they can see the queue.
2. Nobody sees a button they cannot use. Read-only roles see no action buttons at all.
3. A member sees only their own loans and transactions. Another member's record answers "not found" (404), never "forbidden".
4. The platform owner cannot read SACCO money without a consent grant.
5. A suspended SACCO shows as locked in the switcher and returns a clear message on every screen (423).

---

## 6. Open question: finance officer and the disburse screen

**The premise in the first draft is out of date.** Finance officers already hold `loan.view`, which lets them read every loan (`backend/app/security/permissions.py`, the `finance_officer` set, and `docs/roles-permissions.md` section 5). So there is no gap to close.

**Recommendation:** do not add a permission. The disburse screen lists approved loans using the existing `loan.view` permission plus the loan status filter that Neo adds (`GET /loans?status=approved`). The screen shows only loans that are approved and not yet disbursed, with a Disburse button gated by `loan.disburse`.

Why not a new permission:
- The matrix already agreed on 2026-11-17 gives finance officers `loan.view`.
- A new permission would be one more backend change before the frontend can start, and it would duplicate what `loan.view` already gives.

If Collins wants finance officers to see only approved loans, that is a narrower backend rule (for example a `loan.view_approved` permission). It is a backend change and should be a decision for Collins, not the frontend team.

---

## 7. Security and PIN gate

- The PIN gate is **UI-level only**. It is kept in memory for the session and is lost on reload. It does not stop an API call.
- The server does not verify PIN proof in release 1. **Server-enforced PIN proof is release 2.** This is recorded in `docs/security-checklist.md`.

---

## 8. Every screen has the same states

- **Loading:** a skeleton or a plain sentence ("Loading your loans…"). Never a blank page.
- **Empty:** a plain sentence saying why nothing is shown and what to do next ("No loans are waiting for a decision.").
- **Error:** a banner with a plain sentence. No raw API errors, status codes, or stack traces are shown.
- **Replayed money request:** a banner saying the earlier request was already recorded and nothing was posted twice.
- **Reversal already done (409):** a message saying the entry was already reversed.
- **Join code errors:** expired, used, wrong, and burned each have their own sentence.

---

## 9. Dependencies and blockers

- Neo's backend items must land before the screens that depend on them: the permissions endpoint (every guard), roles on member items (members screen), the loan status filter (disburse list and queue), and `Retry-After` in the CORS exposed headers (the rate-limit banner).
- Until the permissions endpoint exists, the frontend cannot decide menus and must not guess from role names.

---

## 10. Look and feel rules (agreed after the second design review, 2026-11-18)

The visual reference is the animated prototype, NEXORA Savings Studio (private artifact, link kept by Collins). Port its tokens and components into the scaffold rather than redesigning.

- **Background:** cream field with three drifting colour fields (teal, terracotta, saffron), a soft cursor spotlight and light grain. No plain white page.
- **Surfaces:** frosted glass cards (blur, 1px light edge, soft shadow). 3D tilt only on small cards, never on chart cards.
- **No muddy gradients:** buttons and numbers are solid teal or ink. Colour mixing lives in the background and in chart accents.
- **Wording:** the product word is **SACCO**. Never "Circle" in any label, tab, title or tagline. The member count is labelled "Members".
- **Logo slot:** one `BRAND` constant renders the wordmark everywhere. When Collins supplies the logo, swap that one constant (image or inline SVG). No other file changes.

## 11. Navigation shell

- **Wide screens (64rem and up):** a fixed sidebar with the logo, the permission-filtered menu, and the profile card at the bottom (name, role, Log out). The page scrolls beside it.
- **Phones:** the same sidebar becomes a slide-in drawer from a sticky top bar with a menu button. It closes on route change, scrim tap, or Escape.
- **No visible scrollbars** anywhere. Pages still scroll by wheel, touch and keyboard.
- **Menu items are filtered by permission name** from the permissions endpoint, never by role name.

## 12. Route change: the green wave (replaces every loading spinner)

- Every route change runs the same sequence: the green wave rises, the page swaps underneath, a signature "Nexora" writes itself, the wave lifts away. In-app changes use the short version (about 1.3 s). First open and sign-in use the long version (about 3 s).
- Owned by the scaffold: one `RouteTransition` component wraps the router. Pages never show their own full-page loader.
- Animations on the new page start only after the wave begins to lift (paused while covered).
- Respect `prefers-reduced-motion`: swap instantly, no wave.
- The signature is a script font revealed left to right with a soft mask. A true single-stroke Apple-style "hello" needs traced path data of the real logo; that is a stretch item once the logo exists.

## 13. Landing page and session

- **`/` landing** (public): hero with a live chart preview, features, how a member starts, who sees what, call to action, footer. First open plays the long wave and signature.
- **Stay signed in:** after the first sign-in the user is signed in on that device until they choose Log out. Opening the site while signed in goes straight to their first allowed screen.
- **Decision for Collins (security):** release 1 keeps the refresh token in browser storage so the session survives reloads (7-day rotating refresh token, logout revokes it). The risk is that a script injected into the page could read it. The alternative is memory only, which logs the user out on every reload. Recommendation: browser storage for release 1, no sensitive data on screen without the PIN gate, revisit with release 2 PIN proof. The PIN gate stays in memory.

## 14. Smooth charts, no glitching

- Charts draw once on arrival (left-to-right reveal, bars grow, donut and ring sweep). A window resize redraws them still, with no replay.
- Redraw only when the width changes by more than about 16 px, debounced. Hover never redraws.
- Animate only opacity, translate and clip-path. Never animate layout. Do not animate `transform` on an element that also tilts.
- A chart container reserves its height before drawing so nothing jumps.

## 15. Units rule: use the right unit for the job

| Use | For |
|---|---|
| `rem` | Type sizes, spacing, radii, control sizes (scales with the user's font setting) |
| `%`, `fr`, `minmax()` | Grid and flex layout, widths inside a parent |
| `vw`, `vh`, `dvh`, `vmax` | Page-level sizes (sidebar width, hero height). Prefer `dvh` over `vh` on phones |
| `clamp(min, fluid, max)` | Headings, gaps and padding that must grow and shrink smoothly with the screen |
| `ch` | Reading widths (about 65ch for running text) |
| `em` | Spacing that must follow its own component's font size (inside a button or chip) |
| `px` | Only 1px hairlines, shadows and chart drawing units |

Breakpoints are in `rem` too: 40rem (phone), 56rem (drawer to sidebar), 64rem (wide). Lint rule for review: no `px` for font-size, padding, margin, width or height.

## 16. Four-person, four-hour plan

People: **Ryan** (scaffold, shared files), **Neo** (backend, then two screens), **Sam** (finance and loans), **Collins** (review, tests, demo, sign-off; builds nothing).

| Hour | Ryan | Neo | Sam | Collins |
|---|---|---|---|---|
| 0 to 1 | Scaffold: router, tokens and background, `RouteTransition`, sidebar shell, permission hook, API client with token refresh | Backend adds in this order: permissions endpoint, roles on member items, loan status filter, `Retry-After` in CORS exposed headers, `sacco-login` rename | Loans and finance screens against local mock data in own folder, styled from the prototype | Write the role-by-screen test sheet from section 5. Decide the session storage question in section 13 |
| 1 to 2 | Login, SACCO switcher, join and PIN gate | Admin members screen and join code with 15-minute countdown | Loans officer queue, approve, reject with reason, two-step message | Review each merged page against the prototype and the units rule |
| 2 to 3 | Landing page, member dashboard with charts | Secretary audit (paged, filters, read only) | Finance: post and reverse, unique reference, replay banner, 409 state, disbursement list | Run the matrix on every merged screen. Log defects, do not fix |
| 3 to 4 | Fix defects, phone pass, wire real API where mocks remain | Fix defects, confirm every endpoint the screens call | Fix defects, wire real API | Full role-by-screen run on a phone and a laptop, demo walkthrough, then lock and sign off |

Rules:
- Shared files change only through Ryan (section 3). Others ask in the team channel and carry on with mock data.
- A page is done when it has loading, empty and error states, uses permission names, passes its matrix row, and works at phone width.
- Cut line if time runs short, in this order: platform owner screen, signature polish, landing page extras, reports page. Never cut the permission checks or the role-by-screen run.
- Biggest risk: Ryan carries scaffold, transitions, three public pages and the dashboard. Porting the prototype's CSS and script wholesale is the mitigation. If Ryan falls behind at hour 2, the landing page moves to Sam after the loans screens.

---

## 17. Third design review (2026-11-18): logo, signature, photo, missing pages

**Logo and intro**
- A logo mark (a ring, an N, and a saffron dot) now sits beside the wordmark everywhere. One `BRAND` constant renders it; swap that constant when the final logo arrives.
- On first open and sign-in the mark draws itself, then "Nexora" is written as a monoline pen stroke (one path per stroke, each drawn in order with easing), then the underline. The wave behind it is a deeper teal with grain and a slow glow. This copies the way Apple's hello is built (a single constant-width stroke that draws on), not a font reveal. The stroke paths are hand drawn and approximate; the final signature should be traced from the real logo.
- In-app route changes use the same wave with a faster draw (about 1.1 s).

**Profile photo**
- The avatar (sidebar and phone top bar) opens a viewer with the photo large. The user can choose a photo, which is cropped to a square, or remove it. Initials show when there is no photo.
- Prototype stores the cropped image on the device only. Real app needs an upload endpoint and an `avatar_url` on the user (backend item for Neo, not in release 1 today).

**Menus no longer see through**
- The SACCO switcher and the role menu are solid, not glass. The cause was a glass element nested inside another glass element, which stops the blur. Rule: popovers and dialogs are always solid.

**Pages added after checking the API and permissions**
- **My savings** (`savings.view`, every member): own accounts across SACCOs (`GET /savings/accounts/me`), balance chart, ledger with filters (`GET /savings/accounts/{id}/transactions`).
- **Accounts** (`savings.view_all`: admin, secretary, finance officer): every member's account with search and a ledger view (`GET /admin/saccos/{id}/accounts`).
- **Post money** now also posts **interest** and **fees** (`/interest`, `/fees`), with the same unique-reference rule.
- **Loans, member view:** own loan with repayment progress and schedule, plus the request form.
- **Reports:** adds the member-activity table (`/admin/saccos/{id}/reports/member-activity`).

**Menu by role (from `permissions.py`)**

| Role | Menu |
|---|---|
| Member | Overview, My savings, Loans |
| Loans officer | Overview, My savings, Loans, Members, Reports |
| Finance officer | Overview, My savings, Accounts, Post money, Loans, Reports |
| Secretary | Overview, My savings, Accounts, Loans, Members, Reports, Audit log |
| SACCO admin | Overview, My savings, Accounts, Post money, Loans, Members, Reports |

**Gap found: members cannot deposit in release 1.** Deposits, withdrawals, interest and fees all need `savings.post`, and the backend refuses posting on your own account (403). No endpoint lets a member ask for a deposit or withdrawal. The prototype shows a "Proposed" form that sends a deposit notice or withdrawal request which stays Pending until an officer confirms it. Decision for Collins and Neo: add a small `deposit-requests` endpoint in release 1 (a member creates a request; a finance officer confirms, which posts the real entry), or keep deposits officer-only and show instructions instead. Recommendation: add the endpoint, since a member page with no way to add money will feel broken in the demo.

**Other**
- The login API route is still named `circle-login`; the planned rename to `sacco-login` must land before the sign-in screen is wired.
- The wireframe canvas needs boards for My savings and Accounts and the photo viewer (not yet drawn).

---

## 18. Fourth design review (2026-11-18): signature, logo, every role, back buttons

**Signature.** The word is now the real script letters (Dancing Script Bold, an open font) revealed by a pen path traced along each stroke in writing order. This replaces the hand-drawn strokes that read as "Mexora". Letters are never drawn by hand; the pen path only decides when each part appears. Duration: about 3.8 s on first open and sign-in, 1.25 s on in-app route changes. The font loads from Google Fonts; the intro waits for it (up to 1.6 s).

**Logo.** A lit 3D coin: dark teal disc, a ring that shades from saffron through terracotta to teal, an N built from three beveled pieces with a fold shadow and a gloss highlight, and a saffron node that orbits the ring. It tilts on hover and flips in during the intro. One `BRAND` constant and one `logoSvg()` function render it everywhere; swap those when the final logo arrives.

**Back buttons, only where you drilled in.** Account ledger, member profile, loan details, SACCO detail, platform access read view, join step 2, forgot-password steps, account settings, and the auth pages (back to home or sign in). Top-level menu pages never have one.

**Pages by role, checked against `permissions.py` and `openapi.yaml`**

| Role | Menu |
|---|---|
| Member | Overview, My savings, Loans |
| Loans officer | Overview, My savings, Loans, Members, Reports |
| Finance officer | Overview, My savings, Accounts, Post money, Loans, Reports |
| Secretary | Overview, My savings, Accounts, Loans, Members, Reports, Audit log |
| SACCO admin | Overview, My savings, Accounts, Post money, Loans, Members, Reports, Access requests, SACCO settings |
| Platform owner | Platform overview, SACCOs (list, create, detail, suspend or reopen, loan rules), Owners, Access to SACCOs, Platform audit |
| Everyone | Account settings: photo, email verification, change password, log out here or everywhere |
| Public | Landing, Sign in, Join with code and PIN, Register, Verify email, Forgot and reset password |

Interactions added: a "needs you" strip per role, a live activity feed, 3M, 6M and 12M ranges on the charts, clickable KPI cards, a notification bell, a Ctrl+K jump-to search, and cursor-following 3D on the landing page.

**Intro starts at the first paint (no lag).** The pen paths and the logo are written into the page, not built by script, the signature letters are embedded as a tiny font (6 glyphs, about 2 KB), and the Google Fonts stylesheet loads without blocking. Route changes start writing as the wave rises instead of after it covers the screen. Rule for the scaffold: nothing the transition needs may depend on a network request or on JavaScript having run.

**Fifth review (2026-11-18): timing, stacking, links, small screens**
- **Timing, chosen by feel.** Wave rises in 0.9 s, lifts in 1.1 s (slower out than in, so the new page arrives calmly). The pen takes 4.8 s on first open (long enough to read as handwriting, short enough to stay a greeting) and 1.7 s on route changes, and starts as the wave rises. Cards fade in over 1 s, charts draw over 1.5 s, numbers count up over 1.7 s. Nothing a user does repeatedly is slower than about 2.7 s.
- **Stacking order, lowest to highest:** page cards, sticky top bar (50), sidebar (45 on wide screens), phone header (60), drawer scrim (65), drawer (70), landing menu (80), modals (95), curtain (90 to cover the page, toast 100). The old bug: the top bar and the phone header shared one layer, so the later one painted over the other while the rest of the cards slid under. One rule now: every card goes under the header.
- **Anything that looks like it leads somewhere does.** Dashboard rows (loans to review, recent transactions, live activity, platform activity) and audit lines open the record they describe, for example a platform event "sacco.deactivate Gamma SACCO" opens that SACCO. Pills that read "Open" are real buttons. A row only links when the signed-in role may open that page.
- **Small screens:** every size is rem, %, fr or clamp(); px is used only for 1 px lines and the drawing units inside charts. The landing menu collapses into a menu button instead of hiding its links, and the sidebar keeps every item visible on short screens. An automated check loaded the landing, money, SACCOs and loans screens at 320, 360, 414, 600, 768, 900, 1024, 1180 and 1440 px wide and found nothing wider than the screen.
- **Landing depth:** three cards at different depths follow the cursor (with a slow sway when it rests), the logo coin floats in front, and sections below the first screen rise into view.

**Known gaps for the team**
- Members cannot deposit in release 1 (see section 17). The Proposed notice form needs a backend endpoint.
- The platform owner's "read audit" view is the only read-through shown. Reading members, savings and loans through a grant needs the same screens with a grant banner.
- Loan rule fields (approvals, cap, savings multiple) are drawn from the schema's loan settings; confirm the exact field names with Neo.


---

## Frontend team split (read this first)

The step-by-step work split, pictures, per-person guides and test sheets are in [docs/frontend/README.md](frontend/README.md). That set replaces the older plan in sections 10 to 18 above wherever they differ.
