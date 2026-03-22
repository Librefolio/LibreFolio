# ⚙️ Paramètres Système

LibreFolio dispose d'un ensemble de **paramètres système** qui affectent tous les utilisateurs. Ils sont gérés par les administrateurs et stockés dans la base de données.

---

## 👁️ Affichage et Modification des Paramètres

### 🖥️ Depuis l'Interface Utilisateur (UI)

1. Accédez à **Paramètres** (icône en forme d'engrenage dans la barre latérale)
2. Cliquez sur l'onglet **Paramètres système** (visible uniquement par les administrateurs/super-admin)
3. Cliquez sur l'**icône de cadenas** à côté d'un paramètre pour le déverrouiller pour l'édition
4. Modifiez la valeur, le changement est enregistré automatiquement

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Paramètres système" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! attention "Administrateurs uniquement"
 Seuls les utilisateurs avec des privilèges de **super-admin** peuvent modifier les paramètres système. Les utilisateurs réguliers voient une **vue en lecture seule**.

### 💻 Depuis la ligne de commande (CLI)

Pour initialiser les paramètres par défaut (ne crée que ceux qui sont absents) :

```bash
./dev.py user init-settings
```

---

## 📋 Paramètres Disponibles

| Clé | Type | Par Défaut | Description |
|-----|------|------------|-------------|
| `session_ttl_hours` | int | `24` | Durée d'expiration du jeton JWT en heures. Après cette période, les utilisateurs doivent se reconnecter. |
| `enable_registration` | bool | `true` | Si l'inscription de nouveaux utilisateurs est autorisée. Définissez sur `false` pour empêcher les nouvelles inscriptions. |
| `require_email_verification` | bool | `false` | Si les nouveaux utilisateurs doivent vérifier leur email avant d'accéder au système. |
| `max_file_upload_mb` | int | `10` | Taille maximale de téléversement de fichier en mégaoctets. S'applique à tous les téléversements (ressources statiques et rapports de courtage). |
| `auto_sync_fx_rates` | bool | `true` | Activer la synchronisation automatique quotidienne des taux de change (devises) depuis les fournisseurs configurés. |
| `auto_sync_prices` | bool | `true` | Activer la synchronisation automatique des **cours** des actifs depuis les fournisseurs (Yahoo Finance, etc.). |
| `price_sync_interval_hours` | int | `6` | **Intervalle** de synchronisation des cours des actifs, en heures. |
| `default_currency` | str | `EUR` | Devise d'affichage par défaut pour les nouveaux utilisateurs inscrits. Les utilisateurs peuvent la modifier dans leurs paramètres personnels. |
| `default_language` | str | `en` | Langue par défaut pour les nouveaux utilisateurs inscrits. **Codes langue pris en charge** : `en` (anglais), `it` (italien), `fr` (français), `es` (espagnol). |

---

## 🗂️ Catégories

Les paramètres sont regroupés en catégories dans l'interface utilisateur :

### 🕐 Session
- ⏱️ `session_ttl_hours` — Contrôle la durée d'une session de connexion

### 🛡️ Sécurité
- 📝 `enable_registration` — Ouvrir/fermer l'inscription
- ✉️ `require_email_verification` — Portail de vérification par email

### 📤 Synchronisation et Téléversements
- 💱 `auto_sync_fx_rates` — Synchronisation automatique des taux de change (devises)
- 📈 `auto_sync_prices` — Synchronisation automatique des cours des actifs
- ⏰ `price_sync_interval_hours` — Intervalle de synchronisation des cours
- 📦 `max_file_upload_mb` — Limite de taille de téléversement

### 🌍 Par Défaut
- 💰 `default_currency` — Devise par défaut pour les nouveaux utilisateurs
- 🗣️ `default_language` — Langue par défaut pour les nouveaux utilisateurs

---

## 🔧 Notes Techniques

- 🗃️ Les paramètres sont stockés sous forme de **paires clé-valeur** dans la table `global_settings`
- 🔀 Les valeurs sont stockées sous forme de chaînes et converties dans le type approprié (`int`, `bool`, `str`) lors de la lecture
- 🔒 Lors du démarrage multi-worker, les paramètres sont initialisés avec `INSERT ... ON CONFLICT DO NOTHING` pour éviter les **conditions de course (race conditions)**.
- ⚡ Les modifications prennent effet **immédiatement** — aucun redémarrage du serveur requis

---

## 📖 Notes du Traducteur
