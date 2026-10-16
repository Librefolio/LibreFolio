"""
Off-loading for BRIM file parsing.

## Why this module exists

``brim_provider.parse_file`` reads a CSV or a PDF and turns it into transactions. It is
plain synchronous code, and it was being called straight from an ``async def`` endpoint.
Two consequences, both invisible until several files are imported at once:

1. the event loop was blocked for the whole parse, so *every other request* — prices, FX,
   the UI itself — waited behind it;
2. firing the parses in parallel from the browser changed nothing, because the server
   could only ever run one at a time. The progress bar promised a concurrency that did
   not exist.

Off-loading to a **thread** fixes (1) and (2) for I/O, but a parse is largely CPU work and
the GIL would still serialise it. So the parse runs in a **process pool**: separate
interpreters, real cores.

## Sizing and safety

- Workers: ``min(cpu_count, MAX_WORKERS)``. More would be pointless — the number of parses
  in flight is bounded by the browser's own concurrency, which is smaller still.
- The pool is created **lazily**, on the first parse: an import should never fork.
- With the warm-up on (``LIBREFOLIO_BRIM_PREWARM``, ``config/brim.py``: off by default, on in test mode; W-B53), its
  ``forkserver`` starts at application startup (``prewarm``), **preloaded** with the BRIM module and every plugin
  (``brim_parse_preload``): every worker is forked from it with them already imported and discovered, instead of a
  fresh interpreter importing them at the first parse after a start (~4 s idle, 31-49 s under load), and the workers
  share the preloaded pages. With it off nothing is preloaded (W-B59): the first parse starts the forkserver, and each
  worker imports the BRIM module itself at its first parse. A preload on that lazy path stalls the event loop for the
  whole import: on Python 3.13 the first ``run_in_executor`` waits, on the loop's thread, for the new worker's pid,
  which a preloading forkserver sends only once the preload is done.
- Start method: ``forkserver`` when the platform has it, otherwise ``spawn``. Never plain
  ``fork`` — this process runs a thread pool and an event loop, and forking that is how
  you get deadlocks that only appear in production.
- **Any** failure to build or use the pool falls back to a thread. A degraded parse is a
  slow parse; a failed parse is a lost import. The fallback is permanent for the process
  lifetime, so a broken environment does not pay the cost of retrying at every file.

The submitted callable and its arguments must be picklable: ``parse_file`` is a
module-level function taking three scalars and returning a Pydantic model, which is why it
is submitted directly rather than through a closure.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import multiprocessing.forkserver
import os
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Optional

import structlog

from backend.app.config.brim import BrimConfigError, brim_prewarm_enabled
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.services.brim import brim_provider

logger = structlog.get_logger(__name__)

# Beyond this, extra workers only cost memory: the browser will not have more parses in
# flight, and each worker pays a full interpreter + plugin-registry import.
MAX_WORKERS = 4

_pool: Optional[ProcessPoolExecutor] = None
_pool_disabled = False
# Imported once by the forkserver, so that every worker is born with the BRIM module and its plugins (W-B53). Named,
# not imported: importing it discovers every plugin, which this module must not do at import. The preload list and
# the forkserver are one per process: this is the only forkserver user (tools, quant and the market calendar spawn).
_PRELOAD = ["backend.app.services.brim.brim_parse_preload"]


def _worker_count() -> int:
    return max(1, min(os.cpu_count() or 1, MAX_WORKERS))


def _prewarm_enabled() -> bool:
    """``brim_prewarm_enabled()``, an invalid value counting as off: the startup step has already logged it."""
    try:
        return brim_prewarm_enabled()
    except BrimConfigError:
        return False


def _get_pool() -> Optional[ProcessPoolExecutor]:
    """Build the pool on first use, once; return ``None`` when it is unavailable."""
    global _pool, _pool_disabled
    if _pool_disabled:
        return None
    if _pool is not None:
        return _pool
    try:
        methods = multiprocessing.get_all_start_methods()
        method = "forkserver" if "forkserver" in methods else "spawn"
        ctx = multiprocessing.get_context(method)
        if method == "forkserver" and _prewarm_enabled():
            # Only with the warm-up on (W-B59: on the lazy path the first parse would hold the event loop for the whole
            # preload), and only taken into account if the forkserver is not running yet (``prewarm`` already set it).
            ctx.set_forkserver_preload(_PRELOAD)
        _pool = ProcessPoolExecutor(max_workers=_worker_count(), mp_context=ctx)
        logger.info("BRIM parse pool started", workers=_worker_count(), start_method=method)
        return _pool
    except Exception as exc:  # pragma: no cover - environment dependent
        _pool_disabled = True
        logger.warning("BRIM parse pool unavailable, falling back to threads", error=str(exc))
        return None


def prewarm() -> None:
    """Start the pool's ``forkserver`` now, with the BRIM module preloaded (W-B53): application startup, in a thread.

    The forkserver imports the module in its own process; this call returns at once, and the first parse forks a
    worker that already has it instead of starting a fresh interpreter. The pool itself stays lazy. Never raises:
    whatever fails is logged, and the first parse starts everything as before. Nothing to do where only ``spawn``
    exists, or when the pool has been given up.
    """
    if _pool_disabled or "forkserver" not in multiprocessing.get_all_start_methods():
        return
    try:
        multiprocessing.get_context("forkserver").set_forkserver_preload(_PRELOAD)
        multiprocessing.forkserver.ensure_running()
        logger.info("BRIM parse pool forkserver started", preload=_PRELOAD)
    except Exception as exc:  # noqa: BLE001 - startup goes on; the first parse starts the pool as before
        logger.warning("BRIM parse pool prewarm failed; the first parse will start the pool", error=str(exc))


async def parse_file_offloaded(file_id: str, plugin_code: str, broker_id: int) -> BRIMParseOutput:
    """
    Parse a file without blocking the event loop, on a real core when possible.

    Falls back to a worker thread if the process pool cannot be built or dies mid-flight
    (a segfaulting C parser takes its worker with it, and that must not take the import
    down too).
    """
    pool = _get_pool()
    if pool is not None:
        loop = asyncio.get_running_loop()
        try:
            future = loop.run_in_executor(pool, brim_provider.parse_file, file_id, plugin_code, broker_id)
        except Exception as exc:  # pragma: no cover - environment dependent
            # Submitting is our own machinery: a failure here is never the parser's.
            _disable_pool(exc)
        else:
            try:
                return await future
            except BrokenProcessPool as exc:
                # The worker died. Anything else the parse raises is the parser speaking —
                # re-raised untouched, because turning "unsupported layout" into a silent
                # retry would hide the only useful message the user gets.
                _disable_pool(exc)
    return await asyncio.to_thread(brim_provider.parse_file, file_id, plugin_code, broker_id)


def _disable_pool(exc: BaseException) -> None:
    """Give up on the pool for the rest of the process lifetime.

    Permanent on purpose: an environment that cannot run workers will not start being able
    to halfway through an import, and retrying at every file would pay the startup cost
    again for nothing.
    """
    global _pool, _pool_disabled
    logger.warning("BRIM parse pool unusable, falling back to threads", error=str(exc))
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
    _pool = None
    _pool_disabled = True


def shutdown_pool(wait: bool = False) -> None:
    """Release the workers (application shutdown, tests).

    ``wait=False`` by default: application shutdown must not block behind a
    parse that is still running, and an orderly interpreter exit finishes the
    job anyway — ``concurrent.futures`` registers an ``atexit`` handler that
    joins the pool.

    Pass ``wait=True`` when the caller is about to leave through ``os._exit``,
    which skips that handler. Without the join the forkserver control process
    and its workers survive, are re-parented to init, and keep the *inherited*
    stdout open — a run piped into ``tee`` then never sees EOF and hangs.
    ``cancel_futures=True`` means the wait covers only parses already running.
    """
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=wait, cancel_futures=True)
        _pool = None
