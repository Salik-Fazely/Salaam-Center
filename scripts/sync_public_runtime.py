"""Synchronize committed Cloudflare Pages backing files from reviewed sources."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from deployment_boundary import public_backing_pairs


REPO_ROOT = Path(__file__).resolve().parents[1]


class SyncError(RuntimeError):
    """Raised when the reviewed public source set cannot be synchronized safely."""


def synchronize(root: Path, write: bool) -> int:
    root = root.resolve()
    drifted: list[tuple[str, str, bytes]] = []
    for source, backing in public_backing_pairs():
        source_path = root / source
        backing_path = root / backing
        try:
            source_bytes = source_path.read_bytes()
        except OSError as error:
            raise SyncError(f"cannot read reviewed public source {source}: {error}") from error
        try:
            backing_bytes = backing_path.read_bytes()
        except FileNotFoundError:
            backing_bytes = None
        except OSError as error:
            raise SyncError(f"cannot read public backing artifact {backing}: {error}") from error
        if backing_bytes != source_bytes:
            drifted.append((source, backing, source_bytes))

    if write:
        for _, backing, source_bytes in drifted:
            backing_path = root / backing
            backing_path.parent.mkdir(parents=True, exist_ok=True)
            backing_path.write_bytes(source_bytes)
        if drifted:
            print("Updated public runtime backing artifacts:")
            for source, backing, _ in drifted:
                print(f"  - {backing} <- {source}")
        else:
            print("Public runtime backing artifacts already synchronized.")
        return 0

    if drifted:
        print("Public runtime backing drift detected:", file=sys.stderr)
        for source, backing, _ in drifted:
            print(f"  - {backing} <- {source}", file=sys.stderr)
        return 1

    print(f"Public runtime synchronized across {len(public_backing_pairs())} public runtime artifact(s).")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize committed Cloudflare Pages backing artifacts."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write reviewed backing artifacts")
    mode.add_argument("--check", action="store_true", help="report drift without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return synchronize(REPO_ROOT, write=args.write)
    except SyncError as error:
        print(f"Public runtime synchronization failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
