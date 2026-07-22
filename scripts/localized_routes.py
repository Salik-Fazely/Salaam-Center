"""Load and validate Salaam Center's bilingual route manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("config/localized-routes.json")
LANGUAGE_KEYS = ("fa_AF", "en")
VALID_STATUSES = frozenset({"page", "success", "not_found"})


class RouteManifestError(RuntimeError):
    """Raised when the localized route manifest is missing or unsafe."""


@dataclass(frozen=True)
class LocalizedRoute:
    id: str
    fa_AF: str
    en: str
    indexable: bool
    sitemap: bool
    status: str

    def public_path(self, language: str) -> str:
        if language not in LANGUAGE_KEYS:
            raise RouteManifestError(f"unsupported language key: {language}")
        return getattr(self, language)


def source_path_for_public_path(public_path: str) -> str:
    """Map a reviewed public URL path to its repository HTML source."""
    if public_path == "/":
        return "index.html"
    if not public_path.startswith("/") or ".." in Path(public_path).parts:
        raise RouteManifestError(f"unsafe public path: {public_path!r}")
    relative = public_path.lstrip("/")
    if relative.endswith("/"):
        relative += "index.html"
    if not relative.endswith(".html"):
        raise RouteManifestError(f"public page path has no HTML source: {public_path!r}")
    return Path(relative).as_posix()


def load_localized_routes(root: Path = REPO_ROOT) -> tuple[LocalizedRoute, ...]:
    manifest = root.resolve() / MANIFEST_PATH
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RouteManifestError(f"localized route manifest is missing: {manifest}") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RouteManifestError(f"localized route manifest cannot be read: {error}") from error
    if not isinstance(raw, list) or not raw:
        raise RouteManifestError("localized route manifest must be a non-empty list")

    required = {"id", "fa_AF", "en", "indexable", "sitemap", "status"}
    routes: list[LocalizedRoute] = []
    seen_ids: set[str] = set()
    seen_paths = {language: set() for language in LANGUAGE_KEYS}
    for index, record in enumerate(raw):
        if not isinstance(record, dict) or set(record) != required:
            raise RouteManifestError(f"route record {index} has an invalid schema")
        if not isinstance(record["id"], str) or not record["id"]:
            raise RouteManifestError(f"route record {index} has an invalid id")
        if record["id"] in seen_ids:
            raise RouteManifestError(f"duplicate route id: {record['id']}")
        seen_ids.add(record["id"])
        for language in LANGUAGE_KEYS:
            public_path = record[language]
            if not isinstance(public_path, str):
                raise RouteManifestError(
                    f"route {record['id']} has a non-string {language} path"
                )
            source_path_for_public_path(public_path)
            if public_path in seen_paths[language]:
                raise RouteManifestError(
                    f"duplicate {language} route path: {public_path}"
                )
            seen_paths[language].add(public_path)
        if not record["en"].startswith("/en/"):
            raise RouteManifestError(f"English route is outside /en/: {record['en']}")
        if not isinstance(record["indexable"], bool) or not isinstance(
            record["sitemap"], bool
        ):
            raise RouteManifestError(f"route {record['id']} has invalid boolean flags")
        if record["indexable"] != record["sitemap"]:
            raise RouteManifestError(
                f"route {record['id']} indexability and sitemap flags differ"
            )
        if record["status"] not in VALID_STATUSES:
            raise RouteManifestError(f"route {record['id']} has an invalid status")
        routes.append(LocalizedRoute(**record))

    indexable = [route for route in routes if route.indexable]
    if len(indexable) != 14:
        raise RouteManifestError("localized route manifest must define 14 indexable pairs")
    statuses = {route.status for route in routes if not route.indexable}
    if statuses != {"success", "not_found"}:
        raise RouteManifestError("non-indexable routes must be Success and Not Found")
    return tuple(routes)


def route_by_id(root: Path = REPO_ROOT) -> dict[str, LocalizedRoute]:
    return {route.id: route for route in load_localized_routes(root)}
