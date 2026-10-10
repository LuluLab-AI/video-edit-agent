#!/usr/bin/env python3
"""Cross-platform, read-only runtime check for the published WorkBuddy skills."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
from pathlib import Path


PROFILES = {
    "recreate-video-agent": {
        "tools": ("ffmpeg", "ffprobe"),
        "modules": (("PIL", "Pillow"),),
        "needs_lululab": True,
    },
    "video-translate-agent": {
        "tools": ("ffmpeg", "ffprobe"),
        "modules": (("pydantic", "pydantic"), ("yaml", "PyYAML"), ("cv2", "opencv-python"), ("numpy", "numpy")),
        "needs_lululab": False,
    },
    "video-edit-agent": {
        "tools": ("ffmpeg", "ffprobe"),
        "modules": (),
        "needs_lululab": True,
    },
    "product-image-ad": {
        "tools": (),
        "modules": (("PIL", "Pillow"),),
        "needs_lululab": True,
    },
    "video-caption-agent": {
        "tools": ("ffmpeg", "ffprobe"),
        "modules": (("cv2", "opencv-python-headless"), ("numpy", "numpy")),
        "needs_lululab": True,
    },
}


def find_lululab() -> str:
    from lululab_task import find_cli, find_node
    try:
        find_node()
        return str(find_cli())
    except RuntimeError:
        return ""


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skill_name = root.name
    profile = PROFILES.get(skill_name)
    if profile is None:
        print(json.dumps({"ok": False, "error": f"UNKNOWN_SKILL: {skill_name}"}, ensure_ascii=False))
        return 2

    system = platform.system()
    supported = system in {"Darwin", "Windows", "Linux"}
    checks: dict[str, object] = {
        "platform": system,
        "architecture": platform.machine(),
        "python": sys.version.split()[0],
        "skillRoot": str(root),
        "pathIndependent": True,
    }
    missing: list[str] = []
    for tool in profile["tools"]:
        value = shutil.which(str(tool)) or ""
        checks[str(tool)] = value
        if not value:
            missing.append(str(tool))
    for module, package in profile["modules"]:
        available = importlib.util.find_spec(str(module)) is not None
        checks[f"python:{module}"] = available
        if not available:
            missing.append(str(package))
    lululab = find_lululab()
    checks["node_cli"] = lululab
    if profile["needs_lululab"] and not lululab:
        missing.append("node_cli")

    if skill_name == "video-caption-agent":
        whisper = shutil.which("whisper") or ""
        checks["whisper"] = whisper
        if not whisper and importlib.util.find_spec("whisper") is None:
            missing.append("openai-whisper")

    result = {
        "ok": supported and not missing,
        "skill": skill_name,
        "checks": checks,
        "missing": missing,
        "message": "PREFLIGHT_OK" if supported and not missing else "PREFLIGHT_MISSING_DEPENDENCIES",
        "nextSteps": [
            "Install missing dependencies listed in README.",
            "Keep the complete Skill folder together.",
            "Rerun preflight after installing dependencies.",
        ] if missing or not supported else [],
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
