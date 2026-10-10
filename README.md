# AI Video Editor

## Overview

Edit user-supplied live-action footage into narrated vertical video variants. This Skill is for creators and merchants who have permission to use the footage. The Agent Skills root is this repository's `video-edit-agent/` folder, with `SKILL.md` at its root.

## Key Features

- Recorded-audio or supplied-script narration, with an optional voice.
- Meaning-based shot selection, captions, optional fixed-level music, several variants, local FFmpeg rendering and technical quality checks.
- Remote edit strategy through the bundled LuluLab Node.js CLI.

## Requirements

A file-capable Agent Skills host such as Codex or Claude Code, Python 3, FFmpeg/FFprobe, Node.js 20+, and macOS or Windows are required. Script narration uses the operating system's speech capability. The remote strategy stage needs network access and a LuluLab API Key. Other agents need an equivalent file-based Skill mechanism.

## Installation

Ask your agent:

> Please install this LuluLab Skill into my current AI agent environment: https://github.com/LuluLab-AI/video-edit-agent . Follow the project's official installation instructions.

After reviewing the repository, copy the **whole** `video-edit-agent/` folder into the current agent's user Skill directory under the name `video-edit-agent`. Agent directories vary; confirm the location in that agent's current documentation. Keep `SKILL.md`, `scripts/`, `references/` and `input/config.json` together. Do not nest the `@indiv-lululab` source namespace in the Skill root. If the name is already installed, compare versions and ask before replacing it. Leave other Skills alone. Run `python3 scripts/workbuddy_preflight.py` on macOS or `py -3 scripts\workbuddy_preflight.py` on Windows, then reload Skill discovery and verify `video-edit-agent` appears.

This release renames the Skill formerly called `ai-video-editor`. If that older Skill is installed, ask the user before disabling or removing it to avoid two names for the same workflow.

## Quick Start

- “Use $video-edit-agent to make two vertical cuts from my live-action product demonstration, using the recorded narration.”
- “Edit my supplied footage into a 25-second UGC video with `input/voiceover_script.txt` as the English narration.”

Place footage in `input/videos/` and select `audio` or `script` in `input/config.json`. See [SKILL.md](SKILL.md) for the full workflow.

## Configuration

Check the client offline with `node scripts/lululab_cli.mjs --help`. Configure `LULULAB_API_KEY` locally before the remote strategy stage. The Skill validates it then with `scripts/validate_lululab_api_key.py` and the CLI's read-only `user --credits` call. Strategy requests use `task submit --workflow-id VideoEditingPolicyV1 --input-file <JSON file>` and `task fetch --id <task ID>`. No npm or `npx` install is needed. Never put a Key in a repository, log or command argument. See [CLI setup](references/lululab-cli-setup.md).

## Supported Languages

English and Chinese interaction follow [the existing locale rules](references/interaction-language.md). Original speech and captions retain their actual media language; explicit video-language instructions apply to generated media.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Skill is not recognized | Check the root folder and `SKILL.md`, then reload the agent's Skill list. |
| CLI is missing | Confirm Node.js 20+ and `scripts/lululab_cli.mjs`; run `--help`. |
| API Key is missing | Set `LULULAB_API_KEY` locally when the strategy stage is reached. |
| Network request fails | Check connectivity and recover a saved task ID before retrying. |
| Model or strategy call fails | Inspect task status; do not repeat a paid request without confirming its state. |
| Dependency is missing | Run the platform preflight and install the reported component. |

## Support

Website: https://lululab.ai  
Email: contact@lululab.ai
