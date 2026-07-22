import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE_MANIFEST = ROOT / "config" / "localized-routes.json"
EXPECTED_IDS = {
    "home",
    "our-approach",
    "programs",
    "quran",
    "dari-persian",
    "afghan-culture-islamic-ethics",
    "teachers",
    "how-it-works",
    "pricing",
    "about",
    "book-trial",
    "contact",
    "privacy-policy",
    "terms",
    "success",
    "not-found",
}
APPROVED_ENGLISH_MAIN_SHA256 = {
    "home": "3e3d16dfcfaf8ace6ffcf52eb666e92da9bbab6883cbbb61ebccb49b6002d757",
    "our-approach": "52773922ed1d09b65292f16eebf0151544858a1367bd358425c96888172fb84f",
    "programs": "680d5c16333fb6800e05cfd193e32680b5cce9504f75ec9b56cdba0382de990b",
    "quran": "fa70c3c5e0e0a6d37481c0d20dce7ed02e6c5c3ead5ce93f028dcb823af0e9cf",
    "dari-persian": "1777220b3cf902a43b739dbd2dcd271d39a581cf0ae372cdcdf2201932716fa9",
    "afghan-culture-islamic-ethics": "4f154b95f38b6c42de494322e058808a6fab56b4a4848bdccc7bc6a47610a09d",
    "teachers": "ac56e3a2aff2011a481d102204a91522e4a40a3303da240a01a84ead16a26b56",
    "how-it-works": "cbb2d58d37809c1a9bc48cf8a9ed65b7c7daf98c1142a2f98e4eef5d967a5705",
    "pricing": "3c053ba1820d3c413242c494fee6fb33d211cc0f9bb2ab915c4ca4613205da0a",
    "about": "2ac814d8429c1318681992a77b69a2cdf979e4aaa66eeb83812e83dff26b2ae2",
    "book-trial": "6597dda695866c3f4d27198b969b3dc0aa2716fbc3b5f79d5f5d7ecfc13338b7",
    "contact": "2c882e265f0b63b3873103803d68eeb5915ab4619c14d7a68b940a2607c381e8",
    "privacy-policy": "d714062eee278e0510131d77572ad439a17a472f7cb1ca495689484729e4ffd4",
    "terms": "86e7ceed76a33b6da0aae704f727cdca0e304c25bce489d12f10b5163e5867b6",
    "success": "69835605e62a7845adcb2d6a0c27ad89efaf8687d04ac7f0f9b565d7d8113576",
    "not-found": "7b246916478d91b50ed95d33ca20cb289559fae61579b95721f8d980087c092e",
}
EXPECTED_DARI_HEADINGS = {
    "home": "به فرزندتان کمک کنید تا با زبان، ایمان و میراث افغان خود پیوند داشته باشد.",
    "our-approach": "یادگیری میراث که زبان، ایمان، فرهنگ و شخصیت را به هم پیوند می‌دهد",
    "programs": "برنامه‌هایی برای زبان، ایمان و میراث افغان",
    "quran": "آموزش خصوصی آنلاین قرآن در یک محیط پشتیبان",
    "dari-persian": "به فرزندتان کمک کنید پیوند خود را با زبان دری نیرومند سازد",
    "afghan-culture-islamic-ethics": "به کودکان کمک کنید میراث خود را بشناسند و ارزش‌های نیک را در عمل پیاده کنند",
    "teachers": "استادانی که خانواده‌های افغان و شاگردان بیرون از کشور را درک می‌کنند",
    "how-it-works": "یک مسیر روشن از نخستین گفت‌وگو تا صنف مناسب",
    "pricing": "برنامه‌های ساده برای یادگیری پیوسته",
    "about": "کمک به کودکان افغان در بیرون از کشور تا با ریشه‌های خود پیوند داشته باشند",
    "book-trial": "با یک جلسهٔ آزمایشی رایگان 40 دقیقه‌ای آغاز کنید",
    "contact": "با Salaam Center تماس بگیرید",
    "privacy-policy": "سیاست حفظ حریم خصوصی",
    "terms": "شرایط و مقررات",
    "success": "گفت‌وگوی خود را در واتس‌اپ ادامه دهید",
    "not-found": "این صفحه پیدا نشد",
}
FONT_SHA256 = "4e3fa217d38fdafc1fea4414ceb58ca5e662cf0ab5fa735a8c8c20e8b42cad92"
OFL_SHA256 = "17e355067c8284f47743a1ee3b1ef7ff684ff0601eda357f9353b10b3016ab31"


def source_path(public_path: str) -> Path:
    if public_path == "/":
        return ROOT / "index.html"
    relative = public_path.lstrip("/")
    if relative.endswith("/"):
        relative += "index.html"
    return ROOT / relative


class LocalizedRouteManifestTests(unittest.TestCase):
    def load_manifest(self):
        self.assertTrue(ROUTE_MANIFEST.is_file(), "localized route manifest is missing")
        return json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_defines_every_unique_route_pair(self):
        routes = self.load_manifest()
        self.assertEqual({route["id"] for route in routes}, EXPECTED_IDS)
        self.assertEqual(len(routes), len(EXPECTED_IDS))
        self.assertEqual(len({route["fa_AF"] for route in routes}), len(routes))
        self.assertEqual(len({route["en"] for route in routes}), len(routes))
        for route in routes:
            self.assertEqual(
                set(route),
                {"id", "fa_AF", "en", "indexable", "sitemap", "status"},
            )
            self.assertTrue(route["fa_AF"].startswith("/"))
            self.assertTrue(route["en"].startswith("/en/"))
            self.assertEqual(route["indexable"], route["sitemap"])

    def test_manifest_has_fourteen_indexable_pairs_and_two_safe_exclusions(self):
        routes = self.load_manifest()
        indexable = [route for route in routes if route["indexable"]]
        excluded = {route["id"]: route for route in routes if not route["indexable"]}
        self.assertEqual(len(indexable), 14)
        self.assertEqual(set(excluded), {"success", "not-found"})
        self.assertEqual(excluded["success"]["status"], "success")
        self.assertEqual(excluded["not-found"]["status"], "not_found")
        self.assertFalse(excluded["success"]["sitemap"])
        self.assertFalse(excluded["not-found"]["sitemap"])


class EnglishPreservationTests(unittest.TestCase):
    def load_manifest(self):
        self.assertTrue(ROUTE_MANIFEST.is_file(), "localized route manifest is missing")
        return json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))

    def test_complete_english_tree_uses_exact_language_and_direction(self):
        for route in self.load_manifest():
            page = source_path(route["en"])
            self.assertTrue(page.is_file(), f"missing English page: {route['en']}")
            html = page.read_text(encoding="utf-8")
            self.assertRegex(html, r'<html\s+lang="en"\s+dir="ltr">')

    def test_approved_english_main_content_is_byte_stable_after_link_normalization(self):
        for route in self.load_manifest():
            html = source_path(route["en"]).read_text(encoding="utf-8")
            main = re.search(r"<main\b[\s\S]*?</main>", html).group(0)
            normalized = main.replace('href="/en/', 'href="/')
            digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            self.assertEqual(
                digest,
                APPROVED_ENGLISH_MAIN_SHA256[route["id"]],
                f"approved English main content changed: {route['en']}",
            )

    def test_english_pages_use_self_canonicals_and_english_internal_navigation(self):
        for route in self.load_manifest():
            page = source_path(route["en"])
            self.assertTrue(page.is_file(), f"missing English page: {route['en']}")
            html = page.read_text(encoding="utf-8")
            expected = f'https://salaam.center{route["en"]}'
            self.assertIn(f'<link rel="canonical" href="{expected}"', html)
            if route["status"] != "not_found":
                self.assertIn('href="/en/"', html)
                self.assertIn('href="/en/programs/"', html)
                self.assertIn('href="/en/book-trial/"', html)
            wrong_language_links = re.findall(
                r'href="(/(?!en(?:/|$)|assets/)[^"#?]*)"', html
            )
            self.assertEqual(
                [match for match in wrong_language_links if match != route["fa_AF"]],
                [],
                f"English page has non-counterpart root-language links: {route['en']}",
            )

    def test_approved_english_commercial_legal_and_media_facts_are_preserved(self):
        def read_required(public_path):
            page = source_path(public_path)
            self.assertTrue(page.is_file(), f"missing English page: {public_path}")
            return page.read_text(encoding="utf-8")

        pricing = read_required("/en/pricing/")
        terms = read_required("/en/terms/")
        privacy = read_required("/en/privacy-policy/")
        teachers = read_required("/en/teachers/")
        home = read_required("/en/")

        for value in ("€49", "€69", "€99", "€119", "€129", "€229"):
            self.assertIn(value, pricing)
            self.assertIn(value, terms)
        for value in (
            "Farkhonda Jami",
            "Foruhar Rahmani",
            "Fareshta Suroush",
            "Sadiah Hamid",
            "iUMB3pKzS_A",
            "iurgyXOzqFU",
            "OtaIpKZpbMM",
            "fOzc2cM5Twk",
        ):
            self.assertIn(value, teachers)
        for value in ("to3h-qq7_FM", "6WxiPdZNcCY"):
            self.assertIn(value, home)
        for page in (terms, privacy):
            self.assertIn("Salaam Center", page)
            self.assertIn("Sabadell, Barcelona", page)
            self.assertIn("+34 614 401 172", page)
            self.assertIn("22 July 2026", page)


class DariDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))

    def test_root_tree_is_dari_rtl_and_every_page_has_localized_primary_content(self):
        for route in self.routes:
            page = source_path(route["fa_AF"])
            self.assertTrue(page.is_file(), f"missing Dari page: {route['fa_AF']}")
            html = page.read_text(encoding="utf-8")
            self.assertRegex(html, r'<html\s+lang="fa-AF"\s+dir="rtl">')
            self.assertIn(EXPECTED_DARI_HEADINGS[route["id"]], html)
            self.assertNotIn(">Skip to main content<", html)
            self.assertNotIn(">Book a Free Trial<", html)
            self.assertNotIn(">Home<", html)
            self.assertNotIn(">Programs<", html)

    def test_dari_teacher_names_remain_exact_latin_identities_with_bidi_isolation(self):
        for public_path in ("/", "/teachers/"):
            html = source_path(public_path).read_text(encoding="utf-8")
            for name in (
                "Farkhonda Jami",
                "Foruhar Rahmani",
                "Fareshta Suroush",
                "Sadiah Hamid",
            ):
                self.assertRegex(
                    html,
                    rf'<bdi\s+lang="en"\s+dir="ltr">{re.escape(name)}</bdi>',
                )
        protected = source_path("/teachers/").read_text(encoding="utf-8")
        for video_id in (
            "iUMB3pKzS_A",
            "iurgyXOzqFU",
            "OtaIpKZpbMM",
            "fOzc2cM5Twk",
        ):
            self.assertIn(video_id, protected)
        home = source_path("/").read_text(encoding="utf-8")
        for video_id in ("to3h-qq7_FM", "6WxiPdZNcCY"):
            self.assertIn(video_id, home)

    def test_dari_prices_and_phone_numbers_are_visually_ltr(self):
        pricing = source_path("/pricing/").read_text(encoding="utf-8")
        terms = source_path("/terms/").read_text(encoding="utf-8")
        contact = source_path("/contact/").read_text(encoding="utf-8")
        for value in ("€49", "€69", "€99", "€119", "€129", "€229"):
            self.assertRegex(pricing, rf'<bdi\s+dir="ltr">{re.escape(value)}</bdi>')
            self.assertRegex(terms, rf'<bdi\s+dir="ltr">{re.escape(value)}</bdi>')
        self.assertRegex(contact, r'<bdi\s+dir="ltr">\+34 614 401 172</bdi>')

    def test_dari_and_english_legal_material_points_are_equivalent(self):
        dari_privacy = source_path("/privacy-policy/").read_text(encoding="utf-8")
        dari_terms = source_path("/terms/").read_text(encoding="utf-8")
        english_privacy = source_path("/en/privacy-policy/").read_text(encoding="utf-8")
        english_terms = source_path("/en/terms/").read_text(encoding="utf-8")
        for value in ("Salaam Center", "Sabadell, Barcelona", "+34 614 401 172"):
            self.assertIn(value, dari_privacy)
            self.assertIn(value, dari_terms)
            self.assertIn(value, english_privacy)
            self.assertIn(value, english_terms)
        for page in (dari_privacy, dari_terms):
            self.assertIn('datetime="2026-07-22"', page)
            self.assertIn("22 July 2026", page)
        for phrase in (
            "تحلیل‌گر بازدیدکنندگان",
            "پرداخت آنلاین",
            "والد یا سرپرست",
            "خودکار فرستاده نمی‌شود",
        ):
            self.assertTrue(
                phrase in dari_privacy or phrase in dari_terms,
                f"missing Dari legal material point: {phrase}",
            )


class FontAndRtlTests(unittest.TestCase):
    def test_official_vazirmatn_variable_font_and_license_are_pinned(self):
        font = ROOT / "assets" / "fonts" / "vazirmatn" / "Vazirmatn-Variable.woff2"
        license_file = ROOT / "assets" / "fonts" / "vazirmatn" / "OFL.txt"
        self.assertTrue(font.is_file(), "official Vazirmatn WOFF2 is missing")
        self.assertTrue(license_file.is_file(), "Vazirmatn OFL is missing")
        self.assertEqual(hashlib.sha256(font.read_bytes()).hexdigest(), FONT_SHA256)
        self.assertEqual(hashlib.sha256(license_file.read_bytes()).hexdigest(), OFL_SHA256)
        self.assertEqual(font.read_bytes()[:4], b"wOF2")
        self.assertIn(
            "Copyright 2015 The Vazirmatn Project Authors",
            license_file.read_text(encoding="utf-8"),
        )

    def test_dari_css_uses_vazirmatn_and_logical_directional_properties(self):
        css = (ROOT / "assets" / "css" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('@font-face', css)
        self.assertIn('font-family: "Vazirmatn"', css)
        self.assertIn('/assets/fonts/vazirmatn/Vazirmatn-Variable.woff2', css)
        self.assertIn('font-weight: 100 900', css)
        self.assertIn('font-display: swap', css)
        self.assertRegex(css, r'html\[lang="fa-AF"\][\s\S]*?input[\s\S]*?textarea')
        self.assertIn('html[dir="rtl"]', css)
        self.assertIn('padding-inline-start', css)
        self.assertIn('border-inline-start', css)
        self.assertNotRegex(css, r'fonts\.(?:googleapis|gstatic)\.com')

    def test_only_dari_pages_preload_the_local_font(self):
        routes = json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))
        preload = (
            '<link rel="preload" href="/assets/fonts/vazirmatn/'
            'Vazirmatn-Variable.woff2" as="font" type="font/woff2" crossorigin />'
        )
        for route in routes:
            dari = source_path(route["fa_AF"]).read_text(encoding="utf-8")
            english = source_path(route["en"]).read_text(encoding="utf-8")
            self.assertEqual(dari.count(preload), 1, route["fa_AF"])
            self.assertNotIn("Vazirmatn-Variable.woff2", english, route["en"])


class LanguageSwitcherAndSeoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))

    def test_every_page_has_header_and_footer_equivalent_language_switches(self):
        for route in self.routes:
            dari = source_path(route["fa_AF"]).read_text(encoding="utf-8")
            english = source_path(route["en"]).read_text(encoding="utf-8")
            self.assertEqual(dari.count("data-language-switch"), 2, route["fa_AF"])
            self.assertEqual(english.count("data-language-switch"), 2, route["en"])
            self.assertEqual(
                dari.count(f'href="{route["en"]}" data-language-switch'),
                2,
                route["fa_AF"],
            )
            self.assertEqual(
                english.count(f'href="{route["fa_AF"]}" data-language-switch'),
                2,
                route["en"],
            )
            self.assertIn('aria-label="Switch to English"', dari)
            self.assertIn('aria-label="تغییر زبان به دری"', english)
            self.assertNotRegex(dari + english, r"[🇦-🇿]{2}")

    def test_every_pair_has_self_canonical_and_reciprocal_hreflang(self):
        for route in self.routes:
            for language in ("fa_AF", "en"):
                html = source_path(route[language]).read_text(encoding="utf-8")
                canonical = f'https://salaam.center{route[language]}'
                dari_url = f'https://salaam.center{route["fa_AF"]}'
                english_url = f'https://salaam.center{route["en"]}'
                self.assertIn(f'<link rel="canonical" href="{canonical}"', html)
                self.assertIn(
                    f'<link rel="alternate" hreflang="fa-AF" href="{dari_url}"', html
                )
                self.assertIn(
                    f'<link rel="alternate" hreflang="en" href="{english_url}"', html
                )
                self.assertIn(
                    f'<link rel="alternate" hreflang="x-default" href="{dari_url}"', html
                )
                self.assertNotIn("https://www.salaam.center", html)
                self.assertNotIn("salaamcenter.org", html)

    def test_page_locale_metadata_and_home_structured_data_are_localized(self):
        for route in self.routes:
            dari = source_path(route["fa_AF"]).read_text(encoding="utf-8")
            english = source_path(route["en"]).read_text(encoding="utf-8")
            self.assertIn('<meta property="og:locale" content="fa_AF"', dari)
            self.assertIn('<meta property="og:locale:alternate" content="en_GB"', dari)
            self.assertIn('<meta property="og:locale" content="en_GB"', english)
            self.assertIn('<meta property="og:locale:alternate" content="fa_AF"', english)
        dari_home = source_path("/").read_text(encoding="utf-8")
        english_home = source_path("/en/").read_text(encoding="utf-8")
        self.assertIn('"inLanguage": "fa-AF"', dari_home)
        self.assertIn('"inLanguage": "en"', english_home)


class SitemapAndIndexabilityTests(unittest.TestCase):
    def test_sitemap_contains_exactly_twenty_eight_localized_canonical_urls(self):
        sitemap = ROOT / "sitemap.xml"
        tree = ET.parse(sitemap)
        root = tree.getroot()
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "xhtml": "http://www.w3.org/1999/xhtml",
        }
        entries = root.findall("sm:url", ns)
        locations = [entry.findtext("sm:loc", namespaces=ns) for entry in entries]
        routes = json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))
        expected = {
            f'https://salaam.center{route[language]}'
            for route in routes
            if route["sitemap"]
            for language in ("fa_AF", "en")
        }
        self.assertEqual(len(entries), 28)
        self.assertEqual(set(locations), expected)
        for entry in entries:
            alternates = {
                link.attrib["hreflang"]: link.attrib["href"]
                for link in entry.findall("xhtml:link", ns)
            }
            location = entry.findtext("sm:loc", namespaces=ns)
            route = next(
                route
                for route in routes
                if location in {
                    f'https://salaam.center{route["fa_AF"]}',
                    f'https://salaam.center{route["en"]}',
                }
            )
            self.assertEqual(
                alternates,
                {
                    "fa-AF": f'https://salaam.center{route["fa_AF"]}',
                    "en": f'https://salaam.center{route["en"]}',
                    "x-default": f'https://salaam.center{route["fa_AF"]}',
                },
            )

    def test_only_success_and_not_found_pages_are_noindex(self):
        routes = json.loads(ROUTE_MANIFEST.read_text(encoding="utf-8"))
        for route in routes:
            for language in ("fa_AF", "en"):
                html = source_path(route[language]).read_text(encoding="utf-8")
                if route["indexable"]:
                    self.assertNotRegex(html, r'<meta\s+name="robots"[^>]*noindex')
                else:
                    self.assertIn('<meta name="robots" content="noindex, nofollow"', html)
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertIn("Sitemap: https://salaam.center/sitemap.xml", robots)
        self.assertNotIn("Disallow: /en", robots)


class BilingualRuntimeBoundaryTests(unittest.TestCase):
    def test_boundary_models_both_language_trees_and_local_font_assets(self):
        from scripts.deployment_boundary import (
            PAGE_ROUTE_SPECS,
            PUBLIC_PAGE_SOURCES,
            PUBLIC_RUNTIME_ASSETS,
            deployment_boundary_errors,
            expected_redirect_rules,
        )

        self.assertEqual(len(PAGE_ROUTE_SPECS), 30)
        self.assertEqual(len(PUBLIC_PAGE_SOURCES), 32)
        self.assertIn("en/404.html", PUBLIC_PAGE_SOURCES)
        self.assertIn(
            "assets/fonts/vazirmatn/Vazirmatn-Variable.woff2",
            PUBLIC_RUNTIME_ASSETS,
        )
        self.assertIn("assets/fonts/vazirmatn/OFL.txt", PUBLIC_RUNTIME_ASSETS)
        rules = expected_redirect_rules()
        self.assertIn("/en/* /en/__salaam_not_found__ 200", rules)
        self.assertEqual(rules[-1], "/* /__salaam_not_found__ 200")
        self.assertEqual(deployment_boundary_errors(ROOT, PUBLIC_PAGE_SOURCES), ())


class LocalizationReadinessTests(unittest.TestCase):
    def test_launch_configuration_records_verified_bilingual_state(self):
        config = json.loads(
            (ROOT / "config" / "launch-readiness.json").read_text(encoding="utf-8")
        )
        required = {
            "default_language",
            "supported_languages",
            "english_path_prefix",
            "automatic_language_redirect",
            "dari_direction",
            "english_direction",
            "dari_font",
            "localized_route_pairs_verified",
            "hreflang_verified",
            "bilingual_sitemap_verified",
        }
        self.assertTrue(required <= set(config), "bilingual readiness fields are missing")
        self.assertEqual(config.get("default_language"), "fa-AF")
        self.assertEqual(config["supported_languages"], ["fa-AF", "en"])
        self.assertEqual(config["english_path_prefix"], "/en")
        self.assertFalse(config["automatic_language_redirect"])
        self.assertEqual(config["dari_direction"], "rtl")
        self.assertEqual(config["english_direction"], "ltr")
        self.assertEqual(config["dari_font"], "Vazirmatn")
        self.assertTrue(config["localized_route_pairs_verified"])
        self.assertTrue(config["hreflang_verified"])
        self.assertTrue(config["bilingual_sitemap_verified"])


if __name__ == "__main__":
    unittest.main()
