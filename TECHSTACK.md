# LifeLink: Tech Stack
**ASI:One Agent Challenge, one-day build**

---

## 1. Stack at a glance
| Layer | Choice | Why |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Best support for uAgents and fastest to build |
| **Agent framework** | uAgents (Fetch.ai) | Native Agentverse registration and Agent Chat Protocol support |
| **Agent hosting** | Local with mailbox, then Agentverse hosted if time allows | Mailbox is the quickest way to be reachable from ASI:One |
| **User interface** | ASI:One chat + ASI1 Interactive Cards | Required by the challenge; no custom frontend |
| **LLM** | ASI:One API (ASI1) or Claude API or OpenAI-compatible, via one `llm.py` wrapper | Intent parsing and reply writing only |
| **Geocoding** | Nominatim (OpenStreetMap) | Free, no key |
| **Nearby facilities** | Overpass API (OSM) | Real live data, no key |
| **Storage** | SQLite (file) + in-memory dict | Zero setup, enough for a demo |
| **Validation** | Pydantic | Strict models for blood type, units, messages |
| **HTTP** | httpx (async) + tenacity | Async calls with retry and backoff |
| **Live accept (optional)** | Telegram Bot API (`python-telegram-bot`) | A teammate can accept live on stage |
| **Tests** | pytest | Eligibility, ranking and parsing tests |
| **Repo** | GitHub (public) with README | Required for submission |

---

## 2. Agents
| Agent | Responsibility | Exposed to ASI:One? |
| :--- | :--- | :--- |
| **coordinator** | ACP handler, intent parsing, planning, card rendering, orchestration | Yes |
| **inventory** | Geocode, find facilities, return stock + last-updated | No (agent-to-agent only) |
| **donor_outreach** | Eligibility, ranking, alert waves, accept handling, masked contact | No (agent-to-agent only) |

Communication: typed `uagents.Model` messages with timeouts, so a failed downstream call degrades the reply instead of crashing the chat.

---

## 3. Agent Chat Protocol (ACP)
- Import chat protocol from the uAgents core package or define standard ACP models (`ChatMessage`, `ChatAcknowledgement`, etc.) on the Coordinator.
- Handle `ChatMessage` and always send a `ChatAcknowledgement` back.
- Reply with `ChatMessage` containing text content, plus card payloads when supported.
- Create the agent with `mailbox=True` and connect it through the Agentverse inspector link printed at startup.
- Agent profile metadata: "blood donor", "emergency", "O+", "India" so ASI:One can discover it.

---

## 4. ASI1 Interactive Cards
- **Carousel**: Ranked donors with badge, distance, availability
- **Form / review**: Confirm blood type, units, hospital, urgency before broadcast
- **Status / detail**: Live accept/decline tracker and final summary
- Build text-first, then add cards. Every card must have a plain-text fallback.

---

## 5. External data and tools
- **Geocode**: Nominatim `/search` with User-Agent and rate limiting.
- **Facilities**: Overpass query for `amenity=hospital`, `healthcare=blood_donation`, `amenity=clinic`. Cache results for demo city (`Jaipur, Rajasthan, India`).
- **Distance**: Haversine formula in Python.
- **Stock levels**: Mock JSON/SQLite, labelled demo data.
- **Donors**: Synthetic JSON, labelled demo data (never use real people's data).

---

## 6. Core logic (deterministic, not LLM)
- **Blood compatibility**: Lookup table (e.g. O+ donors can give to O+, A+, B+, AB+; request of O+ resolves to compatible donor types O- and O+).
- **Eligibility**: Minimum donation interval (90 days for men, 120 days for women per NBTC India guidance), age 18-65, "available now" flag.
- **Ranking score**: Weighted formula `(w_dist * norm_distance) + (w_avail * avail_score) + (w_rel * reliability) + (w_ver * verif_tier)`.
- **Alert waves**: Nearest N donors first, timeout/widen, daily cap per donor.
- **Privacy gate**: Contact details returned only after an accept event, and masked relay-style.

---

## 7. Reliability and error handling
- Retry with exponential backoff on Nominatim and Overpass (`tenacity`).
- Cached fallback data for the demo city if an API fails.
- Timeouts on agent-to-agent messages and a degraded text reply on failure.
- Pydantic validation of all inputs, including blood type and units.
- Structured logging with request IDs.
- A pre-recorded backup run of the full workflow.
