# Status

**Last updated:** 2026-08-20

This file exists to separate **decided** from **done**. Everything else in `docs/` records what Atlas
*will* be; this records where it actually stands. Update it at the end of every working session.

---

## 1. Where we are

**Phase 1 (Architecture) is complete.**
**Phase 2 (Database & Persistence) is complete.**
- Python 3.13 pinned via `uv`, `pyproject.toml`, strict `mypy`, `ruff`, and `pytest`.
- Database schema and Alembic migrations (`0001_initial_schema`) establishing 26 tables in PostgreSQL.
- Knowledge Object row-per-version with current pointer, typed core, versioned JSONB payload, and pure upcast-on-read mechanism (ADR-0003).
- Full normalized foreign-key traceability: Assertion → Claim → Evidence → Source → Snapshot (content-addressed SHA-256).
- Reverse Claim Impact Index (`claim_usages`) for retractions.
- Pipeline execution state machine tables: Runs (capturing Focus by value), Steps (idempotency keys + checkpointing), Gates (suspension rows), Approvals (structured rejection feedback), Resource Locks (GPU lease semaphore), Model Calls audit, and Quota Ledger.
- Publishing schedule and timezone schema seam (ADR-0007): Channels with audience timezone, seeded publishing windows with confidence and provenance, and enforced blackout rules.
- LocalStorage content-addressed blob adapter (`var/blobs/sha256/ab/cd/<hash>`).
- 25 unit and integration tests passing in ~1.1s against live PostgreSQL.

**Phase 3 (Backend) is next.** Acceptance criterion: A Run traverses every stage with fake providers,
suspends at a gate, and resumes via API and CLI. Scope includes FastAPI routes, Dramatiq worker task
definitions, the Run/Step state machine driver, gate suspension/resumption handlers, and quota token buckets.

---

## 2. What exists

```
pyproject.toml       packages/atlas/src/atlas/domain/       tests/unit/
alembic.ini          packages/atlas/src/atlas/adapters/     tests/integration/
README.md            packages/atlas/src/atlas/platform/     docs/SPEC.md
CLAUDE.md            packages/atlas/src/atlas/application/  docs/ARCHITECTURE.md
docs/STATUS.md       docs/DECISIONS.md                      docs/GLOSSARY.md
docs/adr/            prompt.md                              var/
```

Git: `main`, remote `origin` at `https://github.com/bittu1400/atlas.git`, local only until pushed.

---

## 3. Verified environment

Probed 2026-07-30 on the development machine. **Re-verify rather than trust** — this is a snapshot.

| Component | State | Consequence |
|---|---|---|
| OS | Arch Linux, kernel 7.1.5 | — |
| GPU | RTX 5070 Laptop, 8151 MiB VRAM, driver 610.43 | Blackwell. Local Stable Diffusion needs a CUDA 12.8+ PyTorch build. 8 GB cannot host an LLM and an image model at once — hence the GPU lease in ADR-0001 |
| System Python | **3.14.6** | Ahead of much of the ML wheel ecosystem. **This is why D34 pins 3.13 via `uv`** — do not build against system Python |
| `uv` | installed | Will manage the pinned 3.13 interpreter |
| Node | **v26.5.0** | Ahead of Remotion's tested range; pin an LTS via `.nvmrc` before Phase 7 |
| `pnpm` | **not installed** | Required by D35 before any frontend or renderer work |
| Ollama | installed, **no models pulled** | See actions below |
| Docker | installed | Compose stack not yet written |
| FFmpeg | installed | — |
| Timezone | `Asia/Kathmandu`, UTC+05:45, no DST | This is the **operator** clock only. Never the publishing clock — see ADR-0007 |

---

## 4. Operator actions outstanding

Work only the operator can do. None of it blocks Phase 2.

| Action | Needed by | Notes |
|---|---|---|
| Obtain a **Google AI Studio API key** | Phase 5 | Separate product from a Gemini Advanced subscription, which grants no API access — see ADR-0004 context. Free tier |
| **Verify current free-tier limits** against live provider docs | Phase 5 | The quota budget in SPEC §11 is an estimate and must not be fixed until confirmed |
| `ollama pull qwen3:8b` and `ollama pull nomic-embed-text` | Phase 5 | Tier 1 models; both fit in 8 GB together |
| Install `pnpm`, pin Node LTS | Phase 4 | |
| Confirm the GitHub repo's **visibility** | now | The pushed commit contains the full product strategy and all ADRs |
| Delete the orphaned remote `master` branch if it exists, set `main` as default | now | Artifact of the local rename |
| Decide **backup and restore** (Postgres PITR + portable export bundle) | before first publication | Knowledge is the product and it is irreplaceable |

---

## 5. Open questions

Recorded in SPEC §16. Repeated here with the phase that forces the answer.

| Question | Needed by |
|---|---|
| ORIGINS **audience region** — sets the Channel's audience timezone | Phase 8 |
| Retention policy for snapshots and superseded renders | ~month 6 |
| Novelty threshold — cannot be set until a corpus exists | Phase 6 |
| Quality threshold of 78 — provisional until judge calibration | Phase 5 |
| Backup and restore approach | before first publication |

---

## 6. Known risks being carried deliberately

- **Remotion's commercial license ceiling.** Free for solo use, paid above a small team. The only
  dependency in the stack with this property. Exit path documented in ADR-0005; review before any team
  growth.
- **Free-tier dependency.** Limits and terms can change without notice. Provider independence is not a
  principle here, it is the continuity plan.
- **Hand-rolled durability primitives.** Retry, backoff, lease expiry, and stuck-run detection are ours to
  get right instead of Temporal's. ADR-0001 lists the triggers that should force the migration.
- **Quality priors are unvalidated.** The 78 threshold, the rubric weights, the pacing constants, and the
  seeded publishing windows are all reasoned starting points with no measured data behind them yet.
- **Storage grows monotonically** by design, ~500 MB per video. Retention policy required by month six.

---

## 7. Session log

| Date | Outcome |
|---|---|
| 2026-07-30 | Phase 1 completed. Vision reviewed against 38 identified gaps; D1–D38 settled; ADRs 0001–0007 written. Format changed from narrated 8-minute to 60-second text-and-sound-design. Budget fixed at zero. First channel changed from WHY to ORIGINS on archival imagery supply. Repo initialized, `main` pushed to GitHub. |
| 2026-08-20 | Phase 2 completed. Python 3.13 project initialized with `uv`. Alembic migrations established 26 normalized PostgreSQL tables with foreign-key traceability. Row-per-version KO mechanics, JSONB upcast-on-read, Focus-by-value capture in Runs, GPU resource locks, quota ledger, and ADR-0007 publishing schedule seam implemented with 25 passing unit/integration tests. |
