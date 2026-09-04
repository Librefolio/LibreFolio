# 🛡️ Manuel de l'administrateur

Ce manuel est destiné aux administrateurs système et aux utilisateurs avancés qui doivent effectuer des opérations de maintenance, gérer les utilisateurs ou interagir avec le système via la ligne de commande.

## 📖 Aperçu

La plupart des tâches administratives et de maintenance sont gérées via l'interface en ligne de commande principale ou configurées à l'aide de variables d'environnement.

---

## 📚 Guides

La documentation est organisée en trois domaines principaux :

### 🐳 Déploiement et exposition
- 📦 **[Installation sur l'hôte](host_installation.md)** : installation manuelle utilisant Python, Node.js et Pipenv directement sur la machine hôte.
- 🐳 **[Docker avancé](docker_advanced.md)** : déploiement conteneurisé utilisant Docker Compose, les liaisons de volumes et la configuration de la propriété GID/UID de l'utilisateur.
- 🌐 **[Exposition sécurisée](service_exposure.md)** : exposez en toute sécurité votre instance privée LibreFolio sur Internet.

### ⚙️ Configuration système
- 📝 **[Variables d'environnement](configuration.md)** : liste complète des variables `.env` prises en charge (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) et précédence de résolution des variables.
- ⚙️ **[Paramètres globaux](settings.md)** : configurez les paramètres d'exécution à l'échelle du système (durée de vie des sessions (TTL), limites de téléversement, intervalles de synchronisation des données de marché).

### 🧹 Maintenance et opérations
- 🛠️ **[Outils d'administration en CLI](cli_tools.md)** : comment utiliser le script `dev.py` pour les tâches administratives (gestion des utilisateurs, mises à niveau de la base de données).
- 📂 **[Structure du système de fichiers](filesystem.md)** : détails sur l'emplacement des bases de données, des journaux, des téléversements et des dossiers temporaires, et sur la manière d'effectuer des sauvegardes.

---

## 🔔 Notifications de mise à jour {: #update-notifications }

Après chaque connexion, le navigateur d'un **administrateur** interroge l'API GitHub Releases à la recherche d'une version **stable** plus récente de LibreFolio (les brouillons et les préversions ne sont jamais pris en compte). Pour rester discret :

- La vérification s'exécute **au plus une fois toutes les 24 heures** — le dernier résultat est mis en cache dans le stockage local du navigateur.
- Les installations auto-hébergées sans accès à Internet échouent simplement, en silence, à récupérer les données : **aucune erreur, aucune bannière**.

Lorsqu'une version stable plus récente existe, une **modale « Mise à jour disponible »** apparaît, affichant côte à côte la version actuelle et la plus récente, avec des liens vers le **[guide de mise à jour](../user/installation.md#updating)** et vers la page des versions GitHub. Deux façons de la fermer :

- **« Plus tard »** — la modale se ferme et réapparaîtra lors de la prochaine connexion.
- **« Ignorer cette version »** — la modale ne proposera plus jamais cette version spécifique (une version future plus récente sera toujours annoncée).

Les utilisateurs non administrateurs ne sont jamais interrogés lors de la connexion. Si un non-administrateur vérifie manuellement les mises à jour depuis la [modale du journal des modifications](../user/settings/about.md#changelog-modal) et qu'une version plus récente existe, il voit à la place une boîte de dialogue listant les administrateurs de l'instance (avec leurs adresses e-mail lorsque disponibles), afin qu'il sache à qui demander la mise à niveau.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Modale de mise à jour disponible avec la version actuelle et la dernière version">
</div>

---

## 🔐 Authentification et persistance des sessions

LibreFolio utilise **JWT (JSON Web Tokens)** pour l'authentification des utilisateurs. Par défaut :
- Si la variable d'environnement **`JWT_SECRET`** est laissée vide dans votre fichier `.env`, le serveur génère un secret de signature aléatoire au démarrage. Cela offre une sécurité maximale, mais les sessions utilisateur seront perdues si le serveur est redémarré.
- Pour conserver les sessions lors des redémarrages du serveur (ou lors de l'exécution de plusieurs instances de serveur indépendantes derrière un équilibreur de charge), définissez une clé **`JWT_SECRET`** stable. Notez que plusieurs workers uvicorn démarrés sur le même hôte partageront automatiquement le secret généré par le processus parent, ce qui signifie que la persistance des sessions est maintenue entre les workers même lorsque `JWT_SECRET` est laissée vide.

Pour les détails techniques, consultez la page [Architecture de sécurité](../developer/architecture/security.md) destinée aux développeurs.
