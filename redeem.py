"""On-demand auto-redeemer for AFK Arena gift codes (F1 + F2).

Redemption needs an in-game verification code that rotates every 2 minutes,
so this can't run on the unattended cron — you trigger it and hand it a fresh
code. A single verified session redeems ALL pending codes at once.

Usage:
    AFK_PLAYER_UID=<your_uid> python redeem.py <verification_code>

Get the verification code in-game: tap your profile → Settings → Verification Code.

Endpoints/flow mirror the community wrapper github.com/scragly/afkarena (unofficial).
"""
import os
import sys

import requests

from scraper import load_store, save_store, update_readme, now_iso

BASE = "https://cdkey.lilith.com/api/"
GAME = "afk"

# Map the API's `info` string to a code status (F2).
STATUS_BY_INFO = {
    "ok": "claimed",
    "err_cdkey_batch_error": "claimed",     # already redeemed on this account
    "err_cdkey_expired": "expired",
    "err_cdkey_record_not_found": "invalid",
}

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 Chrome/120.0 Safari/537.36")


def _post(session, uid, endpoint, **extra):
    payload = {"game": GAME, "uid": int(uid)}
    payload.update(extra)
    resp = session.post(BASE + endpoint, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    uid = os.environ.get("AFK_PLAYER_UID")
    if not uid:
        print("[!] AFK_PLAYER_UID not set. Export it or add it as a GitHub Secret.")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Usage: AFK_PLAYER_UID=<uid> python redeem.py <verification_code>")
        sys.exit(1)
    verification_code = sys.argv[1].strip()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 1) Verify — establishes the session cookie used by every redeem call.
    try:
        v = _post(session, uid, "verify-afk-code", code=str(verification_code))
    except requests.RequestException as e:
        print(f"[!] Verification request failed: {e}")
        sys.exit(1)

    if v.get("info") != "ok":
        info = v.get("info", "unknown")
        print(f"[!] Verification failed: {info}")
        if info in ("err_wrong_code", "err_code_must_be_valid_string"):
            print("    The verification code is wrong or expired (it rotates every "
                  "2 minutes). Grab a fresh one in-game and re-run quickly.")
        elif info == "err_uid_must_be_number":
            print("    AFK_PLAYER_UID must be your numeric in-game UID.")
        sys.exit(1)

    print(f"[✓] Verified UID {uid}. Redeeming pending codes...")

    # 2) Redeem every pending code in this one session.
    store = load_store()
    pending = [c for c, e in store["codes"].items() if e.get("status") == "pending"]
    if not pending:
        print("[=] No pending codes to redeem.")
        return

    claimed = 0
    for code in pending:
        try:
            r = _post(session, uid, "cd-key/consume", type="cdkey_web", cdkey=code)
        except requests.RequestException as e:
            print(f"   {code}: request error ({e}) — leaving as pending")
            continue

        info = r.get("info", "")
        if info == "err_login_state_out_of_date":
            print("[!] Session expired mid-run. Re-run with a fresh verification code.")
            break

        status = STATUS_BY_INFO.get(info, "claimed" if info == "ok" else "invalid")
        entry = store["codes"][code]
        entry["status"] = status
        entry["last_redeem_result"] = info or "ok"
        entry["last_checked"] = now_iso()
        if status == "claimed":
            claimed += 1
        print(f"   {code}: {status} ({info or 'ok'})")

    save_store(store)
    update_readme(store)
    print(f"[*] Done. {claimed}/{len(pending)} code(s) claimed. Rewards land in your in-game mail.")


if __name__ == "__main__":
    main()
