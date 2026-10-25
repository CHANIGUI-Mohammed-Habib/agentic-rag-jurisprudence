"""Thin Claude wrapper: one call shape for agent, verifier and baseline, plus per-run metrics."""

import time
from dataclasses import dataclass, field

import anthropic

from . import config

# Server-side refusal fallback (Claude API): re-routes a refused request instead of failing the run.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    content: list[dict]
    stop_reason: str
    model: str
    usage: dict
    latency_s: float

    @property
    def text(self) -> str:
        return "".join(b.get("text", "") for b in self.content if b.get("type") == "text")

    @property
    def tool_uses(self) -> list[dict]:
        return [b for b in self.content if b.get("type") == "tool_use"]


@dataclass
class Metrics:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_latency_s: float = 0.0
    cost_usd: float = 0.0
    calls_by_role: dict = field(default_factory=dict)

    def add(self, role: str, model: str, usage: dict, latency: float) -> None:
        self.llm_calls += 1
        self.calls_by_role[role] = self.calls_by_role.get(role, 0) + 1
        inp = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
        out = usage.get("output_tokens", 0)
        self.input_tokens += inp
        self.output_tokens += out
        self.llm_latency_s += latency
        pin, pout = config.PRICES.get(model, (0.0, 0.0))
        self.cost_usd += (inp * pin + out * pout) / 1e6

    def as_dict(self) -> dict:
        return {**self.__dict__, "llm_latency_s": round(self.llm_latency_s, 2), "cost_usd": round(self.cost_usd, 4)}


class ClaudeLLM:
    def __init__(self, model: str = config.MODEL, client: anthropic.Anthropic | None = None):
        self.model = model
        self.client = client or anthropic.Anthropic()
        self.metrics = Metrics()

    def reset_metrics(self) -> Metrics:
        self.metrics = Metrics()
        return self.metrics

    def complete(self, *, role: str, system: str, messages: list[dict], effort: str,
                 tools: list[dict] | None = None, json_schema: dict | None = None,
                 max_tokens: int = config.MAX_TOKENS) -> LLMResult:
        output_config: dict = {"effort": effort}
        if json_schema:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        kwargs: dict = {"model": self.model, "max_tokens": max_tokens, "system": system,
                        "messages": messages, "output_config": output_config}
        if tools:
            kwargs["tools"] = tools
        if self.model in FALLBACK_MODELS:
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        t0 = time.perf_counter()
        try:
            resp = self.client.beta.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise LLMError("Authentification Anthropic refusée : définir ANTHROPIC_API_KEY dans .env") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Limite de débit Anthropic atteinte (429) après les tentatives automatiques") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Erreur API Anthropic {e.status_code} : {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f"Connexion à l'API Anthropic impossible : {e}") from e
        latency = time.perf_counter() - t0
        usage = resp.usage.model_dump(exclude_none=True) if resp.usage else {}
        self.metrics.add(role, self.model, usage, latency)
        return LLMResult(
            content=[b.model_dump(exclude_none=True) for b in resp.content],
            stop_reason=resp.stop_reason or "",
            model=resp.model,
            usage=usage,
            latency_s=latency,
        )
