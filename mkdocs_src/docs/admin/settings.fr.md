# ⚙️ Paramètres globaux

LibreFolio dispose d'un ensemble de **paramètres à l'échelle du système** qui affectent tous les utilisateurs. Ils sont gérés par les administrateurs et stockés dans la base de données.

---

## 👁️ Affichage et modification des paramètres

### 🖥️ Depuis l'interface

1. Accédez à **Paramètres** (icône d'engrenage dans la barre latérale)
2. Cliquez sur l'onglet **Paramètres globaux** (visible pour tous les utilisateurs ; seuls les administrateurs/superutilisateurs peuvent modifier)
3. Cliquez sur l'**icône de cadenas** à côté d'un paramètre pour le déverrouiller et le modifier
4. Modifiez la valeur : elle est enregistrée automatiquement

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Global Settings" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Administrateurs uniquement"

    Seuls les utilisateurs disposant des privilèges **superutilisateur** peuvent modifier les paramètres globaux. Les utilisateurs ordinaires voient une vue en lecture seule.

### 💻 Depuis la CLI

Pour initialiser les paramètres par défaut (ne crée que ceux qui manquent) :

```bash
./dev.py user init-settings
```

---

## 🕐 Session

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `session_ttl_hours` | int | `24` | Temps d'expiration du jeton JWT en heures. Passé ce délai, les utilisateurs doivent se reconnecter. |

## 🛡️ Sécurité

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `enable_registration` | bool | `true` | Indique si l'inscription de nouveaux utilisateurs est autorisée. Définissez sur `false` pour empêcher de nouvelles inscriptions. |
| `require_email_verification` | bool | `false` | **Provisoire — pas encore appliqué.** Indique si les nouveaux utilisateurs doivent vérifier leur e-mail avant d'accéder au système. L'envoi d'e-mails (SMTP) est une fonctionnalité prévue ; dans l'interface, ce paramètre est donc en lecture seule et porte un badge « Bientôt disponible ». |

## 🔄 Tâche de mise à jour

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `scheduler_enabled` | bool | `true` | Active ou désactive le démon de synchronisation automatique en arrière-plan pour les taux de change et les prix historiques/temps réel. |

Les paramètres restants du planificateur ne sont pas affichés sous forme de champs individuels : ils sont modifiés ensemble depuis la fenêtre modale **Configurer** de la ligne du planificateur — voir [Planificateur des données de marché](#market-data-scheduler) ci-dessous.

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `scheduler_current_price_frequency_minutes` | int | `10` | Fréquence (en minutes) à laquelle le démon met à jour les prix actuels en temps réel (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Heures HH:MM séparées par des virgules pour la synchronisation quotidienne de l'historique, exprimées **dans le `scheduler_timezone` configuré**. Les heures sont stockées telles que saisies (heure locale) ; le démon ne convertit chaque créneau local en un instant UTC que lorsqu'il décide si une tâche est due. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Jours spécifiques de la semaine (séparés par des virgules) pour exécuter la synchronisation historique. |
| `scheduler_history_sync_horizon_days` | int | `14` | Fenêtre d'analyse rétrospective glissante (en jours) utilisée pour détecter les prix historiques manquants. |
| `scheduler_timezone` | str | `UTC` | Fuseau horaire IANA utilisé pour **stocker et évaluer** les jours et heures de synchronisation de l'historique. Les heures/jours que vous configurez sont exprimés dans ce fuseau ; les valeurs invalides reviennent à UTC. |

## 🧠 Mémoire

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `max_file_upload_mb` | int | `10` | Taille maximale de téléversement de fichiers en mégaoctets. S'applique à tous les téléversements (ressources statiques et rapports de courtier). |

La catégorie Mémoire héberge également le panneau **Caches serveur** — voir [Caches serveur](#server-caches) ci-dessous.

## 🌍 Valeurs par défaut

| Clé | Type | Défaut | Description |
|-----|------|--------|-------------|
| `default_currency` | str | `EUR` | Devise d'affichage par défaut pour les nouveaux utilisateurs enregistrés. Les utilisateurs peuvent la remplacer dans leurs paramètres personnels. |
| `default_language` | str | `en` | Langue par défaut pour les nouveaux utilisateurs enregistrés. Langues prises en charge : 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr`, 🇪🇸 `es`. |
| `default_theme` | str | `auto` | Thème par défaut pour les nouveaux utilisateurs enregistrés : ☀️ `light`, 🌙 `dark`, 🖥️ `auto`. |

---

## 🕐 Planificateur des données de marché {: #market-data-scheduler }

Lorsque le planificateur en arrière-plan est activé, les administrateurs peuvent configurer les paramètres de synchronisation et inspecter les journaux d'exécution en arrière-plan directement depuis l'interface utilisateur.

### ⚙️ Configurer le planificateur

Cliquez sur le bouton **Configurer** dans la ligne du planificateur pour personnaliser les fréquences et les paramètres d'exécution :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Scheduler Configuration Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Fréquence des prix actuels** : la fréquence (en minutes) à laquelle le démon récupère les cotations en temps réel pour maintenir le cache du tableau de bord à jour (défaut : 10 min).
* **Heures de synchronisation de l'historique** : heures quotidiennes spécifiques (séparées par des virgules, p. ex. `06:00,23:00`) pour exécuter les mises à jour quotidiennes des clôtures historiques. Les heures sont des heures locales **dans le fuseau horaire du planificateur configuré**.
* **Jours de synchronisation de l'historique** : jours spécifiques de la semaine où la synchronisation historique est effectuée (généralement du lundi au samedi), également évalués dans le fuseau horaire du planificateur.
* **Horizon de l'historique** : fenêtre d'analyse (en jours) pour détecter les points de prix historiques manquants (défaut : 14 jours).
* **Fuseau horaire** : le fuseau horaire IANA (`scheduler_timezone`) dans lequel les heures et les jours ci-dessus sont stockés et évalués. La fenêtre modale affiche également l'horloge UTC du serveur, afin que vous puissiez apprécier le décalage ; le backend ne convertit chaque créneau local en un instant UTC que lorsqu'il décide si une tâche est due. Les valeurs invalides reviennent à UTC.

### 📜 Journaux du planificateur

Cliquez sur **Voir les journaux** pour ouvrir l'inspecteur de journaux. Cette fenêtre modale affiche une liste des exécutions récentes du planificateur :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Scheduler Log Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le journal indique l'horodatage de l'exécution, le nom de la tâche, le statut (Succès/Erreur), la durée d'exécution et des détails structurés sur les actifs traités, les flux de prix et toute trace d'erreur.

---

## 🗄️ Caches serveur {: #server-caches }

LibreFolio conserve plusieurs **caches en mémoire** côté backend (récupérations de prix, résultats de recherche, calculs de portefeuille, réponses des fournisseurs, etc.) afin que les demandes répétées ne sollicitent pas les fournisseurs de données externes à chaque fois. L'onglet **Paramètres globaux** se termine par un **panneau des caches** (catégorie Mémoire) qui répertorie chaque cache enregistré par nom, avec ses colonnes **taille actuelle / taille maximale** et **TTL** (durée de vie) — chaque en-tête de colonne est cliquable pour trier par nom, taille ou TTL ; un bouton **Actualiser** recharge les statistiques en direct.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Server caches panel in Global Settings (Memory category)">
</div>

**Qui peut faire quoi :**

- 👁️ **La lecture de l'état** est disponible pour **tout utilisateur authentifié** (`GET /api/v1/settings/cache/status`).
- 🧹 **Le vidage** est **réservé aux administrateurs et nécessite que la page soit déverrouillée** (les boutons n'apparaissent que pour les superutilisateurs en mode édition) : chaque ligne possède son propre bouton **Vider** (`POST /api/v1/settings/cache/clear/{name}`), et l'en-tête du panneau comporte un bouton **Tout vider** (`POST /api/v1/settings/cache/clear-all`).

!!! warning "Vider un cache ralentit la prochaine récupération"

    Les deux actions de vidage demandent une confirmation, et pour cause : après un vidage, la prochaine demande pour ces données **sollicite à nouveau les fournisseurs externes**, attendez-vous donc à un ralentissement comparable à un redémarrage du serveur pendant que les caches se remplissent. Les caches se vident également à chaque redémarrage du serveur — le vidage n'est utile que pour forcer l'obtention de données fraîches sans redémarrer.

---

## 🔧 Notes techniques

- 🗃️ Les paramètres sont stockés sous forme de **paires clé-valeur** dans la table `global_settings`
- 🔀 Les valeurs sont stockées sous forme de chaînes et converties au type approprié (`int`, `bool`, `str`) à la lecture
- 🔒 Au démarrage multi-workers, les paramètres sont initialisés avec `INSERT ... ON CONFLICT DO NOTHING` pour éviter les conditions de concurrence
- ⚡ Les modifications prennent effet **immédiatement** — aucun redémarrage du serveur n'est requis
