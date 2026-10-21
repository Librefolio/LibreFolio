"""
H-61 checkpoint 2 · level L2 of the hosting panel (LibreFolio 1.3, workstream H, platform): the test vectors of the admin
documentation, checked by a test that reads them. The contract is H-61 CP2's, §6: «The vectors of the docs, checked by a
test that reads them».

Under test: the page ``mkdocs_src/docs/admin/hosting_providers.en.md``, the heading carrying the attribute
``{: #panel-api-test-vectors }``, and the first fenced block opened with ``json`` after it. A hosting provider that writes
its own panel (not the one LibreFolio ships) is given that block to check its signer against: a published test key, a
ticket, and what an instance answers to that ticket at several moments, in several scopes, for several public addresses.
A vector that is wrong is worse than none, so this file makes the page and the code answer to each other.

The block is one JSON object: ``private_key_seed_hex`` and ``public_key`` (the test key, published: never a real one),
``environment`` (``LIBREFOLIO_PANEL_PUBLIC_KEYS``, ``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS``, as
an operator writes them), ``header`` and ``payload`` (what the ticket holds), ``ticket`` (the compact JWS) and
``verdicts``, a list of ``{now, scope, verdict, public_url?}``: the instance's clock, the scope of the route asked, and
``accepted`` or a ``panel_ticket_*`` code; ``public_url``, when present, replaces ``LIBREFOLIO_PUBLIC_URL`` for that row.

The tests:

- HPV-001, the block is found: the anchor once in the page, a ``json`` block after it, parsed, with every key and the
  shape of each verdict row. The failure names the page and the anchor.
- HPV-002, the seed derives the public key, and the variable of ``environment`` is ``kid:public_key``, the ``kid`` of the
  header.
- HPV-003, the ticket is what it says: its first two segments are the ``header`` and the ``payload`` of the page, and
  signing that ``payload`` again with the seed's key gives the very same ticket.
- HPV-004, each verdict row, once, through the three readers of the configuration and ``verify_ticket``: ``accepted`` is a
  ``TicketClaims`` with the payload's ``jti``, ``iat`` and ``exp``, any other verdict is the ``TicketRefusal`` code.
- HPV-005, the vectors cover the contract: ``accepted`` and the four refusals a provider's signer can cause, and the four
  instants of the tolerance, one second on each side of each edge.

How. Pure: a file of the repository read from disk (its path found from this file's, never from the working directory),
no server, no database, no network, no clock — each row carries its own ``now``. The ticket is verified by the real
readers (``panel_public_keys``, ``panel_audience``, ``panel_clock_skew_seconds`` read the process environment at each
call) and the real ``verify_ticket``: no re-implementation of the contract in this file. The three variables of L2 are
deleted before each test, then set through ``monkeypatch`` from the page. The key is the page's test key: a real key
never appears here.

Read here beyond the contract's words, each in one place of this file, so that another choice changes one line:

- The rows are read when pytest collects this file, to parametrize HPV-004. A page that is missing, or whose block cannot
  be read, must not crash the collection of the whole suite: the parametrization then holds one placeholder row whose test
  fails with the reason, and HPV-001 fails with the same reason, naming the page and the anchor (``_rows``).
- The exact equality of HPV-003 rests on three facts, each stable by design and not by luck of an implementation: Ed25519
  signs deterministically (RFC 8032, no random nonce), PyJWT writes the header with its keys sorted and the payload in the
  order of the dict it is given, both in the most compact JSON. The vectors of a published page need exactly that: a
  provider reproduces the ticket byte for byte, and any other signature of the same claims would not be the vector. If a
  later PyJWT stops sorting the header, this test is the one to fail, and the page's ticket is regenerated, not the test
  loosened: a provider's library does not read this file.
- Each row names the scope the route asks for (``scope``): ``verify_ticket`` is given that string, as ``panel_access``
  gives it the value of a ``PanelScope``.

Red today: when the page has not got the block, HPV-001..005 fail on its reason, «the page … has no heading with the
attribute {: #panel-api-test-vectors }».
"""

import base64
import json
import re
from functools import cache
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend.app.config.hosting_panel import panel_audience, panel_clock_skew_seconds, panel_public_keys
from backend.app.services.platform.hosting_panel.tickets import TicketClaims, TicketRefusal, verify_ticket
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE PAGE, SPELLED OUT
# =============================================================================

#: The root of the repository: this file is ``backend/test_scripts/test_services/<name>.py``.
REPO_ROOT = Path(__file__).resolve().parents[3]
#: The page of the vectors, relative to the root, and the anchor of the heading they follow.
PAGE = "mkdocs_src/docs/admin/hosting_providers.en.md"
ANCHOR_ID = "panel-api-test-vectors"
ANCHOR = re.compile(r"\{:\s*#" + re.escape(ANCHOR_ID) + r"\s*\}")
#: What the page says of itself when the block is not there: the same words for every test that needs it.
WHERE = f"the page {PAGE}, the heading with the attribute {{: #{ANCHOR_ID} }}"

#: The variables of L2, as .env.example writes them: spelled out here, so that a rename shows.
KEYS_VARIABLE = "LIBREFOLIO_PANEL_PUBLIC_KEYS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
SKEW_VARIABLE = "LIBREFOLIO_PANEL_CLOCK_SKEW_SECONDS"
KEYFILE_VARIABLE = KEYS_VARIABLE + "_FILE"
#: What the page's ``environment`` holds, and every variable the readers could see: none comes from the runner.
PAGE_VARIABLES = (KEYS_VARIABLE, PUBLIC_URL_VARIABLE, SKEW_VARIABLE)
L2_VARIABLES = (*PAGE_VARIABLES, KEYFILE_VARIABLE)

#: The keys of the block, by what they must be.
TOP_KEYS = {
    "private_key_seed_hex": str,
    "public_key": str,
    "environment": dict,
    "header": dict,
    "payload": dict,
    "ticket": str,
    "verdicts": list,
}
#: The claims a ticket's payload carries, for the checks that read them.
PAYLOAD_CLAIMS = ("aud", "scope", "iat", "exp", "jti")

#: The verdicts the contract names: accepted, and the codes of §2.
ACCEPTED = "accepted"
EXPIRED = "panel_ticket_expired"
NOT_YET_VALID = "panel_ticket_not_yet_valid"
WRONG_SCOPE = "panel_ticket_wrong_scope"
WRONG_AUDIENCE = "panel_ticket_wrong_audience"
#: What the vectors must show at least: the verdict a provider's signer or clock can cause.
REQUIRED_VERDICTS = (ACCEPTED, EXPIRED, NOT_YET_VALID, WRONG_SCOPE, WRONG_AUDIENCE)
CODE_PREFIX = "panel_ticket_"

# =============================================================================
# READING THE BLOCK
# =============================================================================


def _json_block(text: str) -> str:
    """The content of the first fence opened with ``json`` after the anchor of the vectors; ValueError, with the reason,
    when the page does not hold it. The fence may be indented (inside a tab or an admonition): the indent is removed."""
    anchors = ANCHOR.findall(text)
    if len(anchors) != 1:
        raise ValueError(f"{WHERE}, found {len(anchors)} time(s) in the page, expected exactly once")
    lines = text[ANCHOR.search(text).end() :].splitlines()
    opening = next((index for index, line in enumerate(lines) if re.fullmatch(r"\s*```json\b.*", line)), None)
    if opening is None:
        raise ValueError(f"{WHERE} is not followed by a block opened with ```json")
    indent = re.match(r"\s*", lines[opening]).group()
    body: list[str] = []
    for line in lines[opening + 1 :]:
        if line.strip() == "```" and line.startswith(indent):
            return "\n".join(body)
        body.append(line[len(indent) :] if line.startswith(indent) else line)
    raise ValueError(f"{WHERE}: the ```json block that follows is never closed")


def _problem_with(data: Any) -> str | None:  # noqa: C901 — flat shape validator, one early return per field, no nested logic
    """What is wrong with the shape of the block, in one sentence, or None: every key of its type, the three variables in
    ``environment``, the claims in ``payload``, and each verdict a row of its own shape."""
    if not isinstance(data, dict):
        return f"the block is {type(data).__name__}, expected a JSON object"
    for name, kind in TOP_KEYS.items():
        if name not in data:
            return f"the block has no key {name!r}"
        if not isinstance(data[name], kind):
            return f"{name!r} is {type(data[name]).__name__}, expected {kind.__name__}"
    missing = [name for name in PAGE_VARIABLES if not isinstance(data["environment"].get(name), str)]
    if missing:
        return f"'environment' has no value (a string) for {', '.join(missing)}"
    if not re.fullmatch(r"\d+", data["environment"][SKEW_VARIABLE].strip()):
        return f"environment.{SKEW_VARIABLE} is not a whole number of seconds: {data['environment'][SKEW_VARIABLE]!r}"
    absent = [name for name in PAYLOAD_CLAIMS if name not in data["payload"]]
    if absent:
        return f"'payload' lacks the claims {absent}"
    for name in ("iat", "exp"):
        if not isinstance(data["payload"][name], int) or isinstance(data["payload"][name], bool):
            return f"payload.{name} is not an integer: {data['payload'][name]!r}"
    if not isinstance(data["header"].get("kid"), str) or not isinstance(data["header"].get("typ"), str):
        return "'header' has no string 'kid' and 'typ'"
    if not data["verdicts"]:
        return "'verdicts' is empty"
    for index, row in enumerate(data["verdicts"]):
        if not isinstance(row, dict):
            return f"verdicts[{index}] is {type(row).__name__}, expected an object"
        if not isinstance(row.get("now"), int) or isinstance(row.get("now"), bool):
            return f"verdicts[{index}].now is not an integer: {row.get('now')!r}"
        if not isinstance(row.get("scope"), str) or not row["scope"]:
            return f"verdicts[{index}].scope is not a scope name: {row.get('scope')!r}"
        verdict = row.get("verdict")
        if not isinstance(verdict, str) or not (verdict == ACCEPTED or verdict.startswith(CODE_PREFIX)):
            return f"verdicts[{index}].verdict is neither {ACCEPTED!r} nor a {CODE_PREFIX}* code: {verdict!r}"
        if "public_url" in row and not isinstance(row["public_url"], str):
            return f"verdicts[{index}].public_url is not a string: {row['public_url']!r}"
    return None


@cache
def _read() -> tuple[dict[str, Any] | None, str | None]:
    """The block of the page and ``None``, or ``None`` and why it could not be had: never an exception, so that collecting
    this file cannot crash on a page that has not got the vectors (yet, or any more)."""
    path = REPO_ROOT / PAGE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return None, f"{WHERE}: the page cannot be read ({path}): {error}"
    try:
        block = _json_block(text)
        data = json.loads(block)
    except ValueError as error:  # json.JSONDecodeError is one
        return None, f"{error}" if str(error).startswith("the page") else f"{WHERE}: the ```json block is not JSON: {error}"
    problem = _problem_with(data)
    return (None, f"{WHERE}: {problem}") if problem else (data, None)


def _rows() -> list[Any]:
    """The rows of the verdicts as parameters of HPV-004, each (index, row), its id the index and the verdict. A block that
    could not be read gives one placeholder, which fails with the reason: a parametrization over nothing is skipped, and
    a skipped test is a green nobody looks at."""
    data, _ = _read()
    if data is None:
        return [pytest.param(None, id="vectors-block-not-readable")]
    return [pytest.param((index, row), id=f"{index}-{row['verdict']}") for index, row in enumerate(data["verdicts"])]


@pytest.fixture(autouse=True)
def no_inherited_l2_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with none of the variables of L2: nothing comes from the runner's environment."""
    for name in L2_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def vectors() -> dict[str, Any]:
    """The block of the page, or the test fails naming the page, the anchor and what is wrong."""
    data, problem = _read()
    if data is None:
        pytest.fail(f"H-61 CP2 §6: {problem}")
    return data


def _b64url(data: bytes) -> str:
    """``data`` in base64url without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(text: str) -> bytes:
    """What ``text`` holds, base64url without padding."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _private_key(vectors: dict[str, Any]) -> Ed25519PrivateKey:
    """The private key of the page's seed: the test key, published, never a real one."""
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(vectors["private_key_seed_hex"]))


# =============================================================================
# HPV-001: the block is found
# =============================================================================


def test_the_page_holds_the_vectors_block() -> None:
    """HPV-001 (§6): the page has the heading with ``{: #panel-api-test-vectors }`` once, a block opened with ``json`` after
    it, which parses, has the seven keys (``private_key_seed_hex``, ``public_key``, ``environment`` with the three
    variables, ``header``, ``payload``, ``ticket``, ``verdicts``) and rows of ``now``, ``scope`` and ``verdict``. Fails
    when the heading or its anchor is renamed, moved to another page or doubled; when the block is no longer ``json``, no
    longer follows the heading or is not valid JSON; when a key is dropped or changes type."""
    print_section("H-61 CP2 §6: the vectors block of the admin page")
    data, problem = _read()

    assert data is not None, f"H-61 CP2 §6: {problem}"
    assert set(TOP_KEYS) <= set(data), f"every key of the block is there: {sorted(set(TOP_KEYS) - set(data))} missing"
    print_success(f"{WHERE}: {len(data['verdicts'])} verdict rows")


# =============================================================================
# HPV-002: the key
# =============================================================================


def test_the_seed_derives_the_public_key_and_the_variable(vectors: dict[str, Any]) -> None:
    """HPV-002 (§6): ``Ed25519PrivateKey.from_private_bytes(seed)``'s public key, raw (32 bytes) in base64url without
    padding, is ``public_key``; and ``environment.LIBREFOLIO_PANEL_PUBLIC_KEYS`` is ``<kid of the header>:<public_key>``,
    which is what an operator pastes. Fails when the seed or the public key is edited alone, when the variable names
    another key or another ``kid`` than the ticket's, or when the entry stops being ``kid:key``."""
    derived = _b64url(_private_key(vectors).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))

    assert derived == vectors["public_key"], f"the seed's public key is {derived!r}, the page says {vectors['public_key']!r}"
    expected = f"{vectors['header']['kid']}:{vectors['public_key']}"
    assert vectors["environment"][KEYS_VARIABLE] == expected, f"{KEYS_VARIABLE} is kid:public_key, {expected!r}"


# =============================================================================
# HPV-003: the ticket
# =============================================================================


def test_the_ticket_is_the_header_and_the_payload_signed_by_the_seed(vectors: dict[str, Any]) -> None:
    """HPV-003 (§6): the ticket is three base64url segments; the first two decode to JSON equal to ``header`` and
    ``payload``; and signing ``payload`` with the seed's key by PyJWT (``EdDSA``, the ``typ`` and ``kid`` of the header)
    gives that ticket byte for byte: Ed25519 is deterministic, PyJWT sorts the header's keys and keeps the payload's order
    (module docstring). Fails when the ticket is edited without its header or payload (or the reverse), when the
    signature is not the seed's, when the payload's keys are reordered, or when PyJWT stops writing what a provider's
    library writes."""
    segments = vectors["ticket"].split(".")

    assert len(segments) == 3 and all(re.fullmatch(r"[A-Za-z0-9_-]+", segment) for segment in segments), f"a compact JWS, three base64url segments: {segments!r}"
    assert json.loads(_unb64url(segments[0])) == vectors["header"], "the ticket's first segment is the page's header"
    assert json.loads(_unb64url(segments[1])) == vectors["payload"], "the ticket's second segment is the page's payload"
    header = vectors["header"]
    resigned = jwt.encode(vectors["payload"], _private_key(vectors), algorithm="EdDSA", headers={"typ": header["typ"], "kid": header["kid"]})
    assert resigned == vectors["ticket"], "the payload signed again with the seed's key is the ticket, byte for byte"


# =============================================================================
# HPV-004: each verdict
# =============================================================================


@pytest.mark.parametrize("case", _rows())
def test_each_verdict_is_what_the_instance_answers(monkeypatch: pytest.MonkeyPatch, vectors: dict[str, Any], case: tuple[int, dict[str, Any]] | None) -> None:
    """HPV-004 (§6): for each row of ``verdicts``, with the variables of ``environment`` set (the row's ``public_url``
    replacing ``LIBREFOLIO_PUBLIC_URL``), ``panel_public_keys()``, ``panel_audience()`` and ``panel_clock_skew_seconds()``
    read as the instance reads them, and ``verify_ticket(ticket, scope, keys, audience, skew, now)``: ``accepted`` is a
    ``TicketClaims`` with the payload's ``jti``, ``iat`` and ``exp`` (and its ``kid`` and ``scope``); any other verdict is
    a ``TicketRefusal`` whose code is that verdict. Fails when the page's verdict, clock, scope or address is edited
    without the code, when the code's order of checks, tolerance, audience or scope rule changes without the page, or when
    a reader of the configuration stops giving what the page's variables mean."""
    if case is None:
        pytest.fail("H-61 CP2 §6: the vectors block is not readable (see HPV-001)")
    index, row = case
    for name in PAGE_VARIABLES:
        monkeypatch.setenv(name, vectors["environment"][name])
    if "public_url" in row:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, row["public_url"])
    payload = vectors["payload"]

    result = verify_ticket(
        vectors["ticket"],
        scope=row["scope"],
        keys=panel_public_keys(),
        audience=panel_audience(),
        skew=panel_clock_skew_seconds(),
        now=row["now"],
    )

    where = f"row {index}: now {row['now']}, scope {row['scope']!r}" + (f", public URL {row['public_url']!r}" if "public_url" in row else "")
    if row["verdict"] == ACCEPTED:
        assert isinstance(result, TicketClaims), f"{where}: the page says accepted, the code answers {result!r}"
        assert (result.jti, result.iat, result.exp) == (payload["jti"], payload["iat"], payload["exp"]), f"{where}: the claims are the payload's: {result!r}"
        assert (result.kid, result.scope) == (vectors["header"]["kid"], payload["scope"]), f"{where}: the kid and the scope are the ticket's: {result!r}"
    else:
        assert isinstance(result, TicketRefusal), f"{where}: the page says {row['verdict']}, the code accepts: {result!r}"
        assert result.code == row["verdict"], f"{where}: the page says {row['verdict']}, the code refuses with {result.code!r}"
    print_success(f"{where}: {row['verdict']}")


# =============================================================================
# HPV-005: the vectors cover the contract
# =============================================================================


def test_the_vectors_cover_the_contract(vectors: dict[str, Any]) -> None:
    """HPV-005 (§6): the verdicts include ``accepted``, ``panel_ticket_expired``, ``panel_ticket_not_yet_valid``,
    ``panel_ticket_wrong_scope`` and ``panel_ticket_wrong_audience``; and, for the payload's scope and the environment's
    public URL, both edges of the tolerance, ``skew`` being the environment's: ``iat - skew`` accepted and ``iat - skew - 1``
    not yet valid, ``exp + skew - 1`` accepted and ``exp + skew`` expired. The wrong-scope rows ask another scope than the
    payload's and the wrong-audience rows another address, so that each refusal is the one it names. Fails when a row is
    dropped, when an edge is moved off its second (an edge row that is not exactly at the tolerance proves nothing), or
    when a refusal row is edited into one that fails for another reason."""
    rows, payload = vectors["verdicts"], vectors["payload"]
    skew = int(vectors["environment"][SKEW_VARIABLE])
    public_url = vectors["environment"][PUBLIC_URL_VARIABLE]
    # A row that changes nothing but the clock: the payload's scope, the environment's public URL.
    plain = {(row["now"], row["verdict"]) for row in rows if row["scope"] == payload["scope"] and row.get("public_url", public_url) == public_url}

    missing = [name for name in REQUIRED_VERDICTS if name not in {row["verdict"] for row in rows}]
    assert missing == [], f"the vectors show every verdict a provider can cause: {missing} missing"
    edges = {
        "iat - skew, accepted": (payload["iat"] - skew, ACCEPTED),
        "iat - skew - 1, not yet valid": (payload["iat"] - skew - 1, NOT_YET_VALID),
        "exp + skew - 1, accepted": (payload["exp"] + skew - 1, ACCEPTED),
        "exp + skew, expired": (payload["exp"] + skew, EXPIRED),
    }
    absent = [label for label, edge in edges.items() if edge not in plain]
    assert absent == [], f"both edges of the tolerance (skew {skew} s), one row per instant, changing only the clock: {absent} missing"
    other_scope = [row for row in rows if row["verdict"] == WRONG_SCOPE and row["scope"] == payload["scope"]]
    assert other_scope == [], f"a wrong-scope row asks another scope than the payload's, {payload['scope']!r}: {other_scope}"
    same_address = [row for row in rows if row["verdict"] == WRONG_AUDIENCE and row.get("public_url", public_url) == public_url]
    assert same_address == [], f"a wrong-audience row gives another public URL than the environment's, {public_url!r}: {same_address}"
