# ⚙️ Paramètres Globaux

LibreFolio dispose d'un ensemble de **paramètres système** qui affectent tous les utilisateurs. Ceux-ci sont gérés par les administrateurs et stockés dans la base de données.

---

## 👁️ Visualisation et Modification des Paramètres

### 🖥️ Depuis l'interface utilisateur (UI)

1. Naviguez vers **Paramètres** (icône d'engrenage dans la barre latérale)
2. Cliquez sur l'onglet **Paramètres globaux** (visible uniquement pour l'admin/superuser)
3. Cliquez sur l'**icône de cadenas** à côté d'un paramètre pour le déverrouiller et le modifier
4. Modifiez la valeur et la modification est enregistrée automatiquement

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Paramètres Globaux" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! warning "Administrateurs Uniquement"

    Seuls les utilisateurs disposant des privilèges **superuser** peuvent modifier les paramètres globaux. Les utilisateurs réguliers voient une vue en lecture seule.

### 💻 Depuis l'interface de ligne de commande (CLI)

Pour initialiser les paramètres par défaut (crée uniquement ceux manquants) :

```bash
./dev.py user init-settings
```

---

## 📋 Paramètres Disponibles

| Clé | Type | Par défaut | Description |
|-----|------|---------|-------------|
| `session_ttl_hours` | int | `24` | Temps d'expiration du jeton JWT en heures. Après cette période, les utilisateurs doivent se reconnecter. |
| `enable_registration` | bool | `true` | Indique si l'inscription de nouveaux utilisateurs est autorisée. Réglez sur `false` pour empêcher les nouvelles inscriptions. |
| `require_email_verification` | bool | `false` | Indique si les nouveaux utilisateurs doivent vérifier leur e-mail avant d'accéder au système. |
| `max_file_upload_mb` | int | `10` | Taille maximale de téléchargement de fichier en mégaoctets. S'applique à tous les téléchargements (ressources statiques et rapports de courtier). |
| `scheduler_enabled` | bool | `true` | Active ou désactive le démon de synchronisation automatique en arrière-plan pour les taux de change et les prix historiques/temps réel. |
| `scheduler_current_price_frequency_minutes` | int | `10` | Fréquence (en minutes) avec laquelle le démon rafraîchit les prix actuels en temps réel (1-1440). |
| `scheduler_history_sync_times` | str | `06:00,23:00` | Heures quotidiennes spécifiques (heure locale du serveur, séparées par des virgules) pour déclencher la synchronisation historique de clôture. |
| `scheduler_history_sync_days` | str | `mon,tue,wed,thu,fri,sat` | Jours spécifiques de la semaine (séparés par des virgules) pour exécuter la synchronisation historique. |
| `scheduler_history_sync_horizon_days` | int | `14` | Fenêtre d'analyse rétrospective glissante (en jours) utilisée pour vérifier s'il manque des prix historiques. |
| `default_currency` | str | `EUR` | Devise d'affichage par défaut pour les nouveaux utilisateurs inscrits. Les utilisateurs peuvent modifier cela dans leurs paramètres personnels. |
| `default_language` | str | `en` | Langue par défaut pour les nouveaux utilisateurs inscrits. Supportées : `en`, `it`, `fr`, `es`. |

---

## 🗂️ Catégories

Les paramètres sont regroupés par catégories dans l'UI :

### 🕐 Session
- ⏱️ `session_ttl_hours` — Contrôle la durée d'une session de connexion

### 🛡️ Sécurité
- 📝 `enable_registration` — Ouvrir/fermer les inscriptions
- ✉️ `require_email_verification` — Validation de l'e-mail obligatoire

### 📤 Synchronisation et Téléchargements
- 🕐 `scheduler_enabled` — Activer ou désactiver le planificateur en arrière-plan
- ⚡ `scheduler_current_price_frequency_minutes` — Fréquence de rafraîchissement des prix en temps réel
- 📅 `scheduler_history_sync_times` — Heures de synchronisation historique quotidienne
- 📅 `scheduler_history_sync_days` — Jours de synchronisation historique hebdomadaire
- 🔍 `scheduler_history_sync_horizon_days` — Horizon d'analyse de synchronisation historique (en jours)
- 📦 `max_file_upload_mb` — Limite de taille de fichier

### 🌍 Valeurs par Défaut
- 💰 `default_currency` — Devise par défaut des nouveaux utilisateurs
- 🗣️ `default_language` — Langue par défaut des nouveaux utilisateurs

---

## 🕐 Planificateur de Données de Marché (Scheduler)

Lorsque le planificateur en arrière-plan est activé, les administrateurs peuvent configurer les paramètres de synchronisation et inspecter les journaux d'exécution directement depuis l'interface utilisateur.

### ⚙️ Configurer le Planificateur

Cliquez sur le bouton **Configurer** dans la ligne du Planificateur pour personnaliser les fréquences d'exécution et les paramètres :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale de Configuration du Planificateur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

* **Current Price Frequency** : La fréquence (en minutes) à laquelle le démon récupère les cours en temps réel pour maintenir à jour le cache du tableau de bord (par défaut : 10m).
* **History Sync Times** : Heures spécifiques de la journée (séparées par des virgules, ex: `06:00,23:00`) pour exécuter les mises à jour historiques de clôture quotidienne.
* **History Sync Days** : Jours spécifiques de la semaine pendant lesquels la synchronisation historique est effectuée (généralement du lundi au samedi).
* **History Horizon** : La fenêtre d'analyse (en jours) pour vérifier d'éventuels points de prix historiques manquants (par défaut : 14 jours).

### 📜 Journaux du Planificateur

Cliquez sur **Afficher les Journaux** pour ouvrir l'inspecteur des journaux. Cette modale affiche la liste des exécutions récentes du planificateur :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale Journaux du Planificateur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Le journal indique l'horodatage d'exécution, le nom de la tâche, le statut (Success/Error), la durée d'exécution et les détails structurés des actifs traités, les flux de prix et les éventuelles traces d'erreur.

---

## 🔧 Notes Techniques

- 🗃️ Les paramètres sont stockés sous forme de **paires clé-valeur** dans la table `global_settings`
- 🔀 Les valeurs sont stockées en tant que chaînes de caractères et converties vers le type approprié (`int`, `bool`, `str`) lors de la lecture
- 🔒 Lors d'un démarrage multi-worker, les paramètres sont initialisés avec `INSERT ... ON CONFLICT DO NOTHING` pour éviter les conditions de concurrence
- ⚡ Les changements prennent effet **immédiatement** — aucun redémarrage du serveur n'est requis
