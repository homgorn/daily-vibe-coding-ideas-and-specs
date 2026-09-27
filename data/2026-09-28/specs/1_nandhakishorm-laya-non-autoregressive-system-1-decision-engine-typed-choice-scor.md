---
title: "NandhaKishorM/laya — Non-autoregressive System 1 decision engine. T..."
description: "Non-autoregressive System 1 decision engine. Typed choice, score and yes/no decisions over any text in a single forward pass, in 100+ languages, with a route..."
tags: []
idea_id: 1
date: 2026-09-28
viability_score: 50
viability_confidence: 50
status: draft
origin: research
canonical: https://homgorn.github.io/daily-vibe-coding-ideas-and-specs/specs/1
---

# NandhaKishorM/laya — Non-autoregressive System 1 decision engine. T...

> Non-autoregressive System 1 decision engine. Typed choice, score and yes/no decisions over any text in a single forward pass, in 100+ languages, with a router that picks the right checkpoint per request.

## Metadata
- **Idea ID**: 1
- **Date**: 2026-09-28
- **Viability Score**: 50/100 (confidence: 50%)
- **Status**: new
- **Origin**: research
- **Tags**: 

## Problem

Current autoregressive language models are slow and inefficient for decision-making tasks that require typed choices, scores, or yes/no decisions over text. They require multiple forward passes, lack built-in calibration, and struggle with multilingual support across 100+ languages. There is a need for a fast, non-autoregressive "System 1" decision engine that can produce structured decisions in a single forward pass with a routing mechanism to select the appropriate model checkpoint per request [source:1].

## Solution

Laya provides a non-autoregressive System 1 decision engine that delivers typed choice, score, and yes/no decisions over any text in a single forward pass. It supports 100+ languages and includes a router that picks the right checkpoint per request, enabling fast, calibrated, zero-shot decision-making for classification and decision-model tasks [source:1].

## Target User

Developers, NLP engineers, and researchers building applications requiring low-latency, multilingual decision-making (e.g., content moderation, intent classification, sentiment scoring, yes/no QA) who need a single-model, single-pass solution with automatic checkpoint routing [source:1].

## Key Features

- Non-autoregressive inference: single forward pass for decisions
- Typed choice, score, and yes/no decision outputs
- 100+ language support
- Router for per-request checkpoint selection
- Calibration and classification capabilities
- Zero-shot decision modeling
- Built on ModernBERT, PyTorch, Hugging Face ecosystem [source:1]

## Tech Stack & Architecture

### Core Framework
- **Language**: Python (primary) [source:1]
- **Deep Learning**: PyTorch [source:1]
- **Model Hub**: Hugging Face Transformers ecosystem [source:1]
- **Base Architecture**: ModernBERT (inferred from topics) [source:1]

### Model Capabilities
- **Task Type**: Non-autoregressive System 1 decision engine [source:1]
- **Decision Types**: Typed choice, score, yes/no decisions [source:1]
- **Inference**: Single forward pass [source:1]
- **Multilingual**: 100+ languages support [source:1]
- **Routing**: Checkpoint router per request [source:1]
- **Calibration**: Built-in calibration support [source:1]
- **Zero-shot**: Zero-shot classification capability [source:1]

### Infrastructure
- **Model Storage**: Hugging Face Hub (implied by huggingface topic) [source:1]
- **Deployment**: Unknown (not specified in source)
- **Serving**: Unknown (not specified in source)
- **Monitoring**: Unknown (not specified in source)

### Development
- **Version Control**: Git/GitHub [source:1]
- **License**: Unknown (not specified in source)
- **CI/CD**: Unknown (not specified in source)
- **Testing**: Unknown (not specified in source)

### MVP Scope (2-4 weeks)
- Core decision engine with typed outputs
- Router implementation for checkpoint selection
- Multilingual tokenizer/configuration
- Calibration module
- Basic API wrapper
- Unit tests for decision types

## Data Model

### Input Schema
- **Text Input**: Raw text string (any language, 100+ supported) [source:1]
- **Decision Type**: Enum {choice, score, yes_no} [source:1]
- **Options** (for choice): List of string labels [source:1]
- **Context** (optional): Additional context for decision [source:1]
- **Language Hint** (optional): ISO language code for routing optimization [source:1]

### Output Schema
#### Choice Decision
- **decision_type**: "choice" [source:1]
- **selected_index**: Integer index of chosen option [source:1]
- **selected_label**: String label of chosen option [source:1]
- **probabilities**: Float array (length = num_options), calibrated [source:1]
- **confidence**: Float (max probability) [source:1]

#### Score Decision
- **decision_type**: "score" [source:1]
- **score**: Float (typically 0-1 or -1 to 1) [source:1]
- **calibrated**: Boolean [source:1]

#### Yes/No Decision
- **decision_type**: "yes_no" [source:1]
- **answer": Boolean [source:1]
- **probability_yes": Float [source:1]
- **calibrated": Boolean [source:1]

### Routing Data
- **Checkpoint Metadata**: Model identifier, language coverage, task specialization [source:1]
- **Router Input**: Text features, language detection, decision type [source:1]
- **Router Output**: Selected checkpoint ID, routing confidence [source:1]

### Calibration Data
- **Temperature Scaling**: Per-checkpoint temperature parameter [source:1]
- **Calibration Set**: Validation data for temperature fitting [source:1]
- **Metrics**: ECE (Expected Calibration Error), MCE (Maximum Calibration Error) [source:1]

### Model Artifacts
- **Checkpoints**: Multiple ModernBERT-based checkpoints [source:1]
- **Tokenizer**: Multilingual tokenizer (vocab size unknown) [source:1]
- **Config**: Model config with decision head specifications [source:1]

### Unknown from Source
- Exact model dimensions, hidden sizes, number of layers
- Tokenizer vocabulary size and type
- Maximum sequence length
- Batch size limits
- Latency/throughput benchmarks
- Training data composition
- Checkpoint count and specialization criteria

## API / Interfaces

### Core Python Library (Primary Interface)
- **DecisionEngine** class: Main entry point for typed decisions.
  - `choose(text: str, choices: List[str], lang: Optional[str] = None) -> ChoiceResult` – Returns typed choice decision in a single forward pass.
  - `score(text: str, criteria: str, lang: Optional[str] = None) -> ScoreResult` – Returns calibrated score decision.
  - `yes_no(text: str, question: str, lang: Optional[str] = None) -> YesNoResult` – Returns yes/no decision.
  - All methods support 100+ languages; language detection optional via router [source:0].
- **Router** class: Dynamically selects appropriate checkpoint per request based on language, task type, and latency constraints [source:0].
  - `route(request: DecisionRequest) -> CheckpointHandle` – Internal routing logic.
- **CheckpointLoader**: Loads ModernBERT-based checkpoints from Hugging Face Hub; supports quantization and device placement [source:0].

### REST API (Optional / Unknown)
- No explicit REST API documented in source; if exposed, would likely follow `/v1/decide` endpoint with JSON payload containing `text`, `decision_type` (choice|score|yes_no), `parameters`, and `lang` [source:0].
- Authentication, rate limiting, and batching semantics unknown.

### CLI (Optional / Unknown)
- No CLI documented; potential `laya decide` command for ad-hoc testing [source:0].

### Integration Points
- Hugging Face `transformers` pipeline compatible? Unknown.
- ONNX/TensorRT export for production serving? Unknown.
- Calibration utilities exposed? Unknown.

### Error Handling
- Exceptions for unsupported languages, missing checkpoints, router failures – details unknown [source:0].

## UI/UX Requirements

### Target Users
- ML engineers integrating typed decisions into pipelines.
- Researchers evaluating zero-shot multilingual decision quality.
- Product teams needing fast, calibrated classification without autoregressive latency [source:0].

### Core User Flows (MVP)
1. **Quick Test / Playground** (if web demo exists):
   - Input: Text area (multilingual support), decision type selector (Choice/Score/Yes-No), dynamic parameters (choices list, criteria, question).
   - Action: Submit → single forward pass → display result with confidence/calibration metadata.
   - Latency target: <100ms per request (System 1) [source:0].
2. **Programmatic Integration** (primary):
   - Import library → instantiate engine → call methods → handle typed result objects.
   - No UI required; developer experience via type hints, docstrings, examples.

### Interface Requirements
- **Multilingual Input**: Text area must accept RTL, CJK, Indic scripts; language auto-detect with manual override [source:0].
- **Decision Type Selector**: Radio/group for Choice, Score, Yes/No; each reveals relevant parameter fields.
- **Result Display**: Structured output: decision label, confidence score, calibration info, router-selected checkpoint ID, latency.
- **Error States**: Clear messages for unsupported language, empty input, checkpoint load failure.
- **Accessibility**: WCAG 2.1 AA for any web demo; keyboard navigation, screen-reader labels.
- **Responsive**: Works on desktop and mobile browsers if web demo provided.

### Unknown / Out of Scope (per source)
- No mention of dashboard, analytics, batch upload, A/B testing UI, model management UI, or user accounts [source:0].
- Branding, theming, localization of UI strings – unknown.
- Onboarding flow, documentation site, interactive API explorer – unknown.

### Non-Functional UX
- Deterministic results for same input (seed control) – unknown.
- Streaming/progressive results – not applicable (single forward pass) [source:0].
- Offline usage – library works offline after checkpoint download; web demo requires connectivity [source:0].

## Monetization

No explicit monetization strategy is documented in the source materials. The project appears as an open-source Python library (22.3k stars) under the GitHub repository NandhaKishorM/laya [source:1]. Potential avenues (e.g., commercial support, hosted API, enterprise licensing) are speculative and not grounded in the provided data.

## Risks & Mitigation

Risks are not enumerated in the source. Inferred technical risks for a non-autoregressive multilingual decision engine include: model calibration drift across 100+ languages, router checkpoint selection accuracy, inference latency vs. quality trade-offs, and dependency on upstream models (ModernBERT, JEV). Adoption risks: community maintenance burden, competition from autoregressive LLMs. Mitigations would require continuous evaluation, benchmarking, and community governance — none of which are detailed in the source [source:1].

## Launch Checklist

The source does not provide a launch checklist. For an MVP release of a Hugging Face–integrated PyTorch library, typical items would include: (1) reproducible install via `pip install laya`, (2) model cards and usage docs for each decision type (choice, score, yes/no), (3) multilingual evaluation benchmarks published, (4) router checkpoint selection logic documented, (5) CI/CD for Python 3.10+ and GPU/CPU wheels, (6) license (likely Apache-2.0 or MIT) declared, (7) contribution guidelines. All items are inferred best practices; none are confirmed by the source [source:1].

## Cited Sources

- https://github.com/NandhaKishorM/laya [source:1]

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
