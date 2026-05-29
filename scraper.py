import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re

# ─── CONFIG (set these as GitHub Secrets) ───────────────────────────
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")   # Your ntfy topic name
CODES_FILE = "known_codes.json"

# ─── SCRAPE SOURCES ──────────────────────────────────────────────────
SOURCES = [
    {
        "name": "Pocket Tactics",
        "url": "https://www.pockettactics.com/afk-arena/codes",
    },
    {
        "name": "Dexerto",
        "url": "https://www.dexerto.com/gaming/afk-arena-codes-may-2021-how-to-redeem-rewards-more-1569624/",
    },
    {
        "name": "Beebom",
        "url": "https://beebom.com/afk-arena-codes/",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}

# ─── HELPERS ─────────────────────────────────────────────────────────
def load_known_codes():
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            return json.load(f)
    return {"all": []}

def save_known_codes(codes):
    with open(CODES_FILE, "w") as f:
        json.dump(codes, f, indent=2)

def extract_codes_from_text(text):
    pattern = r'\b[A-Z0-9]{6,16}\b'
    candidates = re.findall(pattern, text)
    exclude = {"ARENA", "HERO", "CODE", "FREE", "CLICK", "HERE", "MORE", "VIEW",
               "GAMES", "LILITH", "SERVER", "CLASSIC", "COMPANIONS", "DIAMOND",
               "SCROLL", "EMBLEM", "HTML", "HTTP", "HTTPS", "NULL", "TRUE", "FALSE"}
    return [c for c in candidates if c not in exclude and len(c) >= 8]

def scrape_source(source):
    results = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ")

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            is_companions = "companion" in line.lower()
            is_classic = "classic" in line.lower() and not is_companions
            codes_in_line = extract_codes_from_text(line.upper())

            for code in codes_in_line:
                results.append({
                    "code": code,
                    "source": source["name"],
                    "context": line[:120],
                    "server": "companions" if is_companions else ("classic" if is_classic else "unknown"),
                    "found_at": datetime.utcnow().isoformat()
                })
    except Exception as e:
        print(f"[!] Error scraping {source['name']}: {e}")
    return results

def send_ntfy(new_codes):
    if not NTFY_TOPIC:
        print("[!] NTFY_TOPIC not set, skipping notification.")
        return

    companions = [c for c in new_codes if c["server"] in ("companions", "unknown")]
    classic = [c for c in new_codes if c["server"] == "classic"]

    # Build message
    lines = [f"🎮 AFK Arena — {len(new_codes)} new code(s)!\n"]

    if companions:
        lines.append("👥 COMPANIONS SERVER:")
        for c in companions:
            lines.append(f"  ➜ {c['code']}  ({c['source']})")

    if classic:
        lines.append("\n⚔️ CLASSIC SERVER:")
        for c in classic:
            lines.append(f"  ➜ {c['code']}  ({c['source']})")

    lines.append("\n🔗 Redeem: cdkey.lilithgames.com/act/afk-gift")
    lines.append("⚡ Redeem quickly before they expire!")

    message = "\n".join(lines)

    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": f"🎮 AFK Arena {len(new_codes)} New Code(s)!",
                "Priority": "high",
                "Tags": "video_game,gift",
            },
            timeout=10
        )
        print(f"[✓] ntfy notification sent with {len(new_codes)} new codes!")
    except Exception as e:
        print(f"[!] Failed to send ntfy notification: {e}")

# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    print(f"[*] Starting AFK Arena code scraper at {datetime.utcnow()} UTC")
    known = load_known_codes()
    all_known = set(known.get("all", []))

    all_found = []
    for source in SOURCES:
        print(f"[*] Scraping {source['name']}...")
        found = scrape_source(source)
        all_found.extend(found)
        print(f"    → Found {len(found)} code candidates")

    # Deduplicate
    seen = set()
    unique_found = []
    for entry in all_found:
        if entry["code"] not in seen:
            seen.add(entry["code"])
            unique_found.append(entry)

    # Find new codes
    new_codes = [c for c in unique_found if c["code"] not in all_known]

    if new_codes:
        print(f"[✓] {len(new_codes)} NEW code(s): {[c['code'] for c in new_codes]}")
        send_ntfy(new_codes)
        for c in new_codes:
            all_known.add(c["code"])
        known["all"] = list(all_known)
        save_known_codes(known)
    else:
        print("[=] No new codes found.")

    print("[*] Done.")

if __name__ == "__main__":
    main()
