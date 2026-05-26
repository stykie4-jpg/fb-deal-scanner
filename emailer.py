import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import SENDER_EMAIL, SENDER_APP_PASSWORD, RECIPIENT_EMAIL

def score_emoji(score):
    if score >= 9: return "🔥🔥🔥"
    if score >= 8: return "🔥🔥"
    return "🔥"

def urgency_banner(score, listing):
    """Highlight time-sensitive deals at the top of each card."""
    desc = (listing.get("description") or "").lower()
    title = (listing.get("title") or "").lower()
    text = desc + " " + title
    signals = []
    for phrase in ("moving", "pcs", "divorce", "need gone", "cash today", "first $", "make offer", "estate sale", "garage clean", "don't have time", "no time"):
        if phrase in text:
            signals.append(phrase)
    if score >= 9:
        return '<div style="background:#c0392b;color:#fff;padding:10px 16px;border-radius:8px;font-weight:bold;margin-bottom:12px;text-align:center;font-size:14px;">⚡ ACT FAST — TOP-TIER DEAL. Send opener within 30 minutes.</div>'
    if signals:
        return f'<div style="background:#f39c12;color:#fff;padding:10px 16px;border-radius:8px;font-weight:bold;margin-bottom:12px;text-align:center;font-size:13px;">⚡ MOTIVATED SELLER signals: {", ".join(signals[:3])}</div>'
    return ""

def trade_route_hint(listing):
    desc = (listing.get("description") or "").lower()
    title = (listing.get("title") or "").lower()
    if any(w in desc + " " + title for w in ("open to trade", "will trade", "trades welcome", "open to trades", "obo + trades", "considering trades", "interested in trades")):
        return '<div style="background:#e8f5e9;border-left:4px solid #27ae60;padding:12px;margin-top:12px;border-radius:6px;"><strong style="color:#27ae60;">🔄 TRADE OPPORTUNITY:</strong> Seller is open to trades. Consider offering one of your current bikes (Sur Ron LBX, R6, Talaria MX4, Razor Stage 2 M2) instead of cash.</div>'
    return ""

def build_listing_html(listing):
    a = listing.get("analysis", {})
    score = listing.get("deal_score", 0)
    red = "".join(f"<li style='color:#c0392b'>⚠️ {f}</li>" for f in a.get("red_flags",[]))
    green = "".join(f"<li style='color:#27ae60'>✅ {f}</li>" for f in a.get("green_flags",[]))
    img = f'<img src="{listing["image_url"]}" style="max-width:400px;border-radius:8px;margin:12px 0;"/>' if listing.get("image_url") else ""
    return f"""
    <div style="background:#fff;border:1px solid #ddd;border-radius:12px;padding:24px;margin-bottom:24px;font-family:sans-serif;">
      {urgency_banner(score, listing)}
      <h2>{score_emoji(score)} {listing.get('title')} — {score}/10</h2>
      {img}
      <table style="width:100%;border-collapse:collapse;">
        <tr><td style="padding:8px;background:#f8f9fa;font-weight:bold;">💰 Asking Price</td><td style="padding:8px;font-size:18px;color:#1877f2;font-weight:bold;">{listing.get('price')}</td></tr>
        <tr><td style="padding:8px;background:#f8f9fa;font-weight:bold;">📈 Market Value</td><td style="padding:8px;">{a.get('estimated_market_value','?')}</td></tr>
        <tr><td style="padding:8px;background:#f8f9fa;font-weight:bold;">💵 Flip Profit</td><td style="padding:8px;color:#27ae60;font-weight:bold;">{a.get('estimated_flip_profit','?')}</td></tr>
        <tr><td style="padding:8px;background:#f8f9fa;font-weight:bold;">🎯 Offer</td><td style="padding:8px;font-weight:bold;">{a.get('recommended_offer','?')}</td></tr>
        <tr><td style="padding:8px;background:#f8f9fa;font-weight:bold;">🔧 Condition</td><td style="padding:8px;">{a.get('condition_assessment','?')}</td></tr>
      </table>
      <p>{a.get('summary','')}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div><strong style="color:#27ae60;">Green Flags</strong><ul>{green}</ul></div>
        <div><strong style="color:#c0392b;">Red Flags</strong><ul>{red}</ul></div>
      </div>
      <div style="background:#fff9e6;border-left:4px solid #f39c12;padding:12px;margin:16px 0;">
        <strong>💬 Negotiation Tip:</strong> {a.get('negotiation_tip','')}
      </div>
      {trade_route_hint(listing)}
      <a href="{listing.get('url','#')}" style="background:#1877f2;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">👉 View on Facebook</a>
      {f'<div style="background:#e3f2fd;border-left:4px solid #1877f2;padding:16px;margin-top:16px;border-radius:6px;"><strong style="color:#1877f2;font-size:15px;">📋 SUGGESTED OPENER — copy/paste this:</strong><div style="background:#fff;border:1px dashed #1877f2;border-radius:6px;padding:12px;margin-top:10px;font-family:monospace;color:#222;user-select:all;">{listing["suggested_opener"]}</div><div style="font-size:12px;color:#666;margin-top:6px;">Triple-click the box above to select, then ⌘C to copy.</div></div>' if listing.get("suggested_opener") else '<div style="background:#fff3e0;border-left:4px solid #ff9800;padding:12px;margin-top:16px;"><strong>⚠️ Score below opener threshold — write your own message if interested.</strong></div>'}
    </div>"""

def send_deal_alert(deals):
    if not deals: return
    now = datetime.now().strftime("%b %d at %I:%M %p")
    subject = f"🔥 {len(deals)} Deal(s) Found — Best Score: {deals[0]['deal_score']}/10 | {now}"
    html = f"<html><body style='background:#f0f2f5;padding:24px;font-family:sans-serif;'><div style='max-width:650px;margin:0 auto;'><div style='background:#1877f2;color:#fff;padding:20px;border-radius:12px;margin-bottom:16px;'><h1 style='margin:0;'>🏍️ Deal Scanner Alert</h1><p style='margin:4px 0 0;'>{len(deals)} deal(s) found — {now}</p></div>{''.join(build_listing_html(d) for d in deals)}</div></body></html>"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    print(f"Email sent! {len(deals)} deal(s) to {RECIPIENT_EMAIL}\n")
