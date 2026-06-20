# 🛠️ Outils en ligne de commande

LibreFolio fournit le script `dev.py` pour les tâches d'administration. Cette page couvre les commandes les plus pertinentes pour les **administrateurs système**.

!!! info "👩‍💻 Pour les développeurs"

    Pour les commandes spécifiques au développement (build frontend, lanceur de tests, synchronisation API, audit i18n), consultez le [Guide de Workflow pour les Développeurs](../developer/dev_workflow.md).

---
## 🖥️ Serveur (Production)

### ▶️ Démarrage du serveur

```bash
# Standard start
./dev.py server

# With auto-calculated workers (2 × (CPU-1))
./dev.py server --workers N

# Kill existing process on port before starting
./dev.py server --force
```

!!! tip "Multi-worker"

    Pour la production, utilisez `--workers` pour exécuter plusieurs workers Uvicorn. Cela améliore le débit et est recommandé pour tout déploiement disposant de plus d'un cœur CPU.

---

## 👤 Gestion des utilisateurs

La gestion des utilisateurs s'effectue via les sous-commandes `./dev.py user` :

```bash
# Create a user (first user becomes admin automatically)
./dev.py user create <username> <email> <password>

# List all users
./dev.py user list

# Reset a user's password
./dev.py user reset <username> <new_password>

# Promote a user to admin
./dev.py user promote <username>

# Demote an admin to regular user
./dev.py user demote <username>
```

---

## ⚙️ Gestion du système

### 🔧 Initialiser les paramètres globaux

```bash
./dev.py user init-settings
```

Remplit la base de données avec les [Paramètres globaux](settings.md) par défaut s'ils n'existent pas déjà.

### 🗄️ Migrations de la base de données

```bash
# Apply pending migrations
./dev.py db upgrade
```

!!! warning "🗄️ Réinitialisation de la base de données"

    `./dev.py db create-clean` recrée la base de données à partir de zéro — **toutes les données sont perdues**. À utiliser uniquement si vous avez besoin d'un nouveau départ.

---

## 📚 Documentation

```bash
# Build and deploy MkDocs documentation to GitHub Pages
./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
./dev.py mkdocs gallery
```

---

## 📋 Arborescence complète des commandes

Pour une liste complète de toutes les commandes disponibles :

```bash
./dev.py --help
```

!!! info "👩‍💻 Commandes développeurs"

    Commandes supplémentaires pour les flux de travail de développement :

    - **Frontend** : `./dev.py front build`, `front dev`, `front check` — voir [Développement Frontend](../developer/frontend/index.md)
    - **Tests** : `./dev.py test all` — voir [Parcours guidé des tests](../developer/test-walkthrough/index.md)
    - **Client API** : `./dev.py api sync` — voir [Aperçu de l'API](../developer/api/overview.md)
    - **i18n** : `./dev.py i18n audit` — voir [Internationalisation](../developer/frontend/i18n.md)
