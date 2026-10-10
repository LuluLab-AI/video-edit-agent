#!/usr/bin/env python3
"""Require a working LuluLab API key immediately before the remote strategy stage."""
from __future__ import annotations

import argparse

from lululab_task import require_valid_api_key


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", help="Optional Node.js .mjs CLI path")
    args = parser.parse_args()

    try:
        require_valid_api_key(cli_path=args.cli)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None

    print("API_KEY_VALID")


if __name__ == "__main__":
    main()
