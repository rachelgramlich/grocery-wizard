# Load-time performance report

**Scope:** Streamlit UI + Notion I/O (October 2026 load-time optimization pass).  
**Related:** early research in [`docs/ui-performance-research.md`](ui-performance-research.md) ([#128](https://github.com/rachelgramlich/grocery-wizard/issues/128)); repeatable measurement in [`docs/performance-audit.md`](performance-audit.md) and `/performance-audit`.

This page is the **architecture-facing summary**: what was slow, what we changed, the **post-fix baseline**, and how to re-measure. It does not duplicate the harness playbook (flags, tap, adding scenarios) — that stays in [`docs/performance-audit.md`](performance-audit.md).

---

## How the app spends time

Streamlit reruns the active page script on every interaction. Cost comes from:

1. **Notion HTTP** — recipe pagination, pantry rows, saved plans, view ensure/patch, writes.
2. **Python CPU** — ingredient parsing (CRF), index builds, widget serialization.
3. **DOM weight** — large `selectbox` option lists sent every rerun (including closed popovers unless gated).

The app keeps hot data in `ui/notion_cache.py` (`st.cache_data` / `st.cache_resource`), runs **one** nav section per rerun (`st.segmented_control`), and splits weekly flow under `ui/views/weekly_plan/`. See the diagram and call-site table in [`docs/ui-performance-research.md`](ui-performance-research.md).

Control IDs and pages follow [`docs/ui-map.md`](ui-map.md).

---

## Measurement harness

| What | Where |
| --- | --- |
| Run full audit | `just performance-audit --profile` |
| List scenarios | `just performance-audit --list` |
| Compare to baseline | `just performance-audit --only 'weekly.*' --reps 3 --compare latest` |
| CI-style gate | `just performance-audit --fail-over 5` |
| Reports | `.local/grocery_wizard/perf/perf-<stamp>.md` and `latest.json` |

Headless **AppTest** against live Notion: reads are real; writes are stubbed and charged at 0.4s each in **Warm est** columns. No browser paint or websocket time — spot-check top rows with `just grocery-ui` when UX matters.

---

## Budgets (“fast enough”)

Warm interaction budgets and the full flag glossary live in [`docs/performance-audit.md`](performance-audit.md#budgets-what-fast-enough-means). **Severity flags (warm wall time):** P0 ≥ 5s, P1 ≥ 2s, P2 ≥ 1s (estimated write cost included in **Warm est** when writes are stubbed).

---

## Work shipped (issues #406–#411, PRs #405–#420)

Audit-driven fixes merged on `main` in October 2026. Before numbers come from the **pre-fix performance-audit baseline** recorded in each GitHub issue; after numbers from the **full re-audit** at commit [`4fbc95b`](https://github.com/rachelgramlich/grocery-wizard/commit/4fbc95b) (309 recipes, 66 pantry items, 6 saved plans), plus follow-ups [#417](https://github.com/rachelgramlich/grocery-wizard/pull/417), [#418](https://github.com/rachelgramlich/grocery-wizard/pull/418), [#420](https://github.com/rachelgramlich/grocery-wizard/pull/420).

| Issue | Problem | Before (typical warm) | After (warm / notes) | PR |
| --- | --- | --- | --- | --- |
| [#406](https://github.com/rachelgramlich/grocery-wizard/issues/406) | Ingredient index rebuilt on cold picker open | cold count_continue ~14s (4fbc95b audit); warm ~0.01s | Background warm during meal-count step; prebuild pin ~0.01s warm / ~1.1s cold | [#420](https://github.com/rachelgramlich/grocery-wizard/pull/420) |
| [#407](https://github.com/rachelgramlich/grocery-wizard/issues/407) | Meals step re-queried Notion every rerun | 1.5–3s, 7–15 reads | ≤ 0.02s, 0 reads on idle / build / continue | [#412](https://github.com/rachelgramlich/grocery-wizard/pull/412) |
| [#408](https://github.com/rachelgramlich/grocery-wizard/issues/408) | Closed popovers still built ~300-option pickers | ~3,244 select options | 46 elements / 4 options on meals scenarios | [#412](https://github.com/rachelgramlich/grocery-wizard/pull/412) |
| [#409](https://github.com/rachelgramlich/grocery-wizard/issues/409) | Any write cleared all caches → full recipe refetch | 3–6s after pantry swap / regenerate | Writes mostly ≤ 0.8s wall; recipe list kept on pantry writes | [#415](https://github.com/rachelgramlich/grocery-wizard/pull/415), [#414](https://github.com/rachelgramlich/grocery-wizard/pull/414) |
| [#410](https://github.com/rachelgramlich/grocery-wizard/issues/410) | Pantry page rebuilt DB + queried every render | ~0.7s page open, 3 reads | 0.03s page, 0.01s search, 0 reads | [#414](https://github.com/rachelgramlich/grocery-wizard/pull/414) |
| [#411](https://github.com/rachelgramlich/grocery-wizard/issues/411) | Maintenance re-PATCHed Notion views every render | 3–4s, ~19 Notion calls | 0.01s page switch warm; apply status 0.17s wall | [#413](https://github.com/rachelgramlich/grocery-wizard/pull/413) |
| — | Saved-plan picker re-queried recipes | extra recipe query on continue | reuses loaded recipe cache | [#417](https://github.com/rachelgramlich/grocery-wizard/pull/417) |
| — | Refresh payload size | ~3.35s warm refresh (4fbc95b) | `filter_properties` on recipe queries; ~1.75s warm ([#420](https://github.com/rachelgramlich/grocery-wizard/pull/420)) | [#420](https://github.com/rachelgramlich/grocery-wizard/pull/420) |

Harness and docs: [#405](https://github.com/rachelgramlich/grocery-wizard/pull/405) introduced `src/grocery_wizard/dev/perf_audit/`; [#416](https://github.com/rachelgramlich/grocery-wizard/pull/416) logs Notion caller stacks; [#418](https://github.com/rachelgramlich/grocery-wizard/pull/418) added this report and renamed user-facing **`performance-audit`** (see [`docs/performance-audit.md`](performance-audit.md)).

---

## Post-optimization baseline (ranked slowest warm)

Full audit: **2026-10-17**, commit `4fbc95b`, 36 measured scenarios (5 dev-jump controls listed as coverage gaps). **Warm** = caches primed, fresh session; **Warm est** adds 0.4s per stubbed write.

| Rank | Scenario | Warm est (s) | Warm (s) | Flags |
| ---: | --- | ---: | ---: | --- |
| 1 | `global.refresh` — Refresh from Notion | 3.35 | 3.35 | P1, READ_FANOUT |
| 2 | `weekly.meals.regenerate_all` | 2.21 | 0.21 | P1, POST_WRITE_REFETCH, WRITE_FANOUT |
| 3 | `maintenance.apply_status` | 1.37 | 0.17 | P2, POST_WRITE_REFETCH |
| 4 | `pantry.remove_item` | 1.16 | 0.76 | P2, POST_WRITE_REFETCH |
| 5 | `pantry.add_item` | 1.15 | 0.75 | P2, POST_WRITE_REFETCH |
| 6 | `pantry.remove_recurring` | 1.15 | 0.75 | P2, POST_WRITE_REFETCH |
| 7 | `pantry.add_recurring` | 1.08 | 0.68 | P2, POST_WRITE_REFETCH |
| 8 | `global.page_switch.maintenance` | 0.81 | 0.01 | (cold gap only) |
| 9 | `maintenance.pick_recipe` | 0.81 | 0.01 | (cold gap only) |
| 10 | `add.manual.save` | 0.71 | 0.31 | POST_WRITE_REFETCH |

**Healthy weekly flow (warm, 0 Notion reads):** app load 0.07s; continue saved plan 0.02s; build plan 0.02s; build final grocery list 0.07s; idle reruns ≤ 0.03s.

**Interpretation:**

- **Refresh from Notion** is intentionally heavy (full invalidation + refetch). After [#420](https://github.com/rachelgramlich/grocery-wizard/pull/420) it is ~1.75s warm with `filter_properties`; the table above still reflects the pre-#420 `4fbc95b` snapshot until the next full audit.
- **Write + refetch** (`POST_WRITE_REFETCH`) remains on pantry edits and meal regeneration; wall times are much lower than pre-#409 but still P2 when write latency is included.
- **`add.url.duplicate`** still does one warm Notion read (`CACHE_MISS_WARM`) — candidate for filter-based lookup without full scan.
- Many scenarios show **COLD_GAP** only: first load after cache clear is slower; warm path is fine.

Re-run after changes:

```bash
just performance-audit --profile --reps 3
# or targeted:
just performance-audit --only 'global.refresh' --only 'weekly.meals.*' --reps 3 --compare latest
```

Update this section when a new full audit becomes the team baseline (paste the top of the generated `.md` report and adjust the fixes table if issue numbers change).

---

## Fix patterns (quick reference)

| Symptom | Pattern |
| --- | --- |
| Notion reads on warm idle rerun | Route through `notion_cache.py`; `@st.cache_resource` for DB clients |
| Spike after small write | Targeted `cache_data.clear()` or in-place cache update, not global invalidation |
| Huge select option counts | Gate popover/expander bodies until open; `@st.fragment` for local reruns |
| View ensure on every render | Memoize ensured URLs per process (`notion_views.py`) |
| CPU on meal open | Background warm during meal-count step; memoized parse ([#406](https://github.com/rachelgramlich/grocery-wizard/issues/406) / [#420](https://github.com/rachelgramlich/grocery-wizard/pull/420)) |

Full flag → playbook table: [`docs/performance-audit.md`](performance-audit.md#fix-playbook-flag---cause---pattern).

---

## See also

- [`docs/performance-audit.md`](performance-audit.md) — harness, flags, scenarios, limitations  
- [`docs/ui-performance-research.md`](ui-performance-research.md) — pre-audit research and phased roadmap  
- [`docs/weekly-flow-ui.md`](weekly-flow-ui.md) — weekly UX and when Notion saves run  
- [`AGENTS.md`](../AGENTS.md) — `/performance-audit` agent workflow  
