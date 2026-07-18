#!/usr/bin/env python3
"""Aggregate every downloaded nightly campaign and record honest completeness."""

from __future__ import annotations

import argparse
from pathlib import Path

from svtorture.campaign import (
    aggregate_campaigns,
    create_missing_campaign,
    load_campaign,
)
from svtorture.catalog import load_catalog
from svtorture.models import Distribution, ExecutionBackend

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", type=Path)
    parser.add_argument(
        "--output-file",
        type=Path,
        default=ROOT / ".svtorture" / "nightly-aggregate-path",
    )
    arguments = parser.parse_args()
    paths = sorted(arguments.artifacts.rglob("campaign.json"))
    catalog = load_catalog(ROOT)
    expected = tuple(
        sorted(
            tool.id
            for tool in catalog.tools.tools
            if tool.ci
            and tool.publish
            and tool.distribution is Distribution.OPEN_SOURCE
            and tool.execution is ExecutionBackend.DOCKER
        )
    )
    if paths:
        campaign = aggregate_campaigns(
            ROOT,
            tuple(load_campaign(path) for path in paths),
            expected_tools=expected,
        )
    else:
        campaign = create_missing_campaign(
            catalog,
            suite_id="all",
            expected_tool_ids=expected,
        )
    campaign_path = ROOT / ".svtorture" / "campaigns" / campaign.id / "campaign.json"
    portable_campaign_path = campaign_path.relative_to(ROOT)
    arguments.output_file.parent.mkdir(parents=True, exist_ok=True)
    arguments.output_file.write_text(str(portable_campaign_path) + "\n", encoding="utf-8")
    print(portable_campaign_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
