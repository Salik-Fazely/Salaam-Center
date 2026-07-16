import html
import re
import unittest
from pathlib import Path

from tests.commercial_truth_test import StructureParser


ROOT = Path(__file__).resolve().parents[1]
WHATSAPP_URL = "https://wa.me/34614494311"
PUBLIC_PAGES = (
    "index.html",
    "about/index.html",
    "teachers/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "terms/index.html",
    "privacy-policy/index.html",
    "book-trial/index.html",
    "success/index.html",
    "blog/index.html",
    "blog/free-online-quran-trial-lesson-parent-checklist/index.html",
    "blog/help-children-memorize-short-surahs/index.html",
    "blog/how-parents-can-track-their-childs-quran-progress/index.html",
    "blog/one-to-one-quran-classes-vs-group-classes-for-children/index.html",
    "blog/online-quran-classes-for-kids-parents-look-for/index.html",
)
FOOTER_CONTACT_PAGES = (
    "index.html",
    "about/index.html",
    "teachers/index.html",
    "how-it-works/index.html",
    "pricing/index.html",
    "terms/index.html",
    "privacy-policy/index.html",
    "book-trial/index.html",
    "blog/index.html",
)
UNCHANGED_FOOTER_PAGES = tuple(
    path for path in PUBLIC_PAGES if path not in FOOTER_CONTACT_PAGES
)


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def visible_text(path):
    text = re.sub(r"<[^>]+>", " ", source(path))
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


class TrustSafeguardingPatchTests(unittest.TestCase):
    def test_homepage_uses_approved_statistics(self):
        homepage = source("index.html")
        self.assertIn('aria-label="4 Teachers"', homepage)
        self.assertIn('data-count-to="4">4</span>', homepage)
        self.assertIn('aria-label="1-to-1 Lessons"', homepage)
        self.assertIn('<span class="trust-stats__phrase">1-to-1</span>', homepage)
        self.assertIn('aria-label="4 Teaching languages"', homepage)
        for removed in ("21+ Students", "100% Trusted by Families"):
            self.assertNotIn(removed, "\n".join(source(path) for path in PUBLIC_PAGES))

    def test_homepage_removes_written_testimonials_but_keeps_student_videos(self):
        homepage = source("index.html")
        self.assertIn("Student moments", homepage)
        self.assertIn(
            "Short messages shared by students and families learning with Tarteel House.",
            homepage,
        )
        self.assertEqual(2, homepage.count('class="feedback-video-card"'))
        for video_id in ("to3h-qq7_FM", "6WxiPdZNcCY"):
            self.assertIn(video_id, homepage)
        for removed in (
            "Sara A.",
            "Youssef B.",
            "Aisha M.",
            "Real voices from the families currently learning with us",
            'class="testimonials"',
            'class="testimonial-card"',
        ):
            self.assertNotIn(removed, homepage)

    def test_teacher_video_and_confirmed_experience_are_preserved(self):
        teachers = source("teachers/index.html")
        all_public = "\n".join(source(path) for path in PUBLIC_PAGES)
        self.assertNotIn("GtCRaK_mojc", all_public)
        self.assertEqual(2, teachers.count("fOzc2cM5Twk"))
        self.assertIn("Watch lesson samples from our teachers.", teachers)
        self.assertNotIn("only two teacher samples", teachers.lower())
        for retained_id in ("iUMB3pKzS_A", "iurgyXOzqFU", "OtaIpKZpbMM"):
            self.assertIn(retained_id, teachers)

        claims = {
            "Farkhonda Jami": "2 years teaching Tajweed and Tafsir",
            "Foruhar Rahmani": "2 years teaching Tajweed",
            "Fareshta Suroush": "2 years teaching Tajweed",
            "Sadiah Hamid": "6 years teaching Tajweed, Hifz, and Quranic recitation",
        }
        for teacher, claim in claims.items():
            card = re.search(
                rf'<article class="teacher-card".*?>.*?{re.escape(teacher)}.*?</article>',
                teachers,
                re.DOTALL,
            )
            self.assertIsNotNone(card, teacher)
            self.assertIn(claim, html.unescape(card.group()), teacher)

    def test_service_promises_use_approved_qualified_copy(self):
        how = visible_text("how-it-works/index.html")
        about = visible_text("about/index.html")
        self.assertIn("From the trial lesson to a clear learning plan", how)
        self.assertIn(
            "Once we understand your child’s needs and availability, we arrange the trial lesson with a suitable teacher.",
            how,
        )
        self.assertIn(
            "We normally contact families within two days to arrange the next steps.",
            how,
        )
        self.assertIn(
            "Short, regular practice between lessons can support steady progress.",
            how,
        )
        self.assertIn(
            "We design lessons around calm, consistency, and regular practice.",
            about,
        )
        self.assertNotIn("Most families are in their first session within a week", how)
        self.assertNotIn("makes the biggest difference", how)
        self.assertNotIn("Learning deepens when the conditions around it are stable", about)

        approved = (
            "Your child normally continues with the same dedicated teacher throughout the package. "
            "If a change becomes unavoidable, we will discuss the best alternative with you."
        )
        for path in ("index.html", "about/index.html", "teachers/index.html", "pricing/index.html"):
            self.assertIn(approved, visible_text(path), path)
        combined = " ".join(
            visible_text(path)
            for path in (
                "index.html",
                "about/index.html",
                "teachers/index.html",
                "how-it-works/index.html",
                "pricing/index.html",
            )
        ).lower()
        for absolute in (
            "same teacher every session",
            "same teacher throughout the package",
            "stays with one dedicated teacher throughout the package",
        ):
            self.assertNotIn(absolute, combined)

    def test_approved_safeguarding_rules_are_published_consistently(self):
        how = visible_text("how-it-works/index.html")
        teachers = visible_text("teachers/index.html")
        terms = visible_text("terms/index.html")
        privacy = visible_text("privacy-policy/index.html")

        self.assertIn("Safe learning with parent involvement", how)
        self.assertIn(
            "Scheduling and service communication are handled through a parent or guardian. "
            "Lessons take place through Tarteel House-approved platforms such as Zoom or Google Meet. "
            "For younger children, we ask a parent or guardian to be nearby and available during the lesson.",
            how,
        )
        self.assertIn(
            "Lesson scheduling and service communication are managed through a parent or guardian. "
            "Teachers should not privately contact a child outside the lesson without the parent or guardian’s prior permission and involvement.",
            teachers,
        )
        self.assertIn("Child safeguarding and communication", terms)
        for required in (
            "Scheduling, lesson links, progress communication, and service decisions are managed through a parent or guardian.",
            "Teachers should not privately message a child outside a scheduled lesson without the parent or guardian’s prior permission and involvement.",
            "Teachers, parents, and students must not exchange personal social-media accounts or unnecessary private contact information.",
            "Lessons should take place using platforms approved by Tarteel House, normally Zoom or Google Meet.",
            "Tarteel House does not record lessons by default.",
            "No participant may record, photograph, screenshot, publish, or share lesson content without prior permission from the parent or guardian, the teacher, and Tarteel House where applicable.",
            "Teachers and students are expected to behave respectfully and appropriately during lessons.",
            "A parent or guardian may report a safeguarding or conduct concern through the official Tarteel House WhatsApp channel or hello@tarteelhouse.com.",
            "When a serious concern is reported, Tarteel House may pause lessons while the matter is reviewed and decide what steps are appropriate before lessons continue.",
        ):
            self.assertIn(required, terms)
        self.assertIn(
            "Lessons are not recorded by Tarteel House by default. If recording or use of lesson media is ever proposed, the purpose and required permissions will be explained in advance.",
            privacy,
        )

        combined = " ".join((how, teachers, terms, privacy)).lower()
        for unsupported in (
            "criminal-record check",
            "criminal record check",
            "background check",
            "safeguarding certification",
        ):
            self.assertNotIn(unsupported, combined)

        self.assertIn("Last updated: 14 July 2026", terms)
        self.assertIn("Last updated: 14 July 2026", privacy)

    def test_prebooking_whatsapp_links_are_consistent_and_safe(self):
        footer_link_pattern = re.compile(
            rf'<a href="{re.escape(WHATSAPP_URL)}" class="footer__contact-link" '
            r'target="_blank" rel="noopener noreferrer" aria-label="[^"]+">WhatsApp us</a>'
        )
        for path in FOOTER_CONTACT_PAGES:
            page = source(path)
            self.assertIn("Have a question before booking?", page, path)
            self.assertEqual(1, len(footer_link_pattern.findall(page)), path)
        for path in UNCHANGED_FOOTER_PAGES:
            self.assertNotIn('class="footer__contact-link"', source(path), path)

        for path in ("teachers/index.html", "pricing/index.html"):
            page = source(path)
            self.assertRegex(
                page,
                rf'<a href="{re.escape(WHATSAPP_URL)}" class="final-cta__secondary-link" '
                r'target="_blank" rel="noopener noreferrer" aria-label="[^"]+">Ask a question</a>',
            )

    def test_changed_pages_keep_balanced_html(self):
        for path in FOOTER_CONTACT_PAGES:
            parser = StructureParser()
            parser.feed(source(path))
            parser.close()
            self.assertEqual([], parser.errors, path)


if __name__ == "__main__":
    unittest.main()
