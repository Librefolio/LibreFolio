# 🛡️ Manuel d'administration

Pour les personnes qui installent et exploitent LibreFolio. Presque tout se fait à l'un de ces trois endroits : en **ligne de commande**, dans le fichier **`.env`** (variables d'environnement) ou dans les onglets **Paramètres › Administration** de l'application.

---

## 📚 Guides

### 🐳 Déploiement et exposition
- 📦 **[Installation sur l'hôte](host_installation.md)** : Python, Node.js et Pipenv directement sur la machine hôte.
- 🐳 **[Docker avancé](docker_advanced.md)** : Docker Compose, volumes et propriété des fichiers via GID/UID.
- 🌐 **[Exposer en toute sécurité](service_exposure.md)** : votre instance privée avec Tailscale, sans ouvrir de port sur le routeur : un VPN pour vos propres appareils ou un routeur de sous-réseau pour tout votre réseau domestique.
    - 🌍 **[Exposer en toute sécurité : accès public avec Funnel](service_exposure_funnel.md)** : une adresse HTTPS publique avec Tailscale Funnel, une pour LibreFolio ou une pour chaque service avec Docker.
- 🔍 **[Vérifier la sécurité de la connexion](connection_checks.md)** : la liste de contrôle, l'indicateur, la vue du serveur et le cookie de session ; que faire lorsqu'une vérification échoue.
    - 🧰 **[Vérifier la sécurité de la connexion : derrière un proxy inverse](connection_proxy.md)** : Nginx, Caddy, Traefik ou Tailscale : les en-têtes à envoyer, le proxy de confiance et l'adresse du visiteur.

### ⚙️ Configuration du système
- 📝 **[Variables d'environnement](configuration.md)** : le fichier `.env` et les principales variables (`PORT`, `JWT_SECRET`, `LIBREFOLIO_DATA_DIR`, etc.), avec la priorité entre les valeurs.
    - 🔐 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** : les secrets lus depuis des fichiers (comme les secrets Docker), la clé de l'instance, les paramètres et les clés d'API des plugins.
    - 🛡️ **[Configuration : vérifications et protections](configuration_security.md)** : les vérifications au démarrage, la Content-Security-Policy, la protection contre l'encadrement et la façon dont le serveur s'arrête.
    - 👥 **[Configuration : comptes et recherche d'actifs](configuration_accounts.md)** : qui peut s'inscrire, les limites de comptes et de connexions échouées, l'administrateur initial, l'ordre des fournisseurs de prix.
- 📧 **[E-mail](email.md)** : SMTP facultatif : les variables, des exemples pour les serveurs les plus courants, l'onglet **E-mail** de Paramètres › Administration et l'e-mail de test.
    - 📬 **[E-mail : liens et messages](email_flows.md)** : invitations et réinitialisations de mot de passe, mots de passe oubliés et leurs limites, vérification de l'adresse e-mail, avis de changement d'adresse e-mail.
    - 🛠️ **[E-mail : quand cela ne fonctionne pas](email_troubleshooting.md)** : les erreurs, ce que dit le journal, notes de sécurité SMTP.
- ⚙️ **[Paramètres globaux](settings.md)** : les paramètres d'exécution (TTL de session, limites de téléversement, intervalles de synchronisation des données de marché), les onglets **Administration** et les vérifications de **Sécurité** de l'instance.
- 👥 **[Utilisateurs et invitations](users.md)** : l'onglet **Utilisateurs** de l'application : invitations, liens de réinitialisation du mot de passe, droits d'administrateur, désactivation et suppression.

### 🧹 Maintenance et exploitation
- 🛠️ **[Outils d'administration en ligne de commande](cli_tools.md)** : le script `dev.py` pour la gestion des utilisateurs, les mises à niveau de la base de données et les sauvegardes de l'instance.
- 💾 **[Sauvegarde, restauration et déplacement](backup_restore.md)** : une archive unique avec toute l'instance, depuis Paramètres › Administration › Sauvegarde ou en ligne de commande : la créer, la vérifier, la restaurer, déplacer LibreFolio d'une installation à l'autre.
- 📂 **[Structure du système de fichiers](filesystem.md)** : où se trouvent les bases de données, les journaux, les fichiers téléversés et les dossiers temporaires, et comment effectuer des sauvegardes.

---

## 🔔 Notifications de mise à jour {: #update-notifications }

Lorsqu'un administrateur se connecte, LibreFolio vérifie sur GitHub s'il existe une version **stable** plus récente. Si c'est le cas, la fenêtre **Nouvelle version disponible** affiche côte à côte votre version et la dernière version, avec les liens **Comment mettre à jour** ([guide de mise à jour](../user/installation.md#updating)) et **Notes de version sur GitHub**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="update-available-modal" alt="Fenêtre de mise à jour disponible avec la version actuelle et la dernière version">
</div>

| Bouton | Effet |
| --- | --- |
| **Me le rappeler plus tard** | Ferme la fenêtre jusqu'à une prochaine connexion. |
| **Ignorer cette version** | Plus d'invite automatique pour cette version ; une version encore plus récente sera annoncée. |

- Une version n'est annoncée qu'une fois son image Docker téléchargeable ; la fenêtre attend qu'aucune autre fenêtre ni aucun guide ne soit ouvert.
- Sans accès à Internet, la vérification échoue silencieusement : aucune erreur, aucune bannière.
- Pour vérifier tout de suite : **Vérifier les mises à jour** dans le [journal des modifications](../user/settings/about.md#changelog-modal). Il signale les erreurs, et aussi les versions ignorées.

??? note "👥 Autres utilisateurs — lorsqu'une personne qui n'est pas administrateur effectue une vérification"

    Pour les utilisateurs qui ne sont pas administrateurs, aucune vérification n'est lancée à la connexion. Si l'un d'eux lance **Vérifier les mises à jour** et qu'une version plus récente existe, la fenêtre **Mise à jour disponible — contactez un administrateur** liste les administrateurs, avec leurs adresses e-mail lorsqu'elles sont disponibles.

---

## 🔐 Maintenir les utilisateurs connectés après un redémarrage {: #session-persistence }

`JWT_SECRET` est la clé qui signe chaque session de connexion.

- **Non défini** (valeur par défaut) : une nouvelle clé aléatoire à chaque démarrage, donc tout le monde se reconnecte après un redémarrage ou une mise à jour.
- **Défini** : les sessions survivent aux redémarrages. Définissez-le aussi lorsque plusieurs serveurs LibreFolio partagent les mêmes utilisateurs derrière un répartiteur de charge.

Pour le définir :

1. Générez une clé. **Depuis un terminal**, sur l'hôte :

    ```bash
    python3 -c "import secrets; k = secrets.token_urlsafe(64); print(f'JWT_SECRET={k}'); print(k)"
    ```

    Vous obtenez deux lignes : la première, `JWT_SECRET=…`, est prête à coller dans `.env` ; la seconde est la clé seule, pour la garder dans un fichier (`JWT_SECRET_FILE`, plus bas). Sans Python sur l'hôte, exécutez la commande **dans le conteneur** :

    ```bash
    docker exec librefolio python -c "import secrets; k = secrets.token_urlsafe(64); print(f'JWT_SECRET={k}'); print(k)"
    ```

2. Collez la première ligne **dans le fichier `.env` de LibreFolio** :

    ```bash
    JWT_SECRET=paste-the-generated-value-here
    ```

3. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

    Dès lors, un redémarrage ne déconnecte plus personne.

!!! warning "🔒 Gardez la clé secrète"

    Quiconque la connaît peut forger une session.

??? tip "🐳 Garder la clé hors de `.env` — `JWT_SECRET_FILE`"

    Enregistrez la clé dans un fichier, par exemple un secret Docker, et définissez `JWT_SECRET_FILE` sur son chemin au lieu de `JWT_SECRET` : par exemple `JWT_SECRET_FILE=/run/secrets/jwt_secret`. Les règles et un exemple Docker Compose se trouvent dans [Secrets](configuration_secrets.md#secrets).

- Les workers d'un même `./dev.py server --workers …` partagent une clé d'eux-mêmes.
- La durée d'une session correspond à la **Durée de Session** dans les [Paramètres globaux](settings.md).
- Détails pour les développeurs : [Architecture de sécurité](../developer/architecture/security.md).
