import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/launch-readiness.json"
WHATSAPP_NUMBER = "34614401172"
WHATSAPP_URL = f"https://wa.me/{WHATSAPP_NUMBER}"
PUBLIC_PAGES = (
    "index.html",
    "our-approach/index.html",
    "programs/index.html",
    "programs/quran/index.html",
    "programs/dari-persian/index.html",
    "programs/afghan-culture-islamic-ethics/index.html",
    "teachers/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "about/index.html",
    "book-trial/index.html",
    "contact/index.html",
    "privacy-policy/index.html",
    "terms/index.html",
    "success/index.html",
    "404.html",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class WhatsAppConfigurationTests(unittest.TestCase):
    def test_launch_configuration_describes_the_exact_cloudflare_whatsapp_architecture(self):
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual("prelaunch", data["site_mode"])
        self.assertEqual("https://salaam.center", data["production_origin"])
        self.assertEqual(["salaam.center", "www.salaam.center"], data["production_domains"])
        self.assertEqual("cloudflare_pages", data["hosting_source"])
        self.assertEqual("salaam-center", data["cloudflare_pages_project"])
        self.assertIs(data["automatic_deployment_from_main"], True)
        self.assertIs(data["production_domains_active"], True)
        self.assertIs(data["https_confirmed"], True)
        self.assertEqual("whatsapp", data["contact_channel"])
        self.assertEqual(WHATSAPP_NUMBER, data["whatsapp_number"])
        self.assertRegex(data["whatsapp_number"], r"^[1-9]\d{7,14}$")
        self.assertIs(data["whatsapp_number_verified"], True)
        self.assertIs(data["whatsapp_link_verified"], True)
        self.assertIs(data["whatsapp_live_link_tested"], False)
        self.assertEqual("client_side_whatsapp_handoff", data["form_submission_mode"])
        self.assertEqual("none", data["booking_provider"])
        self.assertEqual("", data["booking_endpoint"])
        self.assertEqual("none", data["analytics_mode"])
        self.assertIs(data["github_pages_enabled"], False)
        self.assertIs(data["cname_required"], False)

        obsolete = {
            "contact_email",
            "contact_email_verified",
            "booking_endpoint_verified",
            "formspree_domain_restriction_confirmed",
            "domain_verified_with_github",
            "dns_configured",
        }
        self.assertTrue(obsolete.isdisjoint(data), obsolete & data.keys())
        self.assertNotRegex(
            CONFIG.read_text(encoding="utf-8"),
            r"(?i)(api[_-]?key|access[_-]?token|password|secret)",
        )


class PublicWhatsAppArchitectureTests(unittest.TestCase):
    def test_public_code_contains_no_email_formspree_network_or_storage_submission(self):
        public_html = "\n".join(read(path) for path in PUBLIC_PAGES)
        executable = "\n".join(read(path) for path in (
            "assets/js/main.js",
            "assets/js/trial-form.js",
        ))
        public_code = public_html + "\n" + executable
        self.assertNotRegex(public_code, r"(?i)hello@salaam\.center|mailto:")
        self.assertNotRegex(public_code, r"(?i)formspree(?:\.io)?")
        self.assertNotRegex(executable, r"\bfetch\s*\(|XMLHttpRequest")
        self.assertNotRegex(executable, r"localStorage|sessionStorage")
        self.assertNotRegex(executable, r"(?i)whatsapp[^\n]{0,50}(?:api[_-]?key|access[_-]?token|secret)")

    def test_every_public_whatsapp_destination_uses_the_exact_number_without_tracking(self):
        public_html = "\n".join(read(path) for path in PUBLIC_PAGES)
        urls = re.findall(r'href="(https://wa\.me/[^"]+)"', public_html)
        self.assertGreaterEqual(len(urls), len(PUBLIC_PAGES))
        self.assertEqual({WHATSAPP_URL}, set(urls))
        script = read("assets/js/trial-form.js")
        self.assertIn(f'"{WHATSAPP_URL}?text="', script)
        self.assertIn("encodeURIComponent(message)", script)
        self.assertNotRegex(public_html + script, r"(?i)wa\.me/[^\s\"']+[?&](?:utm_|fbclid|gclid|ref=)")

    def test_contact_page_and_footer_make_whatsapp_the_only_public_contact_route(self):
        contact = read("contact/index.html")
        footer = read("partials/footer.html")
        for source in (contact, footer):
            self.assertIn(WHATSAPP_URL, source)
            self.assertIn('target="_blank"', source)
            self.assertIn('rel="noopener noreferrer"', source)
            self.assertNotRegex(source, r"(?i)mailto:|\btel:")
        self.assertIn("Contact Salaam Center", contact)
        self.assertIn("Questions about programs, eligibility or free trials", contact)
        self.assertIn("Chat with Salaam Center on WhatsApp", contact)
        self.assertIn("parent or guardian", contact.casefold())
        self.assertIn('href="/contact/"', footer)

    def test_privacy_discloses_local_processing_third_party_transfer_and_minor_safety(self):
        privacy = read("privacy-policy/index.html").casefold()
        for phrase in (
            "locally in your browser",
            "does not submit or store",
            "third-party service",
            "review the prepared message",
            "sensitive information",
            "parent or guardian",
            "no analytics",
            "no advertising pixels",
            "privacy-enhanced",
            "pre-launch",
            "not the final",
        ):
            self.assertIn(phrase, privacy)
        self.assertNotIn("formspree", privacy)
        self.assertNotRegex(privacy, r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")

    def test_terms_describe_whatsapp_as_an_enquiry_without_booking_or_payment_obligation(self):
        terms = read("terms/index.html").casefold()
        for phrase in (
            "whatsapp message is an enquiry",
            "not a confirmed booking",
            "no payment obligation",
            "teacher and schedule availability",
            "final terms",
            "before any payment is accepted",
        ):
            self.assertIn(phrase, terms)

    def test_success_route_never_claims_a_submission_or_booking(self):
        success = read("success/index.html")
        self.assertIn("Continue your conversation in WhatsApp", success)
        self.assertIn("cannot confirm", success)
        self.assertIn("press Send", success)
        self.assertIn("not booked until Salaam Center confirms", success)
        self.assertIn(WHATSAPP_URL, success)
        self.assertNotRegex(
            success,
            r"(?i)data-success-state|request received|message sent|trial (?:is )?confirmed|trial request was submitted",
        )
        self.assertNotIn("trial-form.js", success)

    def test_all_public_pages_remain_noindex_and_have_no_analytics_or_payment_integration(self):
        public = "\n".join(read(path) for path in PUBLIC_PAGES)
        for path in PUBLIC_PAGES:
            self.assertIn('name="robots" content="noindex, nofollow"', read(path), path)
        self.assertNotRegex(
            public,
            r"(?i)googletagmanager|google-analytics|\bgtag\s*\(|\bfbq\s*\(|connect\.facebook\.net",
        )
        self.assertNotRegex(
            public,
            r"(?i)stripe\.com|paypal\.com|checkout\.js|href=[\"'][^\"']*(?:checkout|pay)[^\"']*[\"']",
        )


class InfrastructureAndDocumentationTests(unittest.TestCase):
    def test_repository_has_no_github_pages_cname_or_workflow(self):
        self.assertFalse((ROOT / "CNAME").exists())
        workflows = ROOT / ".github/workflows"
        if workflows.is_dir():
            for path in (*workflows.glob("*.yml"), *workflows.glob("*.yaml")):
                source = path.read_text(encoding="utf-8").casefold()
                self.assertNotRegex(
                    path.name.casefold() + "\n" + source,
                    r"deploy-pages|upload-pages-artifact|github-pages|pages:\s*write",
                )

    def test_authoritative_documents_record_the_cloudflare_and_whatsapp_decisions(self):
        files = (
            "SALAM-CENTER-APPROVED-FACTS.md",
            "docs/COMMERCIAL-AND-ENROLMENT.md",
            "docs/LAUNCH-ACTIVATION-CHECKLIST.md",
        )
        combined = "\n".join(read(path) for path in files).casefold()
        for phrase in (
            "cloudflare pages",
            "hosting source of truth",
            WHATSAPP_NUMBER,
            "only initial public contact channel",
            "formspree is superseded",
            "domain email is not required",
            "press send",
            "no automatic",
            "parent or guardian",
            "no analytics",
            "no payments",
            "dns must not be changed",
            "github pages must not be configured",
        ):
            self.assertIn(phrase, combined)
        checklist = read("docs/LAUNCH-ACTIVATION-CHECKLIST.md").casefold()
        for phrase in (
            "whatsapp business profile",
            "android or iphone",
            "whatsapp web",
            "prepared message",
            "sensitive data",
            "remove noindex",
        ):
            self.assertIn(phrase, checklist)


if __name__ == "__main__":
    unittest.main()
