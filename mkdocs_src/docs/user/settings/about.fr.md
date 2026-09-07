# ℹ️ À propos

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

L'onglet **À propos** affiche :

- La **version** actuelle de LibreFolio
- La **licence** (AGPL-3.0)
- Les liens vers le **dépôt GitHub** et la **documentation**
- Une grille **d'informations système** (version de Python, système d'exploitation, mode de déploiement — Docker ou local — navigateur, viewport, thème et langue) avec un bouton **Copier pour un ticket** qui regroupe ces détails dans un rapport de bug prêt à coller
- Les **plugins installés** : listes dépliables des fournisseurs de prix d'actifs, des fournisseurs de taux FX, des plugins d'importation de courtiers et des indicateurs de signaux détectés au démarrage

---

## 🧩 Diagnostics des plugins

Le panneau dépliable **Diagnostics des plugins** rend compte de l'état des quatre registres de plugins — **fournisseurs d'actifs**, **fournisseurs FX**, **importateurs de courtiers** et **indicateurs de signaux**.

Chaque registre est soit **entièrement chargé** (vert), soit affiche les **plugins qui n'ont pas pu être importés** (rouge), avec le nom du fichier et l'erreur sous-jacente. Si un fournisseur, un importateur ou un indicateur que vous attendiez est absent du reste de l'application, ce panneau vous explique pourquoi — un plugin qui ne parvient pas à se charger au démarrage n'est tout simplement pas enregistré.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Plugin diagnostics collapsible in the About tab">
</div>

---

## 📜 Modale du changelog {: #changelog-modal }

La **modale du changelog** intégrée à l'application affiche le fichier `CHANGELOG.md` inclus. Vous pouvez y accéder depuis deux endroits :

- le **numéro de version en bas de la barre latérale** (sur n'importe quelle page), et
- l'**étiquette de version juste sous le titre de cette page À propos** (Paramètres → À propos).

- Un **panneau dépliable par version** — seule la version la plus récente commence ouverte ; les sections et sous-sections se replient également.
- Un **index des versions** sous forme de pastilles en haut : cliquer sur une version la déplie et fait défiler directement jusqu'à elle.
- Une **zone de recherche** qui descend dans les plis : les sections correspondantes s'ouvrent automatiquement, et les pastilles de résultats cliquables mènent directement à l'endroit exact.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Changelog modal search opening the matching folds">
</div>

- Des boutons **Tout déplier / Tout replier**, et un lien vers le fichier du changelog sur GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Changelog modal with foldable releases and search">
</div>

### 🔄 Vérifier les mises à jour

L'en-tête de la modale comporte également un bouton **Vérifier les mises à jour**, qui interroge GitHub pour connaître la dernière version stable. Ce qui se passe ensuite dépend de votre rôle :

- Si LibreFolio est **à jour**, un toast de confirmation apparaît.
- Si une version plus récente existe et que vous êtes **administrateur**, la **modale de mise à jour disponible** s'ouvre : la version actuelle et la dernière version côte à côte, avec des liens vers le [guide de mise à jour](../installation.md#updating) et la page des versions GitHub. Vous pouvez la fermer avec **Plus tard** (un rappel vous sera fait à la prochaine connexion) ou **Ignorer cette version** (aucune invite ne s'affichera plus pour cette version). Les administrateurs sont également interrogés automatiquement à la connexion — voir [Notifications de mise à jour](../../admin/index.md#update-notifications) pour le flux côté administrateur.
- Si une version plus récente existe et que vous n'êtes **pas administrateur**, une boîte de dialogue liste les **administrateurs** de l'instance — avec les adresses e-mail lorsqu'elles sont disponibles, chacune accompagnée d'un lien mailto et d'un bouton de copie — afin que vous sachiez à qui demander la mise à jour. Les non-administrateurs ne sont jamais interrogés automatiquement.

---

## 🔗 Liens connexes

- ⚙️ **[Aperçu des paramètres](index.md)** — Résumé des paramètres généraux
- 👤 **[Profil](profile.md)** — Nom d'utilisateur, e-mail, avatar, mot de passe
- 🎛️ **[Préférences utilisateur](preferences.md)** — Langue, devise de base et thème
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options d'administration et planificateur
