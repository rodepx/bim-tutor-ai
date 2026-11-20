from fastapi import APIRouter

from app.ai import llm_mode
from app.config import API_VERSION
from app.schemas import Health, UniclassCode
from app.services.data import load_rules, uniclass_public

router = APIRouter(tags=["sistema"])


@router.get("/health", response_model=Health)
def health():
    return {"status": "ok", "version": API_VERSION, "llm_mode": llm_mode()}


@router.get("/rules")
def get_rules():
    return load_rules()


@router.get("/uniclass", response_model=list[UniclassCode])
def list_uniclass(category: str | None = None):
    return uniclass_public(category)
