#!/usr/bin/env python3
"""Persist agent supplied interaction language separately from media language."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'work' / 'language_context.json'

def normalize_locale(value: str | None) -> str | None:
    if not value or not value.strip(): return None
    parts = value.strip().replace('_', '-').split('-')
    if not re.fullmatch(r'[A-Za-z]{2,8}', parts[0]) or not all(re.fullmatch(r'[A-Za-z0-9]{1,8}', x) for x in parts[1:]):
        raise ValueError('Invalid BCP-47 locale')
    return '-'.join([parts[0].lower()] + [x.upper() if len(x)==2 and x.isalpha() else x.title() if len(x)==4 and x.isalpha() else x.lower() for x in parts[1:]])

def resolve_context(*, explicit_locale=None, message_locale=None, saved=None,
                    agent_default_locale=None, media_language=None):
    saved = saved or {}
    for source, value in [('user_explicit', explicit_locale), ('user_message', message_locale),
                          ('saved_task', saved.get('interactionLocale')),
                          ('agent_default', agent_default_locale)]:
        locale = normalize_locale(value)
        if locale: break
    else: locale, source = 'en', 'fallback'
    return {'interactionLocale': locale, 'interactionLanguageSource': source,
            'mediaLanguage': normalize_locale(media_language) if media_language else saved.get('mediaLanguage')}

def save_context(path=DEFAULT_PATH, **kwargs):
    path = Path(path)
    saved = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    context = resolve_context(saved=saved, **kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return context

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--path', type=Path, default=DEFAULT_PATH)
    ap.add_argument('--explicit-locale')
    ap.add_argument('--message-locale')
    ap.add_argument('--agent-default-locale')
    ap.add_argument('--media-language')
    args=ap.parse_args()
    print(json.dumps(save_context(args.path, explicit_locale=args.explicit_locale,
          message_locale=args.message_locale, agent_default_locale=args.agent_default_locale,
          media_language=args.media_language), ensure_ascii=False))
if __name__ == '__main__': main()
