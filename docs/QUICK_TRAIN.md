# 🚀 Quick Start — Training New Patterns

## Second 1-2: Open the bot
```text
Telegram → @ScamGuardAI_bot
```

## Second 3-5: Press the button
```text
Main Menu
↓
🧠 Train on a New Pattern ← PRESS
```

## Second 6-15: Send scam text
```text
Copy and send a suspicious message:

"Urgent! 2-room apartment in the city center, price 800,000 UZS!
100% card prepayment, no viewing and no in-person meeting.
Passport is not required, documents are not needed.
WhatsApp: +998901234567"
```

## Second 16-25: Choose severity
```text
🔴 High (9)   ← clear scam
or
🟡 Medium (7) ← suspicious
or
🟢 Low (5)    ← potential risk
```

## Second 26-35: Choose the type
```text
🏠 Rental / Sale   ← listing scams
💰 Investment      ← financial pyramid schemes
❤️ Romance         ← romance scams
🔒 Phishing        ← credential theft
👔 Job             ← fake vacancies
🎁 Giveaway        ← fake prizes
💳 Data theft      ← phishing / account theft
❓ Other           ← if nothing else fits
```

## Result: ✅ Done

The system has learned the new pattern and will detect similar scams more accurately.

---

## What should you add?

### ✅ ADD:
- Real scams you encountered
- New scam schemes the system missed
- Variations of existing scam patterns

### ❌ DO NOT ADD:
- Spam with no fraud element
- Legitimate offers
- Text in a language you cannot verify

---

## Training examples

### 1. New rental scam
```text
"Luxury apartments in a new complex!
A 30% guarantee payment is required.
The owner is in America and will open the unit after transfer.
Hurry, there are already 3 other applicants!"

Choose: 🏠 Rental / Sale + 🔴 High (9)
```

### 2. New investment scam
```text
"BOOM cryptocurrency will go 10x in one month!
Minimum deposit: 100,000.
Trusted team, already 5000 participants.
Hurry, only 50 spots left!"

Choose: 💰 Investment + 🔴 High (9)
```

### 3. New job scam
```text
"Sales Manager (Remote)
Salary: 500,000 RUB / month
No experience? No problem!
A 50,000 RUB deposit is required"

Choose: 👔 Job + 🔴 High (9)
```

---

## If something does not work

### Problem: The bot does not respond
```bash
# Restart the bot
./stop.sh && ./start-bot.sh
```

### Problem: The pattern is not detected during checks
```bash
# Restart all services
./stop.sh && ./start.sh
```

### Problem: Too many false positives
```text
Choose a lower severity (🟢 Low instead of 🔴 High)
or
Add an exclusion rule in backend/services/rule_engine.py
```

---

## Future improvements

```text
🚀 Hot reload without restart
🚀 Pattern moderation
🚀 Versioning with rollback
🚀 Effectiveness statistics
🚀 Rewards for the best patterns
```

Even this simple version already helps protect people. 🛡️

---

**Every new pattern means one fewer deceived person.** 💪
