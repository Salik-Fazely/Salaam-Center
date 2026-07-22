"""Offline, read-only launch readiness checks for Salaam Center."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
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
PRODUCTION_ORIGIN = "https://salaam.center"
PRODUCTION_DOMAINS = ["salaam.center", "www.salaam.center"]
APPROVED_WHATSAPP_NUMBER = "34614401172"
WHATSAPP_URL = f"https://wa.me/{APPROVED_WHATSAPP_NUMBER}"
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
    r"being prepared|not yet open|\bpending\b|not active yet|will only become active|"
    r"(?<![-_])\bplaceholder\b|not operationally verified",
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


def executable_source() -> str:
    scripts = (ROOT / "assets/js/main.js", ROOT / "assets/js/trial-form.js")
    return "\n".join(path.read_text(encoding="utf-8") for path in scripts if path.is_file())


def trial_form_source() -> str:
    path = ROOT / "assets/js/trial-form.js"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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
    locations = [node.text or "" for node in root.findall(f"{{{namespace}}}url/{{{namespace}}}loc")]
    all_locations = [node for node in root.iter() if node.tag.endswith("loc")]
    return (
        root.tag == f"{{{namespace}}}urlset"
        and len(locations) == len(all_locations)
        and len(locations) == len(set(locations))
        and set(locations) == SITEMAP_URLS
    )


def common_safety_checks(result: Result, config: dict, source: dict[str, str]) -> None:
    public_joined = "\n".join(source.values())
    script = executable_source()
    handoff_script = trial_form_source()
    executable_joined = public_joined + "\n" + script
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
    result.require(config.get("github_pages_enabled") is False, "GitHub Pages is disabled")
    result.require(config.get("cname_required") is False, "CNAME is not required")
    result.require(not (ROOT / "CNAME").exists(), "no repository CNAME")
    result.require(not github_pages_workflow_exists(), "no GitHub Pages workflow")
    result.require(
        deployment_safe,
        "unreviewed repository paths fail closed with styled HTTP 404",
    )
    result.require(public_contact_is_whatsapp_only(source, script), "no public email contact")
    result.require(FORMSPREE_RE.search(executable_joined) is None, "no active Formspree reference")
    result.require(
        NETWORK_SUBMISSION_RE.search(handoff_script) is None,
        "no browser network submission",
    )
    result.require(STORAGE_RE.search(script) is None, "no personal-data storage")
    result.require(whatsapp_links_are_valid(source, script, config.get("whatsapp_number")), "exact safe wa.me links")
    result.require(client_handoff_is_safe(source.get("book-trial/index.html", ""), handoff_script), "safe client-side WhatsApp handoff")
    result.require(success_page_is_truthful(source.get("success/index.html", "")), "Success page remains truthful")
    result.require(not ANALYTICS_RE.search(executable_joined), "no analytics or advertising pixels")
    result.require(not PAYMENT_RE.search(executable_joined), "no payment integration")
    result.require(not SEARCH_CONSOLE_RE.search(executable_joined), "no Search Console verification")
    result.require(all(name in public_joined for name in PROTECTED_NAMES), "all protected teacher content remains")
    result.require(all(video_id in public_joined for video_id in PROTECTED_VIDEO_IDS), "all protected teacher and student video IDs remain")
    pricing = source.get("pricing/index.html", "")
    result.require(all(price in pricing for price in APPROVED_PRICES), "public prices remain approved")
    folded = executable_joined.casefold()
    result.require(
        deployment_safe
        and "€8 per completed" not in folded
        and "teacher rate" not in folded,
        "no internal teacher-cost information is served by the website",
    )


def prelaunch(config: dict, source: dict[str, str], result: Result) -> None:
    result.require(config.get("site_mode") == "prelaunch", "site_mode is prelaunch")
    result.require(all('name="robots" content="noindex, nofollow"' in page for page in source.values()), "noindex, nofollow on every public HTML page")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    result.require("User-agent: *" in robots and "Disallow: /" in robots, "robots.txt blocks crawling")
    result.require(config.get("privacy_policy_final_approved") is False, "privacy_policy_final_approved is not claimed")
    result.require(config.get("terms_final_approved") is False, "terms_final_approved is not claimed")
    result.require(config.get("search_console_enabled") is False, "search_console_enabled is not claimed")
    common_safety_checks(result, config, source)
    if result.failures:
        print(f"FAIL: prelaunch readiness ({len(result.failures)} requirement(s))")
    else:
        print("PASS: prelaunch readiness")


def production(config: dict, source: dict[str, str], result: Result) -> None:
    requirements = {
        "site_mode is production": config.get("site_mode") == "production",
        "legal_controller_name is present": bool(str(config.get("legal_controller_name", "")).strip()),
        "legal_controller_address is present": bool(str(config.get("legal_controller_address", "")).strip()),
        "privacy_policy_final_approved is true": config.get("privacy_policy_final_approved") is True,
        "terms_final_approved is true": config.get("terms_final_approved") is True,
        "whatsapp_live_link_tested is true": config.get("whatsapp_live_link_tested") is True,
    }
    for label, condition in requirements.items():
        result.require(condition, label)
    result.require(all('name="robots" content="noindex, nofollow"' not in page for page in source.values()), "noindex, nofollow removed from production pages")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    result.require("Disallow: /" not in robots, "robots.txt allows intended crawling")
    result.require(sitemap_is_valid(), "sitemap.xml is present and valid")
    canonical_ok = all(
        f'<link rel="canonical" href="{PRODUCTION_ORIGIN + ROUTES[relative]}"' in page
        and "salaamcenter.org" not in page
        for relative, page in source.items()
    )
    result.require(canonical_ok, "canonical URLs point only to https://salaam.center")
    joined = "\n".join(source.values())
    production_content = joined + "\n" + json.dumps(config, ensure_ascii=False, sort_keys=True)
    result.require(not PLACEHOLDER_RE.search(production_content), "no placeholder strings remain")
    common_safety_checks(result, config, source)
    print("EXPECTED BLOCKED PRODUCTION STATE" if result.failures else "PASS: production readiness")


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
