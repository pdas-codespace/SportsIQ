import asyncio
import copy

import agents.workflow_nodes_edges as workflow


class _FakeSpan:
    def __init__(self, name):
        self.name = name
        self.attributes = {}
        self.events = []
        self.exceptions = []
        self.status = None

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def add_event(self, name, attributes=None):
        self.events.append((name, attributes or {}))

    def record_exception(self, exc):
        self.exceptions.append(exc)

    def set_status(self, status):
        self.status = status


class _FakeTracer:
    def __init__(self):
        self.spans = []

    def start_as_current_span(self, name):
        span = _FakeSpan(name)
        self.spans.append(span)
        return span


def test_graph_workflow_emits_approval_requests_and_finishes(monkeypatch):
    async def fake_monitor(ctx):
        return {
            "monitor_data": {
                "should_generate_offers": True,
                "engagement_score": 0.41,
            }
        }

    async def fake_generator(ctx):
        return {
            "offers": [
                {
                    "id": "offer_1",
                    "title": "Jersey Deal",
                    "description": "20% off",
                    "category": "merchandise",
                }
            ]
        }

    async def fake_guardrails(ctx):
        return {"clean_offers": ctx["offers"], "suppressed_offers": []}

    async def fake_approver(ctx):
        return {"approver_output": "processed"}

    saved_states = {}
    fake_tracer = _FakeTracer()

    def fake_save(run_id, state):
        saved_states[run_id] = copy.deepcopy(state)

    emitted = []

    def emitter(event_type, payload):
        emitted.append((event_type, copy.deepcopy(payload)))
        if event_type == "approval_required":
            workflow.set_approval_decision(
                payload["run_id"],
                payload["offer_id"],
                approved=True,
                reason="approved in test",
            )

    monkeypatch.setattr(workflow.checkpoint, "save", fake_save)
    monkeypatch.setattr(workflow, "_tracer", fake_tracer)
    monkeypatch.setattr(workflow, "_execute_engagement_monitor", fake_monitor)
    monkeypatch.setattr(workflow, "_execute_offer_generator", fake_generator)
    monkeypatch.setattr(workflow, "_execute_policy_guardrails", fake_guardrails)
    monkeypatch.setattr(workflow, "_execute_offer_approver", fake_approver)

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
    assert saved_states["run_1"]["workflow_status"] == "completed"
    assert saved_states["run_1"]["approval_decisions"] == {
        "offer_1": {"approved": True, "reason": "approved in test"}
    }
    span_names = [span.name for span in fake_tracer.spans]
    assert "sportsiq.workflow.graph.run" in span_names
    assert "sportsiq.workflow.node.engagement_monitor" in span_names
    assert "sportsiq.workflow.node.hitl_approval" in span_names
    assert "sportsiq.workflow.hitl_wait" in span_names

    root_span = next(span for span in fake_tracer.spans if span.name == "sportsiq.workflow.graph.run")
    assert root_span.attributes["sportsiq.workflow.kind"] == "nodes_edges"
    assert root_span.attributes["sportsiq.fan_id"] == "fan_1"
    assert root_span.attributes["sportsiq.game_id"] == "game_1"
    assert root_span.attributes["sportsiq.workflow.status"] == "completed"
    assert "sportsiq.fan_email" not in root_span.attributes

    for span in fake_tracer.spans:
        assert span.attributes["sportsiq.application_id"] == "sports-iq"
        assert span.attributes["sportsiq.deployment_id"] == "local"
        assert span.attributes["sportsiq.environment"] == "development"
        assert span.attributes["service.name"] == "sports-iq"
        assert span.attributes["service.version"] == "local"
        assert span.attributes["deployment.environment.name"] == "development"
        assert span.attributes["sportsiq.session_id"] == "run_1"
        assert span.attributes["sportsiq.conversation_id"] == "run_1"
        assert span.attributes["session.id"] == "run_1"
        assert span.attributes["conversation.id"] == "run_1"
        assert span.attributes["sportsiq.tenant_id"] == "sports-iq"
        assert span.attributes["tenant.id"] == "sports-iq"
        assert span.attributes["user.id"] == "fan_1"
        assert span.attributes["enduser.id"] == "fan_1"
        assert span.attributes["sportsiq.agent_name"]

    assert not workflow._approval_events
    assert not workflow._approval_decisions


def test_graph_records_suppressed_terminal():
    async def first_step(_ctx):
        return {"monitor_data": {"should_generate_offers": False}}

    async def run_graph():
        graph = workflow.WorkflowGraph()
        graph.add_node(workflow.Node("engagement_monitor", "step", execute_fn=first_step))
        graph.add_node(workflow.Node("terminal_suppressed", "terminal"))
        graph.add_edge(
            "engagement_monitor",
            "terminal_suppressed",
            condition=lambda ctx: not ctx["monitor_data"]["should_generate_offers"],
        )

        return await graph.execute("engagement_monitor")

    context = asyncio.run(run_graph())

    assert context["terminal_node"] == "terminal_suppressed"


def test_offer_generator_prompt_uses_selected_fan_section(monkeypatch):
    captured = {}

    class FakeAgent:
        async def run(self, prompt):
            captured["prompt"] = prompt

            class Response:
                text = (
                    '{"offers":[{"id":"offer_1","title":"End Zone Merch Hub Deal",'
                    '"description":"Limited cap pickup near EZ5","category":"merchandise",'
                    '"offer_type":"percentage_discount","value":"20%",'
                    '"offer_code":"ATL-EZ5","justification":"Near merch hub",'
                    '"incident_alert":null}]}'
                )

            return Response()

    monkeypatch.setattr(workflow.generator_def, "create_agent", lambda _credential: FakeAgent())

    result = asyncio.run(
        workflow._execute_offer_generator(
            {
                "run_id": "run_2",
                "fan_id": "fan_demo_003",
                "game_id": "game_1",
                "fan_name": "Fictional Fan 0003",
                "fan_loyalty_tier": "Gold",
                "preferred_section_id": "EZ5",
                "sport_context": {
                    "sport": "soccer",
                    "league_name": "soccer",
                    "home_team": "HCC",
                    "home_team_name": "Harbor City Comets",
                    "away_team": "MST",
                    "away_team_name": "Metro Stars",
                    "venue_label": "Stadium",
                    "period_label": "Half",
                },
                "monitor_data": {"engagement_score": 0.44},
            }
        )
    )

    assert result["offers"][0]["title"] == "End Zone Merch Hub Deal"
    assert '"section_id": "EZ5"' in captured["prompt"]
    assert '"preferred_section_id": "EZ5"' in captured["prompt"]
    assert '"sport": "soccer"' in captured["prompt"]
    assert '"home_team_name": "Harbor City Comets"' in captured["prompt"]
    assert '"away_team_name": "Metro Stars"' in captured["prompt"]
    assert '"home_team": "HCC"' in captured["prompt"]
    assert "Fictional Fan 0003" in captured["prompt"]
    assert "generic jersey and food/beverage discount pair" in captured["prompt"]
    assert '"section_id": "S112"' not in captured["prompt"]
