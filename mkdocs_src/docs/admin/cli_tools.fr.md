# 🛠️ Outils en ligne de commande

LibreFolio fournit le script `dev.py` pour les tâches d'administration. Cette page couvre les commandes les plus pertinentes pour les **administrateurs système**.

!!! tip "Contexte de l'environnement virtuel Python"

    Si vous exécutez LibreFolio directement sur la **machine hôte**, toutes les opérations en ligne de commande doivent être exécutées au sein de l'environnement virtuel Python. Vous pouvez soit préfixer chaque commande par `pipenv run` (par exemple, `pipenv run ./dev.py server`), soit entrer dans l'environnement virtuel une fois pour toutes en exécutant `pipenv shell`.

    Si vous êtes à l'intérieur du **terminal d'un conteneur Docker** (par exemple, via `docker exec`), vous **n'avez pas** besoin d'utiliser `pipenv run` ou `pipenv shell`, car les dépendances sont préinstallées globalement dans l'image du conteneur. Vous pouvez exécuter directement les commandes `./dev.py`.

!!! info "👩‍💻 Pour les développeurs"

    Pour les commandes spécifiques au développement (build frontend, lanceur de tests, synchronisation API, audit i18n), consultez le [Guide de Workflow pour les Développeurs](../developer/dev_workflow.md).

---
## 🖥️ Serveur (Production)

### ▶️ Démarrage du serveur

```bash
# Standard start
pipenv run ./dev.py server

# With auto-calculated workers (2 × (CPU-1))
pipenv run ./dev.py server --workers N

# Kill existing process on port before starting
pipenv run ./dev.py server --force
```

!!! tip "Multi-worker"

    Pour la production, utilisez `--workers` pour exécuter plusieurs workers Uvicorn. Cela améliore le débit et est recommandé pour tout déploiement disposant de plus d'un cœur CPU.

---

## 👤 Gestion des utilisateurs

La gestion des utilisateurs s'effectue via les sous-commandes `./dev.py user` :

```bash
# Create a user (first user becomes admin automatically)
pipenv run ./dev.py user create <username> <email> <password>

# List all users
pipenv run ./dev.py user list

# Reset a user's password
pipenv run ./dev.py user reset <username> <new_password>

# Promote a user to admin
pipenv run ./dev.py user promote <username>

# Demote an admin to regular user
pipenv run ./dev.py user demote <username>
```

---

## ⚙️ Gestion du système

### 🔧 Initialiser les paramètres globaux

```bash
pipenv run ./dev.py user init-settings
```

Remplit la base de données avec les [Paramètres globaux](settings.md) par défaut s'ils n'existent pas déjà.

### 🗄️ Migrations de la base de données

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade
```

!!! warning "🗄️ Réinitialisation de la base de données"

    `pipenv run ./dev.py db create-clean` recrée la base de données à partir de zéro — **toutes les données sont perdues**. À utiliser uniquement si vous avez besoin d'un nouveau départ.

---

## 📚 Documentation

```bash
# Build and deploy MkDocs documentation to GitHub Pages
pipenv run ./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
pipenv run ./dev.py mkdocs gallery
```

---

## 📋 Arborescence complète des commandes

Pour une liste complète de toutes les commandes disponibles :

```bash
pipenv run ./dev.py --help
```

!!! info "👩‍💻 Commandes développeurs"

    Commandes supplémentaires pour les flux de travail de développement :

    - **Frontend** : `pipenv run ./dev.py front build`, `front dev`, `front check` — voir [Développement Frontend](../developer/frontend/index.md)
    - **Tests** : `pipenv run ./dev.py test all` — voir [Parcours guidé des tests](../developer/test-walkthrough/index.md)
    - **Client API** : `pipenv run ./dev.py api sync` — voir [Aperçu de l'API](../developer/api/overview.md)
    - **i18n** : `pipenv run ./dev.py i18n audit` — voir [Internationalisation](../developer/frontend/i18n.md)
