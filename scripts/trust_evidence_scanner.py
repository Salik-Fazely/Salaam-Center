from dataclasses import dataclass
from enum import Enum
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import sys
from typing import Collection, Sequence
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True

try:
    from scripts.deployment_boundary import PUBLIC_PAGE_SOURCES, deployment_boundary_errors
except ModuleNotFoundError:  # Support direct execution outside the repository cwd.
    from deployment_boundary import PUBLIC_PAGE_SOURCES, deployment_boundary_errors


PUBLIC_HTML_PATHS = PUBLIC_PAGE_SOURCES

DOCUMENTATION_PATHS = frozenset({
    "SALAM-CENTER-APPROVED-FACTS.md",
    "MIGRATION-SOURCE.md",
    "docs/COMMERCIAL-AND-ENROLMENT.md",
})

# Skip links are in-page controls, not public HTML routes. Any other clean internal
# route must resolve to a manifest entry before it can be linked from a public page.
NON_PAGE_INTERNAL_HREFS = frozenset({"#main-content"})


class SurfaceType(str, Enum):
    HTML = "HTML"
    METADATA = "metadata"
    STRUCTURED_DATA = "structured data"
    EXECUTABLE_JAVASCRIPT = "executable JavaScript"


class Classification(str, Enum):
    PUBLIC = "public"
    DOCUMENTATION_ONLY = "documentation only"
    INACTIVE = "inactive"


@dataclass(frozen=True)
class SurfaceText:
    path: Path
    surface: SurfaceType
    text: str
    start_line: int = 1
    classification: Classification = Classification.PUBLIC
    line_map: tuple[int, ...] = ()
    protected_ranges: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class Finding:
    path: Path
    surface: SurfaceType
    category: str
    rule: str
    line: int
    excerpt: str
    classification: Classification

    @property
    def is_failure(self) -> bool:
        return self.classification is Classification.PUBLIC


@dataclass(frozen=True)
class ScanReport:
    public_surfaces: tuple[SurfaceText, ...]
    public_html_paths: tuple[Path, ...]
    public_script_paths: tuple[Path, ...]
    findings: tuple[Finding, ...]

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.classification is Classification.PUBLIC
        )

    @property
    def documentation(self) -> tuple[Finding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.classification is Classification.DOCUMENTATION_ONLY
        )

    @property
    def html_paths(self) -> tuple[Path, ...]:
        return self.public_html_paths

    @property
    def referenced_scripts(self) -> tuple[Path, ...]:
        return self.public_script_paths


APPROVED_TEACHER_EVIDENCE = (
    (
        "Farkhonda Jami",
        "2 years teaching Tajweed and Tafsir",
        "iUMB3pKzS_A",
    ),
    ("Foruhar Rahmani", "2 years teaching Tajweed", "iurgyXOzqFU"),
    ("Fareshta Suroush", "2 years teaching Tajweed", "OtaIpKZpbMM"),
    (
        "Sadiah Hamid",
        "6 years teaching Tajweed, Hifz, and Quranic recitation",
        "fOzc2cM5Twk",
    ),
)

APPROVED_STUDENT_EVIDENCE = (
    (
        "to3h-qq7_FM",
        "A short message of appreciation from a student sharing their learning "
        "experience.",
    ),
    (
        "6WxiPdZNcCY",
        "A student shares thanks and happiness about their Quran learning journey.",
    ),
)

APPROVED_PRIVATE_PLAN_EVIDENCE = (
    (4, 1, 4, 49, None),
    (4, 2, 8, 69, None),
    (4, 4, 16, 99, None),
    (12, 1, 12, 119, 28),
    (12, 2, 24, 129, 78),
    (12, 4, 48, 229, 68),
)

APPROVED_CERTIFICATE_EVIDENCE = (
    "Digital certificate of completion for eligible 12-week-plan learners.",
    "At least 80% of scheduled paid classes must be completed.",
    "Any outstanding payment obligation must be resolved.",
    "The certificate acknowledges participation and completion.",
    "It is not an academic accreditation, qualification or government-recognised certificate.",
)

APPROVED_CERTIFICATE_EVIDENCE_FA_AF = (
    "تصدیق‌نامهٔ دیجیتالی تکمیل برای شاگردان واجد شرایط برنامهٔ 12 هفته‌ای",
    "دست‌کم 80% صنف‌های پولی برنامه‌ریزی‌شده باید تکمیل شود.",
    "هرگونه مکلفیت پرداخت‌نشده باید حل شود.",
    "این تصدیق‌نامه اشتراک و تکمیل برنامه را تأیید می‌کند.",
    "این سند اعتباردهی تحصیلی، مدرک یا تصدیق‌نامهٔ به‌رسمیت‌شناخته‌شده از سوی دولت نیست.",
)

APPROVED_TERMS_PLAN_EVIDENCE = tuple(
    f"{weeks}-week plan, {frequency} "
    f"{'class' if frequency == 1 else 'classes'} per week: "
    f"{classes} paid classes, €{price} total."
    for weeks, frequency, classes, price, _ in APPROVED_PRIVATE_PLAN_EVIDENCE
)

APPROVED_TERMS_PLAN_EVIDENCE_FA_AF = tuple(
    f"برنامهٔ {weeks} هفته‌ای، {frequency} صنف در هفته: "
    f"{classes} صنف پولی، مجموع €{price}."
    for weeks, frequency, classes, price, _ in APPROVED_PRIVATE_PLAN_EVIDENCE
)

_APPROVED_LEGAL_DISCLOSURES = {
    "privacy-policy/index.html": (
        "Operator and controller: Salaam Center",
        "Correspondence address: Sabadell, Barcelona",
    ),
    "terms/index.html": (
        "Operator: Salaam Center",
        "Correspondence address: Sabadell, Barcelona",
    ),
}

_APPROVED_TEACHER_PATHS = frozenset({"index.html", "teachers/index.html"})
_APPROVED_STUDENT_PATHS = frozenset({"index.html"})
_APPROVED_CERTIFICATE_PATHS = frozenset({
    "pricing/index.html",
    "terms/index.html",
})
_VISIBLE_BOUNDARY = "\n\u2063\n"


@dataclass(frozen=True)
class _ClaimRule:
    category: str
    label: str
    pattern: re.Pattern[str]
    surfaces: frozenset[SurfaceType] | None = None
    certificate_rule: bool = False
    commercial_rule: bool = False
    question_safe: bool = False


_HTML_ONLY = frozenset({SurfaceType.HTML})
_STRUCTURED_ONLY = frozenset({SurfaceType.STRUCTURED_DATA})
_EXECUTABLE_ONLY = frozenset({SurfaceType.EXECUTABLE_JAVASCRIPT})
_APPROVED_WHATSAPP_LINKS = frozenset({
    "https://wa.me/34614401172",
    "https://wa.me/34614401172?text=",
})
_WHATSAPP_URL_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9:/._-])(?:(?:[A-Za-z][A-Za-z0-9+.-]*:)?//)?"
    r"(?:[A-Z0-9-]+\.)*wa\.me(?::\d+)?(?:/[^\s\"'<>]*)?|"
    r"(?<![A-Za-z0-9:/._-])(?:(?:[A-Za-z][A-Za-z0-9+.-]*:)?//)?"
    r"(?:[A-Z0-9-]+\.)*whatsapp\.com(?::\d+)?(?:/[^\s\"'<>]*)?|"
    r"(?<![A-Za-z0-9:/._-])https?://[^\s\"'<>]*whatsapp[^\s\"'<>]*|"
    r"(?<![A-Za-z0-9:/._-])(?:https?://)?(?:www\.)?"
    r"(?:bit\.ly|tinyurl\.com|t\.co|is\.gd|tiny\.cc)/[^\s\"'<>]+",
    re.IGNORECASE,
)
_NETWORK_SUBMISSION_RE = re.compile(
    r"(?<![\w$.])fetch\s*\((?![^()\n]*\)\s*\{)|"
    r"\b(?:window|globalThis|self)\s*\.\s*fetch\s*\(|"
    r"\b(?:new\s+)?XMLHttpRequest\b|"
    r"\bnavigator\s*\.\s*sendBeacon\s*\(|"
    r"(?:\(\s*)?\bnew\s+Image\s*\([^)]*\)\s*(?:\)\s*)?\.\s*src\s*=",
    re.IGNORECASE,
)
_PRODUCTION_PLACEHOLDER_RE = re.compile(
    r"FORM_ID|\bTBD\b|\bTODO\b|pre-launch|prelaunch|being prepared|not yet open|"
    r"\bpending\b|not active yet|will only become active|not operationally verified",
    re.IGNORECASE,
)

CLAIM_RULES = (
    _ClaimRule(
        "testimonial or endorsement",
        "approved student caption outside its associated video card",
        re.compile(
            "|".join(
                re.escape(caption) for _, caption in APPROVED_STUDENT_EVIDENCE
            ),
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "testimonial or endorsement",
        "testimonial or recommendation language",
        re.compile(
            r"\b(?:testimonial(?:s)?|what\s+(?:families|parents|students)\s+say|"
            r"recommended\s+by|(?:parents?|families|students?)\s+recommend(?:s|ed)?\b|"
            r"(?:parents?|famil(?:y|ies)|students?)\s+recommendations?\b|"
            r"recommendations?\s+from\s+(?:parents?|famil(?:y|ies)|students?)\b|"
            r"endorsement(?:s)?)\b",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "rating or review evidence",
        "numeric star or review pattern",
        re.compile(
            r"(?:[★☆]{1,5}|\b(?:rated\s+)?\d+(?:\.\d+)?\s+stars?\b|"
            r"\b\d+(?:\.\d+)?\s*(?:/|out\s+of)\s*5\b|"
            r"\b\d[\d,]*\s+(?:reviews?|ratings?)\b)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "learner or family count",
        "numeric learner or family count",
        re.compile(
            r"\b\d[\d,]*\+?\s+(?:learners?|families|students|parents)\b",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "success percentage",
        "success or completion percentage",
        re.compile(
            r"(?:\b\d{1,3}(?:\.\d+)?\s*%\s+(?:success|completion|"
            r"satisfaction|achievement|pass)\w*(?:\s+rate)?\b|"
            r"\b(?:success|completion|satisfaction|achievement|pass)\w*\s+rate\s*:?\s*"
            r"\d{1,3}(?:\.\d+)?\s*%)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "certificate promise",
        "positive certificate verb",
        re.compile(
            r"\b(?:receive|earn|get|gain|award(?:ed)?|provide(?:d|s)?|include(?:d|s)?|"
            r"promis(?:e|ed|es)|comes?\s+with)\b[^.!?;\n]{0,80}?\bcertificates?\b|"
            r"\bcertificates?\b[^.!?;\n]{0,80}?\b(?:receive|earn|get|gain|"
            r"award(?:ed)?|provide(?:d|s)?|include(?:d|s)?|promis(?:e|ed|es)|"
            r"comes?\s+with)\b",
            re.IGNORECASE,
        ),
        certificate_rule=True,
    ),
    _ClaimRule(
        "certificate promise",
        "completion-certificate noun phrase outside its eligible 12-week evidence card",
        re.compile(
            r"\b(?:(?:digital|eligible|end-of-course)\s+){0,2}(?:certificate\s+of\s+completion|completion\s+certificate)\b",
            re.IGNORECASE,
        ),
        certificate_rule=True,
    ),
    _ClaimRule(
        "combined teacher experience",
        "collective teaching experience total",
        re.compile(
            r"(?:\b(?:our\s+)?(?:team|teachers?|staff|instructors?|educators?)\b"
            r"[^.!?\n]{0,80}\b\d[\d,]*\+?\s+years?\b[^.!?\n]{0,80}"
            r"\b(?:teaching|experience)\b|\b\d[\d,]*\+?\s+years?\b"
            r"[^.!?\n]{0,80}\b(?:teaching|experience)\b)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "aggregate statistic",
        "aggregate counter attribute",
        re.compile(r"\bdata-(?:count-to|counter|target)\s*=\s*['\"]?\d", re.IGNORECASE),
        _HTML_ONLY,
    ),
    _ClaimRule(
        "analytics integration",
        "analytics URL or function",
        re.compile(
            r"(?:googletagmanager\.com|google-analytics\.com|analytics\.js|"
            r"\bgtag\s*\(|\bga\s*\(|\bfbq\s*\(|\bdataLayer\s*=)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "unsupported legal identity",
        "unapproved operator, company, or registration assertion",
        re.compile(
            r"\b(?:operated|owned|run)\s+by\s+[^.!?\n]{1,80}\b(?:Ltd|Limited|LLC|Inc(?:orporated)?|GmbH|S\.?\s*L\.?|Company|Corporation)\b|"
            r"\bcompany\s+registration\s+(?:number|no\.?)\s*(?:is|:)\s*[A-Za-z0-9-]+|"
            r"\b(?:legal\s+)?(?:operator|controller)\s*(?:is|:)\s+[^.!?\n]{2,100}",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "unsupported postal address",
        "unapproved public postal or business address",
        re.compile(
            r"<address\b|"
            r"\b(?:postal|business|registered|office|correspondence)\s+address\s*(?:is|:)\s*(?!pending\b|not\b)[^.!?\n]{2,120}|"
            r"\b(?:P\.?\s*O\.?\s+Box\s+\d+|\d{1,6}\s+[A-Za-z][A-Za-z0-9 .'-]{1,60}\s(?:Street|St|Road|Rd|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr|Calle|Plaza)\b)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "unsupported postal address",
        "unapproved structured postal address",
        re.compile(
            r"[\"'](?:address|streetAddress|postalCode|addressLocality|addressRegion|addressCountry)[\"']\s*:|"
            r"[\"']PostalAddress[\"']",
            re.IGNORECASE,
        ),
        _STRUCTURED_ONLY,
    ),
    _ClaimRule(
        "active form or contact destination",
        "form action or contact integration",
        re.compile(
            r"(?:<form\b(?![^>]*\bdata-prelaunch-disabled\s*=\s*['\"]true['\"])(?![^>]*\bdata-whatsapp-handoff\s*=\s*['\"]true['\"])|"
            r"\baction\s*=\s*['\"]?(?:https?:|mailto:|tel:)|"
            r"\bmailto:|\btel:|"
            r"https?://script\.google\.com/macros/)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "unapproved WhatsApp destination",
        "wrong number, tracking query, API endpoint, or non-wa.me wrapper",
        _WHATSAPP_URL_CANDIDATE,
    ),
    _ClaimRule(
        "active Formspree endpoint",
        "Formspree endpoint is superseded and prohibited in public code",
        re.compile(r"\bformspree(?:\.io)?\b", re.IGNORECASE),
    ),
    _ClaimRule(
        "unsafe form endpoint",
        "Formspree endpoint or placeholder is prohibited in public code",
        re.compile(r"\bformspree(?:\.io)?\b", re.IGNORECASE),
    ),
    _ClaimRule(
        "email contact publication",
        "public email address or mailto destination",
        re.compile(
            r"\bmailto:|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "network form submission",
        "browser network submission or tracking-pixel path",
        _NETWORK_SUBMISSION_RE,
        _EXECUTABLE_ONLY,
    ),
    _ClaimRule(
        "personal-data storage",
        "browser storage used by the trial or contact flow",
        re.compile(r"\b(?:localStorage|sessionStorage)\b"),
        _EXECUTABLE_ONLY,
    ),
    _ClaimRule(
        "WhatsApp API credential",
        "WhatsApp token, API key, or secret in executable code",
        re.compile(
            r"\bwhatsapp(?:(?:[_\s-]?)(?:business|platform|api|access|auth))*"
            r"[_\s-]?(?:token|key|secret|credential)s?\b",
            re.IGNORECASE,
        ),
        _EXECUTABLE_ONLY,
    ),
    _ClaimRule(
        "false message-sent confirmation",
        "message-sent state the website cannot verify",
        re.compile(
            r"\b(?:(?:your|the)\s+)?(?:whatsapp\s+)?message\s+"
            r"(?:(?:is|was|has\s+been)\s+)?(?:successfully\s+)?sent\b",
            re.IGNORECASE,
        ),
        commercial_rule=True,
    ),
    _ClaimRule(
        "false booking confirmation",
        "trial or booking confirmation without operational confirmation",
        re.compile(
            r"\b(?:"
            r"(?:(?:your|the)\s+)?(?:trial|booking)\s+"
            r"(?:is\s+|has\s+been\s+)?(?:now\s+|successfully\s+)?(?:booked|confirmed)|"
            r"(?:we|salaam\s+center|the\s+website)\s+(?:have\s+)?confirmed\s+"
            r"(?:your|the)\s+(?:trial|booking)"
            r")\b(?!\s+only\s+after)",
            re.IGNORECASE,
        ),
        commercial_rule=True,
    ),
    _ClaimRule(
        "automatic WhatsApp sending claim",
        "claim that a WhatsApp message is sent automatically",
        re.compile(
            r"\b(?:automatically\s+(?:send|sends|sent)|auto[- ]send(?:s|ing)?|"
            r"send(?:s|ing)?\s+(?:the\s+message\s+)?automatically|"
            r"sent\s+automatically)\b",
            re.IGNORECASE,
        ),
        commercial_rule=True,
    ),
    _ClaimRule(
        "forbidden form field",
        "child contact, sensitive, payment, upload, or marketing field",
        re.compile(
            r"\bname\s*=\s*['\"](?:email|child[_-]?(?:email|phone)|phone|telephone|mobile|"
            r"learner[_-]?(?:name|first[_-]?name|surname|last[_-]?name)|"
            r"date[_-]?of[_-]?birth|dob|passport|government[_-]?id|national[_-]?id|id[_-]?number|"
            r"school[_-]?name|(?:home[_-]?)?address|payment|card[_-]?number|bank[_-]?account|"
            r"financial(?:[_-]info)?|income|file|marketing(?:[_-]consent)?|"
            r"newsletter(?:[_-]opt[_-]in)?|social(?:[_-](?:media|handle|account))?|"
            r"religion|religious[_-]?confession|faith[_-]?declaration|password|whatsapp|medical|diagnosis)['\"]|"
            r"\btype\s*=\s*['\"]file['\"]",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "pre-checked acknowledgement",
        "privacy acknowledgement must be unchecked",
        re.compile(
            r"<input\b(?=[^>]*\bname\s*=\s*['\"]privacy_acknowledgement['\"])(?=[^>]*\bchecked\b)[^>]*>",
            re.IGNORECASE,
        ),
        _HTML_ONLY,
    ),
    _ClaimRule(
        "false submission confirmation",
        "positive submission state outside the protected Success state",
        re.compile(
            r"\b(?:your trial request was submitted|Salaam Center has received the request|"
            r"successfully submitted|we received your request)\b",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "unapproved public price",
        "currency amount outside an exact approved pricing card or homepage preview",
        re.compile(
            r"(?:[€$£]\s*\d[\d,.]*|\b(?:EUR|USD|CAD|GBP)\s*\d[\d,.]*\b|"
            r"\b\d[\d,.]*\s*(?:EUR|USD|CAD|GBP)\b)",
            re.IGNORECASE,
        ),
    ),
    _ClaimRule(
        "unapproved public price",
        "structured price or currency field outside an approved HTML evidence card",
        re.compile(
            r"[\"'](?:price|lowPrice|highPrice|minPrice|maxPrice|priceCurrency)"
            r"[\"']\s*:",
            re.IGNORECASE,
        ),
        _STRUCTURED_ONLY,
    ),
    _ClaimRule(
        "unapproved public percentage",
        "numeric percentage outside exact approved certificate eligibility",
        re.compile(r"\b\d{1,3}(?:\.\d+)?\s*%"),
    ),
    _ClaimRule(
        "active automatic renewal",
        "positive automatic-renewal language",
        re.compile(
            r"\bautomatic\s+renewal\b|\brenew(?:s|ed|ing)?\s+automatically\b|"
            r"\bautomatically\s+renew(?:s|ed|ing)?\b",
            re.IGNORECASE,
        ),
        commercial_rule=True,
        question_safe=True,
    ),
    _ClaimRule(
        "active checkout or payment state",
        "checkout, payment action, or completed-payment language",
        re.compile(
            r"\b(?:checkout|buy\s+now|pay\s+now|subscribe|reserve\s+with\s+payment)\b|"
            r"\bpayment\b[^.!?;\n]{0,28}\bcompleted\b",
            re.IGNORECASE,
        ),
        commercial_rule=True,
    ),
    _ClaimRule(
        "unsupported free paid plan",
        "paid plan, class, or lesson described as free",
        re.compile(
            r"(?:\bpaid\s+(?:plan|classes?|lessons?)\b[^.!?;\n]{0,30}\bfree\b|"
            r"\bfree\b[^.!?;\n]{0,30}\bpaid\s+(?:plan|classes?|lessons?)\b)",
            re.IGNORECASE,
        ),
        commercial_rule=True,
    ),
    _ClaimRule(
        "unsupported tax claim",
        "tax or VAT inclusion claim",
        re.compile(
            r"(?:\b(?:tax(?:es)?|vat)\b[^.!?;\n]{0,24}\b(?:included|inclusive)\b|"
            r"\b(?:prices?|pricing|amounts?|totals?)\b[^.!?;\n]{0,36}"
            r"\binclude(?:s|d|ing)?\s+(?:tax(?:es)?|vat)\b)",
            re.IGNORECASE,
        ),
        commercial_rule=True,
    ),
    _ClaimRule(
        "payment-provider integration",
        "named payment provider",
        re.compile(r"\b(?:Stripe|PayPal|Revolut)\b", re.IGNORECASE),
    ),
)

_DIRECT_NEGATION_PREFIX = re.compile(
    r"(?:\bno(?:\s+[\w/-]+){0,2}\s+|"
    r"\b(?:do|does|did|is|are|was|were|has|have|had|will|would|can|could|"
    r"should|must)\s+not(?:\s+[\w/-]+)?\s+|"
    r"\b(?:don['’]t|doesn['’]t|didn['’]t|isn['’]t|aren['’]t|wasn['’]t|"
    r"weren['’]t|hasn['’]t|haven['’]t|hadn['’]t|won['’]t|wouldn['’]t|"
    r"can['’]t|cannot|couldn['’]t|shouldn['’]t|mustn['’]t)"
    r"(?:\s+[\w/-]+)?\s+)$",
    re.IGNORECASE,
)

_DIRECT_NEGATION_WITHIN_MATCH = re.compile(
    r"\b(?:(?:not|never)\s+|"
    r"(?:don['’]t|doesn['’]t|didn['’]t|isn['’]t|aren['’]t|wasn['’]t|"
    r"weren['’]t|hasn['’]t|haven['’]t|hadn['’]t|won['’]t|wouldn['’]t|"
    r"can['’]t|cannot|couldn['’]t|shouldn['’]t|mustn['’]t)\s+)"
    r"(?:currently\s+|yet\s+)?(?:be(?:en)?\s+)?(?:renew\w*|complete(?:d)?|"
    r"active|available|free|include\w*|inclusive|promis\w*|provid\w*|"
    r"award\w*|receiv\w*|earn\w*|get|gain)\b",
    re.IGNORECASE,
)

_DIRECT_NEGATION_SUFFIX = re.compile(
    r"^\s+(?:(?:is|are|was|were|has|have|had|will|would|can|could|should|"
    r"must)(?:\s+be|\s+been)?\s+(?:not|never)|"
    r"(?:isn['’]t|aren['’]t|wasn['’]t|weren['’]t|hasn['’]t|haven['’]t|"
    r"hadn['’]t|won['’]t|wouldn['’]t|can['’]t|cannot|couldn['’]t|"
    r"shouldn['’]t|mustn['’]t))\b\s+(?:currently\s+|yet\s+)?"
    r"(?:active|available|enabled|included|promised|provided|awarded|offered|"
    r"complete(?:d)?|free)\b",
    re.IGNORECASE,
)

_COORDINATING_BOUNDARY = re.compile(
    r"\b(?:and|but|yet|while|although|however|then)\b",
    re.IGNORECASE,
)

_SENSITIVE_QUERY = re.compile(
    r"(?i)(\b(?:access[_-]?token|api[_-]?key|auth|password|secret|token)=)"
    r"[^&\s\"'<>]+"
)
_URL_QUERY = re.compile(r"(?i)(https?://[^\s\"'<>?]+)\?[^\s\"'<>]+")
_EXCERPT_LIMIT = 180


def _mask_protected_ranges(surface: SurfaceText) -> str:
    masked = list(surface.text)
    for start, end in surface.protected_ranges:
        for index in range(max(0, start), min(end, len(masked))):
            if masked[index] != "\n":
                masked[index] = " "
    return "".join(masked)


def _predicate_match_is_negated(
    text: str,
    start: int,
    end: int,
    question_safe: bool = False,
) -> bool:
    clause_marks = (".", "!", "?", ";", ",", ":", "\n")
    clause_start = max(text.rfind(mark, 0, start) for mark in clause_marks) + 1
    clause_ends = [
        position
        for mark in clause_marks
        if (position := text.find(mark, end)) != -1
    ]
    clause_end = min(clause_ends) if clause_ends else len(text)
    clause = text[clause_start:clause_end]
    match_start = start - clause_start
    match_end = end - clause_start

    if (
        question_safe
        and clause_end < len(text)
        and text[clause_end] == "?"
        and re.match(
            r"\s*(?:does|do|did|will|would|is|are|can|could|should)\b",
            clause,
            re.IGNORECASE,
        )
    ):
        return True

    prefix = clause[:match_start]
    coordinating_matches = tuple(_COORDINATING_BOUNDARY.finditer(prefix))
    if coordinating_matches:
        prefix = prefix[coordinating_matches[-1].end():]
    prefix = re.sub(r"[\"'`]\s*\+\s*[\"'`]\s*$", "", prefix)
    matched_text = clause[match_start:match_end]
    suffix = clause[match_end:]
    return (
        _DIRECT_NEGATION_PREFIX.search(prefix) is not None
        or _DIRECT_NEGATION_WITHIN_MATCH.search(matched_text) is not None
        or _DIRECT_NEGATION_SUFFIX.search(suffix) is not None
    )


def _certificate_match_is_negated(text: str, start: int, end: int) -> bool:
    return _predicate_match_is_negated(text, start, end)


def _commercial_match_is_negated(
    text: str,
    start: int,
    end: int,
    question_safe: bool = False,
) -> bool:
    clause_start = max(text.rfind(mark, 0, start) for mark in (".", "!", "?", ";", "\n")) + 1
    prefix = text[clause_start:start]
    coordinating_matches = tuple(_COORDINATING_BOUNDARY.finditer(prefix))
    if coordinating_matches:
        prefix = prefix[coordinating_matches[-1].end():]
    if re.search(
        r"\b(?:cannot|can\s+not|can['’]t|does\s+not|doesn['’]t)\s+"
        r"(?:know|confirm|verify|tell)\b",
        prefix,
        re.IGNORECASE,
    ):
        return True
    return _predicate_match_is_negated(
        text,
        start,
        end,
        question_safe=question_safe,
    )


def _legal_match_is_negated(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(mark, 0, start) for mark in (".", "!", "?", ";", "\n")) + 1
    context = text[clause_start:end]
    return re.search(r"\b(?:no|not|without|unapproved|unsupported)\b", context, re.IGNORECASE) is not None


def _sanitize_excerpt(text: str) -> str:
    sanitized = unescape(text).replace("\u2063", " ")
    sanitized = _URL_QUERY.sub(r"\1?[redacted]", sanitized)
    sanitized = _SENSITIVE_QUERY.sub(r"\1[redacted]", sanitized)
    return " ".join(sanitized.split())


def _excerpt_for_match(text: str, start: int, end: int) -> str:
    raw_start = max(0, start - (_EXCERPT_LIMIT * 2))
    raw_end = min(len(text), end + (_EXCERPT_LIMIT * 2))
    excerpt = _sanitize_excerpt(text[raw_start:raw_end])
    matched = _sanitize_excerpt(text[start:end])
    match_start = excerpt.find(matched)
    if match_start == -1:
        excerpt = matched
        match_start = 0

    context = max(0, _EXCERPT_LIMIT - len(matched))
    window_start = max(0, match_start - (context // 2))
    window_end = min(len(excerpt), window_start + _EXCERPT_LIMIT)
    window_start = max(0, window_end - _EXCERPT_LIMIT)
    centered = excerpt[window_start:window_end]
    if window_start:
        centered = "..." + centered[3:]
    if window_end < len(excerpt):
        centered = centered[:-3] + "..."
    return centered


_STRUCTURED_REVIEW_PROPERTIES = frozenset({
    "aggregaterating",
    "bestrating",
    "rating",
    "ratingcount",
    "ratingvalue",
    "review",
    "reviewbody",
    "reviewcount",
    "reviewrating",
    "reviews",
    "worstrating",
})
_STRUCTURED_REVIEW_TYPES = frozenset({"aggregaterating", "review"})
_MALFORMED_STRUCTURED_REVIEW = re.compile(
    r"[\"']@type[\"']\s*:\s*(?:\[[^\]]{0,120})?[\"']"
    r"(?:[^\"']{0,240}[/#:])?(?:AggregateRating|Review)[\"']|"
    r"[\"'](?:aggregateRating|bestRating|rating|ratingCount|ratingValue|review|"
    r"reviewBody|reviewCount|reviewRating|reviews|worstRating)[\"']\s*:",
    re.IGNORECASE,
)


def _structured_review_tokens(value: object) -> list[tuple[str, bool]]:
    tokens: list[tuple[str, bool]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in _STRUCTURED_REVIEW_PROPERTIES:
                tokens.append((str(key), True))
            if normalized_key == "@type":
                types = child if isinstance(child, list) else [child]
                for item in types:
                    if (
                        isinstance(item, str)
                        and re.split(r"[/#:]", item)[-1].casefold()
                        in _STRUCTURED_REVIEW_TYPES
                    ):
                        tokens.append((item, False))
            tokens.extend(_structured_review_tokens(child))
    elif isinstance(value, list):
        for item in value:
            tokens.extend(_structured_review_tokens(item))
    return tokens


def _json_token_span(
    text: str,
    token: str,
    is_key: bool,
    used_starts: set[int],
) -> tuple[int, int]:
    suffix = r"\s*:" if is_key else ""
    pattern = re.compile(rf"[\"']{re.escape(token)}[\"']{suffix}", re.IGNORECASE)
    for match in pattern.finditer(text):
        if match.start() not in used_starts:
            used_starts.add(match.start())
            return match.span()
    fallback = re.search(re.escape(token), text, re.IGNORECASE)
    return fallback.span() if fallback else (0, min(len(text), 1))


def _structured_data_claims(text: str) -> tuple[tuple[str, str, int, int], ...]:
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return tuple(
            (
                "structured rating or review",
                "malformed structured rating or review fallback",
                match.start(),
                match.end(),
            )
            for match in _MALFORMED_STRUCTURED_REVIEW.finditer(text)
        )

    used_starts: set[int] = set()
    return tuple(
        (
            "structured rating or review",
            "recursive structured rating or review value",
            *(_json_token_span(text, token, is_key, used_starts)),
        )
        for token, is_key in _structured_review_tokens(parsed)
    )


_JS_ASSIGNMENT_SINK = re.compile(
    r"\b(?:textContent|innerText|innerHTML|outerHTML)\s*\+?=\s*"
    r"(?P<expression>[^;\n]+)",
    re.IGNORECASE,
)
_JS_INSERTION_SINK = re.compile(
    r"\b(?P<method>insertAdjacentHTML|insertAdjacentText|append|prepend|before|"
    r"after|appendChild|replaceChildren|replaceWith)\s*\("
    r"(?P<expression>[^;\n]*)\)",
    re.IGNORECASE,
)
_JS_CREATE_TEXT_NODE = re.compile(
    r"\A\s*(?:document\.)?createTextNode\s*\((?P<expression>.*)\)\s*\Z",
    re.IGNORECASE | re.DOTALL,
)
_JS_DYNAMIC_VALUE = re.compile(
    r"\b(?:[A-Za-z_$]\w*(?:Count|Total|Rate|Rating|Value|Counter|Number)\w*|"
    r"(?:count|total|rate|rating|value|counter|number)[A-Za-z_$]\w*)\b|"
    r"\.dataset\.(?:count|counter|target)\b|"
    r"getAttribute\s*\(\s*[\"']data-(?:count|counter|target)[\"']\s*\)",
)
_JS_DYNAMIC_AUDIENCE_ADJACENCY = re.compile(
    r"(?:\$\{[^}\n]+\}|"
    r"(?:[A-Za-z_$]\w*(?:Count|Total|Rate|Rating|Value|Counter|Number)\w*|"
    r"(?:count|total|rate|rating|value|counter|number)[A-Za-z_$]\w*)|"
    r"[A-Za-z_$]\w*\.dataset\.(?:count|counter|target)|"
    r"getAttribute\s*\(\s*[\"']data-(?:count|counter|target)[\"']\s*\))"
    r"\s*(?:\+\s*[\"'`]\s*)?(?:learners?|students?|families|parents)\b",
    re.IGNORECASE,
)
_JS_LITERAL_TOKEN = (
    r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`)"
)
_JS_SIMPLE_LITERAL_CONCATENATION = re.compile(
    rf"\A\s*{_JS_LITERAL_TOKEN}(?:\s*\+\s*{_JS_LITERAL_TOKEN})+\s*\Z"
)
_JS_LITERAL = re.compile(_JS_LITERAL_TOKEN)
_JS_AUDIENCE = re.compile(r"\b(?:learners?|students?|families|parents)\b", re.IGNORECASE)
_JS_RATING = re.compile(r"\b(?:stars?|reviews?|ratings?)\b", re.IGNORECASE)
_JS_SUCCESS = re.compile(
    r"\b(?:success|completion|satisfaction|achievement|pass)\w*\b",
    re.IGNORECASE,
)
_JS_EXPERIENCE = re.compile(
    r"\byears?\b[^;\n]{0,80}\b(?:teaching|experience)\b",
    re.IGNORECASE,
)


def _render_simple_literal_concatenation(expression: str) -> str | None:
    if not _JS_SIMPLE_LITERAL_CONCATENATION.fullmatch(expression):
        return None
    rendered: list[str] = []
    for match in _JS_LITERAL.finditer(expression):
        literal = match.group()
        value = literal[1:-1]
        if literal.startswith("`") and "${" in value:
            return None
        value = re.sub(r"\\([\\'\"`])", r"\1", value)
        value = value.replace(r"\n", "\n").replace(r"\t", "\t")
        rendered.append(value)
    return "".join(rendered)


def _virtual_rendered_claims(text: str) -> tuple[tuple[str, str], ...]:
    claims: list[tuple[str, str]] = []
    for claim_rule in CLAIM_RULES:
        if (
            claim_rule.surfaces is not None
            and SurfaceType.EXECUTABLE_JAVASCRIPT not in claim_rule.surfaces
        ):
            continue
        for match in claim_rule.pattern.finditer(text):
            if (
                claim_rule.category == "unapproved WhatsApp destination"
                and match.group(0) in _APPROVED_WHATSAPP_LINKS
            ):
                continue
            if claim_rule.certificate_rule and _certificate_match_is_negated(
                text, match.start(), match.end()
            ):
                continue
            if claim_rule.commercial_rule and _commercial_match_is_negated(
                text,
                match.start(),
                match.end(),
                question_safe=claim_rule.question_safe,
            ):
                continue
            if claim_rule.category in {"unsupported legal identity", "unsupported postal address"} and _legal_match_is_negated(
                text, match.start(), match.end()
            ):
                continue
            claims.append(
                (
                    claim_rule.category,
                    f"rendered literal: {claim_rule.label}",
                )
            )
    return tuple(claims)


def _split_javascript_arguments(arguments: str) -> tuple[str, ...]:
    parts: list[str] = []
    current: list[str] = []
    quote = ""
    escaped = False
    depth = 0
    for character in arguments:
        if quote:
            current.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = ""
            continue
        if character in "'\"`":
            quote = character
            current.append(character)
        elif character in "([{":
            depth += 1
            current.append(character)
        elif character in ")]}" and depth:
            depth -= 1
            current.append(character)
        elif character == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    parts.append("".join(current).strip())
    return tuple(part for part in parts if part)


def _rendered_sink_arguments(sink: re.Match[str]) -> tuple[str, ...]:
    expression = sink.group("expression")
    method = sink.groupdict().get("method")
    if method is None:
        return (expression,)

    arguments = _split_javascript_arguments(expression)
    normalized_method = method.casefold()
    if normalized_method in ("insertadjacenthtml", "insertadjacenttext"):
        return arguments[1:2]
    if normalized_method == "appendchild":
        if len(arguments) != 1:
            return ()
        text_node = _JS_CREATE_TEXT_NODE.fullmatch(arguments[0])
        if text_node is None:
            return ()
        nested_arguments = _split_javascript_arguments(text_node.group("expression"))
        return nested_arguments[:1]
    return arguments


def _javascript_expression_claims(expression: str) -> tuple[tuple[str, str], ...]:
    rendered = _render_simple_literal_concatenation(expression)
    if rendered is not None:
        return tuple(dict.fromkeys(_virtual_rendered_claims(rendered)))

    has_named_dynamic_value = _JS_DYNAMIC_VALUE.search(expression) is not None
    if not has_named_dynamic_value and not _JS_DYNAMIC_AUDIENCE_ADJACENCY.search(
        expression
    ):
        return ()
    categories: list[tuple[str, str]] = []
    if _JS_DYNAMIC_AUDIENCE_ADJACENCY.search(expression):
        categories.append(
            ("learner or family count", "dynamic audience counter in rendering sink")
        )
    if has_named_dynamic_value and _JS_RATING.search(expression):
        categories.append(
            ("rating or review evidence", "dynamic rating or review in rendering sink")
        )
    if (
        has_named_dynamic_value
        and _JS_SUCCESS.search(expression)
        and ("%" in expression or "rate" in expression.lower())
    ):
        categories.append(
            ("success percentage", "dynamic success rate in rendering sink")
        )
    if has_named_dynamic_value and _JS_EXPERIENCE.search(expression):
        categories.append(
            (
                "combined teacher experience",
                "dynamic experience total in rendering sink",
            )
        )
    return tuple(categories)


def _javascript_sink_claims(text: str) -> tuple[tuple[str, str, int, int], ...]:
    claims: list[tuple[str, str, int, int]] = []
    for sink in (*_JS_ASSIGNMENT_SINK.finditer(text), *_JS_INSERTION_SINK.finditer(text)):
        arguments = _rendered_sink_arguments(sink)
        expressions = list(arguments)
        if len(arguments) > 1:
            expressions.append(" + ".join(arguments))

        sink_claims: dict[str, str] = {}
        for expression in expressions:
            for category, rule in _javascript_expression_claims(expression):
                sink_claims.setdefault(category, rule)

        claims.extend(
            (category, rule, sink.start(), sink.end())
            for category, rule in sink_claims.items()
        )
    return tuple(claims)


def _line_for_match(surface: SurfaceText, position: int) -> int:
    if surface.line_map and len(surface.line_map) == len(surface.text):
        if not surface.line_map:
            return surface.start_line
        return surface.line_map[min(position, len(surface.line_map) - 1)]
    return surface.start_line + surface.text.count("\n", 0, position)


def _finding_for_match(
    surface: SurfaceText,
    category: str,
    rule: str,
    start: int,
    end: int,
) -> Finding:
    return Finding(
        path=surface.path,
        surface=surface.surface,
        category=category,
        rule=rule,
        line=_line_for_match(surface, start),
        excerpt=_excerpt_for_match(surface.text, start, end),
        classification=surface.classification,
    )


def scan_surface(surface: SurfaceText) -> tuple[Finding, ...]:
    masked_text = _mask_protected_ranges(surface)
    results: list[Finding] = []
    is_form_surface = (
        surface.surface is SurfaceType.HTML
        and masked_text.lstrip().casefold().startswith("<form")
    )
    for claim_rule in CLAIM_RULES:
        if claim_rule.surfaces is not None and surface.surface not in claim_rule.surfaces:
            continue
        for match in claim_rule.pattern.finditer(masked_text):
            if (
                claim_rule.category == "unapproved WhatsApp destination"
                and match.group(0) in _APPROVED_WHATSAPP_LINKS
            ):
                continue
            if (
                is_form_surface
                and claim_rule.category == "active form or contact destination"
                and any(item.category == claim_rule.category for item in results)
            ):
                continue
            if claim_rule.certificate_rule and _certificate_match_is_negated(
                masked_text, match.start(), match.end()
            ):
                continue
            if claim_rule.commercial_rule and _commercial_match_is_negated(
                masked_text,
                match.start(),
                match.end(),
                question_safe=claim_rule.question_safe,
            ):
                continue
            if claim_rule.category in {"unsupported legal identity", "unsupported postal address"} and _legal_match_is_negated(
                masked_text, match.start(), match.end()
            ):
                continue
            results.append(
                _finding_for_match(
                    surface,
                    claim_rule.category,
                    claim_rule.label,
                    match.start(),
                    match.end(),
                )
            )

    extra_claims: tuple[tuple[str, str, int, int], ...] = ()
    if surface.surface is SurfaceType.STRUCTURED_DATA:
        extra_claims = _structured_data_claims(masked_text)
    elif surface.surface is SurfaceType.EXECUTABLE_JAVASCRIPT:
        extra_claims = _javascript_sink_claims(masked_text)
    results.extend(
        _finding_for_match(surface, category, rule, start, end)
        for category, rule, start, end in extra_claims
    )
    return tuple(results)


def format_finding(finding: Finding, root: Path | None = None) -> str:
    path = finding.path
    if root is not None:
        try:
            path = finding.path.resolve().relative_to(root.resolve())
        except ValueError:
            pass
    return (
        f"{path}:line {finding.line} [{finding.surface.value}] {finding.category}; "
        f"matched rule: {finding.rule}; excerpt: {finding.excerpt}"
    )


def classify_path(
    root: Path,
    path: Path,
    referenced_scripts: Collection[Path] = (),
) -> Classification:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    if relative in DOCUMENTATION_PATHS or relative == "docs" or relative.startswith("docs/") or relative == "tests" or relative.startswith("tests/"):
        return Classification.DOCUMENTATION_ONLY
    if relative in PUBLIC_HTML_PATHS or path.resolve() in {
        item.resolve() for item in referenced_scripts
    }:
        return Classification.PUBLIC
    return Classification.INACTIVE


_VISIBLE_BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
    "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead",
    "tr", "ul", "details", "summary",
})


class _MappedTextBuilder:
    def __init__(self) -> None:
        self.characters: list[str] = []
        self.lines: list[int] = []
        self.protected_ranges: list[tuple[int, int]] = []

    def __len__(self) -> int:
        return len(self.characters)

    @property
    def text(self) -> str:
        return "".join(self.characters)

    def append(self, value: str, start_line: int) -> None:
        line = start_line
        for character in value:
            self.characters.append(character)
            self.lines.append(line)
            if character == "\n":
                line += 1

    def boundary(self, line: int) -> None:
        if not self.characters or self.characters[-3:] == list(_VISIBLE_BOUNDARY):
            return
        for character in _VISIBLE_BOUNDARY:
            self.characters.append(character)
            self.lines.append(line)

    def protect(self, value: str, start: int, end: int) -> None:
        text = self.text
        position = text.find(value, start, end)
        while position != -1:
            self.protected_ranges.append((position, position + len(value)))
            position = text.find(value, position + len(value), end)

    def protect_span(self, start: int, end: int) -> None:
        if 0 <= start < end <= len(self.characters):
            self.protected_ranges.append((start, end))


@dataclass
class _EvidenceCard:
    kind: str
    tag: str
    start: int
    depth: int
    attributes: dict[str, str]
    attribute_values: list[str]


class _PublicHTMLParser(HTMLParser):
    def __init__(self, relative_path: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[tuple[SurfaceType, int, str]] = []
        self.script_sources: list[tuple[int, str]] = []
        self.links: list[tuple[int, str]] = []
        self.visible = _MappedTextBuilder()
        self._relative_path = relative_path
        self._approval_path = (
            relative_path.removeprefix("en/")
            if relative_path.startswith("en/")
            else relative_path
        )
        self._language = "en"
        self._in_head = False
        self._in_title = False
        self._script_surface: SurfaceType | None = None
        self._evidence_card: _EvidenceCard | None = None
        self._terms_section_starts: list[int] = []
        self._whatsapp_form_line: int | None = None
        self._whatsapp_form_has_button = False
        self._whatsapp_form_is_unsafe = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        line, _ = self.getpos()
        attributes = {name.lower(): value or "" for name, value in attrs}
        if normalized_tag == "html" and attributes.get("lang"):
            self._language = attributes["lang"].casefold()
        if not self._in_head:
            self._add_executable_attributes(attrs)

        if normalized_tag == "form" and not self._in_head:
            if attributes.get("data-whatsapp-handoff", "").casefold() == "true":
                self._whatsapp_form_line = line
                self._whatsapp_form_has_button = False
                self._whatsapp_form_is_unsafe = any(
                    name in attributes for name in ("action", "method", "onsubmit")
                )
        elif self._whatsapp_form_line is not None and normalized_tag == "button":
            button_type = attributes.get("type", "submit").casefold()
            if (
                button_type == "button"
                and "data-whatsapp-submit" in attributes
                and "formaction" not in attributes
            ):
                self._whatsapp_form_has_button = True
            elif button_type == "submit" or "formaction" in attributes:
                self._whatsapp_form_is_unsafe = True
        elif self._whatsapp_form_line is not None and normalized_tag == "input":
            if attributes.get("type", "text").casefold() in {"submit", "image"}:
                self._whatsapp_form_is_unsafe = True

        if not self._in_head and normalized_tag in _VISIBLE_BLOCK_TAGS:
            self.visible.boundary(line)

        if (
            not self._in_head
            and normalized_tag == "section"
            and self._approval_path == "terms/index.html"
        ):
            self._terms_section_starts.append(len(self.visible))

        if (
            self._evidence_card is not None
            and normalized_tag == self._evidence_card.tag
        ):
            self._evidence_card.depth += 1
        elif self._evidence_card is None and normalized_tag in ("article", "section", "div"):
            classes = frozenset(attributes.get("class", "").split())
            kind = "confirmed-success" if (
                self._approval_path == "success/index.html"
                and attributes.get("data-success-state") == "confirmed"
                and "hidden" in attributes
            ) else next(
                (
                    value
                    for value in (
                        "teacher-card",
                        "feedback-video-card",
                        "pricing-card",
                        "pricing-preview",
                        "benefit-card--extended",
                    )
                    if value in classes
                ),
                "",
            )
            if kind:
                self._evidence_card = _EvidenceCard(
                    kind,
                    normalized_tag,
                    len(self.visible),
                    1,
                    attributes,
                    [],
                )
        if self._evidence_card is not None:
            self._evidence_card.attribute_values.extend(
                value for _, value in attrs if value is not None
            )

        if normalized_tag == "a":
            href = next((value for name, value in attrs if name.lower() == "href"), None)
            if href is not None:
                self.links.append((line, href))

        if normalized_tag == "head":
            self._in_head = True
        elif normalized_tag == "title":
            self._in_title = True
        elif normalized_tag == "meta":
            self._add_attributes(SurfaceType.METADATA, attrs)
        elif normalized_tag == "script":
            attributes = {name.lower(): value for name, value in attrs}
            source = attributes.get("src")
            if source:
                self.script_sources.append((line, source))
            elif attributes.get("type", "").lower() == "application/ld+json":
                self._script_surface = SurfaceType.STRUCTURED_DATA
            else:
                self._script_surface = SurfaceType.EXECUTABLE_JAVASCRIPT
        elif normalized_tag == "form" and not self._in_head:
            attributes = " ".join(
                f'{name}="{value}"' for name, value in attrs if value
            )
            self.fragments.append(
                (SurfaceType.HTML, line, f"<form {attributes}>".rstrip())
            )
        elif normalized_tag == "address" and not self._in_head:
            attributes = " ".join(
                f'{name}="{value}"' for name, value in attrs if value
            )
            self.fragments.append(
                (SurfaceType.HTML, line, f"<address {attributes}>".rstrip())
            )
        elif not self._in_head:
            self._add_attributes(SurfaceType.HTML, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        line, _ = self.getpos()
        if (
            self._evidence_card is not None
            and normalized_tag == self._evidence_card.tag
        ):
            self._evidence_card.depth -= 1
            if self._evidence_card.depth == 0:
                self._protect_approved_card(self._evidence_card, len(self.visible))
                self._evidence_card = None
        if (
            normalized_tag == "section"
            and self._approval_path == "terms/index.html"
            and self._terms_section_starts
        ):
            self._protect_approved_terms_plan_matrix(
                self._terms_section_starts.pop(),
                len(self.visible),
            )
        if normalized_tag == "head":
            self._in_head = False
        elif normalized_tag == "title":
            self._in_title = False
        elif normalized_tag == "script":
            self._script_surface = None
        elif normalized_tag == "form" and self._whatsapp_form_line is not None:
            if self._whatsapp_form_is_unsafe or not self._whatsapp_form_has_button:
                self.fragments.append((
                    SurfaceType.HTML,
                    self._whatsapp_form_line,
                    '<form data-invalid-whatsapp-handoff="true">',
                ))
            self._whatsapp_form_line = None
            self._whatsapp_form_has_button = False
            self._whatsapp_form_is_unsafe = False
        if not self._in_head and normalized_tag in _VISIBLE_BLOCK_TAGS:
            self.visible.boundary(line)

    def handle_data(self, data: str) -> None:
        line, _ = self.getpos()
        if self._script_surface is not None:
            if data.strip():
                self.fragments.append((self._script_surface, line, data))
        elif self._in_title:
            if data.strip():
                self.fragments.append((SurfaceType.METADATA, line, data))
        elif not self._in_head:
            self.visible.append(data, line)

    def _add_executable_attributes(
        self,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        line, _ = self.getpos()
        for name, value in attrs:
            if not value:
                continue
            normalized_name = name.casefold()
            if normalized_name.startswith("on") and len(normalized_name) > 2:
                self.fragments.append((SurfaceType.EXECUTABLE_JAVASCRIPT, line, value))
                continue
            if normalized_name in {"href", "src", "action", "formaction"}:
                javascript = re.match(r"\s*javascript\s*:(.*)", value, re.I | re.S)
                if javascript:
                    self.fragments.append((
                        SurfaceType.EXECUTABLE_JAVASCRIPT,
                        line,
                        javascript.group(1),
                    ))

    def _add_attributes(
        self,
        surface: SurfaceType,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = [f'{name}="{value}"' for name, value in attrs if value]
        if values:
            line, _ = self.getpos()
            self.fragments.append((surface, line, " ".join(values)))

    def _protect_approved_card(self, card: _EvidenceCard, end: int) -> None:
        card_text = self.visible.text[card.start:end]
        attributes = " ".join(card.attribute_values)
        if card.kind == "teacher-card" and self._approval_path in _APPROVED_TEACHER_PATHS:
            matches = [
                evidence
                for evidence in APPROVED_TEACHER_EVIDENCE
                if evidence[0] in card_text
                and evidence[1] in card_text
                and evidence[2] in attributes
            ]
            if len(matches) == 1:
                self.visible.protect(matches[0][1], card.start, end)
        elif (
            card.kind == "feedback-video-card"
            and self._approval_path in _APPROVED_STUDENT_PATHS
        ):
            matches = [
                evidence
                for evidence in APPROVED_STUDENT_EVIDENCE
                if evidence[0] in attributes and evidence[1] in card_text
            ]
            if len(matches) == 1:
                self.visible.protect(matches[0][1], card.start, end)
        elif card.kind == "pricing-card" and self._approval_path == "pricing/index.html":
            matches = []
            for weeks, frequency, classes, price, saving in APPROVED_PRIVATE_PLAN_EVIDENCE:
                expected_attributes = {
                    "data-plan-weeks": str(weeks),
                    "data-frequency": str(frequency),
                    "data-paid-classes": str(classes),
                    "data-price-eur": str(price),
                }
                if saving is not None:
                    expected_attributes["data-saving-eur"] = str(saving)
                elif card.attributes.get("data-saving-eur"):
                    continue
                if self._language == "fa-af":
                    expected_text = (
                        f"{frequency} صنف در هفته",
                        f"{classes} صنف پولی",
                        "هر کدام 40 دقیقه",
                        f"€{price}",
                        "قرآن یا دری خصوصی",
                        "یک شاگرد",
                        "یک برنامهٔ انتخاب‌شده",
                        f"دورهٔ آموزشی {weeks} هفته‌ای",
                        "6 هفته" if weeks == 4 else "16 هفته",
                        "خودکار تمدید نمی‌شود",
                        "آغاز با جلسهٔ آزمایشی رایگان",
                    )
                    expected_euros = [f"€{price}"]
                    saving_text = None
                    if saving is not None:
                        expected_euros.append(f"€{saving}")
                        saving_text = (
                            "در مقایسه با سه برنامهٔ پی‌هم 4 هفته‌ای با همان "
                            f"تعداد صنف، €{saving} صرفه‌جویی می‌شود."
                        )
                    localized_evidence_is_exact = (
                        tuple(re.findall(r"€\d[\d,.]*", card_text))
                        == tuple(expected_euros)
                        and (saving_text is None or saving_text in card_text)
                    )
                else:
                    frequency_text = (
                        "1 class per week"
                        if frequency == 1
                        else f"{frequency} classes per week"
                    )
                    validity = (
                        "6-week final validity"
                        if weeks == 4
                        else "16-week final validity"
                    )
                    expected_text = (
                        frequency_text,
                        f"{classes} paid classes",
                        "40 minutes each",
                        f"€{price} total",
                        "Private Quran or Dari/Persian",
                        "One learner",
                        "One selected program",
                        f"{weeks}-week teaching period",
                        validity,
                        "Does not renew automatically",
                        "Start with a Free Trial",
                    )
                    localized_evidence_is_exact = saving is None or (
                        f"Saves €{saving} compared with three consecutive 4-week plans at the same frequency."
                        in card_text
                    )
                if all(card.attributes.get(key) == value for key, value in expected_attributes.items()) and all(
                    value in card_text for value in expected_text
                ) and localized_evidence_is_exact:
                    matches.append((price, saving))
            if len(matches) == 1:
                price, saving = matches[0]
                price_evidence = (
                    f"€{price}" if self._language == "fa-af" else f"€{price} total"
                )
                self.visible.protect(price_evidence, card.start, end)
                if saving is not None:
                    saving_evidence = (
                        f"€{saving}"
                        if self._language == "fa-af"
                        else f"Saves €{saving} compared with three consecutive 4-week plans at the same frequency."
                    )
                    self.visible.protect(saving_evidence, card.start, end)
        elif card.kind == "pricing-preview" and self._approval_path == "index.html":
            if self._language == "fa-af":
                expected = (
                    "برنامه‌های انعطاف‌پذیر برای یادگیری پیوسته",
                    "شاگردان خصوصی قرآن و دری می‌توانند بر پایهٔ تعداد صنفی که با هدف‌ها و زمان‌شان سازگار است، برنامهٔ 4 هفته‌ای یا 12 هفته‌ای را انتخاب کنند.",
                    "برنامهٔ 4 هفته‌ای از €49",
                    "درس‌های خصوصی 40 دقیقه‌ای",
                    "نخستین جلسهٔ آزمایشی رایگان",
                    "دیدن برنامه‌ها و قیمت‌ها",
                )
                price_evidence = "€49"
                pricing_href = "/pricing/"
                localized_evidence_is_exact = tuple(
                    re.findall(r"€\d[\d,.]*", card_text)
                ) == ("€49",)
            else:
                expected = (
                    "Flexible plans for consistent learning",
                    "Private Quran and Dari/Persian learners can choose a 4-week or 12-week plan",
                    "From €49 for a 4-week plan",
                    "40-minute private lessons",
                    "Free first trial",
                    "View Plans and Pricing",
                )
                price_evidence = "From €49 for a 4-week plan"
                pricing_href = "/pricing/"
                localized_evidence_is_exact = True
            if (
                card.attributes.get("data-starting-price-eur") == "49"
                and pricing_href in attributes
                and all(value in card_text for value in expected)
                and localized_evidence_is_exact
            ):
                self.visible.protect(price_evidence, card.start, end)
        elif (
            card.kind == "benefit-card--extended"
            and self._approval_path in _APPROVED_CERTIFICATE_PATHS
            and card.attributes.get("data-plan-weeks") == "12"
            and all(
                value in card_text
                for value in (
                    APPROVED_CERTIFICATE_EVIDENCE_FA_AF
                    if self._language == "fa-af"
                    else APPROVED_CERTIFICATE_EVIDENCE
                )
            )
        ):
            if self._approval_path == "terms/index.html":
                self._protect_exact_terms_certificate_context(card, end)
            else:
                if self._language == "fa-af":
                    self.visible.protect("80%", card.start, end)
                else:
                    self.visible.protect("Digital certificate of completion", card.start, end)
                    self.visible.protect(
                        "At least 80% of scheduled paid classes must be completed.",
                        card.start,
                        end,
                    )
        elif card.kind == "confirmed-success" and self._approval_path == "success/index.html":
            required = (
                "Your trial request was submitted",
                "Salaam Center has received the request.",
                "No payment has been made.",
            )
            if all(value in card_text for value in required):
                self.visible.protect(required[0], card.start, end)
                self.visible.protect(required[1], card.start, end)

    def protect_approved_legal_disclosures(self) -> None:
        """Protect only the exact approved legal disclosure blocks on legal pages."""
        expected = _APPROVED_LEGAL_DISCLOSURES.get(self._approval_path)
        if expected is None:
            return

        text = self.visible.text
        block_spans: dict[str, list[tuple[int, int]]] = {
            value: [] for value in expected
        }
        offset = 0
        for block in text.split(_VISIBLE_BOUNDARY):
            block_start = offset
            stripped = block.strip()
            if stripped in block_spans:
                value_start = block_start + block.find(stripped)
                block_spans[stripped].append(
                    (value_start, value_start + len(stripped))
                )
            offset += len(block) + len(_VISIBLE_BOUNDARY)

        # Requiring the complete pair exactly once keeps this exception from
        # becoming a general operator/address whitelist on either legal page.
        if not all(len(block_spans[value]) == 1 for value in expected):
            return
        for value in expected:
            self.visible.protect_span(*block_spans[value][0])

    def _protect_approved_terms_plan_matrix(self, start: int, end: int) -> None:
        """Protect prices only inside the complete, exact six-row Terms matrix."""
        section_text = self.visible.text[start:end]
        if self._language == "fa-af":
            heading = "برنامه‌های خصوصی قرآن و دری"
            approved_rows = APPROVED_TERMS_PLAN_EVIDENCE_FA_AF
        else:
            heading = "Private Quran and Dari/Persian plans"
            approved_rows = APPROVED_TERMS_PLAN_EVIDENCE
        if section_text.count(heading) != 1:
            return

        row_positions: list[int] = []
        for row in approved_rows:
            if section_text.count(row) != 1:
                return
            row_positions.append(section_text.find(row))
        if row_positions != sorted(row_positions):
            return
        if section_text.find(heading) > row_positions[0]:
            return

        price_matches = tuple(re.finditer(r"€\d+", section_text))
        expected_prices = tuple(
            f"€{price}"
            for _, _, _, price, _ in APPROVED_PRIVATE_PLAN_EVIDENCE
        )
        if tuple(match.group(0) for match in price_matches) != expected_prices:
            return

        for match in price_matches:
            self.visible.protect_span(start + match.start(), start + match.end())

    def _protect_exact_terms_certificate_context(
        self,
        card: _EvidenceCard,
        end: int,
    ) -> None:
        card_text = self.visible.text[card.start:end]
        if self._language == "fa-af":
            certificate_phrase = "تصدیق‌نامهٔ دیجیتالی تکمیل"
            percentage_sentence = (
                "دست‌کم 80% صنف‌های پولی برنامه‌ریزی‌شده باید تکمیل شود."
            )
            approved_evidence = APPROVED_CERTIFICATE_EVIDENCE_FA_AF
        else:
            certificate_phrase = "Digital certificate of completion"
            percentage_sentence = (
                "At least 80% of scheduled paid classes must be completed."
            )
            approved_evidence = APPROVED_CERTIFICATE_EVIDENCE
        if not all(
            card_text.count(value) == 1
            for value in approved_evidence
        ):
            return

        certificate_matches = tuple(
            re.finditer(re.escape(certificate_phrase), card_text)
        )
        percentage_matches = tuple(re.finditer(r"\b\d{1,3}(?:\.\d+)?\s*%", card_text))
        if len(certificate_matches) != 2:
            return
        if tuple(match.group(0) for match in percentage_matches) != ("80%",):
            return
        if card_text.count(percentage_sentence) != 1:
            return

        for match in (*certificate_matches, *percentage_matches):
            self.visible.protect_span(
                card.start + match.start(),
                card.start + match.end(),
            )


def _resolve_local_script(root: Path, html_path: Path, source: str) -> Path | None:
    parsed = urlsplit(source)
    if parsed.scheme or parsed.netloc:
        return None

    source_path = unquote(parsed.path)
    if not source_path:
        return None

    root_path = root.resolve()
    candidate = (
        root_path / source_path.lstrip("/")
        if source_path.startswith("/")
        else html_path.parent / source_path
    )
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root_path)
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def extract_public_surfaces(
    root: Path,
    public_html_paths: Sequence[str] = PUBLIC_HTML_PATHS,
) -> tuple[tuple[SurfaceText, ...], tuple[Path, ...], tuple[Path, ...]]:
    root_path = root.resolve()
    html_paths: list[Path] = []
    referenced_scripts: list[Path] = []
    seen_scripts: set[Path] = set()
    surfaces: list[SurfaceText] = []

    for relative_path in public_html_paths:
        html_path = (root_path / relative_path).resolve()
        try:
            html_path.relative_to(root_path)
        except ValueError:
            continue
        if not html_path.is_file():
            continue

        html_paths.append(html_path)
        parser = _PublicHTMLParser(Path(relative_path).as_posix())
        parser.feed(html_path.read_text(encoding="utf-8"))
        parser.close()
        parser.protect_approved_legal_disclosures()
        if parser.visible.text.strip():
            surfaces.append(
                SurfaceText(
                    html_path,
                    SurfaceType.HTML,
                    parser.visible.text,
                    line_map=tuple(parser.visible.lines),
                    protected_ranges=tuple(parser.visible.protected_ranges),
                )
            )
        surfaces.extend(
            SurfaceText(html_path, surface, text, line)
            for surface, line, text in parser.fragments
        )

        for line, source in parser.script_sources:
            parsed = urlsplit(source)
            if parsed.scheme or parsed.netloc:
                surfaces.append(
                    SurfaceText(
                        html_path,
                        SurfaceType.EXECUTABLE_JAVASCRIPT,
                        source,
                        line,
                    )
                )
                continue
            script_path = _resolve_local_script(root_path, html_path, source)
            if script_path is not None and script_path not in seen_scripts:
                seen_scripts.add(script_path)
                referenced_scripts.append(script_path)

    for script_path in referenced_scripts:
        surfaces.append(
            SurfaceText(
                script_path,
                SurfaceType.EXECUTABLE_JAVASCRIPT,
                script_path.read_text(encoding="utf-8"),
            )
        )

    return tuple(surfaces), tuple(html_paths), tuple(referenced_scripts)


def _internal_html_route(source_path: str, href: str) -> str | None:
    if href in NON_PAGE_INTERNAL_HREFS:
        return None
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return None

    linked_path = unquote(parsed.path)
    if not linked_path:
        return None
    if linked_path.startswith("/"):
        route = linked_path.lstrip("/")
    else:
        route = posixpath.join(posixpath.dirname(source_path), linked_path)
    route = posixpath.normpath(route).replace("\\", "/")
    if route in ("", "."):
        route = "index.html"
    elif linked_path.endswith("/") or not posixpath.splitext(route)[1]:
        route = posixpath.join(route, "index.html")
    elif posixpath.splitext(route)[1].casefold() not in (".htm", ".html"):
        return None
    return route


def _assert_manifest_covers_linked_routes(
    root: Path,
    public_html_paths: Sequence[str],
) -> None:
    manifest_routes = {
        Path(relative_path).as_posix().lstrip("./")
        for relative_path in public_html_paths
    }
    missing: list[tuple[str, int, str]] = []
    for relative_path in public_html_paths:
        normalized_source = Path(relative_path).as_posix().lstrip("./")
        html_path = root / relative_path
        parser = _PublicHTMLParser(normalized_source)
        parser.feed(html_path.read_text(encoding="utf-8"))
        parser.close()
        for line, href in parser.links:
            route = _internal_html_route(normalized_source, href)
            if route is not None and route not in manifest_routes:
                missing.append((normalized_source, line, route))

    if missing:
        inventory = ", ".join(
            f"{route} (linked from {source}:line {line})"
            for source, line, route in missing
        )
        raise ValueError(f"Unlisted internal HTML route requires a manifest decision: {inventory}")


def scan_repository(
    root: Path,
    public_html_paths: Sequence[str] = PUBLIC_HTML_PATHS,
) -> ScanReport:
    root_path = root.resolve()
    manifest_paths = []
    for relative_path in public_html_paths:
        manifest_path = (root_path / relative_path).resolve()
        try:
            manifest_path.relative_to(root_path)
        except ValueError as error:
            raise ValueError(
                f"Manifest path resolves outside the repository root: {relative_path}"
            ) from error
        manifest_paths.append(manifest_path)

    required_paths = (*manifest_paths, *(root_path / path for path in sorted(DOCUMENTATION_PATHS)))
    missing_paths = [
        path
        for path in required_paths
        if not path.is_file()
    ]
    if missing_paths:
        missing = ", ".join(path.as_posix() for path in missing_paths)
        raise FileNotFoundError(f"Required trust-evidence paths are missing: {missing}")

    _assert_manifest_covers_linked_routes(root_path, public_html_paths)

    public_surfaces, html_paths, referenced_scripts = extract_public_surfaces(
        root_path, public_html_paths
    )
    documentation_surfaces = tuple(
        SurfaceText(
            root_path / relative_path,
            SurfaceType.HTML,
            (root_path / relative_path).read_text(encoding="utf-8"),
            classification=Classification.DOCUMENTATION_ONLY,
        )
        for relative_path in sorted(DOCUMENTATION_PATHS)
    )
    all_findings = [
        finding
        for surface in (*public_surfaces, *documentation_surfaces)
        for finding in scan_surface(surface)
    ]
    config_path = root_path / "config/launch-readiness.json"
    try:
        production_mode = json.loads(config_path.read_text(encoding="utf-8")).get("site_mode") == "production"
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        production_mode = False
    if config_path.is_file():
        boundary_path = root_path / "_redirects"
        for error in deployment_boundary_errors(root_path, public_html_paths):
            all_findings.append(Finding(
                path=boundary_path,
                surface=SurfaceType.METADATA,
                category="unsafe deployment boundary",
                rule=error,
                line=1,
                excerpt="Cloudflare Pages public deployment allowlist is missing or unsafe.",
                classification=Classification.PUBLIC,
            ))
    if production_mode:
        for surface in public_surfaces:
            masked_text = _mask_protected_ranges(surface)
            all_findings.extend(
                _finding_for_match(
                    surface,
                    "production placeholder",
                    "placeholder or prelaunch language in production-marked public content",
                    match.start(),
                    match.end(),
                )
                for match in _PRODUCTION_PLACEHOLDER_RE.finditer(masked_text)
            )
    findings = tuple(sorted(
        all_findings,
        key=lambda finding: (
            finding.path.resolve().as_posix(),
            finding.line,
            finding.surface.value,
            finding.category,
            finding.rule,
        ),
    ))
    return ScanReport(
        public_surfaces=public_surfaces,
        public_html_paths=html_paths,
        public_script_paths=referenced_scripts,
        findings=findings,
    )
