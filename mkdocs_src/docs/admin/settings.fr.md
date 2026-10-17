# ⚙️ Paramètres globaux

Les paramètres globaux s'appliquent à toute l'instance et à chaque utilisateur. Ils sont stockés dans la base de données :
tout le monde peut les lire, seuls les administrateurs peuvent les modifier.

---

## ✏️ Modifier un paramètre

### 🔓 1. Déverrouiller l'onglet

Ouvrez **Paramètres** (icône d'engrenage dans la barre latérale), puis l'onglet **Administration** : son panneau
**Paramètres globaux** regroupe les paramètres par catégorie. Cliquez sur l'**icône de cadenas** (🔒) dans l'en-tête pour le déverrouiller.
Seuls les administrateurs (superusers) disposent du cadenas ; tous les autres obtiennent une vue en lecture seule.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Paramètres globaux" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Modifier et enregistrer

- Rien n'est écrit tant que vous ne cliquez pas sur **Enregistrer** à côté d'un paramètre, ou sur **Enregistrer Tout** dans l'en-tête.
  **Rétablir** et **Annuler Tout** rétablissent les valeurs enregistrées.
- **Réinitialiser** et **Réinitialiser Tout** remplissent les valeurs par défaut, prêtes à être enregistrées.
- Les valeurs enregistrées s'appliquent immédiatement, sans redémarrage.

??? note "🔒 Verrouillage avec des modifications non enregistrées — quand une boîte de dialogue demande d'abord"

    Cliquer sur le cadenas avec des modifications non enregistrées demande si vous souhaitez les abandonner. **Annuler** conserve vos
    modifications ; **Abandonner** rétablit les valeurs enregistrées et verrouille l'onglet.

??? tip "💻 Paramètres manquants — recréez-les depuis la ligne de commande"

    Chaque démarrage du serveur recrée tout paramètre manquant avec sa valeur par défaut. Pour le faire sans
    redémarrage, exécutez l'[outil en ligne de commande](cli_tools.md) :

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    Les valeurs que vous avez modifiées sont conservées.

---

## 📋 Ce que fait chaque paramètre

| Catégorie | Paramètre | Valeur par défaut | Ce qu'il fait — quand le modifier |
|---|---|---|---|
| ⏳ Session | **Durée de session** | 24 heures | Combien de temps les utilisateurs restent connectés. Raccourcissez-la sur les appareils partagés ; une nouvelle valeur s'applique à partir de la prochaine connexion de chaque utilisateur. |
| 🛡️ Sécurité | **Activer l'inscription** | Activé | Permet à de nouvelles personnes de s'inscrire. Désactivez cet interrupteur une fois que tout le monde a un compte, surtout si l'instance est accessible depuis internet. Le premier compte d'une nouvelle instance peut toujours être créé. |
| 🛡️ Sécurité | **Vérification Email Requise** | Désactivé | Les nouveaux comptes doivent ouvrir un lien envoyé par e-mail à leur adresse avant de pouvoir se connecter ; le premier compte n'attend jamais, et les comptes existants ne changent pas. Elle ne s'active que lorsque l'e-mail fonctionne et que `LIBREFOLIO_PUBLIC_URL` est utilisable : d'ici là, l'interrupteur reste grisé. Voir *Email Verification* dans [E-mail](email.md). |
| 🔄 Tâche de mise à jour | **Planificateur activé** | Activé | Active ou désactive les mises à jour automatiques des prix et des taux de change : voir [Planificateur de données de marché](#market-data-scheduler). |
| 🧠 Mémoire | **Taille Max Téléversement** | 10 Mo | Le plus gros fichier que les utilisateurs peuvent téléverser, rapports de courtiers inclus. Augmentez-la si un gros export est refusé. |
| 🌍 Valeurs par défaut | **Devise par défaut** | `EUR` | La devise dans laquelle les nouveaux utilisateurs déclarent leurs opérations. |
| 🌍 Valeurs par défaut | **Langue par défaut** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` ou 🇪🇸 `es`. |
| 🌍 Valeurs par défaut | **Thème par défaut** | `auto` | ☀️ `light`, 🌙 `dark`, ou 🖥️ `auto`, qui suit l'appareil. |

Les nouveaux utilisateurs partent de ces trois valeurs par défaut : la [configuration d'accueil](../user/getting-started.md#welcome-setup)
affiche leur langue et leur devise pré-remplies. Modifier une valeur par défaut plus tard laisse les
[Préférences](../user/settings/preferences.md) des utilisateurs existants intactes.

---

## 🕐 Planificateur de données de marché {: #market-data-scheduler }

Le planificateur maintient les prix et les taux de change à jour tout seul, même quand personne n'est connecté :

- 💰 **Actualisation des Prix Courants** — toutes les quelques minutes, le dernier prix de chaque actif actif qui dispose
  d'un fournisseur de prix.
- 📊 **Synchronisation Historique** — aux jours et heures que vous choisissez, les prix quotidiens de ces actifs et les
  taux de chaque paire FX disposant d'un fournisseur, sur au moins l'**Horizon de récupération**, pour combler tout
  manque. Pour un actif ou une paire dont le dernier prix ou taux enregistré est plus ancien, elle remonte jusqu'à ce
  jour, d'un an au plus ; un actif sans aucun prix enregistré n'a que l'horizon, car le planificateur ne télécharge
  jamais un historique complet. Les paires avec uniquement des taux manuels sont ignorées.

Si le serveur est éteint ou en veille à une heure de synchronisation, la synchronisation historique
manquée s'exécute dès que le serveur revient, sans attendre l'heure de synchronisation suivante : un serveur
éteint pendant des semaines comble tout son manque.

### ⚙️ Configurer la planification

Déverrouillez l'onglet, ouvrez **Tâche de mise à jour** et cliquez sur **Configurer…** dans la ligne **Configuration du Planning**.
La boîte de dialogue possède son propre bouton **Enregistrer**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale de configuration du planificateur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Champ | Valeur par défaut | Ce qu'il définit |
|---|---|---|
| **Fuseau horaire** | `UTC` | Le fuseau horaire des heures et des jours ci-dessous ; l'horloge UTC du serveur est affichée à côté. |
| **Actualiser toutes les** | 10 minutes | La fréquence de rafraîchissement des prix actuels, de 1 à 1440 minutes. |
| **Heures de synchronisation** | `06:00`, `23:00` | Quand la synchronisation de l'historique s'exécute ; **Ajouter un horaire** ajoute un créneau. |
| **Jours de synchronisation** | Lun au Sam | Les jours de la synchronisation de l'historique. |
| **Horizon de récupération** | 14 jours | Combien de jours passés chaque synchronisation de l'historique vérifie au moins, de 1 à 365. Elle remonte plus loin, jusqu'à un an, quand le dernier prix ou taux enregistré d'un actif ou d'une paire est plus ancien. |

Conservez au moins une heure et un jour. Astuce : une synchronisation de l'historique après la clôture des marchés (par exemple
`22:00`) obtient les données les plus complètes.

??? warning "🌍 Changer le fuseau horaire — les tâches se déplacent dans le temps"

    Les heures et les jours conservent leurs valeurs mais comptent dans le nouveau fuseau horaire, donc les tâches s'exécutent à un autre
    moment. Elles suivent aussi son heure d'été : `06:00` dans `Europe/Rome` s'exécute à 05:00 UTC
    en hiver et à 04:00 UTC en été.

### 📜 Lire le journal du planificateur

La ligne **État du planificateur** affiche le dernier rafraîchissement du prix actuel, avec un point pour son résultat.
Quand un nouvel essai est prévu, une ligne de plus en donne l'heure : **Échec : nouvel essai à …** après un
rafraîchissement qui n'a pas pu aboutir, sinon **Éléments en pause réessayés à …** pour les prix reportés parce que
leur fournisseur est en pause.
Cliquez sur la ligne (ou sur **Détails…**) pour ouvrir le **Journal d'exécution du planificateur**. Seuls les administrateurs peuvent
lire l'état et le journal.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale du journal du planificateur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Chaque entrée correspond à une exécution : tâche, heure, durée et combien d'éléments ont réussi. 🟢 **OK** : tous,
  ou rien à faire ; 🟡 **Partiel** : certains ont échoué, ou ont été reportés parce que leur fournisseur est en pause
  après trop de requêtes ; 🔴 **Erreur** : aucun n'a réussi et aucun n'a été reporté.
- Cliquez sur une entrée pour voir chaque actif ou paire FX, son fournisseur et les prix modifiés (**Delta**).
  Survolez une erreur pour la lire en entier ; double-cliquez dessus (appui long sur un téléphone) pour la copier.
- Un élément reporté affiche une icône de pause et **Reporté : fournisseur en pause** : survolez le libellé pour lire
  le message du fournisseur. L'entrée compte les éléments reportés avec ⏸, à côté de ✓ et ✗ (par exemple
  `3/5 ✓ · 1 ⏸ · 1 ✗`), et **Nouvel essai à …** dans son en-tête donne l'heure prévue pour les réessayer.
- Filtrez par tâche, statut ou période, de la dernière heure aux 30 derniers jours. Seules les exécutions les plus récentes
  sont conservées.

---

## 🗄️ Caches du serveur {: #server-caches }

Pour rester rapide, LibreFolio garde en mémoire les réponses récentes des fournisseurs et les résultats calculés. Le
panneau **État du cache**, à la fin de la catégorie **Mémoire**, liste chaque cache avec sa
**Taille / Max** et son **TTL** (combien de temps une entrée est conservée). Cliquez sur un en-tête de colonne pour trier ;
**Actualiser** met à jour les chiffres.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Panneau des caches du serveur dans les Paramètres globaux (catégorie Mémoire)">
</div>

Tout le monde peut voir le panneau. Un administrateur, avec l'onglet déverrouillé, peut vider un cache avec
**Vider** ou tous les vider avec **Tout vider**, pour forcer des données fraîches sans redémarrage. Un redémarrage
vide aussi tous les caches.

!!! warning "Vider un cache ralentit la prochaine récupération"

    Les deux actions demandent d'abord une confirmation. Après un vidage, la prochaine requête pour ces données est renvoyée aux
    fournisseurs, donc attendez-vous à un ralentissement similaire à un redémarrage du serveur pendant que les caches se remplissent
    à nouveau.

??? note "🧵 Plusieurs workers — quand le serveur tourne avec `--workers`"

    Chaque processus worker a ses propres caches. Le panneau affiche, et vide, ceux du worker qui
    a répondu ; redémarrez le serveur pour tous les vider.

---

## 🔗 Voir aussi

- 📝 **[Variables d'environnement](configuration.md)** — Les paramètres qui vivent dans `.env` à la place
- 👤 **[Préférences utilisateur](../user/settings/preferences.md)** — Ce que chaque utilisateur peut modifier pour lui-même
- 🧑‍💻 Pour les développeurs : **[Système de paramètres](../developer/architecture/settings.md)**,
  **[Registre des caches](../developer/architecture/settings_cache.md)** et
  **[Planificateur de données de marché](../developer/backend/scheduler.md)**
