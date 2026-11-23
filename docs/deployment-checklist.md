# Deployment checklist: production M-Pesa (Daraja)

Read this before setting `DARAJA_ENV=production`. Every box is a thing to check on the real server, not in the code.

## Legal sign-off

NEXORA holds no funds and is not paid through STK push. Each SACCO prompts its own members into its own paybill or till, using its own Daraja credentials; an officer's confirmation credits a deposit. A lawyer has given the go-ahead for production use.

| Item | Value |
|---|---|
| Date of the written advice | **[TO BE FILLED BY COLLINS: date]** |
| One-line summary of the advice | **[TO BE FILLED BY COLLINS: one line, from the written advice]** |
| Where the written advice is kept | **[TO BE FILLED BY COLLINS: location]** |

Do not go live until the three rows above are filled in from the written advice.

## 1. Environment settings

Set these on the server (never in git; `backend/.env` stays untracked).

| Setting | Production value | Why |
|---|---|---|
| `APP_ENV` | `production` | Turns on the production start-up checks. |
| `DARAJA_ENV` | `production` | Uses `https://api.safaricom.co.ke`. The default, `sandbox`, uses `https://sandbox.safaricom.co.ke`. Any other value stops the app at start-up. |
| `DARAJA_ENABLED` | `1` | Daraja stays off unless this is set. |
| `DARAJA_ENCRYPTION_KEY` | a Fernet key | Encrypts each SACCO's saved credentials. Required: the app refuses to start without it. |
| `DARAJA_CALLBACK_URL` | `https://<host>/api/v1/daraja/callback/<DARAJA_CALLBACK_TOKEN>` | Must be `https` and end with the token. |
| `DARAJA_CALLBACK_TOKEN` | 32 or more random letters, digits, `-` or `_` | The only proof a callback came from Safaricom. |
| `DARAJA_CONSUMER_KEY`, `DARAJA_CONSUMER_SECRET`, `DARAJA_PASSKEY`, `DARAJA_SHORTCODE` | leave **unset** | These are shared sandbox keys. In production they are never used: a push needs that SACCO's own saved credentials. |

The app refuses to start (`RuntimeError` naming the setting) if `APP_ENV=production` and `DARAJA_ENABLED=1` but `DARAJA_ENV` is not `production`, the callback URL is not `https` or does not end with the token, the token is weak, or the encryption key is missing or not a valid Fernet key.

Generate the key once:

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate the callback token:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- [ ] All settings above are in the server's environment, not in a file in the repo.
- [ ] `DARAJA_CONSUMER_KEY`, `DARAJA_CONSUMER_SECRET`, `DARAJA_PASSKEY`, `DARAJA_SHORTCODE` are unset.
- [ ] `git status` on the server's checkout shows no `.env`.

## 2. HTTPS and the callback URL

- [ ] The site is served over HTTPS with a valid certificate (Safaricom will not post to plain `http`).
- [ ] `DARAJA_CALLBACK_URL` is reachable from the public internet and ends with `/api/v1/daraja/callback/<token>`.
- [ ] A `POST` to the callback URL with a wrong token answers 404 (the token is the secret). Do not log or share the URL.
- [ ] The reverse proxy passes the request body through unchanged and does not rewrite the path.

## 3. Each SACCO before it takes live prompts

- [ ] The SACCO's officers have approved its pay-in details (two officers: one proposes, another approves; a change waits 24 hours before it goes live).
- [ ] The SACCO admin saved its **own** Daraja shortcode, consumer key, consumer secret and passkey (`PUT /saccos/{id}/daraja-settings`). In production there is no fallback to anything else.
- [ ] For a **paybill**, the saved shortcode equals the approved paybill (a mismatch answers 409 and no prompt is sent).
- [ ] For a **till**, the saved shortcode is the till's head-office number and the approved number is the till. Prompts go to the approved till.
- [ ] Pochi la Biashara SACCOs stay record only: no prompt can be sent.
- [ ] Deposit controls reviewed (`GET /saccos/{id}/deposit-controls`): auto-confirm is off unless the SACCO chose a limit; the large-amount, manual-entry, repeat and quick-withdrawal thresholds suit the SACCO.

## 4. Key backup

`DARAJA_ENCRYPTION_KEY` is the only way to read the saved credentials.

- [ ] The key is stored in at least two places that are not the server and not git (for example a password manager and an offline copy).
- [ ] Whoever holds the backup is written down.
- [ ] Everyone knows the cost of losing it: every SACCO's saved credentials become unreadable. Prompts for that SACCO answer 409 until its admin saves the credentials again. No money is lost and no ledger row changes.
- [ ] Rotating the key means each SACCO admin saves its credentials again. Do not replace the key without telling them first.

## 5. Before the first real payment

- [ ] `alembic upgrade head` ran: one head, `0038`.
- [ ] Take a database backup.
- [ ] Do a small live payment with an officer's own number into a SACCO that agreed to it. Confirm the callback created a pending deposit, an officer confirmed it, the ledger row says `stk`, and `GET /saccos/{id}/reconciliation` lists no mismatch.
- [ ] Check `GET /saccos/{id}/flagged-payments` is readable by the secretary.

## 6. Rollback

Rolling back is safe at any point because NEXORA holds no funds and the ledger is append-only.

1. **Stop new prompts at once:** set `DARAJA_ENABLED=0` and restart. The STK routes and the callback then answer 404. Members can still pay the paybill or till directly; officers record those with a manual deposit (M-Pesa receipt, amount, payer phone).
2. **Pending deposits stay.** Paid pushes already recorded stay in the request queue for officers to confirm. A callback that arrives while Daraja is off is lost to NEXORA: officers record it as a manual deposit from the M-Pesa message, and the reconciliation report shows what M-Pesa took.
3. **Back to sandbox:** set `DARAJA_ENV=sandbox` and, if the app runs with `APP_ENV=production`, also `DARAJA_ENABLED=0` (production refuses sandbox Daraja at start-up).
4. **Code rollback:** redeploy the previous release. Do not run `alembic downgrade` to undo `0038` on a database that has taken live payments: the downgrade drops the reversal requests and the deposit-control settings. Restore from the backup instead if you must.
5. A mistaken ledger entry is never edited or deleted. Reverse it: one officer asks, a different officer approves.

## 7. Where to look when something is wrong

| Symptom | Look at |
|---|---|
| App will not start | The `RuntimeError` message names the setting. |
| A member says they paid but no deposit shows | `GET /saccos/{id}/reconciliation` (`paid_not_recorded`, `paid_not_credited`), then the request queue. |
| A prompt answers 409 | The message says why: no saved credentials, the paybill does not match the approved one, no approved pay-in details, or credentials unreadable (key lost or changed). |
| An entry looks wrong | Ask for a reversal; do not edit. |
