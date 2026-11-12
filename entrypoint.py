"""WhiteBoxXAI Governance Action.

Syncs a whitebox.yaml policy to WhiteBoxXAI, optionally evaluates a model
against it, and exits non-zero when the evaluation result is "block".
Standard library only.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.whiteboxxai.com"
TIMEOUT_SECONDS = 60


def _input(name: str, default: str = "") -> str:
    return os.environ.get(f"INPUT_{name.upper()}", default).strip()


def _base_url() -> str:
    # The input wins, then the variable the WhiteBoxXAI SDK reads, then the
    # name earlier versions of this Action read.
    url = (
        _input("base_url")
        or os.environ.get("WHITEBOX_BASE_URL", "").strip()
        or os.environ.get("WHITEBOXXAI_API_BASE_URL", "").strip()
        or DEFAULT_BASE_URL
    )
    return url.rstrip("/")


def _post(url: str, api_key: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body or {}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "whitebox-governance-action",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def _set_output(name: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def _escape(text: str) -> str:
    # Workflow-command escaping, so a detail can't end the annotation early.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    api_key = _input("api_key")
    policy_file = _input("policy_file", "whitebox.yaml") or "whitebox.yaml"
    sync = _input("sync", "true").lower() not in ("false", "0", "no", "off")
    model_id = _input("model_id")
    base = f"{_base_url()}/api/v1/policy"

    if not api_key:
        print("::error::api_key is empty. Pass it from a repository secret.")
        return 1
    if not sync and not model_id:
        print("::error::Nothing to do: sync is false and no model_id was given.")
        return 1

    try:
        if sync:
            try:
                with open(policy_file, encoding="utf-8") as handle:
                    yaml_content = handle.read()
            except OSError as exc:
                print(f"::error::Cannot read policy file {policy_file}: {exc}")
                return 1
            print(f"Syncing {policy_file} ...")
            _post(f"{base}/sync", api_key, {"yaml_content": yaml_content})
            print("Policy synced.")

        if not model_id:
            return 0

        print(f"Evaluating model {model_id} against the policy ...")
        result = _post(f"{base}/evaluate/{model_id}", api_key)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"::error::WhiteBoxXAI returned HTTP {exc.code}: {_escape(detail)}")
        return 1
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"::error::Could not reach WhiteBoxXAI at {base}: {exc}")
        return 1

    action = str(result.get("action", ""))
    allowed = bool(result.get("allowed", True))
    violations = result.get("violations") or []

    if not result.get("policy_exists", True):
        print("No policy has been synced for this organization; the evaluation passes.")
    print(f"Policy result: {action} (allowed: {str(allowed).lower()})")
    for violation in violations:
        level = "error" if violation.get("action") == "block" else "warning"
        message = (
            f"[{str(violation.get('action', '')).upper()}] "
            f"{violation.get('policy_rule')}: {violation.get('detail')}"
        )
        print(f"::{level} title=WhiteBoxXAI policy::{_escape(message)}")

    _set_output("action", action)
    _set_output("allowed", str(allowed).lower())
    _set_output("violations", json.dumps(violations, separators=(",", ":")))

    if action == "block":
        print("::error::The model is blocked by policy. Failing the job.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
