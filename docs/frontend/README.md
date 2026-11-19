# NEXORA frontend: the master file

Who does what, in what order, and how we know it is finished. Everyone reads this file. Each person then follows their **own file** (`01-Ryan.pdf`, `02-Neo.pdf`, `03-Sam.pdf`, `04-Collins.pdf`).

**Stack: React 19 (JavaScript) and Tailwind CSS v4, built with Vite.** The backend (Flask + Postgres) already exists.

| Person | Personal file | Builds | Collins checks with |
|---|---|---|---|
| **Ryan** | 01-Ryan | Foundation and front door: app shell, sidebar, route transition, error system wiring, sign-in/session, public pages, account settings, **the My settings page (Appearance) and the themed logo and wave** | sheet A |
| **Sam** | 03-Sam | Money and loans: Overview, My savings, **Deposit, Withdraw**, Accounts, Post money, **Requests**, Loans, Reports | sheet B |
| **Neo** | 02-Neo | **Backend: 5 small additions plus the new deposit and withdrawal requests (item 6)**, then People pages (Members, SACCO settings, Access requests, Audit log), then Platform area | sheet C |
| **Collins** | 04-Collins | **Builds nothing.** Starter kit owner, role-by-screen test, error review, responsive test, appearance test, demo, lock | (is the checker) |

Everybody first does the **Common setup** (Steps 0 to 9). It is printed identically at the start of each personal file. Backend details every page needs are in the **Contracts** section of this file. Everything about errors is in the **Errors** section of this file.

---

## The one idea that lets everyone work at the same time

**Nobody waits for anybody.** Each person works in the **dev harness** (`http://localhost:5173/dev.html`) with **sample data** and a **role picker**. A page needs only three things, and all three come in the shared starter kit: the session hook, the API client (with a mock twin of every call) and the shared components. Ryan's real shell later gives the pages the *same* session object the harness gives them, so a page built in the harness works in the real app without changes.

```
Ryan's shell  --provides-->  useSession()  <--provided by--  dev harness
                                  |
              Sam's pages, Neo's pages, Ryan's pages all read it
```

Sam's Deposit, Withdraw and Requests screens work against a **mock** of the new request endpoints, so Sam never waits for Neo's backend. Neo's backend item 6 matches the same shapes, so the switch from mock to real is one line.

The only files two people could both want to edit are the shared ones (`lib/`, `components/`, `mocks/data.js`, `styles/`). **Nobody edits them.** Problems in them go to Collins, who fixes the starter once.

![Dev harness](images/starter-01-dev-harness.png)

---

## What belongs to a person and what belongs to the circle

NEXORA has two kinds of things. Keeping them apart avoids a whole family of mistakes.

| | Belongs to ONE PERSON (only they see or change it) | Belongs to the CIRCLE (the SACCO) (changed only by the people allowed to) |
|---|---|---|
| Examples | the look: colour theme, font, text size (My settings); the photo, email and password (Account settings); the circle PIN; their own savings page, Deposit and Withdraw requests and loan requests (members) | members and their roles; every account and the ledger; loans and their decisions; the circle's name and loan rules; the audit log |
| Who may change it | the person, nobody else, not even the SACCO admin or a platform owner | the admin and staff, by permission (`member.manage`, `savings.post`, `loan.approve` and so on) |
| Where it is saved | on this device under the person's user id (the look) or in their own records on the server | on the server, in the circle's records |
| What happens when someone else signs in on the same computer | they see **their own** look and their own things; nothing of the first person remains | they see the circle's data their role allows |
| What the menu says | "My settings", "My savings", "Deposit", "Withdraw" (personal pages) | "Overview", "Accounts", "Members", "Loans", "Reports" (circle pages) |

Two consequences you must keep in code: (1) never store a person's look, draft or setting under a key that is the same for everyone (always include the user id); (2) a staff page never shows a person's own data as if it were the circle's, which is why staff have no "My savings" and no "My account" tab on the Overview.

## How people get in: accounts, circles, join codes and PINs (the full story)

A **circle** is what the screens and the backend also call a **SACCO**: one savings group with its own members, money and loans. Two different things are needed to use NEXORA, and people mix them up, so this section explains both.

1. **An account** (who you are). Anyone can create one. It is free and open to everyone. It gives **no access to any circle**.
2. **Membership of a circle** (what you may see). You cannot give it to yourself. It comes only from a person who runs the circle, and it is proven with a **join code** and then a **PIN**.

### The two doors

| | Door 1: the account | Door 2: the circle |
|---|---|---|
| Who opens it | the person, alone, from the landing page | the circle's admin gives the person a join code |
| Pages | Landing, Sign in, Create an account, Verify email, Forgot password | Join with a code, Set your PIN, Enter your circle (PIN) |
| What you type | email and password | your phone number and a 6-digit code (once), then a 4-digit PIN you choose (every time you enter the circle) |
| What it gives | you are signed in, with no circle | you are inside one circle and see only what your role allows |
| Backend | `POST /auth/register`, `/auth/verify-email`, `/auth/login` | `POST /auth/join`, `/auth/join/pin`, `/auth/circle-login` (renamed `/auth/sacco-login`) |

### The whole journey, in order

1. **The platform owners create the circle.** Only a platform owner can (Platform area, SACCOs, Create SACCO: a name and a currency, `POST /saccos`). A new circle has no members yet. The platform owner then adds its first **SACCO admin** (only the platform owner may make or remove an admin: permission `admin.manage`). The admin gets a join code like everyone else. The platform owner never reads the circle's money. We, the team, only create circles; we never join them as staff. Note on the picture: the prototype's Create SACCO form shows **Name** and **First admin's email**. The real API takes a name and a currency (`POST /saccos`) and has no admin field, so build the form with **Name** and **Currency** (KES by default) and put the first admin in the second step below, by phone number and join code. The email box in the picture is replaced by that second step. Pictures: ![](images/platform-02-saccos.png) ![](images/platform-03-sacco-detail.png)
2. **A person creates an account** on the landing page: Sign in, or Create an account. They type an email and password, open the link sent to their email (Verify email), then sign in. They are now **signed in but in no circle**. Pictures: ![](images/public-01-landing-top.png) ![](images/public-07-login.png) ![](images/public-11-register.png) ![](images/public-13-register-check-email.png) ![](images/public-14-verify.png)
3. **The circle admin (or the staff member who is allowed to add members) adds the person's phone number** on the **Add a member** page, which is a section of its own in the admin's menu (next to Members). NEXORA makes a **6-digit join code** that works **once** and lasts **15 minutes**, and shows it once, big, with a Copy button. The admin passes it to the person by whatever way they trust (in person, a call, a message). We do not send it for them. Pictures: ![](images/add-member-01-page.png) ![](images/add-member-02-code-made.png)
4. **The person opens Join with a code** (from the landing page or the sign-in page), types the **same phone number** the admin used and the 6 digits. Pictures: ![](images/public-08-join-code.png) ![](images/public-09-join-code-error.png)
5. **The person chooses a 4-digit PIN** (twice). This PIN belongs to **this circle**, not to the account. When it is saved, the person is a member of the circle. Picture: ![](images/public-10-join-pin.png)
6. **Entering the circle.** Whenever the person signs in, or switches to another circle in the switcher, they **type that circle's PIN** (the "Enter your circle" screen). Only after the PIN is accepted do they see the circle's pages. If they belong to more than one circle, they choose which one first. Picture of the switcher: ![](images/shell-04-sacco-switcher.png)
7. **Inside the circle** the menu depends on the role the admin gave (member, loans officer, finance officer, secretary, SACCO admin). Pictures of every menu are in the next section.

```
landing page
   |-- Sign in ------------> signed in? ----no----> error under the form
   |-- Create an account --> verify email -> sign in
   |-- Join with a code (needs to be signed in; if not, sign in first, then continue)
signed in
   |-- platform owner -------------------------------> Platform area (no circle PIN, no balances)
   |-- 0 circles --> "You are not in a circle yet. Ask your SACCO admin for a join code." + [Join with a code]
   |-- 1 circle  --> Enter your circle (PIN) --> the circle's Overview
   |-- 2+ circles -> choose a circle --> Enter your circle (PIN) --> the circle's Overview
```

### What the person sees on each screen, and what can go wrong (every case has a sentence and a next step)

| Where | What happened | What the person sees | What the code does |
|---|---|---|---|
| Sign in | wrong email or password | banner: "Your email or password is not right." | `describe(err, {context:'login'})`; the form keeps what was typed |
| Sign in | 5 wrong tries | banner: "This account is locked for 15 minutes." with a link to Forgot password | 423 with `context: 'login'` |
| Sign in | email not verified | banner telling them to open the link we sent, with "Send it again" | `POST /auth/resend-verification` |
| Create an account | email already used | field message under Email | server 409 sentence shown under the field |
| Join | wrong code | "That code is not right. Check the 6 digits and try again." | `CODE_WRONG` 400. Every wrong try counts; too many burn the code |
| Join | code older than 15 minutes | "This code has expired. Ask your admin to add you again for a new one." | `CODE_EXPIRED` 410 |
| Join | code already used | "This code was already used. Sign in instead, or ask your admin for a new code." | `CODE_USED` 409 |
| Join | code burned by too many wrong tries | "This code is locked after too many wrong tries. Ask your admin to add you again." | named code from the server |
| Join | phone belongs to another account | "That phone belongs to another account." | 409 sentence |
| Join | already a member of this circle | "You are already a member of this circle." | 409 sentence |
| Join | circle is suspended | the suspended page (423): "This SACCO is suspended" | 423 page |
| Join, PIN step | more than 10 minutes between the code and the PIN | "The setup took too long. Join again with your code." and the page goes back to step 1 | 401 from `/auth/join/pin` |
| Join, PIN step | the two PINs differ, or not exactly 4 digits | message under the field, nothing is sent | frontend check, then server 400 sentence |
| Enter your circle | wrong PIN | "That PIN is not right." and how many tries are left if the server says | `PIN_WRONG` 401 |
| Enter your circle | 5 wrong PINs | "Too many wrong PINs. Try again in 15 minutes, or ask your admin to reset it." | `PIN_LOCKED` 423 |
| Enter your circle | membership deactivated by the admin | 403 page: "You do not have access to this page" with the button "Go to my start page" | `/auth/circle-login` answers 403 |
| Anywhere | the person has an account but **no circle** | the "not in a circle yet" page (see below) with a Join with a code button | `GET /members/me/saccos` returns an empty list |
| Anywhere | the circle is suspended while the person is inside | every circle page except Account settings and My settings shows the 423 page; the switcher still lets them choose another circle | 423 on the next request |

**The "not in a circle yet" page.** A person who has an account but no circle must never land on a blank or broken screen. Show a calm full-page message inside a plain shell (no sidebar items except My settings): title "You are not in a circle yet", one sentence "Ask your SACCO admin or a staff member for a join code, then use it here.", and two buttons: **Join with a code** and **Log out**. (Same plain look as an error page: no logo, no decoration.)

**The "Enter your circle" screen (Ryan builds it).** It uses the same card as the Join PIN step (picture ![](images/public-10-join-pin.png)): title "Enter your circle", the circle's name, four PIN boxes (numeric, hidden, the keyboard opens in numbers on a phone), a **Continue** button and a link "Not your circle? Choose another". The backend answer is only `{ok, membership_id, role}`; it does **not** hand back a new token, so the app keeps "I have entered circle X" **in memory for this tab** (not in `localStorage`): reloading the tab asks for the PIN again, signing out forgets it, switching circle asks for the new circle's PIN. In the prototype this screen is described but not drawn: the "view as" menu skips it, which is why you will not see it in the clickable prototype.

**Who may issue join codes.** Whoever holds the permission `member.manage`. Today that is the **SACCO admin** only (see `backend/app/security/permissions.py`). If the team decides staff members (for example the secretary) may also add members, Neo adds `member.manage` to that role in the same place and in a migration; the **Add a member** menu item and the Add button on Members already show only when `can('member.manage')`, so nothing else changes.

## What is shared, what is yours

| Shared (read only, same for all) | Ryan's | Sam's | Neo's |
|---|---|---|---|
| `src/lib/*` `src/components/*` `src/mocks/data.js` `src/styles/nexora*.css` `src/styles/tailwind.css` `src/dev/*` (except registry) `dev.html` `vite.config.js` | `src/shell/` `src/pages/public/` `src/pages/account/` `src/api/auth.js` `src/api/session.js` `src/main.jsx` `src/App.jsx` `index.html` `src/dev/registry.ryan.js` | `src/pages/money/` `src/api/money.js` `src/api/loans.js` `src/api/reports.js` `src/api/requests.js` `src/mocks/sam.js` `src/styles/sam.css` `src/dev/registry.sam.js` | `backend/...` (the 6 listed changes) `tests/...` `src/pages/people/` `src/pages/platform/` `src/api/people.js` `src/api/platform.js` `src/mocks/neo.js` `src/styles/neo.css` `src/dev/registry.neo.js` |

---

## The screens, by role (what each person sees in the sidebar)

This is already coded in `lib/perms.js`. Use it to test with the harness role picker.

| Role | Sidebar items |
|---|---|
| Member | Overview, My savings, **Deposit, Withdraw**, Loans, **My settings** (the member's own pages) |
| Loans officer | Overview, Loans, Members, Reports, **My settings** |
| Finance officer | Overview, Accounts, Post money, **Requests**, Loans, Reports, **My settings** |
| Secretary | Overview, Accounts, Loans, Members, Reports, Audit log, **My settings** |
| SACCO admin | Overview, Accounts, Post money, **Requests**, Loans, Members, **Add a member**, Reports, Access requests, SACCO settings, **My settings** |
| Platform owner | Platform overview, SACCOs, Owners, Access to SACCOs, Platform audit, **My settings** |
| Everyone | **My settings** (its own sidebar item: colour theme, font, text size, for their own view only) and Account settings (from the profile at the bottom of the sidebar) |

**Staff pages are the circle's pages, not personal ones.** The loans officer, finance officer, secretary and SACCO admin run the circle, so their menus hold no "My savings", no Deposit and no Withdraw, and their Overview shows the circle only (there is no "My account" switch). The circle's savings are under **Accounts**. Only a **member** has My savings, Deposit and Withdraw (permission `savings.request`). Officers do not deposit or withdraw for themselves: they confirm members' requests on **Requests** (permission `savings.post`).

| Role | Picture of its menu |
|---|---|
| Member | ![](images/menu-member.png) |
| Loans officer | ![](images/menu-loans-officer.png) |
| Finance officer | ![](images/menu-finance-officer.png) |
| Secretary | ![](images/menu-secretary.png) |
| SACCO admin | ![](images/menu-sacco-admin.png) |
| Platform owner | ![](images/menu-platform-owner.png) |

---

## Every screen, with its picture and its owner

### Public (Ryan)
| Screen | Picture |
|---|---|
| Landing, desktop | ![](images/public-01-landing-top.png) |
| Landing, full page | ![](images/public-02-landing-full.png) |
| Landing, phone | ![](images/public-03-landing-phone.png) |
| Intro: "Nexora" being written | ![](images/public-05-intro-writing.png) |
| Sign in | ![](images/public-07-login.png) |
| Join with a code, then PIN | ![](images/public-08-join-code.png) ![](images/public-10-join-pin.png) |
| Register, check email, verify | ![](images/public-11-register.png) ![](images/public-13-register-check-email.png) ![](images/public-14-verify.png) |
| Forgot password | ![](images/public-15-forgot.png) |

### Shell and account (Ryan)
| Screen | Picture |
|---|---|
| Sidebar, desktop | ![](images/shell-01-sidebar-desktop.png) |
| Phone, closed and drawer open | ![](images/shell-02-phone-closed.png) ![](images/shell-03-phone-drawer-open.png) |
| SACCO switcher | ![](images/shell-04-sacco-switcher.png) |
| Green-wave route change | ![](images/shell-10-wave-transition.png) |
| Notifications, search | ![](images/shell-06-notifications.png) ![](images/shell-07-search.png) |
| Photo viewer | ![](images/shell-08-photo-viewer.png) |
| Account settings | ![](images/shell-09-account-settings.png) |
| My settings (sidebar item), default Cream | ![](images/appearance-01-card-default.png) |
| Appearance, Sage theme applied | ![](images/appearance-02-sage.png) |
| **The ten themes, side by side on the same page (member Overview):** Cream | ![](images/theme-01-cream.png) |
| Sage | ![](images/theme-02-sage.png) |
| Saffron | ![](images/theme-03-saffron.png) |
| Terracotta | ![](images/theme-04-terracotta.png) |
| Teal 2 | ![](images/theme-05-teal2.png) |
| Ocean | ![](images/theme-06-ocean.png) |
| Rose | ![](images/theme-07-rose.png) |
| Slate | ![](images/theme-08-slate.png) |
| Ink | ![](images/theme-09-ink.png) |
| Midnight | ![](images/theme-10-midnight.png) |
| A staff screen in Ocean (the finance officer's Overview) | ![](images/theme-11-ocean-staff.png) |
| Dark themes on a phone: Midnight, and Ink with the menu open | ![](images/theme-12-midnight-phone.png) ![](images/theme-13-ink-phone-drawer.png) |
| Rose and Nunito on the Requests queue | ![](images/theme-14-rose-requests.png) |
| **One person at a time:** the member picked Ocean | ![](images/person-01-member-ocean-settings.png) |
| and the SACCO admin on the same computer still sees Cream | ![](images/person-02-admin-still-cream.png) |
| Appearance, Ink with Lora and Large text | ![](images/appearance-06-ink-settings.png) |
| Appearance on a phone | ![](images/appearance-07-teal2-phone.png) ![](images/appearance-08-card-phone.png) |
| The coin and the route-change wave follow the theme: Terracotta (red) | ![](images/logo-01-terracotta-wave.png) |
| Sage (green) | ![](images/logo-02-sage-wave.png) |
| Saffron (gold) | ![](images/logo-03-saffron-wave.png) |
| Ocean (blue) | ![](images/logo-06-ocean-wave.png) |
| Rose (pink) | ![](images/logo-07-rose-wave.png) |
| Slate (grey) | ![](images/logo-08-slate-wave.png) |
| Midnight (dark navy) | ![](images/logo-09-midnight-wave.png) |
| Ink (dark) | ![](images/logo-04-ink-wave.png) |
| Sign-in page waves in Cream, default | ![](images/public-07-login.png) |

### Money and loans (Sam)
| Screen | Picture |
|---|---|
| Overview, SACCO | ![](images/money-01-overview-sacco.png) |
| Overview, member | ![](images/money-02-overview-member.png) |
| My savings (member only) | ![](images/member-10-my-savings.png) |
| Deposit, M-Pesa | ![](images/member-01-deposit-mpesa.png) |
| Deposit, Bank | ![](images/member-02-deposit-bank.png) |
| Deposit, field errors | ![](images/member-03-deposit-errors.png) |
| Deposit, request sent | ![](images/member-04-deposit-sent.png) |
| Deposit, phone | ![](images/member-09-deposit-phone.png) |
| Withdraw, M-Pesa | ![](images/member-05-withdraw-mpesa.png) |
| Withdraw, more than the balance | ![](images/member-06-withdraw-over-balance.png) |
| Withdraw, Bank | ![](images/member-07-withdraw-bank.png) |
| Withdraw, request sent | ![](images/member-08-withdraw-sent.png) |
| Requests queue (officers) | ![](images/requests-01-queue.png) |
| Reject needs a reason | ![](images/requests-02-reject-reason.png) |
| Confirmed and posted | ![](images/requests-03-confirmed.png) |
| Withdrawal above the balance cannot be confirmed | ![](images/requests-04-over-balance.png) |
| Decided requests | ![](images/requests-05-decided.png) |
| Requests, phone | ![](images/requests-06-phone.png) |
| Accounts, ledger | ![](images/money-05-accounts-list.png) ![](images/money-06-account-ledger.png) |
| Post money, safe retry, reverse | ![](images/money-07-post-money.png) ![](images/money-08-safe-retry.png) ![](images/money-09-reverse-409.png) |
| Loans (officer, member, finance), detail | ![](images/money-10-loans-officer.png) ![](images/money-12-loans-member.png) ![](images/money-13-loans-finance.png) ![](images/money-11-loan-detail.png) |
| Reports | ![](images/money-14-reports.png) |

### People and platform (Neo)
| Screen | Picture |
|---|---|
| Members list and profile | ![](images/people-01-members.png) ![](images/people-02-member-profile.png) |
| **Add a member** (its own page, SACCO admin): empty, code made, wrong phone | ![](images/add-member-01-page.png) ![](images/add-member-02-code-made.png) ![](images/add-member-03-phone-error.png) |
| A secretary sees the Members list but no Add a member button and no menu item | ![](images/add-member-04-staff-no-add.png) |
| Audit log | ![](images/people-04-audit-log.png) |
| SACCO settings | ![](images/people-05-sacco-settings.png) |
| Access requests | ![](images/people-06-access-requests.png) |
| Platform: overview, SACCOs, SACCO detail | ![](images/platform-01-overview.png) ![](images/platform-02-saccos.png) ![](images/platform-03-sacco-detail.png) |
| Platform: owners, access, audit | ![](images/platform-04-owners.png) ![](images/platform-05-access.png) ![](images/platform-06-audit.png) |

### Errors (everyone uses them; Ryan wires them, Collins reviews them)
See the Errors section below.

---

## Timeline (4 hours, everyone in parallel)

| Time | Ryan | Sam | Neo | Collins |
|---|---|---|---|---|
| 0:00 to 0:30 | Common setup 0 to 9 | same | same | same, plus creates the `frontend` branch, adds Tailwind and checks the starter runs |
| 0:30 to 1:30 | Shell, router, transition | Overview, My savings | Backend adds (items 1 to 5) | Writes the test sheets and the demo script |
| 1:30 to 2:30 | Sign-in, session, error wiring, public pages | Deposit, Withdraw, Requests | Backend item 6 (requests), then Members, SACCO settings | Reviews the first pull requests as they arrive (error look, units, colours) |
| 2:30 to 3:15 | Account settings and Appearance, palette, bell, photo viewer | Accounts, Post money, Loans, Reports | Access requests, Audit log, then Platform | Merges finished pull requests, runs the harness against each |
| 3:15 to 3:45 | Fix Collins's list | Fix Collins's list | Fix Collins's list | **Role-by-screen test**, responsive test, error review, appearance test |
| 3:45 to 4:00 | none | none | none | Demo walkthrough, then **lock** (tag `frontend-v1`) |

Times are a guide. The order inside each person's own file is the real order. Anything not finished at 3:15 is moved to "Known gaps" below and does not block the demo.

---

## Definition of done (for the whole frontend)

1. All four pull requests merged into `frontend` and `frontend` merged into `main` only by Collins.
2. `npm run build` passes with no errors. `npm run lint` passes. Backend `pytest` is green.
3. Collins's **role-by-screen sheet** is fully ticked (every role sees the right menu, opens only what it may, sees the right 403).
4. Every error page and banner in the Errors section has been triggered once and looks like its picture, **with no logo on any error page**.
5. Phone, tablet, desktop checked for every screen (no sideways scroll, nothing clipped).
6. A member can send a deposit request and a withdrawal request (M-Pesa and Bank), and an officer can confirm or reject it on Requests.
7. Every person, members and staff alike, has **My settings** in the sidebar and can change their own colour theme (ten to choose from), font (six) and text size there. The coin and the route-change wave change colour with the theme. The choice is **theirs alone**: changing it as the member does not change the admin's screen, and it survives a reload and signing out and in. Every text and button stays readable in every theme.
7b. Staff menus hold circle pages only (no My savings, Deposit or Withdraw); the SACCO admin has **Add a member** as its own page.
8. The 6-minute demo in Collins's file runs from sign-in to log-out without a glitch.
9. Signing out, then back in, works; staying signed in across a reload works.

## Problems and how each is handled (read this before you build)

Every row says what can go wrong, what the person must see, and what your code must do. If your page has a case that is not here, solve it the same way and tell Collins so it is added.

| Problem | What the person sees | What the code does |
|---|---|---|
| Double click on any button that sends something | nothing happens the second time | disable the button while the call is in flight; money forms also reuse one `reference` |
| Network drops during a money submit or a request | banner "We could not confirm that went through. Press Send again; it will not be sent twice." and the form stays filled | keep the same `reference`; on the retry the server returns the first result (`200`), never a second entry |
| Access token expires while the person is typing | nothing, the call just works | `lib/http.js` refreshes once and repeats the call; only if the refresh fails does the 401 page show |
| Refresh token expired or revoked (password changed elsewhere, "log out everywhere") | the 401 page: "Your session ended" and a Sign in button | `onSessionEnded`; the form text is not saved, say so on the page |
| The person's role changes while they are signed in | on their next page change the menu matches the new role; a page they lost shows 403 | reload permissions on every route change and after any 403; never cache `can()` across routes |
| The person is deactivated | 403 page, and "Enter your circle" refuses them | the circle login answers 403; send them to the "not in a circle yet" page if they have no other circle |
| The circle is suspended mid-session | 423 page on circle pages | 423 handling is global in `lib/http.js`; Account settings and My settings stay open |
| Two officers press Confirm on the same request at the same moment | the second one sees "Someone already decided this request." and the list reloads | `409 REQUEST_ALREADY_DECIDED`; backend locks the row |
| An officer tries to decide their own request or post to their own account | "You cannot decide your own request." (no buttons shown) | hide the buttons when the requester is the signed-in member; the server answers 403 `OWN_REQUEST` anyway |
| A withdrawal is larger than the balance | field message under Amount before sending; a banner if the server still refuses | check against the shown balance, handle `409 INSUFFICIENT_FUNDS` |
| A member deposits by M-Pesa but the officer cannot find the payment | the officer rejects with a reason; the member sees the reason under the row | reject needs a reason (400 without one) |
| A list is very long | a Load more button | `?limit=` and `?cursor=`; hide the button when `next` is empty |
| A chart has no history from the API | the empty state "No history yet." | never draw made-up numbers |
| Phone screen is narrow | a wide table scrolls inside its own box; nothing makes the page scroll sideways | tables sit in `.table-wrap`; check at 375 px |
| The browser is offline | the slim offline banner and the Offline page on a failed page load | `NetBanner`, `describe()` code `offline`; typed text stays |
| The person picks a theme that makes a page unreadable | should never happen | no hex colours in `className`; test each theme (Step 9, point 11) |
| localStorage is blocked (private window) | the app still works; the look just resets on reload | every `localStorage` call is in try and catch (see `lib/appearance.js`) |
| Someone opens a link to a record that was deleted or never existed | the 404 page | the API 404 on load shows `ErrorPage code="404"` |
| The server crashes (5xx) | the 500 page with a short reference to quote | `PageBoundary` and `describe()` |
| Too many requests | the 429 page with a countdown, or a banner "Wait N seconds" | read `Retry-After` (Neo exposes it in CORS) |
| One person changes their colours, and another person's screen changes too | must never happen | the key is `nexora.appearance:<userId>`; `syncAppearance(userId)` runs on every sign-in, sign-out and role switch; test: set Ink as the member, sign in as the admin, the admin is still Cream |
| A theme makes a word, icon or button hard to see | must never happen | every theme was checked for 4.5 to 1 text contrast (3 to 1 for large text) on every page for every role; keep text colours on tokens, test new screens with each of the ten themes |
| A staff member looks for "My savings" | there is none: the circle's savings are under Accounts | staff menus are circle pages only (`savings.request` is held by members) |
| The admin forgets where to add a member | Add a member is its own menu item, and the Members page has an "Add a member" button | route `add-member`, permission `member.manage` || A person on a shared computer signs out and someone else signs in | the second person sees their own look; the public pages show the default Cream | `syncAppearance(null)` at sign-out, `syncAppearance(user.id)` at sign-in; keys include the user id |
| The same person has two tabs open and changes their look in one | the other tab follows within a moment | `watchAppearance` (the browser `storage` event) |
| Text size is set to Large on a small phone | nothing is cut off or overlaps | sizes are rem; test every page at 375 px with Large |
| A person invited to two circles with the same phone number | each circle has its own code, its own PIN and its own role; the code itself says which circle is joined | `/auth/join` finds the circle from the code; keep the two memberships apart in the chooser |
| The join code is shared with the wrong person | the real member's join fails with "already used" | the admin adds the phone again to make a new code; the old one stops working |
| The member forgets the circle PIN | after 5 wrong tries the PIN is locked 15 minutes | the admin resets it by adding the member again (new code, new PIN); self-service reset is not in release 1 (see Known gaps) |

## Known gaps (decided, written down, not forgotten)

| Gap | Decision for release 1 |
|---|---|
| **One role per circle for each person.** A staff member cannot also hold a member's personal savings in the same circle. | Staff accounts run the circle; if a staff person also saves, the team decides separately (for example a second account). Not part of release 1. |
| **The circle PIN has no self-service reset.** | A member who forgets it asks the circle admin, who adds the member again (a new join code, a new PIN). |
| **Join codes are issued only by the SACCO admin** (`member.manage`), not by other staff. | Documented in "How people get in". Giving another role `member.manage` is a one-line permission change plus a migration (Neo), if the team decides so. |
| **The "Enter your circle" PIN screen is specified but not drawn in the clickable prototype.** | Ryan builds it from the Join PIN card (see "How people get in"). The backend returns only `{ok, membership_id, role}`, so "entered circle X" is kept in memory for the tab. |
| **Pay-in details** (the M-Pesa paybill and the bank account members pay into) are not stored anywhere in the backend. | The Deposit page shows fixed sample values from `mocks/data.js` (`payIn`), labelled as sample. Collins asks the SACCO for the real ones before the demo and Sam changes the one constant. A SACCO setting for them is not part of release 1. |
| A confirmed request posts the real ledger entry, but **no M-Pesa or bank API is called**. Nobody's money moves by itself. | An officer checks the payment outside the app, then confirms. This is stated on the page. |
| **Platform owner cannot read SACCO money.** | This is correct and stays: the platform pages show counts and statuses only, never balances. |
| Only a **SACCO admin** may revoke support access. | The owner has no Revoke button (matches the API). |
| Member items in the API carry **email only**, no name. | Show the email where the prototype shows a name; the initials circle uses the first letter of the email. |
| Loan statuses in the API are `requested`, `approved`, `rejected`, `disbursed`, `repaid`. | The UI words them: Waiting, Approved, Rejected, Disbursed, Repaid (see `StatusChip.jsx`). |
| Profile photo upload needs an avatar endpoint that does not exist. | Photo viewer and upload dialog are built; upload is kept on the device only and labelled "saved on this device". |
| The look (colours, font, text size) is saved **per person on this device**, not on the server (no backend field yet). | The key contains the user id (`nexora.appearance:<userId>`), so two people on one computer keep separate looks and nobody changes anybody else's. The same person on another device starts with the default. Saving it on the server is not part of release 1. |

---

# Contracts: what the backend gives you, screen by screen

Base URL: `http://localhost:5000/api/v1` (set once in `lib/http.js`). All bodies are JSON. Money is in **minor units** (`10000` = KES 100). The paths below are the real routes in `backend/app/**`. If a field name here does not match what you see in the browser Network tab, **the Network tab wins**: write the real name in your page, tell Collins, and he fixes this file.

**Auth:** every call except the public ones sends `Authorization: Bearer <access_token>`. `lib/http.js` does that for you, refreshes the token once on a `401`, and on a failed refresh calls the session-ended handler (the `401` page).

**Error body (always):** `{"error": {"code": "not_found", "message": "Not found."}}`. `lib/http.js` turns it into `ApiError { status, code, message, retryAfter }`. Show it through `describe()`, never raw.

**Which SACCO:** the SACCO id is in the path (`/loans/saccos/<id>`), taken from `useSession().saccoId`. A person can belong to several SACCOs; the switcher changes `saccoId`.

## 1. Public and sign-in (Ryan)

| Screen | Call | Body | Success | Errors to show |
|---|---|---|---|---|
| Register | `POST /auth/register` | `email`, `password` | `201 {id, email}` then "check your email" | 400 (message under field), 409 email taken (message) |
| Verify email | `POST /auth/verify-email` | `token` (from the link) | `{message}` | 400 expired/used |
| Resend link | `POST /auth/resend-verification` | `email` | `{message}` (always, never reveals if the email exists) | 429 |
| Sign in | `POST /auth/login` | `email`, `password` | `{user:{id,email,is_platform_owner,memberships[],created_at}, token_type, access_token, refresh_token}` | 401 wrong (banner, context `login`), 423 locked 15 minutes (banner + link to Forgot), 429 |
| Forgot | `POST /auth/forgot-password` | `email` | `{message}` always | 429 |
| Reset | `POST /auth/reset-password` | `token`, `new_password` | `{message}` then go to sign in | 400 expired |
| Join with code | `POST /auth/join` | `code`, optional `phone` | `{setup_token, ...}` | CODE_WRONG 400, CODE_EXPIRED 410, CODE_USED 409 |
| Choose PIN | `POST /auth/join/pin` | `setup_token`, `pin` | signed in (tokens) | 400 |
| Sign in with PIN | `POST /auth/circle-login` (Neo renames it `sacco-login`; accept both until then) | `sacco_id`, `pin` (+ identity) | tokens | PIN_WRONG 401, PIN_LOCKED 423 |
| Refresh | `POST /auth/refresh` | `refresh_token` | new tokens | 401 means session ended |
| Sign out | `POST /auth/logout` (`/auth/logout-all` for everywhere) | `refresh_token` | `{message}` | ignore failures, clear tokens anyway |
| Change password | `POST /auth/change-password` | `current_password`, `new_password` | `{message}` and every session ends: go to sign in | 400 wrong current |

**Stay signed in:** tokens live in `localStorage` key `nexora.tokens` (done by `lib/http.js`). On load, if tokens exist call `GET /members/me` to restore the session; if that fails with 401 after refresh, show the sign-in page. Signing out clears the tokens. (The appearance key `nexora.appearance` is **not** cleared on sign-out.)

## 2. Who am I (Ryan builds the session from these)

| Call | Gives |
|---|---|
| `GET /members/me` | the user, `is_platform_owner`, `memberships` |
| `GET /members/me/saccos` | the SACCOs this person belongs to (for the switcher): id, name, status |
| `PATCH /members/me` | edit profile fields |
| `GET /members/me/permissions?sacco_id=<id>` | **built by Neo (backend item 1).** `{roles: [...], permissions: ["loan.view", ...]}`. Until it exists, Ryan uses the fallback table in `lib/perms.js` (`ROLES[...].perms`). The switch is one line in `src/api/session.js`. |

## 3. Money (Sam)

| Screen | Call | Notes |
|---|---|---|
| My savings | `GET /savings/accounts/me` | the caller's own account(s) in the current SACCO: id, balance (minor), status |
| Account ledger | `GET /savings/accounts/<account_id>/transactions` | list of transactions, newest first; paginated (see below) |
| Accounts list (officers) | `GET /admin/saccos/<id>/accounts` | needs `savings.view_all` |
| One account | `GET /savings/accounts/<account_id>` | |
| Open an account | `POST /savings/accounts` | |
| Deposit (officer posts) | `POST /savings/accounts/<id>/deposits` | body `amount` (minor), `reference` (uuid), optional `note`. Needs `savings.post`. Same `reference` twice returns the first result (`200`), no double posting; `DUPLICATE_REFERENCE` 409 for a reference reused with different details |
| Withdraw (officer posts) | `POST /savings/accounts/<id>/withdrawals` | same body. `409 INSUFFICIENT_FUNDS` shows the server sentence under the form |
| Interest / fee | `POST /savings/accounts/<id>/interest` and `/fees` | same body |
| Reverse | `POST /savings/transactions/<transaction_id>/reversals` | body `reference`, optional `reason`. Already reversed: 409 (show the server sentence, picture `money-09`) |
| Reports | `GET /admin/saccos/<id>/reports/summary` and `/reports/member-activity` | needs `report.view` |
| Overview numbers and charts | the reports above plus the loans list | where the API has no history series, the chart shows the empty state, never made-up data |

Reference rule: create the `reference` when the form opens, keep it in state, resend the same one on retry and after a network failure, create a new one only after success. Picture: ![safe retry](images/money-08-safe-retry.png).

### 3b. Member deposit and withdrawal requests (NEW: Neo builds item 6, Sam builds the screens)

Today only an officer can post money (`savings.post`); a member cannot call the deposit or withdrawal routes. Members need to deposit and withdraw by **M-Pesa or Bank**, so we add **requests**. A request is a message from the member: "I paid this" or "please send me this". It changes no balance. An officer confirms it, and only then the real ledger entry is posted, by the **existing** code path (`service.deposit` / `service.withdraw` in `backend/app/savings/service.py`), so every ledger rule (idempotent reference, insufficient funds, tenant checks, audit) stays in one place.

**New permission:** `savings.request` ("Send a deposit or withdrawal request for my own account"). Held by the `member` role only. Officers keep `savings.post`.

**New table `payment_requests`** (model in `backend/app/models/payment_request.py`, migration `0024`):

| Column | Type | Notes |
|---|---|---|
| `id` | integer, primary key | |
| `sacco_id` | FK `saccos.id`, not null, indexed | tenant |
| `membership_id` | FK `sacco_memberships.id`, not null, indexed | who asked |
| `kind` | text: `deposit` or `withdrawal` | check constraint |
| `method` | text: `mpesa` or `bank` | check constraint |
| `amount_minor` | bigint, greater than 0 | minor units |
| `phone` | text, null | normalised `2547XXXXXXXX` or `2541XXXXXXXX`; required when `method = mpesa` |
| `bank_name` | text, null | required when `method = bank` |
| `account_ref` | text, null | required when `method = bank`. Deposit: the reference on the bank receipt. Withdrawal: the member's account number |
| `reference` | text, **unique**, not null | the client-generated uuid. This is the retry key |
| `status` | text: `pending`, `confirmed`, `rejected` | default `pending` |
| `decided_by` | FK `sacco_memberships.id`, null | officer who decided |
| `decided_at` | timestamp, null | |
| `reject_reason` | text, null | required when rejected |
| `ledger_transaction_id` | FK, null | set when confirmed |
| `created_at` | timestamp | |

**Endpoints** (blueprint `savings_bp`, file `backend/app/savings/requests_routes.py`):

| Who | Call | Body or query | Success | Errors |
|---|---|---|---|---|
| Member | `POST /savings/requests` | `sacco_id`, `kind`, `method`, `amount` (minor), `reference`, and `phone` (mpesa) or `bank_name` + `account_ref` (bank) | `201` the request. The same `reference` again returns the original with `200` | 400 with a sentence ("Enter a Safaricom number like 0712 345 678."), 403 no `savings.request`, 409 `INSUFFICIENT_FUNDS` for a withdrawal above the balance, 423 SACCO suspended |
| Member | `GET /savings/requests/me?sacco_id=<id>&kind=<deposit or withdrawal>&limit=&cursor=` | | `{items: [...], next}` newest first, only the caller's own | |
| Officer | `GET /savings/saccos/<id>/requests?status=pending` | `status` optional (`pending`, `confirmed`, `rejected`) | `{items: [...], next}`; each item also has the member's `email` | 403 no `savings.post` |
| Officer | `POST /savings/requests/<id>/confirm` | `{reference}` (a fresh uuid, used for the ledger entry) | `200` the request with `status: confirmed` and `ledger_transaction_id` | 403 (also: an officer cannot decide their own request), 409 `REQUEST_ALREADY_DECIDED`, 409 `INSUFFICIENT_FUNDS` |
| Officer | `POST /savings/requests/<id>/reject` | `{reason}` | `200` with `status: rejected` | 400 reason missing, 403, 409 `REQUEST_ALREADY_DECIDED` |

Phone rule (frontend and backend): accept `07xx xxx xxx`, `01xx xxx xxx`, `+254 7xx xxx xxx`, `+254 1xx xxx xxx`, with or without spaces and dashes. The frontend shows `0712 345 678`; the API stores `254712345678`.

Item shape: `{id, sacco_id, membership_id, email, kind, method, amount_minor, phone, bank_name, account_ref, reference, status, reject_reason, decided_at, created_at}`.

**Frontend rules for these screens**
- Create the `reference` when the form opens; reuse it on every retry; create a new one only after a success (same as every money form).
- The member's withdrawal amount must not exceed the balance shown (field error `You can withdraw up to KES 186,400.`); the server checks again.
- After a send, show: **"Deposit request sent. An officer will confirm it and it shows in My savings."** (for a withdrawal: "Withdrawal request sent. An officer will confirm it and it shows in My savings.") and add the row to the history with a **Pending** chip.
- Status chips: Pending (warn), Confirmed (up), Rejected (bad, with the reason under the row).
- Officers: Confirm posts the entry; Reject needs a reason; nobody decides their own request; a withdrawal above the member's balance cannot be confirmed and shows the server sentence.
- Pictures: Deposit ![](images/member-01-deposit-mpesa.png) Withdraw ![](images/member-05-withdraw-mpesa.png) Queue ![](images/requests-01-queue.png)

## 4. Loans (Sam)

| Screen | Call | Body / notes |
|---|---|---|
| List | `GET /loans/saccos/<id>` (Neo adds `?status=requested`) | each loan: id, member, principal, term_months, status |
| One loan | `GET /loans/<loan_id>` | adds `decisions: [{step, decision, reason, decided_by_membership_id, created_at}]` |
| Request | `POST /loans/saccos/<id>` | `principal` (minor), `term_months`. Needs `loan.request` |
| Decide | `POST /loans/<loan_id>/decisions` | `step`, `decision` (`approve` or `reject`), `reason`. Needs `loan.approve`. `LOAN_SAME_OFFICER` 403: the same officer cannot give both steps |
| Disburse | `POST /loans/<loan_id>/disbursements` | `reference`. Needs `loan.disburse`. `LOAN_NEEDS_APPROVAL` 409 if not approved |
| Repay | `POST /loans/<loan_id>/repayments` | `reference` (+ `amount`). Needs `loan.repay` |

Statuses in the API: `requested`, `approved`, `rejected`, `disbursed`, `repaid`. Words on screen: Waiting, Approved, Rejected, Disbursed, Repaid.

## 5. People (Neo)

| Screen | Call | Notes |
|---|---|---|
| Members list | `GET /saccos/<id>/members` | each item: membership id, email, status, role (Neo adds `roles: [...]`, backend item 2) |
| Member profile | `GET /saccos/<id>/members/<membership_id>` | |
| Add member / make join code | `POST /saccos/<id>/members` | body `phone`, `role` (default `member`); returns the join code shown once (picture `people-03`) |
| Change role/status | `PATCH /saccos/<id>/members/<membership_id>` | `role` or `status` |
| Roles of one member | `GET` and `PUT /saccos/<id>/members/<membership_id>/roles` | |
| SACCO settings | `GET` and `PATCH /saccos/<id>/settings`; name/currency via `PATCH /saccos/<id>` | needs `sacco.update` |
| Access requests | `GET /saccos/<id>/support-access`; `POST /support-access/<rid>/approve` (optional `hours`), `/deny`, `/revoke` | needs `support.approve`. Only the SACCO admin revokes |
| Audit log (SACCO) | `GET /admin/saccos/<id>/audit` | needs `audit.view` |

## 6. Platform area (Neo; platform owner only)

| Screen | Call |
|---|---|
| SACCOs | `GET /saccos`, `POST /saccos` (`name`, `currency`), `POST /saccos/<id>/activate`, `POST /saccos/<id>/deactivate` |
| Owners | `GET /admin/owners`, `POST /admin/owners`, `DELETE /admin/owners/<user_id>` |
| Ask for access to a SACCO | `POST /saccos/<id>/support-access` (`reason`, `scope`) |
| Platform audit | `GET /admin/audit` |

The platform owner **never** sees a SACCO's balances. Platform pages show counts and statuses only.

## Pagination

List endpoints accept `?limit=` and `?cursor=` (or `?page=` where the route says so; check the response for `next`). Build every long list with a **Load more** button, never an endless fetch. If a response has no `next`, hide the button.

## Permission names (from `backend/app/security/permissions.py`)

`dashboard.view`, `sacco.view`, `sacco.update`, `sacco.manage`, `member.view`, `member.manage`, `savings.view`, `savings.view_all`, `savings.post`, `savings.reverse`, **`savings.request` (new)**, `loan.view`, `loan.request`, `loan.approve`, `loan.disburse`, `loan.repay`, `report.view`, `audit.view`, `support.approve`, `admin.manage`, `platform`.

## The 6 backend additions (Neo does these first, see 02-Neo)

1. `GET /members/me/permissions` returning roles and permissions for a SACCO.
2. `roles: [...]` on each item of `GET /saccos/<id>/members`.
3. `?status=` filter on `GET /loans/saccos/<id>`.
4. Add `Retry-After` to the CORS exposed headers so the browser can read it on a 429.
5. Rename `/auth/circle-login` to `/auth/sacco-login`; keep the old path working for one release.
6. **Member deposit and withdrawal requests**: the `savings.request` permission, the `payment_requests` table and the five endpoints in section 3b, with tests.

Nobody waits for these: the frontend has a mock and a fallback for each (see each personal file).

---

# Errors: how a failure looks in NEXORA

The rule: **an error must be impossible to miss, and must tell the person what to do next.** It is loud (terracotta), it sits where the person is looking, and it is one plain sentence. It never shows a code, a stack or the word "undefined".

There are **four sizes** of error. Use the smallest one that fits. All four already exist in the starter kit; you only choose and wire.

| Size | When | Component | Picture |
|---|---|---|---|
| 1. Under a field | one input is wrong | `Field` with `error="..."` | ![](images/error-09-field-error-money.png) |
| 2. Banner | an action or a card failed | `ErrorBanner` (kinds `err`, `warn`, `info`, `ok`), with `onRetry` when trying again can work | ![](images/public-09-join-code-error.png) ![](images/money-09-reverse-409.png) |
| 3. Toast | a small thing failed and the page is fine | `toast('...', 'err')` | (red version of the green toast) |
| 4. Full page | the whole page cannot be shown | `ErrorPage code="..."` | below |

## The seven full-page errors (every one has a picture)

**A full-page error is only this: the big code (or the word Offline), the title, one sentence, one or two buttons. There is no logo, no illustration, no card and no gradient.** The page stays inside the app shell (sidebar visible) so the person can click away; only `401` and the public pages show without the sidebar.

| Code | When it appears | Picture |
|---|---|---|
| **404** Not found | unknown route, or the API says 404 while loading a page | ![](images/error-01-not-found.png) |
| **403** No access | the role may not open the page (guard) or the API says 403 on load. A member opening `/accounts` sees this. | ![](images/error-02-no-access.png) |
| **423** SACCO suspended | the API says 423 on any SACCO page | ![](images/error-03-suspended.png) |
| **401** Session ended | refresh failed, the person must sign in again | ![](images/error-04-session-ended.png) |
| **429** Too many requests | the API says 429; button turns on after the wait (`Retry-After`) | ![](images/error-05-too-many-requests.png) |
| **500** Our fault | 5xx or a crash in a page; shows a short reference the person can quote | ![](images/error-06-server-error.png) |
| **offline** No connection | the fetch itself failed; page reloads by itself when back | ![](images/error-07-offline.png) |

On a phone: ![](images/error-10-error-phone.png)

## The one function: `describe()`

```js
import { describe } from '../lib/errors.js';
const { page, text, wait } = describe(error, { mode: 'page' });   // loading a page
const { text }             = describe(error, { mode: 'action' }); // after a button or form
```

- `page` is `null` or one of the seven codes: show `<ErrorPage code={page} />` instead of the page.
- `text` is the sentence for a banner. Backend sentences for **400** and **409** are written for people ("Insufficient funds.") and are shown as they are. Everything else uses fixed wording so the same failure reads the same on every screen.
- `context: 'login'` makes 401 read "Your email or password is not right" and a lock (423) read "This account is locked for 15 minutes..." with a link to Forgot password.

| Status | Loading a page | After an action |
|---|---|---|
| 0 / network | `offline` page | banner "You are offline. Check your connection and try again." |
| 400 | n/a | the server sentence under the form (banner) |
| 401 | `401` page (after one silent refresh) | banner "Your session ended. Sign in again to carry on." |
| 403 | `403` page | banner "You are not allowed to do that..." |
| 404 | `404` page | banner "That could not be found..." |
| 409 | n/a | the server sentence in a banner |
| 413 | n/a | banner "That is too large to send..." |
| 423 | `423` page | banner "This SACCO is suspended..." |
| 429 | `429` page with countdown | banner "You are doing that too fast. Wait N seconds..." |
| 5xx / unknown | `500` page | banner "Something went wrong on our side. Try again in a moment." |

## Rules for writing an error sentence

1. One sentence. Say **what happened**, then **what to do**: "That amount is more than the balance. Enter a smaller amount."
2. Plain words. No "invalid", "exception", "payload", "request failed".
3. Never blame the person. Never use "oops".
4. If trying again can work, add **Try again** (`onRetry`). If not, say what will fix it.
5. Put it next to the thing that failed: a field error under the field, an action error above the button row, a page error in place of the page.
6. A field error also sets `aria-invalid` and is announced (the `Field` component does this).
7. Do not clear the form on failure. The person keeps what they typed.

## Crashes inside a page

Wrap every page in an error boundary that shows `<ErrorPage code="500" />` (the harness already does; Ryan does the same in the real shell, one boundary around the page area, so the sidebar survives a crash).

## How to trigger each one (for testing; Collins does all of these)

In the harness and with the mock: make the mock function `throw new ApiError(<status>, 'x')` (import `ApiError` from `lib/http.js`).

| Want to see | Do this |
|---|---|
| 404 | open a route name that is not in the registry |
| 403 | harness role = Member, open `accounts` |
| 423 | harness SACCO = Gamma SACCO (suspended) |
| 401, 429, 500 | throw `new ApiError(status, 'x')` (status 401, 429 or 500) from the page's API function (429: set `retryAfter: 5`) |
| offline | throw `new ApiError(0, 'x')`, or turn off Wi-Fi in the real app |
| field error | submit the money form empty |
| banner with retry | throw 500 once, click **Try again** (the second call succeeds) |
