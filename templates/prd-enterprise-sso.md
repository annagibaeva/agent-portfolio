# PRD: Enterprise SSO (SAML / OIDC)

**Author:** Anna Gibaeva
**Status:** Draft
**Last updated:** 2026-05-05
**Target release:** v3.0 / Q2 2026

## 1. Summary
Add SAML 2.0 and OIDC single sign-on so admins at mid-market customers can provision TaskFlow through their existing IdP (Okta, Azure AD, Google Workspace). Unblocks deals that currently stall in security review and reduces password-reset support load.

## 2. Problem
- **Who:** IT admins and security buyers at 100-500 person companies evaluating or expanding TaskFlow.
- **Today:** Users sign up with email/password. Admins manage seats manually; offboarding is a checklist item that gets missed.
- **Evidence:**
  - 14 of the last 22 lost deals (>$10k ACV) cited "no SSO" as a blocker — pulled from Salesforce closed-lost reasons.
  - 9% of support tickets in Q1 2026 were password resets.
  - Top-3 ask in the last two customer advisory boards.

## 3. Goals & Non-Goals
**Goals**
- SAML 2.0 SP-initiated and IdP-initiated login working with Okta, Azure AD, Google Workspace.
- OIDC login as a second protocol option.
- SCIM 2.0 user provisioning and deprovisioning.
- Admin self-serve config (no Support ticket required).

**Non-Goals**
- Multi-IdP per workspace (one IdP per workspace at GA).
- Just-in-time role mapping beyond a single default role.
- Social logins (Google/Microsoft consumer) — already shipped.
- Audit log export — tracked separately.

## 4. Success Metrics
- **North star:** 30% of paid workspaces ≥50 seats have SSO enabled within 60 days of GA.
- **Business:** Unblock ≥$400k in pipeline flagged "SSO required" by end of Q3.
- **Guardrails:**
  - Login p95 latency does not regress more than 100ms.
  - Password-reset tickets drop ≥40% in SSO-enabled workspaces.
  - Zero P0 auth incidents in the 30 days post-GA.

## 5. Users & Use Cases
**Primary persona:** IT admin at a 100-500 person company, owns identity stack, reports to CISO or CIO.

Top use cases:
1. Configure SAML connection from Okta and assign to all TaskFlow users (one-time, weekly during rollout).
2. Auto-provision a new hire on day one via SCIM (daily).
3. Deprovision a leaver within 1 hour of HRIS termination (weekly).

## 6. Requirements
### Must-have (P0)
- SAML 2.0 SP- and IdP-initiated SSO with signed assertions.
- OIDC authorization-code flow with PKCE.
- SCIM 2.0 `/Users` create, update, deactivate.
- Admin UI to upload IdP metadata, test connection, and toggle "SSO required" enforcement.
- Domain capture: workspace owner verifies a DNS TXT record before enforcement is allowed.
- Fallback break-glass admin account that bypasses SSO (audited).

### Should-have (P1)
- Group-to-role mapping via SAML attribute or SCIM `groups`.
- Session length policy per workspace (1h / 8h / 24h).
- Admin audit log of SSO config changes.

### Nice-to-have (P2)
- Multiple email domains per workspace.
- Per-user MFA step-up for sensitive actions.

## 7. UX
Figma: figma.com/team/taskflow → "v3.0 / Enterprise SSO" page.

Key flows:
1. Admin → Settings → Authentication → "Set up SSO" wizard (4 steps: choose protocol, paste metadata, verify domain, test login).
2. End-user first SSO login: redirect to IdP, return to last-visited project.
3. Break-glass login: `/login?bypass=1` with TOTP, rate-limited, audit-logged.

## 8. Technical Notes
- Use a vetted library (`passport-saml`, `openid-client`) — do not hand-roll SAML.
- New tables: `sso_connections`, `scim_tokens`, `domain_verifications`. Migrations must be reversible per CLAUDE.md.
- Session token format unchanged; SSO only changes the issuance path.
- Rate limit SCIM endpoints separately from public API (paid tier 1000/min likely too low for bulk imports).
- Threat model review with security before code freeze. Specifically: assertion replay, XML signature wrapping, open-redirect on `RelayState`.

## 9. Rollout
- **Flag:** `enterprise_sso` (default off).
- **Phases:**
  - Internal dogfood — 2 weeks.
  - Closed beta — 5 design-partner customers (Okta + Azure AD), 3 weeks.
  - GA — flag default on for Business and Enterprise plans.
- **Comms:** Changelog post, admin-targeted email to workspace owners ≥50 seats, Sarah-authored engineering blog on the security model, sales enablement deck for AEs.

## 10. Risks & Open Questions
| Risk / Question | Owner | Resolution by |
|---|---|---|
| Pricing — gate behind Enterprise plan or include in Business? | Jordan | 2026-05-19 |
| Do we support encrypted SAML assertions at GA or P1? | Sarah | 2026-05-12 |
| SCIM token rotation UX — manual or auto? | Marcus + Sarah | 2026-05-26 |
| Legal review of break-glass account audit retention | Legal | 2026-06-02 |

## 11. Appendix
- Salesforce closed-lost analysis Q4 2025 – Q1 2026 (Priya).
- Customer advisory board notes, 2026-02 and 2026-04.
- Competitor SSO matrix: Linear, Asana, Monday, Jira.
- RFC-0042: TaskFlow auth architecture (internal).
