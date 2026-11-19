# 04 Collins: the checker (builds nothing)

Same format as the files of Ryan, Neo and Sam. First read the Master file once, then do the **Common setup** (Part 1, Steps 0 to 9), **then** do Part 2 (your own work).

## 1. Your goal

You write **no screen code**. You own the starter kit, you make the test sheets while the others build, you review and merge their pull requests, you run the role-by-screen test and the error and responsive review, you run the demo, and you lock the release.

You depend on nobody to start: the sheets and the demo script are written from the pictures and the Master file. Only the final test needs the merged code, and that is last by design.

## 2. Your files (only touch these)

```
docs/frontend/*            (these docs, the starter kit in docs/frontend/starter/, the sheets below)
frontend/package.json, frontend/vite.config.js   (ONLY to add Tailwind in step C1, once, before anyone starts)
docs/frontend/done/collins/   (your test evidence: screenshots, filled sheets)
the `frontend` branch      (create it, merge pull requests into it, tag it)
```

**You never edit** `frontend/src/**` (apart from the one-time Tailwind setup in C1). If you find a bug: write it on the **Fix list** (section 6) with the file, the page, the role and a screenshot, and send it to the owner. A bug in a shared starter file you fix **in `docs/frontend/starter/` only**, post "starter updated: <file>, <what changed>" in the team chat, and everyone copies that one file.

## 3. Steps

### C1. Before anyone starts (0:00 to 0:30)

1. `git checkout main && git pull && git checkout -b frontend && git push -u origin frontend`.
2. Do the Common setup Steps 0 to 9 yourself. This proves the instructions work. If any step fails or is unclear, fix the wording in the source file (`docs/frontend/COMMON-SETUP.md`), rebuild the PDFs and tell the team.
3. **Add Tailwind CSS v4 (the stack is React and Tailwind).** In `frontend/`: `npm install tailwindcss @tailwindcss/vite`. Replace `frontend/vite.config.js` with `docs/frontend/starter/vite.config.js` (it adds `tailwindcss()` to the plugins). Commit `package.json`, `package-lock.json` and `vite.config.js` to the `frontend` branch and push. Everyone else gets Tailwind with `git pull` and `npm install`.
4. Copy the starter into `frontend/` (Common setup Step 3), then check it compiles: `npm run build`. Check the harness shows the sample page (picture `starter-01-dev-harness.png`). Open Account settings in the prototype or a page using `AppearanceCard` and check Ink and Sage look right.
5. Post in the team chat: "frontend branch is ready with Tailwind. Start the Common setup."

### C2. Write the test sheets while they build (0:30 to 2:30)

Copy the three tables below into `docs/frontend/done/collins/sheets.md` and the demo script into `demo.md`. Print or keep them open. Go through each picture in `images/` once so you know the right answer by eye.

### C3. Review pull requests as they arrive (1:30 to 3:15)

For each pull request, in order of arrival:

1. Read the pasted checklist: every box ticked? If not, send it back.
2. Files: open "Files changed". **Only the owner's folders** (see the Master file, "What is shared, what is yours"). Any change to a shared file (`src/lib`, `src/components`, `src/styles/nexora*.css`, `src/mocks/data.js`, `src/dev/Harness.jsx`) is rejected with "move this to the starter via Collins".
3. Scan for the red flags (use the editor's search): `role ===`, `fetch(`, `console.log`, `alert(`, bare `px` in sizes (allowed: 1px borders, shadows), hex colours in a `className` (search `\[#`), and a logo or image inside an error page.
4. Pull the branch, `npm install`, `npm run build`, `npm run lint`. Both must pass.
5. Run the owner's pages in the harness: all roles, all states (loading, empty, error, ready). Compare with the pictures in their personal file.
6. Look at their photos in `docs/frontend/done/<name>/`: all present?
7. Merge into `frontend` (squash is fine). After each merge, run `npm run dev` and open `http://localhost:5173/` to confirm the real shell still starts.

### C4. Final tests, after all merges (3:15 to 3:45)

Run the five sheets below on the merged `frontend` branch in the **real app** (`VITE_MOCK=1 npm run dev`, then `http://localhost:5173/`), signing in with each role via the mock role picker on the login page. Record every failure on the Fix list.

### C5. Demo and lock (3:45 to 4:00)

Run the demo script (section 5) once without stopping. If it runs clean: merge `frontend` into `main`, `git tag frontend-v1`, push the tag. If anything breaks the demo, it goes on the Fix list, the owner fixes it, you re-run the demo.

## 4. The test sheets

### Sheet A: role by screen (the big one)

Rows = what you do. Columns = the six roles. Tick `OK`, or write what was wrong. **A page that should be blocked must show the 403 page with the sidebar still visible**, not a blank page and not a crash.

| Check | Member | Loans officer | Finance | Secretary | SACCO admin | Platform owner |
|---|---|---|---|---|---|---|
| Menu matches the Master file table (compare with the menu pictures). Member: Overview, My savings, Deposit, Withdraw, Loans, My settings. **Staff have no My savings, Deposit or Withdraw.** SACCO admin also has Add a member | | | | | | |
| Start page after sign-in (`overview`, owner: `pf-overview`) | | | | | | |
| `/overview` | opens (member version) | opens | opens | opens | opens | 403 |
| `/savings` | opens | 403 | 403 | 403 | 403 | 403 |
| `/deposit` and `/withdraw` | opens (M-Pesa or Bank) | 403 | 403 | 403 | 403 | 403 |
| `/accounts` | 403 | 403 | opens | opens | opens | 403 |
| `/money` | 403 | 403 | opens | 403 | opens | 403 |
| `/requests` | 403 | 403 | opens (Confirm, Reject) | 403 | opens (Confirm, Reject) | 403 |
| `/loans` | opens (Request button) | opens (Approve) | opens (Disburse, Repay) | opens (no buttons) | opens | 403 |
| `/members` | 403 | opens (read-only) | 403 | opens (read-only) | opens (manage) | 403 |
| `/add-member` | 403 | 403 | 403 | 403 | opens | 403 |
| `/reports` | 403 | opens | opens | opens | opens | 403 |
| `/audit` | 403 | 403 | 403 | opens | 403 | 403 |
| `/access` | 403 | 403 | 403 | 403 | opens | 403 |
| `/settings` | 403 | 403 | 403 | 403 | opens | 403 |
| `/pf-overview`, `/pf-saccos`, `/pf-owners`, `/pf-access`, `/pf-audit` | 403 | 403 | 403 | 403 | 403 | opens |
| `/account` and `/my-settings` | opens | opens | opens | opens | opens | opens |
| No balances shown anywhere to the platform owner | n/a | n/a | n/a | n/a | n/a | confirmed |
| Suspended SACCO: every page but `/account` shows 423 | | | | | | n/a |
| Sign out, reload: signed-out page | | | | | | |
| Reload while signed in: still signed in | | | | | | |

### Sheet B: errors (every one triggered once, compared with its picture)

| Error | How to trigger (see the Errors section of the Master file) | Looks like the picture? | Sidebar stays? | Buttons work? |
|---|---|---|---|---|
| 404 | open `/nope` | | | |
| 403 | member opens `/accounts`. **No logo anywhere on the page**: only the code, title, one sentence, buttons | | | |
| 423 | pick the suspended SACCO | | | |
| 401 | stop the session (clear `nexora.tokens` in localStorage, then click a page) | | | |
| 429 | mock throws 429 with `retryAfter: 5`; button enables after 5 s | | | |
| 500 | mock throws 500; reference shown | | | |
| Offline | DevTools, Network, Offline: banner shows, page reloads itself when back (the page shows the word Offline, no icon) | | | |
| Field error | Post money submitted empty: red text under the field | | | |
| Banner with Try again | mock throws 500 once, Try again works | | | |
| Crash boundary | throw in a render: 500 page, sidebar survives | | | |
| Wrong sign-in | wrong password: banner, not a crash | | | |
| Locked account | 423 on login: banner with Forgot link | | | |

For each, ask: could a stranger tell what happened and what to do, in one second? If not, it fails.

### Sheet C: responsive and quality (every page)

For each page at **375 px, 768 px, 1280 px** (DevTools device toolbar): no sideways scroll; no clipped or overlapping text; every button at least 2.75 rem tall and clearly a button; charts resize; tables become cards or scroll inside their own box; the drawer works on phone; the wave plays smoothly; keyboard Tab reaches everything with a visible focus ring; no `console.error`.

| Page | 375 | 768 | 1280 | Loading shows shimmer | Empty state | Error state |
|---|---|---|---|---|---|---|
| landing, login, join, register, forgot | | | | | | |
| overview (SACCO), overview (member) | | | | | | |
| savings, **deposit, withdraw, requests**, accounts, ledger, money | | | | | | |
| loans, loan detail, request | | | | | | |
| reports | | | | | | |
| members, profile, settings, access, audit | | | | | | |
| pf-overview, pf-saccos, pf-owners, pf-access, pf-audit | | | | | | |
| account settings with Appearance | | | | | | |

Also confirm the "no AI slop" rule by eye: no stray emoji, no placeholder text, no lorem ipsum, consistent fonts (Fraunces for headings, Inter for text in the default look), the cream/teal/terracotta/saffron palette only in the default theme, no logo on any error page.

### Sheet D: money requests and appearance (new)

**Deposit and Withdraw (sign in as Member):**

| Check | Result |
|---|---|
| Menu shows Overview, My savings, Deposit, Withdraw, Loans | |
| Deposit: M-Pesa and Bank both switch without losing the typed amount | |
| Deposit: empty amount, bad phone (`12345`), empty bank name, empty bank reference each show their own message under the field and send nothing | |
| Deposit: `0712345678`, `+254 712 345 678`, `0112345678` are accepted | |
| Deposit sent: green banner "Deposit request sent. An officer will confirm it and it shows in My savings." and a Pending row in History | |
| Withdraw: balance shown; `999999` shows "You can withdraw up to KES 186,400." and sends nothing | |
| Withdraw: Bank needs bank name and an account number of 6 to 20 digits | |
| Withdraw sent: banner and Pending row | |
| Press the send button twice quickly: only one request appears | |
| Rejected row shows its reason; Confirmed and Pending chips have the right colours | |
| 375 px: nothing scrolls sideways; the method switch and button are easy to tap | |

**Requests (sign in as Finance officer, then SACCO admin):**

| Check | Result |
|---|---|
| Pending list shows the members' requests; own requests have no buttons ("You cannot decide your own request") | |
| Confirm a deposit: green banner, row moves to Decided as Confirmed | |
| Confirm the KES 60,000 withdrawal for Member 5: red banner, stays Pending | |
| Reject with an empty reason shows the field message; with a reason it moves to Decided as Rejected with the reason | |
| The Overview "Member requests waiting" tile opens Requests | |
| Member and Loans officer, Secretary typing `/requests` get the 403 page | |

**Appearance (sign in as each of the six roles in turn):**

| Check | Result |
|---|---|
| Every role has **My settings** as the last item of the sidebar (members too) and it opens the Appearance card | |
| The coin (sidebar and wave) and the route-change wave change colour with the theme: Terracotta red, Sage green, Saffron gold, Teal 2 turquoise, Ocean blue, Rose pink, Slate grey, Ink dark green-black, Midnight dark navy; the Nexora writing is visible in all | |
| Sign-in page waves follow the theme | |
| Pick each of the ten themes in turn (Cream, Sage, Saffron, Terracotta, Teal 2, Ocean, Rose, Slate, Ink, Midnight): the whole page changes **clearly** (no two look alike), and every word, icon, button, chip, banner, chart and table stays easy to see. Look closely at the sidebar, the top bar (header), the phone drawer and the popups in Ink and Midnight | |
| **One person at a time:** as the Member pick Midnight; sign in as the SACCO admin on the same computer: the admin does NOT get Midnight; set Ocean for the admin; sign in as the Member again: still Midnight; sign in as the secretary: Cream | |
| Fonts: Fraunces, DM Sans, Lora, Nunito, Merriweather, Atkinson each change the whole site; Small and Large change the size of everything; Large at 375 px cuts nothing off | |
| Two tabs as the same person: change the look in one, the other follows | |
| Print preview of Reports in Midnight: black on white, no menus | |
| Lighthouse Accessibility on one page in Cream, Saffron, Ink and Midnight: no contrast warnings | |
| Pick DM Sans, Lora, Atkinson: fonts change everywhere; Small and Large text change the size of everything | |
| Reload: the choice is still there. Sign out and sign in: still there | |
| Reset to default: Cream, Fraunces and Inter, Normal | |
| Ink theme on 375 px: no light patches, popups (switcher, role menu, bell, search) are dark | |
| Error pages in Ink and Saffron are readable and still have no logo | |
### Sheet E: getting in (account, circle code, circle PIN)

Run with the mock role picker off: use the real sign-in flow in mock mode (mock circle PIN `1234`; join codes `123456` good, `000000` expired, `111111` used, `222222` burned).

| Check | Result |
|---|---|
| Landing: Sign in and Create an account both work; "Join with a code" is on the landing and the sign-in page | |
| Create an account, check email page, verify page; a signed-in person with **no circle** sees "You are not in a circle yet" with Join with a code and Log out, and no logo | |
| Join with `123456` and the right phone: step 2 asks for a 4-digit PIN twice; a different second PIN or fewer than 4 digits shows a message and sends nothing | |
| Join with `000000`, `111111`, `222222`, a wrong code: each shows its own sentence (expired, used, locked, wrong) | |
| Waiting more than 10 minutes on the PIN step shows "The setup took too long" and goes back to step 1 | |
| After joining, the person is asked for the PIN (Enter your circle); `1234` opens the circle; a wrong PIN shows "That PIN is not right."; five wrong PINs show the 15-minute lock | |
| Reload the tab inside a circle: the PIN is asked again. Sign out: the next person on the same computer sees nothing of the first | |
| A person in two circles gets the chooser; the suspended one shows the Suspended chip and opens the 423 page; switching circle asks for that circle's PIN | |
| A platform owner signs in and goes straight to the Platform area with no PIN screen | |
| A platform owner creates a circle: it appears Active with 0 members and offers "Add the first admin" | |
| The admin adds a phone and sees the code once with a 15-minute countdown; closing the card hides it; adding the same phone again makes a new code and the old one stops working | |
| A deactivated member gets the 403 page at Enter your circle | |
| **Add a member** is its own item in the SACCO admin's menu (after Members) and the Members page has an "Add a member" button; no other role has either, and the API answers 403 | |
| Add a member: a wrong phone shows the message; a good phone and a role make a 6-digit code, shown once with a countdown and a Copy button; the person then appears under "Invited, not joined yet" with a "Make a new code" button | |
| Staff menus: loans officer, finance officer, secretary and admin show **no My savings, Deposit or Withdraw**, and the Overview has no "My account" switch | |

## 5. The 6-minute demo script (`demo.md`)

1. (0:00) Open the landing page. Scroll once. Point out the 3D layers and the phone version. Explain the two doors in one sentence: an account is free and open to anyone, a circle needs a join code and PIN from its admin. Show Create an account, then Join with a code.
2. (0:45) Click Sign in. The intro writes "Nexora" with the green wave. Sign in as **SACCO admin**. Stay on the Overview: the numbers count up, the charts draw, click a "Waiting for you" row and it opens the loan.
3. (1:45) Go to **Post money**: submit empty to show the field error; post a deposit; press the button twice fast to show it posts once. Open **Accounts**, a ledger (Back button), reverse a transaction, reverse it again to show the friendly 409.
4. (3:00) **Loans**: switch to **Loans officer**, approve a loan with a reason. Switch to **Finance officer**, disburse it.
5. (3:45) Switch to **Member**: the member Overview ring, My savings (only members have it). Open **My settings**, pick Ocean, then Midnight: only this person's screen changes. Open **Deposit**, switch M-Pesa and Bank, send a deposit request and show the Pending row. Open **Withdraw**, try more than the balance to show the message, send one. Request a loan. Try `/accounts` to show the 403 page (no logo). Switch to **Finance officer**, open **Requests**, confirm one and reject one with a reason.
6. (4:30) Switch to **Platform owner**: platform overview, deactivate a SACCO, then sign in as a member of it and show the 423 page. Show there are no balances anywhere.
7. (5:15) Switch back to **SACCO admin** and point out it is still Cream: a look is personal. Open **Add a member**, make a code. Open My settings, switch to Ink and a different font, reload to show it is kept. Show an error: go offline in DevTools, the banner; back online. Shrink the window to phone width and open the drawer.
8. (5:45) Sign out. Reload: signed out. Done.

Practice it twice. If any step glitches, write it on the Fix list.

## 6. The Fix list (copy this table into `done/collins/fixes.md`)

| # | Owner | Page / role | What is wrong | Screenshot | Fixed? |
|---|---|---|---|---|---|
| 1 | | | | | |

Send each owner their rows. They fix on their own branch, push, and you re-test only those rows.

## 7. Photos to hand in (in `docs/frontend/done/collins/`)

The filled `sheets.md` (sheets A to E), `demo.md`, `fixes.md`, and one screenshot per Sheet B row.

## 8. Done checklist (the release gate; all ticked before the lock)

- [ ] `frontend` branch created; Common setup verified by doing it myself
- [ ] Starter kit builds; any starter fix was announced to the team
- [ ] All three pull requests reviewed with the red-flag search and merged
- [ ] Tailwind added to the `frontend` branch before anyone started
- [ ] `npm run build` and `npm run lint` pass on `frontend`
- [ ] Sheet A fully ticked (all six roles)
- [ ] Sheet B fully ticked (all errors look right)
- [ ] Sheet C fully ticked (375, 768, 1280)
- [ ] Sheet D fully ticked (member requests, officer queue, appearance for all six roles)
- [ ] Sheet E fully ticked (account, circle code, circle PIN, circles created by the platform owner)
- [ ] Demo ran clean once start to finish
- [ ] Fix list is empty or every remaining row is accepted as a Known gap in the Master file
- [ ] `frontend` merged into `main` by me only; tag `frontend-v1` pushed

## 10. Pictures to compare against (the right answer, by eye)

### The six menus (Sheet A, first row)
Picture: member ![](images/menu-member.png) loans officer ![](images/menu-loans-officer.png) finance officer ![](images/menu-finance-officer.png)
Picture: secretary ![](images/menu-secretary.png) SACCO admin ![](images/menu-sacco-admin.png) platform owner ![](images/menu-platform-owner.png)

### The error pages (Sheet B). None has a logo.
Picture: 404 ![](images/error-01-not-found.png) 403 ![](images/error-02-no-access.png)
Picture: 423 ![](images/error-03-suspended.png) 401 ![](images/error-04-session-ended.png)
Picture: 429 ![](images/error-05-too-many-requests.png) 500 ![](images/error-06-server-error.png)
Picture: offline ![](images/error-07-offline.png) phone ![](images/error-10-error-phone.png)

### Member requests (Sheet D)
Picture: deposit M-Pesa ![](images/member-01-deposit-mpesa.png) deposit sent ![](images/member-04-deposit-sent.png)
Picture: withdraw over balance ![](images/member-06-withdraw-over-balance.png) withdraw Bank ![](images/member-07-withdraw-bank.png)
Picture: requests queue ![](images/requests-01-queue.png) over balance ![](images/requests-04-over-balance.png)
Picture: requests on a phone ![](images/requests-06-phone.png) deposit on a phone ![](images/member-09-deposit-phone.png)

### Appearance (Sheet D)
Picture: My settings page, default ![](images/appearance-01-card-default.png)
Picture: Cream ![](images/theme-01-cream.png) Sage ![](images/theme-02-sage.png)
Picture: Saffron ![](images/theme-03-saffron.png) Terracotta ![](images/theme-04-terracotta.png)
Picture: Teal 2 ![](images/theme-05-teal2.png) Ocean ![](images/theme-06-ocean.png)
Picture: Rose ![](images/theme-07-rose.png) Slate ![](images/theme-08-slate.png)
Picture: Ink ![](images/theme-09-ink.png) Midnight ![](images/theme-10-midnight.png)
Picture: Midnight on a phone ![](images/theme-12-midnight-phone.png) Ink with the menu open ![](images/theme-13-ink-phone-drawer.png)
Picture: the Member picked Ocean ![](images/person-01-member-ocean-settings.png) the SACCO admin on the same computer ![](images/person-02-admin-still-cream.png)
Picture: Add a member ![](images/add-member-01-page.png) code made ![](images/add-member-02-code-made.png) phone error ![](images/add-member-03-phone-error.png)
Picture: Terracotta wave ![](images/logo-01-terracotta-wave.png) Sage wave ![](images/logo-02-sage-wave.png)
Picture: Saffron wave ![](images/logo-03-saffron-wave.png) Ink wave ![](images/logo-04-ink-wave.png)
Picture: Sage ![](images/appearance-02-sage.png) Saffron ![](images/appearance-03-saffron-overview.png)
Picture: Ink ![](images/appearance-05-ink-overview.png) Ink, Lora, Large ![](images/appearance-06-ink-settings.png)
Picture: on a phone ![](images/appearance-07-teal2-phone.png) ![](images/appearance-08-card-phone.png)
## 9. Hand-in

Post "Frontend locked, tag frontend-v1" in the team chat with the link to `done/collins/sheets.md`.
