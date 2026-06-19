# 📱 Installer en tant qu'application (PWA)

LibreFolio peut être installé en tant qu'**Application Web Progressive (PWA)** sur votre appareil. Cela vous offre une expérience similaire à celle d'une application : mode plein écran, absence de barre d'adresse du navigateur et une icône sur l'écran d'accueil — sans avoir à passer par un magasin d'applications.

---

## ✅ Ce que vous obtenez

| Fonctionnalité | Description |
|---------|-------------|
| **Mode plein écran** | Pas de barre d'adresse ni d'encombrement lié à l'interface du navigateur |
| **Icône d'écran d'accueil** | Lancez LibreFolio comme une application native |
| **Pas d'interférence avec les gestes** | Balayage arrière et zoom par double tapotement désactivés |
| **Session persistante** | Reste connecté entre les lancements |

!!! note "Online Only"

    La PWA LibreFolio nécessite une connexion réseau active. Il n'y a pas de mode hors ligne — vos données résident sur votre serveur.

---

## 📲 Comment installer

### Android (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Recherchez le bouton **"Installer l'application"** dans le menu **Aide et Assistance** (icône ❓ en haut à droite)
3. Appuyez sur **Installer** lorsque vous y êtes invité
4. LibreFolio apparaît sur votre écran d'accueil

!!! tip "Alternative method"

    Si le bouton d'installation n'apparaît pas, appuyez sur le **menu ⋮ du navigateur → "Ajouter à l'écran d'accueil"** ou **"Installer l'application"**.

### iOS (Safari)

1. Ouvrez LibreFolio dans **Safari** (requis — les autres navigateurs ne supportent pas les PWA sur iOS)
2. Appuyez sur le bouton **Partager** (carré avec une flèche)
3. Faites défiler vers le bas et appuyez sur **"Ajouter à l'écran d'accueil"**
4. Appuyez sur **Ajouter**

!!! warning "iOS Limitation"

    L'invite d'installation automatique n'est pas disponible sur iOS. Utilisez le menu Partager comme décrit ci-dessus. Le menu d'aide affichera des instructions si vous utilisez un appareil iOS.

### Desktop (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Cliquez sur le bouton **"Installer l'application"** dans le menu Aide et Assistance
3. Ou cliquez sur l'icône d'installation (⊕) dans la barre d'adresse du navigateur
4. LibreFolio s'ouvre dans sa propre fenêtre

---

## 🌐 HTTP vs HTTPS

| Configuration | Installation PWA | Invite automatique |
|-------|-------------|-------------|
| `https://` (Tailscale, reverse proxy) | ✅ Support complet | ✅ Chrome affiche une bannière |
| `http://localhost` | ✅ Fonctionne | ✅ Fonctionne |
| `http://192.168.x.x` (LAN) | ⚠️ Manuel uniquement | ❌ Pas d'invite automatique |

!!! info "Self-hosted on LAN"

    Si vous accédez à LibreFolio via HTTP sur votre réseau local (ex: `http://192.168.1.100:6040`), l'invite d'installation automatique n'apparaîtra pas. Vous pouvez toujours l'installer manuellement :

    - **Android** : Menu du navigateur → "Ajouter à l'écran d'accueil"
    - **iOS** : Partager → "Ajouter à l'écran d'accueil"
    - **Desktop** : Non disponible en HTTP (utilisez Tailscale pour le HTTPS)

    Pour un support PWA complet, exposez votre instance via [Tailscale](../admin/tailscale_exposure.md) (HTTPS gratuit et facile).

---

## 🔧 Dépannage

| Problème | Solution |
|---------|----------|
| Le bouton d'installation ne s'affiche pas | L'application est peut-être déjà installée, ou vous utilisez une connexion HTTP sur réseau local (LAN) |
| iOS : pas d'option d'installation | Vous devez utiliser **Safari** — Chrome/Firefox sur iOS ne supportent pas les PWA |
| L'application ne se met pas à jour | Fermez et rouvrez l'application — elle récupère toujours la dernière version |
| Session perdue après une mise à jour | Reconnectez-vous — ceci est normal après des redémarrages du serveur |
