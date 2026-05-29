import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re

# ─── CONFIG (set these as GitHub Secrets) ───────────────────────────
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")   # Your ntfy topic name
CODES_FILE = "known_codes.json"
README_FILE = "README.md"

# Markers in README.md between which the live codes table is rendered (F3).
CODES_START = "<!-- CODES:START -->"
CODES_END = "<!-- CODES:END -->"

# Codes that never expire — seeded so the live list and redeemer always know them.
PERMANENT_CODES = {
    "afk888": "Permanent code",
    "misevj66yi": "Permanent code",
    "uf4shqjngq": "Permanent code",
}

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

# Reward phrases to pull out of the text around a code (F4).
REWARD_RE = re.compile(
    r'(\d[\d,\.]*\s*[kKmM]?)\s*(?:x\s*)?'
    r'(diamonds?|gold|hero(?:\'s)? essence|(?:common\s+|elite\s+)?hero(?:\'s)? scrolls?|'
    r'scrolls?|soulstones?|dust|emblems?|gems?|stars?|companion points?|dim crystals?)\b',
    re.IGNORECASE,
)

EXCLUDE = {"ARENA", "HERO", "CODE", "FREE", "CLICK", "HERE", "MORE", "VIEW",
           "GAMES", "LILITH", "SERVER", "CLASSIC", "COMPANIONS", "DIAMOND",
           "DIAMONDS", "SCROLL", "SCROLLS", "EMBLEM", "EMBLEMS", "HTML",
           "HTTP", "HTTPS", "NULL", "TRUE", "FALSE", "REDEEM", "REWARDS"}

# ─── HELPERS ─────────────────────────────────────────────────────────
def now_iso():
    return datetime.utcnow().isoformat()


def _new_entry(source="", server="unknown", reward="", context="", permanent=False):
    return {
        "source": source,
        "server": server,
        "reward": reward,
        "context": context,
        "first_seen": now_iso(),
        "status": "pending",        # pending | claimed | expired | invalid
        "last_redeem_result": "",
        "last_checked": "",
        "permanent": permanent,
    }


def _seed_permanent(store):
    for code, reward in PERMANENT_CODES.items():
        if not _code_present(store, code):
            store["codes"][code] = _new_entry(
                source="known", server="all", reward=reward, permanent=True
            )


def _code_present(store, code):
    """Case-insensitive membership check (redemption codes are case-sensitive,
    but we never want two entries that differ only by case)."""
    lowered = code.lower()
    return any(k.lower() == lowered for k in store["codes"])


def load_store():
    """Load known_codes.json, migrating the legacy {"all": [...]} format."""
    store = {"codes": {}}
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict) and "codes" in data:
            store = data
        else:  # legacy list of plain code strings
            for code in data.get("all", []):
                store["codes"][code] = _new_entry(source="legacy")
    _seed_permanent(store)
    return store


def save_store(store):
    with open(CODES_FILE, "w") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def extract_reward(text):
    parts, seen = [], set()
    for num, kw in REWARD_RE.findall(text):
        phrase = f"{num.strip()} {kw.strip()}"
        key = phrase.lower()
        if key not in seen:
            seen.add(key)
            parts.append(phrase)
    return ", ".join(parts)


CODE_RE = re.compile(r'\b[A-Za-z0-9]{6,16}\b')


def candidate_codes(text):
    """Yield (code, start_index) for code-like tokens, preserving original case
    (redemption codes are case-sensitive). Requiring a digit cheaply rejects the
    flood of plain English words that scraping raw page text would otherwise emit."""
    for m in CODE_RE.finditer(text):
        c = m.group()
        if len(c) < 8 or c.upper() in EXCLUDE:
            continue
        if not any(ch.isdigit() for ch in c):
            continue
        yield c, m.start()


def scrape_source(source):
    results = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ")

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            is_companions = "companion" in line.lower()
            is_classic = "classic" in line.lower() and not is_companions

            for code, pos in candidate_codes(line):
                # Associate the reward that follows the code on the same line.
                results.append({
                    "code": code,
                    "source": source["name"],
                    "context": line[max(0, pos - 10):pos + 90],
                    "reward": extract_reward(line[pos:pos + 90]),
                    "server": "companions" if is_companions else ("classic" if is_classic else "unknown"),
                })
    except Exception as e:
        print(f"[!] Error scraping {source['name']}: {e}")
    return results


# ─── LIVE CODES LIST (F3) ────────────────────────────────────────────
def render_codes_table(store):
    rows = []
    for code, e in sorted(store["codes"].items(), key=lambda kv: kv[0].lower()):
        if e.get("status") in ("expired", "invalid"):
            continue
        reward = e.get("reward") or "—"
        server = e.get("server", "unknown")
        status = e.get("status", "pending")
        tag = " 🔒" if e.get("permanent") else ""
        rows.append(f"| `{code}`{tag} | {server} | {reward} | {status} |")
    header = "| Code | Server | Reward | Status |\n|---|---|---|---|"
    body = "\n".join(rows) if rows else "| _none yet_ | | | |"
    return f"{header}\n{body}\n\n_Last updated: {now_iso()} UTC · 🔒 = permanent_"


def update_readme(store, path=README_FILE):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        content = f.read()
    if CODES_START not in content or CODES_END not in content:
        return
    block = f"{CODES_START}\n{render_codes_table(store)}\n{CODES_END}"
    pattern = re.escape(CODES_START) + r".*?" + re.escape(CODES_END)
    new_content = re.sub(pattern, lambda _m: block, content, flags=re.DOTALL)
    if new_content != content:
        with open(path, "w") as f:
            f.write(new_content)


# ─── NOTIFICATIONS ───────────────────────────────────────────────────
def send_ntfy(new_codes):
    if not NTFY_TOPIC:
        print("[!] NTFY_TOPIC not set, skipping notification.")
        return

    companions = [c for c in new_codes if c["server"] in ("companions", "unknown", "all")]
    classic = [c for c in new_codes if c["server"] == "classic"]

    def fmt(c):
        reward = f"  →  {c['reward']}" if c.get("reward") else ""
        return f"  ➜ {c['code']}  ({c['source']}){reward}"

    lines = [f"🎮 AFK Arena — {len(new_codes)} new code(s)!\n"]
    if companions:
        lines.append("👥 COMPANIONS SERVER:")
        lines.extend(fmt(c) for c in companions)
    if classic:
        lines.append("\n⚔️ CLASSIC SERVER:")
        lines.extend(fmt(c) for c in classic)

    lines.append("\n🔗 Redeem: cdkey.lilith.com/afk-global")
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
    print(f"[*] Starting AFK Arena code scraper at {now_iso()} UTC")
    store = load_store()

    all_found = []
    for source in SOURCES:
        print(f"[*] Scraping {source['name']}...")
        found = scrape_source(source)
        all_found.extend(found)
        print(f"    → Found {len(found)} code candidates")

    # Deduplicate within this run (case-insensitive), keeping the first sighting.
    seen, unique_found = set(), []
    for entry in all_found:
        key = entry["code"].lower()
        if key not in seen:
            seen.add(key)
            unique_found.append(entry)

    # New = not already tracked in the store.
    new_codes = [c for c in unique_found if not _code_present(store, c["code"])]

    if new_codes:
        print(f"[✓] {len(new_codes)} NEW code(s): {[c['code'] for c in new_codes]}")
        for c in new_codes:
            store["codes"][c["code"]] = _new_entry(
                source=c["source"], server=c["server"],
                reward=c["reward"], context=c["context"],
            )
        send_ntfy(new_codes)
        save_store(store)
    else:
        print("[=] No new codes found.")

    # Always refresh the live list so README/JSON stay in sync.
    update_readme(store)
    print("[*] Done.")


if __name__ == "__main__":
    main()
