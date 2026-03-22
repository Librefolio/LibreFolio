# 🌐 Exposer LibreFolio via Tailscale (Travail en cours)

> 🚧 **Travail en cours** : Ce guide est prévu pour une version ultérieure.

Ce document expliquera comment rendre accessible de manière sécurisée votre instance auto-hébergée de LibreFolio sur Internet en utilisant le **Tailscale Funnel** ou un **Tailscale Docker Sidecar**.

## 💡 Concept

Au lieu d'ouvrir des ports sur votre routeur (ce qui est risqué), nous utiliserons Tailscale pour créer un tunnel chiffré.

### 📋 Sujets prévus

- 🐳 Configuration d'un conteneur Tailscale dans `docker-compose.yml`.
- 🌐 Configuration de Tailscale Funnel pour un accès HTTPS public.
- 🔒 Utilisation du VPN Tailscale pour un accès privé et authentifié uniquement.
