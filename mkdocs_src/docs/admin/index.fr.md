# 🛡️ Manuel d'administration

Ce manuel s'adresse aux personnes qui installent et exploitent LibreFolio. La plupart des tâches d'administration s'effectuent depuis la ligne de commande, via des variables d'environnement, ou dans l'onglet **Admin** des paramètres de l'application.

---

## 📚 Guides

### 🐳 Déploiement et exposition
- 📦 **[Installation sur l'hôte](host_installation.md)** : configuration manuelle avec Python, Node.js et Pipenv directement sur la machine hôte.
- 🐳 **[Docker avancé](docker_advanced.md)** : déploiement conteneurisé avec Docker Compose, montages de volumes et configuration de la propriété GID/UID de l'utilisateur.
- 🌐 **[Exposer en toute sécurité](service_exposure.md)** : exposez en toute sécurité votre instance privée LibreFolio sur Internet.

### ⚙️ Configuration système
- 📝 **[Variables d'environnement](configuration.md)** : liste complète des variables `.env` prises en charge (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.) et priorité de résolution des variables.
- ⚙️ **[Paramètres globaux](settings.md)** : configurez les paramètres d'exécution à l'échelle du système (TTL de session, limites de téléversement, intervalles de synchronisation des données de marché).

### 🧹 Maintenance et opérations
- 🛠️ **[Outils d'administration CLI](cli_tools.md)** : comment utiliser le script `dev.py` pour les tâches administratives (gestion des utilisateurs, mises à niveau de la base de données).
- 📂 **[Structure du système de fichiers](filesystem.md)** : détails sur l'emplacement de stockage des bases de données, journaux, téléversements et dossiers temporaires, et comment effectuer des sauvegardes.

---

## 🔔 Notifications de mise à jour {: #update-notifications }

Lorsqu'un administrateur se connecte, LibreFolio vérifie sur GitHub la présence d'une version **stable** plus récente. Si c'est le cas, la fenêtre **Nouvelle version disponible** affiche votre version et la dernière version côte à côte, avec un lien **Comment mettre à jour** vers le [guide de mise à jour](../user/installation.md#updating) et un lien **Notes de version sur GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Fenêtre modale de mise à jour disponible avec la version actuelle et la dernière version">
</div>

- **Me le rappeler plus tard** ferme la fenêtre jusqu'à une prochaine connexion.
- **Ignorer cette version** désactive l'invite automatique pour cette version ; une version plus récente sera à nouveau annoncée.
- Une version n'est annoncée qu'une fois son image Docker téléchargeable, et la fenêtre attend qu'aucune autre fenêtre ni guide ne soit ouvert.
- Sans accès à Internet, la vérification automatique échoue silencieusement : aucune erreur, aucune bannière.
- Pour vérifier immédiatement, utilisez **Rechercher des mises à jour** dans le [journal des modifications](../user/settings/about.md#changelog-modal) : cette vérification signale les erreurs, ainsi que les versions que vous avez ignorées.

??? note "👥 Autres utilisateurs — lorsqu'une personne qui n'est pas administratrice effectue une vérification"

    Pour les utilisateurs qui ne sont pas administrateurs, aucune vérification n'est effectuée à la connexion. Si l'un d'eux lance
    **Rechercher des mises à jour** et qu'une version plus récente existe, la
    boîte de dialogue **Mise à jour disponible — contactez un administrateur** liste les administrateurs, avec leurs
    adresses e-mail lorsqu'elles sont disponibles, afin que ces utilisateurs sachent à qui s'adresser.

---

## 🔐 Maintenir les utilisateurs connectés après un redémarrage {: #session-persistence }

LibreFolio signe chaque session de connexion avec une clé secrète, `JWT_SECRET`.

- **Non définie** (par défaut) : une nouvelle clé aléatoire est générée à chaque démarrage, donc tout le monde doit se reconnecter après un redémarrage ou une mise à jour.
- **Définie** : les sessions survivent aux redémarrages. Définissez-la aussi si plusieurs serveurs LibreFolio distincts partagent les mêmes utilisateurs derrière un répartiteur de charge.

### 🔑 1. Générer une clé

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Vous n'avez pas Python sur l'hôte ? Exécutez-le plutôt dans le conteneur :

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. Ajoutez-la à `.env` et redémarrez

```bash
JWT_SECRET=paste-the-generated-value-here
```

Redémarrez LibreFolio (avec Docker Compose : `docker compose up -d`). Gardez cette clé secrète : quiconque la connaît peut falsifier une session.

Les workers d'une même commande `./dev.py server --workers …` partagent une seule clé d'eux-mêmes. La durée d'une session est définie par la **Durée de session** dans les [Paramètres globaux](settings.md). Pour les détails, consultez la page développeur [Architecture de sécurité](../developer/architecture/security.md).
