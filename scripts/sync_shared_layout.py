"""Synchronize committed Header and Footer markup across complete public pages."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

HEADER_START = "<!-- SHARED HEADER:START -->"
HEADER_END = "<!-- SHARED HEADER:END -->"
FOOTER_START = "<!-- SHARED FOOTER:START -->"
FOOTER_END = "<!-- SHARED FOOTER:END -->"

HEADER_FRAGMENTS = {
    "standard": "partials/header.html",
}
FOOTER_FRAGMENTS = {
    "standard": "partials/footer.html",
}

NAV_PLACEHOLDERS = {
    "home": "{{NAV_HOME_CURRENT}}",
    "our_approach": "{{NAV_OUR_APPROACH_CURRENT}}",
    "programs": "{{NAV_PROGRAMS_CURRENT}}",
    "how_it_works": "{{NAV_HOW_IT_WORKS_CURRENT}}",
    "teachers": "{{NAV_TEACHERS_CURRENT}}",
    "about": "{{NAV_ABOUT_CURRENT}}",
    "pricing": "{{NAV_PRICING_CURRENT}}",
}
NAV_CURRENT_PATHS = {
    "home": "index.html",
    "our_approach": "our-approach/index.html",
    "programs": "programs/index.html",
    "teachers": "teachers/index.html",
    "how_it_works": "how-it-works/index.html",
    "pricing": "pricing/index.html",
    "about": "about/index.html",
}
VALID_NAV_KEYS = {None, *NAV_PLACEHOLDERS}
UNRESOLVED_PLACEHOLDER = re.compile(r"{{[^{}]+}}")


@dataclass(frozen=True)
class PageConfig:
    path: str
    active_nav: str | None
    header_variant: str = "standard"
    footer_variant: str = "standard"
    sync_header: bool = True
    sync_footer: bool = True


PAGE_CONFIGS = (
    PageConfig("404.html", None),
    PageConfig("index.html", "home"),
    PageConfig("our-approach/index.html", "our_approach"),
    PageConfig("programs/index.html", "programs"),
    PageConfig("programs/quran/index.html", "programs"),
    PageConfig("programs/dari-persian/index.html", "programs"),
    PageConfig(
        "programs/afghan-culture-islamic-ethics/index.html",
        "programs",
    ),
    PageConfig("teachers/index.html", "teachers"),
    PageConfig("how-it-works/index.html", "how_it_works"),
    PageConfig("pricing/index.html", "pricing"),
    PageConfig("about/index.html", "about"),
    PageConfig("book-trial/index.html", None),
    PageConfig("contact/index.html", None),
    PageConfig("privacy-policy/index.html", None),
    PageConfig("terms/index.html", None),
    PageConfig("success/index.html", None),
)


class SyncError(RuntimeError):
    """Raised when configuration or marked HTML is unsafe to synchronize."""


def read_exact(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError as error:
        raise SyncError(f"missing required file: {path}") from error
    except UnicodeDecodeError as error:
        raise SyncError(f"file is not valid UTF-8: {path}") from error


def validate_configuration(root: Path) -> None:
    seen_paths = set()
    for config in PAGE_CONFIGS:
        relative = Path(config.path)
        if relative.is_absolute() or ".." in relative.parts:
            raise SyncError(f"configured page path is not repository-relative: {config.path}")
        if config.path in seen_paths:
            raise SyncError(f"configured page is duplicated: {config.path}")
        seen_paths.add(config.path)

        if config.active_nav not in VALID_NAV_KEYS:
            raise SyncError(
                f"unknown navigation key for {config.path}: {config.active_nav!r}"
            )
        if config.header_variant not in HEADER_FRAGMENTS:
            raise SyncError(
                f"unknown Header variant for {config.path}: {config.header_variant!r}"
            )
        if config.footer_variant not in FOOTER_FRAGMENTS:
            raise SyncError(
                f"unknown Footer variant for {config.path}: {config.footer_variant!r}"
            )
        if not config.sync_header and not config.sync_footer:
            raise SyncError(f"configured page has synchronization disabled: {config.path}")
        if not (root / relative).is_file():
            raise SyncError(f"configured page is missing: {config.path}")


def normalized_fragment(root: Path, relative_path: str) -> str:
    fragment = read_exact(root / relative_path)
    fragment = fragment.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    if not fragment.strip():
        raise SyncError(f"rendered fragment would be empty: {relative_path}")
    return fragment


def render_header(root: Path, config: PageConfig) -> str:
    relative_path = HEADER_FRAGMENTS[config.header_variant]
    rendered = normalized_fragment(root, relative_path)

    for placeholder in NAV_PLACEHOLDERS.values():
        if rendered.count(placeholder) != 1:
            raise SyncError(
                f"Header fragment must contain exactly one {placeholder}: {relative_path}"
            )

    for nav_key, placeholder in NAV_PLACEHOLDERS.items():
        attributes = ' class="nav__link"'
        if config.active_nav == nav_key:
            attributes = ' class="nav__link is-active"'
            if NAV_CURRENT_PATHS.get(nav_key) == config.path:
                attributes += ' aria-current="page"'
        rendered = rendered.replace(placeholder, attributes)

    ensure_resolved(rendered, relative_path)
    return rendered


def render_footer(root: Path, config: PageConfig) -> str:
    relative_path = FOOTER_FRAGMENTS[config.footer_variant]
    rendered = normalized_fragment(root, relative_path)
    ensure_resolved(rendered, relative_path)
    return rendered


def ensure_resolved(rendered: str, source_name: str) -> None:
    unresolved = sorted(set(UNRESOLVED_PLACEHOLDER.findall(rendered)))
    if unresolved:
        raise SyncError(
            f"unresolved placeholder(s) in {source_name}: {', '.join(unresolved)}"
        )
    if not rendered.strip():
        raise SyncError(f"rendered output would be empty: {source_name}")


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
    if start_indent.strip() or end_indent.strip():
        raise SyncError(f"{page_path}: {section_name} markers must be on their own lines")
    if start_indent != end_indent:
        raise SyncError(f"{page_path}: {section_name} marker indentation does not match")

    start_line_end = source.find("\n", start_index + len(start_marker))
    if start_line_end == -1 or source[start_index + len(start_marker):start_line_end].strip():
        raise SyncError(f"{page_path}: {section_name} start marker must end its line")

    end_line_end = source.find("\n", end_index + len(end_marker))
    if end_line_end == -1:
        end_line_end = len(source)
    if source[end_index + len(end_marker):end_line_end].strip():
        raise SyncError(f"{page_path}: {section_name} end marker must end its line")

    newline = page_newline(source, page_path)
    rendered_lines = rendered.split("\n")
    rendered_block = newline.join(
        start_indent + line if line else "" for line in rendered_lines
    )
    replacement = (
        f"{start_indent}{start_marker}{newline}"
        f"{rendered_block}{newline}"
        f"{start_indent}{end_marker}"
    )
    return source[:start_line] + replacement + source[end_index + len(end_marker):]


def expected_page(root: Path, config: PageConfig) -> str:
    page_path = root / config.path
    source = read_exact(page_path)
    expected = source

    if config.sync_header:
        expected = replace_marked_section(
            expected,
            HEADER_START,
            HEADER_END,
            render_header(root, config),
            config.path,
            "Header",
        )
    if config.sync_footer:
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
    validate_configuration(root)

    expected_pages = {}
    drifted = []
    for config in PAGE_CONFIGS:
        original = read_exact(root / config.path)
        expected = expected_page(root, config)
        expected_pages[config.path] = expected
        if original != expected:
            drifted.append(config.path)

    if write:
        for relative_path in drifted:
            (root / relative_path).write_bytes(expected_pages[relative_path].encode("utf-8"))
        if drifted:
            print("Updated shared layout:")
            for relative_path in drifted:
                print(f"  - {relative_path}")
        else:
            print("Shared layout already synchronized.")
        return 0

    if drifted:
        print("Shared layout drift detected:", file=sys.stderr)
        for relative_path in drifted:
            print(f"  - {relative_path}", file=sys.stderr)
        return 1

    print(f"Shared layout synchronized across {len(PAGE_CONFIGS)} page(s).")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize committed Header and Footer markup."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write canonical shared markup")
    mode.add_argument("--check", action="store_true", help="report drift without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return synchronize(REPO_ROOT, write=args.write)
    except SyncError as error:
        print(f"Shared layout synchronization failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
