# Performance audit (`/performance-audit`)

Repeatable, headless timing of **every control** in the Streamlit app against live Notion, ranked slowest-first, with flags that point at the likely cause. Slash command: `.cursor/commands/grocery-wizard/performance-audit.md`. Code: `src/grocery_wizard/dev/perf_audit/`.

```bash
just performance-audit --list                              # catalogue (W = writes stubbed, X = external, skipped)
just performance-audit --profile                           # full run, writes report + latest.json baseline
just performance-audit --only 'weekly.meals.*' --reps 3 --compare latest   # targeted re-run vs baseline
just performance-audit --fail-over 5                       # exit 1 if any warm scenario exceeds 5s
```

Output lands in `.local/grocery_wizard/perf/perf-<stamp>.md|.json`; `latest.json` is the baseline for `--compare latest`.

## How it works

| Piece | Role |
| --- | --- |
| `flows.py` | Drives the app with Streamlit `AppTest` (no browser): helpers to open pages, start plans, click buttons, use dev jump tools. |
| `scenarios.py` | The catalogue: one `Scenario` per control/flow (`prepare` puts the app in the right state, `act` is the timed interaction, `covers` lists widget keys it represents). |
| `tap.py` | Patches `notion_client.Client.request`: **reads** are real and timed, **writes** are never sent (a response echoing the request is returned and an estimated latency is charged). Mutating non-Notion HTTP is blocked; GET/HEAD are counted. |
| `measure.py` | Wall time, Notion read/write counts and seconds, Python (non-network) time, DOM weight (elements, select options), optional `cProfile`. |
| `runner.py` | **Cold** run (server caches cleared first) and **warm** runs (caches primed, new session), median of `--reps`. |
| `report.py` | Ranking, flags, per-interaction Notion request table, hot spots, coverage gaps, baseline comparison. |

Safe to run on the real databases: no Notion writes are issued, so no UAT cleanup is needed.

**Never run a scenario's `act` outside the audit runner** (for example in a throwaway script that wraps `Client.request` to count calls). Without the tap the write buttons really write. Use the runner: the report lists the calling site of every Notion request under **Notion requests per interaction**, so you do not need ad-hoc tracing.

## Budgets (what “fast enough” means)

| Interaction | Warm budget | Warm Notion reads |
| --- | --- | --- |
| Idle rerun / widget change in an already-open step | <= 0.5s | 0 |
| Button that does not write | <= 1.0s | 0 |
| Page open or step transition | <= 2.0s | 0 |
| Button that writes to Notion | <= 1.5s + write latency | only the write |
| Cold first load of a page | <= 5s | bounded, parallel/paginated |

## Flag glossary

| Flag | Meaning |
| --- | --- |
| `P0` / `P1` / `P2` | Warm time >= 5s / 2s / 1s. |
| `CACHE_MISS_WARM` | Notion reads on a warm, non-write interaction: something is uncached or a cache key leaks. |
| `POST_WRITE_REFETCH` | A write cleared caches and the following render re-read Notion. |
| `PYTHON_HEAVY` | >= 1s of non-network time: CPU in the script or Streamlit (parsing, index builds, widget serialization). |
| `READ_FANOUT` | >= 6 Notion reads in one interaction. |
| `WRITE_FANOUT` | >= 3 Notion writes in one interaction. |
| `HEAVY_DOM` | >= 1500 elements or >= 2000 select options sent to the browser. |
| `NOISY` | Warm repetitions differ 2x+ (Notion throttling or a parallel run). Re-run before trusting. |
| `COLD_GAP` | Cold >= 3x warm and >= 1s: first-load or cache-rebuild cost. |
| `EXTERNAL_ON_RENDER` | Non-Notion HTTP on a warm interaction. |

Thresholds live in `report.py`. Change them there and note why here.

## Fix playbook (flag -> cause -> pattern)

| Symptom | Typical cause | Fix pattern |
| --- | --- | --- |
| `PYTHON_HEAVY` on a step open | Expensive derived data (e.g. ingredient index, CRF ingredient parsing ~2ms/line) recomputed per session or per render | Memoize at process level keyed by content (`st.cache_data` / `functools.lru_cache`); build lazily only when the UI that needs it is opened; `persist="disk"` for rarely-changing data. |
| `CACHE_MISS_WARM` | Direct `db.query_*` / `find_*` call in a render path; DB handle constructed per call (client + data-source resolve + schema retrieve) | Route through `ui/notion_cache.py`; hold handles in `st.cache_resource`; read through `st.cache_data`. |
| `POST_WRITE_REFETCH` | `st.cache_data.clear()` / global invalidation after a small write | Clear only the affected cached function (`fn.clear(args)`) or update the cached value in place. |
| `HEAVY_DOM` with big selectboxes | `st.popover` / `st.expander` bodies execute and ship their widgets on every rerun even when closed | Gate with a toggle (`st.toggle` / `st.tabs(on_change="rerun")` + `.open`) so the body only runs when open; use `st.fragment` for local reruns. |
| `READ_FANOUT` | Sequential Notion pagination (100 rows/request) or per-row follow-up reads | Request fewer properties (`filter_properties`), incremental sync via `last_edited_time`, batch lookups. |
| Hundreds of Notion requests on a page render | Ensure-style calls (views, schema) executed on every render | Do once per session / cache result; skip when already ensured. |

Sources: Streamlit caching docs (`st.cache_data` returns pickled copies, `st.cache_resource` is a shared singleton, per-function `.clear()`), Streamlit forum guidance that `st.popover`/`st.expander` content always executes, Notion API request limits (3 requests/s average, 100 results per page).

## Adding or changing a scenario

1. Add a `Scenario(id=..., page=..., label=..., prepare=..., act=..., covers=(...))` in `scenarios.py`. The id is `<page>.<area>.<action>`.
2. Put heavy setup in `prepare` (not timed); keep `act` to a single user interaction.
3. Mark `writes=True` when the interaction writes (the tap stubs the write and charges `--write-latency`, default 0.4s).
4. Mark `external=True` for NYT/recipe-site/feedback flows: they are skipped and listed so you time them by hand.
5. List widget keys in `covers` so **Coverage gaps** stays empty.
6. `just test` (the harness has unit tests in `tests/src/grocery_wizard/dev/test_perf_audit.py`).

## Limitations

- Headless: measures server time (script + Notion + serialization), not browser paint or network transfer to the browser. Use `just grocery-ui` for a human spot-check.
- External flows (NYT sync, backfills, feedback submit) are skipped by design.
- Write cost is estimated, not measured, because writes are never sent.
- Numbers depend on the live Notion workspace size (recipe count, pantry size, saved plans); the report header records those counts so runs are comparable.
