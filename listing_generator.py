import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """You are an expert at writing Facebook Marketplace listings for bikes and motorcycles.
You write listings that sell fast at top dollar. Your listings are:
- Honest but highlight the best features first
- Specific (year, model, mods, condition details buyers care about)
- Priced to attract messages, not lowballers
- Written like a real seller, not a dealership
- Short enough to read in 30 seconds"""

def generate_listing(details: str, asking_price: str = None) -> dict:
    price_line = f"I want to list it for ${asking_price}." if asking_price else "Suggest a good asking price too."

    prompt = f"""Create a Facebook Marketplace listing for this bike.

Details:
{details}

{price_line}

Return a JSON object with:
{{
  "title": "<listing title, under 60 chars>",
  "price": "<asking price>",
  "description": "<full listing description>",
  "tips": ["<selling tip 1>", "<selling tip 2>"]
}}

No markdown, just the JSON."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def run_interactive():
    print("\n" + "="*60)
    print("LISTING GENERATOR")
    print("="*60)
    print("Tell me about the bike — year, model, condition, mods, what's included.")
    print("(Type END on its own line when done)\n")

    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    details = "\n".join(lines)

    if not details.strip():
        print("No details entered.")
        return

    price = input("\nAsking price? (press Enter and AI will suggest one): ").strip()

    print("\nGenerating listing...\n")
    result = generate_listing(details, price or None)

    print("─" * 60)
    print(f"TITLE:  {result.get('title')}")
    print(f"PRICE:  {result.get('price')}")
    print("─" * 60)
    print("DESCRIPTION:")
    print(result.get("description", ""))
    print("─" * 60)
    print("SELLING TIPS:")
    for tip in result.get("tips", []):
        print(f"  • {tip}")
    print("─" * 60 + "\n")


if __name__ == "__main__":
    run_interactive()
