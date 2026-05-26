"""
Deal Advisor — your AI business partner for every buying/selling decision.

  python3 advisor.py          → Should I buy this? (paste listing details)
  python3 advisor.py offer    → Someone offered me money — should I accept?
  python3 advisor.py trade    → Someone wants to trade — is it worth it?
"""
import sys, json
import anthropic
from config import ANTHROPIC_API_KEY, RESALE_CONTEXT

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

MARKET_CONTEXT = RESALE_CONTEXT + """

Additional market knowledge:
- Always factor in: how long it will likely sit before selling, your time/effort, transport costs
- Facebook Marketplace DC area: buyers are price-sensitive, deals move in 1-3 days if priced right
- Electric bikes (Sur Ron, Talaria) have strong national demand — easy to sell
- Dirtbikes (KTM, Husqvarna, Honda CRF) sell well locally but take longer
- Chinese pit bikes: easy flip but low margin, not worth much effort over $300 profit
- Salvage/rebuilt titles cut resale value by 20-30% and slow the sale significantly
- Missing title = major red flag, avoid unless very cheap
- "Needs work" bikes: only worth it if you can fix cheap or sell as-is for parts
"""


def check_deal():
    print("\n" + "="*60)
    print("SHOULD I BUY THIS?")
    print("="*60)
    print("Paste the listing details (title, price, description, condition).")
    print("Type END on its own line when done.\n")

    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    listing = "\n".join(lines).strip()
    if not listing:
        return

    url = input("\nListing URL (press Enter to skip): ").strip()
    paid_shipping = input("Would you need to drive far to pick up? (yes/no): ").strip().lower()
    extra = input("Anything else? e.g. 'seller seems motivated', 'been listed 2 weeks': ").strip()

    print("\nAnalyzing...\n")

    prompt = f"""You are advising a professional bike reseller in Washington DC on whether to buy this listing.

{MARKET_CONTEXT}

LISTING:
{listing}
URL: {url or 'not provided'}
Long drive to pick up: {paid_shipping}
Extra context: {extra or 'none'}

Give a blunt, specific verdict. Respond ONLY with JSON, no markdown:
{{
  "verdict": "<BUY | PASS | WORTH A LOOK>",
  "max_offer": "<the most you should pay>",
  "target_offer": "<your opening offer>",
  "estimated_sell_price": "<what you can realistically sell it for in DC>",
  "estimated_profit": "<realistic profit after your time and any costs>",
  "days_to_sell": "<how long it will likely sit: fast (1-3 days) / medium (1-2 weeks) / slow (1+ month)>",
  "confidence": "<high | medium | low>",
  "reason": "<2-3 sentences: why buy or why pass, be specific>",
  "red_flags": ["<flag>"],
  "green_flags": ["<flag>"],
  "negotiation_opener": "<the first message to send if buying>"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)

    verdict = result.get("verdict", "?")
    verdict_display = {
        "BUY": "✅  BUY IT",
        "PASS": "❌  PASS",
        "WORTH A LOOK": "🔍  WORTH A LOOK"
    }.get(verdict, verdict)

    print("─" * 60)
    print(f"  {verdict_display}")
    print("─" * 60)
    print(f"  Open offer:      {result.get('target_offer')}")
    print(f"  Max to pay:      {result.get('max_offer')}")
    print(f"  Sell for:        {result.get('estimated_sell_price')}")
    print(f"  Profit:          {result.get('estimated_profit')}")
    print(f"  Time to sell:    {result.get('days_to_sell')}")
    print(f"  Confidence:      {result.get('confidence')}")
    print(f"\n  {result.get('reason')}")

    flags = result.get("red_flags", [])
    if flags:
        print(f"\n  Red flags:")
        for f in flags:
            print(f"    ⚠️  {f}")

    gflags = result.get("green_flags", [])
    if gflags:
        print(f"\n  Green flags:")
        for f in gflags:
            print(f"    ✅  {f}")

    opener = result.get("negotiation_opener")
    if opener and verdict != "PASS":
        print(f"\n  First message to send:")
        print(f"  ─────────────────────")
        print(f"  {opener}")

    print("─" * 60 + "\n")


def evaluate_offer():
    print("\n" + "="*60)
    print("SHOULD I ACCEPT THIS OFFER?")
    print("="*60)

    your_bike = input("What are you selling? (e.g. '2021 Sur Ron Light Bee X'): ").strip()
    your_asking = input("Your listing price: $").strip()
    you_paid = input("What did you pay for it: $").strip()
    their_offer = input("What they offered: $").strip()
    condition_notes = input("Any notes on condition / how long it's been listed: ").strip()

    print("\nAnalyzing...\n")

    prompt = f"""A bike reseller in DC is deciding whether to accept an offer on their listing.

{MARKET_CONTEXT}

THEIR LISTING:
Bike: {your_bike}
Listed at: ${your_asking}
Paid: ${you_paid}
Offer received: ${their_offer}
Notes: {condition_notes or 'none'}

Advise them. Respond ONLY with JSON, no markdown:
{{
  "verdict": "<ACCEPT | COUNTER | HOLD>",
  "reason": "<2-3 sentences, be specific and direct>",
  "counter_price": "<if countering, what price to counter at>",
  "counter_message": "<the exact message to send back if countering>",
  "profit_if_accepted": "<profit if they take this offer>",
  "profit_if_counter_accepted": "<profit if counter is accepted>",
  "market_assessment": "<is their asking price fair, high, or low for DC right now>"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)

    verdict = result.get("verdict", "?")
    verdict_display = {
        "ACCEPT": "✅  ACCEPT THE OFFER",
        "COUNTER": "💬  COUNTER",
        "HOLD":   "⏳  HOLD — don't budge yet"
    }.get(verdict, verdict)

    print("─" * 60)
    print(f"  {verdict_display}")
    print("─" * 60)
    print(f"  {result.get('reason')}")
    print(f"\n  Profit if accepted:          {result.get('profit_if_accepted')}")
    if result.get("counter_price"):
        print(f"  Profit if counter accepted:  {result.get('profit_if_counter_accepted')}")
        print(f"\n  Counter at: {result.get('counter_price')}")
        print(f"\n  Message to send:")
        print(f"  ─────────────────────")
        print(f"  {result.get('counter_message')}")
    print("─" * 60 + "\n")


def evaluate_trade():
    print("\n" + "="*60)
    print("IS THIS TRADE WORTH IT?")
    print("="*60)
    print("Someone wants to trade their bike for yours (or part of a deal).\n")

    your_bike = input("Your bike: ").strip()
    your_value = input("What yours is worth / what you'd sell it for: $").strip()
    you_paid = input("What you paid for yours: $").strip()

    their_bike = input("\nTheir bike: ").strip()
    their_asking = input("What they say it's worth / their asking: $").strip()
    trade_notes = input("Condition notes on their bike, any cash being added either way: ").strip()

    print("\nAnalyzing...\n")

    prompt = f"""A DC-area bike reseller is evaluating a trade offer.

{MARKET_CONTEXT}

YOUR BIKE:
{your_bike}
Market value / asking: ${your_value}
What you paid: ${you_paid}

THEIR BIKE (what they're offering):
{their_bike}
Their claimed value: ${their_asking}
Notes: {trade_notes or 'none'}

Evaluate this trade for the reseller. Respond ONLY with JSON, no markdown:
{{
  "verdict": "<TAKE IT | PASS | TAKE IT WITH CONDITIONS>",
  "real_value_their_bike": "<what their bike is actually worth in DC>",
  "value_gap": "<who wins in this trade and by how much>",
  "conditions": "<if conditions, what to demand — e.g. 'only if they add $300 cash'>",
  "resale_potential_their_bike": "<how easy is it to flip their bike and for how much>",
  "reason": "<2-3 sentences, direct advice>",
  "response_message": "<what to say to them>"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)

    verdict = result.get("verdict", "?")
    verdict_display = {
        "TAKE IT":                "✅  TAKE THE TRADE",
        "PASS":                   "❌  PASS ON THIS TRADE",
        "TAKE IT WITH CONDITIONS":"⚠️   TAKE IT — but only with conditions"
    }.get(verdict, verdict)

    print("─" * 60)
    print(f"  {verdict_display}")
    print("─" * 60)
    print(f"  Their bike's real value:  {result.get('real_value_their_bike')}")
    print(f"  Value gap:                {result.get('value_gap')}")
    if result.get("conditions"):
        print(f"  Conditions needed:        {result.get('conditions')}")
    print(f"  Flip potential:           {result.get('resale_potential_their_bike')}")
    print(f"\n  {result.get('reason')}")
    print(f"\n  What to say:")
    print(f"  ─────────────────────")
    print(f"  {result.get('response_message')}")
    print("─" * 60 + "\n")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else ""

    if cmd == "offer":
        evaluate_offer()
    elif cmd == "trade":
        evaluate_trade()
    else:
        check_deal()


if __name__ == "__main__":
    main()
