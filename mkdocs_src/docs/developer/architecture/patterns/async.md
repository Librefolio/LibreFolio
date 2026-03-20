# ⚡ Asynchronous Architecture

LibreFolio is built from the ground up using an asynchronous architecture to ensure high performance and efficiency, especially when dealing with I/O-bound operations like database
queries and external API calls.

## Why Async?

A traditional synchronous web server handles one request at a time per worker process. If a request involves waiting for a database query or an external API call, the entire worker
process is blocked, unable to handle other requests.

An **asynchronous** server, on the other hand, can handle multiple requests concurrently within a single process. When a task needs to wait for I/O, the server can switch to
another task instead of blocking. This leads to:

- **Higher Throughput**: The server can handle many more concurrent connections with fewer resources.
- **Better Responsiveness**: The application remains responsive even when performing long-running I/O operations.
- **Efficient Resource Usage**: Less time is spent waiting, and more time is spent doing actual work.

## Implementation in LibreFolio

### FastAPI

**FastAPI** is an asynchronous web framework by default. All API endpoint functions in LibreFolio are defined with `async def`, allowing them to be run concurrently by the ASGI
server (Uvicorn).

```python
@router.get("/assets", response_model=List[AssetRead])
async def get_assets(session: AsyncSession = Depends(get_session)):
    # This is an async function
    assets = await AssetCRUDService.get_all(session)
    return assets
```

### SQLAlchemy with `asyncio`

All database interactions are performed using SQLAlchemy's `asyncio` extension.

- **`AsyncSession`**: Instead of a regular `Session`, the application uses an `AsyncSession` which provides an awaitable interface for all database operations.
- **`asyncpg` / `aiosqlite`**: Asynchronous database drivers are used to communicate with the database in a non-blocking way.

```python
# Example of an async database query
async def get_all(session: AsyncSession) -> List[Asset]:
    result = await session.execute(select(Asset))
    return result.scalars().all()
```

### Asynchronous Providers

The provider system for Assets, FX, and BRIM is designed to be asynchronous. Provider methods like `get_current_value` or `fetch_rates` are defined as `async def`, allowing them to
perform non-blocking HTTP requests to external APIs.

```python
# Example of an async provider method
class YahooFinanceProvider(AssetSourceProvider):
    async def get_current_value(self, identifier: str, ...) -> FACurrentValue:
        # Uses an async HTTP client (e.g., httpx)
        async with httpx.AsyncClient() as client:
            response = await client.get(...)
        # ...
```

This allows the system to fetch data from multiple providers in parallel using `asyncio.gather`, significantly speeding up data refresh operations.
