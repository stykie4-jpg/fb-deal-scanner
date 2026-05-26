import anthropic, json, os, re, base64
import urllib.request
from config import ANTHROPIC_API_KEY, RESALE_CONTEXT, MIN_DEAL_SCORE, MIN_PROFIT_DOLLARS


def extract_year(*texts) -> str | None:
    """Pull a 4-digit model year (1980-2026) out of the title/description."""
    for t in texts:
        if not t:
            continue
        m = re.search(r"\b(19[89]\d|20[0-2]\d)\b", t)
        if m:
            return m.group(1)
    return None


def _parse_profit_max(s: str) -> int:
    """Pull the max dollar amount out of a profit string like '$800-$1,500' or '~$1200'.
    Returns 0 if nothing parseable."""
    if not s:
        return 0
    nums = re.findall(r"\d[\d,]*", str(s).replace(",", ""))
    if not nums:
        return 0
    try:
        return max(int(n) for n in nums)
    except Exception:
        return 0


def _fetch_image_b64(url: str, max_bytes: int = 2_000_000) -> tuple[str, str] | None:
    """Download a listing thumbnail and return (media_type, base64). Returns None on failure.
    FB CDN sometimes 403s direct URL fetches from non-browser UAs, so spoof a UA."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
        })
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None
            ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if ct not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                ct = "image/jpeg"
            return ct, base64.standard_b64encode(data).decode("ascii")
    except Exception:
        return None


def _extract_json(raw: str) -> dict | None:
    """Robustly extract a JSON object from an LLM response.
    Handles ```json fences, leading prose, trailing prose, and minor format issues."""
    if not raw:
        return None
    # Strip markdown code fences
    s = raw.replace("```json", "").replace("```", "").strip()
    # Find the outermost { ... } span
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    blob = s[start:end + 1]
    # First try: strict parse
    try:
        return json.loads(blob)
    except Exception:
        pass
    # Second try: kill trailing commas before closers
    repaired = re.sub(r",\s*([}\]])", r"\1", blob)
    try:
        return json.loads(repaired)
    except Exception:
        pass
    # Third try: collapse stray newlines inside string values (common Sonnet quirk)
    collapsed = re.sub(r"(\".*?[^\\])\n(.*?\")", r"\1 \2", repaired, flags=re.S)
    try:
        return json.loads(collapsed)
    except Exception:
        return None

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
BASE = os.path.dirname(__file__)


def current_capital_snapshot() -> str:
    """Build a live snapshot of Aidan's current inventory + capital position from pipeline.json.
    Injected into every analysis so the AI factors trade routes and cash-on-hand into recommendations."""
    path = os.path.join(BASE, "pipeline.json")
    if not os.path.exists(path):
        return ""
    try:
        with open(path) as f:
            pipe = json.load(f)
    except Exception:
        return ""
    active = [d for d in pipe if d.get("stage") in ("listed", "owned")]
    if not active:
        return ""
    lines = ["CURRENT INVENTORY (cash tied up here — consider trade routes):"]
    total_in = 0
    for b in active:
        buy = b.get("buy_price") or 0
        ask = b.get("ask_price") or 0
        total_in += buy
        floor_hint = int(ask * 0.85) if ask else 0
        lines.append(f"  • {b.get('title','?')} — paid ${buy:,}, asking ${ask:,} (would take ~${floor_hint:,})")
    lines.append(f"TOTAL TIED UP: ${total_in:,}. Until something sells, prioritize either (a) deals so good they justify draining cash, or (b) trades using bikes above.")
    return "\n".join(lines)

PROMPT = """
{context}

═══════════════════════════════════════
LIVE CAPITAL POSITION
═══════════════════════════════════════
{capital}

═══════════════════════════════════════
NOW ANALYZE THIS LISTING
═══════════════════════════════════════
Analyze this Facebook Marketplace listing as a resale deal.

Title: {title}
Detected Year: {year}
Price: {price}
Location: {location}
Description: {description}
URL: {url}

A photo of the item may be attached above. LOOK AT IT before answering — condition, modifications, damage, scams, and seller-type signals are all in the photo.

MANDATORY FIRST STEP — YEAR-BAND COMP MATCH:
- The "Detected Year" above is parsed from the title/description. If it's "unknown", scan the description yourself for a year. If still unknown, assume the OLDEST plausible year for the model and discount.
- Look up the comp range for THAT exact year band (see the year-banded comp tables in the context above). Do NOT use an average across all years — use the matching band.
- State the year-band you used in the "summary" field so a human can sanity-check.

CRITICAL RULES — READ THE DESCRIPTION CAREFULLY:

1. AUTOMATIC SCORE 1 (do NOT recommend) if the title OR description contains ANY of:
   - "missing transmission", "no transmission", "needs transmission"
   - "no engine", "missing engine", "blown motor", "blown engine", "seized"
   - "parts only", "for parts", "part out", "parting out"
   - "doesn't run", "does not run", "won't start", "wont start", "no start"
   - "salvage title", "rebuilt title", "branded title", "no title"
   - "project", "project bike", "project car" (unless price is < 20% of market)
   - "as-is", "as is" combined with any mechanical issue
   - "frame only", "roller", "no motor"
   - "stolen recovery", "theft recovery"
   - "flood", "flooded", "water damage"

2. If the price looks like a placeholder ($1, $123, $1234, $9999, $12345) — score 1.

3. If location shows more than 100 miles away — score 1.

4. If the description is vague AND price seems too good — be SKEPTICAL and score lower. Sellers usually disclose problems somewhere. Re-read for words like "needs", "issue", "problem", "but", "however".

5. Only score 8+ if the listing CLEARLY has no red flags AND price is genuinely below market.

6. TRADE BONUS: If title/description mentions "open to trades", "will trade", "trades welcome", "OBO + trades", etc. — add +1 to deal_score (Aidan has 4 bikes worth $15,600 in current inventory he can trade away). Mention the trade angle in the negotiation_tip.

7. PARTS ARBITRAGE: If the listing is a STANDALONE ebike battery / motor / controller / premium fork set for an ebike (Sur Ron, Talaria, etc.) at a low price, treat it as a flip opportunity. A Sur Ron battery for $100-$200 is a 3-6x flip. Apply the resale comps in the context.

8. OLD WORK TRUCKS (1980s-1998 single cab pickups under $3k that RUN) are proven flips in this market. Don't dismiss them just because they're old.

9. HARD PROFIT FLOOR: If your realistic max profit is under $800, you MUST cap the score at 6 (NOT recommended). Aidan does not flip for "a couple hundred bucks" — his time is worth more. Even a clean, low-risk listing with $400 of margin is a PASS.

10. CAR-SPECIFIC: For cars, asking must be at LEAST $2,000 below the year-band midpoint and the title must be clean for the deal to score 7+. Cars eat capital — don't chase 5% margins.

11. PHOTO CHECK: If a photo is attached, examine it and reflect what you see in "condition_assessment". Note specifically: visible damage, drops, rust, aftermarket parts, photo quality (stock vs real), and the staging environment (garage vs dirt lot). If the photo contradicts the description (e.g. description says "perfect" but photo shows scratched panels), call that out as a red flag.

Put EVERY mechanical issue you find in the description into "red_flags" — don't miss any.

Respond ONLY with a JSON object, no markdown:
{{
  "deal_score": <1-10>,
  "estimated_market_value": "<range>",
  "estimated_flip_profit": "<range>",
  "condition_assessment": "<brief>",
  "red_flags": ["<flag>"],
  "green_flags": ["<flag>"],
  "recommended_offer": "<price>",
  "negotiation_tip": "<one sentence>",
  "summary": "<2-3 sentences>"
}}
"""

_CAPITAL_SNAPSHOT_CACHE = None

def _capital():
    global _CAPITAL_SNAPSHOT_CACHE
    if _CAPITAL_SNAPSHOT_CACHE is None:
        _CAPITAL_SNAPSHOT_CACHE = current_capital_snapshot() or "(no current inventory loaded)"
    return _CAPITAL_SNAPSHOT_CACHE


# ─────────────────────────────────────────────────────────────
# STAGE 1: HAIKU TRIAGE — cheap filter to drop obvious junk
# Only listings that survive triage get the expensive Sonnet analysis.
# When in doubt, triage PASSES (safe default — never lose a real flip).
# ─────────────────────────────────────────────────────────────
TRIAGE_PROMPT = """You're triaging a Facebook Marketplace listing for a DC/VA/MD reseller named Aidan. Your ONLY job: decide if it's worth a full deep-dive analysis. When in doubt → PASS.

Aidan flips: motorcycles, dirt bikes, electric mini bikes (Sur Ron, Talaria, Razor), ATVs, UTVs, sport bikes, ebike parts (batteries/motors/controllers), old work trucks (pre-2000 single cab), power tools (DeWalt/Milwaukee/Makita), snowblowers, generators, trailers, jet skis, kayaks, bicycles, KitchenAid, Yeti, Big Green Egg, Traeger.

LISTING:
Title: {title}
Price: {price}
Location: {location}
Description: {description}

REJECT only if you see one of these CLEAR disqualifiers:
- "missing transmission", "no engine", "blown motor", "seized", "doesn't run", "won't start", "parts only", "for parts", "salvage title", "no title", "flood damage", "frame only"
- Price is an obvious placeholder ($1, $1234, $9999, $12345)
- Location explicitly says >100 miles away
- Listing is clearly nothing Aidan flips (e.g. baby clothes, makeup, jewelry, plants, services)
- Asking price is wildly above market for the category (e.g. $20k for an old pickup, $15k for a 250cc dirt bike)

If price is missing/unclear, or description is short/vague, or you're not sure → PASS (let Sonnet decide).

Respond with ONE WORD ONLY: either PASS or REJECT"""


def triage_listing(listing) -> bool:
    """Cheap Haiku filter. Returns True if listing should advance to Sonnet analysis."""
    try:
        prompt = TRIAGE_PROMPT.format(
            title=listing.get("title", "Unknown"),
            price=listing.get("price", "Unknown"),
            location=listing.get("location", "Unknown"),
            description=(listing.get("description") or "No description")[:1500],
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            timeout=10.0,
            messages=[{"role": "user", "content": prompt}],
        )
        verdict = response.content[0].text.strip().upper()
        if verdict.startswith("REJECT"):
            return False
        return True
    except Exception as e:
        print(f"  Triage error (passing through to Sonnet): {e}")
        return True


def analyze_listing(listing):
    try:
        year = extract_year(listing.get("title"), listing.get("description")) or "unknown"
        prompt = PROMPT.format(
            context=RESALE_CONTEXT,
            capital=_capital(),
            title=listing.get("title","Unknown"),
            year=year,
            price=listing.get("price","Unknown"),
            location=listing.get("location","Unknown"),
            description=listing.get("description","No description"),
            url=listing.get("url",""))

        # Build content blocks — attach the listing photo (vision) when we can fetch it.
        content_blocks = []
        img_url = listing.get("image_url")
        if img_url:
            img = _fetch_image_b64(img_url)
            if img:
                media_type, b64 = img
                content_blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                })
        content_blocks.append({"type": "text", "text": prompt})

        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=900,
            timeout=35.0,
            messages=[{"role": "user", "content": content_blocks}])
        raw = response.content[0].text
        analysis = _extract_json(raw)
        if analysis is None:
            print(f"  Could not parse Sonnet JSON for '{listing.get('title','?')[:50]}' — skipping. Raw start: {raw[:120]!r}")
            return None
        score = int(analysis.get("deal_score", 0))

        # Enforce hard profit floor — never ship deals with <$800 max projected profit,
        # no matter how clean the listing or how confident the model is.
        profit_max = _parse_profit_max(analysis.get("estimated_flip_profit", ""))
        if profit_max and profit_max < MIN_PROFIT_DOLLARS and score >= MIN_DEAL_SCORE:
            print(f"  '{listing['title']}' — capped: ${profit_max} max profit < ${MIN_PROFIT_DOLLARS} floor (was {score}/10)")
            score = min(score, MIN_DEAL_SCORE - 1)
            analysis["deal_score"] = score
            analysis["red_flags"] = (analysis.get("red_flags") or []) + [
                f"Profit floor: max projected ${profit_max} is below ${MIN_PROFIT_DOLLARS} threshold"
            ]

        print(f"  '{listing['title']}' [{year}] — Score: {score}/10 | Offer: {analysis.get('recommended_offer','?')} | Profit: {analysis.get('estimated_flip_profit','?')}")
        if score >= MIN_DEAL_SCORE:
            return {**listing, "analysis": analysis, "deal_score": score, "year": year}
        return None
    except Exception as e:
        print(f"  Analysis error: {e}")
        return None

def analyze_listings(listings):
    global _CAPITAL_SNAPSHOT_CACHE
    _CAPITAL_SNAPSHOT_CACHE = None  # refresh once per scan
    if not listings:
        return []

    # Stage 1: cheap Haiku triage
    print(f"Stage 1: Haiku triage on {len(listings)} listings...")
    survivors = []
    rejected = 0
    for l in listings:
        if triage_listing(l):
            survivors.append(l)
        else:
            rejected += 1
    print(f"  Triage: {len(survivors)} survived, {rejected} rejected as obvious junk.\n")

    # Stage 2: expensive Sonnet analysis on survivors only
    if not survivors:
        print("Nothing survived triage. No Sonnet calls made.\n")
        return []
    print(f"Stage 2: Sonnet deep analysis on {len(survivors)} survivors...\n")
    good_deals = [r for l in survivors if (r := analyze_listing(l))]
    good_deals.sort(key=lambda x: x["deal_score"], reverse=True)
    print(f"\n{len(good_deals)} deal(s) scored {MIN_DEAL_SCORE}+ — will be emailed.\n")
    return good_deals
