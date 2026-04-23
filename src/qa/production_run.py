"""Migration QA production sign-off runner.

Gates on the deployed Vercel SHA matching the reference git ref (default
`origin/Migration-QA`), then runs the Playwright drawer + detail specs
against the live Vercel URL.

Usage:
    from src.qa.production_run import run_production
    run_production()  # defaults
    run_production(ref="origin/main", base_url="https://web-one-lake-22.vercel.app")

Read-only: never writes to the database. Commits the resulting matrix
under `docs/qa/migration-matrix-<date>-prod.md` (by the caller, not this
script) once the pass rate is acceptable.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

from .matrix import run_matrix


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REF = "origin/Migration-QA"
DEFAULT_BASE_URL = "https://web-one-lake-22.vercel.app"


class SHAMismatch(RuntimeError):
    pass


def local_ref_sha(ref: str = DEFAULT_REF) -> str:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SHAMismatch(
            f"Cannot resolve git ref {ref!r}: {result.stderr.strip()}. "
            f"Push the branch to origin first (e.g. `git push -u origin "
            f"{ref.replace('origin/', '')}`) or pass a different --ref."
        )
    return result.stdout.strip()


def deployed_sha(base_url: str = DEFAULT_BASE_URL, timeout: float = 10.0) -> Optional[str]:
    """Resolve the SHA of the Vercel-served build.

    Looks for a common Vercel convention: a `<meta name="x-commit-sha">` tag
    OR a `/__commit` endpoint. Falls back to parsing the built JS bundle
    name (Vite emits content hashes but those are not git SHAs).

    Returns None if the SHA cannot be determined — caller should abort.
    """
    try:
        with urlopen(base_url, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    m = re.search(r'name="x-commit-sha"\s+content="([a-f0-9]{7,40})"', html)
    if m:
        return m.group(1)

    try:
        with urlopen(f"{base_url.rstrip('/')}/__commit", timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="ignore").strip()
            if re.fullmatch(r"[a-f0-9]{7,40}", body):
                return body
    except Exception:
        pass

    return None


def run_production(
    ref: str = DEFAULT_REF,
    base_url: str = DEFAULT_BASE_URL,
    skip_sha_gate: bool = False,
) -> dict:
    """Execute the production sign-off run. Raises SHAMismatch if gated."""
    expected = local_ref_sha(ref)
    observed = deployed_sha(base_url) if not skip_sha_gate else None

    if not skip_sha_gate:
        if observed is None:
            raise SHAMismatch(
                f"Could not resolve deployed SHA from {base_url}. "
                "Expose a <meta name='x-commit-sha'> tag or a /__commit endpoint, "
                "or pass --skip-sha-gate if you have manually verified deploy freshness."
            )
        if not observed.startswith(expected[: len(observed)]) and not expected.startswith(
            observed[: len(expected)]
        ):
            raise SHAMismatch(
                f"Vercel is serving {observed}; {ref} is {expected}. "
                "Redeploy or wait for Vercel, then re-run."
            )

    web_dir = REPO_ROOT / "web"
    env = os.environ.copy()
    env["PLAYWRIGHT_BASE_URL"] = base_url.rstrip("/")
    subprocess.run(
        ["npm", "run", "test:e2e"],
        cwd=web_dir,
        env=env,
        check=False,
    )

    matrix = run_matrix()
    # Caller renames / copies to a -prod-suffixed filename.
    return matrix
