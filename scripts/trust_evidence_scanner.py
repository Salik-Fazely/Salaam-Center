from dataclasses import dataclass
from enum import Enum
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
from typing import Collection, Sequence
from urllib.parse import unquote, urlsplit


PUBLIC_HTML_PATHS = (
    "index.html",
    "our-approach/index.html",
    "programs/index.html",
    "programs/quran/index.html",
    "programs/dari-persian/index.html",
    "programs/afghan-culture-islamic-ethics/index.html",
    "teachers/index.html",
    "how-it-works/index.html",
    "about/index.html",
    "book-trial/index.html",
    "privacy-policy/index.html",
    "terms/index.html",
    "success/index.html",
    "404.html",
)

DOCUMENTATION_PATHS = frozenset({
    "SALAM-CENTER-APPROVED-FACTS.md",
    "MIGRATION-SOURCE.md",
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

_APPROVED_TEACHER_PATHS = frozenset({"index.html", "teachers/index.html"})
_APPROVED_STUDENT_PATHS = frozenset({"index.html"})


@dataclass(frozen=True)
class _ClaimRule:
    category: str
    label: str
    pattern: re.Pattern[str]
    surfaces: frozenset[SurfaceType] | None = None
    certificate_rule: bool = False


_HTML_ONLY = frozenset({SurfaceType.HTML})

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
        "active form or contact destination",
        "form action or contact integration",
        re.compile(
            r"(?:<form\b|\baction\s*=\s*['\"]?(?:https?:|mailto:|tel:)|"
            r"(?:https?:)?//(?:wa\.me|api\.whatsapp\.com)/|\b(?:mailto:|tel:)|"
            r"https?://script\.google\.com/macros/)",
            re.IGNORECASE,
        ),
    ),
)

_CERTIFICATE_NEGATED_CONSTRUCTION = re.compile(
    r"(?:\bno\s+(?:\w+[ -]?){0,4}certificates?\b|"
    r"\b(?:(?:do|does|did|will|would|can|could|should|must)\s+not|"
    r"do(?:es)?n['’]t|didn['’]t|won['’]t|wouldn['’]t|can['’]t|cannot|"
    r"couldn['’]t|shouldn['’]t|mustn['’]t|isn['’]t|aren['’]t)\s+"
    r"(?!only\b)[^,;:.!?\n]{0,40}\b(?:receive|earn|get|gain|award|provide|"
    r"include|promise)\w*\b[^,;:.!?\n]{0,40}\bcertificates?\b|"
    r"\bcertificates?\b[^,;:.!?\n]{0,40}\b(?:(?:(?:is|are|will|would|can|"
    r"could|should|must|be)\s+)?(?:not|never)|isn['’]t|aren['’]t|won['’]t|"
    r"wouldn['’]t|can['’]t|cannot|couldn['’]t|shouldn['’]t|mustn['’]t)\s+"
    r"(?!only\b)[^,;:.!?\n]{0,24}\b(?:receive|earn|get|gain|"
    r"award|provide|include|promise)\w*\b)",
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


def _certificate_match_is_negated(text: str, start: int, end: int) -> bool:
    clause_marks = (".", "!", "?", ";", ",", ":", "\n")
    clause_start = max(
        text.rfind(mark, 0, start) for mark in clause_marks
    ) + 1
    clause_ends = [
        position
        for mark in clause_marks
        if (position := text.find(mark, end)) != -1
    ]
    clause_end = min(clause_ends) if clause_ends else len(text)
    clause = text[clause_start:clause_end]
    return _CERTIFICATE_NEGATED_CONSTRUCTION.search(clause) is not None


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
            if claim_rule.certificate_rule and _certificate_match_is_negated(
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
                is_form_surface
                and claim_rule.category == "active form or contact destination"
                and any(item.category == claim_rule.category for item in results)
            ):
                continue
            if claim_rule.certificate_rule and _certificate_match_is_negated(
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
    if relative in DOCUMENTATION_PATHS or relative == "tests" or relative.startswith("tests/"):
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
    "tr", "ul",
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
        if not self.characters or self.characters[-3:] == list("\n\u2063\n"):
            return
        for character in "\n\u2063\n":
            self.characters.append(character)
            self.lines.append(line)

    def protect(self, value: str, start: int, end: int) -> None:
        text = self.text
        position = text.find(value, start, end)
        while position != -1:
            self.protected_ranges.append((position, position + len(value)))
            position = text.find(value, position + len(value), end)


@dataclass
class _EvidenceCard:
    kind: str
    start: int
    depth: int
    attribute_values: list[str]


class _PublicHTMLParser(HTMLParser):
    def __init__(self, relative_path: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[tuple[SurfaceType, int, str]] = []
        self.script_sources: list[tuple[int, str]] = []
        self.links: list[tuple[int, str]] = []
        self.visible = _MappedTextBuilder()
        self._relative_path = relative_path
        self._in_head = False
        self._in_title = False
        self._script_surface: SurfaceType | None = None
        self._evidence_card: _EvidenceCard | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        line, _ = self.getpos()
        if not self._in_head and normalized_tag in _VISIBLE_BLOCK_TAGS:
            self.visible.boundary(line)

        if normalized_tag == "article":
            if self._evidence_card is not None:
                self._evidence_card.depth += 1
            else:
                attributes = {name.lower(): value or "" for name, value in attrs}
                classes = frozenset(attributes.get("class", "").split())
                kind = next(
                    (
                        value
                        for value in ("teacher-card", "feedback-video-card")
                        if value in classes
                    ),
                    "",
                )
                if kind:
                    self._evidence_card = _EvidenceCard(kind, len(self.visible), 1, [])
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
        elif not self._in_head:
            self._add_attributes(SurfaceType.HTML, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        line, _ = self.getpos()
        if normalized_tag == "article" and self._evidence_card is not None:
            self._evidence_card.depth -= 1
            if self._evidence_card.depth == 0:
                self._protect_approved_card(self._evidence_card, len(self.visible))
                self._evidence_card = None
        if normalized_tag == "head":
            self._in_head = False
        elif normalized_tag == "title":
            self._in_title = False
        elif normalized_tag == "script":
            self._script_surface = None
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
        if card.kind == "teacher-card" and self._relative_path in _APPROVED_TEACHER_PATHS:
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
            and self._relative_path in _APPROVED_STUDENT_PATHS
        ):
            matches = [
                evidence
                for evidence in APPROVED_STUDENT_EVIDENCE
                if evidence[0] in attributes and evidence[1] in card_text
            ]
            if len(matches) == 1:
                self.visible.protect(matches[0][1], card.start, end)


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
    findings = tuple(
        sorted(
            (
                finding
                for surface in (*public_surfaces, *documentation_surfaces)
                for finding in scan_surface(surface)
            ),
            key=lambda finding: (
                finding.path.resolve().as_posix(),
                finding.line,
                finding.surface.value,
                finding.category,
                finding.rule,
            ),
        )
    )
    return ScanReport(
        public_surfaces=public_surfaces,
        public_html_paths=html_paths,
        public_script_paths=referenced_scripts,
        findings=findings,
    )
