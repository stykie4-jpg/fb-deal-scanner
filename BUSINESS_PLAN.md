# TWO WHEELS — MASTER BUSINESS PLAN
### Summer 2026 · Washington DC / VA / MD
### Last updated: May 24, 2026

---

## THE GOAL
| Target | Number |
|---|---|
| Monthly profit | $8,000 |
| Flips per week | 1–2 |
| Avg profit per flip | $1,000–$3,000 |
| End vision | Two Wheels = USA's #1 bike marketplace |

---

## WHAT'S ALREADY BUILT AND RUNNING

| Tool | Status | What it does |
|---|---|---|
| FB Deal Scanner | ✅ LIVE | Scrapes 56 search terms every 20 min, AI scores deals 1-10 |
| Auto-Messenger | ✅ LIVE | Auto-sends lowball openers to any deal scoring 7+ |
| Email Alerts | ✅ LIVE | Emails stykie4@gmail.com every deal scoring 6+ |
| Deal Advisor | ✅ READY | `python3 advisor.py` — buy/pass verdict with profit estimate |
| Offer Evaluator | ✅ READY | `python3 advisor.py offer` — accept/counter/hold |
| Trade Evaluator | ✅ READY | `python3 advisor.py trade` — is a trade worth it? |
| Negotiator | ✅ READY | `python3 negotiator.py` — drafts FB messages through full deal |
| Pipeline Tracker | ✅ READY | `python3 pipeline.py` — tracks every deal lead → sold |
| Listing Generator | ✅ READY | `python3 listing_generator.py` — writes FB/eBay listings from photos |
| Dashboard | ✅ LIVE | http://localhost:5001 — live profit + pipeline view |

---

## AGENT STACK — HOW EACH TOOL FITS YOUR DAY

### Morning (5 min)
1. Check email — scanner ran overnight, deals are waiting
2. Open http://localhost:5001 — see pipeline + profit
3. Any deal scored 7+ was auto-messaged already — check FB Messenger for replies

### When a seller replies
```
python3 negotiator.py
```
Paste the conversation → it writes your next message → you hit send.
Handles: opening offer → haggling → price agreed → scheduling meetup.

### When you're deciding whether to buy something you found yourself
```
python3 advisor.py
```
Paste the listing → get: buy/pass, exact offer, profit estimate, red flags.

### When someone makes you an offer on something you're selling
```
python3 advisor.py offer
```
Tells you: accept / counter / hold, writes the counter message.

### When you close a deal
```
python3 listing_generator.py   # writes the resale listing
python3 pipeline.py add        # adds it to tracker
python3 pipeline.py sold       # marks it sold, logs profit
```

---

## SEARCH TERMS RUNNING NOW (56 total)

**Electric:** Sur Ron LBX, Sur Ron Storm Bee, Talaria Sting, Ultra Bee, Talaria XXX, Altis Sigma, Stark Varg, Segway X260, Super73, Cake Kalk, Ebox

**250cc Dirt:** YZ250F, YZ250, CRF250R, KX250, RMZ250, KTM 250 SXF, KTM 250 EXC, Husqvarna FC250, Husqvarna TE250, Beta 250RR

**450cc Dirt:** CRF450R, YZ450F, KX450, RMZ450, KTM 450 SXF, KTM 450 EXC, Husqvarna FC450, Husqvarna FE450, Beta 450RX

**Enduro:** KTM EXC 300/250, Husqvarna TE300, Beta 300RR, Gas Gas EC300

**Supermoto/Dual Sport:** DRZ400SM, DRZ400S, KLX300, Husqvarna 701, KTM 690 SMC

**Mini/Pit:** Honda Grom, Honda Monkey, Kawasaki Z125, CRF125F, KTM 85SX

**Sport:** Yamaha R6, CBR600RR, GSXR600, GSXR750, ZX6R, Ninja 400

**Naked:** Yamaha MT07, Yamaha MT09, Honda CB500

**Adventure:** BMW GS 1200/800, Africa Twin, Tenere 700

**Cars (NEW):** Honda Civic, Toyota Camry, Honda Accord, Toyota Corolla, Hyundai Elantra, Kia Optima, Mazda3, Subaru WRX, Toyota RAV4, Honda CRV

---

## 90-DAY ROADMAP

### Month 1 (NOW) — Build the Machine
- [x] Scanner live 24/7
- [x] Auto-messager sending lowballs
- [x] Cars added to search
- [x] Dashboard live
- [ ] Move scanner to cloud (Railway.app — $5/mo, laptop doesn't need to stay on)
- [ ] Build buyer SMS list — text every past buyer + inquirer:
  *"Hey it's [name], I flip bikes in DC. New inventory weekly — want first dibs?"*
- [ ] Create @twowheels Instagram + TikTok handles NOW (even if you don't post)
- [ ] First flip logged in pipeline
- **Target: 2–4 flips · $2k–$4k profit**

### Month 2 — Multi-Channel
- [ ] Launch 2wheels.com (Claude builds it, inventory auto-syncs)
- [ ] Add eBay Motors listings (listing_generator.py already writes them)
- [ ] Start posting TikToks — 1 per flip: "Bought this for $X, sold for $Y in 48hrs"
- [ ] Expand radius: DC + Northern VA + Baltimore
- [ ] Add consignment: sell others' bikes for 10–15% cut
- **Target: 6–8 flips · $5k–$7k profit**

### Month 3 — Hit $8k
- [ ] Hire part-time helper for pickups/deliveries
- [ ] Daily social content pipeline
- [ ] 2wheels.com getting Google traffic for "sur ron dc", "dirt bike dc"
- **Target: 8–10 flips · $8k+ profit**

### Month 4+ — The Platform
- [ ] Open Two Wheels to other DC resellers — take % on listings
- [ ] Expand: DC → VA → MD → NC → FL → national
- [ ] "Craigslist for bikes but actually good"

---

## MARKETING PLAYBOOK

### TikTok / Reels (Highest ROI)
- Film 30 seconds when you pick up and when it sells
- Hook: "Bought this [bike] for $X — sold it for $Y in [time]"
- Post every flip. 1 video = potential 100k views = free buyers
- Use `listing_generator.py` — it writes the caption and hashtags

### Facebook Groups (Free, Works Now)
- Join every DMV group: dirt bikes, Sur Ron/Talaria, motocross, classifieds
- Post new inventory in all groups the same day you list
- Takes 10 minutes, costs $0

### Buyer SMS List (Highest Conversion)
- Every person who ever inquired = potential repeat buyer
- Text them first when new inventory drops
- "Hey, just got a [bike]. You first before I list it."
- **50 contacts by end of Month 1 = reliable demand**

### 2wheels.com SEO (Long-term Compound)
- "Sur Ron for sale DC" — own that search result
- Each listing page = permanent Google entry
- Claude builds the whole site in one session

---

## PROFIT REQUIREMENTS (built into the AI)
| Spend | Min profit needed |
|---|---|
| Under $1,500 | $600+ |
| $1,500–$3,000 | $1,000+ |
| $3,000–$5,000 | $1,500+ |
| $5,000–$7,000 | $2,000+ |
| $7,000–$8,000 | $3,000+ |

### Distance rules (AI enforces these)
- 0–30 miles: $600+ profit fine
- 30–60 miles: $1,200+ profit needed
- 60–100 miles: $2,000+ profit, must be exceptional
- Over 100 miles: skip

---

## COMMANDS CHEAT SHEET

```bash
# Start scanner (24/7 background)
cd ~/Desktop/fb_deal_scanner && nohup /opt/homebrew/bin/python3 -u main.py --loop > scanner.log 2>&1 &

# Check if scanner is running
ps aux | grep main.py | grep -v grep

# Watch scanner live
tail -f ~/Desktop/fb_deal_scanner/scanner.log

# Stop scanner
pkill -f "main.py --loop"

# Open dashboard
open http://localhost:5001

# Start dashboard (if not running)
cd ~/Desktop/fb_deal_scanner && nohup /opt/homebrew/bin/python3 -u dashboard.py > dashboard.log 2>&1 &

# Deal tools
python3 advisor.py          # Should I buy this?
python3 advisor.py offer    # Should I accept this offer?
python3 advisor.py trade    # Is this trade worth it?
python3 negotiator.py       # Draft my next FB message
python3 pipeline.py         # View all active deals
python3 pipeline.py add     # Add new deal
python3 pipeline.py sold    # Mark sold + log profit
python3 listing_generator.py # Write listing from photos
```

---

## NEXT PHYSICAL ACTIONS (in order)

1. **Check your email** — scanner already sent deals, check what came in
2. **Check FB Messenger** — auto-messager may have already sent openers
3. **Open the dashboard** — http://localhost:5001
4. **Add your past deals to pipeline** — `python3 pipeline.py add` for each one so profits show on dashboard
5. **Deploy to Railway.app** — so scanner runs when laptop is closed (ask Claude to do this)
6. **Reserve @twowheels** on Instagram + TikTok — do this today
7. **Build buyer SMS list** — pull every past inquiry and text them

---

*This file is your business HQ. Come back to it anytime.*
*Dashboard: http://localhost:5001*
