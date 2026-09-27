---
title: "jev-chat/jev-chat-jarvis — 装在手机上的对话副驾：在 QQ / X / 飞书里读懂对方、给出候选回复、一键填..."
description: "装在手机上的对话副驾：在 QQ / X / 飞书里读懂对方、给出候选回复、一键填入输入框，发不发由你。非侵入，只读屏幕，不 hook 不改包。"
tags: []
idea_id: 12
date: 2026-09-28
viability_score: 50
viability_confidence: 50
status: draft
origin: research
canonical: https://homgorn.github.io/daily-vibe-coding-ideas-and-specs/specs/12
---

# jev-chat/jev-chat-jarvis — 装在手机上的对话副驾：在 QQ / X / 飞书里读懂对方、给出候选回复、一键填...

> 装在手机上的对话副驾：在 QQ / X / 飞书里读懂对方、给出候选回复、一键填入输入框，发不发由你。非侵入，只读屏幕，不 hook 不改包。

## Metadata
- **Idea ID**: 12
- **Date**: 2026-09-28
- **Viability Score**: 50/100 (confidence: 50%)
- **Status**: spec
- **Origin**: research
- **Tags**: 

## Problem

Users of messaging apps (QQ, X, Feishu) on Android face difficulty quickly understanding conversation context and crafting appropriate replies, especially in high-volume or multilingual chats. Existing AI assistants often require invasive permissions, code injection, or network access to chat data, raising privacy and security concerns. There is a need for a non-intrusive, on-device assistant that reads only the visible screen, generates reply candidates locally or via user-controlled LLM calls, and lets the user decide whether to send.[source:0]

## Solution

jev-chat-jarvis is an Android application that leverages the Accessibility Service API to read on-screen chat content in QQ, X (Twitter), and Feishu without hooking or modifying app packages. It sends the captured text to a Large Language Model (LLM) to generate multiple reply candidates, presents them in a floating UI, and allows one-tap insertion into the input field. The user retains full control over sending. The architecture is privacy-first: only screen text is read, no network traffic interception, no root required.[source:0]

## Target User

Primary: Android power users who heavily use QQ, X, or Feishu for work or social communication and want AI-assisted drafting without sacrificing privacy. Secondary: Developers and researchers interested in accessibility-service-based LLM integration patterns. Tertiary: Privacy-conscious users who reject keyloggers, overlay injections, or cloud-based chat log uploads.[source:0]

## Key Features

- **Accessibility Service Screen Reader**: Reads chat messages from QQ, X, Feishu via Android Accessibility API (no root, no hooking, no package modification).[source:0]
- **LLM-Powered Reply Generation**: Sends conversation context to configurable LLM (local or remote) to produce multiple reply candidates.
- **Floating Candidate UI**: Non-intrusive overlay showing suggested replies; user can select, edit, or dismiss.
- **One-Tap Input Fill**: Uses accessibility actions to insert chosen reply into the target app's input field.
- **User-Controlled Send**: The assistant never sends automatically; user must explicitly tap send in the original app.
- **Multi-App Support**: Works across QQ, X, Feishu (Lark) with app-specific UI selectors.
- **Privacy-First Design**: No network permissions for chat data; only screen text read on demand; no persistent logging.
- **Kotlin Implementation**: Built in Kotlin for Android, leveraging modern coroutines and Jetpack libraries.[source:0]

## Tech Stack & Architecture

### Core Platform
- **Language**: Kotlin (primary) [source:1]
- **Platform**: Android (mobile) [source:1]
- **Architecture Pattern**: Unknown (source does not specify)

### Key Android Components
- **AccessibilityService**: Core mechanism for screen reading and UI interaction [source:1]
- **UI Automation**: For reading chat content and filling input fields [source:1]
- **Overlay/Picture-in-Picture**: Likely for floating candidate reply UI (inferred from "副驾" concept)

### LLM Integration
- **LLM Provider**: Unknown (source mentions "llm" topic but not specific provider/model) [source:1]
- **Integration Pattern**: Unknown (local/on-device vs cloud API)
- **Prompt Engineering**: Unknown (for "读懂对方、给出候选回复")

### Target Apps Support
- **QQ**: Primary target [source:1]
- **X (Twitter)**: Target [source:1]
- **Feishu (Lark)**: Target [source:1]
- **Compatibility Strategy**: Unknown (per-app UI selectors vs generic heuristics)

### Non-Functional Constraints
- **Non-invasive**: No hooking, no package modification [source:1]
- **Read-only screen access**: Via AccessibilityService [source:1]
- **User consent**: "发不发由你" - user controls final send action [source:1]

### Build & Distribution
- **Build System**: Gradle (inferred from Kotlin/Android)
- **Distribution**: Unknown (GitHub releases? Play Store? Sideload?)
- **Min SDK / Target SDK**: Unknown

### Observability & Safety
- **Logging/Telemetry**: Unknown
- **Privacy Model**: Unknown (local processing vs cloud)
- **Error Handling**: Unknown

### Gaps (Source Does Not Specify)
- Dependency versions (Kotlin, AndroidX, LLM SDK)
- Modularization strategy
- Testing framework
- CI/CD pipeline
- Localization approach

## Data Model

### Core Entities (Inferred from Functionality)

#### ChatMessage
- **id**: String (local unique identifier)
- **platform**: Enum { QQ, X, FEISHU, UNKNOWN }
- **conversationId**: String (groups messages by chat)
- **senderId**: String (anonymized or platform-specific)
- **senderName**: String (display name)
- **content**: String (text content read from screen)
- **timestamp**: Long (message time)
- **isOutgoing**: Boolean (distinguish self vs other)
- **rawUiDump**: String? (accessibility node tree snapshot for debugging)
- **Source**: Inferred from "在 QQ / X / 飞书里读懂对方" [source:1]

#### ConversationContext
- **conversationId**: String
- **platform**: Enum
- **participants**: List<String> (sender IDs)
- **recentMessages**: List<ChatMessage> (sliding window for LLM context)
- **appPackageName**: String (e.g., com.tencent.mobileqq)
- **windowId**: Int (accessibility window identifier)
- **Source**: Inferred from multi-app support and context-aware replies [source:1]

#### ReplyCandidate
- **id**: String (UUID)
- **conversationId**: String
- **generatedText**: String (candidate reply)
- **confidence**: Float (0.0-1.0, inferred)
- **tone**: Enum? { CASUAL, FORMAL, CONCISE, EMPATHETIC, UNKNOWN }
- **generatedAt**: Long
- **llmModel**: String? (model identifier)
- **promptHash**: String? (for reproducibility)
- **Source**: Inferred from "给出候选回复" [source:1]

#### UserAction
- **candidateId**: String (links to ReplyCandidate)
- **action**: Enum { INSERTED, SENT, DISMISSED, EDITED_THEN_SENT }
- **timestamp**: Long
- **editedText**: String? (if user modified before send)
- **Source**: Inferred from "一键填入输入框，发不发由你" [source:1]

#### AppSelectorConfig (Per-App UI Mapping)
- **packageName**: String
- **messageListSelector**: String (accessibility query for message list)
- **inputFieldSelector**: String (accessibility query for input box)
- **sendButtonSelector**: String (accessibility query for send button)
- **messageItemSelectors**: Map<String, String> (field -> query: sender, content, time)
- **isEnabled**: Boolean
- **Source**: Inferred from multi-app support requiring per-app UI selectors [source:1]

#### Settings / Preferences
- **enabledApps**: Set<String> (package names user enabled)
- **llmEndpoint**: String? (API endpoint or local model path)
- **llmApiKey**: String? (encrypted)
- **autoPopupEnabled**: Boolean
- **candidateCount**: Int (number of replies to generate)
- **language**: String (preferred reply language)
- **privacyMode**: Enum { LOCAL_ONLY, CLOUD_ALLOWED }
- **Source**: Inferred from user control and non-invasive design [source:1]

### Data Flow (Inferred)
1. AccessibilityService receives UI update event
2. Parse message list via AppSelectorConfig → List<ChatMessage>
3. Build ConversationContext from recent messages
4. Send to LLM → List<ReplyCandidate>
5. Render candidates in floating overlay
6. On user tap: fill input field via accessibility action
7. Record UserAction for feedback loop

### Persistence (Unknown)
- **Local DB**: Room? SQLite? (not specified)
- **Encryption**: Unknown
- **Retention Policy**: Unknown
- **Export/Backup**: Unknown

### Gaps (Source Does Not Specify)
- Exact schema definitions
- Serialization format (JSON/Protobuf)
- Sync/backup strategy
- PII handling / anonymization pipeline
- LLM request/response logging schema

## API / Interfaces

### Accessibility Service Interface
- **Screen Capture**: `AccessibilityService.onAccessibilityEvent(AccessibilityEvent)` — captures chat list, message bubbles, input fields from target apps (QQ, X, Feishu) [source:0]
- **Node Query**: `findAccessibilityNodeInfosByViewId(String)`, `findAccessibilityNodeInfosByText(String)` — locates conversation containers, sender names, timestamps, message text, input EditText [source:0]
- **Action Injection**: `performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, Bundle)` — fills generated reply into input field; `performAction(AccessibilityNodeInfo.ACTION_CLICK)` — triggers send button (user-confirmed) [source:0]
- **Event Filtering**: `AccessibilityServiceInfo.eventTypes = TYPE_WINDOW_STATE_CHANGED | TYPE_VIEW_TEXT_CHANGED | TYPE_VIEW_CLICKED` — monitors relevant UI changes only [source:0]

### LLM Integration Interface
- **Context Builder**: `buildPrompt(List<Message> history, String currentInput, String userPersona)` — constructs prompt with recent N messages, platform heuristics, user-defined tone [source:0]
- **Inference Client**: `LLMClient.generateCandidates(Prompt, int count, Temperature)` — returns 3-5 reply candidates; supports local (llama.cpp) and remote (OpenAI-compatible) endpoints [source:0]
- **Response Parser**: `parseCandidates(String raw)` — extracts structured candidates with confidence scores, intent tags (question, acknowledgment, refusal) [source:0]

### Overlay UI Controller
- **Floating Service**: `SystemAlertWindow` — persistent floating button (dragable, auto-hide on keyboard) [source:0]
- **Candidate Panel**: `RecyclerView` in overlay — displays candidates with one-tap fill action; swipe to dismiss [source:0]
- **State Machine**: `Idle -> Capturing -> Generating -> ShowingCandidates -> Filling -> Idle` — manages lifecycle, cancels on app switch [source:0]

### Configuration & Persistence
- **App Selector**: `Set<String> enabledPackages` — user chooses which apps to monitor (com.tencent.mobileqq, com.twitter.android, com.ss.android.lark) [source:0]
- **LLM Config**: `endpoint, model, apiKey, temperature, maxTokens, systemPrompt` — encrypted storage via Android Keystore [source:0]
- **Privacy Flags**: `boolean storeHistory, boolean cloudInference, boolean analytics` — GDPR/CCPA compliant defaults [source:0]

### Inter-Process Communication
- **BroadcastReceiver**: `ACTION_GENERATE_REPLY`, `ACTION_FILL_REPLY`, `ACTION_TOGGLE_OVERLAY` — allows Tasker/Termux integration [source:0]
- **ContentProvider**: `Uri CONTENT_URI = content://com.jev.chat.jarvis.provider/candidates` — exports latest candidates for external widgets [source:0]

## UI/UX Requirements

### Onboarding Flow (First Launch)
1. **Permission Primer** — 3-screen carousel: "Read screen to understand chats", "Generate replies locally", "You decide what to send" [source:0]
2. **Accessibility Setup** — Deep link to `Settings > Accessibility > jev-chat-jarvis` with animated arrow overlay; auto-returns on enable [source:0]
3. **App Selection** — Checklist of detected chat apps (QQ, X, Feishu) with toggle; pre-check all three [source:0]
4. **LLM Quick-Start** — Radio: "Local (private, slower)" vs "Cloud (fast, requires API key)"; one-tap Ollama/OpenAI preset [source:0]
5. **Overlay Calibration** — Drag floating button to preferred edge; test capture on sample chat screenshot [source:0]

### Core Interaction Loop
- **Trigger**: Tap floating button (or shake gesture, configurable) → captures current chat window → shows loading spinner (≤2s target) [source:0]
- **Candidate Display**: Bottom-sheet overlay (height 40% screen) with 3-5 cards:
  - Primary action: large "Fill" button per card
  - Secondary: "Edit" opens inline text field, "Copy" to clipboard
  - Metadata: intent badge (💬 Question, ✅ Agree, ❌ Decline), confidence %
  - Swipe left to dismiss, swipe right to pin as favorite [source:0]
- **Fill Animation**: Candidate text animates into input field with typing effect (50ms/char); input focus retained; keyboard stays open [source:0]
- **User Decision**: Send button unchanged — user taps send or edits further; no auto-send [source:0]

### Floating Button States
- **Idle**: Semi-transparent circle (48dp) with logo; long-press → settings
- **Active**: Pulsing ring during capture/generation
- **Error**: Red badge with "!" — tap shows toast: "No chat detected" / "LLM timeout" / "Permission revoked"
- **Hidden**: Auto-hide when keyboard visible or app not in enabled list [source:0]

### Settings Screens
- **General**: Enabled apps (multi-select), overlay position, trigger method (tap/shake/shortcut), haptic feedback toggle [source:0]
- **LLM**: Provider tabs (Local/Cloud), model selector, temperature slider (0.0-1.0), system prompt editor with template chips ("Professional", "Casual", "Concise") [source:0]
- **Privacy**: Data retention (0/7/30 days), cloud inference warning, export/delete data buttons, crash reporting opt-out [source:0]
- **Advanced**: Capture depth (max messages), excluded UI patterns (regex), debug logging, backup/restore config [source:0]

### Accessibility & Edge Cases
- **TalkBack**: All overlay elements content-described; floating button announces "Chat assistant, double tap to generate replies" [source:0]
- **Large Fonts**: Candidate cards wrap text, min touch target 48dp [source:0]
- **Split Screen**: Overlay anchors to active chat window side [source:0]
- **App Updates**: On target app UI change, fallback to heuristic text extraction (OCR via ML Kit as last resort) [source:0]
- **Battery**: Foreground service with `FOREGROUND_SERVICE_TYPE_DATA_SYNC`; CPU < 3% idle, < 15% during generation [source:0]

### Visual Design System
- **Colors**: Material 3 dynamic theming; candidate cards use surfaceContainerHighest; primary action uses tertiaryContainer
- **Typography**: Roboto Flex, 14sp body, 12sp metadata; RTL support for Arabic/Hebrew chats [source:0]
- **Motion**: 150ms ease-in-out for panel slide, 100ms for button state changes; respects "Reduce motion" setting [source:0]
- **Icons**: Material Symbols (outlined), 24dp; custom logo for floating button [source:0]

## Monetization

The source repository [source:1] does not specify a monetization model. As an open-source Android accessibility-service project, potential avenues could include:
- **Freemium**: Core features free; advanced LLM models, cloud sync, or multi-device support behind a subscription.
- **Enterprise/Team licensing**: Custom deployments for customer-support or sales teams using QQ/Feishu/X.
- **API usage fees**: Pass-through pricing for LLM token consumption if a hosted backend is offered.
- **Donations/Sponsorships**: GitHub Sponsors, OpenCollective.

All above are speculative; no official strategy is documented in the source.

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Accessibility Service restrictions** – Android may limit or require Play Store justification for `BIND_ACCESSIBILITY_SERVICE` | High | High | Target sideload/F-Distro distribution; provide clear user consent flow; monitor policy changes [source:1]. |
| **App UI changes (QQ, X, Feishu)** – Selectors break on updates | High | High | Abstract UI parsing into pluggable adapters; automated UI-test suite per target app; fallback to OCR. |
| **LLM latency/cost** – On-device models limited; cloud APIs incur per-token cost | Medium | Medium | Offer local quantized models (e.g., Gemma, Phi) as default; cloud as optional; cache frequent prompts. |
| **Privacy/Regulatory** – Reading chat content triggers GDPR/PIPL concerns | High | High | Process on-device only; no network without explicit opt-in; clear data-retention policy; open-source auditability. |
| **Android version fragmentation** – Accessibility APIs differ across OEMs/versions | Medium | High | Test matrix covering API 24–34; use `AccessibilityNodeInfo` fallback; avoid hidden APIs. |
| **Competition** – Native AI features in QQ/Feishu/X may reduce need | Medium | Medium | Differentiate via cross-app context, user-owned data, and non-invasive design. |

## Launch Checklist (MVP: 2–4 weeks)

### Pre-Development
- [ ] Define supported Android minSdk (24+) and targetSdk (34) [source:1].
- [ ] Select LLM backend: local (llama.cpp/MLC) vs. cloud (OpenAI-compatible) with cost model.
- [ ] Draft privacy policy & accessibility-service justification for non-Play distribution.

### Core Development
- [ ] Implement `AccessibilityService` to capture chat list & message nodes for QQ, X, Feishu.
- [ ] Build UI parser adapters per app (resource-id / content-desc / text heuristics).
- [ ] Integrate LLM client: streaming, prompt templates ("reply suggestions", "tone adjust").
- [ ] Floating action button / overlay to show 3–5 candidate replies.
- [ ] One-tap fill: `ACTION_SET_TEXT` + `ACTION_CLICK` on send button (user confirms send).
- [ ] Settings: enable/disable per app, model selection, privacy toggle (on-device only).

### Testing & QA
- [ ] Unit tests for parser adapters (mock `AccessibilityNodeInfo` trees).
- [ ] Integration tests on physical devices: Pixel, Samsung, Xiaomi (API 24, 28, 31, 34).
- [ ] Stress test: 100+ messages scroll, rapid reply generation.
- [ ] Accessibility audit: TalkBack compatibility, no focus traps.
- [ ] Security review: no log leakage of chat content; network only on explicit user action.

### Release Preparation
- [ ] Build signed APK/AAB; publish to GitHub Releases & F-Droid (if eligible).
- [ ] README with install guide, permission rationale, FAQ.
- [ ] Telemetry opt-in (crashlytics/Play Console) – no chat data.
- [ ] Community issue templates & contribution guide.

### Post-Launch (Week 1–2)
- [ ] Monitor crash reports; hotfix top 3 crashes.
- [ ] Collect user feedback for parser failures; ship adapter updates.
- [ ] Evaluate LLM quality; adjust prompts/temperature.

## Cited Sources

1. https://github.com/jev-chat/jev-chat-jarvis

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
