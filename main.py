import json, sys, time, os, schedule, random
from datetime import datetime
from scraper import scrape_marketplace, setup_login, enrich_with_descriptions
from analyzer import analyze_listings
from emailer import send_deal_alert
from messenger import attach_suggested_openers
from config import SEEN_LISTINGS_FILE, SCAN_INTERVAL_MINUTES, SEARCH_TERMS, SEARCH_GROUPS

DEALS_HISTORY_FILE = "deals_history.json"
SCAN_STATE_FILE = "scan_state.json"


def load_scan_state():
    if os.path.exists(SCAN_STATE_FILE):
        try:
            with open(SCAN_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"group_index": 0}


def save_scan_state(state):
    with open(SCAN_STATE_FILE, "w") as f:
        json.dump(state, f)


def current_term_slice():
    """Pull the next rotating slice of SEARCH_TERMS. Advances state for next cycle."""
    state = load_scan_state()
    idx = state.get("group_index", 0) % SEARCH_GROUPS
    # Round-robin assignment — every Nth term goes in the same group
    terms = [t for j, t in enumerate(SEARCH_TERMS) if j % SEARCH_GROUPS == idx]
    random.shuffle(terms)  # randomize order so FB doesn't see a robotic pattern
    state["group_index"] = (idx + 1) % SEARCH_GROUPS
    save_scan_state(state)
    print(f"Cycle group {idx + 1}/{SEARCH_GROUPS} — {len(terms)} terms (order shuffled).")
    return terms

def log_deals_history(deals):
    history = []
    if os.path.exists(DEALS_HISTORY_FILE):
        with open(DEALS_HISTORY_FILE) as f:
            history = json.load(f)
    for d in deals:
        history.append({**d, "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    with open(DEALS_HISTORY_FILE, "w") as f:
        json.dump(history[-500:], f, indent=2)

def load_seen():
    if os.path.exists(SEEN_LISTINGS_FILE):
        with open(SEEN_LISTINGS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_LISTINGS_FILE, "w") as f:
        json.dump(list(seen)[-5000:], f)

def run_scan():
    print("\n" + "="*60)
    print(f"Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    seen = load_seen()
    terms = current_term_slice()
    all_listings = scrape_marketplace(terms)
    if not all_listings:
        print("No listings returned. Will retry next cycle.\n")
        return
    new_listings = [l for l in all_listings if l["id"] not in seen]
    print(f"{len(new_listings)} new listings (filtered {len(all_listings)-len(new_listings)} already seen)\n")
    if not new_listings:
        print("No new listings since last scan.\n")
        return
    new_listings = enrich_with_descriptions(new_listings)
    good_deals = analyze_listings(new_listings)
    if good_deals:
        good_deals = attach_suggested_openers(good_deals)
        send_deal_alert(good_deals)
        log_deals_history(good_deals)
    else:
        print("No deals scored high enough. No email sent.\n")
    for l in new_listings:
        seen.add(l["id"])
    save_seen(seen)
    print(f"Scan complete. Next scan in {SCAN_INTERVAL_MINUTES} minutes.\n")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--setup" in args:
        setup_login()
        sys.exit(0)
    elif "--loop" in args:
        print(f"Starting scanner — every {SCAN_INTERVAL_MINUTES} minutes\n")
        run_scan()
        schedule.every(SCAN_INTERVAL_MINUTES).minutes.do(run_scan)
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        run_scan()
