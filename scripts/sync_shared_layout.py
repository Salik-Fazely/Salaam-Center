"""Synchronize bilingual head, Header and Footer markup across public pages."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from .localized_routes import (
        LANGUAGE_KEYS,
        RouteManifestError,
        load_localized_routes,
        source_path_for_public_path,
    )
except ImportError:
    try:
        from scripts.localized_routes import (
            LANGUAGE_KEYS,
            RouteManifestError,
            load_localized_routes,
            source_path_for_public_path,
        )
    except ModuleNotFoundError:
        from localized_routes import (
            LANGUAGE_KEYS,
            RouteManifestError,
            load_localized_routes,
            source_path_for_public_path,
        )


REPO_ROOT = Path(__file__).resolve().parents[1]

HEAD_START = "<!-- LOCALIZED HEAD:START -->"
HEAD_END = "<!-- LOCALIZED HEAD:END -->"
HEADER_START = "<!-- SHARED HEADER:START -->"
HEADER_END = "<!-- SHARED HEADER:END -->"
FOOTER_START = "<!-- SHARED FOOTER:START -->"
FOOTER_END = "<!-- SHARED FOOTER:END -->"

HEADER_FRAGMENTS = {
    "fa_AF": "partials/header.fa-AF.html",
    "en": "partials/header.html",
}
FOOTER_FRAGMENTS = {
    "fa_AF": "partials/footer.fa-AF.html",
    "en": "partials/footer.html",
}
NAV_PLACEHOLDERS = {
    "home": "{{NAV_HOME_CURRENT}}",
    "our-approach": "{{NAV_OUR_APPROACH_CURRENT}}",
    "programs": "{{NAV_PROGRAMS_CURRENT}}",
    "teachers": "{{NAV_TEACHERS_CURRENT}}",
    "how-it-works": "{{NAV_HOW_IT_WORKS_CURRENT}}",
    "pricing": "{{NAV_PRICING_CURRENT}}",
    "about": "{{NAV_ABOUT_CURRENT}}",
}
ACTIVE_NAV_BY_ROUTE = {
    "home": "home",
    "our-approach": "our-approach",
    "programs": "programs",
    "quran": "programs",
    "dari-persian": "programs",
    "afghan-culture-islamic-ethics": "programs",
    "teachers": "teachers",
    "how-it-works": "how-it-works",
    "pricing": "pricing",
    "about": "about",
}
UNRESOLVED_PLACEHOLDER = re.compile(r"{{[^{}]+}}")


@dataclass(frozen=True)
class PageConfig:
    route_id: str
    path: str
    public_path: str
    counterpart_path: str
    language: str
    active_nav: str | None


class SyncError(RuntimeError):
    """Raised when configuration or marked HTML is unsafe to synchronize."""


def page_configs(root: Path) -> tuple[PageConfig, ...]:
    configs = []
    for route in load_localized_routes(root):
        for language in LANGUAGE_KEYS:
            counterpart = "en" if language == "fa_AF" else "fa_AF"
            configs.append(
                PageConfig(
                    route_id=route.id,
                    path=source_path_for_public_path(route.public_path(language)),
                    public_path=route.public_path(language),
                    counterpart_path=route.public_path(counterpart),
                    language=language,
                    active_nav=ACTIVE_NAV_BY_ROUTE.get(route.id),
                )
            )
    return tuple(configs)


def read_exact(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError as error:
        raise SyncError(f"missing required file: {path}") from error
    except UnicodeDecodeError as error:
        raise SyncError(f"file is not valid UTF-8: {path}") from error


def normalized_fragment(root: Path, relative_path: str) -> str:
    fragment = read_exact(root / relative_path)
    fragment = fragment.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    if not fragment.strip():
        raise SyncError(f"rendered fragment would be empty: {relative_path}")
    return fragment


def ensure_resolved(rendered: str, source_name: str) -> None:
    unresolved = sorted(set(UNRESOLVED_PLACEHOLDER.findall(rendered)))
    if unresolved:
        raise SyncError(
            f"unresolved placeholder(s) in {source_name}: {', '.join(unresolved)}"
        )
    if not rendered.strip():
        raise SyncError(f"rendered output would be empty: {source_name}")


def render_localized_head(config: PageConfig) -> str:
    canonical = f"https://salaam.center{config.public_path}"
    if config.language == "fa_AF":
        dari_path, english_path = config.public_path, config.counterpart_path
    else:
        dari_path, english_path = config.counterpart_path, config.public_path
    dari_url = f"https://salaam.center{dari_path}"
    english_url = f"https://salaam.center{english_path}"
    locale = "fa_AF" if config.language == "fa_AF" else "en_GB"
    alternate_locale = "en_GB" if config.language == "fa_AF" else "fa_AF"
    lines = [
        f'<meta property="og:locale" content="{locale}" />',
        f'<meta property="og:locale:alternate" content="{alternate_locale}" />',
        f'<link rel="canonical" href="{canonical}" />',
        f'<link rel="alternate" hreflang="fa-AF" href="{dari_url}" />',
        f'<link rel="alternate" hreflang="en" href="{english_url}" />',
        f'<link rel="alternate" hreflang="x-default" href="{dari_url}" />',
    ]
    if config.language == "fa_AF":
        lines.append(
            '<link rel="preload" href="/assets/fonts/vazirmatn/'
            'Vazirmatn-Variable.woff2" as="font" type="font/woff2" crossorigin />'
        )
    return "\n".join(lines)


def render_header(root: Path, config: PageConfig) -> str:
    relative_path = HEADER_FRAGMENTS[config.language]
    rendered = normalized_fragment(root, relative_path)
    for placeholder in NAV_PLACEHOLDERS.values():
        if rendered.count(placeholder) != 1:
            raise SyncError(
                f"Header fragment must contain exactly one {placeholder}: {relative_path}"
            )
    if rendered.count("{{LANG_SWITCH_HREF}}") != 1:
        raise SyncError(
            f"Header fragment must contain one language switch: {relative_path}"
        )
    for nav_key, placeholder in NAV_PLACEHOLDERS.items():
        attributes = ' class="nav__link"'
        if config.active_nav == nav_key:
            attributes = ' class="nav__link is-active"'
            if config.route_id == nav_key:
                attributes += ' aria-current="page"'
        rendered = rendered.replace(placeholder, attributes)
    rendered = rendered.replace("{{LANG_SWITCH_HREF}}", config.counterpart_path)
    ensure_resolved(rendered, relative_path)
    return rendered


def render_footer(root: Path, config: PageConfig) -> str:
    relative_path = FOOTER_FRAGMENTS[config.language]
    rendered = normalized_fragment(root, relative_path)
    if rendered.count("{{LANG_SWITCH_HREF}}") != 1:
        raise SyncError(
            f"Footer fragment must contain one language switch: {relative_path}"
        )
    rendered = rendered.replace("{{LANG_SWITCH_HREF}}", config.counterpart_path)
    ensure_resolved(rendered, relative_path)
    return rendered


def page_newline(source: str, page_path: str) -> str:
    if "\r\n" in source:
        return "\r\n"
    if "\n" in source:
        return "\n"
    raise SyncError(f"configured page has no detectable line endings: {page_path}")


def replace_marked_section(
    source: str,
    start_marker: str,
    end_marker: str,
    rendered: str,
    page_path: str,
    section_name: str,
) -> str:
    start_count = source.count(start_marker)
    end_count = source.count(end_marker)
    if start_count != 1 or end_count != 1:
        raise SyncError(
            f"{page_path}: expected exactly one {section_name} marker pair "
            f"(found {start_count} start, {end_count} end)"
        )
    start_index = source.index(start_marker)
    end_index = source.index(end_marker)
    if start_index >= end_index:
        raise SyncError(f"{page_path}: {section_name} markers are out of order")
    start_line = source.rfind("\n", 0, start_index) + 1
    end_line = source.rfind("\n", 0, end_index) + 1
    start_indent = source[start_line:start_index]
    end_indent = source[end_line:end_index]
    if start_indent.strip() or end_indent.strip() or start_indent != end_indent:
        raise SyncError(f"{page_path}: {section_name} marker indentation is invalid")
    start_line_end = source.find("\n", start_index + len(start_marker))
    if start_line_end == -1 or source[
        start_index + len(start_marker) : start_line_end
    ].strip():
        raise SyncError(f"{page_path}: {section_name} start marker must end its line")
    end_line_end = source.find("\n", end_index + len(end_marker))
    if end_line_end == -1:
        end_line_end = len(source)
    if source[end_index + len(end_marker) : end_line_end].strip():
        raise SyncError(f"{page_path}: {section_name} end marker must end its line")
    newline = page_newline(source, page_path)
    rendered_block = newline.join(
        start_indent + line if line else "" for line in rendered.split("\n")
    )
    replacement = (
        f"{start_indent}{start_marker}{newline}"
        f"{rendered_block}{newline}"
        f"{start_indent}{end_marker}"
    )
    return source[:start_line] + replacement + source[end_index + len(end_marker) :]


def validate_configuration(root: Path, configs: tuple[PageConfig, ...]) -> None:
    seen_paths = set()
    for config in configs:
        if config.language not in LANGUAGE_KEYS:
            raise SyncError(f"unsupported page language: {config.language}")
        if config.path in seen_paths:
            raise SyncError(f"configured page is duplicated: {config.path}")
        seen_paths.add(config.path)
        if not (root / config.path).is_file():
            raise SyncError(f"configured page is missing: {config.path}")
        if config.active_nav not in {None, *NAV_PLACEHOLDERS}:
            raise SyncError(f"unknown navigation key for {config.path}")


def expected_page(root: Path, config: PageConfig) -> str:
    source = read_exact(root / config.path)
    expected = replace_marked_section(
        source,
        HEAD_START,
        HEAD_END,
        render_localized_head(config),
        config.path,
        "localized Head",
    )
    expected = replace_marked_section(
        expected,
        HEADER_START,
        HEADER_END,
        render_header(root, config),
        config.path,
        "Header",
    )
    expected = replace_marked_section(
        expected,
        FOOTER_START,
        FOOTER_END,
        render_footer(root, config),
        config.path,
        "Footer",
    )
    unresolved = sorted(set(UNRESOLVED_PLACEHOLDER.findall(expected)))
    if unresolved:
        raise SyncError(
            f"{config.path}: unresolved placeholder(s): {', '.join(unresolved)}"
        )
    return expected


def synchronize(root: Path, write: bool) -> int:
    configs = page_configs(root)
    validate_configuration(root, configs)
    expected_pages = {}
    drifted = []
    for config in configs:
        original = read_exact(root / config.path)
        expected = expected_page(root, config)
        expected_pages[config.path] = expected
        if original != expected:
            drifted.append(config.path)
    if write:
        for relative_path in drifted:
            (root / relative_path).write_bytes(expected_pages[relative_path].encode("utf-8"))
        if drifted:
            print("Updated localized shared layout:")
            for relative_path in drifted:
                print(f"  - {relative_path}")
        else:
            print("Localized shared layout already synchronized.")
        return 0
    if drifted:
        print("Localized shared layout drift detected:", file=sys.stderr)
        for relative_path in drifted:
            print(f"  - {relative_path}", file=sys.stderr)
        return 1
    print(f"Shared layout synchronized across {len(configs)} page(s).")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize bilingual Head, Header and Footer markup."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write canonical shared markup")
    mode.add_argument("--check", action="store_true", help="report drift without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return synchronize(REPO_ROOT, write=args.write)
    except (RouteManifestError, SyncError) as error:
        print(f"Shared layout synchronization failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
