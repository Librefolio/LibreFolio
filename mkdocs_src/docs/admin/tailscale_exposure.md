# Exposing LibreFolio via Tailscale (WIP)

> 🚧 **Work In Progress**: This guide is planned for a future release.

This document will explain how to securely expose your self-hosted LibreFolio instance to the internet using **Tailscale Funnel** or a **Tailscale Docker Sidecar**.

## Concept

Instead of opening ports on your router (which is risky), we will use Tailscale to create a secure, encrypted tunnel.

### Planned Topics

- Setting up a Tailscale container in `docker-compose.yml`.
- Configuring Tailscale Funnel for public HTTPS access.
- Using Tailscale VPN for private, authenticated access only.
