#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.poc019_evaluation_dataset import (  # noqa: E402
    CASE_HEADERS,
    DEFAULT_CANDIDATE_WEIGHTS,
    POC019_COMPLETE_DATASET_ID,
    POC019_DATASET_ID,
    POC019_SEED,
    build_complete_evaluation,
    build_sample_evaluation,
    write_evaluation,
)


def _csv_preview(headers: list[str], rows: list[dict], limit: int) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows[:limit])
    return buffer.getvalue().rstrip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the isolated, deterministic POC-019 evaluation dataset."
    )
    parser.add_argument("--scope", choices=("sample", "complete"), default="sample")
    parser.add_argument("--dataset-id")
    parser.add_argument("--seed", type=int, default=POC019_SEED)
    parser.add_argument("--level-1-weight", type=int, default=DEFAULT_CANDIDATE_WEIGHTS["level_1"])
    parser.add_argument("--level-2-weight", type=int, default=DEFAULT_CANDIDATE_WEIGHTS["level_2"])
    parser.add_argument("--level-3-weight", type=int, default=DEFAULT_CANDIDATE_WEIGHTS["level_3"])
    parser.add_argument("--preview-rows", type=int, default=20)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "data" / "evaluation-previews")
    parser.add_argument("--write", action="store_true", help="Write a new isolated directory; otherwise dry-run only")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    dataset_id = args.dataset_id or (
        POC019_COMPLETE_DATASET_ID if args.scope == "complete" else POC019_DATASET_ID
    )
    builder = build_complete_evaluation if args.scope == "complete" else build_sample_evaluation
    package = builder(
        dataset_id=dataset_id,
        seed=args.seed,
        candidate_weights={
            "level_1": args.level_1_weight,
            "level_2": args.level_2_weight,
            "level_3": args.level_3_weight,
        },
    )
    print(json.dumps(package.summary(), indent=2, sort_keys=True))
    print("\nEvaluationCases.csv preview")
    print(_csv_preview(CASE_HEADERS, package.cases, args.preview_rows))
    print("\nSelected score results")
    selected_ids = [
        "P019-L1",
        "P019-L2",
        "P019-L3",
        "P019-UNKNOWN",
        "P019-LSE-L3-C019",
        "P019-LSE-L3-C020",
        "P019-NOCF-C019",
        "P019-NOCF-C020",
        "P019-MULTI-L1-L3",
        "P019-MULTI-L2-L3",
        "P019-CF-BEFORE-AGE",
        "P019-OLDER-NOCF",
    ]
    baseline = package.expected_results["baseline"]["incidents"]
    candidate = package.expected_results["candidate"]["incidents"]
    print(
        json.dumps(
            {
                incident_id: {
                    "baseline_score": baseline[incident_id]["total_score"],
                    "candidate_score": candidate[incident_id]["total_score"],
                    "facility_level": candidate[incident_id]["facility_level"],
                    "warning": candidate[incident_id]["warning"],
                }
                for incident_id in selected_ids
            },
            indent=2,
            sort_keys=True,
        )
    )
    if args.write:
        print(f"\nCreated {args.scope} evaluation: {write_evaluation(package, args.output_root)}")
    else:
        print("\nDry run only; no files were written.")


if __name__ == "__main__":
    main()
