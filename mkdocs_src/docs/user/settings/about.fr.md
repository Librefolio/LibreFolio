# ℹ️ À propos

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="À propos">
</div>

L'onglet **À propos** affiche :

- La **version** actuelle de LibreFolio
- La **licence** (AGPL-3.0)
- Les liens vers le **dépôt GitHub** et la **documentation**
- Une carte **Soutenir LibreFolio** avec le lien café et les boutons de partage — voir [Soutenir LibreFolio](#support-librefolio) ci-dessous
- Une carte **Mentions légales** — voir [Mentions légales](#legal-notice) ci-dessous
- Une grille d'**informations système** (version de Python, système d'exploitation, mode de déploiement — Docker ou local — navigateur, viewport, thème et langue) avec un bouton **copier pour un rapport de bug** qui rassemble ces détails dans un rapport de bug prêt à coller
- Les **plugins installés** : des listes repliables des fournisseurs de prix d'actifs, des fournisseurs de taux de change, des plugins d'import de courtiers et des indicateurs de signaux détectés au démarrage, suivies des **Diagnostics des plugins**

---

## ❤️ Soutenir LibreFolio {: #support-librefolio }

La carte **Soutenir LibreFolio** propose deux façons d'aider le projet :

- **Buy Me a Coffee** ouvre la page Buy Me a Coffee du projet dans un nouvel onglet. Le même lien figure dans
  l'en-tête de la page (l'icône café, avec son libellé sur les écrans plus larges), dans le
  menu **Aide et support**, et en haut des pages de connexion.
- Sous **Ou partager**, un bouton par réseau social : **X**, **Reddit**, **Facebook**,
  **Instagram** et **TikTok**.

Un bouton de partage ouvre une boîte de dialogue **Partager sur …** avec un **Message suggéré** rédigé pour ce
réseau, dans la langue de l'interface. Quelle que soit la langue, chaque message se termine par les
mêmes cinq hashtags : `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="social-share-modal" alt="Boîte de dialogue Partager sur Reddit avec le titre suggéré, un message se terminant par les cinq hashtags, et Copier et ouvrir">
</div>

**Copier et ouvrir** copie le message, suivi du lien vers le site public du projet, et
ouvre le réseau social dans un nouvel onglet : LibreFolio reste ouvert dans son propre onglet. Chaque réseau accepte
une quantité différente de contenu préparé, et la boîte de dialogue explique à quoi vous attendre avant de cliquer :

| Réseau | Ce qui s'ouvre |
|---|---|
| **X** | Une nouvelle publication avec le message et le lien du projet déjà renseignés. |
| **Reddit** | Une nouvelle publication texte, avec le **Titre suggéré** comme titre et le message comme corps. Si Reddit laisse le corps vide, collez le texte que vous venez de copier. |
| **Facebook** | Une publication avec uniquement l'aperçu du lien : collez le texte copié dans le message de la publication. |
| **Instagram** | Instagram lui-même, qui ne peut pas préparer une publication à partir d'un lien : choisissez **Créer** (+), sélectionnez une photo ou une vidéo, puis collez la légende copiée. |
| **TikTok** | La page d'envoi de TikTok (connectez-vous si demandé) : sélectionnez votre vidéo, puis collez la légende copiée. |

Si le texte ne peut pas être copié, la boîte de dialogue le signale et vous demande d'autoriser l'accès au presse-papiers. Si le
navigateur bloque le nouvel onglet, la boîte de dialogue indique que le texte est copié mais que le site n'a pas pu être
ouvert, et vous demande d'autoriser les pop-ups. LibreFolio ne publie jamais rien à votre place : il vous revient
de la relire et de la publier sur le réseau social.

### ☕ La fenêtre de don {: #donation-popup }

De temps en temps, juste après votre connexion, LibreFolio vous rappelle que vous pouvez soutenir
le projet, avec le même lien café et les mêmes boutons de partage.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="donation-popup" alt="Fenêtre de don après connexion, avec Buy Me a Coffee, les cinq boutons de partage et Plus tard">
</div>

---

## ⚖️ Mentions légales {: #legal-notice }

La carte **Mentions légales** contient un court avertissement : LibreFolio vous aide à suivre vos investissements,
et ne constitue pas un conseil financier. Si votre instance en dispose, la carte renvoie aussi vers ses
**Conditions d'utilisation** et sa **Politique de confidentialité** : chacune s'ouvre dans un nouvel onglet.

Vous retrouvez le même avertissement sous la carte de la page d'accueil. Une version plus courte, sur une seule ligne avec les
mêmes liens, figure sous la carte de chaque page de connexion et au pied de la barre latérale, sous le
numéro de version, lorsque la barre latérale est déployée. Chaque texte que vous copiez avec
[l'export IA](../ai-export/index.md) porte aussi cet avertissement, près de sa fin et sans les liens.

---

## 🧩 Diagnostics des plugins

La section repliable **Diagnostics des plugins** indique l'état de santé des quatre registres de plugins — **Actif**
(fournisseurs de prix), **FX** (fournisseurs de taux de change), **BRIM** (importateurs de courtiers) et **Signaux**
(indicateurs) — et, en dessous, celui des **Outils**.

Chaque registre porte soit la mention **Tous chargés** (en vert), soit la liste des **plugins dont l'import a échoué**
(en rouge), avec le nom du fichier et l'erreur sous-jacente. Si un fournisseur, un importateur ou un indicateur que vous attendiez
est absent du reste de l'application, ce panneau vous en donne la raison — un plugin qui ne se charge pas au démarrage n'est tout simplement pas enregistré.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Section repliable des diagnostics des plugins dans l'onglet À propos">
</div>

### 🧰 Outils et diagnostics des outils {: #tool-diagnostics }

Sous les registres, le panneau **Outils** liste le catalogue des [Outils](../tools/index.md). Il est
en lecture seule — aucun calcul, aucune sonde et aucune réparation ne sont exécutés — et ne se charge que lorsque vous ouvrez
**Diagnostics des plugins** ; **Recharger** le relit. Pour chaque outil, vous voyez son nom et sa description,
un lien **Documentation**, son code et `Version: <contract_version>`, et si une interface compatible
est incluse dans le frontend que vous utilisez. La version de l'implémentation n'est pas affichée
ici, et la paire de versions `Backend/API · UI` n'apparaît que sur les cartes de la page Outils et dans
l'en-tête d'un outil ouvert.

Ouvrez **Diagnostics des outils** pour charger un instantané du processus serveur qui a répondu :

- la **portée de l'instantané** et l'**identifiant du processus API** ;
- l'**instantané du pool d'exécution** : si le pool est disponible, les tâches actives, en file d'attente, en attente,
  terminées et échouées, et les voies dégradées ;
- les **outils chargés dans ce processus API**, chacun avec son nom, son code et sa version de contrat, et
  les éventuels **échecs de découverte** ;
- les **limites effectives de la plateforme**, dans une section repliable dédiée.

L'instantané décrit un seul processus serveur, et non l'ensemble de l'instance, et ne se met pas à jour de lui-même :
rechargez-le pour le relire.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-tool-diagnostics" alt="Panneau Outils dans les diagnostics des plugins, avec l'allocateur PAC et les diagnostics des outils ouverts">
</div>

---

## 📜 Modale du journal des modifications {: #changelog-modal }

La **modale du journal des modifications** intégrée à l'application affiche le journal des modifications fourni avec LibreFolio, dans la langue de votre interface. Vous pouvez y accéder depuis deux endroits :

- le **numéro de version en bas de la barre latérale** (sur n'importe quelle page), et
- le **libellé de version juste sous le titre de cette page À propos** (Paramètres → À propos).

Chaque version est affichée dans votre langue lorsque sa traduction est disponible ; une version pas encore traduite apparaît en anglais, marquée d'une petite étiquette **Pas encore traduit**.

- Un **panneau repliable par version** — seule la version la plus récente s'ouvre au départ ; les sections et sous-sections se replient aussi.
- Un **index des versions** sous forme de puces en haut : cliquer sur une version la déplie et fait défiler directement jusqu'à elle.
- Une **zone de recherche** qui descend dans les replis : les sections correspondantes s'ouvrent automatiquement et les puces de résultat cliquables mènent à l'endroit exact.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Recherche dans la modale du journal des modifications ouvrant les replis correspondants">
</div>

- Des boutons **Tout déplier / Tout replier**, et un lien vers le fichier du journal des modifications sur GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modale du journal des modifications avec des versions repliables et la recherche">
</div>

### 🔄 Vérification des mises à jour

L'en-tête de la modale comporte aussi un bouton **Vérifier les mises à jour**. Il demande au serveur quelle version est
en cours d'exécution, relit la dernière version **stable** sur GitHub (au lieu de réutiliser le résultat
que la vérification automatique conserve pendant une heure) et compare les deux. Une version plus récente n'est prise en compte qu'une fois que son image Docker est disponible sur le registre ; une version dont la compilation est encore en cours n'est donc pas encore proposée — voir [Notifications de mise à jour](../../admin/index.md#update-notifications).

Une vérification lancée ici vous indique toujours comment elle s'est déroulée :

- Si LibreFolio est **à jour**, un toast de confirmation apparaît, avec la version détectée en ligne.
- Si GitHub n'a **aucune version stable**, ou si, pour une version plus récente, l'**image Docker n'est pas encore disponible**,
  un avertissement le signale.
- Si la vérification **échoue** — par exemple lorsque GitHub ou le registre est inaccessible — une erreur
  vous demande de réessayer. Une vérification échouée n'indique jamais que vous êtes à jour.
- Si une version plus récente existe et que vous êtes **administrateur**, la modale **Nouvelle version disponible** s'ouvre
  aussitôt, par-dessus le journal des modifications : la version actuelle et la dernière version côte à côte, avec **Comment mettre à jour**
  (le [guide de mise à jour](../installation.md#updating)) et **Notes de version sur GitHub**. Vous pouvez la
  fermer avec **Me rappeler plus tard** (vous serez rappelé à la prochaine connexion) ou
  **Ignorer cette version** (la vérification automatique ne vous sollicitera plus jamais pour cette version ; une vérification lancée
  ici l'affiche toujours). Les administrateurs font aussi l'objet d'une vérification automatique à la connexion — voir
  [Notifications de mise à jour](../../admin/index.md#update-notifications) pour le déroulement côté administrateur.
- Si une version plus récente existe et que vous n'êtes **pas administrateur**, la boîte de dialogue **Mise à jour disponible — contactez un administrateur** liste les **administrateurs** de l'instance — avec les adresses e-mail lorsqu'elles sont disponibles, chacune avec un lien mailto et un bouton de copie — afin que vous sachiez à qui demander la mise à niveau. Aucune vérification automatique n'est effectuée pour les non-administrateurs.

### ✨ Les nouveautés après une mise à jour {: #whats-new }

Lorsque LibreFolio a été mis à jour depuis votre dernière visite, la fois suivante où vous l'ouvrez, une
fenêtre **Nouveautés de LibreFolio** montre ce qui a changé : la partie du journal des modifications correspondant à chaque version
publiée depuis la dernière que vous avez vue. Si votre compte est plus ancien que cette fenêtre, elle affiche la partie du journal
correspondant à la version en cours d'exécution.

- Chaque partie est dans la langue de votre interface lorsque sa traduction est prête ; sinon, elle est en anglais,
  marquée **Pas encore traduit**, comme dans le journal des modifications.
- **Journal des modifications complet** ouvre le journal complet sur GitHub, dans un nouvel onglet.
- **Compris** ferme la fenêtre, tout comme <kbd>Esc</kbd> et un clic à l'extérieur. Elle ne réapparaît
  pas avant la prochaine mise à jour. Si LibreFolio ne peut pas enregistrer que vous l'avez fermée, par exemple parce que
  la connexion a été interrompue, la fenêtre s'affiche de nouveau la fois suivante où vous ouvrez LibreFolio.
- Elle attend qu'aucun guide ni aucune autre fenêtre ne soient ouverts, et apparaît avant la
  [fenêtre de don](#donation-popup) et l'avis de mise à jour.
- Un nouveau compte ne la voit jamais : il démarre avec la version sur laquelle il a été créé.

---

## 🔗 Voir aussi

- ⚙️ **[Vue d'ensemble des paramètres](index.md)** — Résumé des paramètres généraux
- 👤 **[Profil](profile.md)** — Nom d'utilisateur, e-mail, avatar, mot de passe
- 🎛️ **[Préférences utilisateur](preferences.md)** — Langue, devise de base et thème
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options administrateur et planificateur
