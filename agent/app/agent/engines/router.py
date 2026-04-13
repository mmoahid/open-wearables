"""Health router agent — wraps pygentic-ai GenericRouter."""

from __future__ import annotations

from pygentic_ai.engines.routers import GenericRouter

from app.agent.prompts.worker_prompts import WorkerType, build_worker_prompt
from app.agent.utils.model_utils import get_llm


class HealthRouter(GenericRouter):
    """Classifies health assistant messages as answer (1) or refuse (2).

    Wraps pygentic-ai GenericRouter with the health-domain routing prompt
    and the configured worker LLM from app settings.
    Returns pygentic-ai RoutingResponse with route=1 (answer) or route=2 (refuse).
    """

    def __init__(self) -> None:
        vendor, model, api_key = get_llm(is_worker=True)
        routing_prompt = build_worker_prompt(WorkerType.ROUTER)

        super().__init__(
            llm_vendor=vendor,
            llm_model=model,
            api_key=api_key,
            routing_prompt=routing_prompt,
        )
