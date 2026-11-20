"""Exportes: BCF 2.1, CSV 4D, COBie mínimo."""
import csv
import io
import re
import uuid
import zipfile
from xml.sax.saxutils import escape, quoteattr

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app import models
from app.schemas import iso_utc
from app.services.budget import magnitude
from app.services.common import snapshot_issues, unique_elements
from app.services.data import mapping_by_code, rule_name, uniclass_by_code

# ---------------------------------------------------------------- IFC GUID
_IFC_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
_UNIQUE_ID = re.compile(r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})-([0-9a-fA-F]{8})$")


def ifc_guid_from_unique_id(unique_id: str) -> str | None:
    """Mismo algoritmo que Revit ExportUtils.GetExportId: episodio XOR ElementId, comprimido a 22 caracteres."""
    m = _UNIQUE_ID.match(unique_id or "")
    if not m:
        return None
    episode, elem = m.group(1).replace("-", ""), int(m.group(2), 16)
    n = int(episode[:24], 16) << 32 | (int(episode[24:], 16) ^ elem)
    out = []
    for _ in range(22):
        out.append(_IFC_CHARS[n % 64])
        n //= 64
    return "".join(reversed(out))


# ---------------------------------------------------------------- BCF 2.1
_BCF_VERSION = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Version VersionId="2.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<DetailedVersion>2.1</DetailedVersion></Version>\n"
)
_PRIORITY = {"error": "Alta", "warning": "Media", "info": "Baja"}


def _component(guid: str) -> str:
    ifc = ifc_guid_from_unique_id(guid)
    attr = f" IfcGuid={quoteattr(ifc)}" if ifc else ""
    return (
        f"<Component{attr}><OriginatingSystem>Autodesk Revit</OriginatingSystem>"
        f"<AuthoringToolId>{escape(guid)}</AuthoringToolId></Component>"
    )


def build_bcf(db: Session, snap: models.Snapshot) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bcf.version", _BCF_VERSION)
        z.writestr(
            "project.bcfp",
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<ProjectExtension><Project ProjectId="{uuid.uuid5(uuid.NAMESPACE_URL, snap.project_code)}">'
            f"<Name>{escape(snap.project_code)}</Name></Project><ExtensionSchema></ExtensionSchema></ProjectExtension>\n",
        )
        for issue in snapshot_issues(db, snap.id, "open"):
            topic = str(uuid.uuid5(uuid.NAMESPACE_URL, f"profesor-bim/issue/{issue.id}"))
            vp = str(uuid.uuid5(uuid.NAMESPACE_URL, f"profesor-bim/issue/{issue.id}/vp"))
            guids = [g for g in (issue.element_guid, issue.related_guid) if g]
            title = f"{issue.rule_id} - {rule_name(issue.rule_id)}"
            author = snap.author or "profesor-bim"
            markup = (
                '<?xml version="1.0" encoding="UTF-8"?>\n<Markup>'
                f'<Topic Guid="{topic}" TopicType="Issue" TopicStatus="Open">'
                f"<Title>{escape(title)}</Title>"
                f"<Priority>{_PRIORITY.get(issue.severity, 'Media')}</Priority>"
                f"<Labels>{escape(issue.rule_id)}</Labels>"
                f"<Labels>{escape(issue.discipline or 'DOC')}</Labels>"
                f"<CreationDate>{iso_utc(issue.first_seen_at)}</CreationDate>"
                f"<CreationAuthor>{escape(author)}</CreationAuthor>"
                f"<Description>{escape(issue.message)}</Description>"
                "</Topic>"
            )
            if guids:
                markup += f'<Viewpoints Guid="{vp}"><Viewpoint>viewpoint.bcfv</Viewpoint></Viewpoints>'
            markup += "</Markup>\n"
            z.writestr(f"{topic}/markup.bcf", markup)
            if guids:
                comps = "".join(_component(g) for g in guids)
                z.writestr(
                    f"{topic}/viewpoint.bcfv",
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    f'<VisualizationInfo Guid="{vp}"><Components>'
                    f"<Selection>{comps}</Selection>"
                    '<Visibility DefaultVisibility="true"/>'
                    "</Components></VisualizationInfo>\n",
                )
    return buf.getvalue()


# ---------------------------------------------------------------- 4D CSV
CSV_4D_COLUMNS = ["guid", "category", "type_name", "level", "uniclass_code", "partida_codigo", "quantity", "unit", "fase_sugerida"]
_FASE_BY_CATEGORY = {
    "OST_StructuralFoundation": "cimentacion",
    "OST_StructuralColumns": "estructura",
    "OST_StructuralFraming": "estructura",
    "OST_Floors": "estructura",
    "OST_Walls": "albanileria",
    "OST_Doors": "acabados",
    "OST_Windows": "acabados",
}
_FASE_BY_CODE = {"Ss_20_05_65": "cimentacion", "Ss_25_10_20": "estructura"}  # cimiento corrido, placas


def fase_sugerida(category: str, code: str | None) -> str:
    return _FASE_BY_CODE.get(code or "") or _FASE_BY_CATEGORY.get(category, "acabados")


def build_4d_csv(snap: models.Snapshot) -> str:
    mapping, uniclass = mapping_by_code(), uniclass_by_code()
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(CSV_4D_COLUMNS)
    for el in unique_elements(snap):
        code = el.classification_code or ""
        partida, qty, unit = "", "", ""
        uc = uniclass.get(code)
        rows = mapping.get(code) if uc and el.category in uc["revit_categories"] else None
        if rows:  # partida principal = primera fila del mapeo (p. ej. el concreto)
            row = rows[0]
            partida, unit = row["partida_codigo"], row["unidad"]
            mag = magnitude(el, row["magnitud_fuente"])
            qty = round(mag * row["factor"], 3) if mag else ""
        w.writerow([el.guid, el.category, el.type_name, el.level or "", code, partida, qty, unit,
                    fase_sugerida(el.category, code)])
    return out.getvalue()


# ---------------------------------------------------------------- COBie
def build_cobie(snap: models.Snapshot) -> bytes:
    created_by = "bim@profesor-bim.local"
    created_on = iso_utc(snap.created_at)
    elements = unique_elements(snap)
    wb = Workbook()
    ws = wb.active
    ws.title = "Contact"
    ws.append(["Email", "CreatedBy", "CreatedOn", "Category", "Company", "Phone", "GivenName"])
    ws.append([created_by, created_by, created_on, "BIM Manager", snap.project_code, "n/a", snap.author or "n/a"])

    ws = wb.create_sheet("Facility")
    ws.append(["Name", "CreatedBy", "CreatedOn", "Category", "ProjectName", "SiteName", "LinearUnits", "AreaUnits",
               "VolumeUnits", "CurrencyUnit", "Phase", "ExternalProjectIdentifier"])
    ws.append([snap.file_name, created_by, created_on, "n/a", snap.project_code, "n/a", "meters", "square meters",
               "cubic meters", "PEN", snap.cde_state, snap.version_label])

    ws = wb.create_sheet("Floor")
    ws.append(["Name", "CreatedBy", "CreatedOn", "Category", "ExtSystem", "ExtObject", "Description"])
    for level in sorted({e.level for e in elements if e.level}):
        ws.append([level, created_by, created_on, "Floor", "Autodesk Revit", "Level", level])

    ws = wb.create_sheet("Type")
    ws.append(["Name", "CreatedBy", "CreatedOn", "Category", "Description", "AssetType", "ExtSystem", "ExtObject"])
    for type_name, el in sorted({e.type_name: e for e in elements}.items()):
        ws.append([type_name, created_by, created_on, el.classification_code or "n/a", el.family_name or type_name,
                   "Fixed", "Autodesk Revit", el.category])

    ws = wb.create_sheet("Component")
    ws.append(["Name", "CreatedBy", "CreatedOn", "TypeName", "Space", "Description", "ExtSystem", "ExtObject",
               "ExtIdentifier"])
    for el in elements:
        name = f"{el.type_name}-{el.element_id if el.element_id is not None else el.guid[-8:]}"
        ws.append([name, created_by, created_on, el.type_name, el.level or "n/a", el.category, "Autodesk Revit",
                   el.category, el.guid])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
