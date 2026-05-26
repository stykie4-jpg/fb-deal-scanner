"""
Negotiation assistant — handles the full buying flow:
  1. Haggle the price down
  2. Once price is agreed, schedule the meetup

Usage: python3 negotiator.py
"""
import anthropic
from config import ANTHROPIC_API_KEY, RESALE_CONTEXT, LOCATION

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM = """
You are a professional reseller of electric bikes and motorcycles in the Washington DC area.
You are negotiating to BUY vehicles as cheaply as possible on Facebook Marketplace.
Your style: friendly, low-pressure, casual. Sound like a normal guy, not a dealer.
Never act desperate. Always leave room to counter. Keep messages short — 2-4 sentences max.

""" + RESALE_CONTEXT


def analyze_conversation(conversation: str) -> dict:
    """Detect the stage of the negotiation and extract key facts."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": f"""Analyze this Facebook Marketplace buying conversation.

{conversation}

Reply with ONLY a JSON object, no markdown:
{{
  "stage": "<one of: opening | haggling | price_agreed | meetup_scheduling | done>",
  "agreed_price": "<price if agreed, else null>",
  "their_last_price": "<their most recent asking price, or null>",
  "meetup_set": <true or false>,
  "summary": "<one sentence of where things stand>"
}}"""}]
    )
    import json
    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"stage": "haggling", "agreed_price": None, "their_last_price": None, "meetup_set": False, "summary": ""}


def draft_reply(conversation: str, target_price: str, context: str, stage: dict) -> str:
    target_line = f"My max buy price is ${target_price}. Do NOT offer more than this." if target_price else ""
    extra = f"Extra context: {context}" if context else ""

    if stage.get("stage") == "price_agreed" or stage.get("agreed_price"):
        goal = f"""The price is agreed at {stage.get('agreed_price', 'the price we discussed')}.
Now draft a message to schedule the meetup. Ask:
- When are they available (give 2 specific options like "tomorrow afternoon or this weekend")
- Where they want to meet (suggest somewhere public and easy for both — we're in the DC/Maryland/Virginia area)
- Confirm you'll bring cash
Keep it casual and confirmatory. End with something like "Just lmk what works for you."
"""
    else:
        goal = f"""Draft my next negotiation message.
- If no offer made yet: open with a low but reasonable offer
- If they countered: hold firm or move slightly with a reason ("just trying to stay in my budget")
- Never reveal my max
- End with something that invites a response
{target_line}
"""

    prompt = f"""Conversation:
{conversation}

{extra}

{goal}

Reply with ONLY the message to send. No explanation, no quotes around it."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def run_interactive():
    print("\n" + "="*60)
    print("NEGOTIATION ASSISTANT")
    print("Full flow: haggle → close → schedule meetup")
    print("="*60)

    target = input("\nWhat's your max buy price? (e.g. 1800): $").strip()
    context = input("Any context about the listing? e.g. 'listed 3 weeks ago, 2021 Sur Ron': ").strip()

    print("\nPaste the conversation so far (type END on its own line when done):\n")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == "END":
            break
        lines.append(line)
    conversation = "\n".join(lines)

    if not conversation.strip():
        print("No conversation entered.")
        return

    print("\nAnalyzing conversation...")
    stage = analyze_conversation(conversation)

    print(f"Status: {stage.get('summary', '')}")
    if stage.get("agreed_price"):
        print(f"Agreed price: {stage['agreed_price']} — drafting meetup message...")
    elif stage.get("their_last_price"):
        print(f"Their current ask: {stage['their_last_price']}")

    print("\nDrafting your reply...\n")
    reply = draft_reply(conversation, target, context, stage)

    print("─" * 60)
    print("SEND THIS:")
    print("─" * 60)
    print(reply)
    print("─" * 60)

    # Let them keep iterating without restarting
    while True:
        cont = input("\nDid they reply? Paste their response (or press Enter to quit): ").strip()
        if not cont:
            break

        conversation += f"\nThem: {cont}"
        stage = analyze_conversation(conversation)

        if stage.get("stage") == "done" or stage.get("meetup_set"):
            print("\nMeetup looks set — you're good to go!")
            break

        print("\nDrafting reply...")
        reply = draft_reply(conversation, target, context, stage)

        if stage.get("agreed_price") and stage.get("stage") in ("price_agreed", "meetup_scheduling"):
            print("\n[Price agreed — scheduling meetup]")

        print("─" * 60)
        print("SEND THIS:")
        print("─" * 60)
        print(reply)
        print("─" * 60)

        conversation += f"\nMe: {reply}"

    print("\nGood luck with the deal!\n")


if __name__ == "__main__":
    run_interactive()
