# 🎮 AFK Arena Code Tracker (ntfy)

Automatically scrapes and sends push notifications via **ntfy.sh** whenever new codes are available for AFK Arena — and can **auto-redeem** them for you on demand.

## 🎁 Currently active codes

<!-- CODES:START -->
| Code | Server | Reward | Status |
|---|---|---|---|
| `13thlilith` | classic | 1300 Diamonds | pending |
| `2025selene` | companions | — | pending |
| `2b9pyu99rn` | classic | — | pending |
| `2bfe265g6x` | classic | 1000 Diamonds | pending |
| `2bjzpbed53` | classic | 2000 Diamonds | pending |
| `2bqw69udk3` | companions | — | pending |
| `2bxn4k86qd` | classic | 1000 Diamonds | pending |
| `426653P7TD` | classic | 3000 Diamonds | pending |
| `42N6CAGKSV` | companions | — | pending |
| `4hwzcs2umh` | classic | — | pending |
| `9wf6pjg7td` | unknown | — | pending |
| `afk888` 🔒 | all | Permanent code | pending |
| `afknew2024` | unknown | — | pending |
| `afksummer2023` | unknown | — | pending |
| `at7i63zyga` | unknown | — | pending |
| `b6tuz7utxn` | unknown | — | pending |
| `belovedhero2025` | classic | 1000 Diamonds, 3000 Diamonds | pending |
| `bj6xb8kehv` | unknown | — | pending |
| `DON2026classic` | classic | — | pending |
| `Dragon888` | unknown | — | pending |
| `DTZDMHXU83` | unknown | — | pending |
| `ecne2zthiz` | unknown | — | pending |
| `eh2g9fgxg9` | unknown | — | pending |
| `ER85KTZ6CJ` | unknown | — | pending |
| `F9K29QAGQW` | unknown | — | pending |
| `ftqbx5mxfp` | unknown | — | pending |
| `fxbwkxxdt5` | unknown | — | pending |
| `HAPPY2023` | unknown | — | pending |
| `HVBJ9PS6AR` | unknown | — | pending |
| `HVHPFJ9MWI` | unknown | — | pending |
| `IB3WIV7626` | unknown | — | pending |
| `IBI6N3ZBVJ` | unknown | — | pending |
| `KQJ4N3FUP9` | unknown | 1,000 Diamonds | pending |
| `KQN6TGUMXK` | classic | 3000 Diamonds, 10 Common Hero Scrolls | pending |
| `KQVV44SCJ2` | companions | 1,000 Diamonds | pending |
| `lilith11th` | unknown | — | pending |
| `lilithhappy2026` | classic | 1000 Diamonds | pending |
| `MG673B4BIX` | unknown | 1,000 Diamonds | pending |
| `MGEB84EY4Z` | classic | — | pending |
| `misevj66yi` 🔒 | all | Permanent code | pending |
| `mp8mt8q5fp` | unknown | — | pending |
| `mpv3vuctf6` | unknown | — | pending |
| `mystery2023` | unknown | 30 Common Hero Scrolls | pending |
| `n98qbeanvg` | unknown | — | pending |
| `n9kyrevxxx` | unknown | — | pending |
| `n9nsraie2e` | unknown | — | pending |
| `n9tugjzx92` | unknown | — | pending |
| `pc6wed5mut` | unknown | — | pending |
| `selene2025` | classic | 1000 Diamonds | pending |
| `special2023` | unknown | — | pending |
| `u4fctemje2` | classic | 1,000 Diamonds | pending |
| `uf4shqjngq` 🔒 | all | Permanent code | pending |
| `uj5fs5z58s` | unknown | — | pending |
| `UJ6R5HS4CF` | companions | — | pending |
| `ujqrukd2at` | classic | 1200 Diamonds | pending |
| `vdj82fht4r` | classic | 3000 Diamonds | pending |

_Last updated: 2026-05-29T05:28:54.638909 UTC · 🔒 = permanent_
<!-- CODES:END -->

> This table is regenerated automatically every run. `🔒` marks permanent codes.

## 🚀 Setup in 3 steps

### Step 1 — Install the ntfy app
- iOS: [App Store](https://apps.apple.com/app/ntfy/id1625396347)
- Android: [Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)

Open the app → **Subscribe to topic** → enter a random topic name, e.g.:
```
afk-codes-x7k92mzp
```
> ⚠️ Use a hard-to-guess name so nobody else can read your notifications!

### Step 2 — Create a GitHub repo
1. Log in to [github.com](https://github.com)
2. Create a new repo named `afk-code-tracker`
3. Upload all these files to the repo

### Step 3 — Add a GitHub Secret
Go to your repo → **Settings → Secrets and variables → Actions** → add:

| Secret | Value |
|---|---|
| `NTFY_TOPIC` | The topic name you chose in Step 1 (e.g. `afk-codes-x7k92mzp`) |

Done! 🎉

---

## ▶️ Test run
Go to the **Actions** tab → **AFK Arena Code Tracker** → **Run workflow**

If new codes are found, you'll receive a notification on your phone right away!

## ⏰ Schedule
Runs automatically every **3 hours**, completely free.

---

## 🎟️ Auto-redeem codes (`redeem.py`)

The scraper only *tells* you about codes. `redeem.py` actually **claims every pending code** for your account in one go.

AFK Arena's redemption requires a **verification code that rotates every 2 minutes**, generated inside the game — so this step can't run unattended on the cron. You trigger it and hand it a fresh code:

```bash
# 1. In-game: tap your profile → Settings → Verification Code
# 2. Run (works fastest locally, before the 2-minute code expires):
AFK_PLAYER_UID=<your_numeric_uid> python redeem.py <verification_code>
```

A single verified session redeems **all** pending codes at once. Each result is recorded in `known_codes.json` (`claimed` / `expired` / `invalid`) so the active-codes table above stays accurate and dead codes are never re-notified. Rewards arrive in your in-game mailbox.

> ⚠️ **Notes**
> - Uses the unofficial public endpoint `cdkey.lilith.com/api` and only ever touches **your own** account.
> - Store your UID as the `AFK_PLAYER_UID` GitHub Secret (or an env var). The verification code is passed per-run and never stored.
> - Running redemption from a GitHub Action is possible (`workflow_dispatch` input) but the runner's cold-start can eat most of the 2-minute window — **running locally is recommended**.
