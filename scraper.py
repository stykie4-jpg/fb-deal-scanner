import json, time, re, os, random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import SEARCH_TERMS, MIN_PRICE, MAX_PRICE, MAX_DAYS_LISTED, LOCATION, RADIUS_MILES

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "chrome_profile")
SKIP_PHRASES = {"enter your city", "to show local", "local results", "sponsored"}

# Known placeholder/joke prices sellers use when they haven't set a real price
PLACEHOLDER_PRICES = {
    1, 11, 111, 222, 333, 444, 555, 666, 777, 888, 999,
    1111, 1234, 2222, 3333, 4444, 5555, 6666, 7777, 8888, 9999,
    11111, 12345, 22222, 33333, 99999, 123456, 1234567,
}


def is_placeholder_price(price_str: str) -> bool:
    """Detect placeholder prices like $1234, $9999, $1, etc."""
    if not price_str or price_str == "Unknown":
        return True
    digits = re.sub(r'[^\d]', '', str(price_str))
    if not digits:
        return True
    try:
        n = int(digits)
    except ValueError:
        return True
    return n in PLACEHOLDER_PRICES


def build_search_url(query):
    q = query.replace(" ", "%20")
    return (f"https://www.facebook.com/marketplace/{LOCATION}/search"
            f"?query={q}&minPrice={MIN_PRICE}&maxPrice={MAX_PRICE}"
            f"&daysSinceListed={MAX_DAYS_LISTED}&radius={RADIUS_MILES}&exact=false")


def cleanup_locks():
    import subprocess
    # Kill any Chrome process still holding our profile directory
    try:
        result = subprocess.run(
            ["pgrep", "-f", PROFILE_DIR], capture_output=True, text=True)
        for pid in result.stdout.strip().splitlines():
            try:
                os.kill(int(pid), 9)
            except Exception:
                pass
    except Exception:
        pass
    import time as _time
    _time.sleep(1)
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        p = os.path.join(PROFILE_DIR, name)
        if os.path.exists(p):
            os.remove(p)
    lock = os.path.join(PROFILE_DIR, "Default", "LOCK")
    if os.path.exists(lock):
        os.remove(lock)


def make_driver():
    cleanup_locks()
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--no-first-run")
    options.add_argument("--lang=en-US")
    driver = uc.Chrome(options=options, headless=False, version_main=148)
    driver.set_window_size(1280, 900)
    return driver


def setup_login():
    print("\n" + "="*60)
    print("Opening Chrome. Log into Facebook in that window.")
    print("The scanner will detect when you're logged in.")
    print("="*60 + "\n")

    driver = make_driver()
    driver.get("https://www.facebook.com/login")

    logged_in_url = "https://www.facebook.com/login"
    for i in range(150):  # 5 minutes
        time.sleep(2)
        url = driver.current_url
        print(f"Waiting... {url[:70]}")
        if url != logged_in_url and "facebook.com" in url:
            time.sleep(3)
            driver.get("https://www.facebook.com/marketplace")
            time.sleep(4)
            driver.quit()
            print("\n" + "="*60)
            print("✅ SESSION SAVED! You are now logged in.")
            print("Run the scanner: python3 main.py")
            print("="*60 + "\n")
            return

    driver.quit()
    print("Timed out. Run --setup again and log in faster.")


def extract_listing_data(driver, card):
    try:
        link_el = card.find_element(By.CSS_SELECTOR, "a[href*='/marketplace/item/']")
        href = link_el.get_attribute("href")
        listing_id = re.search(r"/marketplace/item/(\d+)", href or "")
        if not listing_id:
            return None
        listing_id = listing_id.group(1)
        full_url = f"https://www.facebook.com/marketplace/item/{listing_id}/"

        # Price
        try:
            price_el = card.find_element(By.XPATH, ".//span[contains(text(),'$')]")
            price_text = price_el.text.strip()
        except Exception:
            price_text = "Unknown"

        # Title and location
        title = "Unknown"
        location = ""
        spans = card.find_elements(By.CSS_SELECTOR, "span[dir='auto']")
        for span in spans:
            text = span.text.strip()
            if not text or len(text) < 4 or "$" in text:
                continue
            if any(p in text.lower() for p in SKIP_PHRASES):
                continue
            if "·" in text or " mi" in text:
                location = location or text
            elif title == "Unknown":
                title = text

        # Hard distance filter — skip anything over 100 miles
        dist_match = re.search(r'(\d+)\s*mi', location)
        if dist_match and int(dist_match.group(1)) > 100:
            return None

        # Skip listings with no real title
        if title == "Unknown" or len(title) < 5:
            return None

        # Skip placeholder / fake prices (1234, 9999, $1, etc.)
        if is_placeholder_price(price_text):
            return None

        # Image
        try:
            img_el = card.find_element(By.TAG_NAME, "img")
            image_url = img_el.get_attribute("src")
        except Exception:
            image_url = None

        return {"id": listing_id, "title": title, "price": price_text,
                "location": location, "url": full_url, "image_url": image_url}
    except Exception:
        return None


def _is_dead_driver_error(err) -> bool:
    msg = str(err).lower()
    return any(s in msg for s in (
        "invalid session id", "no such window", "chrome not reachable",
        "session deleted", "disconnected", "target closed", "browser has closed",
    ))


def scrape_marketplace(terms=None):
    if not os.path.exists(PROFILE_DIR):
        print("No session. Run: python3 main.py --setup first.")
        return []

    terms = terms if terms is not None else SEARCH_TERMS
    print(f"Scanning {len(terms)} search terms this cycle.\n")

    listings = []
    seen_ids = set()
    driver = make_driver()
    driver_restarts = 0
    MAX_RESTARTS = 2

    def _restart():
        nonlocal driver, driver_restarts
        driver_restarts += 1
        print(f"\n⚠ Browser crashed — restarting (attempt {driver_restarts}/{MAX_RESTARTS})...")
        try:
            driver.quit()
        except Exception:
            pass
        time.sleep(2)
        driver = make_driver()
        driver.get("https://www.facebook.com/marketplace")
        time.sleep(4)
        if "login" in driver.current_url:
            raise RuntimeError("Session expired after restart")
        print("✓ Browser restarted, resuming scan.\n")

    try:
        driver.get("https://www.facebook.com/marketplace")
        time.sleep(4)

        if "login" in driver.current_url:
            print("Session expired. Run: python3 main.py --setup")
            driver.quit()
            return []

        for i, term in enumerate(terms):
            print(f"Searching: '{term}'...")
            try:
                driver.get(build_search_url(term))
                time.sleep(random.uniform(3.5, 5.5))

                # Scroll to load more listings (jittered, fewer scrolls)
                for _ in range(2):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(1.5, 2.8))

                cards = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div[aria-label='Collection of Marketplace items'] > div"
                )
                print(f"  Found {len(cards)} listings")

                for card in cards:
                    data = extract_listing_data(driver, card)
                    if data and data["id"] not in seen_ids:
                        seen_ids.add(data["id"])
                        listings.append(data)

                # Human-like pacing: short jitter between searches,
                # longer "coffee break" every 20 searches
                if (i + 1) % 20 == 0 and i + 1 < len(terms):
                    pause = random.uniform(45, 75)
                    print(f"  [Cooldown pause: {int(pause)}s to avoid rate-limit]")
                    time.sleep(pause)
                else:
                    time.sleep(random.uniform(4, 8))
            except Exception as e:
                if _is_dead_driver_error(e):
                    if driver_restarts >= MAX_RESTARTS:
                        print(f"  Browser has crashed {driver_restarts} times this scan — giving up and saving what we have.")
                        break
                    try:
                        _restart()
                    except Exception as restart_err:
                        print(f"  Restart failed: {restart_err}. Ending scan early.")
                        break
                    continue
                print(f"  Error on '{term}': {e}")
                continue

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print(f"\nScrape complete. {len(listings)} unique listings.\n")
    return listings


def fetch_description(driver, url: str) -> str:
    """Visit a listing page and pull the description text. Returns '' on failure."""
    try:
        driver.get(url)
        time.sleep(2.5)

        # Click "See more" to expand truncated descriptions
        for sel in (
            "//div[@role='button'][contains(., 'See more')]",
            "//span[normalize-space()='See more']/..",
        ):
            try:
                btn = driver.find_element(By.XPATH, sel)
                btn.click()
                time.sleep(0.6)
                break
            except Exception:
                continue

        # Description usually sits below the price/location in a span[dir='auto']
        # Pull the longest reasonable text block on the page (descriptions are typically 50+ chars)
        candidates = driver.find_elements(By.CSS_SELECTOR, "span[dir='auto']")
        texts = []
        for el in candidates:
            try:
                t = el.text.strip()
                if 40 <= len(t) <= 5000 and "$" not in t[:5]:
                    texts.append(t)
            except Exception:
                continue
        # The actual description is usually the longest such block
        if texts:
            return max(texts, key=len)
        return ""
    except Exception as e:
        return ""


def enrich_with_descriptions(listings: list, max_listings: int = 80) -> list:
    """Visit each listing URL and add the full description. Caps at max_listings to control runtime."""
    if not listings:
        return listings

    target = listings[:max_listings]
    skipped = len(listings) - len(target)
    print(f"Fetching descriptions for {len(target)} listings"
          + (f" (skipped {skipped} over cap)" if skipped else "") + "...\n")

    driver = make_driver()
    enriched = 0
    try:
        driver.get("https://www.facebook.com/marketplace")
        time.sleep(3)
        if "login" in driver.current_url:
            print("Session expired during enrich. Skipping descriptions.\n")
            driver.quit()
            return listings

        for i, l in enumerate(target, 1):
            desc = fetch_description(driver, l["url"])
            l["description"] = desc
            if desc:
                enriched += 1
            if i % 10 == 0:
                print(f"  {i}/{len(target)} fetched ({enriched} have description text)")
    finally:
        driver.quit()

    print(f"\nDescription fetch done. {enriched}/{len(target)} have description text.\n")
    return listings
