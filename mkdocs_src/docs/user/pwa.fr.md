# 📱 Installer en tant qu'application (PWA)

LibreFolio peut être installé en tant que **Progressive Web App (PWA)** sur votre appareil. Cela vous offre une expérience similaire à une application native : mode plein écran, absence de barre d'adresse du navigateur et une icône sur l'écran d'accueil — sans avoir à passer par un magasin d'applications.

---

## ✅ Ce que vous obtenez

| Fonctionnalité | Description |
|---------|-------------|
| **Mode plein écran** | Pas de barre d'adresse ni d'encombrement de l'interface du navigateur |
| **Icône d'écran d'accueil** | Lancez LibreFolio comme une application native |
| **Aucune interférence de gestes** | Balayage arrière et zoom par double-tap désactivés |
| **Session persistante** | Reste connecté entre les lancements |

!!! note "Online Only"

    La PWA LibreFolio nécessite une connexion réseau active. Il n'y a pas de mode hors ligne — vos données résident sur votre serveur.

---

## 📲 Comment installer

### Android (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Recherchez le bouton **"Installer l'application"** dans le menu **Aide & Support** (icône ❓ en haut à droite)
3. Appuyez sur **Installer** lorsqu'on vous le demande
4. LibreFolio apparaît sur votre écran d'accueil

!!! tip "Alternative method"

    Si le bouton Installer n'apparaît pas, appuyez sur le **menu ⋮ du navigateur → "Ajouter à l'écran d'accueil"** ou **"Installer l'application"**.

### iOS (Safari)

1. Ouvrez LibreFolio dans **Safari** (requis — les autres navigateurs ne supportent pas les PWA sur iOS)
2. Appuyez sur le bouton **Partager** (carré avec une flèche)
3. Faites défiler vers le bas et appuyez sur **"Sur l'écran d'accueil"**
4. Appuyez sur **Ajouter**

!!! warning "iOS Limitation"

    L'invite d'installation automatique n'est pas disponible sur iOS. Utilisez le menu Partager comme décrit ci-dessus. Le menu Aide affichera des instructions si vous utilisez un appareil iOS.

### Desktop (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Cliquez sur le bouton **"Installer l'application"** dans le menu Aide & Support
3. Ou cliquez sur l'icône d'installation (⊕) dans la barre d'adresse du navigateur
4. LibreFolio s'ouvre dans sa propre fenêtre

---

## 🌐 HTTP vs HTTPS

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 45%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Configuration</th>
 <th style="width: 25%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Installation PWA</th>
 <th style="width: 30%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Invite automatique</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, reverse proxy)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Support complet</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Chrome affiche la bannière</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>http://localhost</code></td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Fonctionne</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Fonctionne</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap; background-color: rgba(244, 67, 54, 0.04);"><code>http://192.168.x.x</code> (LAN)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Non disponible (HTTPS requis)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Pas d'invite automatique</td>
 </tr>
 </tbody>
</table>

!!! warning "HTTPS Connection Requirement for PWA"

    Pour installer LibreFolio en tant que PWA, **les navigateurs modernes exigent strictement une connexion HTTPS sécurisée** (sauf lors d'un accès via `localhost` ou `127.0.0.1` pour le développement local).

    Si vous ouvrez LibreFolio via HTTP simple sur votre réseau local (par exemple, `http://192.168.1.100:6040`), l'installation de la PWA ne sera pas disponible et l'application ne pourra pas s'exécuter en mode autonome.

    Vous pouvez choisir la méthode que vous préférez pour activer HTTPS sur votre instance, mais nous recommandons fortement notre guide simple et gratuit : **[Guide d'exposition Tailscale](../admin/tailscale_exposure.md)**. Il vous fournit une URL HTTPS sécurisée sans avoir à configurer de certificats SSL ou à ouvrir des ports de routeur.

---

## 🔧 Dépannage

| Problème | Solution |
|---------|----------|
| Le bouton d'installation ne s'affiche pas | L'application est peut-être déjà installée, ou vous utilisez une connexion HTTP sur un réseau local (LAN) |
| iOS : aucune option d'installation | L'utilisation de **Safari** est requise — Chrome/Firefox sur iOS ne supportent pas les PWA |
| L'application ne se met pas à jour | Fermez et rouvrez l'application — elle récupère toujours la dernière version |
| Session perdue après mise à jour | Reconnectez-vous — cela est normal après les redémarrages du serveur |
