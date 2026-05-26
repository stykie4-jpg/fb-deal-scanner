"""
Suggested opener generator — writes AI opening messages for Aidan to copy/paste.
No longer auto-sends (FB ban risk + unreliable selector matching).
"""
import re
import anthropic
from config import ANTHROPIC_API_KEY, AUTO_MESSAGE_MIN_SCORE

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_opener(listing) -> str:
    analysis = listing.get("analysis", {})
    asking = listing.get("price", "")
    recommended = analysis.get("recommended_offer", "")
    title = listing.get("title", "")

    price_match = re.search(r'[\d,]+', recommended.replace("$", "").replace(",", ""))
    if price_match:
        rec = int(price_match.group().replace(",", ""))
        opener_price = int(rec * 0.88)
    else:
        ask_match = re.search(r'[\d,]+', asking.replace("$", "").replace(",", ""))
        opener_price = int(int(ask_match.group()) * 0.72) if ask_match else None

    price_str = f"${opener_price:,}" if opener_price else "a fair number"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        timeout=15.0,
        messages=[{"role": "user", "content": f"""Write a first message to send on Facebook Marketplace to buy this bike.

Listing: {title}
Asking: {asking}
My opening offer: {price_str}

Rules:
- Sound like a regular person buying for personal use, NOT a dealer
- 1-2 sentences MAX — keep it short
- Include the specific price
- Mention cash and fast pickup
- Casual, no formalities, no "I hope this message finds you well" BS
- Good example: "Hey is this still available? I can do $X cash and come grab it this weekend"

Reply ONLY with the message text, nothing else."""}]
    )
    return response.content[0].text.strip().strip('"')


def attach_suggested_openers(deals: list) -> list:
    """Attach a copy/paste-ready opener to deals scoring AUTO_MESSAGE_MIN_SCORE+."""
    qualifying = [d for d in deals if d.get("deal_score", 0) >= AUTO_MESSAGE_MIN_SCORE]
    if not qualifying:
        print("No deals above suggested-opener threshold.\n")
        return deals

    print(f"Generating openers for {len(qualifying)} deal(s)...\n")
    for deal in qualifying:
        try:
            deal["suggested_opener"] = generate_opener(deal)
            print(f"  [{deal.get('deal_score')}/10] {deal.get('title','')[:60]}")
            print(f"    → {deal['suggested_opener']}\n")
        except Exception as e:
            print(f"  Opener generation failed: {e}")
    return deals
