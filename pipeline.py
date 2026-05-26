"""
Deal pipeline — tracks every deal from lead to sold.
Usage:
  python3 pipeline.py            → show all active deals
  python3 pipeline.py add        → add a new deal
  python3 pipeline.py update     → update a deal's status
  python3 pipeline.py sold       → mark a deal as sold (logs profit)
  python3 pipeline.py bulk       → paste many past flips at once
  python3 pipeline.py summary    → AI summary of your pipeline
"""
import json, os, sys
from datetime import datetime
import anthropic
from config import ANTHROPIC_API_KEY

PIPELINE_FILE = "pipeline.json"
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

STAGES = ["lead", "offer_out", "negotiating", "deal_pending", "owned", "listed", "sold"]
STAGE_LABELS = {
    "lead":        "🔍 Lead",
    "offer_out":   "📤 Offer Out",
    "negotiating": "💬 Negotiating",
    "deal_pending":"🤝 Deal Pending",
    "owned":       "🏠 Owned / In Stock",
    "listed":      "📢 Listed for Sale",
    "sold":        "✅ Sold",
}


def load() -> list:
    if os.path.exists(PIPELINE_FILE):
        with open(PIPELINE_FILE) as f:
            return json.load(f)
    return []

def save(deals: list):
    with open(PIPELINE_FILE, "w") as f:
        json.dump(deals, f, indent=2)

def next_id(deals: list) -> int:
    int_ids = [d["id"] for d in deals if isinstance(d.get("id"), int)]
    return max(int_ids, default=0) + 1

def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def show_pipeline(deals: list):
    active = [d for d in deals if d["stage"] != "sold"]
    sold = [d for d in deals if d["stage"] == "sold"]

    if not active and not sold:
        print("\nPipeline is empty. Run: python3 pipeline.py add\n")
        return

    print("\n" + "="*65)
    print("  DEAL PIPELINE")
    print("="*65)

    for stage in STAGES:
        stage_deals = [d for d in active if d["stage"] == stage]
        if not stage_deals:
            continue
        print(f"\n{STAGE_LABELS[stage]}")
        print("─" * 65)
        for d in stage_deals:
            profit_str = ""
            if d.get("buy_price") and d.get("ask_price"):
                est_profit = int(d["ask_price"]) - int(d["buy_price"])
                profit_str = f"  |  Est. profit: ${est_profit:,}"
            print(f"  #{d['id']}  {d['title']}")
            print(f"       Buy: ${d.get('buy_price','?')}  |  Listing: ${d.get('ask_price','?')}{profit_str}")
            if d.get("notes"):
                print(f"       Note: {d['notes']}")
            print(f"       Added: {d['added']}  |  Updated: {d['updated']}")

    if sold:
        total_profit = sum(
            (d.get("sold_price", 0) or 0) - (d.get("buy_price", 0) or 0)
            for d in sold
            if d.get("sold_price") and d.get("buy_price")
        )
        print(f"\n{STAGE_LABELS['sold']}  ({len(sold)} deals | Total profit: ${total_profit:,})")
        print("─" * 65)
        for d in sold[-5:]:  # show last 5
            profit = (d.get("sold_price", 0) or 0) - (d.get("buy_price", 0) or 0)
            print(f"  #{d['id']}  {d['title']}  →  Profit: ${profit:,}")

    print()


def add_deal(deals: list):
    print("\n── ADD NEW DEAL ──")
    title = input("What is it? (e.g. '2021 Sur Ron Light Bee X'): ").strip()
    url = input("Facebook URL (press Enter to skip): ").strip()
    buy_price = input("Your offer / buy price ($): ").strip()
    ask_price = input("Your planned listing price ($, press Enter to skip): ").strip()
    notes = input("Notes (press Enter to skip): ").strip()

    deal = {
        "id": next_id(deals),
        "title": title,
        "url": url or None,
        "buy_price": int(buy_price) if buy_price.isdigit() else None,
        "ask_price": int(ask_price) if ask_price.isdigit() else None,
        "sold_price": None,
        "stage": "lead",
        "notes": notes or None,
        "added": now(),
        "updated": now(),
    }
    deals.append(deal)
    save(deals)
    print(f"\n✅ Added deal #{deal['id']}: {title}\n")


def update_deal(deals: list):
    show_pipeline(deals)
    active = [d for d in deals if d["stage"] != "sold"]
    if not active:
        return

    try:
        deal_id = int(input("Enter deal # to update: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    deal = next((d for d in deals if d["id"] == deal_id), None)
    if not deal:
        print(f"Deal #{deal_id} not found.")
        return

    print(f"\nUpdating: {deal['title']}  (current stage: {STAGE_LABELS[deal['stage']]})")
    print("\nStages:")
    for i, s in enumerate(STAGES[:-1], 1):  # exclude sold
        print(f"  {i}. {STAGE_LABELS[s]}")

    choice = input("\nNew stage number (press Enter to keep current): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(STAGES) - 1:
        deal["stage"] = STAGES[int(choice) - 1]

    notes = input(f"Notes (current: {deal.get('notes','none')}): ").strip()
    if notes:
        deal["notes"] = notes

    ask = input(f"Update listing price (current: ${deal.get('ask_price','?')}): ").strip()
    if ask.isdigit():
        deal["ask_price"] = int(ask)

    deal["updated"] = now()
    save(deals)
    print(f"\n✅ Deal #{deal_id} updated.\n")


def mark_sold(deals: list):
    show_pipeline(deals)
    try:
        deal_id = int(input("Enter deal # to mark as sold: ").strip())
    except ValueError:
        print("Invalid ID.")
        return

    deal = next((d for d in deals if d["id"] == deal_id), None)
    if not deal:
        print(f"Deal #{deal_id} not found.")
        return

    sold_price = input(f"Sold for how much? (buy price was ${deal.get('buy_price','?')}): ").strip()
    if sold_price.isdigit():
        deal["sold_price"] = int(sold_price)
        if deal.get("buy_price"):
            profit = int(sold_price) - deal["buy_price"]
            print(f"\n💰 Profit on this deal: ${profit:,}")

    deal["stage"] = "sold"
    deal["updated"] = now()
    save(deals)
    print(f"\n✅ Deal #{deal_id} marked as sold.\n")


def bulk_add(deals: list):
    print("\n── BULK ADD PAST FLIPS ──")
    print("Paste your flips, ONE PER LINE, in this format:")
    print("  Title | buy_price | sold_price | date(optional, YYYY-MM or YYYY-MM-DD)")
    print("\nExamples:")
    print("  2022 KTM 250 | 3200 | 4500 | 2025-08")
    print("  2020 CRF250R | 2400 | 3800")
    print("  2019 Sur Ron LBX | 2800 | 4200 | 2024-11-15")
    print("\nWhen done, press Ctrl-D (Mac/Linux) on a blank line.\n")

    lines = sys.stdin.read().strip().splitlines()
    added = 0
    skipped = 0
    total_profit = 0

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            print(f"  ⚠ Skipped (need at least 3 fields): {line}")
            skipped += 1
            continue

        title = parts[0]
        try:
            buy = int(parts[1].replace("$", "").replace(",", ""))
            sold = int(parts[2].replace("$", "").replace(",", ""))
        except ValueError:
            print(f"  ⚠ Skipped (bad price): {line}")
            skipped += 1
            continue

        date_str = parts[3] if len(parts) >= 4 and parts[3] else now()
        if len(date_str) == 7:  # YYYY-MM
            date_str = date_str + "-01"

        deal = {
            "id": next_id(deals),
            "title": title,
            "url": None,
            "buy_price": buy,
            "ask_price": sold,
            "sold_price": sold,
            "stage": "sold",
            "notes": "Bulk-imported past flip",
            "added": date_str,
            "updated": date_str,
        }
        deals.append(deal)
        profit = sold - buy
        total_profit += profit
        added += 1
        print(f"  ✓ #{deal['id']}: {title}  →  +${profit:,}")

    save(deals)
    print(f"\n✅ Added {added} past flips. Total profit logged: ${total_profit:,}")
    if skipped:
        print(f"   ({skipped} lines skipped — fix format and re-run for those)")
    print()


def ai_summary(deals: list):
    active = [d for d in deals if d["stage"] != "sold"]
    sold_30 = [d for d in deals if d["stage"] == "sold"][-10:]

    if not active and not sold_30:
        print("No deals to summarize yet.")
        return

    pipeline_text = json.dumps({"active": active, "recent_sold": sold_30}, indent=2)

    print("\nGenerating AI summary...\n")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": f"""You are helping a bike reseller review their deal pipeline.

Pipeline data:
{pipeline_text}

Give a brief summary (5-8 bullet points):
- Which deals need immediate action
- Which are moving well
- Any deals that look stalled or risky
- Total estimated profit if all active deals close
- One actionable recommendation

Be direct and specific. Use deal titles, not IDs."""}]
    )
    print("─" * 60)
    print(response.content[0].text.strip())
    print("─" * 60 + "\n")


def main():
    deals = load()
    args = sys.argv[1:]
    cmd = args[0] if args else ""

    if cmd == "add":
        add_deal(deals)
    elif cmd == "update":
        update_deal(deals)
    elif cmd == "sold":
        mark_sold(deals)
    elif cmd == "bulk":
        bulk_add(deals)
    elif cmd == "summary":
        ai_summary(deals)
    else:
        show_pipeline(deals)


if __name__ == "__main__":
    main()
