from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
REDIRECTS = ROOT / "_redirects"
SYNC_SCRIPT = ROOT / "scripts/sync_public_runtime.py"

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
ERROR_PAGE_SOURCE = "404.html"
ERROR_SENTINEL_PATHS = (
    "__salaam_not_found__",
    "__salaam_not_found__.html",
    "__salaam_not_found__/index.html",
)
RUNTIME_ASSETS = (
    "robots.txt",
    "sitemap.xml",
    "assets/css/styles.css",
    "assets/js/main.js",
    "assets/js/trial-form.js",
    "assets/logo/salaam-center-favicon.svg",
)
PRIVATE_EXACT = (
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


def backing_relative(source: str) -> str:
    if source == "index.html":
        return "site-runtime/home/index.html"
    return f"site-runtime/{source}"


def expected_rules() -> tuple[str, ...]:
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
        f"/{source} /site-runtime/{source} 200" for source in RUNTIME_ASSETS
    )
    rules.append("/* /__salaam_not_found__ 200")
    return tuple(rules)


def actual_rules() -> tuple[str, ...]:
    source = REDIRECTS.read_text(encoding="utf-8")
    return tuple(
        line.strip()
        for line in source.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def first_matching_rule(path: str) -> str | None:
    for rule in actual_rules():
        source = rule.split()[0]
        if source == path or (source == "/*" and path.startswith("/")):
            return rule
    return None


def private_source(path: str) -> bool:
    return path in PRIVATE_EXACT or any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in PRIVATE_PREFIXES
    )


class DeploymentBoundaryTests(unittest.TestCase):
    def test_cloudflare_public_route_allowlist_is_exact_and_function_free(self):
        self.assertEqual(expected_rules(), actual_rules())
        self.assertFalse((ROOT / "_worker.js").exists())
        self.assertFalse((ROOT / "functions").exists())
        self.assertFalse((ROOT / "_routes.json").exists())

    def test_public_routes_proxy_only_to_distinct_reviewed_backing_files(self):
        for source, route, backing in PAGE_ROUTE_SPECS:
            with self.subTest(route=route):
                self.assertEqual(f"{route} {backing} 200", first_matching_rule(route))
                self.assertNotEqual(route, backing)
                mirror = ROOT / backing_relative(source)
                self.assertTrue(mirror.is_file(), mirror)
                self.assertEqual((ROOT / source).read_bytes(), mirror.read_bytes(), source)

        for source in RUNTIME_ASSETS:
            route = f"/{source}"
            backing = f"/site-runtime/{source}"
            with self.subTest(route=route):
                self.assertEqual(f"{route} {backing} 200", first_matching_rule(route))
                mirror = ROOT / backing.lstrip("/")
                self.assertTrue(mirror.is_file(), mirror)
                self.assertEqual((ROOT / source).read_bytes(), mirror.read_bytes(), source)

    def test_final_catchall_blocks_unknown_and_normalization_bypass_paths(self):
        rules = actual_rules()
        self.assertEqual("/* /__salaam_not_found__ 200", rules[-1])
        self.assertEqual(
            ["/* /__salaam_not_found__ 200"],
            [rule for rule in rules if "*" in rule.split()[0]],
        )
        self.assertTrue((ROOT / ERROR_PAGE_SOURCE).is_file())
        for sentinel in ERROR_SENTINEL_PATHS:
            self.assertFalse((ROOT / sentinel).exists(), sentinel)
        for path in (
            "/SALAM-CENTER-APPROVED-FACTS.md",
            "/docs",
            "/docs/COMMERCIAL-AND-ENROLMENT.md?x=1",
            "/DOCS/COMMERCIAL-AND-ENROLMENT.md",
            "/DoCs/COMMERCIAL-AND-ENROLMENT.md",
            "/docs%2FCOMMERCIAL-AND-ENROLMENT.md",
            "/docs%252FCOMMERCIAL-AND-ENROLMENT.md",
            "/docs//COMMERCIAL-AND-ENROLMENT.md",
            "/config/launch-readiness.json",
            "/scripts/deployment_boundary.py",
            "/tests/teacher_economics_test.py",
            "/assets/Characters/character-usage-guide.txt",
            "/site-runtime/home/index.html",
            "/404.html",
            "/404",
            "/future-unreviewed-file.txt",
        ):
            request_path = path.split("?", 1)[0]
            with self.subTest(path=path):
                self.assertEqual(
                    "/* /__salaam_not_found__ 200",
                    first_matching_rule(request_path),
                )

    def test_all_local_page_and_asset_references_are_allowlisted(self):
        public_routes = {route for _, route, _ in PAGE_ROUTE_SPECS}
        public_routes.update("/" + relative for relative in RUNTIME_ASSETS)
        page_sources = tuple(source for source, _, _ in PAGE_ROUTE_SPECS) + (ERROR_PAGE_SOURCE,)
        for source in page_sources:
            page = (ROOT / source).read_text(encoding="utf-8")
            for match in re.finditer(r"(?:href|src)=['\"]([^'\"]+)['\"]", page):
                parsed = urlsplit(match.group(1))
                if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
                    continue
                self.assertIn(parsed.path, public_routes, f"{source}: {match.group(1)}")
                self.assertNotEqual(
                    "/* /__salaam_not_found__ 200",
                    first_matching_rule(parsed.path),
                )

    def test_every_current_deployment_file_is_reviewed_source_backing_or_private(self):
        public_sources = (
            {source for source, _, _ in PAGE_ROUTE_SPECS}
            | set(RUNTIME_ASSETS)
            | {ERROR_PAGE_SOURCE}
        )
        backing_files = {backing_relative(source) for source in public_sources}
        backing_files.remove(backing_relative(ERROR_PAGE_SOURCE))
        allowed = public_sources | backing_files | {"_redirects"}
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in {".git", ".wrangler", "__pycache__"} for part in relative.parts):
                continue
            if path.suffix.casefold() == ".pyc":
                continue
            normalized = relative.as_posix()
            with self.subTest(path=normalized):
                self.assertTrue(
                    normalized in allowed or private_source("/" + normalized),
                    f"unclassified deployable file: {normalized}",
                )

    def test_public_runtime_synchronizer_reports_no_drift(self):
        self.assertTrue(SYNC_SCRIPT.is_file())
        result = subprocess.run(
            [sys.executable, "-B", str(SYNC_SCRIPT), "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("21 public runtime artifact(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
