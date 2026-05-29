"""On-demand auto-redeemer for AFK Arena gift codes (F1 + F2).

Redemption needs an in-game verification code that rotates every ~2 minutes, so
this can't run on the unattended cron — you trigger it and hand it a fresh code.
A single verified session redeems all of your server's pending codes at once.

Usage:
    AFK_PLAYER_UID=<uid> [AFK_SERVER=companions|classic] python redeem.py [code]

If you omit the code it prompts for it (so the request fires the instant you
paste — important, since the code rotates every ~2 min).

Get the verification code in-game: profile → Settings → Verification Code.

Flow/endpoints reverse-engineered from the live site cdkey.lilith.com/afk-global:
  verify-afk-code → get-role-list → consume.  AFK Arena's two servers don't share
  codes and use different `game` values: Classic="afk", Companions="afkgroup".
"""
import os
import sys
import time

import requests

from scraper import load_store, save_store, update_readme, now_iso

BASE = "https://cdkey.lilith.com/api/"
AFK_APP_ID = "10046"                                   # AFK Arena's app id (from site JS)
SERVERS = {"classic": "afk", "companions": "afkgroup"}  # server name -> `game` value

# Map the API's `info` string to a code status (F2).
STATUS_BY_INFO = {
    "ok": "claimed",
    "err_cdkey_batch_error": "claimed",     # already redeemed on this account
    "err_cdkey_expired": "expired",
    "err_cdkey_record_not_found": "invalid",
}
# `info` values we understand as a per-code redeem outcome. Anything else from
# /consume means a structural problem (wrong params/endpoint), not a code result.
CODE_RESULT_INFOS = set(STATUS_BY_INFO) | {"err_login_state_out_of_date"}

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 Chrome/120.0 Safari/537.36")

# The API throttles rapid redeems (err_freq_limit). The login token is valid for
# ~3 hours, so we can afford to pace ourselves and back off when rate-limited.
REDEEM_DELAY = 4        # seconds between consume calls
FREQ_BACKOFF = 15       # extra wait after hitting err_freq_limit
MAX_FREQ_RETRIES = 3


def _post(session, endpoint, payload):
    """POST and return (status_code, parsed_json). Do NOT raise on 4xx/5xx —
    Lilith returns its real error in the JSON body even on a 400."""
    resp = session.post(BASE + endpoint, json=payload, timeout=15)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        raise RuntimeError(f"HTTP {resp.status_code} (non-JSON): {resp.text[:400]!r}")


def _get(session, endpoint, params):
    resp = session.get(BASE + endpoint, params=params, timeout=15)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        raise RuntimeError(f"HTTP {resp.status_code} (non-JSON): {resp.text[:400]!r}")


def main():
    uid = os.environ.get("AFK_PLAYER_UID")
    if not uid:
        print("[!] AFK_PLAYER_UID not set. Export it or add it as a GitHub Secret.")
        sys.exit(1)

    server = os.environ.get("AFK_SERVER", "companions").strip().lower()
    if server not in SERVERS:
        print(f"[!] AFK_SERVER must be one of {list(SERVERS)} (got {server!r}).")
        sys.exit(1)
    game = SERVERS[server]

    # Set everything up BEFORE asking for the code, so the verify request fires
    # the instant it's pasted (the code rotates every ~2 minutes).
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://cdkey.lilith.com",
        "Referer": "https://cdkey.lilith.com/afk-global",
    })

    if len(sys.argv) >= 2:
        verification_code = sys.argv[1].strip()
    else:
        print(f"UID: {uid}   Server: {server} (game={game})")
        print("In-game: profile → Settings → Verification Code (changes every ~2 min).")
        verification_code = input("Paste the verification code and press Enter: ").strip()
    if not verification_code:
        print("[!] No verification code provided.")
        sys.exit(1)

    # 1) Verify — establishes the session cookie used by the later calls.
    try:
        vstatus, v = _post(session, "verify-afk-code",
                           {"game": game, "uid": int(uid), "code": str(verification_code)})
    except (requests.RequestException, RuntimeError) as e:
        print(f"[!] Verification request failed: {e}")
        sys.exit(1)

    print(f"[i] verify-afk-code → HTTP {vstatus}: {v}")
    if v.get("info") != "ok":
        info = v.get("info", "unknown")
        print(f"[!] Verification failed: {info}")
        if info in ("err_wrong_code", "err_code_must_be_valid_string"):
            print("    → Code wrong/expired (rotates every 2 min), or wrong server. "
                  f"You're targeting '{server}'. Grab a fresh code and re-run.")
        elif info == "err_uid_must_be_number":
            print("    → AFK_PLAYER_UID must be your numeric in-game UID.")
        sys.exit(1)

    print(f"[✓] Verified UID {uid} on {server}.")

    # Use the returned token for auth on the follow-up calls (alongside cookies).
    token = (v.get("data") or {}).get("token")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    # For AFK the role id is just the UID (the role-list call needs a pup_body we
    # don't have, and consume already accepts roleId=uid).
    role_id = str(uid)

    # Redeem this server's pending codes (codes don't cross servers), trying this
    # server's own codes first for the clearest signal.
    store = load_store()
    allowed = {"unknown", "all", server}
    pending = [c for c, e in store["codes"].items()
               if e.get("status") == "pending" and e.get("server", "unknown") in allowed]
    pending.sort(key=lambda c: store["codes"][c].get("server", "unknown") != server)
    if not pending:
        print(f"[=] No pending {server} codes to redeem.")
        return
    print(f"[*] Redeeming {len(pending)} pending {server} code(s)...")

    claimed = channel_errs = rate_limited = 0
    for idx, code in enumerate(pending):
        if idx:
            time.sleep(REDEEM_DELAY)

        # Redeem, backing off and retrying if the API rate-limits us.
        r = None
        for attempt in range(MAX_FREQ_RETRIES + 1):
            try:
                cstatus, r = _post(session, "consume", {
                    "appId": AFK_APP_ID, "game": game, "roleId": role_id, "cdkey": code,
                })
            except (requests.RequestException, RuntimeError) as e:
                print(f"   {code}: request error ({e}) — leaving as pending")
                r = None
                break
            if r.get("info") != "err_freq_limit" or attempt == MAX_FREQ_RETRIES:
                break
            print(f"   {code}: rate-limited, waiting {FREQ_BACKOFF}s and retrying...")
            time.sleep(FREQ_BACKOFF)
        if r is None:
            continue

        info = r.get("info", "")
        if idx < 2:
            print(f"[i] consume[{code}] → HTTP {cstatus}: {r}")

        if info == "err_login_state_out_of_date":
            print("[!] Session expired mid-run. Re-run with a fresh verification code.")
            break
        if info == "err_freq_limit":
            rate_limited += 1
            print(f"   {code}: still rate-limited — left pending, run again later")
            continue
        if info == "err_cdkey_channel_error":
            # Code belongs to a different server/channel — leave it pending, keep going.
            channel_errs += 1
            print(f"   {code}: skipped (channel error — likely the other server's code)")
            continue
        if info not in CODE_RESULT_INFOS:
            # Unrecognised result → the consume request shape is wrong. Stop without
            # corrupting statuses; share this output to finish the fix.
            print(f"[!] Unexpected /consume response for {code}: {r}")
            print("    (Stopping — paste this output so I can adjust the payload.)")
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
    summary = f"[*] Done. {claimed}/{len(pending)} claimed"
    if channel_errs:
        summary += f", {channel_errs} other-server"
    if rate_limited:
        summary += f", {rate_limited} rate-limited (left pending)"
    print(summary + ". Rewards land in your in-game mail.")


if __name__ == "__main__":
    main()
