# 05 — Focus Model & Research Scoping Flow

This document visualizes how the operator's two-input interface (**Field** + **Note**) translates into deep research constraints, Wikidata entity anchoring, and by-value immutable run scoping (ADR-0002).

---

## 1. Focus Disambiguation & Entity Resolution

```
               OPERATOR INPUTS (UI)
        +-----------------------------------+
        | Field:  [ Animal            v ]   |
        | Note:   [ tiger               ]   |
        +-----------------+-----------------+
                          |
                          v
+-------------------------------------------------------------+
| 1. Field maps to Domain: "dom_animal"                       |
|    Carries Research Profile:                                |
|    - Preferred APIs: OpenAlex, Crossref, IUCN RedList       |
|    - Source Allowlist: *.nature.com, *.sciencemag.org       |
|    - Source Tier Floor: PEER_REVIEWED                       |
|    - Disambiguation Hints: "taxonomic classification"       |
+------------------------------+------------------------------+
                               |
                               | Disambiguates "tiger"
                               v
+-------------------------------------------------------------+
| 2. Resolves against Wikidata:                               |
|    "tiger" in Animal Domain -> Q19939 (Panthera tigris)     |
|    (Distinguished from Tiger Woods, Tiger tank, Tiger OS)   |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| 3. Creates Focus Entity (Immutable Record):                 |
|    - id: "foc_tiger_2026"                                   |
|    - name: "Panthera Tigris in Pleistocene Asia"            |
|    - scope_mode: SOFT (default: allows adjacent predators)  |
|    - facets: [                                              |
|        { dimension: "domain",  value: "dom_animal" },       |
|        { dimension: "subject", value: "tiger" },            |
|        { dimension: "entity",  value: "Q19939" }            |
|      ]                                                      |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| 4. Updates Active Focus Pointer (Singleton):                |
|    active_focus -> "foc_tiger_2026"                         |
|    * Newly launched Runs will use this Focus by default!    |
+-------------------------------------------------------------+
```

---

## 2. Capture By-Value: Invariant 10

When a Run is created, its Focus is **captured by value into the run record**. Modifying or updating the active focus pointer later **never** changes the scope of in-flight or past runs:

```
[ Operator sets Active Focus to "Tigers" (foc_01) ]
                        |
                        | Operator starts Run 1
                        v
          +-----------------------------+
          | Run 1 created               |
          | captured_focus = {          |
          |   focus_id: "foc_01",       |
          |   subject: "tiger",         |
          |   scope_mode: "soft"        |
          | }                           |
          +-----------------------------+
                        |
[ Operator changes Active Focus to "Black Holes" (foc_02) ]
                        |
                        | Operator starts Run 2
                        v
          +-----------------------------+
          | Run 2 created               |
          | captured_focus = {          |
          |   focus_id: "foc_02",       |
          |   subject: "black hole",    |
          |   scope_mode: "hard"        |
          | }                           |
          +-----------------------------+

* Run 1 continues researching Tigers with 100% isolation!
* Re-reading scope 6 months later reports the exact parameters used.
```
