"""Validate the fail-closed static Cloudflare Pages deployment surface."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

try:
    from .localized_routes import (
        LANGUAGE_KEYS,
        load_localized_routes,
        source_path_for_public_path,
    )
except ImportError:
    from localized_routes import (
        LANGUAGE_KEYS,
        load_localized_routes,
        source_path_for_public_path,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BACKING_ROOT = "site-runtime"


def backing_relative(source: str) -> str:
    """Return the distinct committed backing path for a reviewed public source."""
    if source == "index.html":
        return f"{PUBLIC_BACKING_ROOT}/home/index.html"
    return f"{PUBLIC_BACKING_ROOT}/{source}"


def _page_route_specs() -> tuple[tuple[str, str, str], ...]:
    specs = []
    for localized_route in load_localized_routes(REPO_ROOT):
        if localized_route.status == "not_found":
            continue
        for language in LANGUAGE_KEYS:
            public_path = localized_route.public_path(language)
            source = source_path_for_public_path(public_path)
            backing_route = "/" + backing_relative(source)
            if backing_route.endswith("/index.html"):
                backing_route = backing_route[: -len("index.html")]
            specs.append((source, public_path, backing_route))
    return tuple(specs)


PAGE_ROUTE_SPECS = _page_route_specs()
PUBLIC_ROUTED_PAGE_SOURCES = tuple(source for source, _, _ in PAGE_ROUTE_SPECS)
ERROR_PAGE_SOURCE = "404.html"
ERROR_PAGE_SOURCES = (ERROR_PAGE_SOURCE, "en/404.html")
ERROR_SENTINEL_PATHS = (
    "__salaam_not_found__",
    "__salaam_not_found__.html",
    "__salaam_not_found__/index.html",
    "en/__salaam_not_found__",
    "en/__salaam_not_found__.html",
    "en/__salaam_not_found__/index.html",
)
PUBLIC_PAGE_SOURCES = (*PUBLIC_ROUTED_PAGE_SOURCES, *ERROR_PAGE_SOURCES)
PUBLIC_RUNTIME_ASSETS = (
    "robots.txt",
    "sitemap.xml",
    "assets/css/styles.css",
    "assets/js/main.js",
    "assets/js/trial-form.js",
    "assets/logo/salaam-center-favicon.svg",
    "assets/fonts/vazirmatn/Vazirmatn-Variable.woff2",
    "assets/fonts/vazirmatn/OFL.txt",
)
PRIVATE_EXACT_PATHS = (
    "/SALAM-CENTER-APPROVED-FACTS.md",
    "/MIGRATION-SOURCE.md",
    "/CNAME",
)
PRIVATE_PREFIXES = (
    "/.agents",
    "/.git",
    "/apps-script",
    "/blog",
    "/config",
    "/docs",
    "/partials",
    "/scripts",
    "/tests",
    "/assets/Characters",
    "/assets/blog",
    "/assets/images",
)
_LOCAL_ONLY_PARTS = frozenset({".git", ".wrangler", "__pycache__"})


def public_backing_pairs() -> tuple[tuple[str, str], ...]:
    sources = (*PUBLIC_ROUTED_PAGE_SOURCES, *PUBLIC_RUNTIME_ASSETS)
    return tuple((source, backing_relative(source)) for source in sources)


def expected_redirect_rules() -> tuple[str, ...]:
    """Return the exact reviewed first-match allowlist and final catchall."""
    rules = [f"{route} {backing} 200" for _, route, backing in PAGE_ROUTE_SPECS]
    for source, route, _ in PAGE_ROUTE_SPECS:
        if route == "/":
            rules.append("/index.html / 308")
        else:
            rules.extend(
                (
                    f"{route.rstrip('/')} {route} 308",
                    f"/{source} {route} 308",
                )
            )
    rules.extend(
        f"/{source} /{backing_relative(source)} 200"
        for source in PUBLIC_RUNTIME_ASSETS
    )
    rules.append("/en/* /en/__salaam_not_found__ 200")
    rules.append("/* /__salaam_not_found__ 200")
    return tuple(rules)


def redirect_rules(path: Path) -> tuple[str, ...]:
    source = path.read_text(encoding="utf-8")
    return tuple(
        line.strip()
        for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def path_is_private(relative_path: str) -> bool:
    route = "/" + Path(relative_path).as_posix().lstrip("/")
    return route in PRIVATE_EXACT_PATHS or any(
        route == prefix or route.startswith(prefix + "/")
        for prefix in PRIVATE_PREFIXES
    )


def _deployment_candidates(root: Path) -> Iterable[str]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in _LOCAL_ONLY_PARTS for part in relative.parts):
            continue
        if path.suffix.casefold() == ".pyc":
            continue
        yield relative.as_posix()


def deployment_boundary_errors(
    root: Path,
    public_html_paths: Sequence[str],
) -> tuple[str, ...]:
    root = root.resolve()
    errors: list[str] = []
    for forbidden in ("_worker.js", "_routes.json", "functions"):
        if (root / forbidden).exists():
            errors.append(f"forbidden Pages Functions surface exists: {forbidden}")

    expected_html = set(PUBLIC_PAGE_SOURCES)
    supplied_html = {
        Path(path).as_posix().lstrip("./") for path in public_html_paths
    }
    if supplied_html != expected_html:
        errors.append("public HTML manifest does not exactly match the reviewed route allowlist")

    redirects = root / "_redirects"
    if not redirects.is_file():
        return (*errors, "root _redirects public-route allowlist is missing")
    try:
        actual = redirect_rules(redirects)
    except (OSError, UnicodeError) as error:
        return (*errors, f"public-route allowlist cannot be validated: {error}")
    expected = expected_redirect_rules()
    if actual != expected:
        errors.append("root _redirects does not exactly match the reviewed public-route allowlist")
    if not actual or actual[-1] != "/* /__salaam_not_found__ 200":
        errors.append("public-route allowlist does not end with the reviewed catchall")
    wildcard_rules = [rule for rule in actual if "*" in rule.split()[0]]
    if wildcard_rules != [
        "/en/* /en/__salaam_not_found__ 200",
        "/* /__salaam_not_found__ 200",
    ]:
        errors.append("public-route allowlist contains an unreviewed wildcard rule")

    public_sources = set(PUBLIC_PAGE_SOURCES) | set(PUBLIC_RUNTIME_ASSETS)
    backing_files = {backing for _, backing in public_backing_pairs()}
    for source, backing in public_backing_pairs():
        source_path = root / source
        backing_path = root / backing
        if not source_path.is_file():
            errors.append(f"reviewed public source is missing: {source}")
            continue
        if not backing_path.is_file():
            errors.append(f"reviewed public backing artifact is missing: {backing}")
            continue
        try:
            if source_path.read_bytes() != backing_path.read_bytes():
                errors.append(f"public runtime backing artifact is out of sync: {backing}")
        except OSError as error:
            errors.append(f"public runtime backing artifact cannot be validated: {error}")

    for error_page_source in ERROR_PAGE_SOURCES:
        if not (root / error_page_source).is_file():
            errors.append(
                f"Cloudflare Pages error template is missing: {error_page_source}"
            )
    for sentinel in ERROR_SENTINEL_PATHS:
        if (root / sentinel).exists():
            errors.append(
                f"catchall target variant must remain absent so Cloudflare returns HTTP 404: {sentinel}"
            )

    reviewed_files = public_sources | backing_files | {"_redirects"}
    for relative in sorted(_deployment_candidates(root)):
        if relative in reviewed_files or path_is_private(relative):
            continue
        errors.append(f"unclassified repository file is outside the reviewed source set: {relative}")

    return tuple(dict.fromkeys(errors))


def deployment_boundary_is_safe(
    root: Path,
    public_html_paths: Sequence[str],
) -> bool:
    return not deployment_boundary_errors(root, public_html_paths)
