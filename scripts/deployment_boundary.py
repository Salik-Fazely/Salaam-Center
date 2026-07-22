"""Validate the fail-closed static Cloudflare Pages deployment surface."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence


PUBLIC_BACKING_ROOT = "site-runtime"
PAGE_ROUTE_SPECS = (
    ("index.html", "/", "/site-runtime/home/"),
    ("our-approach/index.html", "/our-approach/", "/site-runtime/our-approach/"),
    ("programs/index.html", "/programs/", "/site-runtime/programs/"),
    ("programs/quran/index.html", "/programs/quran/", "/site-runtime/programs/quran/"),
    (
        "programs/dari-persian/index.html",
        "/programs/dari-persian/",
        "/site-runtime/programs/dari-persian/",
    ),
    (
        "programs/afghan-culture-islamic-ethics/index.html",
        "/programs/afghan-culture-islamic-ethics/",
        "/site-runtime/programs/afghan-culture-islamic-ethics/",
    ),
    ("teachers/index.html", "/teachers/", "/site-runtime/teachers/"),
    ("how-it-works/index.html", "/how-it-works/", "/site-runtime/how-it-works/"),
    ("pricing/index.html", "/pricing/", "/site-runtime/pricing/"),
    ("about/index.html", "/about/", "/site-runtime/about/"),
    ("book-trial/index.html", "/book-trial/", "/site-runtime/book-trial/"),
    ("contact/index.html", "/contact/", "/site-runtime/contact/"),
    ("privacy-policy/index.html", "/privacy-policy/", "/site-runtime/privacy-policy/"),
    ("terms/index.html", "/terms/", "/site-runtime/terms/"),
    ("success/index.html", "/success/", "/site-runtime/success/"),
)
PUBLIC_ROUTED_PAGE_SOURCES = tuple(source for source, _, _ in PAGE_ROUTE_SPECS)
ERROR_PAGE_SOURCE = "404.html"
ERROR_SENTINEL_PATHS = (
    "__salaam_not_found__",
    "__salaam_not_found__.html",
    "__salaam_not_found__/index.html",
)
PUBLIC_PAGE_SOURCES = (*PUBLIC_ROUTED_PAGE_SOURCES, ERROR_PAGE_SOURCE)
PUBLIC_RUNTIME_ASSETS = (
    "robots.txt",
    "sitemap.xml",
    "assets/css/styles.css",
    "assets/js/main.js",
    "assets/js/trial-form.js",
    "assets/logo/salaam-center-favicon.svg",
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


def backing_relative(source: str) -> str:
    """Return the distinct committed backing path for a reviewed public source."""
    if source == "index.html":
        return f"{PUBLIC_BACKING_ROOT}/home/index.html"
    return f"{PUBLIC_BACKING_ROOT}/{source}"


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
    if wildcard_rules != ["/* /__salaam_not_found__ 200"]:
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

    if not (root / ERROR_PAGE_SOURCE).is_file():
        errors.append(f"Cloudflare Pages error template is missing: {ERROR_PAGE_SOURCE}")
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
