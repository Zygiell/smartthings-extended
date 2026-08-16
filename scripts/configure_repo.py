#!/usr/bin/env python3
"""Fill GitHub owner placeholders before the first push."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 scripts/configure_repo.py GITHUB_USERNAME")

owner = sys.argv[1].strip()
if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", owner):
    raise SystemExit("That does not look like a valid GitHub username.")

root = Path(__file__).resolve().parents[1]
manifest_path = root / "custom_components" / "smartthings_extended" / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

manifest["documentation"] = f"https://github.com/{owner}/smartthings-extended"
manifest["issue_tracker"] = f"https://github.com/{owner}/smartthings-extended/issues"
manifest["codeowners"] = [f"@{owner}"]

manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Configured repository owner: {owner}")
print(f"Repository URL: https://github.com/{owner}/smartthings-extended")
