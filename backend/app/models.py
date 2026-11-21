from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # se guarda naive UTC


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("project_code", "version_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(64), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    version_label: Mapped[str] = mapped_column(String(128))
    cde_state: Mapped[str] = mapped_column(String(16))
    rules_version: Mapped[str] = mapped_column(String(32))
    author: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    elements: Mapped[list["Element"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan", order_by="Element.id"
    )


class Element(Base):
    __tablename__ = "elements"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id", ondelete="CASCADE"), index=True)
    guid: Mapped[str] = mapped_column(String(64), index=True)
    element_id: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(64))
    discipline: Mapped[str] = mapped_column(String(8))
    family_name: Mapped[str | None] = mapped_column(String(255))
    type_name: Mapped[str] = mapped_column(String(255))
    classification_code: Mapped[str | None] = mapped_column(String(64))
    level: Mapped[str | None] = mapped_column(String(128))
    volume_m3: Mapped[float | None] = mapped_column(Float)
    area_m2: Mapped[float | None] = mapped_column(Float)
    length_m: Mapped[float | None] = mapped_column(Float)
    parameters: Mapped[dict | None] = mapped_column(JSON)

    snapshot: Mapped[Snapshot] = relationship(back_populates="elements")


class Issue(Base):
    """Identidad: (project_code, element_guid, rule_id, related_guid, issue_key). Persiste entre snapshots.

    issue_key distingue varios issues de la misma regla en el mismo elemento (R05: uno por parámetro faltante)."""
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(64), index=True)
    element_guid: Mapped[str | None] = mapped_column(String(64), index=True)
    rule_id: Mapped[str] = mapped_column(String(16), index=True)
    related_guid: Mapped[str | None] = mapped_column(String(64))
    issue_key: Mapped[str] = mapped_column(String(255), default="")
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id", ondelete="CASCADE"))  # último visto
    first_snapshot_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="open")
    discipline: Mapped[str | None] = mapped_column(String(8))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    fixed_by: Mapped[str | None] = mapped_column(String(16))


class SnapshotIssue(Base):
    """Qué issues estaban presentes en cada snapshot y su estado dentro de ese snapshot.

    Un PATCH actualiza el enlace del último snapshot del issue; el auto-fix de un snapshot posterior
    no toca los enlaces viejos (en esa versión el issue sí estaba abierto)."""
    __tablename__ = "snapshot_issues"

    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id", ondelete="CASCADE"), primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="open")

    issue: Mapped[Issue] = relationship()


class IssueEvent(Base):
    """Bitácora para el hilo del elemento: opened | fixed | dismissed."""
    __tablename__ = "issue_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    snapshot_id: Mapped[int | None] = mapped_column(Integer)


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    element_guid: Mapped[str | None] = mapped_column(String(64), index=True)
    rule_id: Mapped[str] = mapped_column(String(16), index=True)
    issue_id: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(32))
    comment: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
