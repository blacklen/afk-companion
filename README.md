# 🎮 AFK Arena Code Tracker (ntfy)

Automatically scrapes and sends push notifications via **ntfy.sh** whenever new codes are available for AFK Arena.

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
