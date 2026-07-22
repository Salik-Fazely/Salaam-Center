"""Synchronize the reviewed Cloudflare Pages route allowlist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from .deployment_boundary import expected_redirect_rules
except ImportError:
    from deployment_boundary import expected_redirect_rules


REPO_ROOT = Path(__file__).resolve().parents[1]
REDIRECTS_PATH = Path("_redirects")
HEADER = """# Cloudflare Pages static public-route allowlist.
# First-match 200 proxies read only reviewed bilingual backing artifacts. The
# language-scoped and global catchalls resolve absent sentinels so Cloudflare
# serves the nearest styled 404 with a real HTTP 404 status.
"""


def expected_source() -> str:
    return HEADER + "\n".join(expected_redirect_rules()) + "\n"


def synchronize(root: Path, write: bool) -> int:
    path = root.resolve() / REDIRECTS_PATH
    expected = expected_source()
    try:
        actual = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        actual = ""
    except (OSError, UnicodeError) as error:
        print(f"Route allowlist cannot be read: {error}", file=sys.stderr)
        return 2
    if actual == expected:
        print("Cloudflare route allowlist is synchronized.")
        return 0
    if not write:
        print("Cloudflare route allowlist drift detected: _redirects", file=sys.stderr)
        return 1
    path.write_bytes(expected.encode("utf-8"))
    print("Updated _redirects from the bilingual deployment boundary.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return synchronize(REPO_ROOT, write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
