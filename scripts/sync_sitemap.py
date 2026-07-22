"""Generate the bilingual production sitemap from the localized route manifest."""

from __future__ import annotations

import argparse
import sys
from html import escape
from pathlib import Path

try:
    from .localized_routes import RouteManifestError, load_localized_routes
except ImportError:
    from localized_routes import RouteManifestError, load_localized_routes


REPO_ROOT = Path(__file__).resolve().parents[1]
SITEMAP_PATH = Path("sitemap.xml")
PRODUCTION_ORIGIN = "https://salaam.center"


def absolute_url(public_path: str) -> str:
    return f"{PRODUCTION_ORIGIN}{public_path}"


def expected_sitemap(root: Path) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for route in load_localized_routes(root):
        if not route.sitemap:
            continue
        dari_url = escape(absolute_url(route.fa_AF), quote=True)
        english_url = escape(absolute_url(route.en), quote=True)
        for current_url in (dari_url, english_url):
            lines.extend(
                (
                    "  <url>",
                    f"    <loc>{current_url}</loc>",
                    f'    <xhtml:link rel="alternate" hreflang="fa-AF" href="{dari_url}" />',
                    f'    <xhtml:link rel="alternate" hreflang="en" href="{english_url}" />',
                    f'    <xhtml:link rel="alternate" hreflang="x-default" href="{dari_url}" />',
                    "  </url>",
                )
            )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def synchronize(root: Path, write: bool) -> int:
    target = root.resolve() / SITEMAP_PATH
    expected = expected_sitemap(root)
    try:
        actual = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        actual = ""
    except (OSError, UnicodeError) as error:
        print(f"Sitemap cannot be read: {error}", file=sys.stderr)
        return 2
    if actual == expected:
        print("Bilingual sitemap is synchronized (28 canonical URLs).")
        return 0
    if not write:
        print("Bilingual sitemap drift detected: sitemap.xml", file=sys.stderr)
        return 1
    target.write_bytes(expected.encode("utf-8"))
    print("Updated sitemap.xml from config/localized-routes.json.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return synchronize(REPO_ROOT, write=args.write)
    except RouteManifestError as error:
        print(f"Sitemap synchronization failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
