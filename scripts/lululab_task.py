#!/usr/bin/env python3
"""LuluLab Node.js CLI adapter; never place API keys in process arguments."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_KEY_GUIDANCE = "LULULAB_API_KEY_REQUIRED: https://lululab.ai"
API_KEY_ENV_NAMES = ("LULULAB_API_KEY", "LZSTUDIO_API_KEY", "RECREATE_VIDEO_API_KEY", "LINGZHI_API_KEY")
class CredentialNotFoundError(RuntimeError): pass
class CredentialConfigError(RuntimeError): pass

def credential_config_paths() -> list[Path]:
    """Return a small allowlist of compatible local credential stores."""
    candidates: list[Path] = []
    for name in ("LULULAB_CONFIG", "LZSTUDIO_CONFIG"):
        override = os.getenv(name, "").strip()
        if override:
            candidates.append(Path(override).expanduser())
    home = Path.home()
    candidates.extend(
        [
            home / ".recreate-video" / "config.json",
            home / ".ugc-product-video" / "config.json",
            home / ".product-image-ad" / "config.json",
        ]
    )
    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        marker = str(path.resolve(strict=False))
        if marker not in seen:
            result.append(path)
            seen.add(marker)
    return result


def _read_config_key(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CredentialConfigError(f"API_KEY_CONFIG_UNREADABLE: {path}") from exc
    if not isinstance(data, dict):
        raise CredentialConfigError(f"API_KEY_CONFIG_NOT_OBJECT: {path}")
    value = data.get("apiKey", "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise CredentialConfigError(f"API_KEY_CONFIG_NOT_STRING: {path}")
    return value.strip()


def _json_loads_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def resolve_api_key(
    explicit: str | None = None,
    *,
    config_paths: list[Path] | None = None,
) -> tuple[str, str]:
    """Resolve a key and its non-secret source label in deterministic order."""
    explicit_value = str(explicit or "").strip()
    if explicit_value:
        return explicit_value, "explicit"

    for name in API_KEY_ENV_NAMES:
        value = os.getenv(name, "").strip()
        if value:
            return value, f"env:{name}"

    errors: list[CredentialConfigError] = []
    for path in config_paths if config_paths is not None else credential_config_paths():
        try:
            value = _read_config_key(Path(path))
        except CredentialConfigError as exc:
            errors.append(exc)
            continue
        if value:
            return value, f"config:{path}"

    if errors:
        raise errors[0]
    raise CredentialNotFoundError("Missing LuluLab API key")


def api_key(explicit: str | None = None, *, config_paths: list[Path] | None = None) -> str:
    return resolve_api_key(explicit, config_paths=config_paths)[0]


def _redact(text: str, *secrets: str) -> str:
    result = str(text)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result


def find_cli(explicit: str | None = None) -> Path:
    bundled = ROOT / "scripts" / "lululab_cli.mjs"
    candidate = Path(explicit).expanduser() if explicit else bundled
    if not candidate.is_file() or candidate.suffix.lower() != ".mjs":
        raise RuntimeError("NODE_CLI_MISSING: configure a valid .mjs Node.js CLI path")
    return candidate.resolve()


def find_node() -> str:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("NODE_MISSING: install Node.js 20 or newer")
    try:
        result = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("NODE_UNAVAILABLE: verify the Node.js installation") from exc
    try: major = int(result.stdout.strip().lstrip("v").split(".")[0])
    except (ValueError, IndexError): major = 0
    if result.returncode or major < 20:
        raise RuntimeError("NODE_VERSION: Node.js 20 or newer is required")
    return node


def _run_cli(cli: Path, args: list[str], *, timeout: float = 120, key: str | None = None) -> dict[str, Any]:
    node = find_node()
    secret = key or api_key()
    env = os.environ.copy()
    env["LULULAB_API_KEY"] = secret
    try:
        proc = subprocess.run([node, str(cli), *args], text=True, capture_output=True,
                              timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("NODE_CLI_TIMEOUT: check task status before retrying submission") from exc
    except OSError as exc:
        raise RuntimeError("NODE_CLI_START_FAILED: verify the Node.js installation") from exc
    if proc.returncode:
        try:
            detail = json.loads(proc.stderr).get("error", "")
        except (ValueError, TypeError):
            detail = ""
        # The Node CLI uses controlled diagnostics; do not leak raw server output.
        raise RuntimeError(_redact(f"NODE_CLI_FAILED: {detail or 'command failed'}", secret))
    try:
        result = json.loads(proc.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("NODE_CLI_INVALID_JSON: command returned no valid JSON") from exc
    if not isinstance(result, dict):
        raise RuntimeError("NODE_CLI_INVALID_JSON: expected an object")
    return result


def validate_api_key(*, cli_path: str | None = None, key: str | None = None,
                     timeout_seconds: float = 30) -> dict[str, Any]:
    secret = api_key(key)
    return _run_cli(find_cli(cli_path), ["user", "--credits"],
                    timeout=max(5.0, float(timeout_seconds)), key=secret)


def require_valid_api_key(*, cli_path: str | None = None, key: str | None = None,
                          timeout_seconds: float = 30) -> dict[str, Any]:
    try: return validate_api_key(cli_path=cli_path, key=key, timeout_seconds=timeout_seconds)
    except CredentialNotFoundError as exc: raise RuntimeError(API_KEY_GUIDANCE) from exc
    except CredentialConfigError as exc: raise RuntimeError(f"API_KEY_CONFIG_INVALID: {exc}") from exc
    except RuntimeError as exc:
        if any(x in str(exc).lower() for x in ("http 401", "http 403", "unauthorized", "forbidden")):
            raise RuntimeError("API_KEY_INVALID: https://lululab.ai") from exc
        raise

def _unwrap_output(value: Any) -> Any:
    value = _json_loads_maybe(value)
    # Keep real engine payloads intact. Only peel generic transport wrappers.
    for _ in range(4):
        if not isinstance(value, dict):
            break
        if any(k in value for k in ("variants", "rankings", "engineVersion", "operation")):
            break
        for key in ("body", "data", "result", "output"):
            if key in value and len(value) <= 3:
                value = _json_loads_maybe(value[key])
                break
        else:
            break
    return value


def submit_and_wait(payload: dict[str, Any], *, workflow_id: str,
                    cli_path: str | None = None, key: str | None = None,
                    timeout_seconds: float = 180, poll_seconds: float = 1.5,
                    state_path: str | Path | None = None) -> dict[str, Any]:
    cli = find_cli(cli_path)
    secret = api_key(key)
    compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256((workflow_id + "\n" + compact).encode()).hexdigest()
    state_file = Path(state_path) if state_path else ROOT / "work" / "lululab_task_state.json"
    state = {}
    if state_file.is_file():
        try: state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError): raise RuntimeError("TASK_STATE_INVALID: inspect the saved task state before submitting")
    if state.get("status") in {"pending", "uncertain"} and state.get("digest") != digest:
        raise RuntimeError("PRIOR_TASK_UNRESOLVED: inspect the saved paid task before submitting a different payload")
    if state.get("digest") == digest and state.get("status") in {"pending", "uncertain"}:
        task_id = state.get("id")
        if not task_id:
            raise RuntimeError("TASK_SUBMISSION_UNCERTAIN: check server tasks before retrying; no second paid submission was made")
    else:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"digest": digest, "status": "uncertain"}), encoding="utf-8")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as handle:
            handle.write(compact)
            input_file = Path(handle.name)
        try:
            created = _run_cli(cli, ["task", "submit", "--workflow-id", workflow_id,
                                     "--input-file", str(input_file)],
                               timeout=min(120, timeout_seconds), key=secret)
        finally:
            input_file.unlink(missing_ok=True)
        task_id = str(created.get("id") or "").strip()
        if not task_id:
            raise RuntimeError("TASK_SUBMISSION_UNCERTAIN: no task ID returned; do not submit again")
        state_file.write_text(json.dumps({"digest": digest, "status": "pending", "id": task_id}), encoding="utf-8")
    deadline = time.monotonic() + max(5.0, float(timeout_seconds))
    last = {}
    while True:
        fetched = _run_cli(cli, ["task", "fetch", "--id", task_id],
                           timeout=min(120, timeout_seconds), key=secret)
        last = fetched
        status = str(fetched.get("status") or "").strip().lower()
        if status in {"succeeded", "success", "completed", "complete"}:
            result = _unwrap_output(fetched.get("output"))
            if not isinstance(result, dict): raise RuntimeError("TASK_OUTPUT_INVALID: expected JSON object")
            state_file.write_text(json.dumps({"digest": digest, "status": "completed", "id": task_id}), encoding="utf-8")
            return result
        if status in {"failed", "error", "cancelled", "canceled", "timedout", "timed_out"}:
            state_file.write_text(json.dumps({"digest": digest, "status": "failed", "id": task_id}), encoding="utf-8")
            raise RuntimeError(f"TASK_FAILED: {task_id} ({status})")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"TASK_PENDING: {task_id} ({status}); resume polling without resubmitting")
        time.sleep(max(0.2, float(poll_seconds)))


def upload_file(path: str | Path, *, cli_path: str | None = None, key: str | None = None) -> dict[str, Any]:
    return _run_cli(find_cli(cli_path), ["upload", str(path)], key=api_key(key))


def download_result(url: str, output: str | Path, *, cli_path: str | None = None,
                    key: str | None = None) -> dict[str, Any]:
    return _run_cli(find_cli(cli_path), ["download", "--url", url, "--output", str(output)], key=api_key(key))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow-id", required=True)
    ap.add_argument("--input-file", required=True)
    ap.add_argument("--output-file", required=True)
    ap.add_argument("--cli")
    ap.add_argument("--timeout-seconds", type=float, default=180)
    ap.add_argument("--poll-seconds", type=float, default=1.5)
    args = ap.parse_args()
    payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    result = submit_and_wait(payload, workflow_id=args.workflow_id, cli_path=args.cli,
                             timeout_seconds=args.timeout_seconds, poll_seconds=args.poll_seconds)
    out = Path(args.output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)
if __name__ == "__main__": main()
