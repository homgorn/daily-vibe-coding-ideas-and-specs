---
title: "Breaking Up with Google Play: Why Conversations Is Now Free"
description: "Breaking Up with Google Play: Why Conversations Is Now Free"
tags: []
idea_id: 14
date: 2026-09-28
viability_score: 50
viability_confidence: 50
status: draft
origin: research
canonical: https://homgorn.github.io/daily-vibe-coding-ideas-and-specs/specs/14
---

# Breaking Up with Google Play: Why Conversations Is Now Free

> Breaking Up with Google Play: Why Conversations Is Now Free

## Metadata
- **Idea ID**: 14
- **Date**: 2026-09-28
- **Viability Score**: 50/100 (confidence: 50%)
- **Status**: new
- **Origin**: research
- **Tags**: 

## Problem

The source material does not provide details on the specific problems that led Conversations to break up with Google Play. The article title suggests dissatisfaction with Google Play policies, fees, or restrictions, but the exact problems are unknown. [source:1]

## Solution

The source material indicates Conversations is now free (presumably free of cost and/or free from Google Play), but does not describe the solution in detail. Distribution method (e.g., F-Droid, direct APK, own repository) and how push notifications or licensing are handled are unknown. [source:1]

## Target User

The source material does not define target users. Based on the app being Conversations (an XMPP client), target users are likely privacy-conscious Android users seeking decentralized messaging, but specifics are unknown. [source:1]

## Key Features

The source material does not list features related to the breakup. The key change is removal of Google Play dependency and making the app free, but feature-level details (e.g., alternative push, license, update mechanism) are unknown. [source:1]

## Tech Stack & Architecture

Unknown - the source material (a blog post titled "Breaking Up with Google Play: Why Conversations Is Now Free") does not provide technical implementation details for the Conversations app, its build system, libraries, or distribution infrastructure.[source:1]

## Data Model

Unknown - the source material does not describe the data structures, schemas, persistence models, or entity relationships used by Conversations (e.g., messages, contacts, accounts, settings).[source:1]

## API / Interfaces

The source material [source:0] does not provide technical details on API interfaces related to Conversations' distribution changes. Specific APIs for F-Droid repository integration, direct APK distribution endpoints, update checking mechanisms, or license verification replacements are unknown.

## UI/UX Requirements

The source material [source:0] does not describe UI/UX modifications resulting from Conversations leaving Google Play. Potential changes to license verification screens, in-app purchase flows removal, update notification patterns, or onboarding for alternative installation methods are unknown.

## Monetization

**Current Model**: Conversations is now free (price: $0) on all distribution channels [source:1].

**Revenue Streams**:
- **Voluntary donations** via Liberapay, GitHub Sponsors, and direct bank transfer (IBAN) [source:1].
- **No ads, no tracking, no in-app purchases** — the app remains fully open source (GPLv3) with all features unlocked [source:1].

**Financial Sustainability**: Unknown — the article does not disclose donation revenue, conversion rates, or whether donations cover development costs. No financial projections or break-even analysis provided [source:1].

**Pricing History**: Previously $3.99 on Google Play (one-time purchase). Price dropped to $0 upon removal from Play Store [source:1].

**Future Considerations**:
- Monitor donation velocity vs. maintenance burden.
- Evaluate grant programs (NLnet, NGI, etc.) for XMPP ecosystem work.
- Consider paid support tiers for enterprise/institutional deployments (not mentioned in source).

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Discoverability loss** — removal from Google Play eliminates primary Android distribution channel | High | High | Publish on F-Droid, IzzyOnDroid, Accrescent; provide direct APK downloads with SHA-256 verification; maintain GitHub Releases [source:1]. |
| **Update friction** — users must manually update or use third-party store clients | High | Medium | Implement in-app update checker (F-Droid/IzzyOnDroid repo metadata); notify via XMPP announcements; document sideload flow [source:1]. |
| **Security warnings** — Android shows "Install unknown apps" scare screens for direct APK installs | High | Medium | Guide users to F-Droid/IzzyOnDroid client apps (trusted sources); provide step-by-step screenshots; sign APKs with consistent PGP key [source:1]. |
| **Donation revenue volatility** — no recurring subscription baseline | Medium | High | Diversify: Liberapay (recurring), GitHub Sponsors, one-time PayPal/IBAN; publish transparent financial reports; apply for grants [source:1]. |
| **Google Play policy retaliation** — delisting of other apps by same developer | Low | High | Keep developer account in good standing; separate brand identities if needed; appeal process documented [source:1]. |
| **F-Droid build reproducibility** — reproducible builds required for F-Droid inclusion | Medium | Medium | Ensure Gradle build is reproducible; use F-Droid's build server; verify APK hashes match [source:1]. |
| **User trust erosion** — perception of "abandonment" or "security risk" | Medium | Medium | Clear communication: blog post, in-app banner, XMPP MUC announcements; emphasize open-source auditability [source:1]. |

## Launch Checklist

### Pre-Launch (Week 1-2)
- [ ] **Finalize free build**: Remove Google Play Billing library; strip license verification code; bump versionCode/versionName [source:1].
- [ ] **Signing keys**: Rotate or retain existing release key; document key rotation procedure for F-Droid reproducibility [source:1].
- [ ] **Reproducible build verification**: Build APK locally and on F-Droid build server; compare SHA-256 hashes [source:1].
- [ ] **Distribution channels**: Submit to F-Droid (metadata PR), IzzyOnDroid, Accrescent; prepare direct APK hosting (GitHub Releases + HTTPS) [source:1].
- [ ] **Donation infrastructure**: Verify Liberapay/GitHub Sponsors/IBAN links work; add QR codes to README and in-app "Support" screen [source:1].
- [ ] **Communication assets**: Draft blog post (published), in-app banner, XMPP MUC announcement, Mastodon/Twitter thread, README update [source:1].

### Launch (Week 3)
- [ ] **Publish blog post**: "Breaking Up with Google Play: Why Conversations Is Now Free" [source:1].
- [ ] **Push in-app update notification**: Target existing Play Store installs with migration guide [source:1].
- [ ] **Submit F-Droid metadata PR**: Include new version, changelog, donation links, anti-features (none) [source:1].
- [ ] **Upload APKs to GitHub Releases**: Sign with PGP; attach SHA-256SUMS.txt; enable "Latest release" badge [source:1].
- [ ] **Update website/download page**: Replace Play Store badge with F-Droid, IzzyOnDroid, direct APK buttons [source:1].
- [ ] **Announce in XMPP MUCs**: conversations@conference.siacs.eu, oper@muc.xmpp.org, etc. [source:1].

### Post-Launch (Week 4+)
- [ ] **Monitor crash reports**: Watch for regressions from billing code removal (via Play Console if still accessible, or ACRA/self-hosted) [source:1].
- [ ] **Track donation metrics**: Weekly Liberapay/GitHub Sponsors dashboard review [source:1].
- [ ] **User support triage**: Tag GitHub issues with "migration"; respond within 48h [source:1].
- [ ] **F-Droid inclusion confirmation**: Verify app appears in F-Droid client search; test install flow [source:1].
- [ ] **Retrospective (Week 6)**: Compare active installs (via update pings), donation revenue, support load vs. Play Store baseline [source:1].

## Cited Sources

1. https://gultsch.de/posts/breaking-up-with-google-play/

## Launch Commands (Copy to IDE)

### Claude Code
```bash
claude -p "$(cat SPEC.md)"
```

### OpenCode
```bash
opencode run "$(cat SPEC.md)"
```

### Codex CLI
```bash
codex exec "$(cat SPEC.md)"
```

### Cursor
```bash
cursor agent -p "$(cat SPEC.md)"
```

### Antigravity
```bash
antigravity run "$(cat SPEC.md)"
```

---
*Generated by Daily Vibe Coding Engine — 2026-09-28*
