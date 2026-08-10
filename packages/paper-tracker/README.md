# Personalized Economics Paper Tracker

Weekly discovery is a radar, not an ever-growing reading obligation. The
tracker evaluates a broad labor/education/human-capital set (AI is eligible but
not required), calibrates saturated model scores into deterministic ranks, and
keeps portfolio lanes for direct fit, adjacent work, contradiction, and methods.

## Attention contract

- Weekly paper-card output defaults to 10 candidates.
- The canonical queue keeps full searchable history.
- The active queue defaults to 8 papers: at most 3 Tier 1 and 5 Tier 2.
- Tier 3 methods stay in searchable backlog unless deliberately selected.
- Unselected live records expire after 21 days without being deleted.
- Human `deep` and `targeted` decisions become pinned `in_progress` records.

Environment overrides:

- `PAPER_TRACKER_WEEKLY_MAX` (default `10`)
- `PAPER_TRACKER_ACTIVE_MAX` (default `8`)
- `PAPER_TRACKER_ACTIVE_TIER_CAPS` (default `1:3,2:5,3:0`)
- `PAPER_TRACKER_QUEUE_TTL_DAYS` (default `21`)
- `PAPER_TRACKER_LANE_MIX` (default profile projection or `0.55/0.20/0.15/0.10`)

`queue_state.jsonl` is canonical. `reading_queue.md` is a generated view of
only `queued` and `in_progress` papers; backlog, clustered, expired, and
terminal records remain recoverable in JSONL.
