"""Private, normally importable fixtures for the real Tool worker and supervisor.

Importing this module publishes one immutable test registry, but starts no worker.
Construct ``SpawnHarness`` before replacing the executor module's multiprocessing
binding with it. The harness does not patch anything itself. Its blocking handle
methods belong in ``asyncio.to_thread`` when used by an asynchronous test.

The control pipe is separate from Tool parameters, responses and cancellation.
``start`` opens only the test's cold-start gate: the production ready/ACK handshake
still decides whether construction and computation may begin.

Assert production cleanup before calling ``SpawnHarness.cleanup()``. That method
is emergency teardown, never evidence that the production supervisor succeeded.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Self, cast

import psutil
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.tools import ToolDocumentation, ToolOperationPolicy, ToolUIDescriptor
from backend.app.services.provider_registry import register_plugin
from backend.app.services.tools.base import ToolExecutionContext, ToolPlugin
from backend.app.services.tools.registry import ToolPluginRegistry
from backend.app.services.tools.wire import decode_json, encode_json
from backend.app.services.tools.worker import PipeCancellation, ToolWorkerJob

_SETUP_TIMEOUT = 30.0
_CLEANUP_TIMEOUT = 5.0
_CHILD_CONTROL: Connection | None = None
_CHILD_EXECUTION_ID: str | None = None

type Frame = dict[str, Any]
type Role = Literal["root", "child", "grandchild"]


@dataclass(frozen=True, slots=True)
class OwnedIdentity:
    """A fixture-owned native identity, independent of production tree helpers."""

    pid: int
    created_at: float
    role: Role

    def current(self) -> psutil.Process | None:
        """Return the same living process, excluding exited or reused PIDs."""
        try:
            process = psutil.Process(self.pid)
            if process.create_time() != self.created_at or not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                return None
            return process
        except psutil.NoSuchProcess:
            return None

    def as_frame(self) -> Frame:
        return {"pid": self.pid, "created_at": self.created_at, "role": self.role}


def _current_identity(role: Role) -> OwnedIdentity:
    process = psutil.Process()
    return OwnedIdentity(process.pid, process.create_time(), role)


def _started_identity(process: BaseProcess, role: Role) -> OwnedIdentity | None:
    """Capture ownership even when a child has not reached its Python entrypoint."""
    try:
        pid = process.pid
    except ValueError:
        return None  # The production owner may already have closed the handle.
    if pid is None:
        return None
    try:
        return OwnedIdentity(pid, psutil.Process(pid).create_time(), role)
    except psutil.NoSuchProcess:
        return None


def _identity_from_frame(value: object) -> OwnedIdentity:
    if not isinstance(value, dict):
        raise AssertionError(f"Expected a fixture process identity, received {value!r}")
    pid, created_at, role = value.get("pid"), value.get("created_at"), value.get("role")
    if type(pid) is not int or pid <= 0 or type(created_at) is not float or role not in ("root", "child", "grandchild"):
        raise AssertionError(f"Invalid fixture process identity: {value!r}")
    return OwnedIdentity(pid, created_at, cast(Role, role))


def _signal_owned(owned: tuple[OwnedIdentity, ...], *, force: bool, timeout: float, problems: list[str]) -> None:
    waiting: list[psutil.Process] = []
    for identity in reversed(owned):
        try:
            if identity.pid == os.getpid():
                raise AssertionError("Fixture cleanup must never signal its own process")
            process = identity.current()
            if process is None:
                continue
            # psutil also checks PID reuse inside its native signal methods.
            process.kill() if force else process.terminate()
            waiting.append(process)
        except psutil.NoSuchProcess:
            continue
        except (psutil.Error, OSError, AssertionError) as exc:
            problems.append(f"{identity.role} {identity.pid}: {exc}")
    if waiting:
        try:
            psutil.wait_procs(waiting, timeout=timeout)
        except psutil.Error as exc:
            problems.append(f"Native process wait: {exc}")


def _close_process_handles(processes: Iterable[BaseProcess], problems: list[str]) -> None:
    for process in processes:
        if process is None:
            continue
        try:
            pid = process.pid
            if pid is not None:
                process.join(timeout=0.1)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=0.2)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=_CLEANUP_TIMEOUT)
                if process.is_alive():
                    problems.append(f"Owned multiprocessing handle {pid} is still alive")
                    continue
            process.close()
        except ValueError:
            continue  # An already-closed production Process is a normal outcome.
        except (OSError, AssertionError) as exc:
            problems.append(f"Joining an owned multiprocessing handle: {exc}")


def _check_owned_survivors(owned: tuple[OwnedIdentity, ...], problems: list[str]) -> None:
    for identity in owned:
        try:
            if identity.current() is not None:
                problems.append(f"Surviving owned {identity.role}: pid={identity.pid}, created_at={identity.created_at}")
        except psutil.Error as exc:
            problems.append(f"Checking owned {identity.role} {identity.pid}: {exc}")


def _cleanup_owned(identities: Iterable[OwnedIdentity], processes: Iterable[BaseProcess] = ()) -> None:
    """Last-resort cleanup, using only captured PID/birth pairs and native waits."""
    owned = tuple(dict.fromkeys(identities))
    problems: list[str] = []
    _signal_owned(owned, force=False, timeout=0.2, problems=problems)
    _signal_owned(owned, force=True, timeout=_CLEANUP_TIMEOUT, problems=problems)
    _close_process_handles(processes, problems)
    _check_owned_survivors(owned, problems)
    if problems:
        raise AssertionError("Fixture emergency cleanup failed: " + "; ".join(problems))


def _receive_before(connection: Connection, deadline: float, description: str) -> object:
    remaining = max(0.0, deadline - time.monotonic())
    try:
        if not connection.poll(remaining):
            raise AssertionError(f"Fixture setup deadline while waiting for {description}")
        return connection.recv()
    except (EOFError, OSError) as exc:
        raise AssertionError(f"Fixture setup pipe closed while waiting for {description}") from exc


def _expect_command(connection: Connection, command: str, deadline: float, description: str) -> None:
    received = _receive_before(connection, deadline, description)
    if received != command:
        raise AssertionError(f"Expected fixture command {command!r} for {description}, received {received!r}")


def _setup_frame(connection: Connection, kind: str, deadline: float) -> Frame:
    frame = _receive_before(connection, deadline, f"descendant frame {kind!r}")
    if not isinstance(frame, dict) or frame.get("kind") != kind:
        raise AssertionError(f"Expected descendant frame {kind!r}, received {frame!r}")
    return frame


def _report(kind: str, execution_id: str, **details: Any) -> None:
    if _CHILD_CONTROL is not None:
        _CHILD_CONTROL.send({"kind": kind, "execution_id": execution_id, **_current_identity("root").as_frame(), **details})


class FixtureInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    operation: Literal["exercise"]
    scenario: Literal[
        "echo",
        "hold",
        "crash",
        "oversize",
        "unicode",
        "invalid_output",
        "not_model",
        "descendants",
        "partial_frame",
    ]
    text: str = "private"
    size: int = Field(default=2_048, strict=True, le=1_000_000)
    ignore_term: bool = False


class FixtureOutput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: Literal["ready"]
    text: str
    pid: int
    execution_id: str

    @model_validator(mode="after")
    def reject_private_output(self) -> Self:
        if self.text == "PRIVATE_OUTPUT_REJECTED":
            raise ValueError("PRIVATE_OUTPUT_REJECTED")
        return self


class FixtureRegistry(ToolPluginRegistry):
    """An isolated, static registry that cannot discover production plugins."""

    @classmethod
    def _get_plugin_directory(cls) -> Path:
        # Never create this directory: discovery must not scan the helper folder.
        return Path(__file__).with_name("_tools_executor_fixture_plugins_unused")

    @classmethod
    def _get_module_namespace(cls) -> str:
        return f"{__package__}._tools_executor_fixture_plugins_unused"


class _PrivateFixtureFailure(RuntimeError):
    """An intentionally private computation failure for sanitization assertions."""


def _wait_for_release(text: str) -> None:
    if _CHILD_CONTROL is None:
        raise _PrivateFixtureFailure("This fixture scenario requires the private control wrapper")
    try:
        command = _CHILD_CONTROL.recv()
    except (EOFError, OSError) as exc:
        raise _PrivateFixtureFailure("Private fixture control pipe closed") from exc
    if command == "release":
        return
    if command == "fail":
        raise _PrivateFixtureFailure(f"PRIVATE_COMPUTE_FAILURE: {text}")
    if command == "crash":
        os._exit(23)
    raise _PrivateFixtureFailure(f"Unexpected private fixture command: {command!r}")


@register_plugin(FixtureRegistry)
class FixturePlugin(ToolPlugin[FixtureInput, FixtureOutput]):
    tool_code = "private_executor_fixture"
    contract_version = "1.0.0"
    implementation_version = "1.0.0"
    name = "Private executor fixture"
    description = "Test-only typed computations and independently controlled process lifecycles."
    category = "testing"
    icon_key = "code"
    ui = ToolUIDescriptor(kind="custom", component_key="private-executor-fixture", ui_contract_version=1)
    documentation = ToolDocumentation(path="user/tools/private-executor-fixture/", version="1.0.0")
    operations = (
        ToolOperationPolicy(
            operation="exercise",
            deterministic=False,
            max_parameter_bytes=1_048_576,
            max_result_bytes=1_048_576,
            queue_timeout_ms=120_000,
            soft_timeout_ms=119_000,
            job_timeout_ms=120_000,
        ),
    )
    input_type = FixtureInput
    output_type = FixtureOutput

    def __init__(self) -> None:
        if _CHILD_EXECUTION_ID is not None:
            _report("constructed", _CHILD_EXECUTION_ID)

    def compute(self, parameters: FixtureInput, context: ToolExecutionContext) -> FixtureOutput:
        if parameters.ignore_term:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        _report("compute", context.execution_id)
        if parameters.scenario == "crash":
            os._exit(23)
        if parameters.scenario == "descendants":
            if _CHILD_CONTROL is None:
                raise _PrivateFixtureFailure("Descendants require the private control wrapper")
            _spawn_descendants(context, parameters.ignore_term)
        if parameters.scenario in ("hold", "descendants"):
            _wait_for_release(parameters.text)

        # These two probes must start from a valid, genuinely constructed model.
        text = "private" if parameters.scenario in ("unicode", "invalid_output") else parameters.text
        if parameters.scenario == "oversize":
            text = "x" * parameters.size
        result = FixtureOutput(status="ready", text=text, pid=os.getpid(), execution_id=context.execution_id)
        if parameters.scenario == "unicode":
            result.text = "\ud800"
        elif parameters.scenario == "invalid_output":
            # Assignment is intentionally unvalidated. The real worker must reject
            # the serialized model in output_adapter.validate_json, not compute.
            result.text = "PRIVATE_OUTPUT_REJECTED"
        elif parameters.scenario == "not_model":
            # The cast changes no runtime value: this intentionally violates compute.
            return cast(FixtureOutput, result.model_dump())
        return result


# Use the real decorator, schema generation and publication once in every normal
# parent/child import. Never mutate this registry or its definitions in a test.
FixtureRegistry.get_snapshot()


def _worker_job(args: tuple[object, ...]) -> ToolWorkerJob:
    if not args:
        raise AssertionError("SpawnHarness requires ToolWorkerJob as the first target argument")
    job, *_ = args
    if not isinstance(job, ToolWorkerJob):
        raise AssertionError(f"SpawnHarness expected ToolWorkerJob, received {type(job).__name__}")
    return job


def _stall_after_partial_frame(job: ToolWorkerJob, response: Connection, cancellation: PipeCancellation) -> None:
    """Adopt a real session, then leave half a multiprocessing frame header."""
    os.setsid()
    response.send_bytes(
        encode_json(
            {
                "kind": "ready",
                "execution_id": job.execution_id,
                "pid": os.getpid(),
                "pgid": os.getpgrp(),
                "created_at": psutil.Process().create_time(),
            }
        )
    )
    if not cancellation.await_start(job.hard_deadline):
        return
    if os.write(response.fileno(), b"\x00\x00") != 2:
        raise AssertionError("Fixture could not publish its partial frame header")
    _report("partial-frame", job.execution_id)
    # No clock guess: production cleanup must terminate this owned process.
    threading.Event().wait()


def controlled_worker_entry(target: Callable[..., object], args: tuple[object, ...], control_connection: Connection) -> None:
    """Gate a real worker entrypoint without bypassing its production handshake."""
    global _CHILD_CONTROL, _CHILD_EXECUTION_ID
    try:
        job = _worker_job(args)
        _CHILD_CONTROL = control_connection
        _CHILD_EXECUTION_ID = job.execution_id
        _report("boot", job.execution_id)
        _expect_command(control_connection, "start", time.monotonic() + _SETUP_TIMEOUT, f"worker {job.execution_id} start gate")
        parameters = decode_json(job.parameters)
        if isinstance(parameters, dict) and parameters.get("scenario") == "partial_frame":
            response, cancellation = args[1:3]
            if not isinstance(response, Connection) or not isinstance(cancellation, PipeCancellation):
                raise AssertionError("Partial-frame fixture received unexpected worker arguments")
            _stall_after_partial_frame(job, response, cancellation)
        else:
            target(*args)
    finally:
        _CHILD_CONTROL = None
        _CHILD_EXECUTION_ID = None
        control_connection.close()


def _park_descendant(connection: Connection, identity: OwnedIdentity) -> None:
    # Both endpoints stay local. Losing an ancestor must NOT release this wait:
    # that would let a broken supervisor pass a process-tree cleanup assertion.
    receiver, keeper = multiprocessing.get_context("spawn").Pipe(duplex=False)
    try:
        connection.send({"kind": "parked", "member": identity.as_frame()})
        connection.close()
        receiver.recv()
        raise AssertionError("The private descendant parking pipe unexpectedly received data")
    finally:
        receiver.close()
        keeper.close()


def _create_grandchild(connection: Connection, ignore_term: bool, session_id: int, deadline: float) -> tuple[BaseProcess, Connection, Connection, OwnedIdentity]:
    context = multiprocessing.get_context("spawn")
    grand_connection, grand_endpoint = context.Pipe(duplex=True)
    grandchild = context.Process(target=_descendant_entry, args=("grandchild", grand_endpoint, ignore_term, session_id, deadline), daemon=False)
    birth: OwnedIdentity | None = None
    try:
        try:
            grandchild.start()
        finally:
            grand_endpoint.close()
        birth = _started_identity(grandchild, "grandchild")
        if birth is None:
            raise AssertionError("Fixture grandchild exited before its birth could be recorded")
        connection.send({"kind": "member", "member": birth.as_frame()})
        born = _setup_frame(grand_connection, "born", deadline)
        if _identity_from_frame(born.get("member")) != birth:
            raise AssertionError("Fixture grandchild changed identity during setup")
        return grandchild, grand_connection, grand_endpoint, birth
    except BaseException:
        _cleanup_owned((birth,) if birth is not None else (), (grandchild,))
        grand_connection.close()
        grand_endpoint.close()
        raise


def _prepare_descendant_tree(connection: Connection, ignore_term: bool, session_id: int, deadline: float) -> tuple[BaseProcess, Connection, Connection, OwnedIdentity]:
    _expect_command(connection, "spawn", deadline, "permission to create the grandchild")
    grandchild, grand_connection, grand_endpoint, birth = _create_grandchild(connection, ignore_term, session_id, deadline)
    try:
        connection.send({"kind": "ready"})
        _expect_command(connection, "park", deadline, "permission to park the descendant tree")
        grand_connection.send("park")
        parked = _setup_frame(grand_connection, "parked", deadline)
        if _identity_from_frame(parked.get("member")) != birth:
            raise AssertionError("Unexpected grandchild parked acknowledgement")
        return grandchild, grand_connection, grand_endpoint, birth
    except BaseException:
        _cleanup_owned((birth,), (grandchild,))
        grand_connection.close()
        grand_endpoint.close()
        raise


def _descendant_entry(role: Literal["child", "grandchild"], connection: Connection, ignore_term: bool, session_id: int, deadline: float) -> None:
    """Spawn only owned descendants; park only after the root records their births."""
    grandchild: BaseProcess | None = None
    grand_connection: Connection | None = None
    grand_endpoint: Connection | None = None
    owned: list[OwnedIdentity] = []
    try:
        if ignore_term:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if os.getsid(0) != session_id:
            raise AssertionError("Fixture descendant did not inherit the worker session")
        identity = _current_identity(role)
        connection.send({"kind": "born", "member": identity.as_frame()})
        if role == "child":
            grandchild, grand_connection, grand_endpoint, birth = _prepare_descendant_tree(connection, ignore_term, session_id, deadline)
            owned.append(birth)
        else:
            _expect_command(connection, "park", deadline, "permission to park the grandchild")
        _park_descendant(connection, identity)
    except BaseException:
        _cleanup_owned(owned, (grandchild,) if grandchild is not None else ())
        raise
    finally:
        connection.close()
        if grand_connection is not None:
            grand_connection.close()
        if grand_endpoint is not None:
            grand_endpoint.close()


def _spawn_descendants(context: ToolExecutionContext, ignore_term: bool) -> None:
    """Publish a complete, live tree; successful setup leaves cleanup to production."""
    deadline = min(context.hard_deadline, time.monotonic() + _SETUP_TIMEOUT)
    native = multiprocessing.get_context("spawn")
    connection, child_endpoint = native.Pipe(duplex=True)
    child: BaseProcess | None = None
    owned: list[OwnedIdentity] = []
    try:
        child = native.Process(target=_descendant_entry, args=("child", child_endpoint, ignore_term, os.getsid(0), deadline), daemon=False)
        try:
            child.start()
        finally:
            child_endpoint.close()
            birth = _started_identity(child, "child")
            if birth is not None:
                owned.append(birth)
        if birth is None:
            raise AssertionError("Fixture child exited before its birth could be recorded")
        _report("member", context.execution_id, member=birth.as_frame())
        born = _setup_frame(connection, "born", deadline)
        if _identity_from_frame(born.get("member")) != birth:
            raise AssertionError("Fixture child changed identity during setup")
        connection.send("spawn")
        member = _identity_from_frame(_setup_frame(connection, "member", deadline).get("member"))
        if member.role != "grandchild":
            raise AssertionError("Fixture child reported an unexpected descendant role")
        owned.append(member)
        # Publish ownership BEFORE permitting an indefinite park. Emergency parent
        # teardown can recover these frames even if cancellation interrupts setup.
        _report("member", context.execution_id, member=member.as_frame())
        _setup_frame(connection, "ready", deadline)
        connection.send("park")
        parked = _setup_frame(connection, "parked", deadline)
        if _identity_from_frame(parked.get("member")) != birth:
            raise AssertionError("Unexpected child parked acknowledgement")
        _report("tree", context.execution_id, members=[_current_identity("root").as_frame(), *(identity.as_frame() for identity in owned)])
    except BaseException:
        _cleanup_owned(owned, (child,) if child is not None else ())
        raise
    finally:
        connection.close()
        child_endpoint.close()


class SpawnHandle:
    """One job's private control endpoint and retained native ownership evidence.

    ``receive`` consumes one matching frame; unmatched frames remain available to
    later calls. ``frames`` retains every received frame, including consumed ones.
    All properties remain readable after production closes the Process, except
    the delegated Process methods themselves, which preserve native semantics.
    """

    def __init__(self, execution_id: str, process: _ProcessProxy, requested_daemon: bool | None, connection: Connection) -> None:
        self.execution_id = execution_id
        self.process = process
        self.requested_daemon = requested_daemon
        self._connection = connection
        self._lock = threading.RLock()
        self._receive_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._frames: list[Frame] = []
        self._pending: list[Frame] = []
        self._identities: dict[Role, OwnedIdentity] = {}
        self._end_reason: str | None = None

    @property
    def frames(self) -> tuple[Frame, ...]:
        with self._lock:
            return tuple(self._frames)

    @property
    def owned_identities(self) -> tuple[OwnedIdentity, ...]:
        with self._lock:
            return tuple(self._identities.values())

    def _remember(self, identity: OwnedIdentity) -> None:
        with self._lock:
            previous = self._identities.get(identity.role)
            if previous is not None and previous != identity:
                raise AssertionError(f"Execution {self.execution_id} changed its {identity.role} identity: {previous!r} -> {identity!r}")
            if any(known.pid == identity.pid and known != identity for known in self._identities.values()):
                raise AssertionError(f"Execution {self.execution_id} reused an owned PID in its control frames")
            self._identities[identity.role] = identity

    def _record_started(self, process: BaseProcess) -> None:
        identity = _started_identity(process, "root")
        if identity is not None:
            self._remember(identity)

    def _record_frame(self, frame: object) -> None:
        if not isinstance(frame, dict) or not isinstance(frame.get("kind"), str) or frame.get("execution_id") != self.execution_id:
            raise AssertionError(f"Invalid control frame for execution {self.execution_id}: {frame!r}")
        with self._lock:
            self._frames.append(frame)
            self._pending.append(frame)
            root = _identity_from_frame(frame)
            if root.role != "root":
                raise AssertionError(f"Non-root sender on execution {self.execution_id}'s control pipe")
            self._remember(root)
            if frame["kind"] == "member":
                self._remember(_identity_from_frame(frame.get("member")))
            if frame["kind"] == "tree":
                members = frame.get("members")
                if not isinstance(members, list):
                    raise AssertionError(f"Execution {self.execution_id} reported a tree without members")
                identities = tuple(_identity_from_frame(member) for member in members)
                if len(identities) != 3 or {identity.role for identity in identities} != {"root", "child", "grandchild"}:
                    raise AssertionError(f"Execution {self.execution_id} did not report its complete three-process tree")
                for identity in identities:
                    self._remember(identity)

    def _read_one(self, timeout: float) -> bool:
        if self._end_reason is not None:
            return False
        try:
            if not self._connection.poll(timeout):
                return False
            frame = self._connection.recv()
        except EOFError:
            self._end_reason = "EOF"
            return False
        except (OSError, ValueError) as exc:
            self._end_reason = f"closed pipe ({type(exc).__name__})"
            return False
        self._record_frame(frame)
        return True

    def receive(self, kind: str, timeout: float = 30) -> Frame:
        """Wait for one frame kind, retaining unmatched frames and every identity."""
        deadline = time.monotonic() + timeout
        with self._receive_lock:
            while True:
                with self._lock:
                    for index, frame in enumerate(self._pending):
                        if frame["kind"] == kind:
                            return self._pending.pop(index)
                if self._end_reason is not None:
                    raise AssertionError(f"Control {self._end_reason} for execution {self.execution_id} while waiting for {kind!r}; received kinds: {[frame['kind'] for frame in self.frames]}")
                remaining = max(0.0, deadline - time.monotonic())
                if not self._read_one(remaining) and self._end_reason is None:
                    raise AssertionError(f"Control deadline after {timeout}s for execution {self.execution_id} while waiting for {kind!r}; received kinds: {[frame['kind'] for frame in self.frames]}")

    def send(self, command: str) -> None:
        if not isinstance(command, str):
            raise TypeError("A private fixture command must be a string")
        with self._send_lock:
            try:
                self._connection.send(command)
            except (EOFError, OSError, ValueError) as exc:
                raise AssertionError(f"Cannot send {command!r} to execution {self.execution_id}: control pipe closed") from exc

    def drain(self) -> tuple[Frame, ...]:
        """Read currently available frames; not an absence barrier for a live job."""
        with self._receive_lock:
            while self._read_one(0.0):
                pass
        return self.frames


class _ProcessProxy:
    """Delegate native Process behavior, adding only private endpoint ownership."""

    def __init__(self, owner: SpawnHarness, process: BaseProcess, child_control: Connection) -> None:
        self._owner = owner
        self._process = process
        self._child_control = child_control
        self._handle: SpawnHandle | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._process, name)

    def start(self) -> None:
        # Serialize only harness bookkeeping, never production worker lifetimes.
        with self._owner._condition:
            if self._owner._closed:
                raise RuntimeError("Cannot start a process after SpawnHarness cleanup")
            if self._handle is None:
                raise AssertionError("SpawnHarness did not attach a control handle")
            try:
                self._process.start()
            finally:
                self._child_control.close()
                self._handle._record_started(self._process)

    def close(self) -> None:
        self._process.close()
        self._child_control.close()


class SpawnHarness:
    """A test-owned spawn context proxy; construction captures the real context."""

    def __init__(self) -> None:
        self._context = multiprocessing.get_context("spawn")
        self._condition = threading.Condition()
        self._queue: deque[SpawnHandle] = deque()
        self._handles: dict[str, SpawnHandle] = {}
        self._connections: list[Connection] = []
        self._closed = False

    @property
    def handles(self) -> Mapping[str, SpawnHandle]:
        """Snapshot of handles keyed by the real ToolWorkerJob.execution_id."""
        with self._condition:
            return MappingProxyType(dict(self._handles))

    def get_context(self, method: str) -> Self:
        if method != "spawn":
            raise AssertionError(f"SpawnHarness requires 'spawn', received {method!r}")
        return self

    def Pipe(self, duplex: bool = True) -> tuple[Connection, Connection]:
        with self._condition:
            if self._closed:
                raise RuntimeError("Cannot allocate a pipe after SpawnHarness cleanup")
            endpoints = self._context.Pipe(duplex=duplex)
            self._connections.extend(endpoints)
            return endpoints

    def Process(self, *, target: Callable[..., object], args: tuple[object, ...], **kwargs: Any) -> _ProcessProxy:
        job = _worker_job(args)
        with self._condition:
            if self._closed:
                raise RuntimeError("Cannot allocate a process after SpawnHarness cleanup")
            if job.execution_id in self._handles:
                raise AssertionError(f"Duplicate fixture execution_id: {job.execution_id}")
            parent_control, child_control = self._context.Pipe(duplex=True)
            self._connections.extend((parent_control, child_control))
            try:
                native = self._context.Process(target=controlled_worker_entry, args=(target, args, child_control), **kwargs)
                process = _ProcessProxy(self, native, child_control)
                handle = SpawnHandle(job.execution_id, process, kwargs.get("daemon"), parent_control)
                process._handle = handle
                self._handles[job.execution_id] = handle
                self._queue.append(handle)
                self._condition.notify_all()
                return process
            except BaseException:
                parent_control.close()
                child_control.close()
                raise

    def next_handle(self, timeout: float = 30) -> SpawnHandle:
        """Wait on a condition-backed queue, not on process-start timing guesses."""
        deadline = time.monotonic() + timeout
        with self._condition:
            while not self._queue:
                if self._closed:
                    raise AssertionError("SpawnHarness closed while waiting for the next handle")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError(f"No spawned Tool handle within {timeout}s; recorded execution_ids: {tuple(self._handles)}")
                self._condition.wait(timeout=remaining)
            return self._queue.popleft()

    def cleanup(self) -> None:
        """Close pipes and reap only recorded identities after product assertions."""
        with self._condition:
            self._closed = True
            self._condition.notify_all()
            handles = tuple(self._handles.values())
            connections = tuple(self._connections)
        problems: list[str] = []
        for handle in handles:
            try:
                handle.drain()
            except Exception as exc:
                problems.append(f"Draining execution {handle.execution_id}: {exc}")
        for connection in connections:
            try:
                connection.close()
            except OSError as exc:
                problems.append(f"Closing a fixture-owned pipe: {exc}")
        try:
            _cleanup_owned(
                (identity for handle in handles for identity in handle.owned_identities),
                (handle.process for handle in handles),
            )
        except Exception as exc:
            problems.append(str(exc))
        if problems:
            raise AssertionError("SpawnHarness teardown failed: " + "; ".join(problems))
