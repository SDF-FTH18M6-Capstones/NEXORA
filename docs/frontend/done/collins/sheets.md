# Collins test sheets (results empty until run on merged `frontend`)


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
