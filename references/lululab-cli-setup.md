# LuluLab Node.js CLI setup

Install Node.js 20 or newer on macOS, Windows, or Linux. This Skill uses only `scripts/lululab_cli.mjs`; it has no npm dependencies and never falls back to a native binary. Run `node scripts/lululab_cli.mjs --help` to verify startup. Set `input/config.json` `lululab_cli_path` only when pointing to a compatible `.mjs` entry.

At the remote strategy stage, the Python adapter discovers the API Key from its existing allowlisted sources and passes it through the child process environment. Never put the Key in command arguments or Skill files. The CLI supports `user --credits`, `upload <file>`, `task submit --workflow-id <id> --input-file <JSON file>`, `task fetch --id <id>`, and `download --url <URL> --output <file>`. The workflow remains `VideoEditingPolicyV1` with `schemaVersion: 1` and `operation: plan_edit`.

The adapter stores the paid task ID in `work/lululab_task_state.json`. A timeout resumes status polling; an uncertain submission without an ID blocks a second submission and requires checking the server task list.
