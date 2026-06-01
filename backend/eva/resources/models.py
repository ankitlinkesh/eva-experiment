from __future__ import annotations

from dataclasses import asdict

from ..schemas.modeling import schema_dataclass


@schema_dataclass
class EvaResource:
    id: str
    name: str
    category: str
    provider: str
    kind: str
    license_hint: str | None
    homepage: str | None
    repo: str | None
    local_only: bool
    cloud_capable: bool
    requires_api_key: bool
    requires_network: bool
    can_read_files: bool
    can_write_files: bool
    can_execute_code: bool
    can_control_browser: bool
    can_control_desktop: bool
    can_send_external_messages: bool
    can_delete_or_modify_system: bool
    default_enabled: bool
    feature_flag: str | None
    risk_level: str
    status: str
    notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaResourceDecision:
    resource_id: str
    allowed: bool
    executable_now: bool
    status: str
    risk_level: str
    permission_required: bool
    override_required: bool
    reason: str
    blocked_capabilities: list[str]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaResourceCatalogStatus:
    total_resources: int
    allowed_count: int
    experimental_count: int
    blocked_count: int
    reference_only_count: int
    high_risk_count: int
    default_enabled_count: int
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict
