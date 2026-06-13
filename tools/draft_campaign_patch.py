"""Draft an AI-assisted campaign manifest patch and apply it with user approval.

Usage:
    python tools/draft_campaign_patch.py --manifest path/to/manifest.json --request "Add an undead jailer to the ossuary."

Flow:
    1. Load manifest
    2. LLM drafts a ManifestPatch from the request
    3. Validator checks the proposed result
    4. Show diff + any errors
    5. Prompt user: apply? [y/N]
    6. If approved and valid: write updated manifest
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


if __name__ == "__main__":
    import argparse
    import os

    from dungeon_daddy.campaign.drafter import CampaignDrafter
    from dungeon_daddy.campaign.draft_flow import run_draft_flow
    from dungeon_daddy.llm.openai_provider import OpenAIProvider

    parser = argparse.ArgumentParser(description="Draft and apply an AI-assisted campaign patch.")
    parser.add_argument("--manifest", required=True, metavar="PATH", help="Path to campaign_manifest.json")
    parser.add_argument("--request", required=True, metavar="TEXT", help="Natural-language authoring request")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    provider = OpenAIProvider(api_key=api_key)
    drafter = CampaignDrafter(provider=provider)

    sys.exit(run_draft_flow(
        manifest_path=Path(args.manifest),
        request=args.request,
        drafter=drafter,
    ))
