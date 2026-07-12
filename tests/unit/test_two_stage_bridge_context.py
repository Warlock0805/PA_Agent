from __future__ import annotations


def test_orchestrator_sets_stage_on_context_aware_client() -> None:
    from pa_agent.orchestrator.two_stage import TwoStageOrchestrator

    class ContextAwareClient:
        def __init__(self) -> None:
            self.stages: list[str] = []

        def set_stage_context(self, stage: str) -> None:
            self.stages.append(stage)

    orchestrator = TwoStageOrchestrator.__new__(TwoStageOrchestrator)
    client = ContextAwareClient()
    orchestrator._client = client

    orchestrator._set_client_stage_context("stage1")
    orchestrator._set_client_stage_context("stage2")

    assert client.stages == ["stage1", "stage2"]


def test_orchestrator_keeps_existing_client_compatible() -> None:
    from pa_agent.orchestrator.two_stage import TwoStageOrchestrator

    orchestrator = TwoStageOrchestrator.__new__(TwoStageOrchestrator)
    orchestrator._client = object()

    orchestrator._set_client_stage_context("stage1")
