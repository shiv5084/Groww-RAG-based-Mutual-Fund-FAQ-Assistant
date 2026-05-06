# Policy: Facts-Only Mutual Fund FAQ Assistant

This policy defines non-negotiable guardrails for the assistant.

## 1) Scope

- Domain: mutual fund scheme FAQs only.
- Source type: official public sources only.
- Product context: Groww-style FAQ assistant, but facts must come from AMC/AMFI/SEBI sources.

## 2) Allowed and Blocked Sources

### Allowed source classes

- Selected AMC official domains (including relevant subdomains). **This repo’s curated AMC is HDFC Mutual Fund**; allowlisted hosts are in `config/source_allowlist.txt` and schemes in `config/amc_schemes.yaml`.
- `sebi.gov.in`

### Blocked source classes

- Third-party blogs and personal finance opinion sites.
- Unofficial aggregators and forums.
- Social media posts.

## 3) Response Contract (Factual Route)

Every factual response must satisfy all rules below:

1. Maximum 3 sentences.
2. Exactly 1 citation URL in the visible answer.
3. Citation must be allowlisted.
4. Footer required:
   `Last updated from sources: <date>`
5. No speculation, no advice, no return projection.

## 4) Refusal Contract (Advisory / Comparative Route)

Refusal is mandatory for advisory or comparative intent, including:

- "Should I invest?"
- "Should I buy/sell?"
- "Which fund is better?"
- Timing calls and return expectation advice.

Refusal response must:

1. Be polite and clear.
2. Reinforce facts-only scope.
3. Include 1 educational AMFI/SEBI link.

## 5) Performance Query Policy

- Performance-return queries must not produce generated numbers.
- Response should point user to official factsheet source only.
- No performance comparison computation in assistant output.

## 6) Privacy and Security

The system must not collect/store/process:

- PAN / Aadhaar
- Bank account number
- OTP
- Email address or phone number

If users share PII accidentally, do not echo it and avoid persisting it in logs.

## 7) Multi-Thread Safety

- Conversation memory must be isolated by `thread_id`.
- No cross-thread history use for retrieval or generation.

## 8) Change Management

Any update to source policy, refusal wording, or citation/format contract must be reflected in:

- `config/source_allowlist.txt`
- `config/source_blocklist.txt`
- `doc/templates/refusal_educational_links.yaml`
- `doc/problemStatement.md` (if scope changes)
