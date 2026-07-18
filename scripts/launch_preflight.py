"""Offline, read-only launch readiness checks for Salaam Center."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit


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
ENDPOINT_RE = re.compile(r"https://formspree\.io/f/[A-Za-z0-9_-]{5,}$")
ACTIVE_ENDPOINT_RE = re.compile(r"https://formspree\.io/f/[A-Za-z0-9_-]{5,}(?![A-Za-z0-9_-])")
ANALYTICS_RE = re.compile(
    r"googletagmanager|google-analytics|\bgtag\s*\(|\bfbq\s*\(|connect\.facebook\.net|meta pixel",
    re.I,
)
PAYMENT_RE = re.compile(r"stripe\.com|paypal\.com|checkout\.js|buy now|pay now", re.I)
SEARCH_CONSOLE_RE = re.compile(r"google-site-verification|search console verification", re.I)
PLACEHOLDER_RE = re.compile(
    r"FORM_ID|\bTBD\b|\bTODO\b|pre-launch|prelaunch|being prepared|not yet open|"
    r"\bpending\b|not active yet|will only become active|(?<![-_])\bplaceholder\b|not operationally verified",
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


def valid_endpoint(value: object) -> bool:
    if not isinstance(value, str) or not ENDPOINT_RE.fullmatch(value):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and parsed.netloc == "formspree.io" and "@" not in value


def executable_source() -> str:
    scripts = (ROOT / "assets/js/main.js", ROOT / "assets/js/trial-form.js")
    return "\n".join(path.read_text(encoding="utf-8") for path in scripts if path.is_file())


def deployment_workflow_exists() -> bool:
    workflows = ROOT / ".github/workflows"
    if not workflows.is_dir():
        return False
    deployment_markers = (
        "actions/deploy-pages", "actions/upload-pages-artifact", "github-pages",
        "pages build and deployment", "deploy to pages", "pages: write",
    )
    for path in (*workflows.glob("*.yml"), *workflows.glob("*.yaml")):
        text = path.read_text(encoding="utf-8").casefold()
        if "deploy" in path.stem.casefold() or "pages" in path.stem.casefold() or any(marker in text for marker in deployment_markers):
            return True
    return False


def success_flow_is_protected(success: str, script: str) -> bool:
    direct_state = re.search(r"data-success-state=['\"]direct['\"]", success) is not None
    confirmed_hidden = re.search(
        r"<[a-z][^>]*(?=[^>]*data-success-state=['\"]confirmed['\"])(?=[^>]*\bhidden\b)[^>]*>",
        success,
        re.I,
    ) is not None
    required_script_evidence = (
        "sessionStorage.getItem(markerKey)",
        "sessionStorage.removeItem(markerKey)",
        "marker.confirmed !== true",
        "response.ok",
        "payload.ok",
        "sessionStorage.setItem(markerKey",
        "JSON.stringify({ confirmed: true, at:",
        'window.location.assign("/success/")',
    )
    if not direct_state or not confirmed_hidden or not all(value in script for value in required_script_evidence):
        return False
    response_index = script.index("response.ok")
    payload_index = script.index("payload.ok")
    marker_index = script.index("sessionStorage.setItem(markerKey")
    redirect_index = script.index('window.location.assign("/success/")')
    return response_index < marker_index and payload_index < marker_index < redirect_index


def common_safety_checks(result: Result, source: dict[str, str]) -> None:
    public_joined = "\n".join(source.values())
    executable_joined = public_joined + "\n" + executable_source()
    result.require(all(source.values()), "all 16 public HTML pages exist")
    result.require(not ANALYTICS_RE.search(executable_joined), "no analytics or advertising pixels")
    result.require(not PAYMENT_RE.search(executable_joined), "no payment integration")
    result.require(all(name in public_joined for name in PROTECTED_NAMES), "all protected teacher content remains")
    result.require(all(video_id in public_joined for video_id in PROTECTED_VIDEO_IDS), "all protected teacher and student video IDs remain")
    pricing = source.get("pricing/index.html", "")
    result.require(all(price in pricing for price in APPROVED_PRICES), "public prices remain approved")
    public_without_docs = executable_joined.casefold()
    result.require("€8 per completed" not in public_without_docs and "teacher rate" not in public_without_docs, "no internal teacher-cost information is public")


def prelaunch(config: dict, source: dict[str, str], result: Result) -> None:
    result.require(config.get("site_mode") == "prelaunch", "site_mode is prelaunch")
    result.require(all('name="robots" content="noindex, nofollow"' in page for page in source.values()), "noindex, nofollow on every public HTML page")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    result.require("User-agent: *" in robots and "Disallow: /" in robots, "robots.txt blocks crawling")
    result.require(config.get("booking_endpoint") == "", "booking_endpoint is empty")
    form = source.get("book-trial/index.html", "")
    inactive_form = (
        'data-endpoint=""' in form
        and 'data-endpoint-verified="false"' in form
        and re.search(r'<button[^>]+type="submit"[^>]+disabled', form) is not None
        and "<fieldset disabled" in form
    )
    result.require(inactive_form, "no active form submission is possible")
    public_code = "\n".join(source.values()) + "\n" + executable_source()
    result.require(not ACTIVE_ENDPOINT_RE.search(public_code), "no active Formspree endpoint exists in public code")
    result.require(not (ROOT / "CNAME").exists(), "no CNAME")
    result.require(not deployment_workflow_exists(), "no deployment workflow")
    result.require(not SEARCH_CONSOLE_RE.search(public_code), "no Search Console verification")
    for flag in (
        "contact_email_verified", "booking_endpoint_verified",
        "formspree_domain_restriction_confirmed", "privacy_policy_final_approved",
        "terms_final_approved", "domain_verified_with_github",
        "github_pages_enabled", "dns_configured", "https_confirmed",
        "search_console_enabled",
    ):
        result.require(config.get(flag) is False, f"{flag} is not claimed")
    common_safety_checks(result, source)
    if result.failures:
        print(f"FAIL: prelaunch readiness ({len(result.failures)} requirement(s))")
    else:
        print("PASS: prelaunch readiness")


def production(config: dict, source: dict[str, str], result: Result) -> None:
    requirements = {
        "site_mode is production": config.get("site_mode") == "production",
        "contact_email_verified is true": config.get("contact_email_verified") is True,
        "booking_endpoint is a verified HTTPS Formspree form-ID URL": valid_endpoint(config.get("booking_endpoint")),
        "booking_endpoint_verified is true": config.get("booking_endpoint_verified") is True,
        "formspree_domain_restriction_confirmed is true": config.get("formspree_domain_restriction_confirmed") is True,
        "legal_controller_name is present": bool(str(config.get("legal_controller_name", "")).strip()),
        "legal_controller_address is present": bool(str(config.get("legal_controller_address", "")).strip()),
        "privacy_policy_final_approved is true": config.get("privacy_policy_final_approved") is True,
        "terms_final_approved is true": config.get("terms_final_approved") is True,
        "domain_verified_with_github is true": config.get("domain_verified_with_github") is True,
        "github_pages_enabled is true": config.get("github_pages_enabled") is True,
        "dns_configured is true": config.get("dns_configured") is True,
        "https_confirmed is true": config.get("https_confirmed") is True,
        "analytics_mode remains none": config.get("analytics_mode") == "none",
    }
    for label, condition in requirements.items():
        result.require(condition, label)
    result.require(all('name="robots" content="noindex, nofollow"' not in page for page in source.values()), "noindex, nofollow removed from production pages")
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    result.require("Disallow: /" not in robots, "robots.txt allows intended crawling")
    sitemap = ROOT / "sitemap.xml"
    sitemap_valid = False
    if sitemap.is_file():
        try:
            sitemap_root = ET.parse(sitemap).getroot()
            namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
            location_nodes = sitemap_root.findall(f"{{{namespace}}}url/{{{namespace}}}loc")
            all_location_nodes = [node for node in sitemap_root.iter() if node.tag.endswith("loc")]
            locations = [node.text or "" for node in location_nodes]
            sitemap_valid = (
                sitemap_root.tag == f"{{{namespace}}}urlset"
                and len(location_nodes) == len(all_location_nodes)
                and len(locations) == len(set(locations))
                and set(locations) == SITEMAP_URLS
            )
        except ET.ParseError:
            sitemap_valid = False
    result.require(sitemap_valid, "sitemap.xml is present and valid")
    canonical_ok = all(
        f'<link rel="canonical" href="{PRODUCTION_ORIGIN + ROUTES[relative]}"' in page
        and "salaamcenter.org" not in page
        for relative, page in source.items()
    )
    result.require(canonical_ok, "canonical URLs point only to https://salaam.center")
    joined = "\n".join(source.values())
    production_content = joined + "\n" + json.dumps(config, ensure_ascii=False, sort_keys=True)
    result.require(not PLACEHOLDER_RE.search(production_content), "no placeholder strings remain")
    trial = source.get("book-trial/index.html", "")
    endpoint = str(config.get("booking_endpoint", ""))
    form_match = re.search(r"<form\b.*?</form>", trial, re.S)
    form_markup = form_match.group(0) if form_match else ""
    active = (
        valid_endpoint(endpoint)
        and f'data-endpoint="{endpoint}"' in form_markup
        and 'data-endpoint-verified="true"' in form_markup
        and re.search(r"\bdisabled\b", form_markup) is None
    )
    result.require(bool(active), "active booking form")
    success = source.get("success/index.html", "")
    trial_script = (ROOT / "assets/js/trial-form.js").read_text(encoding="utf-8")
    result.require(success_flow_is_protected(success, trial_script), "success flow requires confirmed submission")
    cname = ROOT / "CNAME"
    result.require(cname.is_file() and cname.read_text(encoding="utf-8").strip() == "salaam.center", "CNAME contains only salaam.center")
    search_console_present = SEARCH_CONSOLE_RE.search(joined) is not None
    search_console_flag = config.get("search_console_enabled")
    result.require(
        isinstance(search_console_flag, bool) and (search_console_flag or not search_console_present),
        "search_console_enabled is explicit and consistent with repository verification",
    )
    common_safety_checks(result, source)
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
