# Prototype (the reference for how everything looks and behaves)

Double-click `index.html` to open it in a browser; no install needed. Use the profile menu to "view as" each role. Also published: https://claude.ai/artifact/SPDZB7PDFbRt9wDJ3cvxH7

| File | Contains |
|---|---|
| `index.html` | markup, the intro and wave curtain, the pen-stroke paths, the embedded font |
| `style.css`, `style2.css` | all styling (the starter's `nexora.css` and `nexora-2.css` are copies) |
| `app.js` | core: router, shell, sidebar, overview, savings, loans |
| `ext.js` | role menus, palette, bell, landing reveal |
| `pages2.js` | accounts, members, loan details, settings, access, account settings |
| `platform.js` | platform pages, register, verify, forgot |
| `errors.js` | error pages (no logo), guard, offline banner, field errors, style guide |
| `requests.js` | member Deposit and Withdraw pages (M-Pesa or Bank) and the officers' Requests queue |
| `addmember.js` | the Add a member page (phone, role, one-time join code) |
| `appearance.js` | colour theme, font and text size, saved in `nexora.appearance` |

It is a reference only. Do not copy its code into React blindly: use the starter kit components and rebuild each screen to match the pictures.
