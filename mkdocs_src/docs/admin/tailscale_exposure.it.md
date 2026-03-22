# 🌐 Esporre LibreFolio tramite Tailscale (In Corso)

> 🚧 **In Corso**: Questa guida è prevista per una prossima release.

Questo documento spiegherà come esporre in modo sicuro la tua istanza self-hosted di LibreFolio a Internet utilizzando **Tailscale Funnel** o un **Tailscale Docker Sidecar**.

## 💡 Concetto

Invece di aprire porte sul router (che è rischioso), useremo Tailscale per creare un tunnel sicuro e cifrato.

### 📋 Argomenti previsti

- 🐳 Configurare un container Tailscale in `docker-compose.yml`.
- 🌐 Configurare Tailscale Funnel per l'accesso HTTPS pubblico.
- 🔒 Utilizzare la VPN Tailscale solo per accessi privati e autenticati.
