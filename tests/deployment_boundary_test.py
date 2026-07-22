from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import urlsplit

from scripts.deployment_boundary import (
    ERROR_PAGE_SOURCES,
    ERROR_SENTINEL_PATHS,
    PAGE_ROUTE_SPECS,
    PUBLIC_PAGE_SOURCES,
    PUBLIC_RUNTIME_ASSETS as RUNTIME_ASSETS,
    backing_relative,
    expected_redirect_rules,
    path_is_private,
    public_backing_pairs,
)


ROOT = Path(__file__).resolve().parents[1]
REDIRECTS = ROOT / "_redirects"
SYNC_SCRIPT = ROOT / "scripts/sync_public_runtime.py"

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
        if source == path or (
            source.endswith("*") and path.startswith(source.removesuffix("*"))
        ):
            return rule
    return None


class DeploymentBoundaryTests(unittest.TestCase):
    def test_cloudflare_public_route_allowlist_is_exact_and_function_free(self):
        self.assertEqual(expected_redirect_rules(), actual_rules())
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
            [
                "/en/* /en/__salaam_not_found__ 200",
                "/* /__salaam_not_found__ 200",
            ],
            [rule for rule in rules if "*" in rule.split()[0]],
        )
        for error_page_source in ERROR_PAGE_SOURCES:
            self.assertTrue((ROOT / error_page_source).is_file())
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
            "/en/404.html",
            "/en/future-unreviewed-file.txt",
            "/future-unreviewed-file.txt",
        ):
            request_path = path.split("?", 1)[0]
            expected_catchall = (
                "/en/* /en/__salaam_not_found__ 200"
                if request_path.startswith("/en/")
                else "/* /__salaam_not_found__ 200"
            )
            with self.subTest(path=path):
                self.assertEqual(expected_catchall, first_matching_rule(request_path))

    def test_all_local_page_and_asset_references_are_allowlisted(self):
        public_routes = {route for _, route, _ in PAGE_ROUTE_SPECS}
        public_routes.update("/" + relative for relative in RUNTIME_ASSETS)
        error_routes = {"/404.html", "/en/404.html"}
        for source in PUBLIC_PAGE_SOURCES:
            page = (ROOT / source).read_text(encoding="utf-8")
            for match in re.finditer(r"(?:href|src)=['\"]([^'\"]+)['\"]", page):
                parsed = urlsplit(match.group(1))
                if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
                    continue
                self.assertIn(
                    parsed.path,
                    public_routes | error_routes,
                    f"{source}: {match.group(1)}",
                )
                if parsed.path in error_routes:
                    expected_catchall = (
                        "/en/* /en/__salaam_not_found__ 200"
                        if parsed.path.startswith("/en/")
                        else "/* /__salaam_not_found__ 200"
                    )
                    self.assertEqual(expected_catchall, first_matching_rule(parsed.path))
                else:
                    self.assertNotIn("*", first_matching_rule(parsed.path).split()[0])

    def test_every_current_deployment_file_is_reviewed_source_backing_or_private(self):
        public_sources = set(PUBLIC_PAGE_SOURCES) | set(RUNTIME_ASSETS)
        backing_files = {backing for _, backing in public_backing_pairs()}
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
                    normalized in allowed or path_is_private(normalized),
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
        self.assertIn("38 public runtime artifact(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
