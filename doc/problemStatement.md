# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview

This project defines a **facts-only** FAQ assistant for mutual fund schemes, using **Groww** as the reference product context. The assistant answers objective, verifiable questions about mutual funds by retrieving information **only** from official public sources—such as AMC (Asset Management Company) sites, AMFI, and SEBI.

The system must **not** give investment advice, opinions, or recommendations. Every answer must stay within defined limits on clarity, accuracy, and compliance, and must include **one clear source link** plus a **last updated** line from sources.

---

## Objective

Design and implement a **lightweight Retrieval-Augmented Generation (RAG)** assistant that:

- Answers **factual** queries about mutual fund schemes.
- Uses a **curated corpus** of official documents.
- Returns **short, source-backed** responses.

---

## Target Users

- **Retail investors** comparing mutual fund schemes.
- **Customer support and content teams** handling repetitive mutual fund queries.

---

## Scope of Work

### 1. Corpus definition

- Select **one** Asset Management Company (AMC).
- Choose **3–5** mutual fund schemes with **category diversity** (e.g. large-cap, flexi-cap, ELSS).
- Collect **15–25** official public URLs, including:
  - Scheme factsheets  
  - KIM (Key Information Memorandum)  
  - SID (Scheme Information Document)  
  - AMC FAQ / help pages  
  - AMFI / SEBI guidance pages  
  - Guides for downloading statements and tax-related documents  

### 2. FAQ assistant behaviour

The assistant must answer **facts-only** queries, for example:

- Expense ratio of a scheme  
- Exit load rules  
- Minimum SIP amount  
- ELSS lock-in period  
- Riskometer classification  
- Benchmark index  
- How to download statements or capital gains reports  

**Every factual answer must:**

- Use **at most three sentences**.
- Include **exactly one** clear citation link.
- End with a footer:  
  `Last updated from sources: <date>`

### 3. Refusal handling

The assistant must **refuse** non-factual or advisory questions, for example:

- “Should I invest in this fund?”  
- “Should I buy / sell?”  
- “Which fund is better?”  

**Refusal responses must:**

- Be polite and explicit about the **facts-only** scope.
- Reinforce that the assistant does **not** give advice.
- Provide a **relevant educational** link (e.g. AMFI or SEBI).

### 4. User interface (minimal)

Provide a simple UI that includes:

- A **welcome** message.  
- **Three** example questions.  
- A visible disclaimer: **“Facts-only. No investment advice.”**

---

## Constraints

### Data and sources

- Use **only** official public sources (AMC, AMFI, SEBI).  
- Do **not** use third-party blogs or generic aggregator sites as corpus or citations.

### Privacy and security

Do **not** collect, store, or process:

- PAN or Aadhaar numbers  
- Account numbers  
- OTPs  
- Email addresses or phone numbers  

### Content Restrictions

- No investment advice or recommendations.  
- No performance comparisons or return calculations.  
- For performance-related questions, respond with a link to the **official factsheet** only (no invented numbers).

### Transparency

- Answers stay short, factual, and verifiable.  
- Every answer includes a **source link** and **last updated from sources** date.

---

## Expected deliverables

| Deliverable | Notes |
|-------------|--------|
| **README** | Setup steps; chosen AMC and schemes; RAG architecture overview; known limitations |
| **Sample Q&A** | 5–10 example queries with the assistant’s answers and links |
| **Disclaimer snippet** | `Facts-only. No investment advice.` |

---

## Multiple Chat Thread Support
- A RAG-based chatbot capable of handling **multiple independent conversations simultaneously**

---

## Success criteria

- Accurate retrieval of factual mutual fund information.  
- Strict **facts-only** answers; no advisory drift.  
- **Consistent** valid source citations.  
- **Polite, clear refusals** for advisory or unsuitable queries.  
- **Clean, minimal** UI that matches the scope above.

---

## Summary

The goal is a **trustworthy, transparent, and compliant** mutual fund FAQ assistant that favours **accuracy and traceability** over sounding clever. Users should get **verified, source-backed** information only—no advisory bias and no speculative content.
