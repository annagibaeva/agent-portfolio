# PRD: Audit Log Export — S3 Streaming with PII Redaction & Tamper-Evidence

**Author:** TBD
**Status:** Draft
**Last updated:** 2026-05-25
**Target release:** v3.3 / Q1 2027

## 1. Summary
TaskFlow enterprise customers — particularly those in regulated industries — need a verifiable, continuous record of every workspace event delivered to infrastructure they own. Today no such export exists, forcing compliance officers to rely on in-app audit views that are neither SIEM-ready nor tamper-evident. This feature streams all workspace events to a customer-owned S3 bucket in near-real-time, applies SOC2-grade tamper-evidence (cryptographic chaining), and redacts PII before events leave TaskFlow's systems. It is gated to enterprise tier and targets full enablement across all enterprise tenants within 90 days of GA.

## 2. Problem & Users
- **Primary persona:** Compliance officers and security teams at enterprise customers (typically 50–500-seat companies in regulated verticals)
- **What they do today:** Export periodic CSV snapshots from the in-app audit log, manually redact PII, and import into a SIEM — a brittle, labor-intensive process with multi-hour latency
- **Evidence the problem is real:** TBD — open question (see §9); flag during enterprise sales cycles as a blocker to sign
- **Top use cases and frequency:**
  1. Continuous ingestion into a customer SIEM (Splunk, Datadog, etc.) — ongoing, daily
  2. On-demand forensic review of permission changes or data exports — ad hoc, weekly
  3. Evidence package for SOC2 / ISO 27001 auditor — quarterly / annual

## 3. Goals & Non-Goals
**Goals**
- 100% of enterprise tenants have S3 export enabled within 90 days of GA
- p99 event-to-S3 latency ≤ 60 seconds under normal load
- Zero PII leaks: all redaction happens before events leave TaskFlow's network boundary
- Events are tamper-evident: any modification to a delivered file is detectable by the customer

**Non-Goals**
- Splunk / Datadog / generic webhook connectors (future release)
- Custom per-customer event-type filtering
- Retroactive export of historical events pre-feature-launch
- Real-time alerting or rule-based triggers on event content

## 4. Success Metrics
- **North-star:** ≥ 100% of enterprise tenants with S3 export enabled ≤ 90 days post-GA
- **Latency guardrail:** p99 event-to-S3 latency ≤ 60 s; p50 ≤ 15 s
- **Reliability guardrail:** event delivery durability ≥ 99.9% (no silent drops)
- **Security guardrail:** 0 PII-positive events delivered to customer buckets (validated by automated scan in staging)
- **Must NOT regress:** existing in-app audit log availability and search latency

## 5. Requirements

### Must-have (P0)
- Stream all workspace event types (auth, permission changes, data exports, project/task CRUD, member management) to a customer-configured S3 bucket via cross-account IAM role
- PII redaction applied server-side before events leave TaskFlow's network; redacted fields replaced with a deterministic token so event correlation remains possible
- Tamper-evidence: each delivered file includes a SHA-256 hash and an HMAC signed with a TaskFlow-managed key; hashes are chained across sequential files so gaps are detectable
- Events delivered as newline-delimited JSON (NDJSON) files, partitioned by `workspace_id / YYYY / MM / DD / HH /`
- S3 destination, IAM role ARN, and KMS key ARN configurable by a TaskFlow admin in the enterprise settings UI
- Feature gated to enterprise tier; attempting to enable on a non-enterprise workspace returns a clear upgrade prompt
- Delivery failures retry with exponential backoff for ≥ 24 hours; ops team alerted on sustained failures > 15 minutes

### Should-have (P1)
- Test-delivery button in the settings UI that writes a synthetic event to the configured bucket and confirms success/failure in under 30 seconds
- Per-workspace enable/disable toggle without requiring TaskFlow engineering intervention
- Delivery status dashboard (last successful delivery timestamp, error rate) visible to the workspace admin
- Support for multi-region S3 buckets (us-east-1, eu-west-1, ap-southeast-1 at minimum)

### Nice-to-have (P2)
- Configurable file-roll interval (default 5 minutes; range 1–60 minutes)
- Option for customer to provide their own KMS key for HMAC signing

## 6. Dependencies
| Dependency | Team | Blocking for GA? |
|---|---|---|
| Kinesis pipeline tap into existing event bus | Data Engineering | **Blocking** |
| PII detection model integration + validation | Security | **Blocking** |
| Cross-account S3 DPA template and legal review | Legal | **Blocking** |
| Multi-region S3 replication support | Platform | **Blocking** |
| Enterprise gating in pricing/billing system | Sales / Growth | **Blocking** |
| SOC2 controls review of tamper-evidence design | Security | **Blocking** |
| In-app settings UI (admin panel extension) | Frontend | **Blocking** |

## 7. UX
> LOW CONFIDENCE
Figma link: TBD — Marcus Rivera to design; reference TaskFlow enterprise settings patterns for consistency.

Key flows:
1. **Setup flow** — Enterprise admin navigates to Settings → Security & Compliance → Audit Export; enters S3 bucket ARN, cross-account IAM role ARN, optional KMS key ARN; clicks "Verify & Enable"; sees confirmation or error inline.
2. **Test delivery** — Admin clicks "Send test event"; UI polls for confirmation and shows success (object key written) or failure (error message with troubleshooting link) within 30 s.
3. **Status view** — Admin sees last successful delivery timestamp, 24-hour error count, and a "Disable export" toggle.
4. **Onboarding** — On first enterprise login post-GA, a dismissible banner prompts admins to configure audit export; links to docs.

## 8. Technical Notes & Rollout

**Architecture**
- Tap into existing Kinesis stream (Data Eng); add a consumer that fans out to per-workspace S3 writers
- PII redaction runs as a Lambda transform in the Kinesis pipeline; uses Security team's detection model (exact integration TBD — see §9)
- Tamper-evidence: writer generates NDJSON batch, computes SHA-256, signs HMAC with a per-workspace secret stored in AWS Secrets Manager, appends a `_manifest.json` sidecar per file
- Cross-account delivery via AssumeRole; customer provides IAM role ARN with `s3:PutObject` on their bucket
- Feature flag: `enterprise_audit_export_enabled` — default `false`; enabled per workspace via admin UI or internal tooling

**Data model changes**
- New table: `audit_export_configs (workspace_id, s3_bucket_arn, iam_role_arn, kms_key_arn, enabled, created_at, updated_at)`
- New table: `audit_export_delivery_log (workspace_id, file_key, delivered_at, event_count, hmac_signature, status)`

**Perf / rate-limit considerations**
- High-volume workspaces (> 10k events/min) need back-pressure handling in the Kinesis consumer — coordinate with Data Eng
- S3 `PutObject` rate limits: partition strategy (per-workspace prefix) should stay well under 3,500 PUT/s per prefix

**Rollout plan**
1. **Internal alpha** (2026-Q3): Enable on TaskFlow's own workspace; ops and Security validate delivery, latency, and PII redaction accuracy
2. **Closed beta** (2026-Q4): 5–10 design-partner enterprise customers; gather SOC2 auditor feedback
3. **GA** (Q1 2027, v3.3): Enable for all enterprise tier; 90-day adoption campaign with CSM outreach

**Comms plan**
- Changelog entry and in-app banner for enterprise admins at GA
- CSM-led onboarding email sequence targeting all enterprise workspace admins
- Docs page: setup guide, IAM policy template, tamper-evidence verification script

## 9. Risks & Open Questions
| Risk / Question | Owner | Resolution by |
|---|---|---|
| No hard evidence (tickets/interviews) that audit export is a signed-deal blocker vs. nice-to-have | Sales / PM | 2026-06-30 |
| PII detection model false-negative rate unknown — what's the acceptable miss rate for GA? | Security | 2026-07-31 |
| DPA template for cross-account S3 delivery: does Legal need per-customer addendums or is a standard exhibit sufficient? | Legal | 2026-08-31 |
| Tamper-evidence key rotation: who manages rotation cadence and what's the customer's verification workflow? | Security / Platform | 2026-09-30 |
| Multi-region replication timeline from Platform team — could block GA if not scoped into Q3 planning | Platform | 2026-07-15 |
| Event schema versioning: how are breaking schema changes communicated to customers with existing SIEM parsers? | Data Engineering / PM | 2026-09-30 |
| Pricing: is audit export included in all enterprise plans or a premium add-on? | Sales / Jordan Park | 2026-06-30 |
