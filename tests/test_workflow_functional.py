import asyncio
import copy

from agent_framework import WorkflowRunState

import agents.workflow_functional as workflow


class _FakeRequest:
    def __init__(self, request_id, data):
        self.request_id = request_id
        self.data = data


class _FakeResult:
    def __init__(self, final_state, requests=None, outputs=None):
        self._final_state = final_state
        self._requests = requests or []
        self._outputs = outputs or []

    def get_final_state(self):
        return self._final_state

    def get_request_info_events(self):
        return self._requests

    def get_outputs(self):
        return self._outputs


class _FakeFunctionalWorkflow:
    def __init__(self):
        self.responses = None

    async def run(self, payload=None, responses=None):
        if responses is None:
            return _FakeResult(
                WorkflowRunState.IDLE_WITH_PENDING_REQUESTS,
                requests=[
                    _FakeRequest(
                        "approval:offer_1",
                        {
                            "offer_id": "offer_1",
                            "offer": {
                                "id": "offer_1",
                                "title": "Jersey Deal",
                                "description": "20% off",
                                "category": "merchandise",
                            },
                        },
                    )
                ],
            )

        self.responses = responses
        return _FakeResult(
            "completed",
            outputs=[
                {
                    "status": "completed",
                    "monitor_output": {"should_generate_offers": True},
                    "offers": [
                        {
                            "id": "offer_1",
                            "title": "Jersey Deal",
                            "description": "20% off",
                            "category": "merchandise",
                        }
                    ],
                    "decisions": responses,
                    "suppressed_offers": [],
                    "approver_output": "processed",
                }
            ],
        )


def test_wait_for_decisions_handles_fast_approval_before_event_registration():
    workflow._approval_events.clear()
    workflow._approval_decisions.clear()

    workflow.set_approval_decision(
        "run_fast",
        "offer_1",
        approved=True,
        reason="approved before wait",
    )

    decisions = asyncio.run(
        asyncio.wait_for(workflow._wait_for_decisions("run_fast", ["offer_1"]), timeout=1.0)
    )

    assert decisions == {"offer_1": {"approved": True, "reason": "approved before wait"}}

    workflow._approval_events.clear()
    workflow._approval_decisions.clear()


def test_functional_workflow_registers_approval_events_before_emitting(monkeypatch):
    fake_workflow = _FakeFunctionalWorkflow()
    saved_states = []

    def fake_save(_run_id, state):
        saved_states.append(copy.deepcopy(state))

    emitted = []

    def emitter(event_type, payload):
        emitted.append((event_type, copy.deepcopy(payload)))
        if event_type == "approval_required":
            assert f"{payload['run_id']}:{payload['offer_id']}" in workflow._approval_events
            workflow.set_approval_decision(
                payload["run_id"],
                payload["offer_id"],
                approved=True,
                reason="approved in test",
            )

    monkeypatch.setattr(workflow.checkpoint, "save", fake_save)
    monkeypatch.setattr(workflow, "_sportsiq_workflow", fake_workflow)

    workflow._approval_events.clear()
    workflow._approval_decisions.clear()

    asyncio.run(
        workflow.start(
            run_id="run_1",
            fan_id="fan_1",
            game_id="game_1",
            event_emitter=emitter,
            fan_name="Test Fan",
            fan_loyalty_tier="Gold",
            fan_email="fan@example.com",
        )
    )

    event_types = [event_type for event_type, _ in emitted]
    assert "approval_required" in event_types
    assert event_types.index("approval_required") < event_types.index("run_finished")
    assert any(state["workflow_status"] == "awaiting_approval" for state in saved_states)
    assert saved_states[-1]["workflow_status"] == "completed"
    assert fake_workflow.responses == {
        "approval:offer_1": {"approved": True, "reason": "approved in test"}
    }
    assert not workflow._approval_events
    assert not workflow._approval_decisions
