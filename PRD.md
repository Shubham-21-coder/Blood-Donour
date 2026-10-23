# LifeLink: Emergency Blood Donor Agent
**Product Requirements Document (ASI:One Agent Challenge, "From Intent to Action")**

- **Version**: 0.1 (hackathon scope)
- **Date**: 23 Oct 2026
- **Status**: Draft for build
- **Primary surface**: ASI:One chat (no custom frontend)

---

## 1. Problem
When a patient needs blood urgently, families lose critical time calling relatives, posting in WhatsApp groups and phoning blood banks one by one. Information is scattered and unverified, stock data is stale, and donors are contacted blindly or not at all. Donors, in turn, worry about spam and about sharing their phone numbers with strangers.

## 2. Vision
A user types one sentence into ASI:One, such as *"Need 2 units of O+ at SMS Hospital, Jaipur, urgent"*, and the agent plans, queries, alerts and confirms. It returns a confirmed donor and a backup blood-bank list within minutes, without the user leaving the conversation.

## 3. Target users
| User | Need |
| :--- | :--- |
| **Requester** (patient family, friend) | Find blood fast, trust who they are contacting |
| **Donor** | Be alerted only when relevant, keep contact details private |
| **Hospital / blood bank** | Broadcast urgent needs, reduce phone-chasing |

*For the hackathon the primary persona is the Requester. The donor side is simulated.*

## 4. Goals and non-goals
### Goals (hackathon)
- Complete the primary workflow entirely inside an ASI:One conversation.
- Show real multi-step planning and tool execution, with multi-agent orchestration.
- Be registered on Agentverse, implement the Agent Chat Protocol (ACP), and be discoverable through ASI:One.
- Make safety and privacy visible in the demo.

### Non-goals (hackathon)
- Real donor onboarding, real SMS/WhatsApp alerts to the public, real medical record verification.
- Real-time integration with government blood-bank systems.
- Any payment for blood or donors (see Safety).
- Mobile or web app.

---

## 5. Primary user flow (the demo)
1. **Intent**: User says *"Need 2 units of O+ at SMS Hospital, Jaipur, urgent."*
2. **Parse and clarify**: The agent extracts blood type, units, urgency and hospital. If one field is missing or ambiguous, it asks a single follow-up.
3. **Inventory check**: The Inventory Agent finds nearby hospitals and blood banks and returns stock with a "last updated" time.
4. **Donor match**: The Donor Agent ranks eligible, available donors by distance and reliability.
5. **Review**: A donor carousel card shows matches with verification badge, distance and availability.
6. **Confirm**: A request review card lets the user edit and confirm before anything is sent.
7. **Broadcast**: Alerts go out in waves (nearest first).
8. **Track**: A status card updates as donors accept or decline. Masked contact unlocks only for donors who accepted.
9. **Summary**: The agent posts who is coming, ETA, and the backup blood banks.

---

## 6. Functional requirements
*Priority: P0 must ship, P1 should ship, P2 if time remains.*

### 6.1 Intent understanding
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F1 | Extract blood type, units, urgency, hospital/location from free text | P0 |
| F2 | Validate blood type (A/B/AB/O, +/-) and units (1 to 10) | P0 |
| F3 | Ask at most one clarifying question at a time | P0 |
| F4 | Accept Hindi and English input; reply in the user's language | P1 |

### 6.2 Inventory
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F5 | Geocode the location and find hospitals/blood banks within a radius (live OpenStreetMap data) | P0 |
| F6 | Show stock by blood type with "last updated" timestamp, clearly labelled demo data | P0 |
| F7 | Expand the radius automatically if results are few | P1 |

### 6.3 Donor matching
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F8 | Filter donors by blood-type compatibility, availability and donation-interval eligibility (enforced in code) | P0 |
| F9 | Rank by distance, reliability score and availability | P0 |
| F10 | Verification tiers shown as badges (phone, ID, blood-bank confirmed) | P1 |

### 6.4 Alerts and tracking
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F11 | Broadcast in waves with a per-donor cap | P0 |
| F12 | Simulated donor replies, with an optional Telegram bot for a live accept on stage | P0 / P1 |
| F13 | Status updates streamed to the conversation | P0 |
| F14 | Masked contact released only after a donor accepts that specific request | P0 |

### 6.5 Interactive cards
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F15 | Donor carousel card | P1 |
| F16 | Request review/confirm form card | P1 |
| F17 | Live status card | P1 |
| F18 | Text-only fallback for every card | P0 |

### 6.6 Reliability
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F19 | Retry with backoff on external APIs; cached fallback for the demo city | P0 |
| F20 | Timeouts on agent-to-agent calls; friendly degraded response on failure | P0 |

### 6.7 Stretch
| ID | Requirement | Priority |
| :--- | :--- | :--- |
| F21 | Payment Protocol: hospital/NGO-side fee or optional NGO donation, never for blood | P2 |
| F22 | Donation scheduling and history, badges, analytics view | P2 |

---

## 7. Multi-agent architecture
| Agent | Role |
| :--- | :--- |
| **Coordinator** | The only agent exposed to ASI:One. Implements ACP, parses intent, plans, renders cards, orchestrates the others |
| **Inventory** | Geocoding, nearby facilities, stock lookup |
| **Donor Match and Outreach** | Eligibility, ranking, alert waves, accept handling |

The Coordinator calls the other two through agent-to-agent messages so orchestration is visible in the demo.

---

## 8. Safety, privacy and ethics
- **No payment for blood or donors**: Paid donation is illegal in India. Any monetization targets hospitals or NGOs for the service only.
- **Rule-based eligibility**: Eligibility is rule-based code, never decided by the LLM.
- **Masked contact details**: Contact details are never shown until the donor accepts, and are masked even then.
- **Demo data only**: Synthetic, labelled donors. No real personal data is used.
- **Medical disclaimer**: The agent connects people to licensed blood banks and does not give medical advice. For a real emergency it tells the user to contact the hospital directly.
- **Abuse controls**: OTP, rate limits, report/block.

---

## 9. Success metrics
- Full workflow completes in one ASI:One chat in under 2 minutes.
- Agent is found by a plain-language search in ASI:One.
- No unhandled errors in the demo run, including one deliberate tool failure.
