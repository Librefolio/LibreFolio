# 🐳 Guide Docker Avancé

Ce guide propose un examen plus approfondi de la configuration Docker pour LibreFolio, destiné aux utilisateurs qui souhaitent personnaliser leur déploiement.

## 📄 `docker-compose.yml`

Le fichier `docker-compose.yml` définit les services, réseaux et volumes pour l'application.

### 🔧 Services

- **`backend`** : L'application principale FastAPI.
 - 🏗️ **`build`** : Spécifie le Dockerfile à la racine du projet.
 - 🔌 **`ports`** : Mappe le port hôte (défini par `${PORT}` dans `.env`) vers le port 8000 du conteneur.
 - 📂 **`volumes`** :
 - `./backend:/app/backend` : Monte le code source backend pour le développement (permet le rechargement à chaud).
 - `./frontend/build:/app/frontend/build` : Monte la build de production du frontend.
 - `./mkdocs_src/site:/app/mkdocs_src/site` : Monte le site de documentation.
 - `./logs:/app/logs` : Monte le répertoire `./logs` de l'hôte dans le conteneur pour stocker les fichiers de logs de manière persistante.
 - 🌍 **`env_file`** : Charge les variables d'environnement à partir du fichier `.env`.

### 💾 Volumes

- **`libre-folio-data`** : Un volume nommé utilisé pour persister les fichiers de la base de données SQLite. Cela garantit que vos données ne sont pas perdues lorsque vous arrêtez ou supprimez les conteneurs.

### 🌐 Réseaux

- **`libre-folio-net`** : Un réseau bridge personnalisé pour permettre aux services de communiquer entre eux.

## 🏭 Considérations pour la Production

Pour un déploiement en production, vous pourriez envisager les modifications suivantes :

### 🔒 1. Reverse Proxy

Il est fortement recommandé d'exécuter LibreFolio derrière un reverse proxy comme **Nginx** ou **Traefik**. Cela vous permet de :

- 🔐 Gérer facilement les certificats SSL/TLS pour HTTPS.
- 🖥️ Servir plusieurs applications sur le même serveur.
- 🛡️ Ajouter des en-têtes de sécurité et une limitation de débit.

### 💾 2. Sauvegarde de la Base de Données

Étant donné que la base de données est stockée dans un volume Docker, vous devriez avoir une stratégie pour la sauvegarder. Vous pouvez utiliser une simple tâche `cron` pour copier le fichier de la base de données depuis le volume vers un emplacement sûr.

Exemple de script de sauvegarde :

```bash
#!/bin/bash
docker cp librefolio_backend_1:/app/backend/data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

### 🚫 3. Désactivation des Montages de Développement

Dans un environnement de production, il peut être préférable de ne pas monter directement le code source. Vous pouvez créer un fichier `docker-compose.prod.yml` séparé qui ne définit pas les volumes de code source et utilise uniquement l'image Docker construite.
