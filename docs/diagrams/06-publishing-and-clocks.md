# 06 — Publishing Schedule & The Four Clocks

This document visualizes how Atlas schedules content releases across global audiences without ever conflating operator local time with audience prime time (ADR-0007).

---

## 1. The Four Clocks (Never Conflated)

```
+---------------------------------------------------------------------------------------+
|                                    THE FOUR CLOCKS                                    |
+---------------------------------------------------------------------------------------+

1. UTC CLOCK (System Truth)
   * Governs every stored database timestamp (`created_at`, `retrieved_at`, etc.).
   * No naive datetime is ever allowed.

2. OPERATOR CLOCK (Asia/Kathmandu, UTC+05:45, No DST)
   * Governs dashboard UI display, operator approval reminders, and quiet hours.
   * NEVER used to compute publish slots!

3. AUDIENCE CLOCK (Per Channel, e.g. America/New_York, Europe/London)
   * The ONLY clock used to evaluate publishing windows and audience prime time.
   * Evaluated with real IANA tz database at calculation time (handles DST).

4. PROVIDER RESET CLOCK (Per Provider Quota Window)
   * Governs daily quota reset boundaries for Google Gemini, Ollama, etc.
```

---

## 2. Publishing Slot Allocation Workflow

```
[ Target: 3 Published Videos Daily for Channel ORIGINS ]
                         |
                         v
+-------------------------------------------------------------+
| 1. Look up Channel Audience Timezone:                       |
|    Channel "origins" -> "America/New_York" (US Eastern)     |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| 2. Fetch Ranked Publishing Windows (Priors as Data):        |
|    - YouTube: Sun / Thu 09:00 - 11:00 (Rank 1)              |
|    - TikTok:  Tue - Thu 09:00 - 12:00 & 14:00 - 17:00       |
|    - Instagram: Tue - Thu 11:00 - 13:00                     |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| 3. Evaluate Enforced Blackout Rules:                        |
|    Rule: No publish between 22:00 and 06:00 audience-local! |
|    * HARD GATE: Violations raise BlackoutViolationError     |
+------------------------------+------------------------------+
                               |
                               | Assigns 3 distinct spaced slots
                               v
+---------------------------------------------------------------------------------------+
| 4. Compute Concrete Publish Slots (Audience-Local -> Converted to UTC Instants):      |
|                                                                                       |
|  Slot A (Morning Peak):                                                               |
|   * Audience Local: Tuesday 10:00 EDT (New York)                                      |
|   * UTC Instant:    Tuesday 14:00 UTC (Stored in DB)                                  |
|   * Operator Local: Tuesday 19:45 Kathmandu (Comfortable evening approval)            |
|                                                                                       |
|  Slot B (Afternoon Peak):                                                             |
|   * Audience Local: Tuesday 15:00 EDT (New York)                                      |
|   * UTC Instant:    Tuesday 19:00 UTC (Stored in DB)                                  |
|   * Operator Local: Wednesday 00:45 Kathmandu (Handled via automated queue)           |
+---------------------------------------------------------------------------------------+
```

---

## 3. Why the Operator Clock is Never the Publishing Clock

```
  If published at 10:00 Operator Local (Kathmandu, UTC+05:45):
  -------------------------------------------------------------
  -> UTC Time:             04:15 UTC
  -> US Eastern Time:      00:15 EDT (Midnight / Deep Sleep!)   <-- VIOLATES BLACKOUT
  -> London Time:          05:15 BST (Early Dawn / Low Reach!)  <-- VIOLATES BLACKOUT

  If published at 14:00 UTC (10:00 US Eastern / 15:00 London):
  -------------------------------------------------------------
  -> US Eastern Time:      10:00 EDT (Prime Morning Discovery!)
  -> London Time:          15:00 BST (Prime Afternoon Peak!)
  -> Operator Local:       19:45 Kathmandu (Evening review)
```
