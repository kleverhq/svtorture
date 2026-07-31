#!/usr/bin/env python3
"""Publish immutable campaign Releases and derive a latest-only Pages tree.

The manual GitHub Actions publication workflow calls this script through the
root ``just dashboard-publish`` recipe after campaign artifacts are aggregated
and the React application is built. It creates or verifies campaign Releases,
rebuilds trends from their unchanged summary assets, downloads the campaign
that is latest by campaign time, and writes a bounded static tree for the Pages
artifact uploader.
"""

from __future__ import annotations

import argparse
import os
import shlex
from pathlib import Path

from svtorture.campaign import load_campaign
from svtorture.catalog import load_catalog
from svtorture.github_publish import publish_dashboard
from svtorture.publish import PublicationError

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaigns", nargs="*", type=Path)
    parser.add_argument(
        "--campaign-list",
        help="Shell-like path list supplied safely by the variadic just recipe.",
    )
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--built-site", type=Path, default=ROOT / "dashboard" / "dist")
    parser.add_argument("--pages-output", type=Path, default=ROOT / ".svtorture" / "pages")
    arguments = parser.parse_args()
    if not arguments.repository:
        parser.error("--repository or GITHUB_REPOSITORY is required")
    listed = tuple(Path(value) for value in shlex.split(arguments.campaign_list or ""))
    campaign_paths = (*arguments.campaigns, *listed)
    if not campaign_paths:
        parser.error("at least one campaign path is required")

    try:
        summaries, report = publish_dashboard(
            load_catalog(ROOT),
            tuple(load_campaign(path) for path in campaign_paths),
            arguments.repository,
            arguments.built_site,
            arguments.pages_output,
            ROOT / "schemas",
        )
    except PublicationError as error:
        parser.error(str(error))
    print(f"published_campaigns={len(summaries)}")
    print(f"latest_campaign={summaries[-1].id}")
    print(f"pages_total_bytes={report.total_bytes}")
    print(f"pages_frontend_bytes={report.frontend_bytes}")
    print(f"pages_schema_bytes={report.schema_bytes}")
    print(f"pages_index_bytes={report.index_bytes}")
    print(f"pages_trends_bytes={report.trends_bytes}")
    print(f"pages_campaign_bytes={report.campaign_bytes}")
    print(f"pages_manifest_bytes={report.manifest_bytes}")
    print(f"pages_catalog_bytes={report.catalog_bytes}")
    print(f"pages_verdicts_bytes={report.verdicts_bytes}")
    print(f"pages_evidence_bytes={report.evidence_bytes}")
    print(f"pages_largest_evidence_shard_bytes={report.largest_evidence_shard_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
