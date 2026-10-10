# Interaction language contract

Apply this in Codex, Claude Code, WorkBuddy, and other agents before every user-facing message. The agent supplies a BCP-47 locale. Scripts never infer it from OS locale, tool output, filenames, transcripts, or server prose.

Priority: (1) explicit user reply language; (2) main language of the current user task message; (3) saved task locale; (4) agent default reply language if available; (5) English. Exclude quotes, uploads, isolated numbers, and simple confirmations from message-language detection.

At task start run `python scripts/language_context.py --message-locale <BCP-47>`. Pass `--explicit-locale` on a user language switch. Pass `--agent-default-locale` only when exposed by the agent. On numeric replies, simple confirmations, retries, and resumes, run with no locale options to retain the saved locale. Keep `work/language_context.json` throughout the task. `mediaLanguage` describes actual audio/script language only when known and never chooses the interaction language.

Compose the task introduction, material instructions, parameter confirmation, footage summary, edit-plan explanation, progress, quality findings, errors, retry guidance, and delivery in `interactionLocale`. Use structured data and the agent's language ability, without translation APIs or fixed language packs. CLI stderr, Python exceptions, and server text are internal diagnostics: explain their error codes or facts in the interaction language; never paste raw text that conflicts with it.

Preserve JSON keys, paths, IDs, source references, times, numeric scores, confidence, edit actions, API arguments, schema fields, narration, transcripts, captions, subtitles, and timeline data. Audio mode uses the recorded voice and actual transcript even when the user interacts in another language. Script mode follows the supplied script and existing audio priority. Keep `VideoEditingPolicyV1` output as structured internal data; translate only the explanation of that data.
