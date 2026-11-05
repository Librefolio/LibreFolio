# 🛡️ Manuel d'administration

Ce manuel s'adresse aux personnes qui installent et exploitent LibreFolio. L'essentiel de l'administration se fait depuis la ligne de commande, via des variables d'environnement, ou dans les onglets **Paramètres › Administration** de l'application.

---

## 📚 Guides

### 🐳 Déploiement et exposition
- 📦 **[Installation sur l'hôte](host_installation.md)** : installation manuelle avec Python, Node.js et Pipenv directement sur la machine hôte.
- 🐳 **[Docker avancé](docker_advanced.md)** : déploiement conteneurisé avec Docker Compose, montages de volumes et configuration de la propriété GID/UID de l'utilisateur.
- 🌐 **[Exposer en toute sécurité](service_exposure.md)** : exposez en toute sécurité votre instance LibreFolio privée avec Tailscale, sans ouvrir de port sur le routeur : pourquoi c'est préférable à la redirection de port, et les niveaux d'accès privé, un VPN pour vos propres appareils ou un routeur de sous-réseau pour tout votre réseau domestique.
    - 🌍 **[Exposer en toute sécurité : accès public avec Funnel](service_exposure_funnel.md)** : une adresse HTTPS publique avec Tailscale Funnel : activer Funnel et les ACL, une adresse pour LibreFolio, ou une pour chaque service avec Docker.
- 🔍 **[Vérifier la sécurité de la connexion](connection_checks.md)** : vérifiez que vos utilisateurs se connectent de manière sécurisée : la liste de contrôle, l'indicateur, la vue du serveur et le cookie de session, et que faire lorsqu'une vérification échoue.
    - 🧰 **[Vérifier la sécurité de la connexion : derrière un reverse proxy](connection_proxy.md)** : exécutez LibreFolio derrière Nginx, Caddy, Traefik ou Tailscale : les en-têtes à envoyer, le proxy auquel LibreFolio fait confiance et l'adresse du visiteur.

### ⚙️ Configuration du système
- 📝 **[Variables d'environnement](configuration.md)** : créez le fichier `.env` et découvrez les principales variables prises en charge (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.), avec la priorité qui détermine quelle valeur l'emporte.
    - 🔐 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** : les secrets et comment les lire depuis des fichiers tels que les secrets Docker, la clé de l'instance, et les paramètres et clés d'API des plugins.
    - 🛡️ **[Configuration : vérifications et protections](configuration_security.md)** : ce que LibreFolio vérifie au démarrage, la Content-Security-Policy et la protection contre l'encadrement, et comment le serveur s'arrête.
    - 👥 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** : qui peut s'inscrire, les limites de comptes et de tentatives de connexion échouées, l'administrateur initial, et l'ordre des fournisseurs de prix dans la recherche d'actifs.
- 📧 **[E-mail](email.md)** : e-mail SMTP facultatif : les variables, des exemples pour les serveurs habituels, et l'onglet **E-mail** de Paramètres › Administration avec son e-mail de test.
    - 📬 **[E-mail : liens et messages](email_flows.md)** : les e-mails contenant un lien, les invitations et les réinitialisations de mot de passe, les mots de passe oubliés et leurs limites, la vérification de l'adresse e-mail et la notification d'un changement d'adresse e-mail.
    - 🛠️ **[E-mail : quand ça ne fonctionne pas](email_troubleshooting.md)** : les erreurs, ce que dit le journal, et les notes de sécurité de la configuration SMTP.
- ⚙️ **[Paramètres globaux](settings.md)** : configurez les paramètres d'exécution à l'échelle du système (TTL de session, limites de téléversement, intervalles de synchronisation des données de marché), repérez-vous dans les onglets **Administration** des Paramètres, et consultez les vérifications de **Sécurité** de l'instance.
- 👥 **[Utilisateurs et invitations](users.md)** : gérez les comptes de l'instance depuis l'onglet **Utilisateurs** de l'application : invitations, liens de réinitialisation de mot de passe, droits d'administrateur, désactivation et suppression.

### 🧹 Maintenance et exploitation
- 🛠️ **[Outils d'administration en ligne de commande](cli_tools.md)** : comment utiliser le script `dev.py` pour les tâches d'administration (gestion des utilisateurs, mises à niveau de la base de données, sauvegardes de l'instance).
- 💾 **[Sauvegarde, restauration et déplacement](backup_restore.md)** : une seule archive pour toute l'instance : créez-la depuis Paramètres › Administration › Sauvegarde ou en ligne de commande, vérifiez-la, restaurez-la, et déplacez LibreFolio d'une installation à l'autre.
- 📂 **[Structure du système de fichiers](filesystem.md)** : détails sur l'emplacement des bases de données, des journaux, des fichiers téléversés et des dossiers temporaires, et sur la manière d'effectuer des sauvegardes.

---

## 🔔 Notifications de mise à jour {: #update-notifications }

Lorsqu'un administrateur se connecte, LibreFolio vérifie sur GitHub s'il existe une version **stable** plus récente. Si c'est le cas, la fenêtre **Nouvelle version disponible** affiche côte à côte votre version et la dernière version, avec un lien **Comment mettre à jour** vers le [guide de mise à jour](../user/installation.md#updating) et un lien **Notes de version sur GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Modale de mise à jour disponible avec la version actuelle et la dernière version">
</div>

- **Me le rappeler plus tard** ferme la fenêtre jusqu'à une prochaine connexion.
- **Ignorer cette version** arrête l'invite automatique pour cette version ; une version plus récente sera de nouveau annoncée.
- Une version n'est annoncée qu'une fois son image Docker téléchargeable, et la fenêtre attend qu'aucune autre fenêtre ni aucun guide ne soit ouvert.
- Sans accès à Internet, la vérification automatique échoue silencieusement : aucune erreur, aucune bannière.
- Pour vérifier immédiatement, utilisez **Rechercher des mises à jour** dans le [journal des modifications](../user/settings/about.md#changelog-modal) : il signale les erreurs, ainsi que les versions que vous avez ignorées.

??? note "👥 Autres utilisateurs — lorsqu'une personne qui n'est pas administrateur effectue une vérification"

    Pour les utilisateurs qui ne sont pas administrateurs, aucune vérification n'est lancée à la connexion. Si l'un d'eux lance
    **Rechercher des mises à jour** et qu'une version plus récente existe, la
    boîte de dialogue **Mise à jour disponible — contactez un administrateur** liste les administrateurs, avec leurs
    adresses e-mail lorsqu'elles sont disponibles, afin qu'ils sachent à qui s'adresser.

---

## 🔐 Maintenir les utilisateurs connectés après un redémarrage {: #session-persistence }

LibreFolio signe chaque session de connexion avec une clé secrète, `JWT_SECRET`.

- **Non définie** (valeur par défaut) : une nouvelle clé aléatoire est générée à chaque démarrage, donc tout le monde doit se connecter de nouveau après un redémarrage ou une mise à jour.
- **Définie** : les sessions survivent aux redémarrages. Définissez-la également si plusieurs serveurs LibreFolio distincts partagent les mêmes utilisateurs derrière un répartiteur de charge.

### 🔑 1. Générer une clé

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Pas de Python sur l'hôte ? Exécutez cette commande à l'intérieur du conteneur :

```bash
docker exec librefolio python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 📝 2. L'ajouter dans `.env` et redémarrer

```bash
JWT_SECRET=paste-the-generated-value-here
```

Redémarrez LibreFolio (avec Docker Compose : `docker compose up -d`). Gardez la clé confidentielle : quiconque la connaît peut forger une session.

??? tip "🐳 Garder la clé hors de `.env` — `JWT_SECRET_FILE`"

    Enregistrez la clé dans un fichier, par exemple un secret Docker, et définissez `JWT_SECRET_FILE` sur son chemin au lieu de
    `JWT_SECRET`, par exemple `JWT_SECRET_FILE=/run/secrets/jwt_secret`. Les règles et un exemple Docker
    Compose se trouvent dans [Secrets](configuration_secrets.md#secrets).

Les workers d'une même instance lancée avec `./dev.py server --workers …` partagent automatiquement une même clé. La durée d'une session correspond à la **Durée de session** dans les [Paramètres globaux](settings.md). Pour les détails, consultez la page développeur [Architecture de sécurité](../developer/architecture/security.md).
