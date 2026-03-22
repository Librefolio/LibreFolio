# 🌐 Exponer LibreFolio a través de Tailscale (WIP)

> 🚧 **Trabajo en Progreso**: Esta guía está planeada para un lanzamiento futuro.

Este documento explicará cómo exponer de forma segura tu instancia autohospedada de LibreFolio a través de internet utilizando **Tailscale Funnel** o un **Tailscale Docker Sidecar**.

## 💡 Concepto

En lugar de abrir puertos en tu router (lo cual es arriesgado), usaremos Tailscale para crear un túnel seguro y cifrado.

### 📋 Temas Previstos

- 🐳 Configurar un contenedor con Tailscale en `docker-compose.yml`.
- 🌐 Configurar Tailscale Funnel para acceso público HTTPS.
- 🔒 Usar la VPN de Tailscale solo para acceso privado y autenticado.
