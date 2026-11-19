# AI README: COLLINS (the checker; builds nothing)

Give this file to your AI assistant together with `docs/frontend/04-collins.md` and the Master file. The AI helps Collins **verify**. It writes **no screen code** and never edits `frontend/src/**` (except the one-time Tailwind setup in C1).

## 0. Project in one paragraph
NEXORA is a SACCO (a "circle") savings and loans app. Frontend: **React 19 (JavaScript) + Tailwind CSS v4 + Vite** in `frontend/`, built by Ryan (foundation, front door, My settings), Sam (money, loans, Deposit/Withdraw/Requests), Neo (backend additions incl. payment requests, People pages, Add a member, Platform area). The prototype (https://claude.ai/artifact/SPDZB7PDFbRt9wDJ3cvxH7, `docs/frontend/prototype/`) and screenshots (`docs/frontend/images/`) are the right answer by eye. Human docs: `pdf/NEXORA-Frontend-MASTER.pdf`, `pdf/04-Collins.pdf`.

## 1. Rules for this role
- Collins owns `docs/frontend/*`, the starter kit in `docs/frontend/starter/`, `docs/frontend/done/collins/`, and the `frontend` branch. Only Collins merges PRs and merges `frontend` into `main`; tag `frontend-v1`.
- A bug in a shared starter file is fixed **in `docs/frontend/starter/` only**, announced ("starter updated: <file>, <what>") and everyone copies that file. A bug in a teammate's file goes on the Fix list with file, page, role and screenshot.
- Judge by evidence (screens, test output), never by intention. Anything not verified is reported as not verified.

## 2. Tasks
**C1 Before anyone starts**: `git checkout main && git pull && git checkout -b frontend && git push -u origin frontend`. In `frontend/`: `npm install tailwindcss @tailwindcss/vite`; replace `vite.config.js` with `docs/frontend/starter/vite.config.js`; copy the starter into `frontend/` (dev.html; dev, lib, components, mocks, styles into `src/`); do COMMON-SETUP Steps 0-9 yourself; `npm run build` passes; harness shows the sample page. Commit `package.json`, `package-lock.json`, `vite.config.js` to `frontend` and push. Post "frontend branch is ready with Tailwind. Start the Common setup."
**C2 Sheets**: copy sheets A-E and the demo script from `04-collins.md` into `docs/frontend/done/collins/sheets.md` and `demo.md`.
**C3 Review each PR** in order: checklist fully ticked; "Files changed" only the owner's folders (any shared file change is rejected: "move this to the starter via Collins"); search red flags: `role ===`, `fetch(`, `console.log`, `alert(`, bare `px` sizes (allowed: 1px borders, shadows), hex colours in `className` (search `\[#`), a logo or image inside an error page; `npm install && npm run build && npm run lint` pass; run the owner's pages in the harness for all roles and all four states; owner's photos present; merge into `frontend`, then check `npm run dev` still starts the real shell. For Neo's PR also `pytest` green and the summary line pasted.
**C4 Final tests on merged `frontend`** in the real app (`VITE_MOCK=1 npm run dev`): Sheet A (role by screen, incl. `/savings` member only, `/deposit` `/withdraw` member only, `/requests` finance+admin, `/add-member` admin only, `/account` and `/my-settings` everyone), Sheet B (every error, no logo), Sheet C (375/768/1280, every page), Sheet D (member requests, officer queue, Add a member, appearance for all six roles), Sheet E (account, join code, circle PIN).
**C5 Demo and lock**: run the 6-minute demo once without stopping; if clean merge `frontend` into `main`, `git tag frontend-v1`, push the tag.

## 3. What "correct" means (check against this)
- **Menus**: Member: Overview, My savings, Deposit, Withdraw, Loans, My settings. Loans officer: Overview, Loans, Members, Reports, My settings. Finance: Overview, Accounts, Post money, Requests, Loans, Reports, My settings. Secretary: Overview, Accounts, Loans, Members, Reports, Audit log, My settings. SACCO admin: Overview, Accounts, Post money, Requests, Loans, Members, Add a member, Reports, Access requests, SACCO settings, My settings. Platform owner: Platform overview, SACCOs, Owners, Access to SACCOs, Platform audit, My settings. Staff have no My savings/Deposit/Withdraw and no "My account" tab on Overview.
- **Errors**: 401/403/404/423/429/500/offline are code, title, one sentence, buttons; no logo; inside the shell (401 without). Member opening `/accounts` = 403; suspended SACCO = 423 except `account` and `my-settings`; unknown route = 404.
- **Getting in**: account (sign in/create/verify) gives no circle; Join with code (6 digits, once, 15 min) then 4-digit PIN; Enter your circle PIN screen; "not in a circle yet" page; chooser for several circles; mock PIN `1234`, codes `123456` ok / `000000` expired / `111111` used / `222222` burned; PIN-step timeout 10 min; 5 wrong PINs = 15 min lock; platform owners create circles only.
- **Requests**: a request is not money; Confirm posts the ledger entry; Reject needs a reason; nobody decides their own; over-balance withdrawal cannot be confirmed; one reference per submit, retry safe.
- **Appearance**: 10 themes, 6 fonts, 3 sizes, per person (`nexora.appearance:<userId>`), survives reload and sign-out, other tab follows; Member's Midnight never shows for the admin on the same computer; coin, wave and sign-in waves follow the theme; every word, icon and button visible in every theme (Lighthouse Accessibility in Cream, Saffron, Ink, Midnight: no contrast warnings); print black on white; Large text at 375 px cuts nothing.
- **Quality**: no emoji or slop; rem/%/vw/clamp; no hex in `className`; no `role ===`; no `fetch(` in pages; money minor units.

## 4. Fix list (`done/collins/fixes.md`)
`| # | Owner | Page / role | What is wrong | Screenshot | Fixed? |`. Send each owner their rows; re-test only those rows after they push.

## 5. Open decisions Collins must make
Real M-Pesa paybill and bank pay-in details (Deposit page uses sample `payIn`); whether staff other than the SACCO admin may add members (`member.manage` is admin-only today); how a staff person who also saves is handled (one role per circle); PIN reset stays admin re-add in release 1.

## 6. Release gate (all must be true before locking)
- [ ] `frontend` created with Tailwind; Common setup verified by doing it; starter builds; every starter fix announced.
- [ ] All three PRs (Ryan, Sam, Neo) reviewed with the red-flag search and merged.
- [ ] `npm run build` and `npm run lint` pass; backend `pytest` green.
- [ ] Sheets A, B, C, D, E fully ticked; demo ran clean once.
- [ ] Fix list empty or each remaining row accepted as a Known gap in the Master file.
- [ ] `frontend` merged into `main` by Collins only; tag `frontend-v1` pushed.
- [ ] Post "Frontend locked, tag frontend-v1" with the link to `done/collins/sheets.md`.
