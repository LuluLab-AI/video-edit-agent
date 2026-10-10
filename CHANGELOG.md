# Changelog

## 5.0.0 (2026-10-10, release candidate)

- Rename the public Skill name, installation folder, invocation, and repository to `video-edit-agent`.
- Keep the existing editing workflow, service request client identifier, and API contract unchanged.
- Add English and Chinese GitHub installation guides and GPL-3.0-only licensing.
- Correct the public LuluLab support link and preserve the existing editing policy integration.
- Resolve the default subtitle font directory to Windows system fonts on Windows while retaining the existing macOS style.

## 4.5.0 (2026-10-10)

- Added persistent BCP-47 interaction language context and strict separation from narration and subtitle language.
- Replaced native LuluLab binaries with the bundled Node.js 20+ CLI; added file input and result download commands.
- Preserved the VideoEditingPolicyV1 request schema and delayed Key gate. Saved task IDs for safe polling after timeout.
- Added Mock tests for CLI requests, credentials, paths, task recovery, and language priority.
