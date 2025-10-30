# Environment Variables

LibreFolio can be configured through environment variables. This is particularly useful for Docker deployments and production environments.

---

## 📋 Available Variables

### **Database**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | SQLite database file path | `sqlite:///./backend/data/sqlite/app.db` | No |

**Example:**
```bash
export DATABASE_URL="sqlite:///./data/portfolio.db"
```

---

### **Server**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Main server port (production/development) | `8000` | No |
| `TEST_PORT` | Test server port (used during automated tests) | `8001` | No |

**Example:**
```bash
export PORT="3000"          # Main server on port 3000
export TEST_PORT="3001"     # Test server on port 3001
```

**Notes:**
- The test server runs on a separate port to avoid conflicts with development
- When running tests, the test server automatically starts on `TEST_PORT`
- Production/development server uses `PORT`

---

### **Application**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | No |

**Example:**
```bash
export LOG_LEVEL="WARNING"
```

---

### **Testing**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TEST_DATABASE_URL` | SQLite URL for test database | `sqlite:///./backend/data/sqlite/test_app.db` | No |

**Example:**
```bash
export TEST_DATABASE_URL="sqlite:///./backend/data/sqlite/my_test.db"
```

**Notes:**
- Test database is in the same directory as production database
- Production: `sqlite:///./backend/data/sqlite/app.db`
- Test: `sqlite:///./backend/data/sqlite/test_app.db` (default)
- Tests never touch the production database
- Full SQLite URL format allows flexibility

---

### **Portfolio Settings**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORTFOLIO_BASE_CURRENCY` | Base currency for portfolio calculations (ISO 4217 code) | `EUR` | No |

**Example:**
```bash
export PORTFOLIO_BASE_CURRENCY="USD"
```

**Supported currencies:**
- The system supports all currencies available through the ECB (European Central Bank) API
- Use the API endpoint `GET /api/v1/fx/currencies` to retrieve the current list
- Common currencies: EUR, USD, GBP, CHF, JPY, CAD, AUD, etc.

---

## 📚 Related Documentation

- [Database Schema](./database-schema.md)
- [Alembic Migrations Guide](./alembic-guide.md)
- [Main README](../README.md)

