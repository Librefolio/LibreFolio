# 📱 Installer comme application (PWA)

LibreFolio peut être installé comme **Progressive Web App (PWA)** sur votre téléphone, tablette ou ordinateur :
il s'ouvre comme une application native, depuis sa propre icône, sans passer par un magasin d'applications.

---

## ✅ Ce que vous obtenez

- 🖥️ **Plein écran** — ni barre d'adresse, ni barre d'outils du navigateur.
- 🏠 **Icône sur l'écran d'accueil** — lancez LibreFolio comme n'importe quelle autre application.
- 👆 **Aucun geste accidentel** — le retour par balayage et le zoom par double appui sont désactivés.
- 🔐 **Rester connecté** entre les lancements, jusqu'à l'expiration de votre session.

!!! note "En ligne uniquement"

    L'application a besoin d'une connexion à votre serveur LibreFolio : il n'existe pas de mode hors ligne —
    vos données résident sur votre serveur. Si vous ouvrez l'application alors que le serveur est
    injoignable, une page **Serveur injoignable** s'affiche et réessaie automatiquement.

---

## 📲 Comment installer

### 🤖 Android (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge.
2. Ouvrez le menu **Aide et support** (❓, en haut à droite) et appuyez sur **Installer l'application**.
3. Confirmez avec **Installer** : LibreFolio apparaît sur votre écran d'accueil.

Pas de boîte de dialogue d'installation ? Utilisez le menu **⋮** du navigateur → **Installer l'application** ou **Ajouter à l'écran d'accueil**.

### 🍎 iOS (Safari)

1. Ouvrez LibreFolio dans **Safari**.
2. Appuyez sur le bouton **Partager** (carré avec une flèche).
3. Faites défiler vers le bas, appuyez sur **Sur l'écran d'accueil**, puis sur **Ajouter**.

iOS n'a pas de boîte de dialogue d'installation : sur un iPhone ou un iPad, **Installer l'application** dans le menu Aide et support affiche
ces instructions à la place.

### 💻 Ordinateur (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge.
2. Cliquez sur **Installer l'application** dans le menu **Aide et support**, ou sur l'icône d'installation (⊕) dans la barre d'adresse.
3. LibreFolio s'ouvre dans sa propre fenêtre.

---

## 🌐 HTTP vs HTTPS

| Adresse | Installation comme application | Boîte de dialogue d'installation depuis **Installer l'application** |
|---|---|---|
| `https://…` (Tailscale, proxy inverse) | ✅ | ✅ |
| `http://localhost` | ✅ | ✅ |
| `http://192.168.x.x` (LAN) | ❌ HTTPS requis | ❌ une simple indication |

!!! warning "Exigence de connexion HTTPS pour la PWA"

    Les navigateurs n'installent une application qu'à partir d'une adresse **HTTPS** sécurisée — `localhost` et `127.0.0.1` sont
    les seules exceptions. En HTTP simple sur votre réseau (par exemple `http://192.168.1.100:6040`),
    LibreFolio fonctionne toujours dans le navigateur, mais ne peut pas être installé.

    N'importe quelle configuration HTTPS fera l'affaire. L'option la plus simple et gratuite est notre
    **[Guide d'exposition de services Tailscale](../admin/service_exposure.md)** : une adresse HTTPS sécurisée sans
    certificats SSL à gérer ni ports de routeur à ouvrir.

---

## 🔧 Dépannage

| Problème | Solution |
|---------|----------|
| **Installer l'application** n'est pas dans le menu | Vous êtes déjà dans l'application installée : l'élément y est masqué |
| **Installer l'application** affiche une indication au lieu d'installer | Le navigateur n'a pas proposé d'installation : vérifiez que vous utilisez HTTPS (ou `localhost`), ou que l'application n'est pas déjà installée, puis suivez l'indication |
| iOS : l'option **Sur l'écran d'accueil** est absente | Ouvrez la page dans **Safari** et cherchez dans son menu **Partager** |
| L'application ne se met pas à jour | Fermez et rouvrez l'application — elle charge toujours la dernière version depuis votre serveur |
| Déconnecté après une mise à jour | Reconnectez-vous — un redémarrage du serveur peut mettre fin à toutes les sessions |

---

## 🔗 Voir aussi

- 🌐 **[Guide d'exposition de services Tailscale](../admin/service_exposure.md)** — Une adresse HTTPS gratuite pour votre instance
- 🛠️ **[Optimisations PWA et mobiles](../developer/frontend/pwa.md)** — Comment le côté application est construit (pour les développeurs)
