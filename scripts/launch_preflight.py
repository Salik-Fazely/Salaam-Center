"""Offline, read-only launch readiness checks for Salaam Center."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from scripts.deployment_boundary import deployment_boundary_is_safe
except ModuleNotFoundError:  # Support direct execution outside the repository cwd.
    from deployment_boundary import deployment_boundary_is_safe


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/launch-readiness.json"
PUBLIC_PAGES = (
    "index.html", "our-approach/index.html", "programs/index.html",
    "programs/quran/index.html", "programs/dari-persian/index.html",
    "programs/afghan-culture-islamic-ethics/index.html", "teachers/index.html",
    "how-it-works/index.html", "pricing/index.html", "about/index.html",
    "book-trial/index.html", "contact/index.html", "privacy-policy/index.html",
    "terms/index.html", "success/index.html", "404.html",
)
NOINDEX_PAGES = ("success/index.html", "404.html")
INDEXABLE_PAGES = tuple(page for page in PUBLIC_PAGES if page not in NOINDEX_PAGES)
PRODUCTION_ORIGIN = "https://salaam.center"
PRODUCTION_DOMAINS = ["salaam.center", "www.salaam.center"]
APPROVED_WHATSAPP_NUMBER = "34614401172"
WHATSAPP_URL = f"https://wa.me/{APPROVED_WHATSAPP_NUMBER}"
LEGAL_CONTROLLER_NAME = "Salaam Center"
LEGAL_CONTROLLER_ADDRESS = "Sabadell, Barcelona"
ROUTES = {
    "index.html": "/",
    "404.html": "/404.html",
    **{
        path: f"/{path.removesuffix('index.html')}"
        for path in PUBLIC_PAGES
        if path not in {"index.html", "404.html"}
    },
}
SITEMAP_URLS = {
    PRODUCTION_ORIGIN + route
    for path, route in ROUTES.items()
    if path not in {"success/index.html", "404.html"}
}
PROTECTED_NAMES = ("Farkhonda Jami", "Foruhar Rahmani", "Fareshta Suroush", "Sadiah Hamid")
PROTECTED_VIDEO_IDS = (
    "iUMB3pKzS_A", "iurgyXOzqFU", "OtaIpKZpbMM", "fOzc2cM5Twk",
    "to3h-qq7_FM", "6WxiPdZNcCY",
)
APPROVED_PRICES = ("€49 total", "€69 total", "€99 total", "€119 total", "€129 total", "€229 total")
ANALYTICS_RE = re.compile(
    r"googletagmanager|google-analytics|\bgtag\s*\(|\bfbq\s*\(|connect\.facebook\.net|meta pixel",
    re.I,
)
PAYMENT_RE = re.compile(r"stripe\.com|paypal\.com|checkout\.js|buy now|pay now", re.I)
SEARCH_CONSOLE_RE = re.compile(r"google-site-verification|search console verification", re.I)
PLACEHOLDER_RE = re.compile(
    r"FORM_ID|WHATSAPP_NUMBER_DIGITS|\bTBD\b|\bTODO\b|pre-launch|prelaunch|"
    r"being prepared|not yet open|\bnot final\b|\bpending\b|future activation|"
    r"not active yet|will only become active|when enrolment opens|when enrollment opens|"
    r"\bplaceholder\b|not operationally verified",
    re.I,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|mailto:", re.I)
FORMSPREE_RE = re.compile(r"formspree(?:\.io)?", re.I)
NETWORK_SUBMISSION_RE = re.compile(
    r"(?<![\w$.])fetch\s*\((?![^()\n]*\)\s*\{)|"
    r"\b(?:window|globalThis|self)\s*\.\s*fetch\s*\(|"
    r"\b(?:new\s+)?XMLHttpRequest\b|"
    r"\bnavigator\s*\.\s*sendBeacon\s*\(|"
    r"(?:\(\s*)?\bnew\s+Image\s*\([^)]*\)\s*(?:\)\s*)?\.\s*src\s*=",
    re.I,
)
STORAGE_RE = re.compile(r"\b(?:localStorage|sessionStorage)\b")
WHATSAPP_LINK_RE = re.compile(r"https://wa\.me/[^\s\"'<>]+", re.I)
TRACKING_RE = re.compile(r"[?&](?:utm_[^=&]*|fbclid|gclid|ref)=", re.I)
FALSE_SUCCESS_RE = re.compile(
    r"\b(?:request received|message sent|trial booked|booking confirmed|trial confirmed|"
    r"your trial request was submitted|we received your request)\b",
    re.I,
)
ECONOMICS_LEAK_RE = re.compile(
    r"\bteacher(?:s'|s)?[-\s]+(?:rate|pay|payment|compensation|wage|salary|"
    r"earnings|payout|cost|margin|economics)\b|"
    r"\b(?:internal|unit)\s+economics\b|"
    r"\b(?:gross|contribution)\s+margin\b|"
    r"(?:€\s*8(?:[.,]00)?|8(?:[.,]00)?\s*€|EUR\s*8(?:[.,]00)?|"
    r"8(?:[.,]00)?\s*EUR|eight euros?)\s+(?:per|/)\s+(?:each\s+)?"
    r"(?:completed\s+)?(?:(?:40|forty)[-\s]+minute\s+)?(?:class|lesson)\b|"
    r"\bcost\s+per\s+(?:completed\s+)?(?:class|lesson)\b",
    re.I,
)
PRODUCTION_ROBOTS_DIRECTIVES = (
    ("user-agent", "*"),
    ("allow", "/"),
    ("sitemap", f"{PRODUCTION_ORIGIN}/sitemap.xml"),
)
PRELAUNCH_ROBOTS_DIRECTIVES = (("user-agent", "*"), ("disallow", "/"))


class Result:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def require(self, condition: bool, label: str) -> None:
        if condition:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label}")
            self.failures.append(label)


def load_config(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"configuration missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in launch configuration: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("invalid JSON: launch configuration must be an object")
    return value


def pages() -> dict[str, str]:
    output = {}
    for relative in PUBLIC_PAGES:
        path = ROOT / relative
        output[relative] = path.read_text(encoding="utf-8") if path.is_file() else ""
    return output


def text_files_under(relative: str, suffixes: set[str]) -> list[Path]:
    root = ROOT / relative
    if not root.is_dir():
        return []
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.casefold() in suffixes
        ),
        key=lambda path: path.as_posix(),
    )


def executable_source() -> str:
    scripts = text_files_under("assets/js", {".js", ".mjs", ".cjs"})
    return "\n".join(path.read_text(encoding="utf-8") for path in scripts)


def public_supporting_source() -> str:
    paths = (
        text_files_under("partials", {".html"})
        + text_files_under("assets/css", {".css"})
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def public_surface_source(source: dict[str, str], script: str) -> str:
    return "\n".join(source.values()) + "\n" + script + "\n" + public_supporting_source()


def trial_form_source() -> str:
    path = ROOT / "assets/js/trial-form.js"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


class HeadDirectiveParser(HTMLParser):
    """Collect canonical links and robots directives independent of attribute order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.robots: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {
            key.casefold(): (value or "")
            for key, value in attrs
        }
        if tag.casefold() == "link":
            relationships = {
                token.casefold()
                for token in attributes.get("rel", "").split()
            }
            if "canonical" in relationships:
                self.canonicals.append(attributes.get("href", ""))
        elif (
            tag.casefold() == "meta"
            and attributes.get("name", "").strip().casefold() == "robots"
        ):
            self.robots.append(attributes.get("content", ""))


def head_directives(markup: str) -> HeadDirectiveParser:
    parser = HeadDirectiveParser()
    parser.feed(markup)
    return parser


def normalized_meta_directives(value: str) -> tuple[str, ...]:
    return tuple(
        directive
        for directive in re.split(r"[\s,]+", value.strip().casefold())
        if directive
    )


def has_noindex(markup: str) -> bool:
    return any(
        "noindex" in directives or "none" in directives
        for directives in map(normalized_meta_directives, head_directives(markup).robots)
    )


def has_exact_noindex(markup: str) -> bool:
    robots = head_directives(markup).robots
    return (
        len(robots) == 1
        and normalized_meta_directives(robots[0]) == ("noindex", "nofollow")
    )


def canonicals_are_exact(source: dict[str, str]) -> bool:
    if any("salaamcenter.org" in markup.casefold() for markup in source.values()):
        return False
    for relative in PUBLIC_PAGES:
        expected = PRODUCTION_ORIGIN + ROUTES[relative]
        if head_directives(source.get(relative, "")).canonicals != [expected]:
            return False
    return True


def normalized_robots_directives() -> tuple[tuple[str, str], ...] | None:
    path = ROOT / "robots.txt"
    if not path.is_file():
        return None
    directives: list[tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            return None
        field, value = line.split(":", 1)
        field = field.strip().casefold()
        value = value.strip()
        if not field or not value:
            return None
        directives.append((field, value))
    return tuple(directives)


def valid_whatsapp_number(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == APPROVED_WHATSAPP_NUMBER
        and re.fullmatch(r"[1-9]\d{7,14}", value) is not None
    )


def github_pages_workflow_exists() -> bool:
    workflows = ROOT / ".github/workflows"
    if not workflows.is_dir():
        return False
    markers = (
        "actions/deploy-pages", "actions/upload-pages-artifact", "github-pages",
        "pages build and deployment", "pages: write",
    )
    for path in (*workflows.glob("*.yml"), *workflows.glob("*.yaml")):
        text = path.read_text(encoding="utf-8").casefold()
        if any(marker in text for marker in markers):
            return True
    return False


def whatsapp_links_are_valid(source: dict[str, str], script: str, number: object) -> bool:
    if not valid_whatsapp_number(number):
        return False
    required_pages = ("book-trial/index.html", "contact/index.html", "success/index.html")
    if not all(f'href="{WHATSAPP_URL}"' in source.get(page, "") for page in required_pages):
        return False
    joined = "\n".join(source.values()) + "\n" + script
    urls = WHATSAPP_LINK_RE.findall(joined)
    if not urls or any(url not in {WHATSAPP_URL, WHATSAPP_URL + "?text="} for url in urls):
        return False
    return (
        f'"{WHATSAPP_URL}?text="' in script
        and "encodeURIComponent(message)" in script
        and TRACKING_RE.search(joined) is None
        and "api.whatsapp.com" not in joined.casefold()
    )


def client_handoff_is_safe(trial: str, script: str) -> bool:
    form_match = re.search(r"<form\b.*?</form>", trial, re.S | re.I)
    if not form_match:
        return False
    form = form_match.group(0)
    forbidden_fields = re.compile(
        r"name=['\"](?:email|learner_(?:name|first_name|surname)|phone|telephone|mobile|"
        r"date_of_birth|address|medical|privacy_acknowledgement|_gotcha|payment|marketing|file)['\"]",
        re.I,
    )
    script_safe = (
        NETWORK_SUBMISSION_RE.search(script) is None
        and STORAGE_RE.search(script) is None
        and FORMSPREE_RE.search(script) is None
        and "FormData" not in script
        and "URLSearchParams" not in script
        and "location.search" not in script
    )
    return (
        'data-whatsapp-handoff="true"' in form
        and re.search(r"\baction\s*=", form, re.I) is None
        and re.search(r"\bmethod\s*=\s*['\"]?post", form, re.I) is None
        and re.search(r"type=['\"]submit['\"]", form, re.I) is None
        and re.search(r"type=['\"]button['\"][^>]*data-whatsapp-submit", form, re.I) is not None
        and "Continue in WhatsApp" in form
        and forbidden_fields.search(form) is None
        and f'href="{WHATSAPP_URL}"' in trial
        and script_safe
        and "window.open(" in script
        and "window.location.assign(" in script
    )


def success_page_is_truthful(success: str) -> bool:
    folded = success.casefold()
    return (
        "continue your conversation in whatsapp" in folded
        and "cannot confirm" in folded
        and re.search(r"\bpress(?:ed)? send\b", folded) is not None
        and "not booked until salaam center confirms" in folded
        and f'href="{WHATSAPP_URL}"' in success
        and "data-success-state" not in folded
        and "trial-form.js" not in folded
        and FALSE_SUCCESS_RE.search(success) is None
    )


def public_contact_is_whatsapp_only(source: dict[str, str], script: str) -> bool:
    joined = "\n".join(source.values()) + "\n" + script
    return (
        EMAIL_RE.search(joined) is None
        and FORMSPREE_RE.search(joined) is None
        and re.search(r"\btel:", joined, re.I) is None
    )


def sitemap_is_valid() -> bool:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.is_file():
        return False
    try:
        root = ET.parse(sitemap).getroot()
    except ET.ParseError:
        return False
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    if (
        root.tag != f"{{{namespace}}}urlset"
        or root.attrib
        or (root.text and root.text.strip())
    ):
        return False
    locations: list[str] = []
    for url in list(root):
        children = list(url)
        if (
            url.tag != f"{{{namespace}}}url"
            or url.attrib
            or len(children) != 1
            or children[0].tag != f"{{{namespace}}}loc"
            or children[0].attrib
            or list(children[0])
            or (url.text and url.text.strip())
            or (url.tail and url.tail.strip())
            or (children[0].tail and children[0].tail.strip())
        ):
            return False
        location = children[0].text or ""
        if location != location.strip():
            return False
        locations.append(location)
    return (
        len(locations) == len(set(locations))
        and len(locations) == len(SITEMAP_URLS)
        and set(locations) == SITEMAP_URLS
    )


def common_safety_checks(result: Result, config: dict, source: dict[str, str]) -> None:
    public_joined = "\n".join(source.values())
    script = executable_source()
    handoff_script = trial_form_source()
    public_surface = public_surface_source(source, script)
    deployment_safe = deployment_boundary_is_safe(ROOT, PUBLIC_PAGES)
    result.require(all(source.values()), "all 16 public HTML pages exist")
    result.require(config.get("production_origin") == PRODUCTION_ORIGIN, "production_origin is https://salaam.center")
    result.require(config.get("production_domains") == PRODUCTION_DOMAINS, "production domains are exact")
    result.require(config.get("hosting_source") == "cloudflare_pages", "hosting source is Cloudflare Pages")
    result.require(config.get("cloudflare_pages_project") == "salaam-center", "Cloudflare Pages project is salaam-center")
    result.require(config.get("automatic_deployment_from_main") is True, "automatic deployment from main is enabled")
    result.require(
        config.get("deployment_surface_mode") == "static_public_route_allowlist",
        "deployment surface uses static public-route allowlist",
    )
    result.require(
        config.get("pages_functions_enabled") is False,
        "Cloudflare Pages Functions remain disabled",
    )
    result.require(config.get("production_domains_active") is True, "production domains are active")
    result.require(config.get("https_confirmed") is True, "HTTPS is confirmed")
    result.require(config.get("contact_channel") == "whatsapp", "contact_channel is whatsapp")
    result.require(valid_whatsapp_number(config.get("whatsapp_number")), "whatsapp_number is the exact digits-only approved number")
    result.require(config.get("whatsapp_number_verified") is True, "whatsapp_number_verified is true")
    result.require(config.get("whatsapp_link_verified") is True, "whatsapp_link_verified is true")
    result.require(config.get("form_submission_mode") == "client_side_whatsapp_handoff", "form submission mode is client-side WhatsApp handoff")
    result.require(config.get("booking_provider") == "none", "booking_provider is none")
    result.require(config.get("booking_endpoint") == "", "booking_endpoint is empty")
    result.require(config.get("analytics_mode") == "none", "analytics_mode remains none")
    result.require(config.get("search_console_enabled") is False, "search_console_enabled remains false")
    result.require(config.get("github_pages_enabled") is False, "GitHub Pages is disabled")
    result.require(config.get("cname_required") is False, "CNAME is not required")
    result.require(not (ROOT / "CNAME").exists(), "no repository CNAME")
    result.require(not github_pages_workflow_exists(), "no GitHub Pages workflow")
    result.require(
        deployment_safe,
        "unreviewed repository paths fail closed with styled HTTP 404",
    )
    result.require(
        EMAIL_RE.search(public_surface) is None
        and re.search(r"\btel:", public_surface, re.I) is None,
        "no public email contact",
    )
    result.require(FORMSPREE_RE.search(public_surface) is None, "no active Formspree reference")
    result.require(
        NETWORK_SUBMISSION_RE.search(script) is None,
        "no browser network submission",
    )
    result.require(STORAGE_RE.search(script) is None, "no personal-data storage")
    result.require(whatsapp_links_are_valid(source, script, config.get("whatsapp_number")), "exact safe wa.me links")
    result.require(client_handoff_is_safe(source.get("book-trial/index.html", ""), handoff_script), "safe client-side WhatsApp handoff")
    result.require(success_page_is_truthful(source.get("success/index.html", "")), "Success page remains truthful")
    result.require(not ANALYTICS_RE.search(public_surface), "no analytics or advertising pixels")
    result.require(not PAYMENT_RE.search(public_surface), "no payment integration")
    result.require(not SEARCH_CONSOLE_RE.search(public_surface), "no Search Console verification")
    result.require(all(name in public_joined for name in PROTECTED_NAMES), "all protected teacher content remains")
    result.require(all(video_id in public_joined for video_id in PROTECTED_VIDEO_IDS), "all protected teacher and student video IDs remain")
    pricing = source.get("pricing/index.html", "")
    result.require(all(price in pricing for price in APPROVED_PRICES), "public prices remain approved")
    result.require(
        ECONOMICS_LEAK_RE.search(public_surface) is None,
        "no internal teacher-cost information is served by the website",
    )


def readiness_summary(result: Result, label: str) -> None:
    if result.failures:
        print(f"FAIL: {label} ({len(result.failures)} requirement(s))")
    else:
        print(f"PASS: {label}")


def prelaunch(config: dict, source: dict[str, str], result: Result) -> None:
    """Keep the historical entrypoint useful after the production switch."""

    if config.get("site_mode") == "production":
        production(
            config,
            source,
            result,
            readiness_label="prelaunch/backward-compatible readiness",
        )
        return

    result.require(config.get("site_mode") == "prelaunch", "site_mode is prelaunch")
    result.require(
        all(has_exact_noindex(source.get(page, "")) for page in PUBLIC_PAGES),
        "noindex, nofollow on every public HTML page",
    )
    result.require(
        normalized_robots_directives() == PRELAUNCH_ROBOTS_DIRECTIVES,
        "robots.txt blocks crawling",
    )
    result.require(
        config.get("privacy_policy_final_approved") is False,
        "privacy_policy_final_approved is not claimed",
    )
    result.require(
        config.get("terms_final_approved") is False,
        "terms_final_approved is not claimed",
    )
    result.require(
        config.get("search_console_enabled") is False,
        "search_console_enabled is not claimed",
    )
    common_safety_checks(result, config, source)
    readiness_summary(result, "prelaunch/backward-compatible readiness")


def production(
    config: dict,
    source: dict[str, str],
    result: Result,
    *,
    readiness_label: str = "production readiness",
) -> None:
    requirements = {
        "site_mode is production": config.get("site_mode") == "production",
        "legal_controller_name is exact": config.get("legal_controller_name") == LEGAL_CONTROLLER_NAME,
        "legal_controller_address is exact": config.get("legal_controller_address") == LEGAL_CONTROLLER_ADDRESS,
        "privacy_policy_final_approved is true": config.get("privacy_policy_final_approved") is True,
        "terms_final_approved is true": config.get("terms_final_approved") is True,
        "whatsapp_live_link_tested is true": config.get("whatsapp_live_link_tested") is True,
    }
    for label, condition in requirements.items():
        result.require(condition, label)
    result.require(
        all(not has_noindex(source.get(page, "")) for page in INDEXABLE_PAGES),
        "intended indexable pages have no noindex directive",
    )
    result.require(
        all(has_exact_noindex(source.get(page, "")) for page in NOINDEX_PAGES),
        "Success and 404 retain exact noindex, nofollow",
    )
    result.require(
        normalized_robots_directives() == PRODUCTION_ROBOTS_DIRECTIVES,
        "robots.txt allows intended crawling",
    )
    result.require(sitemap_is_valid(), "sitemap.xml is present and valid")
    result.require(
        canonicals_are_exact(source),
        "canonical URLs point only to https://salaam.center",
    )
    production_content = (
        public_surface_source(source, executable_source())
        + "\n"
        + json.dumps(config, ensure_ascii=False, sort_keys=True)
    )
    result.require(not PLACEHOLDER_RE.search(production_content), "no placeholder strings remain")
    common_safety_checks(result, config, source)
    readiness_summary(result, readiness_label)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("prelaunch", "production"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        config = load_config(args.config)
        source = pages()
        result = Result()
        (prelaunch if args.mode == "prelaunch" else production)(config, source, result)
        return 1 if result.failures else 0
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
