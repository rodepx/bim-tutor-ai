"""Módulo de IA del Agente Profesor BIM (OpenRouter o mock determinista)."""
from .guard import check_text
from .llm import llm_mode
from .service import build_recommendations, explain_rule, suggest_classification

__all__ = ["explain_rule", "suggest_classification", "build_recommendations", "llm_mode", "check_text"]
