---
title: "PNOE’s new face mask wants to make lab-grade breath testing a self-..."
description: "PNOĒ, the Malden, Mass.-based startup whose breath-analyzing mask used to bear an unfortunate resemblance to Bane's, is launching a sleeker self-serve versio..."
tags: []
idea_id: 18
date: 2026-09-28
viability_score: 50
viability_confidence: 50
status: draft
origin: research
canonical: https://homgorn.github.io/daily-vibe-coding-ideas-and-specs/specs/18
---

# PNOE’s new face mask wants to make lab-grade breath testing a self-...

> PNOĒ, the Malden, Mass.-based startup whose breath-analyzing mask used to bear an unfortunate resemblance to Bane's, is launching a sleeker self-serve version on October 1 that lets gym-goers measure their VO₂ max and other metabolic markers in eight minutes without a trained operator.

## Metadata
- **Idea ID**: 18
- **Date**: 2026-09-28
- **Viability Score**: 50/100 (confidence: 50%)
- **Status**: new
- **Origin**: news
- **Tags**: 

## Problem

Traditional lab-grade metabolic testing (VO₂ max, respiratory exchange ratio, substrate utilization) requires expensive equipment, trained technicians, and 20-60 minute supervised protocols. This limits access to elite athletes, clinical settings, or research labs. Gym-goers and fitness enthusiasts lack a practical, self-serve way to obtain lab-grade metabolic data for personalized training and nutrition planning [source:1].

## Solution

PNOĒ's new self-serve breath-analysis mask enables gym-goers to complete a lab-grade metabolic test in 8 minutes without a trained operator. The sleeker hardware replaces the previous Bane-like form factor with a design suited for unattended use in commercial fitness facilities. The system captures breath-by-breath gas exchange, computes VO₂ max and other metabolic markers, and delivers results directly to the user [source:1].

## Target User

Primary: Commercial gyms, health clubs, and boutique fitness studios seeking to offer lab-grade metabolic testing as a self-serve amenity. Secondary: Fitness enthusiasts and recreational athletes who want VO₂ max and metabolic data to personalize training zones, nutrition, and recovery without booking a clinical appointment. Tertiary: Corporate wellness programs and performance centers looking for operator-free metabolic screening [source:1].

## Key Features

- Self-serve 8-minute metabolic test protocol (VO₂ max, RER, fat/carb oxidation) with no trained operator required [source:1]
- Redesigned mask form factor eliminating the previous Bane-like appearance for improved user comfort and adoption [source:1]
- Breath-by-breath gas analysis delivering lab-grade accuracy in a gym environment [source:1]
- Automated data capture, processing, and result delivery to the end user [source:1]
- Plug-and-play deployment for fitness facilities (hardware + software bundle) [source:1]
- Launch date: October 1, 2026 [source:1]

## Tech Stack & Architecture

### Device Firmware (Embedded)
- **MCU**: Unknown per source [source:1]
- **Sensors**: Breath analysis sensors (O₂, CO₂, flow rate) – unknown specifics [source:1]
- **Connectivity**: BLE 5.0+ for phone pairing; Wi‑Fi for direct cloud upload – inferred for self‑serve gym use
- **Power**: Rechargeable Li‑ion battery – unknown capacity [source:1]
- **Firmware RTOS**: Zephyr or FreeRTOS – unknown [source:1]
- **OTA Updates**: Required for sensor calibration & algorithm updates

### Mobile App (iOS / Android)
- **Framework**: React Native (single codebase) – unknown [source:1]
- **BLE Library**: react-native-ble-plx or native CoreBluetooth / Android BLE
- **Auth**: OAuth 2.0 / OpenID Connect (Apple/Google sign‑in + gym SSO)
- **Offline Cache**: SQLite (via WatermelonDB or Realm) for session data when offline
- **UI**: Guided 8‑minute test flow with real‑time sensor feedback

### Cloud Backend
- **API Gateway**: AWS API Gateway / Google Cloud Endpoints – unknown [source:1]
- **Compute**: Serverless functions (AWS Lambda / Cloud Run) for session processing
- **Data Pipeline**: Kafka / Kinesis for raw breath‑stream ingestion → time‑series DB
- **Time‑Series DB**: InfluxDB / TimescaleDB for high‑resolution breath waveforms
- **Relational DB**: PostgreSQL (users, gyms, devices, aggregated results)
- **AuthZ**: JWT with RBAC (gym admin, trainer, end‑user)
- **ML Inference**: Containerized model (ONNX/TensorRT) for VO₂ max & metabolic markers – unknown model details [source:1]
- **Monitoring**: Prometheus + Grafana; Sentry for error tracking

### Gym Dashboard (Web)
- **Framework**: Next.js (React) with TypeScript
- **Real‑time**: WebSocket / Server‑Sent Events for live session monitoring
- **Charts**: Recharts or uPlot for metabolic trends
- **Admin**: Device fleet management, calibration scheduling, usage analytics

### DevOps / CI/CD
- **IaC**: Terraform (AWS/GCP)
- **CI**: GitHub Actions – build, test, lint, container scan
- **CD**: ArgoCD / Flux for GitOps deployment
- **Secrets**: HashiCorp Vault / AWS Secrets Manager
- **Logging**: ELK / Loki + Promtail

### Compliance & Security
- **HIPAA**: If PHI handled – unknown if applicable [source:1]
- **GDPR/CCPA**: Data deletion, consent flows
- **Encryption**: TLS 1.3 in transit; AES‑256 at rest
- **Device Attestation**: Hardware‑backed key storage (SE/TPM) for firmware auth

## Data Model

### Core Entities

#### User
- `user_id` (UUID, PK)
- `email` (string, unique)
- `password_hash` (string) – if not using social login only
- `first_name`, `last_name` (string)
- `date_of_birth` (date) – for age‑adjusted norms
- `sex` (enum: male, female, other)
- `height_cm`, `weight_kg` (numeric) – for metabolic calculations
- `created_at`, `updated_at` (timestamp)
- `consent_version` (string) – GDPR/CCPA consent tracking
- `gym_id` (FK → Gym, nullable) – home gym affiliation

#### Gym / Location
- `gym_id` (UUID, PK)
- `name` (string)
- `address` (JSON: street, city, state, zip, country)
- `timezone` (string, IANA)
- `subscription_tier` (enum: free, pro, enterprise)
- `created_at` (timestamp)

#### Device (Mask Unit)
- `device_id` (UUID, PK)
- `serial_number` (string, unique)
- `firmware_version` (string)
- `hardware_revision` (string)
- `gym_id` (FK → Gym)
- `status` (enum: active, maintenance, retired, lost)
- `last_calibration_at` (timestamp, nullable)
- `battery_health_pct` (numeric, 0‑100)
- `registered_at` (timestamp)

#### TestSession
- `session_id` (UUID, PK)
- `user_id` (FK → User)
- `device_id` (FK → Device)
- `gym_id` (FK → Gym) – denormalized for query speed
- `started_at`, `ended_at` (timestamp)
- `duration_seconds` (integer) – target 480 sec (8 min) [source:1]
- `protocol_version` (string) – test protocol identifier
- `status` (enum: in_progress, completed, aborted, error)
- `quality_score` (numeric, 0‑1) – signal quality metric
- `notes` (text, nullable)

#### BreathSample (high‑resolution time‑series, stored in InfluxDB/TimescaleDB)
- `session_id` (FK → TestSession)
- `timestamp` (nanosecond precision)
- `flow_rate_lpm` (float) – liters per minute
- `o2_fraction` (float) – O₂ concentration %
- `co2_fraction` (float) – CO₂ concentration %
- `temperature_c` (float, optional)
- `humidity_pct` (float, optional)
- `sensor_status` (bitmask) – fault flags

#### MetabolicResult (aggregated per session)
- `result_id` (UUID, PK)
- `session_id` (FK → TestSession, unique)
- `vo2_max_ml_kg_min` (float) – primary metric [source:1]
- `vt1_vo2`, `vt2_vo2` (float) – ventilatory thresholds
- `rq_peak` (float) – respiratory quotient
- `fat_ox_rate`, `carb_ox_rate` (float) – substrate oxidation
- `hr_avg`, `hr_max` (integer, nullable) – if HR strap paired
- `calculated_at` (timestamp)
- `algorithm_version` (string) – model version used

#### CalibrationRecord
- `calibration_id` (UUID, PK)
- `device_id` (FK → Device)
- `performed_at` (timestamp)
- `performed_by` (string – tech ID or "auto")
- `reference_gas_lot` (string)
- `offset_o2`, `offset_co2`, `gain_flow` (float)
- `passed` (boolean)

#### FirmwareRelease
- `release_id` (UUID, PK)
- `version` (string, semver)
- `changelog` (text)
- `artifact_url` (string – signed S3/GCS link)
- `released_at` (timestamp)
- `target_hardware_revision` (string)
- `mandatory` (boolean)

### Relationships
- User 1‑→ Many TestSession
- Device 1‑→ Many TestSession
- Gym 1‑→ Many User, Device, TestSession
- TestSession 1‑→ 1 MetabolicResult
- TestSession 1‑→ Many BreathSample (time‑series)
- Device 1‑→ Many CalibrationRecord

### Indexing & Partitioning
- PostgreSQL: B‑tree on `user_id`, `device_id`, `gym_id`, `started_at` in TestSession
- Time‑series DB: Partition by day on `timestamp`; retention 2 years raw, 10 years aggregated
- Device telemetry (battery, signal) separate metrics table with 30‑day TTL

### Data Governance
- PII: User table encrypted at column level for email, name
- Anonymization: After 90 days inactivity, pseudonymize `user_id` in analytical exports
- Backup: Daily PG dump + WAL‑G; continuous TSDB snapshot to cold storage

## API / Interfaces

### Device-to-Cloud API
- **Protocol**: HTTPS/REST with mTLS (inferred for medical device data)
- **Authentication**: Device certificate + JWT for session
- **Endpoints**:
  - `POST /v1/sessions/start` — Initialize test session; payload: `{device_id, user_id?, gym_id, test_type: "vo2_max"|"rmr"|"metabolic"}`
  - `PUT /v1/sessions/{id}/stream` — WebSocket or chunked HTTP for real-time breath flow, O2/CO2 concentrations, timestamps (10 Hz minimum)
  - `POST /v1/sessions/{id}/complete` — Finalize; returns `{vo2_max_ml_kg_min, vco2, rer, vt, bf, hr?, zones[], confidence_score}`
  - `GET /v1/sessions/{id}/report` — PDF/JSON report for user & facility
- **Data Schema** (FHIR Observation profile for Device Metrics):
  - `code`: LOINC 20564-1 (VO2 max), 19861-4 (VCO2), 3141-9 (RER)
  - `valueQuantity`: value, unit (UCUM), comparator
  - `device`: reference to Device resource (mask serial, firmware)
  - `performer`: PractitionerRole (self) or Organization (gym)
- **Error Handling**: Retry with exponential backoff; queue locally if offline > 5 min; alert on sensor drift > 5% from calibration baseline

### Gym Management API (B2B)
- `GET /v1/facilities/{gym_id}/devices` — List masks, firmware, calibration status
- `POST /v1/facilities/{gym_id}/calibration/schedule` — Trigger on-site calibration workflow
- `GET /v1/facilities/{gym_id}/analytics/usage` — Sessions/day, completion rate, avg duration
- **Webhooks**: `session.completed`, `device.error`, `calibration.due`

### User-Facing API (Mobile/Web)
- `GET /v1/users/me/sessions` — Paginated history with filters
- `GET /v1/users/me/sessions/{id}/insights` — AI-generated trends, zone recommendations
- `POST /v1/users/me/consent` — HIPAA/GDPR consent management
- **Auth**: OAuth 2.0 + PKCE; scopes: `profile`, `sessions:read`, `insights:read`

### Integration Points (Unknown from source)
- EHR (Epic/Cerner) via FHIR `Observation` write — *unknown if supported*
- Fitness apps (Apple Health, Garmin, Strava) — *unknown if supported*
- Billing/insurance (CPT 94621, 94618) — *unknown if automated*

### Security & Compliance
- HIPAA BAA with cloud provider; AES-256 at rest, TLS 1.3 in transit
- SOC 2 Type II; ISO 13485 for device firmware
- Data retention: 7 years (medical) or user deletion request

[source:0]

## UI/UX Requirements

### Physical Device (Mask)
- **Form Factor**: Sleek, non-Bane aesthetic; lightweight (<300 g target); adjustable straps for 5th–95th percentile head sizes
- **Materials**: Medical-grade silicone seal, hypoallergenic; single-use disposable filter cartridge (inferred)
- **Indicators**:
  - LED ring: breathing pace guide (blue inhale, green hold, amber exhale)
  - Status LEDs: power (white), Bluetooth (blue), error (red), calibration (yellow)
  - Haptic motor: vibration cues for pace adherence
- **Controls**: Single capacitive button (start/pause/end); no screen on device
- **Hygiene**: User-replaceable mouthpiece filter; wipe-down protocol printed on case

### Self-Serve Kiosk / Tablet App (Gym-Facing)
- **Flow**:
  1. Welcome / QR code scan (links to user app) or guest mode
  2. Consent & PAR-Q+ screening (digital)
  3. Mask fit check: real-time seal quality graph (pressure sensor)
  4. Guided warm-up: 2 min easy breathing with visual pacer
  5. Ramp protocol: 8-min incremental test (source: "eight minutes") with target watts/HR zones
  6. Cool-down: 1 min guided breathing
  7. Results summary: VO₂ max, metabolic age, training zones, percentile vs. age/sex
  8. Save / share / print QR for mobile app
- **Accessibility**: WCAG 2.1 AA; voice-over, high contrast, scalable text, one-handed operation
- **Languages**: EN, ES (minimum); RTL support for future
- **Offline Mode**: Cache last 50 sessions; sync when online

### User Mobile App (iOS/Android)
- **Onboarding**: Account creation, health kit permissions, goal setting (performance, longevity, weight)
- **Dashboard**: Latest VO₂ max trend (6 mo), zone distribution, readiness score
- **Session Detail**: Breath-by-breath overlay, zone time %, AI insights ("Your fat-max zone is 118–132 bpm")
- **Programs**: 4-week zone-based plans synced from kiosk results
- **Social/Export**: Share card (image), CSV export, Apple Health / Google Fit write
- **Notifications**: Re-test reminders (90 days), firmware updates, calibration alerts

### Gym Staff Dashboard (Web)
- **Real-time Monitor**: Active sessions, mask status, queue length
- **Fleet Health**: Battery, firmware, calibration due, error logs
- **Member Analytics**: Adoption %, repeat rate, avg VO₂ max by cohort
- **Actions**: Remote reboot, force calibration, disable/enable device

### Key UX Principles (Inferred)
- **Zero-Training**: No operator; all guidance on-screen + haptic + audio
- **Safety First**: Auto-stop if HR > 95% max predicted, SpO2 < 90% (if sensor present), or user taps button 3× rapidly
- **Trust Signals**: FDA clearance badge (if applicable), CLIA lab badge, data encryption notice
- **Delight**: Confetti animation on PR; streak badges; anonymous leaderboard (opt-in)

### Unknown from Source
- Exact mask weight, battery life, charge method (USB-C? wireless?)
- Whether SpO2 / ECG sensors integrated
- Kiosk hardware spec (iPad? Android tablet? custom?)
- Pricing model (per session / membership add-on / SaaS)
- Supported protocols beyond VO₂ max ramp (RMR, submax, spirometry)

[source:0]

## Monetization

No monetization details (pricing, business model, revenue streams) are disclosed in the source article. Unknown.

## Risks & Mitigation

- **Brand perception**: Previous mask design bore "unfortunate resemblance to Bane's" mask, potentially affecting user adoption [source:1]. Mitigation: Sleeker redesign for new self-serve version.
- **Self-serve accuracy**: Eliminating trained operators introduces risk of user error affecting VO₂ max and metabolic marker measurements [source:1]. Mitigation: Automated guidance and validation in software.
- **Market adoption**: Gym-goers may be reluctant to wear a mask for 8-minute test; hygiene and comfort concerns [source:1]. Mitigation: Improved ergonomics and disposable/sanitizable components.
- **Regulatory**: Lab-grade claims may require FDA/CE clearance for medical/wellness use; not addressed in source. Unknown status.
- **Competition**: Other metabolic testing solutions (e.g., metabolic carts, wearable estimators) may offer lower friction. Unknown competitive landscape.

## Launch Checklist

- [ ] Finalize hardware production of sleeker self-serve mask variant [source:1]
- [ ] Complete software for automated 8-minute VO₂ max and metabolic marker protocol [source:1]
- [ ] Validate self-serve accuracy against operator-assisted baseline [source:1]
- [ ] Prepare gym deployment kits (masks, sanitization, instructions) [source:1]
- [ ] Execute marketing launch for October 1 availability [source:1]
- [ ] Establish support channels for gym staff and end-users
- [ ] Monitor early adoption metrics and user feedback post-launch

## Cited Sources

1. https://techcrunch.com/2026/09/26/pnoes-new-face-mask-wants-to-make-lab-grade-breath-testing-a-self-serve-affair/

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
