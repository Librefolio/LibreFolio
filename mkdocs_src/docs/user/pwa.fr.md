# 📱 Installer comme application (PWA)

LibreFolio peut être installé en tant qu'**application web progressive (PWA)** sur votre appareil. Cela vous offre une expérience proche d'une application native : mode plein écran, absence de barre d'adresse du navigateur et icône sur l'écran d'accueil — sans téléchargement depuis un magasin d'applications.

---

## ✅ Ce que vous obtenez

| Fonctionnalité | Description |
|---------|-------------|
| **Mode plein écran** | Pas de barre d'adresse ni d'interface encombrée du navigateur |
| **Icône sur l'écran d'accueil** | Lancez LibreFolio comme une application native |
| **Aucune interférence gestuelle** | Balayage arrière et zoom par double tap désactivés |
| **Session persistante** | Restez connecté entre les lancements |

!!! note "En ligne uniquement"

    La PWA LibreFolio nécessite une connexion réseau active. Il n'y a pas de mode hors ligne — vos données résident sur votre serveur.

---

## 📲 Comment installer

### Android (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Recherchez le bouton **"Installer l'application"** dans le menu **Aide et support** (icône ❓ en haut à droite)
3. Appuyez sur **Installer** lorsque vous y êtes invité
4. LibreFolio apparaît sur votre écran d'accueil

!!! tip "Méthode alternative"

    Si le bouton d'installation n'apparaît pas, appuyez sur **le menu ⋮ → "Ajouter à l'écran d'accueil"** ou **"Installer l'application"**.

### iOS (Safari)

1. Ouvrez LibreFolio dans **Safari** (obligatoire — les autres navigateurs ne prennent pas en charge les PWA sur iOS)
2. Appuyez sur le bouton **Partager** (carré avec une flèche)
3. Faites défiler vers le bas et appuyez sur **"Ajouter à l'écran d'accueil"**
4. Appuyez sur **Ajouter**

!!! warning "Limitation iOS"

    L'invite d'installation automatique n'est pas disponible sur iOS. Utilisez le menu Partager comme décrit ci-dessus. Le menu Aide affichera des instructions si vous êtes sur un appareil iOS.

### Bureau (Chrome / Edge)

1. Ouvrez LibreFolio dans Chrome ou Edge
2. Cliquez sur le bouton **"Installer l'application"** dans le menu Aide et support
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
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, proxy inverse)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Prise en charge complète</td>
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

!!! warning "Exigence de connexion HTTPS pour la PWA"

    Pour installer LibreFolio en tant que PWA, **les navigateurs modernes exigent strictement une connexion HTTPS sécurisée** (sauf lors de l'accès via `localhost` ou `127.0.0.1` pour le développement local).

    Si vous ouvrez LibreFolio en HTTP simple sur votre réseau local (par exemple, `http://192.168.1.100:6040`), l'installation de la PWA ne sera pas disponible et l'application ne pourra pas fonctionner en mode autonome.

    Vous pouvez choisir n'importe quelle méthode pour activer HTTPS sur votre instance, mais nous recommandons fortement notre guide simple et gratuit : **[Guide d'exposition Tailscale](../admin/service_exposure.md)**. Il vous fournit une URL HTTPS sécurisée sans configurer de certificats SSL ni ouvrir de ports routeur.

---

## 🔧 Dépannage

| Problème | Solution |
|---------|----------|
| Le bouton d'installation n'apparaît pas | Vous l'avez peut-être déjà installée, ou vous êtes en HTTP sur le LAN |
| iOS : pas d'option d'installation | Vous devez utiliser **Safari** — Chrome/Firefox sur iOS ne prennent pas en charge les PWA |
| L'application ne se met pas à jour | Fermez et rouvrez l'application — elle récupère toujours la dernière version |
| Session perdue après une mise à jour | Reconnectez-vous — c'est normal après un redémarrage du serveur |
