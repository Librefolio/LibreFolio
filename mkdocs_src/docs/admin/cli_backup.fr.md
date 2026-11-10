# 💾 Outils d'administration CLI : sauvegardes

Cette page du guide des commandes couvre `dev.py backup` : créer, vérifier et restaurer une archive, suivre une restauration, travailler avec Docker.

Le reste du guide commence par [Outils en ligne de commande](cli_tools.md).

---

## 💾 Sauvegarder l'instance {: #backup }

`backup create` place toute l'instance dans un seul zip, alors que le serveur fonctionne : base de données, fichiers téléversés, rapports de courtier, scénarios de stress. Pour copier le répertoire de données à la main, voir [Sauvegarde](filesystem.md#backup).

| Tâche | Commande |
| --- | --- |
| Créer une archive | `backup create` ; avec `--encrypt` une [archive sécurisée](#backup-secure), avec `--sealed` ou `--recipient` une [archive scellée](#backup-sealed) pour les sauvegardes qui s'exécutent seules |
| Vérifier une archive et voir ce qu'elle contient | `backup inspect` |
| Essayer une restauration sur une copie, instance intacte | `backup restore --dry-run` |
| Restaurer au prochain démarrage du serveur | `backup restore` |
| Suivre ou annuler une restauration | `backup pending` |
| Reconvertir une archive sécurisée en son zip | `backup decrypt` |
| Générer la clé d'une archive scellée | `backup keygen` |

**Où s'exécutent les commandes :**

| Installation | Où | Commande |
| --- | --- | --- |
| Hôte | Terminal du serveur, dossier de LibreFolio | `pipenv run ./dev.py backup …` |
| Docker | Terminal du serveur, dossier de `docker-compose.yml` : la commande s'exécute dans le conteneur | `docker compose exec librefolio python dev.py backup …`, avec les chemins du conteneur : [Sauvegarder avec Docker](#backup-docker) |
| Un de vos ordinateurs | `backup keygen`, et l'ouverture d'une archive scellée là où se trouve la clé privée | [Une archive scellée](#backup-sealed) |

Un chemin relatif (`-o`, archives, fichiers de mot de passe) part de la racine du projet, quel que soit l'endroit d'où vous lancez la commande : préférez les chemins absolus. `backup --test-db create` sauvegarde le répertoire de données de test : une option de développement.

### 📦 Créer une archive

**Où : terminal du serveur, dossier de LibreFolio** (Docker : [dans le conteneur](#backup-docker)).

```bash
# Keep an archive in its own folder of <data dir>/backups/, and print its SHA-256
pipenv run ./dev.py backup create

# Copy it into another folder instead, which must already exist
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/

# Or give the archive a name of your own
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/before-update.zip

# A secure archive (.lfbk): the password is asked twice
pipenv run ./dev.py backup create --encrypt -o /mnt/nas/librefolio/
```

Résultat : l'archive zip, à l'endroit choisi avec les options ci-dessous, et sa somme de contrôle affichée.

| Option | Effet |
| --- | --- |
| aucune | **L'archive reste sur le serveur**, dans un dossier qui lui est propre dans `backups/` : `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip` (moment, origine `cli`, code court). Rien n'est copié ni déplacé. Elle figure dans **Paramètres › Administration › Sauvegarde** et dans le nettoyage automatique : [Sauvegardes conservées sur le serveur](backup_restore.md#kept-backups) |
| `-o`, `--output PATH` | **L'archive y est copiée**, rien ne reste dans `backups/`. Un dossier existant : l'archive avec son nom par défaut à l'intérieur. Tout autre chemin, même avec un `/` final : le fichier de l'archive, qui ne doit pas exister et n'est jamais renommé ; les dossiers manquants ne sont créés qu'au déplacement, de sorte qu'une sauvegarde échouée ne laisse aucun dossier vide. Vérifié avant le début de la sauvegarde : la commande doit pouvoir y écrire |
| `--encrypt` | [Archive sécurisée](#backup-secure) `.lfbk`, mot de passe demandé deux fois |
| `--password-file FILE`, `--password-stdin` | Archive sécurisée avec le mot de passe lu dans un fichier ou sur l'entrée standard, sans `--encrypt` |
| `--recipient age1…`, `--sealed` | [Archive scellée](#backup-sealed) `.tar`, sans mot de passe |

À savoir :

- ✅ Elle se termine avec `✅ Backup written: <path>`, la taille et le temps pris, `SHA-256: <checksum>`, les éventuels avertissements et le rappel `🔒 The archive holds every user's data: keep it private.` (archive sécurisée : `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`). Elle se termine avec `0` lorsque l'archive se trouve là où vous l'avez demandé, avertissements compris, et `1` sinon.
- 🟢 Le serveur continue de fonctionner, et d'écrire : la base de données est copiée avec `VACUUM INTO` de SQLite, un instantané cohérent, puis la copie passe le contrôle d'intégrité et le contrôle des clés étrangères.
- 🏷️ Le nom vient du moment où la sauvegarde commence, en UTC : `librefolio-backup-20261015-121500.zip`, `.lfbk` pour une archive sécurisée. Dans un dossier `--output` qui contient déjà ce nom, après deux sauvegardes dans la même seconde par exemple : `librefolio-backup-20261015-121500-2.zip`, puis `-3`, et ainsi de suite. Une archive ne remplace jamais un fichier.
- 🧾 Après le chemin, la commande affiche `SHA-256: <64 hexadecimal digits>`, la somme de contrôle de l'archive : comparez-la à celle du fichier une fois qu'il se trouve sur un autre disque.
- 💽 **Espace** : vérifié avant l'écriture, dans le dossier `backups/` du répertoire de données, même avec `-o` : environ deux fois la base de données, plus les fichiers, plus une petite marge. Insuffisant, ou disque ou quota qui se remplit pendant la sauvegarde → `❌ Backup failed (backup_no_space): not enough free space`. Avec `-o` sur un autre disque, l'espace disponible y est vérifié une fois l'archive construite et sa taille connue.
- 🛟 Si l'archive terminée ne peut pas aller dans `-o` (un fichier de ce nom est apparu entre-temps, des dossiers qui ne peuvent pas être créés, l'autre disque plein, une erreur d'écriture) → elle reste dans `backups/` comme fichier isolé : hors de la liste des sauvegardes conservées, jamais supprimée par le nettoyage automatique. La commande se termine avec `1`. Un déplacement qui échoue à mi-chemin ne laisse aucun fichier partiel.
- 🚦 Une seule sauvegarde à la fois : pendant qu'une autre est en cours, la commande s'arrête et vous demande de réessayer lorsque l'autre est terminée.
- 🔒 Sans mot de passe, l'archive n'est pas chiffrée : elle est écrite en `0600`, lisible et modifiable par son propriétaire seul. Conservez-la, ainsi que chaque copie, aussi privée que le répertoire de données.
- 🗑️ Les sauvegardes de `backups/` y restent jusqu'à ce que vous les supprimiez depuis **Paramètres › Administration › Sauvegarde** ou depuis le dossier, ou jusqu'à ce que le [nettoyage automatique](backup_restore.md#backup-cleanup) les supprime, à l'exception de la plus récente. Les fichiers isolés `librefolio-backup-*.zip` des versions antérieures ne sont jamais touchés. `backups/` se trouve sur le disque des données : copiez les archives sur un autre disque, un NAS ou hors site, ou écrivez-les directement à cet endroit avec `-o`.
- 🔗 Veillez à ce que `backups/` reste un vrai dossier, jamais un lien vers un NAS ou un autre disque : chaque archive y est construite, même avec `-o`. Un lien, ou un fichier, à sa place → `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.

??? note "⚠️ Avertissements et erreurs — signification des messages"

    **Avertissements** : l'archive est écrite malgré tout.

    - `The database failed its integrity check` ou `The database has foreign-key violations` : la base de données est dans l'archive telle quelle ; `backup inspect` affiche le résultat du contrôle.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, suivi des entrées, au maximum 50 : elles ne figurent pas dans l'archive. Les liens ne sont jamais suivis, même lorsqu'un dossier entier comme `custom-uploads/` est un lien vers un autre disque.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore` : une [archive sécurisée](#backup-secure) sans la clé.

    **Pas là où vous l'avez demandé** : l'archive est écrite, code de sortie `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, suivi des lignes habituelles : `-o` n'a pas pu recevoir l'archive, qui se trouve dans `backups/` comme fichier isolé, hors de la liste des sauvegardes conservées. Déplacez-la où vous le souhaitez.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.` : `backups/` n'a pas pu la recevoir non plus. Elle se trouve dans le dossier de travail, dans `backups/.jobs/`, que la première sauvegarde ou le premier démarrage de LibreFolio après cette heure supprime : déplacez-la avant.

    **Erreurs** : aucune archive n'est écrite, code de sortie `1`.

    - `❌ No data directory at <path>` ou `❌ No database at <path>: nothing to back up` : la commande utilise le [répertoire de données](filesystem.md) avec lequel LibreFolio est configuré ; vérifiez `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (un fichier se trouve là où le chemin exige un dossier) ou `❌ cannot write into <folder>: choose another folder, or run the command as a user who can` : `-o` ne peut pas recevoir l'archive. La sauvegarde n'a pas commencé.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …` : remettez `backups/` en tant que vrai dossier. `❌ The backup could not run in <data dir>/backups: <reason>` : le dossier de travail ne peut pas y être préparé, par exemple parce que le répertoire de données n'est pas accessible en écriture.
    - `❌ Backup failed (backup_no_space): not enough free space` : espace insuffisant au départ, ou disque ou quota qui s'est rempli pendant la sauvegarde, même au milieu d'un fichier. Libérez de l'espace sur le disque du répertoire de données.
    - `❌ Backup failed (backup_failed): the cause is in the log above` : toute autre erreur, par exemple un fichier qui échoue pendant sa copie dans l'archive (une erreur de lecture à mi-chemin) : une partie de fichier ne peut pas être retirée d'un zip, donc toute la sauvegarde s'arrête. Un fichier qui échoue avant la copie est laissé de côté avec l'avertissement ci-dessus.

### 🗃️ Où sont conservées les sauvegardes {: #backup-kept }

La commande et l'application laissent les sauvegardes terminées dans `backups/`, un dossier chacune : `librefolio-backup-<date>-<time>-<origin>-<id>`, origine `cli` pour la commande et `ui` pour l'application. `backups/.jobs/` ne contient qu'une sauvegarde en cours ou une sauvegarde échouée.

| Que faire avec elles | Où |
| --- | --- |
| Les lister, les télécharger, les supprimer | **Paramètres › Administration › Sauvegarde**, ou **Fichiers › Sauvegardes** (administrateurs uniquement) : [Sauvegardes conservées sur le serveur](backup_restore.md#kept-backups) |
| Supprimer les plus anciennes d'elles-mêmes, jamais la plus récente : taille totale et âge maximal, tous deux facultatifs | [Nettoyage automatique](backup_restore.md#backup-cleanup). La commande les applique après chaque sauvegarde, comme le fait l'application |
| Vérifier ou restaurer une archive conservée depuis la ligne de commande | `backup inspect` ou `backup restore`, avec le chemin affiché par `backup create` |

💽 Une copie sur le disque de vos données n'est pas une vraie sauvegarde : copiez l'archive sur un autre disque, ou utilisez `--output`.

### 🔐 Une archive sécurisée {: #backup-secure }

**Où : terminal du serveur, dossier de LibreFolio** (Docker, depuis cron : `-T` et un secret, [ci-dessous](#backup-docker)).

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Résultat : `librefolio-backup-20261015-121500.lfbk`, le zip que `backup create` écrit sans mot de passe, chiffré avec le vôtre.

Seul ce mot de passe l'ouvre, et LibreFolio ne récupère pas un mot de passe perdu : la commande se termine comme une sauvegarde normale, avec le rappel `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` Ce que cela protège et ce que cela ne protège pas : [Sauvegardes sécurisées](backup_restore.md#secure).

**D'où vient le mot de passe** : jamais de la ligne de commande, que chaque utilisateur du serveur lit (`ps`) et que le shell conserve dans son historique. Il n'y a pas de `--password`, et les options de mot de passe n'ont pas de forme abrégée.

| Option | Le mot de passe |
| --- | --- |
| `--encrypt` seul | Saisi au terminal, deux fois |
| `--password-file FILE` | Le texte du fichier, sans la marque d'ordre des octets au début ni les sauts de ligne à la fin, comme pour les [Secrets dans des fichiers](configuration_secrets.md#secret-files) : un fichier contenant le seul mot de passe, tel qu'un secret Docker. Un chemin relatif part de la racine du projet |
| `--password-stdin` | Une ligne de l'entrée standard, sans son saut de ligne, par exemple depuis un tube. Au terminal, il est demandé comme sans l'option, masqué, deux fois pour `create` : saisi là comme une ligne, il serait visible |

`--password-file` et `--password-stdin` s'excluent mutuellement, et chacune rend l'archive sécurisée sans `--encrypt`.

- 📄 **Un fichier auquel la commande peut se fier.** Le fichier de `--password-file`, comme celui de `--instance-key-file` ([La clé d'instance d'une autre installation](#backup-restore-instance-key)), doit être un fichier ordinaire. Un FIFO, un dossier ou un périphérique est refusé aussitôt, sans être lu : `❌ password file: <path> is not a regular file (password_unreadable)`. En root, par exemple avec `docker compose exec`, un chemin qui passe par un lien à l'intérieur du répertoire de données est refusé lui aussi (l'utilisateur de LibreFolio pourrait le faire pointer vers un fichier que seul root lit) : `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. Un lien ailleurs est suivi, comme le sont les secrets de Kubernetes ; les secrets de Docker et de Compose sont des fichiers ordinaires. Pour `--instance-key-file`, les mêmes lignes commencent par `instance key file:` et se terminent par `(instance_key_unreadable)`.
- 📏 **Les règles** : comme pour un mot de passe de compte, au moins 12 caractères avec une majuscule, une minuscule, un chiffre et un symbole (classes comptées en Unicode comme pour les comptes), au plus 1024. Vérifiées avant le début de la sauvegarde : un mot de passe qui en enfreint une n'écrit rien.
- 🗝️ **La clé d'instance** : `secrets/instance.key` est dans l'archive lorsque LibreFolio a généré la clé et peut l'utiliser ; jamais une clé venant de `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE`. Une clé générée qui ne peut pas être utilisée (abîmée, hors de portée, de plus de 4096 octets, plus qu'une restauration n'en relit) est laissée de côté avec `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore` ; l'archive est écrite malgré tout.
- 💽 **Espace** : le chiffrement (`… encrypting`, après les phases habituelles) écrit le `.lfbk` à côté du zip dans `backups/` : la taille du zip est de nouveau nécessaire là, plus 64 Mo, sinon `❌ Backup failed (backup_no_space): not enough free space`. Le zip est supprimé une fois chiffré, ou si la sauvegarde échoue. Après une interruption brutale (coupure de courant, `kill -9`), le démarrage suivant de LibreFolio termine cette sauvegarde comme interrompue et supprime ce qui reste dans `backups/.jobs/`, zip et copie de la base de données compris.

??? note "❌ Erreurs de mot de passe — signification des messages"

    Rien n'est écrit, code de sortie `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` : `--encrypt` sans terminal où demander, par exemple dans cron. Mot de passe vide saisi au terminal : `❌ No password was typed (password_required)` ; ligne vide par un tube avec `--password-stdin` : `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)` : les codes des règles enfreintes, dans cet ordre : `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, ou `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` (« Un fichier auquel la commande peut se fier » ci-dessus).

    Les deux options de mot de passe ensemble, ou une option qui n'existe pas comme `--password`, arrêtent la commande avant son démarrage, avec la ligne d'usage et le code de sortie `2`.

### 🗂️ Ce que contient l'archive

L'archive a la structure du répertoire de données et ne contient que ceci :

| Entrée | Ce que c'est |
| --- | --- |
| `manifest.json` | La description de l'archive, ci-dessous |
| `sqlite/app.db` | La copie de la base de données |
| `custom-uploads/` | Les fichiers téléversés dans l'application |
| `broker_reports/` | Les rapports de courtier |
| `scenario_catalog/` | Vos propres scénarios de stress, si vous en avez ajouté |
| `secrets/instance.key` | Dans une [archive sécurisée](#backup-secure) uniquement, lorsque LibreFolio a généré la clé d'instance : son texte, hors de la liste de fichiers du manifeste. Une restauration la lit pour rechiffrer les secrets enregistrés, et ne la décompresse jamais |

Tout le reste reste dehors : `secrets/` (sauf `secrets/instance.key` dans une archive sécurisée), `logs/`, `scheduler_state.json`, le dossier `backups/`, le marqueur `.librefolio-production-data` et les fichiers de travail de SQLite à côté de la base de données : `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` et les copies `.bak` des [correctifs post-migration](cli_tools.md#post-migration-fixes). La copie de la base de données contient déjà ce qui attendait dans `app.db-wal`. Les liens symboliques et les fichiers spéciaux ne sont jamais suivis ni archivés.

!!! warning "🔑 La clé d'instance se trouve uniquement dans une archive sécurisée"

    Une archive en clair laisse de côté `secrets/`, avec la [clé d'instance](configuration_secrets.md#instance-key). Sauvegardez-la séparément ([Structure du système de fichiers → Ce qu’il faut sauvegarder](filesystem.md#what-to-back-up)) et conservez la copie aussi privée que les archives. Avant de démarrer LibreFolio sur les données d'une archive en clair, remettez `secrets/` avec elles : sans sa clé, ce que LibreFolio a chiffré ne peut plus être lu. Une [archive sécurisée](#backup-secure) contient la clé générée par LibreFolio, jamais une clé venant de `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE` : conservez celle-là là où vous l'avez définie. Avec une copie de la clé, une restauration sur une autre installation lit encore les secrets enregistrés d'une archive en clair : [La clé d'instance d'une autre installation](#backup-restore-instance-key).

??? info "📋 `manifest.json` — ce qu'il enregistre"

    - le format, `librefolio-backup`, et sa version ;
    - la version de LibreFolio qui a créé l'archive, comment (`cli` pour cette commande, `ui` pour l'interface web) et quand, en UTC ;
    - la base de données : la révision de migration (Alembic), le résultat du contrôle d'intégrité de SQLite, le nombre de violations de clés étrangères, les lignes de chaque table et les totaux de contrôle du registre, la trésorerie de chaque courtier dans chaque devise et la quantité de chaque position (une archive créée avant eux n'en a pas) ;
    - chaque entrée, la base de données en premier, avec chemin, taille et SHA-256 ;
    - si l'archive contient la clé d'instance, et le SHA-256 de cette entrée : seule une archive sécurisée la contient.

### 🔍 Vérifier une archive

**Où : n'importe quelle installation**, serveur en marche ou arrêté ; il n'a pas besoin de répertoire de données, sauf pour une archive sécurisée (ci-dessous). Docker : [dans le conteneur](#backup-docker), avec le chemin du conteneur.

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

Résultat : le rapport de l'archive, et `✅ Every entry matches the manifest` une fois la taille et le SHA-256 de chaque entrée comparés au manifeste.

| Option | Effet |
| --- | --- |
| `--no-verify` | Compare uniquement les noms des entrées, sans les lire : `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)` |
| `--password-file FILE`, `--password-stdin` | Le mot de passe d'une archive sécurisée, aux mêmes sources que `create` ([Une archive sécurisée](#backup-secure)) ; un `.zip` les ignore |
| `--identity-file FILE` | La clé privée d'une [archive scellée](#backup-sealed) |

- 📋 Le rapport : qui a créé l'archive et quand (`Made by LibreFolio <version> (cli) on <date> UTC`), la révision de migration de la base de données, sa taille et son contrôle d'intégrité, les lignes et les tables, le nombre et la taille des fichiers, si la clé d'instance est incluse.
- 🔐 Une archive sécurisée, reconnue à ses premiers octets quel que soit son nom, demande d'abord le mot de passe, une fois. Elle est déchiffrée (`🔓 Decrypting <path>`) dans un dossier privé `.decrypt-…` à l'intérieur du dossier `backups/` du répertoire de données, supprimé à la fin même si la commande échoue : ce répertoire est nécessaire, ainsi que la place pour l'archive déchiffrée, environ la taille du `.lfbk`. Un dossier laissé par un `inspect` interrompu brutalement (coupure de courant, `kill -9`) est supprimé par le `inspect` suivant, ou par le démarrage suivant de LibreFolio, une fois qu'il a une heure : un plus récent peut appartenir à un autre `inspect` encore en cours. Le rapport ajoute `Secure backup: decrypted with its password`. Mot de passe erroné : `❌ The password does not open this backup (wrong_password)` ; `password_required`, `envelope_damaged` et `envelope_unsupported` figurent parmi les refus de [Essayer une restauration sur une copie](#backup-restore-dry-run).
- ❌ Elle se termine avec `1` lorsque des entrées manquent, diffèrent du manifeste ou n'y figurent pas (les cinq premières de chaque sorte), et lorsque le fichier n'est pas une archive lisible : le message se termine par un code, tel que `archive_unreadable` (pas un zip, ou tronqué), `manifest_missing`, `manifest_unknown_format` (pas une sauvegarde LibreFolio) ou `manifest_newer_format` (créée par un LibreFolio plus récent : vérifiez-la avec cette version ou une plus récente).

### 🔏 Une archive scellée {: #backup-sealed }

Une archive scellée est un `.tar` dont le mot de passe est généré par LibreFolio et chiffré pour une ou deux clés publiques age : seule la clé privée correspondante l'ouvre, le serveur qui l'a créée ne le peut pas. Elle est conçue pour les sauvegardes qui s'exécutent seules, par exemple chaque nuit depuis cron. Ce qu'elle contient, comment conserver et changer la clé : [Sauvegardes scellées](backup_sealed.md#sealed).

1. **Sur un de vos ordinateurs, pas sur le serveur** : la clé privée ne doit pas rester sur le serveur.

    ```bash
    # A key pair: the private key into a file of its own (0600, never over a file), the public key printed
    pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt
    ```

    Résultat : la clé privée au format de `age-keygen` (`# created:`, `# public key: age1…`, puis `AGE-SECRET-KEY-1…`), lisible par son propriétaire seul, jamais par-dessus un fichier existant (`❌ <path> already exists: a key file is never written over`) ; puis `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` et la ligne `age1…`.

2. **Terminal du serveur, dossier de LibreFolio** (Docker : `docker compose exec -T librefolio python dev.py backup create --sealed`).

    ```bash
    # A sealed archive for that public key (twice --recipient while a key is being changed)
    pipenv run ./dev.py backup create --recipient age1…

    # The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
    pipenv run ./dev.py backup create --sealed
    ```

    Résultat : `librefolio-backup-20261015-121500.tar`, avec les règles habituelles de `-o` et des noms ; après les phases d'une archive sécurisée, `… sealing`, puis `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`

3. **Là où se trouve la clé privée** : vérifiez-la, restaurez-la ou déchiffrez-la avec `--identity-file`.

    ```bash
    # Check, restore or decrypt it where the private key is
    pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
    pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
    pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
    ```

    Résultat : `🔏 Sealed backup <path>: its password opened with <key file>`, puis la commande continue comme pour une archive sécurisée avec son mot de passe.

| Option | Effet |
| --- | --- |
| `--recipient age1…` | Scelle pour cette clé ; deux fois pour deux clés, pendant qu'une clé est changée |
| `--sealed` | Scelle pour les clés de `LIBREFOLIO_BACKUP_RECIPIENTS` ([Variables d'environnement](configuration.md)) ; sans `--recipient` |
| `--identity-file FILE` | Ouvre un `.tar` pour `inspect`, `restore` et `decrypt` : un fichier de clé tel que `age-keygen` l'écrit, lu avant tout changement d'utilisateur, comme `--password-file` : un secret Docker fonctionne |

À savoir :

- 🔑 **Pas de mot de passe à donner** : `--sealed` et `--recipient` se passent de `--encrypt`, `--password-file` et `--password-stdin`, sinon la commande s'arrête avant d'écrire quoi que ce soit. Elle n'a pas besoin de terminal : elle s'exécute telle quelle depuis cron.
- 🗝️ **Jamais la clé d'instance**, pas même une clé générée par LibreFolio : contrairement à une [archive sécurisée](#backup-secure), une archive scellée laisse de côté `secrets/instance.key`.
- 💽 **Espace** : le scellement écrit le `.tar` à côté du `.lfbk`, donc le dossier de travail dans `backups/` a de nouveau besoin de la taille du `.lfbk`, plus 64 Mo, sinon `backup_no_space`.
- 🔓 **Comment elle s'ouvre** : la commande vérifie le `.tar` et son manifeste, ouvre le mot de passe avec la clé, le vérifie sur `backup.lfbk`, puis copie `backup.lfbk` dans un dossier privé du dossier temporaire du système, supprimé à la fin.
- ❌ Un `.tar` sans `--identity-file` s'arrête avec `sealed_backup_needs_key` ; `--identity-file` avec toute autre archive avec `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **Les refus**, à la fin du message : `sealed_identity_invalid` (le fichier ne contient aucune clé age, ou ne peut pas être lu), `sealed_no_identity` (aucune clé du fichier n'ouvre le mot de passe), `sealed_tar_invalid` (il ne contient pas les trois fichiers d'une archive scellée, dans l'ordre, en fichiers ustar ordinaires), `sealed_manifest_invalid` (son `manifest.json` ne la décrit pas), `sealed_password_invalid` (ce que la clé a ouvert n'est pas un mot de passe écrit par LibreFolio), puis ceux d'une archive sécurisée : `wrong_password` (il n'ouvre pas `backup.lfbk`) et `envelope_damaged`. Chaque message, avec ce qu'il faut faire : [Créer ou ouvrir une sauvegarde scellée](backup_moving.md#sealed-problems).

### 🧪 Essayer une restauration sur une copie {: #backup-restore-dry-run }

**Où : terminal du serveur, dossier de LibreFolio** (Docker : [dans le conteneur](#backup-docker)). Elle fonctionne sur toute installation disposant d'un répertoire de données, y compris une nouvelle : elle n'utilise jamais la base de données de l'instance, et le serveur peut continuer de fonctionner.

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

Résultat : l'archive est décompressée dans une copie, `.restore/stage/<id>/` dans le répertoire de données, mise à jour et vérifiée, puis le rapport indique ce que ferait une restauration et la copie est supprimée.

- ✅ Elle se termine avec `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.`, code de sortie `0` ; `1` lorsque l'archive est refusée ou la restauration bloquée : une ligne avec un code entre parenthèses, telle que `❌ The file is not a LibreFolio backup (not_a_backup)`, et rien de la copie ne reste.
- ♻️ Sans `--dry-run`, le même contrôle est la première moitié d'une restauration : [Restaurer une archive](#backup-restore).
- 🔐 Une [archive sécurisée](#backup-secure) demande d'abord le mot de passe, comme `inspect`, et est déchiffrée dans la copie sous le nom `.restore/stage/<id>/archive.zip`, supprimée une fois décompressée. Un contrôle interrompu brutalement laisse cette archive, ou sa partie `archive.zip.part` : le démarrage suivant de LibreFolio la supprime.

**Ce qu'elle vérifie**, en six étapes, en s'arrêtant à la première qui refuse l'archive (`… decrypting` pour une archive sécurisée, `… checking`, `… unpacking`, `… upgrading`, `… verifying`) :

1. **Une archive LibreFolio**, avec son `manifest.json` : un répertoire de données zippé à la main n'en est pas une. Chaque entrée, avant qu'un octet soit écrit : listée par le manifeste (ou annoncée, pour la clé d'instance), un fichier ordinaire (ni dossier, ni lien, ni entrée chiffrée), un nom unique même sans tenir compte des majuscules et minuscules, la taille du manifeste ; l'ensemble tient dans l'espace libre.
2. **Décompressée** : chaque entrée dans un nouveau fichier de la copie, jamais à travers un lien ni par-dessus un autre fichier, SHA-256 comparé au manifeste. Le schéma de la base de données est lu sans en exécuter la moindre partie : un déclencheur, une vue ou une table virtuelle, que LibreFolio ne crée jamais, fait refuser l'archive (`database_foreign_objects`).
3. **La révision décide** : la révision de migration (Alembic), tirée du manifeste et confirmée par la base de données.
    - identique à celle de ce LibreFolio : restaurée telle quelle ;
    - plus ancienne : la copie est mise à niveau jusqu'à la révision de ce LibreFolio, dans un processus séparé, arrêté après une heure ;
    - inconnue, très probablement plus récente : `revision_unknown`. Mettez d'abord LibreFolio à jour : une base de données n'est jamais rétrogradée.

    Puis les [correctifs post-migration](cli_tools.md#post-migration-fixes) s'exécutent sur la copie, comme à chaque démarrage.

4. **Contrôlée avant et après** : avant la mise à niveau, la copie passe le contrôle d'intégrité de SQLite, contient exactement les lignes que le manifeste a comptées et aucun texte qui ne soit pas en UTF-8 (LibreFolio n'en écrit aucun, et le serveur ne pourrait pas le lire) ; après, elle passe de nouveau le contrôle d'intégrité. Les lignes modifiées par une migration et les références cassées (clés étrangères), conservées telles quelles, sont des avertissements, pas des refus.
5. **Administrateurs** : sans administrateur actif dans la sauvegarde, la restauration est bloquée : personne ne pourrait ensuite gérer l'instance.
6. **Secrets enregistrés** : l'instance garde sa propre [clé d'instance](configuration_secrets.md#instance-key). Les secrets de plugins enregistrés (comme la clé d'API d'une source de données) sont rechiffrés sur la copie avec elle lorsque l'archive contient la clé qui les a chiffrés, ou que vous la donnez avec `--instance-key-file` ([La clé d'instance d'une autre installation](#backup-restore-instance-key)) ; les autres sont comptés, à saisir de nouveau après la restauration. Une copie sans secrets ne lit même pas la clé de cette instance.

**Le rapport** :

- 📦 Qui a créé l'archive et quand (`Made by LibreFolio <version> (<how>) on <date> UTC`), et ce que fait une restauration de la base de données : `this LibreFolio's own: restored as it is`, ou `upgraded on the copy to <revision> (<n> migrations)`, puis chaque migration avec la première ligne de sa description.
- 🩹 Les correctifs post-migration qui ont modifié quelque chose sur la copie, le cas échéant.
- 🔢 Lignes, tables et taille de la base de données, puis les tables dont les lignes ont changé avec la mise à niveau, sous la forme `<table> (<before> → <after>)`, avec `—` pour une table qui n'existait pas.
- 📁 Nombre et taille des fichiers ; `Secure backup: decrypted with its password` pour une archive sécurisée ; `Instance key: included` ou `Instance key: not included`, ou `Instance key: not included; given with --instance-key-file` avec cette option ; les clés enregistrées des fournisseurs de données : `Saved provider keys: <n> re-encrypted with this instance's key`, et `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` pour celles que la clé de l'archive, ou la clé donnée, n'a pas lues, ou lorsqu'il n'y a pas de clé.
- ⚖️ Les totaux de contrôle du registre : la trésorerie de chaque courtier dans chaque devise et la quantité de chaque position, à partir des seules transactions, sans prix, taux de change, coût ni date. Enregistrés dans le manifeste à la création, relus sur la copie une fois à jour. Une différence est un avertissement, jamais un refus : une migration peut corriger des données. L'une de ces lignes :
    - `Ledger totals: the same as when the backup was made` ;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, puis les lignes qui diffèrent, trésorerie d'abord, au maximum 20 : `broker <id>, <currency> cash: <before> → <after>` ou `broker <id>, asset <id> quantity: <before> → <after>`, le montant de la sauvegarde avant la flèche et celui de la copie après, `—` pour zéro. `… and <n> more` compte les lignes laissées de côté ;
    - `Ledger totals: not recorded in this archive` : une archive d'un LibreFolio antérieur aux totaux, ou dont les totaux n'ont pas pu être lus à la création ;
    - `Ledger totals: recorded by another version of the method, not compared` ;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 Les administrateurs, et ce que signifiera une restauration pour tout le monde : `After a restore you sign in with one of them, with the password of then; every session open now ends.` et `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ Les avertissements, qui laissent la restauration se poursuivre : `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` ou `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, comme l'explique [Codes de devise qui ne sont pas des codes ISO](cli_tools.md).
- 👥 Une sauvegarde contenant plus de comptes actifs que n'en permet `LIBREFOLIO_MAX_USERS` ajoute une ligne, une seule fois, sans noms ni adresses : `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. Elle informe seulement : `backup restore --yes` confirme et `--dry-run` se termine avec `0`, comme pour n'importe quelle sauvegarde.
- ⛔ Le bloquant : `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

À savoir :

- 💽 La copie a besoin d'espace libre sur le disque du répertoire de données : le contenu décompressé de l'archive, plus deux fois sa base de données pour la mise à niveau, plus 64 Mo (`backup inspect` affiche ces tailles) ; l'archive est lue là où elle se trouve, jamais copiée. Une archive sécurisée a aussi besoin de place pour l'archive déchiffrée, environ sa propre taille, jusqu'à sa décompression. Espace insuffisant → le contrôle s'arrête avant la décompression, avec les octets nécessaires (`no_space`) ; un disque qui se remplit pendant le contrôle l'arrête aussi.
- 📦 `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (« Options principales » dans [Variables d'environnement](configuration.md)) limite la taille décompressée : les tailles du manifeste sont additionnées avant le contrôle d'espace, et une archive au-delà de la limite est refusée avec `unpacked_too_large`, sans rien décompresser. Pour lever la limite le temps d'une commande, placez `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` devant elle :

    ```bash
    # Host
    LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>

    # Docker
    docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>
    ```

    Une limite illisible arrête la commande avant `🔎 Checking … on a copy`, code de sortie `1` : `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.

- 🚦 Une seule archive à la fois : pendant qu'un autre contrôle est en cours, `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Seul le répertoire de données est nécessaire, sinon `❌ No data directory at <path>`. Comme avec `-o`, un chemin relatif part de la racine du projet.
- 🔗 Veillez à ce que `.restore/` et `.restore/stage/` restent de vrais dossiers : un lien, ou un fichier, à leur place → `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Refus — signification des codes"

    | Code | Pourquoi l'archive est refusée |
    | --- | --- |
    | `not_a_backup` | Pas un zip, ou un zip sans le manifeste que LibreFolio écrit, comme un répertoire de données zippé à la main |
    | `password_required` | Une archive sécurisée, et aucun mot de passe : pas de terminal où le demander, et ni `--password-file` ni `--password-stdin` |
    | `wrong_password` | Le mot de passe n'ouvre pas l'archive sécurisée : ce n'est pas celui avec lequel elle a été créée, ou le début du fichier a été modifié |
    | `envelope_damaged` | L'archive sécurisée est abîmée, tronquée, ou a été modifiée après sa création |
    | `envelope_unsupported` | L'archive sécurisée provient d'un LibreFolio plus récent, ou demande des réglages que celui-ci n'accepte pas : mettez d'abord LibreFolio à jour |
    | `instance_key_unreadable`, `instance_key_invalid` | Le fichier donné avec `--instance-key-file` ne peut pas fournir la clé, ou la clé fait moins de 32 caractères : [La clé d'instance d'une autre installation](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | Le fichier ne peut pas être lu, ou le zip est abîmé |
    | `manifest_newer_format` | Le format de l'archive est plus récent que ce que ce LibreFolio lit : mettez d'abord LibreFolio à jour |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | Le manifeste est abîmé ou non valide |
    | `unexpected_entry`, `missing_entry` | L'archive contient une entrée que le manifeste ne liste pas, ou il lui manque des entrées qu'il liste ; pour la clé d'instance, une entrée que le manifeste n'annonce pas, ou une qu'il annonce et que l'archive n'a pas |
    | `duplicate_entry` | Une entrée apparaît deux fois, même lorsque seule la casse de son nom change, ou se trouve là où le dossier d'une autre entrée doit être |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | Une entrée est un dossier ou un lien, est chiffrée, ou utilise une compression que LibreFolio n'écrit pas |
    | `too_many_entries` | L'archive contient plus de 500 000 entrées |
    | `checksum_mismatch` | La taille ou le SHA-256 d'une entrée diffère du manifeste : l'archive est abîmée ou a été modifiée |
    | `unpacked_too_large` | Décompressée, l'archive dépasserait ce que cette installation accepte pour une restauration, d'après les tailles du manifeste : `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. Rien n'est décompressé |
    | `no_space` | Espace libre insuffisant pour la copie |
    | `stage_failed` | La copie n'a pas pu être écrite : l'erreur affichée juste au-dessus donne la cause |
    | `database_damaged` | La base de données de la sauvegarde échoue au contrôle d'intégrité de SQLite, avant ou après la mise à niveau, SQLite ne peut pas lire son schéma, ou elle contient du texte qui n'est pas en UTF-8 (un autre programme y a écrit, ou elle a été modifiée) |
    | `database_foreign_objects` | La base de données de la sauvegarde contient un déclencheur, une vue ou une table virtuelle, que LibreFolio ne crée jamais : elle n'a pas été créée par LibreFolio, ou a été modifiée. Utilisez une autre sauvegarde |
    | `manifest_mismatch` | La base de données de la sauvegarde n'est pas celle que décrit son manifeste |
    | `revision_missing` | La base de données de la sauvegarde n'enregistre aucune révision de migration |
    | `revision_unknown` | La sauvegarde provient d'un LibreFolio plus récent, ou pas de celui-ci : mettez LibreFolio à jour, puis vérifiez-la de nouveau |
    | `upgrade_failed` | La mise à niveau de la copie a échoué ou a duré plus d'une heure (l'erreur affichée juste au-dessus donne la cause), ou n'a pas atteint la révision de ce LibreFolio |
    | `post_migration_failed` | Un correctif post-migration a échoué sur la copie : l'erreur affichée juste au-dessus donne la cause |
    | `head_unknown` | Ce LibreFolio ne peut pas lire ses propres scripts de migration |

### ♻️ Restaurer une archive {: #backup-restore }

**Où : là où le serveur s'exécute** — terminal du serveur, dossier de LibreFolio ; avec Docker [dans le conteneur](#backup-docker). La restauration est enregistrée pour le chemin du répertoire de données : un serveur qui trouve son répertoire de données sous un autre chemin ne l'applique pas.

1. **Lancez la commande.**

    ```bash
    # Check the archive on a copy, then restore it at the next start of the server
    pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
    ```

    Résultat : le même contrôle sur une copie et le même rapport que [Essayer une restauration sur une copie](#backup-restore-dry-run) ; si l'archive peut être restaurée, la question :

    ```text
       Type "restore" to restore this archive at the next start of the server:
    ```

2. **Tapez `restore`**, en minuscules ; les espaces autour ne comptent pas. Toute autre réponse, `Restore` ou une ligne vide comprises, se termine par `Nothing restored: the copy was removed.` et le code de sortie `1`.

    Résultat, code de sortie `0` :

    ```text
    ✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
       That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
       ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
    ```

    Rien n'a encore changé : le serveur continue de fonctionner sur ses données, et la copie vérifiée attend dans `.restore/stage/<id>/`, aussi longtemps qu'il le faut.

3. **Redémarrez LibreFolio** quand cela vous convient : arrêtez tout le serveur, puis [redémarrez-le](cli_tools.md#start-the-server) ; avec Docker, `docker compose restart librefolio` ([Sauvegarder avec Docker](#backup-docker)). Si le serveur est arrêté, son prochain démarrage applique la restauration.

    Résultat : ce démarrage applique la restauration avant de lire la moindre donnée (ci-dessous).

| Option | Effet |
| --- | --- |
| `--dry-run` | Le contrôle seul : [Essayer une restauration sur une copie](#backup-restore-dry-run) |
| `--yes`, `-y` | Confirme sans demander. Sans terminal, par exemple dans un script, elle est requise : sinon `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.`, code de sortie `1` |
| `--password-file FILE`, `--password-stdin` | Le mot de passe d'une [archive sécurisée](#backup-secure), requis sans terminal |
| `--instance-key-file FILE` | La clé d'instance d'une autre installation : [ci-dessous](#backup-restore-instance-key) |
| `--identity-file FILE` | La clé privée d'une [archive scellée](#backup-sealed) |

**Ce que fait ce démarrage :**

1. 🛑 **Uniquement un démarrage de tout le serveur.** Chaque processus du serveur détient un verrou sur le répertoire de données depuis le début de son démarrage jusqu'à sa sortie. Un démarrage qui le trouve détenu par un autre processus (un worker que uvicorn redémarre à côté de ses frères, avec `--workers` ; un second serveur sur le même répertoire) laisse la restauration en attente (`server_running`). Redémarrez tout le serveur, jamais un seul worker. Un démarrage qui trouve la restauration appliquée par un autre serveur encore en marche, ou par un autre démarrage, s'arrête plutôt que de servir des données dont la restauration n'est pas terminée.
2. 🔀 **L'échange.** Les dossiers `sqlite/`, `custom-uploads/`, `broker_reports/` et `scenario_catalog/` de l'instance échangent leur place avec ceux de la copie : des renommages à l'intérieur du répertoire de données, instantanés quelle que soit la taille. Les dossiers de l'instance vont dans `.restore/previous/`.
3. 🔒 **Ce qui reste.** `secrets/`, `logs/`, `scheduler_state.json` et `backups/` ne sont pas touchés : l'instance garde sa [clé d'instance](configuration_secrets.md#instance-key), ses journaux et ses archives.
4. ✅ **Le premier démarrage doit aboutir.** Il se poursuit, sur les données restaurées, déjà à la révision de ce LibreFolio. Une fois passé, avant de répondre à qui que ce soit, il termine toutes les sessions, révoque les liens à usage unique de la sauvegarde et supprime les anciennes données et la copie : la restauration est terminée.
5. ↩️ **Sinon, retour à l'état précédent.** Si ce premier démarrage échoue (une migration, un fichier abîmé), le démarrage suivant remet seul les données comme elles étaient et enregistre le retour en arrière avec sa raison ([Suivre ou annuler une restauration](#backup-pending)). Avec Docker, le conteneur redémarre seul ; si rien ne redémarre le serveur, démarrez-le vous-même.

**Après la restauration :**

- 🔑 Tout le monde se reconnecte, sur chaque appareil, avec un compte de la sauvegarde et le mot de passe de l'époque. Le rapport du contrôle nomme les administrateurs de la sauvegarde.
- 🔗 Aucun lien envoyé avant la restauration ne fonctionne plus (invitations, réinitialisations de mot de passe, vérifications d'e-mail), pas même ceux qui se trouvent encore dans la sauvegarde : envoyez-en de nouveaux.
- 📧 Un compte que la sauvegarde contenait en attente de la vérification de son e-mail perd son lien et cesse d'attendre : la page de connexion ne lui en envoie pas d'autre et répond que le compte est désactivé. Un administrateur l'active dans [Utilisateurs et invitations](users.md#actions), l'adresse restant non vérifiée, ou le supprime ([Supprimer un compte](users.md#delete)), afin que son titulaire s'inscrive de nouveau et reçoive un nouveau lien. Un tel compte ne s'est jamais connecté : il ne contient aucune donnée.
- 🆘 Si personne ne se souvient du mot de passe de l'époque d'un administrateur, la personne qui gère le serveur crée un lien de réinitialisation avec [`user reset-link`](cli_tools.md), ou définit un nouveau mot de passe avec `user reset`. Une fois connecté, un administrateur envoie les liens de réinitialisation aux autres depuis [Utilisateurs et invitations](users.md#reset-links).

À savoir :

- 🚦 Une seule restauration à la fois : pendant qu'une attend ou est en cours d'application, `backup restore` s'arrête avant le contrôle avec `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)`, code de sortie `1`. Elle s'arrête là aussi lorsqu'elle ne peut pas lire l'état de la restauration, car elle ne peut pas savoir si une attend : `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, code de sortie `1`, rien de vérifié. `--dry-run` fonctionne toujours.
- ❌ Si la confirmation est refusée, la commande affiche une ligne avec un code, supprime la copie et se termine avec `1` : `restore_stage_outdated` (LibreFolio mis à jour entre le contrôle et la confirmation), `restore_stage_expired` (question en attente depuis plus de 24 heures), `restore_already_pending` (une autre restauration confirmée entre-temps). Relancez la commande ; après `restore_stage_outdated`, vérifiez de nouveau l'archive.
- 🔗 Veillez à ce que les quatre dossiers restent de vrais dossiers du répertoire de données : un dossier qui est un lien, ou monté à part, ne peut pas être échangé. Le démarrage laisse les données telles quelles et enregistre le retour en arrière avec `swap_failed`.
- 💽 L'échange n'a besoin d'aucun espace propre : la copie du contrôle devient les données de l'instance, et les anciennes données sont supprimées une fois le premier démarrage abouti.
- 🗝️ La restauration conserve la clé d'instance de cette installation. Les secrets enregistrés d'une archive d'une autre installation sont rechiffrés avec elle par le contrôle si l'archive contient la clé qui les a chiffrés (une [archive sécurisée](#backup-secure), avec une clé générée par LibreFolio) ou si vous la donnez avec `--instance-key-file` ([La clé d'instance d'une autre installation](#backup-restore-instance-key)). Sinon ils ne peuvent pas être lus ici : le rapport les compte, à saisir de nouveau après la restauration, sauf si vous remettez d'abord la clé de cette installation ([Secrets enregistrés et clé d'instance](configuration_secrets.md#plugin-secrets)). Voir « La clé d'instance se trouve uniquement dans une archive sécurisée » ci-dessus.

### 🗝️ La clé d'instance d'une autre installation {: #backup-restore-instance-key }

**Où : terminal du serveur, dossier de LibreFolio**, avec le fichier de clé en dehors du répertoire de données (Docker : un secret que seul root lit, [ci-dessous](#backup-docker)).

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Résultat : le contrôle rechiffre sur la copie les secrets de plugins enregistrés (comme la clé d'API d'une source de données) avec la clé de cette instance, qui reste telle quelle.

Elle est nécessaire car une archive en clair laisse de côté la clé d'instance, et une archive sécurisée dont la clé venait de l'environnement aussi : ses secrets enregistrés ne s'ouvrent qu'avec la clé de l'installation qui l'a créée. Elle fonctionne avec ou sans `--dry-run`.

- 📁 Le rapport indique `Instance key: not included; given with --instance-key-file`, puis `Saved provider keys: <n> re-encrypted with this instance's key`.
- 📄 **Le fichier** : une copie du `secrets/instance.key` de l'ancienne installation, le fichier de son `LIBREFOLIO_INSTANCE_KEY_FILE` tel quel, ou la valeur de son `LIBREFOLIO_INSTANCE_KEY` écrite dans un fichier telle qu'elle était dans la variable, espaces compris. Seuls une marque d'ordre des octets au début et les sauts de ligne à la fin sont retirés, comme pour `--password-file` : une clé qui fonctionnait comme variable fonctionne de même dans le fichier.
- 🔑 Lu en premier, par l'utilisateur qui a lancé la commande, avant le passage au propriétaire du répertoire de données, comme `--password-file` : avec `docker compose exec`, un secret Docker que seul root lit fonctionne. Même règle que `--password-file`, « Un fichier auquel la commande peut se fier » dans [Une archive sécurisée](#backup-secure) : gardez-le en dehors du répertoire de données.
- 🙈 La clé n'est jamais affichée. Seule la ligne de commande la prend : l'interface web non, et une restauration depuis Paramètres › Administration › Sauvegarde compte ces secrets comme illisibles.
- ℹ️ Une archive avec sa propre clé est restaurée avec celle-là, quel que soit le contenu du fichier : `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ Une clé qui ne lit aucun secret enregistré n'est pas la clé de l'installation qui a créé la sauvegarde : `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, avant la ligne qui les compte. Si la clé de cette instance ne peut pas être utilisée, ou s'il n'y en a pas et que le contrôle ne peut pas la créer (`secrets/` non accessible en écriture), rien n'est rechiffré, quelle que soit la clé donnée : `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>`, avec le problème du `The instance key cannot be used: …` du journal de démarrage (« Contrôles au démarrage » dans [Variables d'environnement](configuration.md)) ou, sans clé, `<path>: there is no instance key yet, and it could not be created`. Les secrets déjà sous la clé de cette instance, comme dans une archive de cette même instance, restent tels quels.
- ❌ Elle se termine avec `1`, avant de rien vérifier, lorsque le fichier ne fournit pas la clé : `❌ instance key file: <path> does not exist (instance_key_unreadable)`, ou `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. Une clé de moins de 32 caractères l'arrête avant la création de la copie : `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Suivre ou annuler une restauration {: #backup-pending }

**Où : terminal du serveur, dossier de LibreFolio** (Docker : [dans le conteneur](#backup-docker)) ; `--recover previous` uniquement avec LibreFolio arrêté.

```bash
# The restore waiting for the next start, or the last one
pipenv run ./dev.py backup pending

# Drop the restore waiting, and its checked copy (the same as --recover cancel)
pipenv run ./dev.py backup pending --cancel

# When the state of the restore cannot be read: put the data of before back (LibreFolio stopped)
pipenv run ./dev.py backup pending --recover previous

# For a script: the state as one JSON line, and the same actions with fixed exit codes
pipenv run ./dev.py backup pending --json
pipenv run ./dev.py backup pending --recover cancel --json
```

Résultat : `backup pending` ne change rien et se termine avec `0`, sauf s'il ne peut pas lire l'état de la restauration ([Un état de restauration illisible](#backup-pending-unreadable)). Il affiche l'une de ces lignes :

| Il affiche | Ce que cela signifie |
| --- | --- |
| `ℹ️ No restore waits for the next start` | Aucune restauration confirmée, ou la dernière a été abandonnée |
| `⏳ A restore waits for the next start of the server`, puis `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmée, pas encore appliquée. `<who>` est `cli` pour cette commande, sinon le nom d'utilisateur de l'administrateur qui l'a confirmée |
| `⏳ A restore is being applied by the server` | Un démarrage l'a appliquée et n'a pas encore abouti. Si ce processus s'est terminé anormalement, le suivant remet les données |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | Terminée |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | Annulée, pour la raison du tableau ci-dessous |

| Option | Effet |
| --- | --- |
| `--cancel` | Abandonne la restauration en attente, avec sa copie : [ci-dessous](#backup-pending-unreadable) |
| `--json` | L'état sous forme d'une ligne JSON, pour les scripts : [Pour les scripts](#backup-pending-json) |
| `--recover CHOICE` | `previous` ou `cancel`, avec des codes de sortie fixes : [Pour les scripts](#backup-pending-json) |

Lorsqu'un démarrage a trouvé une restauration en attente sans l'appliquer, une ligne de plus en donne la raison, et la restauration continue d'attendre :

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)` : une sauvegarde s'exécutait au démarrage, par exemple un `backup create` depuis la ligne de commande.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)` : le serveur a trouvé son répertoire de données sous un chemin différent de celui de la confirmation, par exemple une copie du répertoire de données. Abandonnez-la avec `--cancel`, puis lancez `backup restore` là où le serveur s'exécute.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)` : un worker a redémarré pendant que les autres servaient (`--workers`), ou un autre serveur utilise le même répertoire de données. Redémarrez tout le serveur.

| Code | `<reason>` | Que faire |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | Le journal de ce démarrage donne la cause |
| `swap_interrupted` | `the start that applied it was interrupted` | Rien : un démarrage arrêté pendant l'échange, et le suivant l'a annulé |
| `swap_failed` | `its folders could not be moved into place` | Faites des quatre dossiers de vrais dossiers du répertoire de données, ni liens ni montages séparés |
| `stage_missing` | `its checked copy was gone` | La copie dans `.restore/stage/` a été supprimée ou modifiée : vérifiez de nouveau l'archive |

Un retour en arrière supprime aussi les données restaurées et la copie : pour réessayer, lancez de nouveau `backup restore`. Si même le retour aux anciennes données échoue (disque, permissions), LibreFolio ne démarre pas : le journal contient `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, et chaque démarrage réessaie.

#### 🧩 Un état de restauration illisible {: #backup-pending-unreadable }

L'état de la restauration, `.restore/restore.json`, peut devenir illisible : propriétaire ou permissions modifiés, erreur de disque, lien ou dossier à sa place, contenu que LibreFolio n'a pas écrit. Une restauration a pu s'arrêter à mi-chemin, et LibreFolio ne sait pas quelles données il contient. `backup pending` le dit et se termine avec `1` :

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` est `io` (le système de fichiers le refuse : rendez `.restore/` et ses fichiers à l'utilisateur qui exécute LibreFolio, puis relancez `backup pending`, ce qui peut suffire), `not_a_file` ou `invalid`. Tant que l'état est illisible, aucune copie vérifiée n'est supprimée, ni par le nettoyage du serveur ni par Paramètres › Administration › Sauvegarde, et aucune restauration ne peut être confirmée.

**`--recover previous`**, avec LibreFolio arrêté, remet les données de l'époque à partir des dossiers : chaque dossier conservé dans `.restore/previous/` retourne à sa place, et celui qu'il remplace va dans `.restore/failed/`. Une restauration terminée n'a conservé aucune ancienne donnée : ses données restent. L'état illisible est conservé sous le nom `.restore/restore.json.unreadable-<date>` pour qu'on y jette un œil, et n'est plus jamais relu. Ensuite, démarrez LibreFolio sur les données de l'époque, ou restaurez de nouveau une sauvegarde avec `backup restore`. Avec LibreFolio en marche, elle s'arrête avec `(restore_in_use)`, code de sortie `5` ; avec un état lisible, ou aucun, avec `(restore_nothing_to_recover)`, code de sortie `3` ([Pour les scripts](#backup-pending-json)). Lancée deux fois, la seconde ne change rien.

**`--cancel`**, identique à `--recover cancel` mais avec les codes de sortie ci-dessous, abandonne la restauration en attente avec sa copie vérifiée, quelle que soit la personne qui l'a confirmée :

| Résultat | Il affiche | Sortie |
| --- | --- | --- |
| Abandonnée | `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is` | `0` |
| Abandonnée, copie non supprimée (permissions, disque) | `✅ The restore waiting for the next start was dropped: the data stays as it is` et `⚠️ Its checked copy could not be removed: it goes when its check expires`. Avec une erreur, le journal au-dessus contient `The copy of a cancelled restore could not be removed: it goes when its check expires` ; une copie laissée sans erreur, comme une avec un dossier en lecture seule, n'en a pas. LibreFolio réessaie à son premier démarrage une fois le contrôle vieux de 24 heures | `0` |
| Impossible à abandonner, pour une erreur du système de fichiers avant (le verrou, ou la suppression de l'état) | `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)` | `1` |
| État illisible | La ligne `restore_state_unreadable` de `backup pending` | `1` |
| Aucune restauration en attente, ou une déjà en cours d'application | `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)` | `1` |

#### 🤖 Pour les scripts : --json et --recover {: #backup-pending-json }

Un script, ou une machine qui atteint le serveur par `ssh`, lit l'état avec `--json` et agit avec `--recover CHOICE` : rien n'est demandé au terminal, et les codes de sortie sont fixes.

**La ligne JSON.** Avec `--json`, `backup pending` écrit exactement une ligne sur stdout : un objet JSON, puis un saut de ligne, sans couleur. Tout le reste, lignes de journal de LibreFolio comprises, va sur stderr. Il se termine avec `0` chaque fois que la ligne est affichée : un état illisible est un état, pas une erreur.

| Clé | Valeur |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` ou `unreadable` |
| `reason` | La raison du retour en arrière d'un état `rolled_back` (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), ou `io`, `not_a_file`, `invalid` pour un état `unreadable` ; `null` sinon |
| `waiting` | Pourquoi un démarrage n'a pas appliqué une restauration en attente : `backup_running`, `other_data_directory`, `server_running`, ou `null` |
| `backup_created_at` | Quand la sauvegarde de la restauration a été créée, sous la forme `2026-10-23T03:00:12Z` (UTC) ; `null` sans état, ou avec un état illisible |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` lorsque les données d'avant un échange se trouvent dans `.restore/previous/`, sinon `{"present": false, "at": null}` |
| `choices` | Les mots que `--recover` accepte maintenant, dans le tableau ci-dessous |

Après un `--recover`, la ligne décrit l'état **après** celui-ci et ajoute `recover`, `{"choice": "<word>", "done": true}` ou `false`, et, avec un code de sortie autre que `0`, `error`, le mot du tableau des codes de sortie.

| `state` | Signification | `choices` |
| --- | --- | --- |
| `none` | Aucune restauration confirmée, ou la dernière a été abandonnée | aucun |
| `pending` | Une restauration attend le prochain démarrage | `cancel` |
| `in_progress` | Un démarrage l'applique, ou l'a appliquée et n'a pas encore abouti | aucun |
| `committed` | La dernière restauration est terminée | aucun |
| `rolled_back` | La dernière restauration a été annulée, avec son `reason` | aucun |
| `unreadable` | L'état ne peut pas être lu : [Un état de restauration illisible](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

La ligne ne contient jamais de nom d'utilisateur, d'e-mail, de chemin ni d'identifiant : qui a confirmé, le répertoire de données et la copie vérifiée n'y figurent pas. `safety_copy.at` est le moment où la restauration a été appliquée, ou, avec un état illisible, la dernière modification de `.restore/previous/`.

**Les codes de sortie.** `--recover previous` remet les données de l'époque lorsque l'état ne peut pas être lu, avec LibreFolio arrêté ; `--recover cancel` abandonne la restauration en attente, avec sa copie vérifiée. Pareil avec ou sans `--json` :

| Sortie | Quand | `error` dans la ligne |
| --- | --- | --- |
| `0` | Fait : les données de l'époque sont remises, ou la restauration en attente a été abandonnée | aucun |
| `2` | Une erreur d'usage : `--recover` sans choix, `--recover` avec `--cancel`, ou `--json` avec `--cancel` (utilisez `--recover cancel`) | aucun : la ligne n'est pas écrite |
| `3` | Rien à récupérer : aucun état de restauration, ou le choix était déjà fait | `nothing_to_recover` |
| `4` | Le choix n'est pas valide dans cet état, comme `previous` alors que l'état est lisible, `cancel` alors qu'il ne l'est pas, ou un mot qui n'est pas un choix : rien ne change | `choice_not_valid` |
| `5` | Échec : LibreFolio s'exécute sur ce répertoire de données (`restore_in_use`), un dossier ne peut pas être remis en place (`restore_apply_failed`), la restauration ne peut pas être abandonnée (`failed`) : rien n'est déclaré fait. Avec un répertoire de données manquant, `5` aussi, mais sans ligne : stdout vide, stderr en donne la raison | `restore_in_use`, `restore_apply_failed` ou `failed` |

Relancé, un choix ne change rien : le second `--recover previous` ne trouve aucun état illisible, ne déplace aucun dossier, n'ajoute rien à `.restore/failed/` et se termine avec `3` ; de même pour un second `--recover cancel`. Un script peut répéter `previous` ou `cancel` jusqu'à lire `0` ou `3`.

Un script qui lit l'état et récupère, sur un serveur où LibreFolio est arrêté :

```bash
state=$(pipenv run ./dev.py backup pending --json 2>/dev/null)

if [ "$(echo "$state" | jq -r '.choices | index("previous") != null')" = "true" ]; then
    pipenv run ./dev.py backup pending --recover previous --json 2>/dev/null
    case $? in
        0|3) echo "data of before is back" ;;
        5)   echo "failed: stop LibreFolio, read the log" >&2; exit 1 ;;
    esac
fi
```

### 🔓 Déchiffrer une archive sécurisée {: #backup-decrypt }

**Où : n'importe quelle installation**, serveur en marche ou arrêté ; il n'a pas besoin de répertoire de données. Docker : [dans le conteneur](#backup-docker), avec `-o` là où l'utilisateur du serveur peut écrire.

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Résultat : le zip contenu dans l'[archive sécurisée](#backup-secure), celui que `backup create` écrit sans mot de passe, avec `secrets/instance.key` si l'archive sécurisée contient la clé.

| Option | Effet |
| --- | --- |
| `-o`, `--output FILE` | Requis : le fichier du zip, qui ne doit pas encore exister. Un fichier existant est refusé avant le mot de passe, `❌ <path> already exists: choose another name`, rien n'est écrit. Chemin relatif à partir de la racine du projet, comme avec `create` |
| `--password-file FILE`, `--password-stdin` | Le mot de passe, sinon demandé une fois au terminal ([Une archive sécurisée](#backup-secure)) |
| `--identity-file FILE` | La clé privée d'une [archive scellée](#backup-sealed) |

- ✅ Elle se termine avec `✅ Decrypted: <path> (<size>)` et `🔒 It holds every user's data in clear: keep it private, and remove it once used.` ; avec la clé d'instance, une dernière ligne : `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- ♻️ `inspect` et `restore` prennent ce zip comme n'importe quel autre, et sa clé rechiffre toujours les secrets enregistrés. Pour restaurer une archive sécurisée, il n'est pas nécessaire : `backup restore` prend le `.lfbk` tel quel.
- 🔒 Le zip contient les données de tous les utilisateurs en clair, et seul son propriétaire le lit (`0600`) : l'utilisateur qui a lancé la commande, ou l'utilisateur du serveur lorsque la commande a basculé vers lui.
- 👤 Là où il y a un répertoire de données et que vous l'exécutez en root, par exemple avec `docker compose exec`, elle lit d'abord `--password-file` en root (un secret Docker de root fonctionne), puis bascule vers le propriétaire du répertoire de données, comme les autres commandes : le zip appartient à l'utilisateur du serveur, et `-o` doit être accessible en écriture par cet utilisateur ([Sauvegarder avec Docker](#backup-docker)). Si elle ne peut pas basculer, elle s'arrête avant de lire l'archive ou de demander le mot de passe : `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ Elle se termine avec `1` lorsqu'elle ne peut pas lire le fichier, comme un que seul root lit une fois basculé vers l'utilisateur du serveur (`❌ Cannot read <path>: <reason> (archive_unreadable)`, avant le mot de passe), lorsque le fichier n'est pas une archive sécurisée (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), lorsque le mot de passe ne l'ouvre pas (`wrong_password`), lorsqu'il est abîmé (`envelope_damaged` : rien n'est laissé à `-o`) ou provient d'un LibreFolio plus récent (`envelope_unsupported`), et lorsqu'elle ne peut pas écrire à `-o` (`❌ Cannot write <path>: <reason>`, une fois le mot de passe donné : rien n'y est laissé).

### 🚚 Utiliser une archive sur une autre installation

[`backup restore`](#backup-restore) restaure une archive sur l'installation où vous l'exécutez, avec le `secrets/` de cette installation. Pour démarrer à la place une autre installation à la main sur les données d'une archive, avec le `secrets/` de l'installation qui l'a créée, par exemple lorsque vous déplacez LibreFolio :

1. **Installation qui reçoit les données, terminal** : commencez par vérifier l'archive avec `backup restore <archive> --dry-run` ([Essayer une restauration sur une copie](#backup-restore-dry-run)) : sans rien modifier, elle vous dit si ce LibreFolio accepte l'archive, quelles migrations il appliquera et avec quels administrateurs vous vous connecterez. Puis **arrêtez LibreFolio**.
2. **Répertoire de données vide** (`LibreFolio-data/` avec Docker Compose) : s'il contient quoi que ce soit, mettez-le d'abord de côté : rien des anciennes données ne doit se mélanger à celles de l'archive, pas même `app.db-wal` et `app.db-shm` de SQLite. **Décompressez l'archive** à cet endroit ; une archive sécurisée est d'abord déchiffrée en son zip ([Déchiffrer une archive sécurisée](#backup-decrypt)).
3. **`secrets/` dans le répertoire de données** : remettez-le à partir de la copie enregistrée séparément. Le zip d'une archive sécurisée avec la clé apporte déjà `secrets/instance.key` : donnez au dossier le mode `0700` et au fichier `0600` (`chmod`), sinon le journal de démarrage affiche un avertissement.
4. **Démarrez LibreFolio**, la version qui a créé l'archive ou une plus récente : les migrations en attente s'exécutent seules au démarrage.

À savoir :

- ⛔ LibreFolio ne rétrograde jamais une base de données : une archive d'une version plus récente demande cette version ou une plus récente, et une plus ancienne ne démarre pas dessus. `backup inspect` affiche la version qui a créé l'archive ; `backup restore --dry-run` la refuse avec `revision_unknown`.
- 🧹 Le `manifest.json` laissé à la racine du répertoire de données est sans danger : vous pouvez le supprimer.
- 👤 Avec Docker, le conteneur donne le répertoire de données à son utilisateur à chaque démarrage : le propriétaire des fichiers décompressés n'a pas d'importance. Sur une installation hôte, décompressez avec l'utilisateur qui exécute LibreFolio.
- 🗝️ La clé d'une archive sécurisée ne fonctionne que là où ni `LIBREFOLIO_INSTANCE_KEY` ni `LIBREFOLIO_INSTANCE_KEY_FILE` n'est défini : une clé définie là l'emporte sur `secrets/instance.key`. Ne la mettez jamais à la place d'une clé déjà utilisée : ce qui a été enregistré avec cette clé deviendrait illisible. Une installation avec sa propre clé prend l'archive avec [`backup restore`](#backup-restore), qui rechiffre les secrets enregistrés.

### 🐳 Sauvegarder avec Docker {: #backup-docker }

**Où : terminal du serveur, dossier de `docker-compose.yml`.** La commande s'exécute dans le conteneur, où le répertoire de données est `/app/backend/data/prod-docker`.

```bash
# Write an archive: on the host, it appears in its own folder of ./LibreFolio-data/backups/
docker compose exec librefolio python dev.py backup create

# Check it, with its path inside the container
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Try a restore of it on a copy: the instance stays as it is
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# Restore it: the same check, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Restart the container: its start applies the restore
docker compose restart librefolio

# Then see how it went
docker compose exec librefolio python dev.py backup pending
```

Résultat : comme sur l'hôte ; l'archive de `backup create` se trouve dans un dossier qui lui est propre, tel que `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`, c'est-à-dire `./LibreFolio-data/backups/` sur l'hôte.

- 👤 `docker compose exec` s'exécute en root : la commande bascule vers le propriétaire du répertoire de données, `backup decrypt` compris, et ce qu'elle écrit appartient à l'utilisateur du serveur. Si elle ne peut pas basculer, elle s'arrête et vous demande de l'exécuter avec cet utilisateur : `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, avec les nombres du message.
- 📂 `-o` et les archives de `inspect` et `restore` sont des chemins à l'intérieur du conteneur. Une archive qui se trouve sur l'hôte : copiez-la d'abord dans `LibreFolio-data/`, par exemple dans `LibreFolio-data/backups/`. Une archive à écrire en dehors de `LibreFolio-data/backups/` : un dossier monté depuis l'hôte, accessible en écriture par l'utilisateur du serveur ; ailleurs, elle reste dans le conteneur et est perdue lorsque le conteneur est recréé.
- 🔑 `restore` et `decrypt` lisent l'archive avec l'utilisateur du serveur : une archive écrite par `backup create` convient, une archive que vous avez copiée doit être lisible par cet utilisateur, sinon `archive_unreadable`. Avec l'image officielle, `sudo chown 1000:1000 <archive>` sur l'hôte.
- ⌨️ `docker compose exec` donne à la commande un terminal où demander. Sans terminal, par exemple `docker compose exec -T` dans un script, ajoutez `--yes`.
- 🔐 [Archive sécurisée](#backup-secure) : `--encrypt` demande le mot de passe sur ce terminal. Avec `-T`, par exemple depuis cron, utilisez `--password-file` et un secret Docker, tel que `/run/secrets/backup_password` : [l'exemple](backup_restore.md#command-line) de Sauvegarde, restauration et déplacement de votre instance montre les lignes à ajouter à `docker-compose.yml`. Le zip de `backup decrypt` appartient à l'utilisateur du serveur : donnez-lui un `-o` que cet utilisateur peut écrire, dans `LibreFolio-data/backups/` ou dans un dossier monté depuis l'hôte : `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 [Archive scellée](#backup-sealed), sans terminal : `docker compose exec -T librefolio python dev.py backup create --sealed` lit `LIBREFOLIO_BACKUP_RECIPIENTS` dans l'environnement du conteneur, que remplit `env_file: .env` ; après une modification de `.env`, `docker compose up -d` recrée le conteneur. Pour en ouvrir une dans le conteneur, donnez à `--identity-file` un chemin à l'intérieur de celui-ci ; mieux, ouvrez-la sur votre ordinateur, là où se trouve la clé privée ([Ouvrir une sauvegarde scellée](backup_sealed.md#sealed-open)).
- 🔁 Après un premier démarrage qui échoue sur les données restaurées, le conteneur redémarre seul (`restart: unless-stopped`, dans les deux fichiers compose que LibreFolio fournit), et ce démarrage remet les données comme elles étaient.
- 🔒 Sur l'hôte, les archives appartiennent à l'utilisateur du conteneur, et seul cet utilisateur les lit : avec un autre utilisateur de l'hôte, copiez-les avec `sudo cp -a`.
- 💻 Depuis une copie des sources, `./dev.py docker exec backup create` fait la même chose.

---

## 🔗 Voir aussi

- 📄 **[Outils en ligne de commande](cli_tools.md)** — Démarrer le serveur, gérer les utilisateurs, entretenir la base de données, …
