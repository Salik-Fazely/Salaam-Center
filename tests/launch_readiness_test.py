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

from scripts.deployment_boundary import expected_redirect_rules, public_backing_pairs


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
    def test_prelaunch_configuration_is_strict_cloudflare_whatsapp_only(self):
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual("prelaunch", data["site_mode"])
        self.assertEqual("https://salaam.center", data["production_origin"])
        self.assertEqual(["salaam.center", "www.salaam.center"], data["production_domains"])
        self.assertEqual("cloudflare_pages", data["hosting_source"])
        self.assertEqual("salaam-center", data["cloudflare_pages_project"])
        self.assertIs(data["automatic_deployment_from_main"], True)
        self.assertEqual("static_public_route_allowlist", data["deployment_surface_mode"])
        self.assertIs(data["pages_functions_enabled"], False)
        self.assertIs(data["production_domains_active"], True)
        self.assertIs(data["https_confirmed"], True)
        self.assertEqual("whatsapp", data["contact_channel"])
        self.assertEqual("34614401172", data["whatsapp_number"])
        self.assertRegex(data["whatsapp_number"], r"^[1-9]\d{7,14}$")
        self.assertIs(data["whatsapp_number_verified"], True)
        self.assertIs(data["whatsapp_link_verified"], True)
        self.assertIs(data["whatsapp_live_link_tested"], False)
        self.assertEqual("client_side_whatsapp_handoff", data["form_submission_mode"])
        self.assertEqual("none", data["booking_provider"])
        self.assertEqual("", data["booking_endpoint"])
        self.assertEqual("none", data["analytics_mode"])
        for key in ("privacy_policy_final_approved", "terms_final_approved",
                    "github_pages_enabled", "cname_required", "search_console_enabled"):
            self.assertIs(data[key], False, key)
        for obsolete in (
            "contact_email", "contact_email_verified", "booking_endpoint_verified",
            "formspree_domain_restriction_confirmed", "domain_verified_with_github",
            "dns_configured",
        ):
            self.assertNotIn(obsolete, data)
        self.assertNotRegex(
            CONFIG.read_text(encoding="utf-8"),
            r"(?i)(api[_-]?key|access[_-]?token|password|secret)",
        )


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
        self.assertIn(
            "PASS: unreviewed repository paths fail closed with styled HTTP 404",
            result.stdout,
        )
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
            "legal_controller_name is present",
            "legal_controller_address is present",
            "privacy_policy_final_approved is true",
            "terms_final_approved is true",
            "whatsapp_live_link_tested is true",
            "noindex, nofollow removed from production pages",
            "robots.txt allows intended crawling",
            "no placeholder strings remain",
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

    def test_wrong_malformed_and_placeholder_whatsapp_numbers_fail(self):
        base = json.loads(CONFIG.read_text(encoding="utf-8"))
        for number in (
            "WHATSAPP_NUMBER_DIGITS",
            "+34614401172",
            "34 614 401 172",
            "34614401173",
            "123",
        ):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / "config.json"
                config.write_text(json.dumps({**base, "whatsapp_number": number}), encoding="utf-8")
                result = self.run_preflight("prelaunch", config)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("whatsapp_number", result.stdout)

    def test_prelaunch_rejects_architecture_mismatches(self):
        base = json.loads(CONFIG.read_text(encoding="utf-8"))
        cases = (
            ({"whatsapp_number_verified": False}, "whatsapp_number_verified is true"),
            ({"whatsapp_link_verified": False}, "whatsapp_link_verified is true"),
            ({"production_domains_active": False}, "production domains are active"),
            ({"automatic_deployment_from_main": False}, "automatic deployment from main is enabled"),
            ({"deployment_surface_mode": "repository_root"}, "deployment surface uses static public-route allowlist"),
            ({"pages_functions_enabled": True}, "Cloudflare Pages Functions remain disabled"),
            ({"https_confirmed": False}, "HTTPS is confirmed"),
            ({"github_pages_enabled": True}, "GitHub Pages is disabled"),
            ({"cname_required": True}, "CNAME is not required"),
            ({"booking_provider": "formspree"}, "booking_provider is none"),
            ({"booking_endpoint": "https://example.test/form"}, "booking_endpoint is empty"),
            ({"analytics_mode": "active"}, "analytics_mode remains none"),
        )
        for patch, expected in cases:
            with self.subTest(patch=patch), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / "config.json"
                config.write_text(json.dumps({**base, **patch}), encoding="utf-8")
                result = self.run_preflight("prelaunch", config)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(expected, result.stdout)

    def test_a_complete_future_production_state_is_logically_passable(self):
        spec = importlib.util.spec_from_file_location("launch_preflight_under_test", PREFLIGHT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config.update({
            "site_mode": "production",
            "legal_controller_name": "Approved Operator",
            "legal_controller_address": "Approved disclosure address",
            "privacy_policy_final_approved": True,
            "terms_final_approved": True,
            "whatsapp_live_link_tested": True,
        })
        generic_link = (
            f'<a href="{module.WHATSAPP_URL}" target="_blank" '
            'rel="noopener noreferrer">WhatsApp</a>'
        )
        bases = {
            page: (
                f'<link rel="canonical" href="{module.PRODUCTION_ORIGIN + module.ROUTES[page]}">'
                + generic_link
            )
            for page in PUBLIC_PAGES
        }
        source = dict(bases)
        source["teachers/index.html"] += " ".join(module.PROTECTED_NAMES + module.PROTECTED_VIDEO_IDS)
        source["pricing/index.html"] += " ".join(module.APPROVED_PRICES)
        source["book-trial/index.html"] = (
            bases["book-trial/index.html"]
            + '<form data-whatsapp-handoff="true">'
            + '<button type="button" data-whatsapp-submit>Continue in WhatsApp</button></form>'
        )
        truthful_success = (
            bases["success/index.html"]
            + "<h1>Continue your conversation in WhatsApp</h1>"
            + "<p>The website cannot confirm whether you pressed Send.</p>"
            + "<p>The trial is not booked until Salaam Center confirms teacher and schedule availability.</p>"
        )
        source["success/index.html"] = truthful_success

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "assets/js").mkdir(parents=True)
            (root / "assets/css").mkdir(parents=True)
            (root / "assets/logo").mkdir(parents=True)
            for page, markup in source.items():
                target = root / page
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(markup, encoding="utf-8")
            (root / "assets/css/styles.css").write_text("", encoding="utf-8")
            (root / "assets/logo/salaam-center-favicon.svg").write_text("", encoding="utf-8")
            redirects_path = root / "_redirects"
            redirects_path.write_text(
                "\n".join(expected_redirect_rules()) + "\n",
                encoding="utf-8",
            )
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
            handoff_script = (
                f'var url = "{module.WHATSAPP_URL}?text=" + encodeURIComponent(message); '
                'var popup = window.open(url, "_blank"); '
                "if (popup) popup.opener = null; else window.location.assign(url);"
            )
            script_path = root / "assets/js/trial-form.js"
            script_path.write_text(handoff_script, encoding="utf-8")
            (root / "assets/js/main.js").write_text("", encoding="utf-8")
            for source_path, backing_path in public_backing_pairs():
                target = root / backing_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((root / source_path).read_bytes())
            module.ROOT = root
            result = module.Result()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.production(config, source, result)
            self.assertEqual([], result.failures, output.getvalue())
            self.assertIn("PASS: production readiness", output.getvalue())

            redirects_path.unlink()
            missing_boundary = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, missing_boundary)
            self.assertIn(
                "unreviewed repository paths fail closed with styled HTTP 404",
                missing_boundary.failures,
            )
            redirects_path.write_text(
                "\n".join(expected_redirect_rules()) + "\n",
                encoding="utf-8",
            )

            source["success/index.html"] = bases["success/index.html"] + "<h1>Message Sent</h1>"
            false_success = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, false_success)
            self.assertIn("Success page remains truthful", false_success.failures)

            source["success/index.html"] = truthful_success
            source["contact/index.html"] += " Contact us at hello@example.test."
            public_email = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, public_email)
            self.assertIn("no public email contact", public_email.failures)

            source["contact/index.html"] = bases["contact/index.html"]
            for unsafe_network in (
                "fetch('/submit');",
                "navigator.sendBeacon('/collect', value);",
                "new Image().src = '/collect?value=' + value;",
            ):
                with self.subTest(unsafe_network=unsafe_network):
                    script_path.write_text(
                        handoff_script + " " + unsafe_network,
                        encoding="utf-8",
                    )
                    network_submission = module.Result()
                    with contextlib.redirect_stdout(io.StringIO()):
                        module.production(config, source, network_submission)
                    self.assertIn(
                        "no browser network submission",
                        network_submission.failures,
                    )
                    self.assertIn(
                        "safe client-side WhatsApp handoff",
                        network_submission.failures,
                    )

            (root / "assets/js/main.js").write_text(
                "iframe.src = 'https://www.youtube-nocookie.com/embed/video';",
                encoding="utf-8",
            )
            script_path.write_text(handoff_script, encoding="utf-8")
            safe_video = module.Result()
            with contextlib.redirect_stdout(io.StringIO()):
                module.production(config, source, safe_video)
            self.assertNotIn("no browser network submission", safe_video.failures)

            script_path.write_text(handoff_script, encoding="utf-8")
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
        self.assertNotIn("email", organization)
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
        self.assertIn('href="https://wa.me/34614401172"', contact)
        self.assertIn('target="_blank"', contact)
        self.assertIn('rel="noopener noreferrer"', contact)
        self.assertIn("parent or guardian", contact.lower())
        self.assertIn('href="/contact/"', footer)
        self.assertNotRegex(contact + footer, r"(?i)mailto:|\btel:|hello@salaam\.center")

    def test_privacy_terms_and_no_analytics_position_are_explicit(self):
        privacy = (ROOT / "privacy-policy/index.html").read_text(encoding="utf-8")
        terms = (ROOT / "terms/index.html").read_text(encoding="utf-8")
        docs = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in (
            "SALAM-CENTER-APPROVED-FACTS.md", "docs/COMMERCIAL-AND-ENROLMENT.md"))
        for phrase in (
            "locally in your browser", "does not submit or store", "WhatsApp",
            "third-party service", "No analytics", "No advertising pixels",
            "controller identity",
        ):
            self.assertIn(phrase.casefold(), privacy.casefold())
        self.assertNotIn("formspree", privacy.casefold())
        for phrase in (
            "not the final contractual Terms and Conditions", "WhatsApp message is an enquiry",
            "not a confirmed booking", "no payment obligation", "Legal operator identity",
        ):
            self.assertIn(phrase.casefold(), terms.casefold())
        self.assertIn("no analytics", docs.casefold())
        self.assertIn("no advertising pixels", docs.casefold())
        self.assertIn("separate future approval", docs.casefold())

    def test_approved_facts_do_not_contradict_the_locked_contact_decision(self):
        facts = (ROOT / "SALAM-CENTER-APPROVED-FACTS.md").read_text(encoding="utf-8")
        self.assertIn("WhatsApp is the only initial public contact channel", facts)
        self.assertIn("`34614401172`", facts)
        self.assertIn("Domain email is not required", facts)
        self.assertIn("Formspree is superseded", facts)
        self.assertIn("Cloudflare Pages is the production hosting source of truth", facts)

    def test_obsolete_disabled_form_honeypot_and_acknowledgement_styles_are_removed(self):
        css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
        self.assertNotIn(".trial-form > fieldset:disabled", css)
        self.assertNotIn(".acknowledgement", css)
        self.assertNotIn(".honeypot", css)


if __name__ == "__main__":
    unittest.main()
