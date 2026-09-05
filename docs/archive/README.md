# Archive

Superseded documents, kept because rule **R11** forbids deleting the evidence of a failure.

**Nothing in this directory is a current claim.** Every file here was true-sounding and wrong, and it
is retained so the record of *how* it was wrong survives. If you need to know what is true now, read
[`docs/STATUS.md`](../STATUS.md).

| File | What it was | Why it is here |
|---|---|---|
| [`audit-2026-08-20-gpt.md`](audit-2026-08-20-gpt.md) | An independent audit dated 2026-08-20, written to the **repository root** as `gpt-audit.md` | Moved here 2026-08-31 (**D123**). It sat at the root, referenced by no document and listed in no read order, next to `CLAUDE.md` and `prompt.md` — so it read as current when its metrics ("33 passed", "52 source files") describe a tree three phases old. Its Phase 2 findings were addressed by ADR-0008. |
| [`review-2026-08-24-ox-alpha.md`](review-2026-08-24-ox-alpha.md) | An independent read-only review dated 2026-08-24, written to the repository root as `ox-alpha-analysis.md` | Moved here 2026-08-31 (**D123**). Same reason. Superseded by [`../AUDIT-2026-08-29.md`](../AUDIT-2026-08-29.md), which covers the same ground after the fabrication incident. |
| [`STATUS-2026-08-29.md`](STATUS-2026-08-29.md) | The body of `docs/STATUS.md` as it stood at the end of the 2026-08-29 Stage C remediation session | Superseded by the 2026-08-31 rewrite (task **T-31**, decisions **D100**, **D103**). Its Phase 5, 6 and 7 completion statements are false, its metrics were carried forward rather than measured, and its phase numbering predates the adoption of SPEC §15. It lives here rather than at the bottom of `STATUS.md` because the honesty guard (`test_status_honesty_check`) reads that file line by line and cannot tell a quoted false metric from a live one. |

Two other retained records are **not** in this directory, because other documents link to them by
path and moving them would break those links:

- [`../phase-7-execution.md`](../phase-7-execution.md) — the fabricated Phase 7 report. Retracted in
  place with a banner at the top. Do not cite it.
- [`../audit-2026-08-20.md`](../audit-2026-08-20.md), `-second`, `-third`, and
  [`../audit-phase-3-1.md`](../audit-phase-3-1.md) — earlier audits, superseded by
  [`../AUDIT-2026-08-29.md`](../AUDIT-2026-08-29.md).
