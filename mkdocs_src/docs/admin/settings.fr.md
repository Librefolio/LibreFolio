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
| `auto_sync_fx_rates` | bool | `true` | Active la synchronisation quotidienne automatique des taux de change FX à partir des fournisseurs configurés. |
| `auto_sync_prices` | bool | `true` | Active la synchronisation automatique des prix des actifs à partir des fournisseurs (Yahoo Finance, etc.). |
| `price_sync_interval_hours` | int | `6` | Fréquence de synchronisation des prix des actifs, en heures. |
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
- 💱 `auto_sync_fx_rates` — Synchronisation automatique des taux de change
- 📈 `auto_sync_prices` — Synchronisation automatique des prix des actifs
- ⏰ `price_sync_interval_hours` — Fréquence de synchronisation des prix
- 📦 `max_file_upload_mb` — Limite de taille de fichier

### 🌍 Valeurs par Défaut
- 💰 `default_currency` — Devise par défaut des nouveaux utilisateurs
- 🗣️ `default_language` — Langue par défaut des nouveaux utilisateurs

---

## 🔧 Notes Techniques

- 🗃️ Les paramètres sont stockés sous forme de **paires clé-valeur** dans la table `global_settings`
- 🔀 Les valeurs sont stockées en tant que chaînes de caractères et converties vers le type approprié (`int`, `bool`, `str`) lors de la lecture
- 🔒 Lors d'un démarrage multi-worker, les paramètres sont initialisés avec `INSERT ... ON CONFLICT DO NOTHING` pour éviter les conditions de concurrence
- ⚡ Les changements prennent effet **immédiatement** — aucun redémarrage du serveur n'est requis
