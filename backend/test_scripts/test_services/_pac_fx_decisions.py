"""Test helper (A2, project 67): a test names an FX decision by what it converts, and asks the engine's one list for its id.

The engine's ``evaluation.reachability.fx_decision_specs`` is the only place that says which FX decisions a scenario has and how
they are keyed. A test that wrote ``fx:<route>:<currency>`` by hand would pin today's key; this helper finds the decision by
broker and currencies (and, while a pair can still have one decision per buy route, by the route it serves), so a change of key
moves no test. Not a test module (leading underscore): pytest never collects it, and the runner catalogue does not list it.
"""

from __future__ import annotations

from backend.app.services.pac_allocator.evaluation.reachability import FxDecisionSpec, fx_decision_specs
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index
from backend.app.services.pac_allocator.models import ExactPlannerScenario


def fx_spec(scenario: ExactPlannerScenario, *, source: str, destination: str | None = None, broker_id: str | None = None, route_id: str | None = None) -> FxDecisionSpec:
    """The one FX decision of ``scenario`` that converts ``source`` (to ``destination``, at ``broker_id``, for ``route_id``, when given)."""
    specs = fx_decision_specs(scenario, build_scenario_index(scenario), None)
    matches = [spec for spec in specs if spec.source_currency == source and (destination is None or spec.destination_currency == destination) and (broker_id is None or spec.broker_id == broker_id) and (route_id is None or spec.representative_route_id == route_id)]
    if len(matches) != 1:
        raise AssertionError(f"expected one FX decision {source}->{destination} (broker {broker_id}, route {route_id}), found {[spec.decision_id for spec in matches]}")
    return matches[0]


def fx_id(scenario: ExactPlannerScenario, *, source: str, destination: str | None = None, broker_id: str | None = None, route_id: str | None = None) -> str:
    """The decision id of ``fx_spec``."""
    return fx_spec(scenario, source=source, destination=destination, broker_id=broker_id, route_id=route_id).decision_id
