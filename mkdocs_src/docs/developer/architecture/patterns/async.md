# ⚡ Asynchronous Architecture

LibreFolio is built from the ground up using an asynchronous architecture to ensure high performance and efficiency, especially when dealing with I/O-bound operations like database
queries and external API calls.

## 🤔 Why Async?

A traditional synchronous web server handles one request at a time per worker process. If a request involves waiting for a database query or an external API call, the entire worker
process is blocked, unable to handle other requests.

An **asynchronous** server, on the other hand, can handle multiple requests concurrently within a single process. When a task needs to wait for I/O, the server can switch to
another task instead of blocking. This leads to:

- **Higher Throughput**: The server can handle many more concurrent connections with fewer resources.
- **Better Responsiveness**: The application remains responsive even when performing long-running I/O operations.
- **Efficient Resource Usage**: Less time is spent waiting, and more time is spent doing actual work.

## 🔧 Implementation in LibreFolio

### 🚀 FastAPI

**FastAPI** is an asynchronous web framework by default. All API endpoint functions in LibreFolio are defined with `async def`, allowing them to be run concurrently by the ASGI
server (Uvicorn).

```python
@router.get("/assets", response_model=List[AssetRead])
async def get_assets(session: AsyncSession = Depends(get_session)):
    # This is an async function
    assets = await AssetCRUDService.get_all(session)
    return assets
```

### 🗃️ SQLAlchemy with `asyncio`

All database interactions are performed using SQLAlchemy's `asyncio` extension.

- **`AsyncSession`**: Instead of a regular `Session`, the application uses an `AsyncSession` which provides an awaitable interface for all database operations.
- **`asyncpg` / `aiosqlite`**: Asynchronous database drivers are used to communicate with the database in a non-blocking way.

```python
# Example of an async database query
async def get_all(session: AsyncSession) -> List[Asset]:
    result = await session.execute(select(Asset))
    return result.scalars().all()
```

### 🌐 Asynchronous Provider Contracts

Asset provider methods such as `get_current_value()`, `get_history_value()`,
`fetch_asset_metadata()`, `search()`, and `resolve_url()` have asynchronous contracts. The
service layer can therefore fan out work with `asyncio.gather()` and limit provider concurrency
with semaphores.

The contract does **not** require every third-party SDK to be async-native. For example,
`YahooFinanceProvider` calls the synchronous `yfinance` API directly inside its `async def`
methods. This is safe because the caller moves the entire provider coroutine away from the main
event loop before it starts.

### 🧵 Canonical Provider Thread Boundary

The single provider isolation helper is
`backend/app/services/asset_sources/core.py::_run_provider_in_thread()`. Manager operation
modules and `AssetSearchService` route provider I/O through it. For every call, the helper:

1. starts a worker with `asyncio.to_thread()`;
2. creates a new event loop inside that worker thread;
3. runs the provider coroutine to completion on that loop;
4. closes the loop and applies the caller's timeout with `asyncio.wait_for()`.

The implementation is equivalent to this shortened excerpt:

```python
async def _run_provider_in_thread(coro_factory, *, timeout=60.0):
    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_factory())
        finally:
            loop.close()

    return await asyncio.wait_for(
        asyncio.to_thread(_sync_runner),
        timeout=timeout,
    )
```

Provider implementations must therefore leave synchronous I/O direct:

```python
class YahooFinanceProvider(AssetSourceProvider):
    async def get_current_value(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        provider_params: dict | None,
    ) -> FACurrentValue:
        info = yf.Ticker(identifier).info  # Direct sync call in the provider thread
        ...
```

Do not add `asyncio.to_thread()` or `run_in_executor()` inside an asset provider. A nested
offload is redundant and makes timeout and exception behavior harder to reason about. Async-native
provider clients remain valid; they simply run on the worker thread's event loop.

!!! warning "Event Loop Blocking Rule"

    Outside the asset-provider boundary, never call synchronous I/O (HTTP requests, file reads,
    `time.sleep()`) directly inside an `async def` endpoint or service method. Use an
    async-native library or an explicit service-level offload.

    Symptoms of event loop blocking:

    - Other API calls hang until the blocking call completes
    - E2E tests time out intermittently
    - Health checks fail during provider sync operations
