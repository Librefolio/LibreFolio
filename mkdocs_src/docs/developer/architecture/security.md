# Security

This document outlines the security model, boundaries, and reporting procedures for LibreFolio.

## Threat Model and Scope

LibreFolio is a **self-hosted** application. The primary security assumption is that the **host system is secure**.

### In Scope

The following are considered within the scope of LibreFolio's security concerns:

-   **API Exploitation**: Any attempt to gain unauthorized access, escalate privileges, or perform unauthorized actions by exploiting vulnerabilities in the FastAPI backend.
-   **Data Segregation**: Ensuring that one user cannot access another user's data.
-   **Authentication Bypass**: Any method that allows access to protected endpoints without a valid JWT.
-   **Cross-Site Scripting (XSS)**: Vulnerabilities in the frontend that could allow an attacker to execute malicious scripts in a user's browser.

### Out of Scope

The following are considered out of scope:

-   **Host System Compromise**: If an attacker gains shell access to the server where LibreFolio is running, it is assumed that all data is compromised. The application does not and cannot protect against an attacker with direct access to the filesystem or database file.
-   **Physical Security**: The physical security of the server is the user's responsibility.
-   **Network Security (Internal)**: It is assumed that the local network is trusted. LibreFolio should be exposed to the internet only via a secure reverse proxy with HTTPS.

## Security Boundary

The security boundary of the application is the **HTTPS connection** to the server. All communication between the client and the server must be encrypted.

-   **Frontend <-> Backend**: All API calls are made over HTTPS.
-   **Backend <-> Database**: The connection to the SQLite database is a local file operation and is considered within the secure boundary of the host system.

## Key Security Measures

-   **Authentication**: Uses JWT with a strong, secret key (`SECRET_KEY` in `.env`). Passwords are never stored in plaintext; they are hashed using `passlib`.
-   **Dependencies**: The project uses `pipenv` and `npm` to manage dependencies, with lockfiles (`Pipfile.lock`, `package-lock.json`) to ensure reproducible and verifiable builds.
-   **Data Validation**: Pydantic is used for strict data validation at the API boundary, preventing many common injection-style attacks.
-   **CORS**: Cross-Origin Resource Sharing (CORS) is configured to only allow requests from the frontend's domain.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by opening a **GitHub Issue** on the project repository.

Please provide a detailed description of the vulnerability, including:
-   The steps to reproduce it.
-   The potential impact.
-   Any suggested mitigation.

We take security seriously and will prioritize addressing any valid vulnerability reports.
