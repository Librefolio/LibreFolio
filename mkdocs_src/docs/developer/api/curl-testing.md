# 🧪 API Testing with cURL

This guide explains how to test LibreFolio's REST API using cURL from the terminal.

## 🔐 Authentication

LibreFolio uses session-based authentication with HTTP-only cookies. To make authenticated API calls, you must first login and then pass the session cookie.

### 1️⃣ Step 1: Login and Get Session Cookie

```bash
# Login and save the session cookie
curl -v -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}' \
  -c /tmp/cookies.txt
```

This will:

1. Send login credentials
2. Receive a `Set-Cookie` header with the session token
3. Save the cookie to `/tmp/cookies.txt`

**Example response:**

```json
{
  "user": {
    "id": 1,
    "username": "alfy",
    "email": "user@example.com",
    "is_active": true,
    "is_superuser": true
  },
  "message": "Login successful"
}
```

### 2️⃣ Step 2: Make Authenticated Requests

Use the `-b` flag to send the saved cookie:

```bash
# Get current user info
curl -s -b /tmp/cookies.txt http://localhost:8000/api/v1/auth/me

# List brokers
curl -s -b /tmp/cookies.txt http://localhost:8000/api/v1/brokers

# List uploaded files
curl -s -b /tmp/cookies.txt http://localhost:8000/api/v1/uploads
```

### 🔑 Alternative: Direct Cookie Header

If `-b` doesn't work, you can extract the cookie from the login response and use it directly:

```bash
# From the login response, copy the session value from Set-Cookie header
# Example: session=PL4H9KVBq2...

# Use it directly
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Cookie: session=YOUR_SESSION_TOKEN_HERE"
```

## 📋 Common API Endpoints

### 🏥 Health Check (No Auth Required)

```bash
curl http://localhost:8000/api/v1/system/health
# Returns: {"status":"ok"}
```

### 👤 User Management

```bash
# Get current user
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/auth/me

# Update preferences
curl -X PATCH -b /tmp/cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"language":"it","currency":"EUR"}' \
  http://localhost:8000/api/v1/auth/users/me/preferences
```

### 🏦 Brokers

```bash
# List all brokers
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/brokers

# Get broker by ID
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/brokers/1

# Get broker summary (with balances)
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/brokers/1/summary
```

### 📥 BRIM (Broker Report Import)

```bash
# List BRIM files
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/brokers/import/files

# Filter by status
curl -b /tmp/cookies.txt "http://localhost:8000/api/v1/brokers/import/files?status=uploaded"

# Filter by broker IDs
curl -b /tmp/cookies.txt "http://localhost:8000/api/v1/brokers/import/files?broker_ids=1&broker_ids=2"

# Upload a file (requires broker_id)
curl -b /tmp/cookies.txt \
  -F "file=@/path/to/report.csv" \
  "http://localhost:8000/api/v1/brokers/import/upload?broker_id=1"

# Get available plugins
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/brokers/import/plugins
```

### 📁 Static Files

```bash
# List uploaded files
curl -b /tmp/cookies.txt http://localhost:8000/api/v1/uploads

# Upload a file
curl -b /tmp/cookies.txt \
  -F "file=@/path/to/image.png" \
  http://localhost:8000/api/v1/uploads

# Download a file
curl -b /tmp/cookies.txt -O \
  "http://localhost:8000/api/v1/uploads/file/FILE_ID?download=true"
```

## 🧰 Useful cURL Flags

| Flag                  | Description                            |
|-----------------------|----------------------------------------|
| `-s`                  | Silent mode (no progress bar)          |
| `-v`                  | Verbose (show headers)                 |
| `-i`                  | Include response headers               |
| `-X METHOD`           | HTTP method (GET, POST, PATCH, DELETE) |
| `-H "Header: value"`  | Add request header                     |
| `-d 'data'`           | Send request body                      |
| `-F "file=@path"`     | Send multipart form (file upload)      |
| `-b file`             | Send cookies from file                 |
| `-c file`             | Save cookies to file                   |
| `-o file`             | Save response to file                  |
| `-O`                  | Save with original filename            |
| `-w "\n%{http_code}"` | Print HTTP status code                 |

## 🧪 Test Mode

To test against the test database (port 8001):

```bash
# Start server in test mode
./dev.py server --test

# Use port 8001 for all requests
curl http://localhost:8001/api/v1/system/health
```

## 📖 API Documentation

For complete API documentation, visit:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json
