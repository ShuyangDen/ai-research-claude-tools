from __future__ import annotations

import argparse
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "src"))

from research_workbench.abstract_resolver import AbstractResolver, complete_abstract, repair_mojibake  # noqa: E402
from research_workbench.service import _paper_from_mapping  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill only missing complete paper abstracts.")
    parser.add_argument("queue", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed-queue", type=Path, help="Copy verified abstracts from another queue before lookup.")
    parser.add_argument("--nber-abstracts", type=Path, help="Optional official NBER abs.tsv metadata file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    queue = args.queue.resolve()
    records = [json.loads(line) for line in queue.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seeded_abstracts = 0
    repaired_text = 0
    if args.seed_queue:
        seed_records = [json.loads(line) for line in args.seed_queue.resolve().read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        seeds = {str(raw.get("paper_id", "")): raw for raw in seed_records if complete_abstract(str(raw.get("abstract", "") or ""))}
        for raw in records:
            if complete_abstract(str(raw.get("abstract", "") or "")):
                continue
            seed = seeds.get(str(raw.get("paper_id", "")))
            if not seed:
                continue
            for key in ("abstract", "abstract_evidence", "abstract_source", "abstract_fetched_at", "identifiers", "provenance"):
                if key in seed:
                    raw[key] = seed[key]
            raw["abstract_evidence"] = "complete"
            seeded_abstracts += 1
    if args.nber_abstracts:
        nber_rows = {}
        for line in args.nber_abstracts.resolve().read_text(encoding="utf-8-sig").splitlines():
            paper_id, separator, abstract = line.partition("\t")
            if separator and complete_abstract(abstract.replace("\\n", " ")):
                nber_rows[paper_id.casefold()] = abstract.replace("\\n", " ")
        for raw in records:
            if complete_abstract(str(raw.get("abstract", "") or "")):
                continue
            paper_id = str(raw.get("paper_id", ""))
            abstract = nber_rows.get(paper_id.replace("nber:", "").casefold(), "")
            if not abstract:
                continue
            raw["abstract"] = abstract
            raw["abstract_evidence"] = "complete"
            raw["abstract_source"] = "Official NBER metadata"
            raw["provenance"] = list(raw.get("provenance", [])) + [{
                "source": "Official NBER metadata", "source_id": paper_id,
                "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "url": "https://www.nber.org/research/data/nber-working-papers-and-chapters-metadata",
            }]
            seeded_abstracts += 1
    for raw in records:
        for key in ("title", "authors", "abstract"):
            value = raw.get(key)
            if not isinstance(value, str):
                continue
            repaired = repair_mojibake(value)
            if repaired != value:
                raw[key] = repaired
                repaired_text += 1
    false_abstracts = 0
    for raw in records:
        abstract = str(raw.get("abstract", "") or "").casefold()
        if "founded in 1920, the nber is a private" in abstract:
            raw["abstract"] = ""
            raw["abstract_evidence"] = "missing"
            raw.pop("abstract_source", None)
            raw.pop("abstract_fetched_at", None)
            false_abstracts += 1
    candidates = [(index, _paper_from_mapping(raw)) for index, raw in enumerate(records)]
    candidates = [(index, paper) for index, paper in candidates if not paper.abstract_ready]
    if args.limit > 0:
        candidates = candidates[: args.limit]
    resolver = AbstractResolver(timeout=25.0)
    resolved: dict[int, object] = {}

    def fetch(index_paper: tuple[int, object]):
        index, paper = index_paper
        return index, resolver.resolve(paper)

    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as pool:
        futures = [pool.submit(fetch, item) for item in candidates]
        for completed, future in enumerate(as_completed(futures), 1):
            index, result = future.result()
            if result is not None:
                resolved[index] = result
            if completed % 20 == 0 or completed == len(futures):
                print(f"checked={completed}/{len(futures)} resolved={len(resolved)}", flush=True)

    if not resolved and not false_abstracts and not seeded_abstracts and not repaired_text:
        print("No complete abstracts resolved; queue unchanged.")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = queue.with_name(f"{queue.name}.pre-abstract-backfill-{stamp}.bak")
    shutil.copy2(queue, backup)
    fetched_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for index, result in resolved.items():
        raw = records[index]
        raw["abstract"] = result.abstract
        raw["abstract_evidence"] = "complete"
        raw["abstract_source"] = result.source
        raw["abstract_fetched_at"] = fetched_at
        identifiers = raw.get("identifiers") if isinstance(raw.get("identifiers"), dict) else {}
        if result.identifier_type and result.identifier:
            identifiers[result.identifier_type] = result.identifier
        raw["identifiers"] = identifiers
        provenance = raw.get("provenance") if isinstance(raw.get("provenance"), list) else []
        provenance.append({"source": result.source, "source_id": result.identifier, "fetched_at": fetched_at, "url": result.url})
        raw["provenance"] = provenance
    temporary = queue.with_suffix(queue.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(raw, ensure_ascii=False) + "\n" for raw in records), encoding="utf-8")
    temporary.replace(queue)
    print(
        f"updated={len(resolved)} seeded={seeded_abstracts} repaired_text={repaired_text} "
        f"cleared_false_abstracts={false_abstracts} backup={backup}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
