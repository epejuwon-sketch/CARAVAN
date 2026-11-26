"""CARAVAN Standalone Platform — Provider-Independent AI Architecture.

Supports:
1. Google Gemini (via secure server-side REST API with structured tool calling)
2. CARAVAN Local Rule & Retrieval Engine (resilient, zero-downtime offline fallback)
3. Extensible provider abstraction for future proprietary CARAVAN models
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_settings
from app.services.copilot_tools import COPILOT_TOOL_DEFINITIONS

logger = logging.getLogger("caravan.ai")


class AIProviderResponse:
    """Standardized response from any AI Intelligence Provider."""

    def __init__(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        provider_used: str = "google_gemini",
        model_used: str = "gemini-2.5-flash",
        tokens_used: int = 0,
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.citations = citations or []
        self.actions = actions or []
        self.provider_used = provider_used
        self.model_used = model_used
        self.tokens_used = tokens_used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "citations": self.citations,
            "actions": self.actions,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
        }


class BaseAIProvider(ABC):
    """Abstract interface for AI Intelligence Providers."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIProviderResponse:
        pass


class GeminiAIProvider(BaseAIProvider):
    """Google Gemini AI Provider with secure server-side tool calling and context management."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key.strip()
        self.model = model.strip()

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIProviderResponse:
        # Build Gemini contents payload
        contents = []
        for m in messages:
            role = "user" if m.get("role") in ("USER", "user") else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m.get("content", "")}],
            })

        payload: Dict[str, Any] = {
            "contents": contents,
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if tools:
            # Map tools to Gemini standard format
            payload["tools"] = [{
                "functionDeclarations": tools
            }]

        # Candidate models and auth modes to try in priority order
        candidates = []
        if AIProviderFactory._discovered_working_model:
            candidates.append(AIProviderFactory._discovered_working_model)
        for m in [self.model, "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"]:
            if m and m not in candidates:
                candidates.append(m)

        auth_modes = [AIProviderFactory._discovered_auth_mode]
        for a in ["header", "query"]:
            if a not in auth_modes:
                auth_modes.append(a)

        api_versions = ["v1beta", "v1"]
        last_error = None

        for cand_model in candidates:
            clean_cand = cand_model.replace("models/", "")
            for api_ver in api_versions:
                for auth_mode in auth_modes:
                    url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{clean_cand}:generateContent"
                    headers = {"Content-Type": "application/json"}
                    params = {}
                    if auth_mode == "header":
                        headers["x-goog-api-key"] = self.api_key
                    else:
                        params["key"] = self.api_key

                    try:
                        with httpx.Client(timeout=12.0) as client:
                            res = client.post(url, json=payload, headers=headers, params=params)
                            if res.status_code == 200:
                                # Save working configuration
                                AIProviderFactory._discovered_working_model = clean_cand
                                AIProviderFactory._discovered_auth_mode = auth_mode
                                AIProviderFactory._discovered_api_version = api_ver

                                data = res.json()
                                candidates_data = data.get("candidates", [])
                                if not candidates_data:
                                    raise RuntimeError("Gemini returned empty candidates")

                                first_candidate = candidates_data[0]
                                parts = first_candidate.get("content", {}).get("parts", [])

                                text_content = ""
                                tool_calls = []

                                for p in parts:
                                    if "text" in p:
                                        text_content += p["text"]
                                    if "functionCall" in p:
                                        fc = p["functionCall"]
                                        tool_calls.append({
                                            "name": fc.get("name"),
                                            "args": fc.get("args", {}),
                                        })

                                usage_meta = data.get("usageMetadata", {})
                                tokens = usage_meta.get("totalTokenCount", len(text_content.split()))

                                return AIProviderResponse(
                                    content=text_content,
                                    tool_calls=tool_calls,
                                    provider_used="google_gemini",
                                    model_used=clean_cand,
                                    tokens_used=tokens,
                                )
                            else:
                                raw_err = res.text[:150]
                                if self.api_key in raw_err:
                                    raw_err = raw_err.replace(self.api_key, "[REDACTED_KEY]")
                                last_error = f"{api_ver}/{clean_cand} ({auth_mode}) HTTP {res.status_code}: {raw_err}"
                    except Exception as exc:
                        last_error = f"{api_ver}/{clean_cand} ({auth_mode}) exception: {exc}"

        logger.warning("All Gemini candidate attempts exhausted. Last error: %s", last_error)
        raise RuntimeError(f"Gemini API invocation failed: {last_error}")


class LocalRuleAIProvider(BaseAIProvider):
    """Deterministic, domain-grounded intelligence provider with zero hallucination guarantee."""

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIProviderResponse:
        last_msg = messages[-1].get("content", "") if messages else ""
        msg_lower = last_msg.lower()

        tool_calls = []
        # Pattern match user intent to structured tools
        if any(w in msg_lower for w in ("search", "find", "grant", "fund", "catalogue", "marketplace", "opportunit")):
            tool_calls.append({
                "name": "search_funding_opportunities",
                "args": {"query": last_msg, "open_only": True},
            })

        if any(w in msg_lower for w in ("eligible", "qualif", "score", "criteria", "assessment")):
            tool_calls.append({
                "name": "assess_business_eligibility",
                "args": {"opportunity_id": context.get("opportunity_id", "") if context else ""},
            })

        if any(w in msg_lower for w in ("doc", "upload", "file", "attach", "cac", "bank statement", "checklist")):
            tool_calls.append({
                "name": "inspect_organization_documents",
                "args": {"opportunity_id": context.get("opportunity_id", "") if context else ""},
            })

        if any(w in msg_lower for w in ("draft", "apply", "proposal", "executive summary", "outline", "write")):
            tool_calls.append({
                "name": "draft_application_package",
                "args": {"opportunity_id": context.get("opportunity_id", "") if context else ""},
            })

        if any(w in msg_lower for w in ("readiness", "diagnostic", "pillar", "governance", "maturity")):
            tool_calls.append({
                "name": "run_readiness_diagnostic",
                "args": {},
            })

        return AIProviderResponse(
            content="",
            tool_calls=tool_calls,
            provider_used="caravan_grounded_engine",
            model_used="caravan-rule-retrieval-v1",
            tokens_used=len(last_msg.split()),
        )


class AIProviderFactory:
    """Provider-independent factory with resilient fallback logic."""

    _discovered_working_model: Optional[str] = None
    _discovered_auth_mode: str = "header"
    _discovered_api_version: str = "v1beta"

    @staticmethod
    def get_provider() -> BaseAIProvider:
        settings = get_settings()
        api_key = (settings.GEMINI_API_KEY or "").strip()

        if api_key and settings.CARAVAN_AI_PROVIDER == "gemini":
            selected_model = AIProviderFactory._discovered_working_model or settings.CARAVAN_AI_MODEL
            return GeminiAIProvider(api_key=api_key, model=selected_model)

        return LocalRuleAIProvider()

    @staticmethod
    def generate_resilient(
        messages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AIProviderResponse:
        """Attempts Gemini invocation first; safely falls back to local engine upon failure."""
        provider = AIProviderFactory.get_provider()
        try:
            return provider.generate(
                messages=messages,
                system_instruction=system_instruction,
                tools=tools,
                context=context,
            )
        except Exception as exc:
            logger.info("AI Provider exception handled gracefully with LocalRuleAIProvider fallback: %s", exc)
            fallback = LocalRuleAIProvider()
            resp = fallback.generate(
                messages=messages,
                system_instruction=system_instruction,
                tools=tools,
                context=context,
            )
            resp.provider_used = "caravan_grounded_engine (gemini_fallback)"
            return resp

    @staticmethod
    def diagnose_gemini() -> Dict[str, Any]:
        """Diagnose exact endpoint availability, model listing, and candidate models without leaking secrets."""
        settings = get_settings()
        api_key = (settings.GEMINI_API_KEY or "").strip()
        if not api_key:
            return {
                "configured": False,
                "gemini_configured": False,
                "error": "GEMINI_API_KEY is not configured.",
                "list_models_probes": [],
                "available_models": [],
                "candidate_probes": {},
                "working_model": None,
            }

        diag: Dict[str, Any] = {
            "configured": True,
            "gemini_configured": True,
            "configured_model": settings.CARAVAN_AI_MODEL,
            "list_models_probes": [],
            "available_models": [],
            "candidate_probes": {},
            "working_model": None,
            "working_auth_mode": None,
            "working_api_version": None,
        }

        # Probe 1: List models via v1beta and v1, header and query (with early exit on 200)
        list_endpoints = [
            ("v1beta_header", "https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": api_key}, {}),
            ("v1beta_query", "https://generativelanguage.googleapis.com/v1beta/models", {}, {"key": api_key}),
            ("v1_header", "https://generativelanguage.googleapis.com/v1/models", {"x-goog-api-key": api_key}, {}),
        ]

        working_list = None
        for name, url, headers, params in list_endpoints:
            try:
                with httpx.Client(timeout=2.5) as client:
                    resp = client.get(url, headers=headers, params=params)
                    snippet = resp.text[:250]
                    if api_key in snippet:
                        snippet = snippet.replace(api_key, "[REDACTED_KEY]")
                    diag["list_models_probes"].append({
                        "endpoint": name,
                        "status_code": resp.status_code,
                        "response": snippet,
                    })
                    if resp.status_code == 200:
                        working_list = resp.json()
                        break
            except Exception as exc:
                diag["list_models_probes"].append({
                    "endpoint": name,
                    "error": str(exc),
                })

        if working_list and "models" in working_list:
            for m in working_list.get("models", []):
                m_name = m.get("name", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    diag["available_models"].append({
                        "name": m_name,
                        "displayName": m.get("displayName", ""),
                        "supportedMethods": methods,
                    })

        # Probe 2: Test candidate models
        candidates = []
        if AIProviderFactory._discovered_working_model:
            candidates.append(AIProviderFactory._discovered_working_model)
        candidates.extend([
            settings.CARAVAN_AI_MODEL,
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ])
        for am in diag["available_models"]:
            clean_am = am["name"].replace("models/", "")
            if clean_am not in candidates:
                candidates.append(clean_am)

        seen = set()
        dedup_candidates = [c for c in candidates if c and not (c in seen or seen.add(c))]

        for cand in dedup_candidates:
            if diag["working_model"]:
                break
            clean_cand = cand.replace("models/", "")
            cand_results = {}
            for api_ver in ("v1beta", "v1"):
                if diag["working_model"]:
                    break
                for auth_mode in ("header", "query"):
                    mode_key = f"{api_ver}_{auth_mode}"
                    url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{clean_cand}:generateContent"
                    headers = {"Content-Type": "application/json"}
                    params = {}
                    if auth_mode == "header":
                        headers["x-goog-api-key"] = api_key
                    else:
                        params["key"] = api_key

                    payload = {"contents": [{"parts": [{"text": "CARAVAN diagnostic ping"}]}]}
                    try:
                        with httpx.Client(timeout=2.5) as client:
                            resp = client.post(url, json=payload, headers=headers, params=params)
                            snippet = resp.text[:200]
                            if api_key in snippet:
                                snippet = snippet.replace(api_key, "[REDACTED_KEY]")
                            cand_results[mode_key] = {
                                "status_code": resp.status_code,
                                "response": snippet,
                            }
                            if resp.status_code == 200:
                                diag["working_model"] = clean_cand
                                diag["working_auth_mode"] = auth_mode
                                diag["working_api_version"] = api_ver
                                AIProviderFactory._discovered_working_model = clean_cand
                                AIProviderFactory._discovered_auth_mode = auth_mode
                                AIProviderFactory._discovered_api_version = api_ver
                                break
                    except Exception as exc:
                        cand_results[mode_key] = {"error": str(exc)}
            diag["candidate_probes"][clean_cand] = cand_results

        return diag

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Returns live AI provider diagnostics without leaking secrets (fast serverless check)."""
        settings = get_settings()
        api_key = (settings.GEMINI_API_KEY or "").strip()
        gemini_configured = bool(api_key)
        provider = settings.CARAVAN_AI_PROVIDER
        model = settings.CARAVAN_AI_MODEL

        live_probe_status = "NOT_CONFIGURED"
        probe_detail = "GEMINI_API_KEY is not configured in environment variables. Local Grounded Engine is active."
        is_healthy = False
        working_model = AIProviderFactory._discovered_working_model

        if gemini_configured and provider == "gemini":
            target_model = working_model or model or "gemini-2.0-flash"
            clean_model = target_model.replace("models/", "")
            
            # Fast live probe (max 2 attempts, <= 2.5s timeout each)
            try:
                auth_mode = AIProviderFactory._discovered_auth_mode or "header"
                api_ver = AIProviderFactory._discovered_api_version or "v1beta"
                
                headers = {"Content-Type": "application/json"}
                params = {}
                if auth_mode == "header":
                    headers["x-goog-api-key"] = api_key
                else:
                    params["key"] = api_key
                    
                url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{clean_model}:generateContent"
                with httpx.Client(timeout=2.5) as client:
                    probe_res = client.post(
                        url,
                        json={"contents": [{"parts": [{"text": "ping"}]}]},
                        headers=headers,
                        params=params,
                    )
                    
                    if probe_res.status_code == 200:
                        is_healthy = True
                        working_model = clean_model
                        live_probe_status = "HEALTHY"
                        probe_detail = f"Live handshake confirmed: Google Gemini API is answering queries successfully using model '{clean_model}'."
                    elif probe_res.status_code == 404:
                        # Fast fallback attempt with query auth and gemini-1.5-flash
                        with httpx.Client(timeout=2.5) as fb_client:
                            fb_res = fb_client.post(
                                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                                json={"contents": [{"parts": [{"text": "ping"}]}]},
                                headers={"Content-Type": "application/json"},
                                params={"key": api_key},
                            )
                            if fb_res.status_code == 200:
                                is_healthy = True
                                working_model = "gemini-1.5-flash"
                                AIProviderFactory._discovered_working_model = "gemini-1.5-flash"
                                AIProviderFactory._discovered_auth_mode = "query"
                                AIProviderFactory._discovered_api_version = "v1beta"
                                live_probe_status = "HEALTHY"
                                probe_detail = "Live handshake confirmed: Google Gemini API is answering queries successfully using model 'gemini-1.5-flash'."
                            else:
                                live_probe_status = f"ERROR_HTTP_{fb_res.status_code}"
                                probe_detail = f"Configured model '{clean_model}' returned 404; fallback returned HTTP {fb_res.status_code}."
                    elif probe_res.status_code in (400, 401, 403):
                        live_probe_status = f"AUTHENTICATION_FAILED_HTTP_{probe_res.status_code}"
                        probe_detail = f"Google API returned HTTP {probe_res.status_code} (check API key validity and Generative Language API enablement)."
                    elif probe_res.status_code == 429:
                        live_probe_status = "RATE_LIMITED_HTTP_429"
                        probe_detail = "Google Generative Language API quota exceeded or rate limited."
                    else:
                        live_probe_status = f"ERROR_HTTP_{probe_res.status_code}"
                        probe_detail = f"Google API returned HTTP {probe_res.status_code} during status probe."
            except Exception as exc:
                live_probe_status = "TIMEOUT_OR_NETWORK_ERROR"
                probe_detail = f"Could not reach Google Gemini endpoint: {exc.__class__.__name__}"

        active_provider = "google_gemini" if is_healthy else "caravan_grounded_engine"

        return {
            "gemini_configured": gemini_configured,
            "configured_provider": provider,
            "configured_model": model,
            "active_provider": active_provider,
            "active_model": working_model or (model if is_healthy else "caravan-rule-retrieval-v1"),
            "fallback_active": not is_healthy,
            "live_probe_status": live_probe_status,
            "reason": probe_detail,
            "database_grounding_active": True,
            "structured_tool_calling_ready": True,
        }
