# Bot Feature Roadmap

## High-Impact Features

### 1. Complete Multilingual Support
- Finish full `ru / en / uz` coverage for all bot replies, reports, error messages, stats screens, and callbacks.
- Keep the interface language consistent across menus, buttons, deep reports, and fallback messages.

### 2. Stronger Link Verification
- Return a clear verdict for every link: `Official`, `Suspicious`, or `Unknown`.
- Validate redirect chains and final destination domains.
- Compare domain names against trusted brands, banks, government portals, marketplaces, and payment providers.
- Show simple user advice when a link looks unsafe.

### 3. Voice Note And Screenshot Analysis
- Extract text from screenshots and run the same scam checks on the detected content.
- Add voice note transcription and analyze spoken scam patterns.

### 4. Scam-Type Specific Advice
- Tailor recommendations by category:
  - phishing
  - fake job scams
  - investment scams
  - romance scams
  - delivery and payment scams

### 5. One-Tap Safety Actions
- Add quick actions such as:
  - `Block sender`
  - `Report scam`
  - `Delete message`
  - `Safety checklist`

## Trust And Product Quality

### 6. Better Explanations
- Show a short plain-language explanation of why a message or link is suspicious.
- Avoid overly technical wording in the main result screen.

### 7. Confidence Score
- Display when the bot is uncertain instead of presenting every result as equally confident.

### 8. Feedback Loop
- Let users mark results as correct or incorrect.
- Use this feedback to improve detection patterns and ranking logic.

### 9. Trusted And Blocked Sources
- Allow users to maintain:
  - trusted contacts
  - trusted domains
  - blocked senders
  - blocked domains

### 10. Conversation-Level Analysis
- Analyze multi-message scam flows instead of only a single message at a time.

## Telegram-Specific Features

### 11. Campaign Detection
- Detect repeated scam messages, links, or scripts being forwarded across many users.

### 12. Sender And Profile Checks
- Check suspicious usernames, impersonation-style handles, and weak account signals.

### 13. Advanced Attachment Risk
- Improve file analysis for:
  - APK
  - ZIP
  - DOCM
  - PDF with embedded links or suspicious text

### 14. Inline Sharing
- Let users share a quick safety verdict directly into Telegram chats.

## Growth And Retention

### 15. Personal Safety History
- Show how many suspicious messages, links, or files the user avoided over time.

### 16. Regional Scam Alerts
- Send optional scam warnings by country and language.

### 17. Family Or Team Protection
- Support shared alerts for family members or teams.

### 18. Admin Dashboard
- Show scam trends, top malicious domains, top scam categories, and detection metrics.

## Recommended Priority Order

1. Complete multilingual support.
2. Upgrade official-link detection.
3. Add screenshot and voice-note analysis.
4. Add a user feedback loop.
5. Add scam-type specific recommendations.

## Short-Term Execution Plan

### This Week
- Finish full language coverage.
- Improve link verdicts and domain trust lists.
- Clean up result wording for clearer explanations.

### Next Stage
- Add screenshot OCR and voice transcription.
- Add feedback collection and reporting.
- Add sender and domain trust management.

### Demo-Friendly Additions
- One-tap safety actions.
- Personal avoided-scam stats.
- Scam trend dashboard and top malicious domains.
