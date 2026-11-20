"""Agente Profesor BIM — API. Ejecutar desde backend/:
    .venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db
from app.config import API_VERSION, CORS_ORIGINS
from app.routers import ai, analysis, exports, feedback, issues, snapshots, system
from app.services.data import load_mapping, load_rules, load_uniclass


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_rules()  # valida data/rules.json contra contracts/rules.schema.json (falla al arrancar si no cumple)
    load_uniclass()
    load_mapping()
    db.init_db()
    yield


app = FastAPI(title="Agente Profesor BIM — API", version=API_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


def _msg_es(e: dict) -> str:
    """Mensaje en español para un error de validación de pydantic."""
    t, ctx = e.get("type", ""), e.get("ctx") or {}
    if t == "missing":
        return "campo obligatorio"
    if t in ("literal_error", "enum"):
        return f"valor no permitido (opciones: {str(ctx.get('expected', '')).replace(' or ', ' o ')})"
    if t.startswith("int_"):
        return "debe ser un número entero"
    if t.startswith("float_"):
        return "debe ser un número"
    if t.startswith("bool_"):
        return "debe ser verdadero o falso"
    if t == "string_type":
        return "debe ser texto"
    if t == "string_too_long":
        return f"texto demasiado largo (máximo {ctx.get('max_length')} caracteres)"
    if t in ("greater_than_equal", "greater_than"):
        return f"debe ser mayor{' o igual' if t.endswith('equal') else ''} que {ctx.get('ge', ctx.get('gt'))}"
    if t in ("list_type", "dict_type", "model_type", "model_attributes_type"):
        return "tipo de dato inválido"
    if t == "json_invalid":
        return "JSON mal formado"
    return "valor inválido"


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    """Cuerpo `Error` del contrato (detail string en español) + lista original en `errors`."""
    errs = exc.errors()
    detail = "; ".join(f"{'.'.join(str(p) for p in e.get('loc', []))}: {_msg_es(e)}" for e in errs)
    return JSONResponse(status_code=422, content={"detail": detail or "Cuerpo inválido",
                                                  "errors": jsonable_encoder(errs, custom_encoder={Exception: str})})


for r in (system, snapshots, issues, feedback, analysis, ai, exports):
    app.include_router(r.router, prefix="/api")
