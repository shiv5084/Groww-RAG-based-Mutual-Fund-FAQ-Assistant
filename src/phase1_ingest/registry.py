"""Phase 1.1: URL registry validation and scope filtering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any


REQUIRED_URL_FIELDS = {
    "id",
    "url",
    "doc_type",
    "scheme",
    "source_owner",
    "verification_status",
}

ALLOWED_VERIFICATION_STATUS = {
    "verified",
    "pending_verification",
    "failed_verification",
}


@dataclass(frozen=True)
class ScopeFilter:
    exclude_doc_types: set[str]

    @classmethod
    def from_registry(cls, registry: dict[str, Any]) -> "ScopeFilter":
        scope = registry.get("current_iteration_scope") or {}
        excluded = scope.get("exclude_doc_types") or []
        return cls(exclude_doc_types={str(item).strip() for item in excluded if str(item).strip()})


def load_registry(path: Path) -> dict[str, Any]:
    """Load YAML registry with PyYAML if available."""
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to parse config/url_registry.yaml. "
            "Install it with: pip install pyyaml"
        ) from exc

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError("Registry root must be a mapping/object.")
    return data


def validate_registry_schema(registry: dict[str, Any]) -> None:
    """Validate top-level and row-level schema constraints for Phase 1.1."""
    if "urls" not in registry:
        raise ValueError("Registry missing required key: urls")
    if not isinstance(registry["urls"], list):
        raise ValueError("Registry field 'urls' must be a list.")

    seen_ids: set[str] = set()
    for idx, row in enumerate(registry["urls"], start=1):
        if not isinstance(row, dict):
            raise ValueError(f"urls[{idx}] must be an object.")

        missing = REQUIRED_URL_FIELDS - set(row.keys())
        if missing:
            missing_str = ", ".join(sorted(missing))
            raise ValueError(f"urls[{idx}] missing fields: {missing_str}")

        row_id = str(row["id"]).strip()
        if not row_id:
            raise ValueError(f"urls[{idx}] has empty id.")
        if row_id in seen_ids:
            raise ValueError(f"Duplicate id detected: {row_id}")
        seen_ids.add(row_id)

        url = str(row["url"]).strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError(f"{row_id}: url must start with http:// or https://")

        status = str(row["verification_status"]).strip()
        if status not in ALLOWED_VERIFICATION_STATUS:
            allowed = ", ".join(sorted(ALLOWED_VERIFICATION_STATUS))
            raise ValueError(f"{row_id}: verification_status must be one of: {allowed}")


def resolve_fetch_list(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic in-scope URL list for current iteration."""
    scope = ScopeFilter.from_registry(registry)
    rows = registry["urls"]

    result: list[dict[str, Any]] = []
    for row in rows:
        in_scope_flag = row.get("in_scope_current_iteration", True)
        if in_scope_flag is False:
            continue
        if str(row.get("doc_type", "")).strip() in scope.exclude_doc_types:
            continue

        result.append(
            {
                "id": str(row["id"]).strip(),
                "url": str(row["url"]).strip(),
                "doc_type": str(row["doc_type"]).strip(),
                "scheme": row.get("scheme"),
                "source_owner": str(row["source_owner"]).strip(),
                "verification_status": str(row["verification_status"]).strip(),
            }
        )

    # Deterministic ordering keeps output stable across runs.
    result.sort(key=lambda x: (x["id"], x["url"]))
    return result


def build_phase_1_1_artifact(registry_path: Path, output_path: Path) -> dict[str, Any]:
    """Validate + scope-filter and emit a resolved fetch artifact."""
    registry = load_registry(registry_path)
    validate_registry_schema(registry)
    fetch_list = resolve_fetch_list(registry)

    payload = {
        "phase": "1.1",
        "registry_path": str(registry_path),
        "total_registry_urls": len(registry["urls"]),
        "in_scope_urls": len(fetch_list),
        "excluded_doc_types": sorted(ScopeFilter.from_registry(registry).exclude_doc_types),
        "fetch_list": fetch_list,
    }

    # Save artifact summary to artifacts directory
    artifact_path = Path("data/artifacts/phase_1_1_registry.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=True)
        fh.write("\n")

    return payload

