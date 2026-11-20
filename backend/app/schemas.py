"""Modelos pydantic que reflejan contracts/openapi.yaml (components/schemas)."""
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

LlmMode = Literal["mock", "openrouter", "anthropic", "ollama"]
CdeState = Literal["WIP", "SHARED", "PUBLISHED", "ARCHIVED"]
Discipline = Literal["ARQ", "EST", "MEP"]
Severity = Literal["error", "warning", "info"]
IssueStatus = Literal["open", "fixed", "dismissed"]
FixedBy = Literal["one_click", "manual"]
Unit = Literal["m3", "m2", "m", "und", "kg"]
FeedbackReason = Literal[
    "no_entiendo_regla", "no_encuentro_codigo", "falta_informacion", "regla_no_aplica", "error_del_plugin", "otro"
]


def iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(iso_utc, return_type=str)]


def _none(v: Any) -> bool:
    return v is None


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Error(_Base):
    detail: str


class Health(_Base):
    status: Literal["ok"] = "ok"
    version: str
    llm_mode: LlmMode


class UniclassCode(_Base):
    code: str
    title_es: str
    title_en: str | None = Field(default=None, exclude_if=_none)
    table: str
    revit_categories: list[str]


class Element(_Base):
    guid: str
    element_id: int | None = Field(default=None, exclude_if=_none)
    category: str
    discipline: Discipline
    family_name: str | None = Field(default=None, exclude_if=_none)
    type_name: str
    classification_code: str | None = None
    level: str | None = None
    volume_m3: float | None = Field(default=None, ge=0)
    area_m2: float | None = Field(default=None, ge=0)
    length_m: float | None = Field(default=None, ge=0)
    parameters: dict[str, str | None] | None = Field(default=None, exclude_if=_none)


class IssueCreate(_Base):
    element_guid: str | None = None
    rule_id: str
    severity: Severity
    message: str
    related_guid: str | None = None


class Issue(IssueCreate):
    id: int
    snapshot_id: int
    status: IssueStatus
    discipline: Discipline | None = None
    first_seen_at: UtcDatetime
    resolved_at: UtcDatetime | None = None
    fixed_by: FixedBy | None = None


class IssueUpdate(_Base):
    status: IssueStatus
    fixed_by: FixedBy | None = None


class SnapshotCreate(_Base):
    project_code: str = Field(min_length=1)
    file_name: str
    version_label: str = Field(min_length=1)
    cde_state: CdeState
    rules_version: str
    author: str | None = None
    elements: list[Element]
    issues: list[IssueCreate]


class Snapshot(_Base):
    id: int
    project_code: str
    file_name: str
    version_label: str
    cde_state: CdeState
    rules_version: str
    author: str | None = None
    created_at: UtcDatetime
    element_count: int
    open_issue_count: int


class SnapshotDetail(Snapshot):
    elements: list[Element]


class CdeStateUpdate(_Base):
    cde_state: CdeState


class FeedbackCreate(_Base):
    element_guid: str
    rule_id: str
    issue_id: int | None = None
    reason: FeedbackReason
    comment: str | None = Field(default=None, max_length=500)
    author: str | None = None


class Feedback(FeedbackCreate):
    id: int
    created_at: UtcDatetime


class ThreadEvent(_Base):
    at: UtcDatetime
    kind: Literal["issue_opened", "issue_fixed", "issue_dismissed", "feedback"]
    snapshot_id: int | None = None
    issue: Issue | None = Field(default=None, exclude_if=_none)
    feedback: Feedback | None = Field(default=None, exclude_if=_none)


class ElementThread(_Base):
    guid: str
    latest: Element | None = Field(default=None, exclude_if=_none)
    events: list[ThreadEvent]


class DisciplineStats(_Base):
    discipline: Discipline
    element_count: int
    conforming_count: int
    conformance_pct: float = Field(ge=0, le=100)
    open_errors: int
    open_warnings: int


class RuleStats(_Base):
    rule_id: str
    rule_name: str
    open_count: int
    fixed_count: int
    feedback_count: int


class Stats(_Base):
    snapshot_id: int
    cde_state: CdeState
    element_count: int
    conformance_pct: float
    can_move_to_shared: bool
    by_discipline: list[DisciplineStats]
    by_rule: list[RuleStats]
    feedback_by_reason: dict[str, int]
    snapshots_by_cde_state: dict[str, int]
    fixed_one_click: int
    fixed_manual: int


class BudgetLine(_Base):
    partida_codigo: str
    descripcion: str
    unidad: Unit
    cantidad: float
    precio_unitario: float
    subtotal: float
    element_count: int
    uniclass_codes: list[str]
    pendiente_validar: bool


class Unbudgeted(_Base):
    element_count: int
    guids_sample: list[str] = Field(max_length=20)
    by_reason: dict[str, int]


class Budget(_Base):
    snapshot_id: int
    cde_state: CdeState
    is_official: bool
    currency: Literal["PEN"] = "PEN"
    total: float
    lines: list[BudgetLine]
    unbudgeted: Unbudgeted
    overlap_warnings: int


class BudgetDiffLine(_Base):
    partida_codigo: str
    descripcion: str
    unidad: Unit
    cantidad_from: float
    cantidad_to: float
    subtotal_from: float
    subtotal_to: float
    delta_subtotal: float
    change: Literal["added", "removed", "changed", "unchanged"]


class BudgetDiff(_Base):
    from_snapshot_id: int
    to_snapshot_id: int
    total_from: float
    total_to: float
    delta_total: float
    delta_pct: float | None = None
    lines: list[BudgetDiffLine]
    elements_added: int
    elements_removed: int
    elements_modified: int


class ExplainRequest(_Base):
    rule_id: str
    element: Element | None = None


class Explanation(_Base):
    rule_id: str
    text: str
    cached: bool
    mode: LlmMode


class SuggestRequest(_Base):
    element: Element


class ClassificationSuggestion(_Base):
    element_guid: str
    candidates: list[UniclassCode]
    suggested_code: str | None = None
    reason: str | None = None
    mode: LlmMode


class Recommendation(_Base):
    id: str
    title: str
    text: str
    priority: Literal["alta", "media", "baja"]
    facts: dict[str, float | int | str]
    mode: LlmMode
