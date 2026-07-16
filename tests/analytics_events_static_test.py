import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSENT_SCRIPT = '<script src="/assets/js/consent.js"></script>'
EVENT_SCRIPT = '<script src="/assets/js/analytics-events.js"></script>'
MAIN_SCRIPT = '<script src="/assets/js/main.js"></script>'
APPROVED_EVENTS = (
    "trial_cta_click",
    "trial_form_start",
    "trial_form_submit_attempt",
)


def public_pages():
    return tuple(
        path
        for path in sorted(ROOT.rglob("*.html"))
        if "<!-- SHARED FOOTER:START -->" in path.read_text(encoding="utf-8")
    )


class AnalyticsEventsStaticTests(unittest.TestCase):
    def test_all_public_pages_load_the_shared_module_once_after_consent(self):
        pages = public_pages()
        self.assertEqual(16, len(pages))

        for page in pages:
            source = page.read_text(encoding="utf-8")
            relative = page.relative_to(ROOT)
            self.assertEqual(1, source.count(EVENT_SCRIPT), relative)
            self.assertLess(source.index(CONSENT_SCRIPT), source.index(EVENT_SCRIPT), relative)
            self.assertLess(source.index(EVENT_SCRIPT), source.index(MAIN_SCRIPT), relative)

    def test_module_contains_only_approved_events_and_no_analytics_loader(self):
        source = (ROOT / "assets/js/analytics-events.js").read_text(encoding="utf-8")

        for event_name in APPROVED_EVENTS:
            self.assertEqual(1, source.count(event_name), event_name)
        for excluded in (
            "generate_lead",
            "confirmed_booking",
            "successful_booking",
            "/success/",
            "googletagmanager.com",
            "google-analytics.com",
            "gtag('config'",
            "dataLayer",
            "FormData",
        ):
            self.assertNotIn(excluded, source)

    def test_success_page_has_no_conversion_event(self):
        source = (ROOT / "success/index.html").read_text(encoding="utf-8")

        for event_name in APPROVED_EVENTS:
            self.assertNotIn(event_name, source)
        self.assertNotIn("gtag(", source)


if __name__ == "__main__":
    unittest.main()
