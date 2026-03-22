# 🛠️ Outils en ligne de commande

LibreFolio fournit le script `dev.py` pour les tâches d'administration. Cette page couvre les commandes les plus pertinentes pour les **administrateurs système**.

!!! info "👩‍💻 Pour les développeurs"
    Pour les commandes spécifiques au développement (build frontend, exécuteur de tests, synchronisation API, audit i18n), consultez le [Guide d'installation pour développeurs](../developer/dev-installation.md).

---

## 🚀 Installation

Installer toutes les dépendances du projet (Python et Node.js) :

```bash
./dev.py install
```

---

## 🖥️ Serveur (Production)

### ▶️ Démarrer le serveur

```bash
# Démarrage standard
./dev.py server

# Avec des workers calculés automatiquement (2 × (CPU-1))
./dev.py server --workers N

# Termine le processus existant sur le port avant de démarrer
./dev.py server --force
```

!!! tip "Multi-worker"
    En production, utilisez `--workers` pour exécuter plusieurs workers Uvicorn. Cela améliore le débit et est recommandé pour tout déploiement avec plus d'un cœur de CPU.

---

## 👤 Gestion des utilisateurs

La gestion des utilisateurs se fait via les sous-commandes `./dev.py user` :

```bash
# Créer un utilisateur (le premier utilisateur devient automatiquement administrateur)
./dev.py user create <nom_utilisateur> <email> <mot_de_passe>

# Lister tous les utilisateurs
./dev.py user list

# Réinitialiser le mot de passe d'un utilisateur
./dev.py user reset <nom_utilisateur> <nouveau_mot_de_passe>

# Promouvoir un utilisateur au rang d'administrateur
./dev.py user promote <nom_utilisateur>

# Rétrograder un administrateur en utilisateur standard
./dev.py user demote <nom_utilisateur>
```

---

## ⚙️ Gestion système

### 🔧 Initialiser les paramètres globaux

```bash
./dev.py user init-settings
```

Remplit la base de données avec les [Paramètres Globaux](settings.md) par défaut s'ils n'existent pas déjà.

### 🗄️ Migrations de base de données

```bash
# Appliquer les migrations en attente
./dev.py db upgrade
```

!!! warning "🗄️ Réinitialisation de la base de données"
    `./dev.py db create-clean` recrée la base de données à partir de zéro — **toutes les données sont perdues**. À utiliser uniquement si vous avez besoin de partir de zéro.

---

## 📚 Documentation

```bash
# Générer et déployer la documentation MkDocs sur GitHub Pages
./dev.py mkdocs deploy

# Générer les captures d'écran de la galerie (nécessite un serveur en cours d'exécution + des données de test)
./dev.py mkdocs gallery
```

---

## 📋 Arborescence complète des commandes

Pour une liste complète de toutes les commandes disponibles :

```bash
./dev.py --help
```

!!! info "👩‍💻 Commandes développeur"
    Commandes supplémentaires pour les workflows de développement :

    - **Frontend** : `./dev.py front build`, `front dev`, `front check` — voir [Développement frontend](../developer/frontend/index.md)
    - **Tests** : `./dev.py test all` — voir [Parcours des tests](../developer/test-walkthrough/index.md)
    - **Client API** : `./dev.py api sync` — voir [Vue d'ensemble de l'API](../developer/api/overview.md)
    - **i18n** : `./dev.py i18n audit` — voir [Internationalisation](../developer/frontend/i18n.md)

