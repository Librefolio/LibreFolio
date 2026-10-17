"""
GET /api/v1/utilities/currencies/suggest — lot E-19b1 (workstream E), item 2: the public suggestion endpoint.

E-19a gave the backend three answers about a stored currency value (``backend/app/schemas/common.py``):
``is_canonical_iso_currency`` (stored as ``iso_currency_code`` stores it), ``suggested_iso_currency`` (the one ISO 4217
code it stands for, or None) and, with E-19b1, ``iso_currency_candidates`` (every code it may stand for). The currency
picker of the frontend shows a stored non-ISO value with a hint, so it asks the backend through this endpoint.

The contract (E-19b1):

- ``GET /api/v1/utilities/currencies/suggest?value=<text>`` is **public**, like ``GET /api/v1/utilities/currencies``:
  no login needed. Every call of this module is made without a session.
- It answers 200 with exactly the keys ``canonical`` (bool, ``is_canonical_iso_currency(value)``), ``suggestion``
  (a string or null, ``suggested_iso_currency(value)``) and ``candidates`` (a list, ``iso_currency_candidates(value)``):

  ===================  =========  ==========  ==============
  value                canonical  suggestion  candidates
  ===================  =========  ==========  ==============
  ``978``              false      EUR         ["EUR"]
  ``EUR``              true       EUR         ["EUR"]
  ``eur``              false      EUR         ["EUR"]
  ``Bolívar Soberano`` false      null        ["VED", "VES"]
  ``BTC``              false      null        []
  ``GBX``              false      null        []
  XXX's own name (65)  false      XXX         ["XXX"]
  ===================  =========  ==========  ==============

  ``Bolívar Soberano`` travels through httpx ``params``, URL-encoded.
- The bound: a value of 200 characters answers 200 (false, null, []); one of 201 characters answers 422.
- A missing ``value`` answers 422; an empty one answers 422.

Two more, read from the rest of E-19b1 rather than from this item's table: the answer agrees with the three functions
for more values than the table's (CSA-API-05), and the OpenAPI document names the operation
``suggest_currency_api_v1_utilities_currencies_suggest_get``, the name the frontend's ``currencyStore.suggestCurrency``
calls through the generated client (CSA-API-06).

"RED" tests (marked ``# red until E-19b1``) fail before E-19b1: the route does not exist yet, so it answers 404.
``iso_currency_candidates`` is looked up inside the test that needs it, never at import, so the module collects. The
"GUARD (green today)" half of CSA-API-02 checks that ``GET /utilities/currencies`` is public today: the property the
new route must share.

Reads only: the endpoint is a computation, so nothing is written to the lane's database and nothing needs cleaning.
The server is the lane's, reached as ``test_utilities.py`` reaches it (``_TestingServerManager``, ``TEST_PORT``).
"""

from typing import Any, Callable

import httpx
import pycountry
import pytest

from backend.app.config import get_settings
from backend.app.schemas import common as common_module
from backend.app.schemas.common import is_canonical_iso_currency, suggested_iso_currency
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
SUGGEST_URL = f"{API_BASE}/utilities/currencies/suggest"
SUGGEST_PATH = "/api/v1/utilities/currencies/suggest"
TIMEOUT = 30

#: The operation the frontend's generated client calls (``currencyStore.suggestCurrency``, E-19b1 item 2's client).
OPERATION_ID = "suggest_currency_api_v1_utilities_currencies_suggest_get"

#: The three keys of an answer, and nothing else.
ANSWER_KEYS = {"canonical", "suggestion", "candidates"}

#: The longest value the endpoint takes.
VALUE_MAX_LENGTH = 200

#: XXX's own ISO name: 65 characters, the longest ISO name.
XXX_NAME = getattr(pycountry.currencies.get(alpha_3="XXX"), "name", "")

#: The contract's table: (value, canonical, suggestion, candidates, test id).
TABLE = (
    ("978", False, "EUR", ["EUR"], "numeric-978"),
    ("EUR", True, "EUR", ["EUR"], "EUR"),
    ("eur", False, "EUR", ["EUR"], "lower-eur"),
    ("Bolívar Soberano", False, None, ["VED", "VES"], "Bolivar-Soberano"),
    ("BTC", False, None, [], "BTC"),
    ("GBX", False, None, [], "GBX"),
    (XXX_NAME, False, "XXX", ["XXX"], "XXX-own-name-65-chars"),
)

#: More values, for the agreement with the three functions: padding, a name, other numeric codes, a subunit code, a
#: test code, a name of other case.
MORE_VALUES = (" usd ", "\u00a0gbp\u00a0", "Euro", "840", "999", "ZAC", "ila", "XTS", "Pound Sterling", "bolívar soberano", "8", "YEN")


@pytest.fixture(scope="module")
def test_server():
    """Start test server once for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


def _candidates() -> Callable[[Any], tuple[str, ...]]:
    """``iso_currency_candidates``, or the test fails. Looked up here, not imported, so the module collects before E-19b1."""
    function = getattr(common_module, "iso_currency_candidates", None)
    if function is None:
        pytest.fail("red until E-19b1: backend.app.schemas.common.iso_currency_candidates does not exist yet", pytrace=False)
    return function


async def _suggest(client: httpx.AsyncClient, **params: Any) -> httpx.Response:
    """``GET /utilities/currencies/suggest`` with these query parameters, on a client without a session."""
    assert not client.cookies, f"precondition: the call is made without a session, the client holds {list(client.cookies)}"
    return await client.get(SUGGEST_URL, params=params, timeout=TIMEOUT)


def _answer(response: httpx.Response, value: str) -> dict[str, Any]:
    """The JSON of a 200, or the test fails naming the status (404 before E-19b1: the route does not exist)."""
    shown = value if len(value) <= 24 else f"{value[:12]}…({len(value)} chars)"
    if response.status_code == 404:
        pytest.fail(f"red until E-19b1: GET {SUGGEST_PATH}?value={shown} answers 404: the route does not exist yet", pytrace=False)
    assert response.status_code == 200, f"GET {SUGGEST_PATH}?value={shown}: expected 200, got {response.status_code}: {response.text[:300]}"
    body = response.json()
    assert isinstance(body, dict) and set(body) == ANSWER_KEYS, f"the answer has exactly the keys {sorted(ANSWER_KEYS)}: {body}"
    assert isinstance(body["canonical"], bool), f"canonical is a boolean: {body}"
    assert body["suggestion"] is None or isinstance(body["suggestion"], str), f"suggestion is a string or null: {body}"
    assert isinstance(body["candidates"], list) and all(isinstance(code, str) for code in body["candidates"]), f"candidates is a list of strings: {body}"
    return body


# ============================================================
# The answer
# ============================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("value,canonical,suggestion,candidates", [pytest.param(value, canonical, suggestion, candidates, id=name) for value, canonical, suggestion, candidates, name in TABLE])
async def test_the_answer_for_each_value_of_the_table(test_server, value, canonical, suggestion, candidates):  # red until E-19b1
    """CSA-API-01 — RED: without a session, each value of the contract's table answers 200 with exactly ``canonical``,
    ``suggestion`` and ``candidates``, as the table says. ``Bolívar Soberano`` travels URL-encoded through ``params``."""
    print_section(f"CSA-API-01: suggest {value[:24]!r}")
    if suggestion == "XXX":
        assert len(value) == 65, f"precondition: XXX's own ISO name is 65 characters: {value!r}"
    async with httpx.AsyncClient() as client:
        body = _answer(await _suggest(client, value=value), value)
    assert body == {"canonical": canonical, "suggestion": suggestion, "candidates": candidates}, f"{value!r}: {body}"
    print_success(f"{value[:24]!r} → {body}")


@pytest.mark.asyncio
async def test_the_suggestion_is_public_like_the_currency_list(test_server):  # red until E-19b1
    """CSA-API-02 — RED (with a GUARD half, green today): without a session, ``GET /utilities/currencies`` answers 200 (the
    positive control: the list is public today), and so does ``GET /utilities/currencies/suggest?value=EUR``."""
    print_section("CSA-API-02: public, like the currency list")
    async with httpx.AsyncClient() as client:
        listed = await client.get(f"{API_BASE}/utilities/currencies", timeout=TIMEOUT)
        assert listed.status_code == 200, f"GUARD: GET /utilities/currencies is public, it answers 200 without a session: {listed.status_code} {listed.text[:200]}"
        body = _answer(await _suggest(client, value="EUR"), "EUR")
    assert body["canonical"] is True, body
    print_success("both answer without a session")


# ============================================================
# The bound and the missing value
# ============================================================


@pytest.mark.asyncio
async def test_a_value_of_200_characters_is_answered_and_one_of_201_is_refused(test_server):  # red until E-19b1
    """CSA-API-03 — RED: a value of 200 characters answers 200, ``false``, ``null``, ``[]``; one of 201 characters answers
    422 (the refusal does not send the value back, A-35)."""
    print_section("CSA-API-03: 200 characters, then 201")
    at_bound = "Q" * VALUE_MAX_LENGTH
    past_bound = "Q" * (VALUE_MAX_LENGTH + 1)
    async with httpx.AsyncClient() as client:
        body = _answer(await _suggest(client, value=at_bound), at_bound)
        assert body == {"canonical": False, "suggestion": None, "candidates": []}, f"200 characters: {body}"
        refused = await _suggest(client, value=past_bound)
    assert refused.status_code == 422, f"201 characters: expected 422, got {refused.status_code}: {refused.text[:300]}"
    assert past_bound not in refused.text, "a 422 never sends the request's input back (A-35)"
    print_success("200 characters: answered; 201: 422")


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [pytest.param({}, id="missing"), pytest.param({"value": ""}, id="empty")])
async def test_a_missing_or_empty_value_is_refused(test_server, params):  # red until E-19b1
    """CSA-API-04 — RED: without ``value``, or with an empty one, the endpoint answers 422.

    Red before E-19b1 because the route answers 404; the positive control (``value=EUR`` answers 200) makes the 422 about
    the value alone.
    """
    print_section(f"CSA-API-04: value {params or 'missing'}")
    async with httpx.AsyncClient() as client:
        _answer(await _suggest(client, value="EUR"), "EUR")
        refused = await _suggest(client, **params)
    assert refused.status_code == 422, f"{params or 'no value'}: expected 422, got {refused.status_code}: {refused.text[:300]}"
    print_success(f"{params or 'missing'} → 422")


# ============================================================
# Agreement with the functions, and the name the client calls
# ============================================================


@pytest.mark.asyncio
async def test_the_answer_is_what_the_three_functions_say(test_server):  # red until E-19b1
    """CSA-API-05 — RED: for every value of the table and a dozen more (padding, NBSP, a name, numeric codes, subunit
    codes, a test code, a lower-cased ambiguous name), the answer is ``is_canonical_iso_currency``,
    ``suggested_iso_currency`` and ``iso_currency_candidates`` of the value, the candidates as a list."""
    print_section("CSA-API-05: the answer and the functions")
    candidates = _candidates()
    values = [value for value, *_ in TABLE] + list(MORE_VALUES)
    wrong = {}
    async with httpx.AsyncClient() as client:
        for value in values:
            body = _answer(await _suggest(client, value=value), value)
            expected = {"canonical": is_canonical_iso_currency(value), "suggestion": suggested_iso_currency(value), "candidates": list(candidates(value))}
            if body != expected:
                wrong[value[:24]] = (body, expected)
    assert not wrong, f"answers that differ from the functions (answer, functions): {wrong}"
    print_info(f"  {len(values)} values")
    print_success("every answer is what the functions say")


@pytest.mark.asyncio
async def test_the_openapi_document_names_the_operation_the_client_calls(test_server):  # red until E-19b1
    """CSA-API-06 — RED: the OpenAPI document has ``GET /api/v1/utilities/currencies/suggest``, whose operationId is
    ``suggest_currency_api_v1_utilities_currencies_suggest_get`` (the generated client's method, which
    ``currencyStore.suggestCurrency`` calls), with ``value`` a required query parameter."""
    print_section("CSA-API-06: the operation in the OpenAPI document")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/openapi.json", timeout=TIMEOUT)
    assert response.status_code == 200, f"GET /api/v1/openapi.json: {response.status_code}"
    operation = response.json().get("paths", {}).get(SUGGEST_PATH, {}).get("get")
    if operation is None:
        pytest.fail(f"red until E-19b1: the OpenAPI document has no GET {SUGGEST_PATH}", pytrace=False)
    assert operation.get("operationId") == OPERATION_ID, f"the generated client calls {OPERATION_ID}: the document names {operation.get('operationId')!r}"
    parameters = {(parameter.get("name"), parameter.get("in")): parameter for parameter in operation.get("parameters", [])}
    assert ("value", "query") in parameters, f"value is a query parameter: {list(parameters)}"
    assert parameters[("value", "query")].get("required") is True, f"value is required: {parameters[('value', 'query')]}"
    print_success(f"{OPERATION_ID}, value required in the query")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
