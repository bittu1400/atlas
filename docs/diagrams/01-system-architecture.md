# 01 — System Architecture & Clean Layering

This document visualizes the complete system architecture of Atlas, demonstrating the strict Clean Architecture dependency boundaries, ports, adapters, and data flows.

---

## 1. System Layer Diagram

```
+---------------------------------------------------------------------------------------+
|                                  OPERATOR SURFACES                                    |
|                                                                                       |
|      +------------------------------+             +-------------------------------+   |
|      |    React 19 Web Dashboard    |             |           Typer CLI           |   |
|      | (Keyboard review & approvals)|             |      (Full parity with UI)    |   |
|      +--------------+---------------+             +---------------+---------------+   |
+---------------------|---------------------------------------------|-------------------+
                      |                                             |
                      | HTTP (polling)                              | CLI Invocation
                      v                                             v
+---------------------------------------------------------------------------------------+
|                              LAYER 4: ENTRYPOINTS                                     |
|                                                                                       |
|   +-------------------------------------+     +-----------------------------------+   |
|   |             FastAPI App             |     |          Dramatiq Worker          |   |
|   |  - Route parsing & serialization    |     |  - Async pipeline step execution  |   |
|   |  - Enqueues jobs to Postgres queue  |     |  - Acquires shared GPU semaphore  |   |
|   |  - 11 routes; see ARCHITECTURE 2.1  |     |  - Checkpoints step output rows   |   |
|   +------------------+------------------+     +-----------------+-----------------+   |
+----------------------|------------------------------------------|---------------------+
                       |                                          |
                       | Calls Use Cases                          | Executes Steps
                       v                                          v
+---------------------------------------------------------------------------------------+
|                         LAYER 3: APPLICATION USE CASES & PORTS                        |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   | Use Cases (One file per use case):                                            |   |
|   |  - CreateRunUseCase            - ApproveGateUseCase       - ReviseKOUseCase   |   |
|   |  - ExtractClaimsUseCase        - SchedulePublishSlot      - MeterQuotaUseCase |   |
|   +---------------------------------------+---------------------------------------+   |
|                                           |                                           |
|   +---------------------------------------v---------------------------------------+   |
|   | Application Ports (Abstract Protocols):                                       |   |
|   |  - Storage Port                - Llm / StructuredLlm Port - Search Port       |   |
|   |  - SourceFetcher Port          - Renderer Port            - SoundLibrary Port |   |
|   +-------------------------------------------------------------------------------+   |
+-------------------------------------------|-------------------------------------------+
                                            |
                     +----------------------+----------------------+
                     |                                             |
                     | Implements Ports                            | Pure Dependency
                     v                                             v
+--------------------------------------------+    +-------------------------------------+
|            LAYER 2: ADAPTERS               |    |           LAYER 1: DOMAIN           |
|                                            |    |                                     |
|  +---------------------------------------+ |    |  +--------------------------------+ |
|  | Persistence (SQLAlchemy 2.0 Repos):   | |    |  | Knowledge Core:                | |
|  |  - KnowledgeRepository                | |    |  |  - KnowledgeObjectVersion      | |
|  |  - SourceRepository                   | |    |  |  - Claim (+ append-only         | |
|  |  - FocusRepository                    | |    |  |    ClaimVersion), Evidence,    | |
|  |  - ExecutionRepository                | |    |  |    Source, Snapshot, ClaimUsage| |
|  |  - PublishingRepository               | |    |  |  - Upcast-on-read pure fns     | |
|  |  - ProductionRepository (ADR-0016)    | |    |  +--------------------------------+ |
|  +---------------------------------------+ |    |                                     |
|                                            |    |  +--------------------------------+ |
|  +---------------------------------------+ |    |  | Focus & Scoping:               | |
|  | Storage Adapters:                     | |    |  |  - Focus, Facet, Domain        | |
|  |  - LocalStorage (SHA-256 tree)        | |    |  |  - Entity (Wikidata QID)       | |
|  +---------------------------------------+ |    |  |  - ScopeMode (soft/hard/exp)   | |
|                                            |    |  +--------------------------------+ |
|  +---------------------------------------+ |    |                                     |
|  | External Providers (Tier 0 / 1 / 2):  | |    |  +--------------------------------+ |
|  |  - GeminiLlm (Tier 2 Frontier)        | |    |  | Execution State Machine:       | |
|  |  - OllamaLlm (Tier 1 — unwired, T-30) | |    |  |  - Run, Step, Gate, Approval   | |
|  |  - WikipediaSearch, HttpSourceFetcher | |    |  |  - ResourceLock, QuotaLedger   | |
|  |  - StubRenderer  (no Remotion yet)    | |    |  |  - PipelineStage (18 stages)   | |
|  |  - StubPublisher (publishes nothing)  | |    |  +--------------------------------+ |
|  +---------------------------------------+ |    |                                     |
+---------------------+----------------------+    +-------------------------------------+
                      |
                      v
+---------------------------------------------------------------------------------------+
|                              INFRASTRUCTURE & PERSISTENCE                             |
|                                                                                       |
|   +------------------------------------+      +-----------------------------------+   |
|   |       PostgreSQL Database          |      |         Filesystem Storage        |   |
|   |  - 30 Relational Schema Tables     |      |  - Content-addressed Blobs:       |   |
|   |  - Row-per-version KO history      |      |    var/blobs/sha256/ab/cd/<hash>  |   |
|   |  - Foreign-key Traceability Chain  |      |  - Source Snapshots:              |   |
|   |  - Append-only Quota Ledger        |      |    var/snapshots/...              |   |
|   +------------------------------------+      +-----------------------------------+   |
+---------------------------------------------------------------------------------------+
```

---

## 2. Invariant: Import Direction Rules

The Clean Architecture enforces that dependencies point **inward only**:

```
[Entrypoints]  --->  [Adapters]  --->  [Application]  --->  [Domain]
   (API/CLI)         (SQL/DB)          (Use Cases)          (Pure Models)
```

* **`domain/`** imports **nothing** from Atlas outside itself and **zero** external I/O libraries (`sqlalchemy`, `httpx`, `asyncpg`, `pydantic-settings`).
* **`application/`** imports only from `domain/`.
* **`adapters/`** imports from `application/` (to implement ports) and `domain/`.
* **`entrypoints/`** imports from `application/` and wires dependencies.
