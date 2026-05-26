---
name: FB Deal Scanner Project
description: 24/7 Facebook Marketplace scanner that finds underpriced bikes and emails alerts
type: project
originSessionId: acfbc94c-308f-4377-9393-0ca3939031ef
---
Working directory: ~/Desktop/fb_deal_scanner/

Files:
- main.py — entry point: --setup (login), --loop (24/7), bare (one scan)
- scraper.py — undetected_chromedriver + Selenium, scrapes FB Marketplace
- analyzer.py — Claude API scoring (claude-sonnet-4-6), scores 1-10
- emailer.py — Gmail SMTP alerts to stykie4@gmail.com
- config.py — search terms, prices, RESALE_CONTEXT for AI
- advisor.py — interactive: should I buy? accept offer? take trade?
- negotiator.py — drafts FB Messenger replies, handles haggle → meetup flow
- pipeline.py — deal tracker: lead → offer_out → negotiating → owned → sold
- listing_generator.py — writes listing descriptions for selling

Key config:
- SCAN_INTERVAL_MINUTES = 20
- LOCATION = "washington-dc", RADIUS_MILES = 100
- MIN_PRICE = 300, MAX_PRICE = 8000, MIN_DEAL_SCORE = 6
- Chrome profile saved in chrome_profile/ directory

Running 24/7:
```
cd ~/Desktop/fb_deal_scanner && nohup /opt/homebrew/bin/python3 -u main.py --loop > scanner.log 2>&1 &
```

Check log: tail -50 ~/Desktop/fb_deal_scanner/scanner.log
Check process: ps aux | grep main.py | grep -v grep

Known issues fixed:
- SingletonLock crash → cleanup_locks() runs before every Chrome launch
- Distance filter → parses "X mi" from location text, skips >100 miles
- Junk listings → uses only specific model search terms (no generic terms)
- Wrong Python → always use /opt/homebrew/bin/python3 -u
- Output buffering in nohup → use -u flag

**Why:** Chrome profile gets locked when Chrome crashes; cleanup needed on restart.
