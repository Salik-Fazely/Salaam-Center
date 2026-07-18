import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/launch-readiness.json"
PREFLIGHT = ROOT / "scripts/launch_preflight.py"
PUBLIC_PAGES = (
    "index.html", "our-approach/index.html", "programs/index.html",
    "programs/quran/index.html", "programs/dari-persian/index.html",
    "programs/afghan-culture-islamic-ethics/index.html", "teachers/index.html",
    "how-it-works/index.html", "pricing/index.html", "about/index.html",
    "book-trial/index.html", "contact/index.html", "privacy-policy/index.html",
    "terms/index.html", "success/index.html", "404.html",
)
ROUTES = {
    "index.html": "/", "404.html": "/404.html",
    **{path: f"/{path.removesuffix('index.html')}" for path in PUBLIC_PAGES
       if path not in {"index.html", "404.html"}},
}
SITEMAP_ROUTES = {route for page, route in ROUTES.items()
                  if page not in {"success/index.html", "404.html"}}


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ""
        self.metas = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.metas.append(data)
        elif tag == "link":
            self.links.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def parse_head(relative):
    parser = HeadParser()
    parser.feed((ROOT / relative).read_text(encoding="utf-8"))
    return parser


class LaunchConfigurationTests(unittest.TestCase):
    def test_prelaunch_configuration_is_strict_and_inactive(self):
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual("prelaunch", data["site_mode"])
        self.assertEqual("https://salaam.center", data["production_origin"])
        self.assertEqual("hello@salaam.center", data["contact_email"])
        self.assertEqual("formspree", data["booking_provider"])
        self.assertEqual("", data["booking_endpoint"])
        self.assertEqual("none", data["analytics_mode"])
        for key in (
            "contact_email_verified", "booking_endpoint_verified",
            "formspree_domain_restriction_confirmed", "privacy_policy_final_approved",
            "terms_final_approved", "domain_verified_with_github",
            "github_pages_enabled", "dns_configured", "https_confirmed",
            "search_console_enabled",
        ):
            self.assertIs(data[key], False, key)
        self.assertNotRegex(CONFIG.read_text(encoding="utf-8"), r"(?i)(api[_-]?key|token|password|secret)")


class PreflightTests(unittest.TestCase):
    def run_preflight(self, mode, config=None):
        command = [sys.executable, str(PREFLIGHT), "--mode", mode]
        if config:
            command += ["--config", str(config)]
        return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)

    def test_prelaunch_passes_without_modifying_repository(self):
        before = {p: p.stat().st_mtime_ns for p in ROOT.rglob("*") if p.is_file()}
        result = self.run_preflight("prelaunch")
        after = {p: p.stat().st_mtime_ns for p in ROOT.rglob("*") if p.is_file()}
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("PASS: prelaunch readiness", result.stdout)
        self.assertEqual(before, after)

    def test_production_reports_expected_external_and_legal_blockers(self):
        result = self.run_preflight("production")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("EXPECTED BLOCKED PRODUCTION STATE", result.stdout)
        failures = {
            line.removeprefix("FAIL: ")
            for line in result.stdout.splitlines()
            if line.startswith("FAIL: ")
        }
        self.assertEqual({
            "site_mode is production",
            "contact_email_verified is true",
            "booking_endpoint is a verified HTTPS Formspree form-ID URL",
            "booking_endpoint_verified is true",
            "formspree_domain_restriction_confirmed is true",
            "legal_controller_name is present",
            "legal_controller_address is present",
            "privacy_policy_final_approved is true",
            "terms_final_approved is true",
            "domain_verified_with_github is true",
            "github_pages_enabled is true",
            "dns_configured is true",
            "https_confirmed is true",
            "noindex, nofollow removed from production pages",
            "robots.txt allows intended crawling",
            "no placeholder strings remain",
            "active booking form",
            "CNAME contains only salaam.center",
        }, failures)

    def test_invalid_json_and_unknown_mode_fail_safely(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            result = self.run_preflight("prelaunch", bad)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("invalid JSON", result.stdout + result.stderr)
        result = self.run_preflight("staging")
        self.assertNotEqual(0, result.returncode)

    def test_invalid_formspree_endpoints_are_explicit_production_failures(self):
        base = json.loads(CONFIG.read_text(encoding="utf-8"))
        for endpoint in (
            "https://formspree.io/f/FORM_ID",
            "https://example.com/f/abc123",
            "http://formspree.io/f/abc123",
            "https://formspree.io/hello@salaam.center",
        ):
            with self.subTest(endpoint=endpoint), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / "config.json"
                config.write_text(json.dumps({**base, "site_mode": "production", "booking_endpoint": endpoint}), encoding="utf-8")
                result = self.run_preflight("production", config)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("booking_endpoint", result.stdout)

    def test_prelaunch_rejects_every_claimed_activation_flag(self):
        base = json.loads(CONFIG.read_text(encoding="utf-8"))
        flags = (
            "contact_email_verified", "booking_endpoint_verified",
            "formspree_domain_restriction_confirmed", "privacy_policy_final_approved",
            "terms_final_approved", "domain_verified_with_github",
            "github_pages_enabled", "dns_configured", "https_confirmed",
            "search_console_enabled",
        )
        for flag in flags:
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / "config.json"
                config.write_text(json.dumps({**base, flag: True}), encoding="utf-8")
                result = self.run_preflight("prelaunch", config)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(flag, result.stdout)

    def test_a_complete_future_production_state_is_logically_passable(self):
        spec = importlib.util.spec_from_file_location("launch_preflight_under_test", PREFLIGHT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        endpoint = "https://formspree.io/f/abc123"
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config.update({
            "site_mode": "production",
            "contact_email_verified": True,
            "booking_endpoint": endpoint,
            "booking_endpoint_verified": True,
            "formspree_domain_restriction_confirmed": True,
            "legal_controller_name": "Approved Operator",
            "legal_controller_address": "Approved disclosure address",
            "privacy_policy_final_approved": True,
            "terms_final_approved": True,
            "domain_verified_with_github": True,
            "github_pages_enabled": True,
            "dns_configured": True,
            "https_confirmed": True,
        })
        bases = {
            page: f'<link rel="canonical" href="{module.PRODUCTION_ORIGIN + module.ROUTES[page]}">'
            for page in PUBLIC_PAGES
        }
        source = dict(bases)
        source["teachers/index.html"] += " ".join(module.PROTECTED_NAMES + module.PROTECTED_VIDEO_IDS)
        source["pricing/index.html"] += " ".join(module.APPROVED_PRICES)
        source["book-trial/index.html"] = (
            bases["book-trial/index.html"]
            + f'<form data-endpoint="{endpoint}" data-endpoint-verified="true">'
            + '<button type="submit">Request</button></form>'
        )
        protected_success = (
            bases["success/index.html"]
            + '<div data-success-state="direct"></div>'
            + '<div data-success-state="confirmed" hidden></div>'
        )
        source["success/index.html"] = protected_success

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets/js").mkdir(parents=True)
            (root / "robots.txt").write_text(
                "User-agent: *\nAllow: /\nSitemap: https://salaam.center/sitemap.xml\n",
                encoding="utf-8",
            )
            sitemap_entries = "".join(f"<url><loc>{url}</loc></url>" for url in sorted(module.SITEMAP_URLS))
            sitemap_path = root / "sitemap.xml"
            sitemap_path.write_text(
                f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sitemap_entries}</urlset>',
                encoding="utf-8",
            )
            protected_script = (
                "sessionStorage.getItem(markerKey); sessionStorage.removeItem(markerKey); "
                "if (marker.confirmed !== true) return; "
                "if (!response.ok || payload.ok !== true) throw new Error(); "
                "sessionStorage.setItem(markerKey, JSON.stringify({ confirmed: true, at: Date.now() })); "
                'window.location.assign("/success/");'
            )
            script_path = root / "assets/js/trial-form.js"
            script_path.write_text(protected_script, encoding="utf-8")
            (root / "CNAME").write_text("salaam.center\n", encoding="utf-8")
            module.ROOT = root
            result = module.Result()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.production(config, source, result)
            self.assertEqual([], result.failures, output.getvalue())
            self.assertIn("PASS: production readiness", output.getvalue())

            source["success/index.html"] = bases["success/index.html"] + '<div data-success-state="confirmed"></div>'
            script_path.write_text("sessionStorage.setItem('confirmed', 'true');", encoding="utf-8")
            unprotected = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, unprotected)
            self.assertIn("success flow requires confirmed submission", unprotected.failures)

            source["success/index.html"] = protected_success
            source["contact/index.html"] += " Mailbox verification remains pending."
            script_path.write_text(protected_script, encoding="utf-8")
            stale_copy = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, stale_copy)
            self.assertIn("no placeholder strings remain", stale_copy.failures)

            source["contact/index.html"] = bases["contact/index.html"]
            placeholder_legal = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production({**config, "legal_controller_name": "TBD"}, source, placeholder_legal)
            self.assertIn("no placeholder strings remain", placeholder_legal.failures)

            sitemap_path.write_text(f'<?xml version="1.0"?><urlset>{sitemap_entries}</urlset>', encoding="utf-8")
            invalid_sitemap = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, invalid_sitemap)
            self.assertIn("sitemap.xml is present and valid", invalid_sitemap.failures)


class MetadataAndSitemapTests(unittest.TestCase):
    def test_all_sixteen_pages_have_unique_complete_route_metadata(self):
        self.assertEqual(16, len(PUBLIC_PAGES))
        titles, descriptions = [], []
        for page in PUBLIC_PAGES:
            parser = parse_head(page)
            metas = {(m.get("name") or m.get("property")): m.get("content") for m in parser.metas}
            links = {item.get("rel"): item.get("href") for item in parser.links}
            expected = "https://salaam.center" + ROUTES[page]
            titles.append(parser.title.strip())
            descriptions.append(metas.get("description"))
            self.assertEqual(expected, links.get("canonical"), page)
            self.assertEqual(expected, metas.get("og:url"), page)
            self.assertEqual("website", metas.get("og:type"), page)
            self.assertEqual("Salaam Center", metas.get("og:site_name"), page)
            self.assertEqual("summary", metas.get("twitter:card"), page)
            self.assertEqual(parser.title.strip(), metas.get("og:title"), page)
            self.assertEqual(parser.title.strip(), metas.get("twitter:title"), page)
            self.assertEqual(metas.get("description"), metas.get("og:description"), page)
            self.assertEqual(metas.get("description"), metas.get("twitter:description"), page)
            self.assertEqual("noindex, nofollow", metas.get("robots"), page)
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_sitemap_is_valid_and_contains_only_approved_search_routes(self):
        root = ET.parse(ROOT / "sitemap.xml").getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in root.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(len(locations), len(set(locations)))
        self.assertEqual({"https://salaam.center" + route for route in SITEMAP_ROUTES}, set(locations))
        self.assertTrue(all(value.startswith("https://salaam.center") for value in locations))
        self.assertFalse(any("success" in value or "salaamcenter.org" in value for value in locations))

    def test_structured_data_is_valid_and_limited_to_approved_home_facts(self):
        blocks = []
        for page in PUBLIC_PAGES:
            source = (ROOT / page).read_text(encoding="utf-8")
            blocks.extend(re.findall(
                r'<script\s+type="application/ld\+json">\s*(.*?)\s*</script>',
                source,
                flags=re.DOTALL,
            ))
        self.assertEqual(1, len(blocks))
        data = json.loads(blocks[0])
        graph = data["@graph"]
        self.assertEqual({"EducationalOrganization", "WebSite"}, {item["@type"] for item in graph})
        organization = next(item for item in graph if item["@type"] == "EducationalOrganization")
        self.assertEqual("Salaam Center", organization["name"])
        self.assertEqual("https://salaam.center/", organization["url"])
        self.assertEqual("hello@salaam.center", organization["email"])
        serialized = json.dumps(data).casefold()
        for unsupported in (
            "aggregaterating", "review", "ratingvalue", "telephone", "address",
            "sameas", "foundingdate", "accreditation", "teacher compensation",
        ):
            self.assertNotIn(unsupported, serialized)


class ContactAndPolicyTests(unittest.TestCase):
    def test_contact_route_and_shared_footer_are_safe(self):
        contact = (ROOT / "contact/index.html").read_text(encoding="utf-8")
        footer = (ROOT / "partials/footer.html").read_text(encoding="utf-8")
        self.assertIn("Contact Salaam Center", contact)
        self.assertIn('href="mailto:hello@salaam.center"', contact)
        self.assertIn("parent or guardian", contact.lower())
        self.assertIn('href="/contact/"', footer)
        self.assertNotRegex(contact, r"(?i)(whatsapp|\btel:|phone number|office hours|instagram|facebook)")

    def test_privacy_terms_and_no_analytics_position_are_explicit(self):
        privacy = (ROOT / "privacy-policy/index.html").read_text(encoding="utf-8")
        terms = (ROOT / "terms/index.html").read_text(encoding="utf-8")
        docs = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in (
            "SALAM-CENTER-APPROVED-FACTS.md", "docs/COMMERCIAL-AND-ENROLMENT.md"))
        for phrase in ("No live booking submissions", "No analytics", "No advertising trackers", "Formspree", "controller identity", "retention"):
            self.assertIn(phrase.casefold(), privacy.casefold())
        for phrase in ("not the final contractual Terms and Conditions", "Legal operator identity", "Consumer withdrawal", "Payment provider", "Final effective date"):
            self.assertIn(phrase.casefold(), terms.casefold())
        self.assertIn("no analytics", docs.casefold())
        self.assertIn("no advertising pixels", docs.casefold())
        self.assertIn("separate future approval", docs.casefold())

    def test_approved_facts_do_not_contradict_the_locked_contact_decision(self):
        facts = (ROOT / "SALAM-CENTER-APPROVED-FACTS.md").read_text(encoding="utf-8")
        self.assertNotIn("No Salaam Center email address", facts)
        self.assertIn("single planned public mailbox is `hello@salaam.center`", facts)
        self.assertIn("production-origin metadata and an unsubmitted sitemap are prepared", facts)

    def test_disabled_preview_banner_is_scoped_to_the_outer_form_fieldset(self):
        css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
        self.assertIn(".trial-form > fieldset:disabled {", css)
        self.assertNotRegex(css, r"(?m)^\.trial-form fieldset:disabled \{")
        self.assertIn(".trial-form > fieldset:disabled::before", css)
        self.assertNotRegex(css, r"(?m)^\.trial-form fieldset:disabled::before")


if __name__ == "__main__":
    unittest.main()
