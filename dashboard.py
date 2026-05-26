"""
Two Wheels Dashboard — run with: python3 dashboard.py
Opens at http://localhost:5001
"""
import json, os, re, subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, send_file

app = Flask(__name__)
BASE = os.path.dirname(__file__)

def r(fname):
    p = os.path.join(BASE, fname)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)

def scanner_status():
    result = subprocess.run(
        ["pgrep", "-f", "main.py --loop"], capture_output=True, text=True)
    running = bool(result.stdout.strip())

    last_scan = last_scan_time = None
    log_path = os.path.join(BASE, "scanner.log")
    if os.path.exists(log_path):
        with open(log_path) as f:
            content = f.read()
        matches = re.findall(r"Scan started at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)
        if matches:
            last_scan = matches[-1]
            try:
                dt = datetime.strptime(last_scan, "%Y-%m-%d %H:%M:%S")
                delta = datetime.now() - dt
                mins = int(delta.total_seconds() / 60)
                last_scan_time = f"{mins}m ago" if mins < 60 else f"{int(mins/60)}h ago"
            except Exception:
                pass

    return {"running": running, "last_scan": last_scan, "last_scan_ago": last_scan_time}

def pipeline_stats():
    deals = r("pipeline.json") or []
    active = [d for d in deals if d.get("stage") != "sold"]
    sold = [d for d in deals if d.get("stage") == "sold"]

    total_profit = sum(
        (d.get("sold_price") or 0) - (d.get("buy_price") or 0)
        for d in sold if d.get("sold_price") and d.get("buy_price")
    )

    # This month
    now = datetime.now()
    month_profit = sum(
        (d.get("sold_price") or 0) - (d.get("buy_price") or 0)
        for d in sold
        if d.get("sold_price") and d.get("buy_price")
        and d.get("updated", "").startswith(now.strftime("%Y-%m"))
    )

    pipeline_value = sum(
        (d.get("ask_price") or 0) - (d.get("buy_price") or 0)
        for d in active if d.get("ask_price") and d.get("buy_price")
    )

    return {
        "total_profit": total_profit,
        "month_profit": month_profit,
        "active_count": len(active),
        "sold_count": len(sold),
        "pipeline_value": pipeline_value,
        "active_deals": active,
        "recent_sold": sorted(sold, key=lambda x: x.get("updated",""), reverse=True)[:5],
    }

def recent_deals():
    history = r("deals_history.json") or []
    return sorted(history, key=lambda x: x.get("found_at",""), reverse=True)[:30]

def messages_sent():
    ids = r("messaged_listings.json") or []
    return len(ids)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    scan = scanner_status()
    pipe = pipeline_stats()
    deals = recent_deals()
    return jsonify({
        "scanner": scan,
        "pipeline": pipe,
        "recent_deals": deals,
        "messages_sent": messages_sent(),
        "updated_at": datetime.now().strftime("%I:%M:%S %p"),
    })

@app.route("/plan")
def plan():
    return render_template("plan.html")

@app.route("/assignments")
def assignments():
    return render_template("assignments.html")

@app.route("/selling")
def selling():
    pipe = r("pipeline.json") or []
    selling_bikes = [d for d in pipe if d.get("stage") in ("listed", "owned")]
    past_flips = sorted(
        [d for d in pipe if d.get("stage") == "sold"],
        key=lambda x: x.get("updated", ""),
        reverse=True,
    )
    total_in = sum(d.get("buy_price", 0) for d in selling_bikes)
    total_ask = sum(d.get("ask_price", 0) for d in selling_bikes)
    potential_profit = total_ask - total_in
    past_profit = sum(
        (d.get("sold_price") or 0) - (d.get("buy_price") or 0) for d in past_flips
    )
    return render_template(
        "selling.html",
        total_in=total_in,
        total_ask=total_ask,
        potential_profit=potential_profit,
        bike_count=len(selling_bikes),
        bikes=selling_bikes,
        past_flips=past_flips,
        past_profit=past_profit,
    )


PLATFORM_LABELS = {
    "facebook": "Facebook Marketplace",
    "offerup": "OfferUp",
    "craigslist": "Craigslist",
    "instagram": "Instagram",
    "reddit": "Reddit",
    "cycletrader": "CycleTrader",
    "other": "Other",
}

PLATFORM_HOMES = {
    "facebook": "https://www.facebook.com/marketplace/you/selling",
    "offerup": "https://offerup.com/login",
    "craigslist": "https://accounts.craigslist.org/login",
    "instagram": "https://www.instagram.com/direct/inbox/",
    "reddit": "https://www.reddit.com/message/inbox/",
    "cycletrader": "https://www.cycletrader.com/my-account",
    "other": "",
}


@app.route("/api/past-flip", methods=["POST"])
def add_past_flip():
    from flask import request
    data = request.get_json(force=True)
    title = (data.get("title") or "").strip()
    try:
        buy = int(str(data.get("buy_price") or "").replace("$","").replace(",",""))
        sold = int(str(data.get("sold_price") or "").replace("$","").replace(",",""))
    except ValueError:
        return jsonify({"ok": False, "error": "buy/sold must be numbers"}), 400
    if not title:
        return jsonify({"ok": False, "error": "title required"}), 400
    date_str = (data.get("date") or "").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif len(date_str) == 7:
        date_str = date_str + "-01"

    path = os.path.join(BASE, "pipeline.json")
    with open(path) as f:
        pipe = json.load(f)
    int_ids = [d["id"] for d in pipe if isinstance(d.get("id"), int)]
    next_id = max(int_ids, default=0) + 1
    pipe.append({
        "id": next_id,
        "title": title,
        "url": None,
        "buy_price": buy,
        "ask_price": sold,
        "sold_price": sold,
        "stage": "sold",
        "notes": data.get("notes") or "Past flip",
        "added": date_str,
        "updated": date_str,
    })
    with open(path, "w") as f:
        json.dump(pipe, f, indent=2)
    return jsonify({"ok": True, "profit": sold - buy, "id": next_id})


@app.route("/api/past-flip/<int:flip_id>", methods=["DELETE"])
def delete_past_flip(flip_id):
    path = os.path.join(BASE, "pipeline.json")
    with open(path) as f:
        pipe = json.load(f)
    new_pipe = [d for d in pipe if d.get("id") != flip_id]
    if len(new_pipe) == len(pipe):
        return jsonify({"ok": False, "error": "not found"}), 404
    with open(path, "w") as f:
        json.dump(new_pipe, f, indent=2)
    return jsonify({"ok": True})


@app.route("/api/listing-url", methods=["POST"])
def update_listing_url():
    from flask import request
    data = request.get_json(force=True)
    bike_id = data.get("bike_id")
    platform = data.get("platform")
    url = (data.get("url") or "").strip()
    if not bike_id or not platform:
        return jsonify({"ok": False, "error": "missing bike_id or platform"}), 400
    path = os.path.join(BASE, "pipeline.json")
    with open(path) as f:
        pipe = json.load(f)
    for b in pipe:
        if b.get("id") == bike_id:
            b.setdefault("listings", {})[platform] = url
            break
    else:
        return jsonify({"ok": False, "error": "bike not found"}), 404
    with open(path, "w") as f:
        json.dump(pipe, f, indent=2)
    return jsonify({"ok": True})


@app.context_processor
def inject_platforms():
    return {"PLATFORM_LABELS": PLATFORM_LABELS, "PLATFORM_HOMES": PLATFORM_HOMES}


# ─────────────────────────────────────────────────────────────
# PUBLIC TWO WHEELS SITE — what buyers see at twowheels.com
# ─────────────────────────────────────────────────────────────
TWO_WHEELS_EMAIL = "twowheelsceo@gmail.com"


def _sanitize_bike(b):
    """Strip private fields from a pipeline entry for public exposure."""
    return {
        "id": b.get("id"),
        "title": b.get("title", ""),
        "ask_price": b.get("ask_price", 0),
        "description": b.get("description", ""),
        "photos": b.get("photos") or [],
        "highlights": b.get("highlights") or [],
        "stage": b.get("stage"),
        "year": b.get("year"),
        "mileage": b.get("mileage"),
        "category": b.get("category"),
        "title_status": b.get("title_status"),
    }


def _forward_email(subject: str, html_body: str) -> bool:
    """Email a chat/lead message to twowheelsceo@gmail.com via the existing SMTP setup."""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from config import SENDER_EMAIL, SENDER_APP_PASSWORD
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = TWO_WHEELS_EMAIL
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, [TWO_WHEELS_EMAIL], msg.as_string())
        return True
    except Exception as e:
        print(f"[email forward failed] {e}")
        return False


@app.route("/inventory")
def public_inventory():
    pipe = r("pipeline.json") or []
    in_stock = [d for d in pipe if d.get("stage") in ("listed", "owned")]
    sold = sorted(
        [d for d in pipe if d.get("stage") == "sold"],
        key=lambda x: x.get("updated", ""),
        reverse=True,
    )[:8]
    public_stock = [_sanitize_bike(b) for b in in_stock]
    public_sold = [{"title": b.get("title", ""), "sold_price": b.get("sold_price", 0)} for b in sold]
    return render_template(
        "twowheels.html",
        bikes=public_stock,
        recent_sold=public_sold,
        stock_count=len(public_stock),
        contact_email=TWO_WHEELS_EMAIL,
    )


@app.route("/bike/<bike_id>")
def bike_detail(bike_id):
    pipe = r("pipeline.json") or []
    bike = next((b for b in pipe if str(b.get("id")) == str(bike_id)), None)
    if not bike or bike.get("stage") == "sold":
        return render_template("twowheels.html", bikes=[], recent_sold=[], stock_count=0,
                               contact_email=TWO_WHEELS_EMAIL), 404
    return render_template(
        "bike_detail.html",
        bike=_sanitize_bike(bike),
        contact_email=TWO_WHEELS_EMAIL,
    )


@app.route("/api/lead", methods=["POST"])
def capture_lead():
    from flask import request
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()[:80]
    contact = (data.get("contact") or "").strip()[:120]
    looking_for = (data.get("looking_for") or "").strip()[:300]
    if not contact:
        return jsonify({"ok": False, "error": "contact required"}), 400
    leads_path = os.path.join(BASE, "leads.json")
    leads = []
    if os.path.exists(leads_path):
        try:
            with open(leads_path) as f:
                leads = json.load(f)
        except Exception:
            leads = []
    received = datetime.now().strftime("%Y-%m-%d %H:%M")
    leads.append({"name": name, "contact": contact, "looking_for": looking_for, "received": received})
    with open(leads_path, "w") as f:
        json.dump(leads, f, indent=2)
    _forward_email(
        f"[Two Wheels] New drop-alert signup: {name or contact}",
        f"<h2>New buyer on the alert list</h2>"
        f"<p><b>Name:</b> {name or '(not given)'}</p>"
        f"<p><b>Contact:</b> {contact}</p>"
        f"<p><b>Looking for:</b> {looking_for or '(not specified)'}</p>"
        f"<p style='color:#888;font-size:12px;'>Received: {received}</p>"
    )
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def chat_message():
    from flask import request
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()[:80]
    contact = (data.get("contact") or "").strip()[:120]
    message = (data.get("message") or "").strip()[:2000]
    bike_id = (data.get("bike_id") or "").strip()[:80]
    bike_title = (data.get("bike_title") or "").strip()[:200]
    if not message or not contact:
        return jsonify({"ok": False, "error": "message and contact required"}), 400
    msgs_path = os.path.join(BASE, "messages.json")
    msgs = []
    if os.path.exists(msgs_path):
        try:
            with open(msgs_path) as f:
                msgs = json.load(f)
        except Exception:
            msgs = []
    received = datetime.now().strftime("%Y-%m-%d %H:%M")
    msgs.append({
        "name": name, "contact": contact, "message": message,
        "bike_id": bike_id, "bike_title": bike_title, "received": received,
    })
    with open(msgs_path, "w") as f:
        json.dump(msgs, f, indent=2)
    subj = f"[Two Wheels] {bike_title or 'New inquiry'} — from {name or contact}"
    body = (
        f"<h2>New customer inquiry</h2>"
        f"<p><b>About:</b> {bike_title or 'General inquiry'}</p>"
        f"<p><b>Name:</b> {name or '(not given)'}</p>"
        f"<p><b>Contact:</b> {contact}</p>"
        f"<div style='background:#f4f4f4;border-left:4px solid #00aa55;padding:14px;margin-top:14px;border-radius:6px;'>"
        f"<b>Message:</b><br>{message.replace(chr(10), '<br>')}</div>"
        f"<p style='color:#888;font-size:12px;margin-top:14px;'>Received: {received}</p>"
        f"<p><b>Reply directly to:</b> {contact}</p>"
    )
    _forward_email(subj, body)
    return jsonify({"ok": True})

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  TWO WHEELS DASHBOARD")
    print("  Open: http://localhost:5001")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
