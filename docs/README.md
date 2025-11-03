# LibreFolio Documentation

Welcome to LibreFolio documentation!

## 📚 Available Guides

### Getting Started
- [Main README](../README.md) - Project overview and quick start

### Architecture
- **[Async Architecture Guide](async-architecture.md)** - ⭐ Understanding LibreFolio's high-performance concurrent request handling

### Database
- **[Database Schema Documentation](database-schema.md)** - Complete guide to all tables and relationships
- **[Alembic Migrations Guide](alembic-guide.md)** - Simple guide to database migrations

### Development
- 🚀 **[API Development Guide](api-development-guide.md)** - ⭐ Complete guide for adding new REST API endpoints (bulk-first pattern, Pydantic, FastAPI)

### Features
- **[FX System Overview](fx-implementation.md)** - Foreign exchange rates system introduction
  - **[FX Architecture](fx/architecture.md)** - Technical design and data flow
  - **[FX API Reference](fx/api-reference.md)** - REST API endpoints for FX operations
  - **[FX Providers](fx/providers.md)** - ECB, FED, BOE, SNB details
  - **[FX Provider Development](fx/provider-development.md)** - ⭐ How to add new providers

### Testing
- **[Testing Guide for New Developers](testing-guide.md)** - ⭐ Hands-on introduction to the test suite (start here!)
- **[Testing Environment](testing-environment.md)** - Test vs production database isolation

### Configuration
- **[Environment Variables](environment-variables.md)** - Configuration options and Docker deployment

## 🎯 Quick Links

todo: add more links when more docs are added

## 📝 Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [environment-variables.md](environment-variables.md) | Configuration & deployment | Developers, DevOps |
| [testing-guide.md](testing-guide.md) | ⭐ Learn the system via testing (new devs start here!) | New Developers |
| [testing-environment.md](testing-environment.md) | Test vs production database isolation | Developers |
| [api-development-guide.md](api-development-guide.md) | 🚀 ⭐ Complete guide to add REST API endpoints | Contributors |
| [alembic-guide.md](alembic-guide.md) | Learn database migrations | Everyone |
| [database-schema.md](database-schema.md) | Database tables & relationships | Everyone |
| [async-architecture.md](async-architecture.md) | ⭐ Async/concurrent architecture explained | Contributors |
| [fx-implementation.md](fx-implementation.md) | FX rates system overview | Everyone |
| [fx/architecture.md](fx/architecture.md) | FX system technical architecture | Developers |
| [fx/api-reference.md](fx/api-reference.md) | FX REST API endpoints | Developers, Frontend |
| [fx/providers.md](fx/providers.md) | Available FX providers details | Developers |
| [fx/provider-development.md](fx/provider-development.md) | ⭐ How to add FX providers | Contributors |
| [README.md](../README.md) | Project overview | Everyone |


**...understand the async architecture and performance**
→ Read [Async Architecture Guide](async-architecture.md) - How concurrent requests are handled

**...add new REST API endpoints**
→ Read [API Development Guide](api-development-guide.md) - Step-by-step guide with examples (bulk-first, Pydantic, FastAPI)

**...contribute to the backend (add endpoints, services)**
→ Read [API Development Guide](api-development-guide.md) first, then [Async Architecture Guide](async-architecture.md)

### I want to...
**...learn the system (I'm a new developer)**
→ Read [Testing Guide](testing-guide.md) - Hands-on introduction via tests

**...understand the database structure**
→ Read [Database Schema Documentation](database-schema.md)

**...understand database migrations**
→ Read [Alembic Guide](alembic-guide.md)

**...understand how FX rates work**
**...develop a new FX data provider (central bank integration)**
→ Read [FX Provider Development Guide](fx/provider-development.md) - Quick start template

→ Read [FX Implementation](fx-implementation.md)

**...configure the application or deploy to Docker**
→ Read [Environment Variables](environment-variables.md)

---

**Need help?**? Join our community or check the [Main README](../README.md)!
