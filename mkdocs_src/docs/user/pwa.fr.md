# 📱 Installation en tant qu'application (PWA)

LibreFolio peut être installé en tant qu'**Application Web Progressive (PWA)** sur votre appareil. Cela vous offre une expérience similaire à une application : mode plein écran, absence de barre d'adresse du navigateur et icône sur l'écran d'accueil — le tout sans téléchargement via un magasin d'applications.

---

## ✅ Ce que vous obtenez

| Fonctionnalité | Description |
|----------------|-------------|
| **Mode plein écran** | Pas de barre d'adresse ni d'encombrement de l'interface du navigateur |
| **Icône sur l'écran d'accueil** | Lancez LibreFolio comme une application native |
| **Aucune interférence avec les gestes** | Balayage pour revenir et zoom par double-tap désactivés |
| **Session persistante** | Reste connecté entre les lancements |

!!! note "Online Only"

    La PWA LibreFolio nécessite une connexion réseau active. Il n'y a pas de mode hors ligne — vos données résident sur votre serveur.

---

## 📲 Comment installer

### Android (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Recherchez le bouton **"Installer l'application"** dans le menu **Aide et Support** (icône ❓ en haut à droite)
3. Appuyez sur **Installer** lorsqu'on vous le demande
4. LibreFolio apparaît sur votre écran d'accueil

!!! tip "Alternative method"

    Si le bouton d'installation n'apparaît pas, appuyez sur le **menu ⋮ du navigateur → "Ajouter à l'écran d'accueil"** ou **"Installer l'application"**.

### iOS (Safari)

1. Ouvrez LibreFolio dans **Safari** (requis — les autres navigateurs ne supportent pas la PWA sur iOS)
2. Appuyez sur le bouton **Partager** (carré avec flèche)
3. Faites défiler vers le bas et appuyez sur **"Sur l'écran d'accueil"**
4. Appuyez sur **Ajouter**

!!! warning "iOS Limitation"

    L'invite d'installation automatique n'est pas disponible sur iOS. Utilisez le bouton Partager comme décrit ci-dessus. Le menu Aide et Support affichera des instructions si vous utilisez un appareil iOS.

### Desktop (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Cliquez sur le bouton **"Installer l'application"** dans le menu Aide et Support
3. Ou cliquez sur l'icône d'installation (⊕) dans la barre d'adresse du navigateur
4. LibreFolio s'ouvre dans sa propre fenêtre

---

## 🌐 HTTP vs HTTPS

| Configuration | Installation PWA | Invite automatique |
|---------------|-----------------|-------------------|
| `https://` (Tailscale, reverse proxy) | ✅ Support complet | ✅ Chrome affiche la bannière |
| `http://localhost` | ✅ Fonctionne | ✅ Fonctionne |
| `http://192.168.x.x` (LAN) | ⚠️ Manuel uniquement | ❌ Pas d'invite automatique |

!!! info "Self-hosted on LAN"

    Si vous accédez à LibreFolio via HTTP sur votre réseau local (ex: `http://192.168.1.100:6040`), l'invite d'installation automatique n'apparaîtra pas. Vous pouvez toujours l'installer manuellement :

    - **Android** : Menu du navigateur → "Ajouter à l'écran d'accueil"
    - **iOS** : Partager → "Sur l'écran d'accueil"
    - **Desktop** : Non disponible en HTTP (utilisez Tailscale pour le HTTPS)

    Pour un support PWA complet, exposez votre instance via [Tailscale](../admin/tailscale_exposure.md) (HTTPS gratuit et facile).

---

## 🔧 Dépannage

| Problème | Solution |
|----------|----------|
| Le bouton d'installation ne s'affiche pas | L'application est peut-être déjà installée, ou vous utilisez une connexion HTTP sur votre réseau local (LAN) |
| iOS : aucune option d'installation | Vous devez utiliser **Safari** — Chrome/Firefox sur iOS ne supportent pas la PWA |
| L'application ne se met pas à jour | Fermez et rouvrez l'application — elle récupère toujours la dernière version |
| Session perdue après une mise à jour | Connectez-vous à nouveau — ceci est attendu après des redémarrages du serveur |
