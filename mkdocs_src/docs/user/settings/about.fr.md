# ℹ️ À propos

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

L'onglet **À propos** affiche :

- La **version** actuelle de LibreFolio
- La **licence** (AGPL-3.0)
- Des liens vers le **dépôt GitHub** et la **documentation**
- Une carte **Soutenir LibreFolio** avec le lien café et les boutons de partage — voir [Soutenir LibreFolio](#support-librefolio) ci-dessous
- Une grille d'**informations système** (version de Python, système d'exploitation, mode de déploiement — Docker ou local — navigateur, fenêtre d'affichage, thème et langue) avec un bouton **copier pour un ticket** qui rassemble ces détails dans un rapport de bogue prêt à coller
- Les **plugins installés** : des listes repliables des fournisseurs de cours d'actifs, des fournisseurs de taux de change, des plugins d'import de courtiers et des indicateurs de signaux détectés au démarrage, suivies des **Diagnostics des plugins**

---

## ❤️ Soutenir LibreFolio {: #support-librefolio }

La carte **Soutenir LibreFolio** propose deux façons d'aider le projet :

- **Buy Me a Coffee** ouvre la page Buy Me a Coffee du projet dans un nouvel onglet. Le même lien figure dans
  l'en-tête de la page (l'icône café, avec son libellé sur les écrans plus larges) et dans le
  menu **Aide & Support**.
- Sous **Ou partager**, un bouton par réseau social : **X**, **Reddit**, **Facebook**,
  **Instagram** et **TikTok**.

Un bouton de partage ouvre une boîte de dialogue **Partager sur …** avec un **Message suggéré** rédigé pour ce
réseau, dans la langue de l'interface. Quelle que soit la langue, chaque message se termine par
les cinq mêmes hashtags : `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="social-share-modal" alt="Boîte de dialogue Partager sur Reddit avec le titre suggéré, un message qui se termine par les cinq hashtags, et Copier et ouvrir">
</div>

**Copier et ouvrir** copie le message, suivi du lien vers le site public du projet, et
ouvre le réseau social dans un nouvel onglet : LibreFolio reste ouvert dans son propre onglet. Chaque réseau accepte
une quantité différente de contenu préparé, et la boîte de dialogue explique à quoi s'attendre avant que vous cliquiez :

| Réseau | Ce qui s'ouvre |
|---|---|
| **X** | Un nouveau post avec le message et le lien du projet déjà remplis. |
| **Reddit** | Un nouveau post texte, avec le **Titre suggéré** comme titre et le message comme corps. Si Reddit laisse le corps vide, collez le texte que vous venez de copier. |
| **Facebook** | Un post avec uniquement l'aperçu du lien : collez le texte copié dans le message du post. |
| **Instagram** | Instagram lui-même, qui ne peut pas préparer un post à partir d'un lien : choisissez **Créer** (+), sélectionnez une photo ou une vidéo, puis collez la légende copiée. |
| **TikTok** | La page de mise en ligne de TikTok (connectez-vous si demandé) : sélectionnez votre vidéo, puis collez la légende copiée. |

Si le texte ne peut pas être copié, la boîte de dialogue le signale et vous demande d'autoriser l'accès au presse-papiers. Si le
navigateur bloque le nouvel onglet, la boîte de dialogue indique que le texte est copié mais que le site n'a pas pu être
ouvert, et vous demande d'autoriser les pop-ups. LibreFolio ne publie jamais rien à votre place : le post vous
appartient, à vous de le vérifier et de le publier sur le réseau social.

### ☕ La pop-up de don {: #donation-popup }

De temps en temps, juste après votre connexion, LibreFolio vous rappelle que vous pouvez soutenir le
projet, avec le même lien café et les mêmes boutons de partage.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="donation-popup" alt="Pop-up de don après la connexion, avec Buy Me a Coffee, les cinq boutons de partage et Plus tard">
</div>

---

## 🧩 Diagnostics des plugins

La section repliable **Diagnostics des plugins** indique l'état des quatre registres de plugins — **Actif**
(fournisseurs de cours), **FX** (fournisseurs de taux de change), **BRIM** (importateurs de courtiers) et **Signaux**
(indicateurs) — et, en dessous, celui des **Outils**.

Chaque registre est soit marqué **Tous chargés** (vert), soit liste les **plugins dont l'import a échoué** (rouge), avec le nom du fichier et l'erreur sous-jacente. Si un fournisseur, un importateur ou un indicateur que vous attendiez est absent du reste de l'application, ce panneau vous en explique la raison — un plugin dont le chargement échoue au démarrage n'est tout simplement pas enregistré.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Section repliable Diagnostics des plugins dans l'onglet À propos">
</div>

### 🧰 Outils et diagnostics des outils {: #tool-diagnostics }

Sous les registres, le panneau **Outils** liste le catalogue des [Outils](../tools/index.md). Il est
en lecture seule — aucun calcul, sondage ou réparation n'est exécuté — et il ne se charge que lorsque vous ouvrez
**Diagnostics des plugins** ; **Recharger** le relit. Pour chaque outil, vous voyez son nom et sa description,
un lien **Documentation**, son code et `Version: <contract_version>`, et si une interface compatible est incluse dans le frontend que vous utilisez. La version d'implémentation n'est pas affichée
ici, et le couple de versions `Backend/API · UI` n'apparaît que sur les cartes de la page Outils et dans
l'en-tête d'un outil ouvert.

Ouvrez **Diagnostics des outils** pour charger un instantané du processus serveur qui a répondu :

- la **Portée de l'instantané** et l'**identifiant du processus API** ;
- l'**Instantané du pool d'exécution** : si le pool est disponible, les tâches actives, en file, en attente,
  terminées et en échec, et les voies dégradées ;
- les **Outils chargés dans ce processus API**, chacun avec son nom, son code et sa version de contrat, ainsi que
  les éventuels **Échecs de découverte** ;
- les **Limites de plateforme effectives**, dans leur propre section repliable.

L'instantané décrit un seul processus serveur, pas l'instance entière, et ne se met pas à jour tout seul :
rechargez-le pour le relire.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-tool-diagnostics" alt="Panneau Outils dans Diagnostics des plugins, avec l'Allocateur PAC et Diagnostics des outils ouverts">
</div>

---

## 📜 Modale du journal des modifications {: #changelog-modal }

La **modale du journal des modifications** intégrée à l'application affiche le fichier `CHANGELOG.md` fourni. Vous pouvez y accéder depuis deux endroits :

- le **numéro de version en bas de la barre latérale** (sur n'importe quelle page), et
- le **libellé de version juste sous le titre de cette page À propos** (Paramètres → À propos).

- Un **panneau repliable par version** — seule la version la plus récente est ouverte au départ ; les sections et sous-sections se replient aussi.
- Un **index des versions** sous forme de pastilles en haut : cliquer sur une version la déplie et fait défiler directement jusqu'à elle.
- Une **zone de recherche** qui descend dans les replis : les sections correspondantes s'ouvrent automatiquement, et les pastilles de résultat cliquables sautent à l'endroit exact.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Recherche dans la modale Journal des modifications, qui ouvre les sections correspondantes">
</div>

- Des boutons **Tout déplier / tout replier**, et un lien vers le fichier du journal des modifications sur GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modale Journal des modifications avec versions repliables et recherche">
</div>

### 🔄 Recherche de mises à jour

L'en-tête de la modale comporte également un bouton **Rechercher des mises à jour**. Il demande au serveur quelle version est
en cours d'exécution, relit la dernière version **stable** sur GitHub (au lieu de réutiliser le résultat
que la vérification automatique conserve pendant une heure), et compare les deux. Une version plus récente ne compte qu'une fois son image Docker disponible sur le registre ; une version dont la compilation est encore en cours
n'est donc pas encore proposée — voir [Notifications de mise à jour](../../admin/index.md#update-notifications).

Une vérification lancée ici vous indique toujours comment elle s'est déroulée :

- Si LibreFolio est **à jour**, une notification de confirmation apparaît, avec la version détectée en ligne.
- Si GitHub n'a **aucune version stable**, ou si l'**image Docker d'une version plus récente n'est pas encore disponible**,
  un avertissement le signale.
- Si la vérification **échoue** — par exemple lorsque GitHub ou le registre est inaccessible — une erreur
  vous invite à réessayer. Une vérification en échec n'indique jamais que vous êtes à jour.
- Si une version plus récente existe et que vous êtes **administrateur**, la modale **Nouvelle version disponible** s'ouvre
  aussitôt, par-dessus le journal des modifications : versions actuelle et dernière côte à côte, avec **Comment mettre à jour**
  (le [guide de mise à jour](../installation.md#updating)) et **Notes de version sur GitHub**. Vous pouvez
  la fermer avec **Me rappeler plus tard** (vous serez rappelé à la prochaine connexion) ou
  **Ignorer cette version** (la vérification automatique ne vous relancera plus pour cette version ; une vérification lancée
  ici l'affiche toujours). Les administrateurs sont également sollicités automatiquement à la connexion — voir
  [Notifications de mise à jour](../../admin/index.md#update-notifications) pour le flux côté administrateur.
- Si une version plus récente existe et que vous **n'êtes pas administrateur**, la boîte de dialogue **Mise à jour disponible — contactez un administrateur** liste les **administrateurs** de l'instance — avec les adresses e-mail lorsqu'elles sont disponibles, chacune accompagnée d'un lien mailto et d'un bouton de copie — afin que vous sachiez à qui demander la mise à niveau. Les non-administrateurs ne sont jamais sollicités automatiquement.

---

## 🔗 Voir aussi

- ⚙️ **[Vue d'ensemble des paramètres](index.md)** — Résumé des paramètres généraux
- 👤 **[Profil](profile.md)** — Nom d'utilisateur, e-mail, avatar, mot de passe
- 🎛️ **[Préférences utilisateur](preferences.md)** — Langue, devise de référence et thème
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options administrateur et planificateur
