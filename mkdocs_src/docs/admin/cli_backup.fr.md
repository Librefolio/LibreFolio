# 💾 Outils d'administration CLI : sauvegardes

Cette page fait partie du guide des outils en ligne de commande. Elle couvre les commandes de **sauvegarde** : créer, vérifier et restaurer une archive, suivre une restauration et sauvegarder avec Docker.

Le reste du guide commence par [Outils en ligne de commande](cli_tools.md).

---

## 💾 Sauvegarder l'instance {: #backup }

`backup create` place toute l'instance dans une seule archive zip, alors que le serveur continue de fonctionner : elle contient la base de données, les fichiers téléversés, les rapports de courtier et vos propres scénarios de stress. Avec `--encrypt`, il crée une [archive sécurisée](#backup-secure), chiffrée avec un mot de passe que vous choisissez, que `backup decrypt` reconvertit en zip. Avec `--sealed` ou `--recipient`, il crée une [archive scellée](#backup-sealed), dont seule une de vos clés privées ouvre le mot de passe, pour les sauvegardes qui s'exécutent seules. `backup inspect` vérifie une archive et affiche son contenu, `backup restore --dry-run` essaie de la restaurer sur une copie, en laissant l'instance telle quelle, et `backup restore` la restaure au prochain démarrage du serveur. Pour copier le répertoire de données à la main, voir [Sauvegarde](filesystem.md#backup).

### 📦 Créer une archive

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

- 🟢 Le serveur continue de fonctionner, et d'écrire, pendant la sauvegarde : la base de données est copiée avec `VACUUM INTO` de SQLite, un instantané cohérent, puis les contrôles d'intégrité et de clés étrangères de SQLite s'exécutent sur la copie.
- 🗃️ **Sans `--output`, l'archive reste sur le serveur**, dans un dossier qui lui est propre dans `backups/`, par exemple `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip` : le dossier est nommé d'après le moment, l'origine de la sauvegarde (`cli`) et un code court. Rien n'est copié ni déplacé, et la commande affiche ce chemin, puis une ligne `SHA-256: <64 hexadecimal digits>`, la somme de contrôle de l'archive. La sauvegarde figure alors dans la liste de **Paramètres › Administration › Sauvegarde**, et dans le nettoyage automatique : [Sauvegardes conservées sur le serveur](backup_restore.md#kept-backups).
- 📋 **Avec `--output`, l'archive y est copiée** et rien ne reste dans `backups/` : la même ligne `SHA-256:` suit le chemin de la copie. Comparez-la à la somme de contrôle du fichier une fois qu'il se trouve sur un autre disque.
- 🏷️ L'archive est nommée d'après le moment où la sauvegarde commence, en UTC : `librefolio-backup-20261015-121500.zip`, ou `.lfbk` pour une [archive sécurisée](#backup-secure). Dans un dossier fourni avec `--output` qui contient déjà un fichier de ce nom, après deux sauvegardes dans la même seconde par exemple, elle devient `librefolio-backup-20261015-121500-2.zip`, puis `-3`, et ainsi de suite : une archive ne remplace jamais un fichier.
- 📁 `--output` (`-o`) est vérifié avant le début de la sauvegarde, et la commande doit pouvoir y écrire. Un dossier existant reçoit l'archive sous son nom par défaut. Tout autre chemin est le fichier de l'archive, même s'il se termine par `/` : un dossier qui n'existe pas encore devient le nom de l'archive. Ce fichier ne doit pas encore exister, et son nom n'est jamais modifié. Ses dossiers manquants ne sont créés qu'au moment où l'archive y est déplacée, de sorte qu'une sauvegarde échouée ne laisse aucun dossier vide derrière elle. Préférez les chemins absolus : un chemin relatif part de la racine du projet, quel que soit l'endroit d'où vous lancez la commande.
- 💽 Avant d'écrire quoi que ce soit, la commande vérifie l'espace libre là où elle construit l'archive, dans le dossier `backups/` du répertoire de données, même avec `-o` : environ deux fois la taille de la base de données, plus les fichiers, plus une petite marge. Lorsqu'il est insuffisant, ou lorsque le disque ou un quota se remplit pendant la sauvegarde malgré tout, la commande s'arrête avec `❌ Backup failed (backup_no_space): not enough free space`. Lorsque `-o` se trouve sur un autre disque, l'espace disponible y est vérifié une fois l'archive construite et sa taille connue.
- 🛟 Si l'archive terminée ne peut pas aller dans `-o` (un fichier de ce nom est apparu entre-temps, ses dossiers ne peuvent pas être créés, l'autre disque manque d'espace, une erreur d'écriture), elle est placée dans `backups/` à la place, comme fichier isolé : elle ne figure pas dans la liste des sauvegardes conservées et le nettoyage automatique ne la supprime jamais. La commande se termine avec `1`. Un déplacement qui échoue à mi-chemin ne laisse aucun fichier partiel derrière lui.
- 🚦 Une seule sauvegarde s'exécute à la fois : pendant qu'une autre est en cours, la commande s'arrête et vous demande de réessayer lorsqu'elle se termine.
- ✅ Elle se termine avec `✅ Backup written: <path>`, la taille et le temps pris, `SHA-256: <checksum>`, les éventuels avertissements, et un rappel : `🔒 The archive holds every user's data: keep it private.`, ou pour une archive sécurisée `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` Elle se termine avec `0` lorsque l'archive se trouve là où vous l'avez demandé, avertissements compris, et `1` sinon.
- 🔒 Sans mot de passe, l'archive n'est pas chiffrée : LibreFolio l'écrit, comme une archive sécurisée, de sorte que seul son propriétaire puisse la lire et y écrire (`0600`). Conservez-la, ainsi que chaque copie, aussi privée que le répertoire de données.
- 🗑️ Les sauvegardes conservées dans `backups/` y restent jusqu'à ce que vous les supprimiez depuis **Paramètres › Administration › Sauvegarde** ou depuis le dossier, ou jusqu'à ce que le [nettoyage automatique](backup_restore.md#backup-cleanup) que vous avez défini les supprime, à l'exception de la plus récente. LibreFolio ne touche jamais aux fichiers isolés `librefolio-backup-*.zip` que les versions antérieures ont laissés dans `backups/`. Ce dossier se trouve sur le même disque que les données : copiez donc les archives sur un autre disque, un NAS ou hors site, ou écrivez-les directement à cet endroit avec `-o`.
- 🔗 Veillez à ce que `backups/` reste un vrai dossier, jamais un lien vers un NAS ou un autre disque : chaque archive y est d'abord construite, même avec `-o`. Un lien, ou un fichier, à sa place arrête la commande avec `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.
- 🧪 `backup --test-db create` sauvegarde à la place le répertoire de données de test : une option de développement.

??? note "⚠️ Avertissements et erreurs — signification des messages"

    **Avertissements** : l'archive est écrite malgré tout.

    - `The database failed its integrity check` ou `The database has foreign-key violations` : l'archive conserve la base de données telle quelle, et `backup inspect` affiche le résultat du contrôle d'intégrité.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, suivi des entrées, au maximum 50 : elles ne figurent pas dans l'archive. Les liens ne sont jamais suivis, même lorsqu'un dossier entier comme `custom-uploads/` est un lien vers un autre disque.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore` : une [archive sécurisée](#backup-secure) sans la clé.

    **Pas là où vous l'avez demandé** : l'archive est écrite, et la commande se termine avec `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, suivi des lignes habituelles : `-o` n'a pas pu recevoir l'archive terminée, elle se trouve donc dans `backups/`, comme fichier isolé hors de la liste des sauvegardes conservées. Déplacez-la où vous le souhaitez.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.` : `backups/` n'a pas pu la recevoir non plus. Elle se trouve encore dans le dossier de travail de la sauvegarde, dans `backups/.jobs/`, que la première sauvegarde démarrée après cette heure, ou le premier démarrage de LibreFolio après celle-ci, supprime : déplacez l'archive avant ce moment.

    **Erreurs** : aucune archive n'est écrite, et la commande se termine avec `1`.

    - `❌ No data directory at <path>` ou `❌ No database at <path>: nothing to back up` : la commande sauvegarde le [répertoire de données](filesystem.md) avec lequel LibreFolio est configuré ; vérifiez `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (un fichier se trouve là où le chemin exige un dossier) ou `❌ cannot write into <folder>: choose another folder, or run the command as a user who can` : `-o` ne peut pas recevoir l'archive. La sauvegarde n'a pas commencé, et rien n'a été créé.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …` : remettez `backups/` en tant que vrai dossier. `❌ The backup could not run in <data dir>/backups: <reason>` : la commande n'a pas pu y préparer son dossier de travail, par exemple parce qu'elle ne peut pas écrire dans le répertoire de données.
    - `❌ Backup failed (backup_no_space): not enough free space` : l'espace libre était insuffisant au départ, ou le disque ou un quota s'est rempli pendant la sauvegarde, même au milieu d'un fichier. Libérez de l'espace sur le disque du répertoire de données.
    - `❌ Backup failed (backup_failed): the cause is in the log above` : toute autre défaillance. L'une d'elles est un fichier qui échoue pendant sa copie dans l'archive, comme une erreur de lecture au milieu du fichier : une partie de fichier ne peut pas être retirée d'un zip, donc toute la sauvegarde s'arrête. Un fichier qui échoue avant le début de sa copie est laissé de côté avec l'avertissement ci-dessus à la place.

### 🗃️ Où sont conservées les sauvegardes {: #backup-kept }

La commande et l'application laissent toutes deux leurs sauvegardes terminées dans `backups/`, un dossier chacune, nommé `librefolio-backup-<date>-<time>-<origin>-<id>`, où l'origine est `cli` ici et `ui` pour l'application. `backups/.jobs/` ne contient qu'une sauvegarde en cours ou une sauvegarde échouée. Que faire avec elles :

- 📋 Listez, téléchargez et supprimez-les dans **Paramètres › Administration › Sauvegarde**, ou **Fichiers › Sauvegardes** (administrateurs uniquement) : [Sauvegardes conservées sur le serveur](backup_restore.md#kept-backups).
- 🧹 Définissez une taille totale et un âge maximal, tous deux facultatifs, afin que les plus anciennes disparaissent d'elles-mêmes, jamais la plus récente : [Nettoyage automatique](backup_restore.md#backup-cleanup). La commande les applique après chaque sauvegarde, comme le fait l'application.
- 💽 Une copie sur le disque de vos données n'est pas une vraie sauvegarde : copiez l'archive sur un autre disque, ou utilisez `--output`.
- 🔎 Pour vérifier ou restaurer une archive conservée depuis la ligne de commande, donnez à `backup inspect` ou `backup restore` le chemin affiché par `backup create`.

### 🔐 Une archive sécurisée {: #backup-secure }

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Une archive sécurisée, `librefolio-backup-20261015-121500.lfbk`, est le zip que `backup create` écrit sans mot de passe, chiffré avec un mot de passe que vous choisissez : seul ce mot de passe l'ouvre, et LibreFolio ne peut pas récupérer un mot de passe perdu. Ce qu'elle protège, et ce qu'elle ne protège pas : [Sauvegardes sécurisées](backup_restore.md#secure).

- 🔑 **D'où vient le mot de passe**, jamais de la ligne de commande, que chaque utilisateur du serveur peut lire (`ps`) et que le shell conserve dans son historique : il n'existe pas d'option `--password`, et les commandes qui prennent un mot de passe n'acceptent aucune option abrégée.
    - `--encrypt` seul : saisi au terminal, deux fois.
    - `--password-file FILE` : le texte du fichier, sans la marque d'ordre des octets en son début ni les sauts de ligne à sa fin, comme pour les [Secrets dans les fichiers](configuration_secrets.md#secret-files) : un fichier qui contient le mot de passe seul, comme un secret Docker. Un chemin relatif part de la racine du projet.
    - `--password-stdin` : une ligne de l'entrée standard, sans son saut de ligne, comme depuis un pipe. Au terminal, le mot de passe est demandé comme sans l'option, sans être affiché, deux fois pour `create` : saisi là comme une ligne, il serait visible.

    `--password-file` et `--password-stdin` s'excluent mutuellement, et l'un ou l'autre rend l'archive sécurisée sans `--encrypt`.

- 📄 **Un fichier auquel la commande peut se fier.** Le fichier de `--password-file`, comme celui de `--instance-key-file` ([La clé d'instance d'une autre installation](#backup-restore-instance-key)), doit être un fichier régulier : un FIFO, un dossier ou un périphérique est refusé immédiatement, sans jamais attendre ni lire, avec `❌ password file: <path> is not a regular file (password_unreadable)`. Lancée en tant que root, par exemple avec `docker compose exec`, la commande refuse aussi un chemin qui passe par un lien à l'intérieur du répertoire de données, où l'utilisateur de LibreFolio aurait pu en placer un vers un fichier que seul root peut lire : `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. Un lien ailleurs est suivi, comme Kubernetes monte ses secrets ; les secrets Docker et Compose sont des fichiers simples. Pour `--instance-key-file`, les mêmes lignes commencent par `instance key file:` et se terminent par `(instance_key_unreadable)`.
- 📏 **Les règles** sont celles d'un mot de passe de compte d'au moins 12 caractères : une lettre majuscule et une lettre minuscule, un chiffre et un symbole, chaque classe étant comptée en Unicode comme pour les comptes ; au maximum 1024 caractères. Elles sont vérifiées avant le début de la sauvegarde : un mot de passe auquel il manque l'une de ces règles n'écrit rien.
- 🗝️ **La clé d'instance.** L'archive contient `secrets/instance.key` lorsque LibreFolio a généré la clé et peut l'utiliser ; jamais une clé définie avec `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE`. Une clé générée qui ne peut pas être utilisée, qui est endommagée, hors d'atteinte, ou plus longue que 4096 octets, soit plus qu'une restauration ne relit, est laissée de côté, avec l'avertissement `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, et l'archive est écrite malgré tout.
- 🔐 **Le chiffrement** intervient après les phases habituelles, sous la forme `… encrypting`. Il écrit le `.lfbk` à côté du zip dans `backups/`, il a donc de nouveau besoin de la taille du zip à cet endroit, plus 64 Mo : lorsque cela est insuffisant, `❌ Backup failed (backup_no_space): not enough free space`. Le zip est supprimé une fois chiffré, ou lorsque la sauvegarde échoue. Une sauvegarde tuée brutalement, par une coupure de courant ou `kill -9`, ne peut pas le supprimer : le prochain démarrage de LibreFolio termine cette sauvegarde comme interrompue et supprime ce qu'elle a laissé dans `backups/.jobs/`, le zip et la copie de la base de données compris.
- ✅ Elle se termine comme ci-dessus, le rappel étant `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`

??? note "❌ Erreurs de mot de passe — signification des messages"

    Rien n'est écrit, et la commande se termine avec `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` : `--encrypt` sans terminal pour le demander, comme dans cron. Un mot de passe vide saisi au terminal se termine par `❌ No password was typed (password_required)` ; une ligne vide lue depuis un pipe avec `--password-stdin` se termine par `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)` : les codes des règles qu'il manque, dans cet ordre : `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, ou `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` (voir « Un fichier auquel la commande peut se fier » ci-dessus).

    Les deux options de mot de passe à la fois, ou une option qui n'existe pas, comme `--password`, arrêtent la commande avant son démarrage, avec sa ligne d'utilisation et le code de sortie `2`.

### 🗂️ Contenu de l'archive

L'archive reprend la structure du répertoire de données et ne contient que :

| Entrée | Ce que c'est |
| --- | --- |
| `manifest.json` | La description de l'archive, voir ci-dessous |
| `sqlite/app.db` | La copie de la base de données |
| `custom-uploads/` | Les fichiers téléversés dans l'application |
| `broker_reports/` | Les rapports de courtier |
| `scenario_catalog/` | Vos propres scénarios de stress, si vous en avez ajouté |
| `secrets/instance.key` | Uniquement dans une [archive sécurisée](#backup-secure), lorsque LibreFolio a généré la clé d'instance : son texte, hors de la liste des fichiers du manifeste. Une restauration le lit pour rechiffrer les secrets enregistrés, et ne le décompresse jamais |

Tout le reste est exclu : `secrets/` (mais `secrets/instance.key` dans une archive sécurisée), `logs/`, `scheduler_state.json`, le dossier `backups/` lui-même, le marqueur `.librefolio-production-data`, et les fichiers de travail de SQLite à côté de la base de données : `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` et les copies `.bak` des [corrections post-migration](cli_tools.md#post-migration-fixes). La copie de la base de données contient déjà ce qui attendait dans `app.db-wal`. Les liens symboliques et les fichiers spéciaux ne sont jamais suivis ni archivés.

!!! warning "🔑 La clé d'instance se trouve uniquement dans une archive sécurisée"

    Une archive en clair exclut `secrets/`, qui contient la [clé d'instance](configuration_secrets.md#instance-key). Sauvegardez-la séparément, comme l'explique [Structure du système de fichiers → Ce qu'il faut sauvegarder](filesystem.md#what-to-back-up), et conservez la copie aussi privée que les archives. Avant de démarrer LibreFolio sur les données d'une archive en clair, remettez `secrets/` avec elles : sans sa clé, ce que LibreFolio a chiffré ne peut plus être lu. Une [archive sécurisée](#backup-secure) contient la clé générée par LibreFolio, jamais une clé définie avec `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE` : conservez celle-là là où vous l'avez définie. Avec une copie de la clé, une restauration sur une autre installation peut encore lire les secrets enregistrés d'une archive en clair : [La clé d'instance d'une autre installation](#backup-restore-instance-key).

??? info "📋 `manifest.json` — ce qu'il enregistre"

    - le format, `librefolio-backup`, et sa version ;
    - la version de LibreFolio qui a créé l'archive, comment (`cli` pour cette commande, `ui` pour l'interface web) et quand, en UTC ;
    - la base de données : sa révision de migration (Alembic), le résultat du contrôle d'intégrité de SQLite, le nombre de violations de clés étrangères, les lignes de chaque table et les totaux de contrôle du registre, les liquidités de chaque courtier dans chaque devise et la quantité de chaque position (une archive créée avant eux n'en contient aucun) ;
    - chaque entrée, la base de données d'abord, avec son chemin, sa taille et son SHA-256 ;
    - si l'archive contient la clé d'instance, et le SHA-256 de cette entrée : seule une archive sécurisée le fait.

### 🔍 Vérifier une archive

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

- 🟢 Elle fonctionne sur n'importe quelle archive, avec le serveur en marche ou arrêté, et ne nécessite aucun répertoire de données, sauf pour une archive sécurisée (ci-dessous). Comme avec `-o`, un chemin relatif part de la racine du projet.
- 📋 Elle affiche qui a créé l'archive et quand (`Made by LibreFolio <version> (cli) on <date> UTC`), la révision de migration de la base de données, sa taille et son contrôle d'intégrité, ses lignes et ses tables, le nombre et la taille des fichiers, et si la clé d'instance est incluse.
- 🔎 Elle compare la taille et le SHA-256 de chaque entrée avec le manifeste, et se termine par `✅ Every entry matches the manifest`. `--no-verify` compare uniquement les noms des entrées, sans lire les entrées, et se termine par `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)`.
- 🔐 Une archive sécurisée, reconnue à ses premiers octets quel que soit son nom, demande d'abord son mot de passe, une fois, depuis les mêmes sources que `create` ([Une archive sécurisée](#backup-secure)). Elle est ensuite déchiffrée (`🔓 Decrypting <path>`) dans un dossier privé `.decrypt-…` du dossier `backups/` du répertoire de données, supprimé à la fin, y compris lorsque la commande échoue : la commande a besoin de ce répertoire de données, et de place dans celui-ci pour l'archive déchiffrée, environ la taille du `.lfbk`. Un dossier qu'un `inspect` tué brutalement (une coupure de courant, `kill -9`) a laissé derrière lui est supprimé par le prochain `inspect`, ou par le prochain démarrage de LibreFolio, une fois qu'il est âgé d'une heure : un dossier plus récent peut appartenir à un autre `inspect` encore en cours. Son rapport ajoute `Secure backup: decrypted with its password`. Un mot de passe erroné se termine par `❌ The password does not open this backup (wrong_password)` ; voir aussi `password_required`, `envelope_damaged` et `envelope_unsupported` dans les refus de [Essayer une restauration sur une copie](#backup-restore-dry-run). Un `.zip` ignore les options de mot de passe.
- ❌ Elle se termine avec `1` lorsque des entrées manquent, diffèrent du manifeste ou n'y figurent pas (elle nomme les cinq premières de chaque catégorie), et lorsque le fichier n'est pas une archive qu'elle peut lire : le message se termine alors par un code, comme `archive_unreadable` (fichier qui n'est pas un zip, ou zip tronqué), `manifest_missing`, `manifest_unknown_format` (pas une sauvegarde LibreFolio) ou `manifest_newer_format` (créée par une version plus récente de LibreFolio : vérifiez-la avec cette version ou une version plus récente).

### 🔏 Une archive scellée {: #backup-sealed }

Une archive scellée est un `.tar` dont LibreFolio tire lui-même le mot de passe et qu'il chiffre pour une ou deux clés publiques age : seule la clé privée correspondante l'ouvre, et le serveur qui l'a créée ne le peut pas. Elle est conçue pour les sauvegardes qui s'exécutent seules, par exemple chaque nuit depuis cron. Ce qu'elle contient, comment conserver la clé et comment la changer : [Sauvegardes scellées](backup_sealed.md#sealed).

```bash
# A key pair: the private key into a file of its own (0600, never over a file), the public key printed
pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt

# A sealed archive for that public key (twice --recipient while a key is being changed)
pipenv run ./dev.py backup create --recipient age1…

# The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
pipenv run ./dev.py backup create --sealed

# Check, restore or decrypt it where the private key is
pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
```

- 🗝️ **`keygen`** écrit la clé privée au format de `age-keygen` (`# created:`, `# public key: age1…`, puis `AGE-SECRET-KEY-1…`), lisible uniquement par son propriétaire, et jamais par-dessus un fichier existant (`❌ <path> already exists: a key file is never written over`). Il affiche ensuite `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` et la ligne `age1…`. Exécutez-le sur un ordinateur qui vous appartient, pas sur le serveur : la clé privée doit rester hors du serveur.
- 🔏 **`create --recipient age1…`** scelle pour la clé donnée, `--recipient` deux fois pour deux clés ; **`create --sealed`** scelle pour les clés de `LIBREFOLIO_BACKUP_RECIPIENTS` ([Variables d'environnement](configuration.md)). L'archive est `librefolio-backup-20261015-121500.tar`, avec les règles habituelles de `-o` et des noms. Après les phases d'une archive sécurisée, la sauvegarde affiche `… sealing`, et se termine par `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`
- 🔑 **Aucun mot de passe à fournir.** `--sealed` et `--recipient` s'utilisent sans `--encrypt`, `--password-file` et `--password-stdin`, et `--sealed` sans `--recipient` : la commande s'arrête avant que quoi que ce soit ne soit écrit. Elle n'a pas besoin de terminal, elle s'exécute donc depuis cron telle quelle ; avec Docker, `docker compose exec -T librefolio python dev.py backup create --sealed`.
- 🗝️ **Jamais la clé d'instance**, même générée par LibreFolio : contrairement à une [archive sécurisée](#backup-secure), une archive scellée laisse `secrets/instance.key` de côté.
- 💽 **Espace.** Le scellement écrit le `.tar` à côté du `.lfbk`, le dossier de travail dans `backups/` a donc de nouveau besoin de la taille du `.lfbk`, plus 64 Mo, sinon la sauvegarde s'arrête avec `backup_no_space`.
- 🔓 **`--identity-file`** ouvre une archive scellée pour `inspect`, `restore` et `decrypt`. Il lit un fichier de clé comme l'écrit `age-keygen`, avant tout changement d'utilisateur, comme le fait `--password-file` : un secret Docker fonctionne. La commande vérifie le `.tar` et son manifeste, ouvre le mot de passe avec la clé, le vérifie par rapport à `backup.lfbk`, affiche `🔏 Sealed backup <path>: its password opened with <key file>`, puis copie `backup.lfbk` dans un dossier privé du dossier temporaire du système, supprimé à la fin, et continue comme pour une archive sécurisée avec son mot de passe.
- ❌ Un `.tar` sans `--identity-file` s'arrête avec `sealed_backup_needs_key` ; `--identity-file` avec toute autre archive s'arrête avec `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **Les refus**, chacun à la fin de son message : `sealed_identity_invalid` (le fichier de clé ne contient aucune clé age, ou ne peut pas être lu), `sealed_no_identity` (aucune clé du fichier n'ouvre le mot de passe), `sealed_tar_invalid` (ce ne sont pas les trois fichiers d'une archive scellée, dans l'ordre, en tant que fichiers ustar simples), `sealed_manifest_invalid` (son `manifest.json` ne la décrit pas), `sealed_password_invalid` (ce que la clé a ouvert n'est pas un mot de passe que LibreFolio écrit), puis ceux d'une archive sécurisée : `wrong_password` (ce mot de passe n'ouvre pas `backup.lfbk`) et `envelope_damaged`. Chaque message, avec ce qu'il faut faire : [Créer ou ouvrir une sauvegarde scellée](backup_moving.md#sealed-problems).

### 🧪 Essayer une restauration sur une copie {: #backup-restore-dry-run }

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

`backup restore --dry-run` décompresse l'archive dans une copie, la met à jour et la vérifie, puis vous indique ce que ferait une restauration. La copie est créée dans le répertoire de données, dans `.restore/stage/<id>/`, et supprimée à la fin : la base de données et les fichiers de l'instance ne sont jamais touchés, le serveur peut donc continuer de fonctionner. Sans `--dry-run`, la même vérification constitue la première moitié d'une restauration : voir [Restaurer une archive](#backup-restore).

Une [archive sécurisée](#backup-secure) demande d'abord son mot de passe, comme le fait `inspect`, et est déchiffrée dans le dossier de la copie, sous `.restore/stage/<id>/archive.zip`, qui est supprimé une fois décompressé. Une vérification tuée brutalement laisse cette archive déchiffrée, ou sa partie `archive.zip.part` : le prochain démarrage de LibreFolio la supprime. Ensuite, la vérification passe par six étapes, et s'arrête à la première qui refuse l'archive :

1. **Une archive LibreFolio.** Seule une archive écrite par LibreFolio, avec son `manifest.json`, est acceptée : un répertoire de données zippé à la main ne l'est pas. Chaque entrée est vérifiée avant qu'un seul octet soit écrit : le manifeste la liste (ou l'annonce, pour la clé d'instance d'une archive sécurisée), il s'agit d'un fichier simple (pas un dossier, un lien ni une entrée chiffrée), son nom n'apparaît qu'une fois, même en ignorant la casse, sa taille est celle indiquée dans le manifeste, et l'ensemble tient dans l'espace libre.
2. **Décompressée.** Chaque entrée est écrite dans un nouveau fichier de la copie, jamais à travers un lien ni par-dessus un autre fichier, et son SHA-256 est comparé à celui du manifeste. Ensuite, avant que quoi que ce soit d'autre n'ouvre la copie, le schéma de sa base de données est lu, et rien de celui-ci ne s'exécute : un déclencheur, une vue ou une table virtuelle, que LibreFolio ne crée jamais et dont le SQL s'exécuterait pendant la vérification et dans le serveur après une restauration, fait refuser l'archive (`database_foreign_objects`).
3. **La révision décide.** La révision de migration (Alembic) de la base de données, donnée par le manifeste et confirmée par la base de données elle-même :
    - la révision propre à ce LibreFolio : la base de données est restaurée telle quelle ;
    - une révision plus ancienne : la copie est mise à niveau vers la révision de ce LibreFolio, dans un processus qui lui est propre, arrêté s'il dure plus d'une heure ;
    - une révision que ce LibreFolio ne connaît pas, très probablement issue d'une version plus récente : refusée avec `revision_unknown`. Mettez d'abord LibreFolio à jour : une base de données n'est jamais rétrogradée.

    Ensuite, les [corrections post-migration](cli_tools.md#post-migration-fixes) s'exécutent sur la copie, comme à chaque démarrage.

4. **Vérifiée avant et après.** Avant la mise à niveau, la copie passe le contrôle d'intégrité de SQLite, contient exactement les lignes comptées par le manifeste, et ne contient aucun texte qui ne soit pas en UTF-8 : LibreFolio n'écrit jamais un tel texte, et le serveur ne pourrait pas lire ses lignes après une restauration. Après celle-ci, la copie repasse le contrôle d'intégrité, à la révision de ce LibreFolio. Une migration peut modifier des données, les lignes qui ont changé sont donc un avertissement, pas un refus, tout comme les références brisées (clés étrangères), conservées telles quelles.
5. **Administrateurs.** Le rapport nomme les administrateurs actifs de la sauvegarde. Sans aucun, la restauration est bloquée : personne ne pourrait gérer l'instance après elle.
6. **Secrets enregistrés.** L'instance conserve sa propre [clé d'instance](configuration_secrets.md#instance-key). Lorsque l'archive contient la clé qui a chiffré ses secrets de plugin enregistrés, comme la clé API d'une source de données, ou lorsque vous fournissez cette clé avec `--instance-key-file` ([La clé d'instance d'une autre installation](#backup-restore-instance-key)), ils sont rechiffrés sur la copie avec la clé de cette instance ; les autres sont comptés, pour être saisis de nouveau après la restauration. Une copie sans secrets ne lit même pas la clé de cette instance.

Elle affiche les étapes au fur et à mesure (`… decrypting` pour une archive sécurisée, `… checking`, `… unpacking`, `… upgrading`, `… verifying`), puis son rapport :

- 📦 Qui a créé l'archive et quand (`Made by LibreFolio <version> (<how>) on <date> UTC`), et ce qu'une restauration fait de la base de données : `this LibreFolio's own: restored as it is`, ou `upgraded on the copy to <revision> (<n> migrations)`, suivi de chaque migration avec la première ligne de sa description.
- 🩹 Les corrections post-migration qui ont modifié quelque chose sur la copie, s'il y en a.
- 🔢 Les lignes, les tables et la taille de la base de données, puis les tables dont la mise à niveau a changé les lignes, sous la forme `<table> (<before> → <after>)`, avec `—` pour une table qui n'existait pas.
- 📁 Le nombre et la taille des fichiers ; `Secure backup: decrypted with its password` pour une archive sécurisée ; `Instance key: included` ou `Instance key: not included`, ou `Instance key: not included; given with --instance-key-file` avec cette option ; et les clés enregistrées des fournisseurs de données : `Saved provider keys: <n> re-encrypted with this instance's key`, et `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` pour celles que la clé de l'archive, ou la clé fournie, n'a pas lues, ou lorsqu'il n'y a pas de clé.
- ⚖️ Les totaux de contrôle du registre : les liquidités de chaque courtier dans chaque devise et la quantité de chaque position, additionnées à partir des seules transactions, sans prix, taux de change, coût ni date. La sauvegarde les a enregistrés dans son manifeste, et la vérification les relit sur la copie une fois qu'elle est à jour. Une différence est un avertissement, jamais un refus : une migration peut corriger des données. Le rapport indique l'un des éléments suivants :
    - `Ledger totals: the same as when the backup was made` ;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, puis les lignes qui diffèrent, liquidités d'abord, au maximum 20 : `broker <id>, <currency> cash: <before> → <after>` ou `broker <id>, asset <id> quantity: <before> → <after>`, le montant de la sauvegarde avant la flèche et celui de la copie après, avec `—` pour zéro. `… and <n> more` compte les lignes omises ;
    - `Ledger totals: not recorded in this archive` : une archive créée par un LibreFolio antérieur, d'avant les totaux, n'en enregistre aucun, pas plus qu'une archive dont les totaux n'ont pas pu être lus au moment de sa création ;
    - `Ledger totals: recorded by another version of the method, not compared` ;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 Les administrateurs, et ce qu'une restauration signifiera pour tout le monde : `After a restore you sign in with one of them, with the password of then; every session open now ends.` et `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ Les avertissements, qui laissent une restauration continuer : `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` ou `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, ce que [Les codes de devise qui ne sont pas des codes ISO](cli_tools.md) explique.
- 👥 Une sauvegarde avec plus de comptes actifs que `LIBREFOLIO_MAX_USERS` ne l'autorise ajoute une ligne, affichée une fois, qui ne nomme aucun compte ni aucune adresse : `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. Elle informe seulement : `backup restore --yes` confirme et `--dry-run` se termine avec `0`, comme pour toute sauvegarde.
- ⛔ Le blocage, qui l'interdit : `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

Elle se conclut par `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` et renvoie `0`. Elle renvoie `1` lorsque l'archive est refusée ou la restauration bloquée. Un refus tient en une ligne, la raison suivie d'un code entre parenthèses, comme `❌ The file is not a LibreFolio backup (not_a_backup)`, et rien de la copie n'est laissé.

- 💽 La copie a besoin d'espace libre sur le disque du répertoire de données : tout ce que l'archive contient une fois décompressée, plus deux fois la taille de sa base de données pour la mise à niveau, plus 64 Mo. `backup inspect` affiche ces tailles ; l'archive elle-même est lue là où elle se trouve, jamais copiée. Une archive sécurisée a aussi besoin de place pour son archive déchiffrée, environ sa propre taille, jusqu'à sa décompression. Lorsque l'espace est insuffisant, la vérification s'arrête avant de décompresser quoi que ce soit, avec le nombre d'octets dont elle a besoin (`no_space`) ; un disque qui se remplit pendant la vérification l'arrête aussi.
- 📦 La taille décompressée de l'archive est limitée lorsque `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` définit une limite (« Options principales » dans [Variables d'environnement](configuration.md)). Les tailles déclarées par le manifeste sont additionnées avant la vérification de l'espace libre, et une archive dépassant la limite est refusée avec `unpacked_too_large`, avant toute décompression. `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` devant la commande lève la limite pour cette commande : `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>`, ou `docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>` avec Docker. Une limite qui ne peut pas être lue arrête la commande avant `🔎 Checking … on a copy`, avec le code de sortie `1` : `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.
- 🚦 Une archive est vérifiée à la fois : pendant qu'une autre vérification est en cours, la commande s'arrête avec `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Elle n'utilise jamais la base de données de l'instance : toute installation peut vérifier une archive, y compris une nouvelle, tant que son répertoire de données existe (sinon `❌ No data directory at <path>`). Comme avec `-o`, un chemin relatif part de la racine du projet.
- 🔗 Veillez à ce que `.restore/` et `.restore/stage/` restent de vrais dossiers : un lien, ou un fichier, à leur place arrête la commande avec `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Refus — signification des codes"

    | Code | Pourquoi l'archive est refusée |
    | --- | --- |
    | `not_a_backup` | Pas un zip, ou un zip sans le manifeste que LibreFolio écrit, comme un répertoire de données zippé à la main |
    | `password_required` | Une archive sécurisée, et aucun mot de passe : pas de terminal pour le demander, et ni `--password-file` ni `--password-stdin` |
    | `wrong_password` | Le mot de passe n'ouvre pas l'archive sécurisée : ce n'est pas celui avec lequel elle a été créée, ou le début du fichier a été modifié |
    | `envelope_damaged` | L'archive sécurisée est endommagée, tronquée, ou a été modifiée après sa création |
    | `envelope_unsupported` | L'archive sécurisée provient d'un LibreFolio plus récent, ou demande des paramètres que celui-ci n'accepte pas : mettez d'abord LibreFolio à jour |
    | `instance_key_unreadable`, `instance_key_invalid` | Le fichier fourni avec `--instance-key-file` ne peut pas fournir la clé, ou la clé fait moins de 32 caractères : voir [La clé d'instance d'une autre installation](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | Le fichier ne peut pas être lu, ou le zip est endommagé |
    | `manifest_newer_format` | Le format de l'archive est plus récent que ce que ce LibreFolio lit : mettez d'abord LibreFolio à jour |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | Le manifeste est endommagé ou non valide |
    | `unexpected_entry`, `missing_entry` | L'archive contient une entrée que son manifeste ne liste pas, ou manque des entrées que le manifeste liste ; pour la clé d'instance, une entrée que le manifeste n'annonce pas, ou une entrée qu'il annonce et que l'archive n'a pas |
    | `duplicate_entry` | Une entrée apparaît deux fois, même si seule la casse de son nom change, ou se trouve là où le dossier d'une autre entrée doit être |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | Une entrée est un dossier ou un lien, est chiffrée, ou utilise une compression que LibreFolio n'écrit pas |
    | `too_many_entries` | L'archive contient plus de 500 000 entrées |
    | `checksum_mismatch` | La taille ou le SHA-256 d'une entrée diffère du manifeste : l'archive est endommagée ou a été modifiée |
    | `unpacked_too_large` | Une fois décompressée, l'archive serait plus grande que ce que cette installation accepte pour une restauration, d'après les tailles déclarées par son manifeste : `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. Rien n'est décompressé |
    | `no_space` | Pas assez d'espace libre pour la copie |
    | `stage_failed` | La copie n'a pas pu être écrite : l'erreur affichée juste au-dessus en donne la cause |
    | `database_damaged` | La base de données de la sauvegarde échoue au contrôle d'intégrité de SQLite, avant ou après la mise à niveau, SQLite ne peut pas lire son schéma, ou elle contient du texte qui n'est pas en UTF-8 (un autre programme y a écrit, ou elle a été modifiée) |
    | `database_foreign_objects` | La base de données de la sauvegarde contient un déclencheur, une vue ou une table virtuelle, que LibreFolio ne crée jamais : elle n'a pas été créée par LibreFolio, ou a été modifiée. Utilisez une autre sauvegarde |
    | `manifest_mismatch` | La base de données de la sauvegarde n'est pas celle que décrit son manifeste |
    | `revision_missing` | La base de données de la sauvegarde n'enregistre aucune révision de migration |
    | `revision_unknown` | La sauvegarde provient d'un LibreFolio plus récent, ou pas de celui-ci : mettez LibreFolio à jour, puis vérifiez-la de nouveau |
    | `upgrade_failed` | La mise à niveau de la copie a échoué ou a duré plus d'une heure (l'erreur affichée juste au-dessus en donne la cause), ou n'a pas atteint la révision de ce LibreFolio |
    | `post_migration_failed` | Une correction post-migration a échoué sur la copie : l'erreur affichée juste au-dessus en donne la cause |
    | `head_unknown` | Ce LibreFolio ne peut pas lire ses propres scripts de migration |

### ♻️ Restaurer une archive {: #backup-restore }

```bash
# Check the archive on a copy, then restore it at the next start of the server
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Sans `--dry-run`, `backup restore` exécute la même vérification sur une copie et affiche le même rapport ([Essayer une restauration sur une copie](#backup-restore-dry-run)). Lorsque l'archive peut être restaurée, elle vous demande de confirmer :

```text
   Type "restore" to restore this archive at the next start of the server:
```

- ⌨️ Saisissez `restore`, en minuscules ; les espaces autour ne comptent pas. Toute autre saisie, y compris `Restore` ou une ligne vide, se termine par `Nothing restored: the copy was removed.` et le code de sortie `1`.
- 🤖 `--yes` (`-y`) confirme sans demander. Sans terminal pour demander, dans un script par exemple, il est obligatoire : sinon la commande s'arrête avec `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.` et se termine avec `1`. Une [archive sécurisée](#backup-secure) y a aussi besoin de son mot de passe : ajoutez `--password-file` ou `--password-stdin`.

Une fois confirmée, la commande se termine avec `0` et indique :

```text
✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
   That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
   ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
```

Rien n'a encore changé : le serveur continue de fonctionner sur ses données, et la copie vérifiée attend dans `.restore/stage/<id>/`, quel que soit le temps que cela prend. Redémarrez LibreFolio quand cela vous convient : arrêtez le serveur entier, puis [démarrez-le](cli_tools.md#start-the-server) de nouveau ; avec Docker, `docker compose restart librefolio` ([Sauvegarder avec Docker](#backup-docker)). Si le serveur est arrêté, son prochain démarrage applique la restauration.

Ce démarrage l'applique avant de lire la moindre donnée :

1. 🛑 **Uniquement un démarrage du serveur entier.** Chaque processus serveur LibreFolio détient un verrou sur le répertoire de données dès le début de son démarrage, avant de lire la moindre donnée, jusqu'à sa sortie. Un démarrage qui le trouve détenu par un autre processus, comme un worker qu'uvicorn redémarre à côté de ses pairs en cours d'exécution avec `--workers`, ou un second serveur sur le même répertoire de données, laisse la restauration en attente (`server_running`). Redémarrez le serveur entier, jamais un seul worker. Un démarrage qui trouve la restauration appliquée par un autre serveur encore en cours, ou par un autre démarrage, s'arrête au lieu de servir des données dont la restauration n'est pas validée.
2. 🔀 **L'échange.** Les dossiers `sqlite/`, `custom-uploads/`, `broker_reports/` et `scenario_catalog/` de l'instance échangent leur place avec ceux de la copie. Chaque déplacement est un renommage à l'intérieur du répertoire de données : instantané, quelle que soit la taille. Les dossiers propres à l'instance sont mis de côté dans `.restore/previous/`.
3. 🔒 **Ce qui reste.** `secrets/`, `logs/`, `scheduler_state.json` et `backups/` ne sont pas touchés : l'instance conserve sa [clé d'instance](configuration_secrets.md#instance-key), ses journaux et ses archives.
4. ✅ **Le premier démarrage doit aboutir.** Le démarrage continue, sur les données restaurées, que la vérification a déjà amenées à la révision de ce LibreFolio. Une fois qu'il a abouti, avant de répondre à qui que ce soit, il met fin à toutes les sessions, révoque les liens à usage unique de la sauvegarde, et supprime les anciennes données de l'instance et la copie : la restauration est terminée.
5. ↩️ **Sinon, retour à l'état précédent.** Si ce premier démarrage échoue, sur une migration qui échoue ou un fichier endommagé, le démarrage suivant remet de lui-même les données dans l'état où elles étaient avant, et enregistre la restauration comme annulée, avec la raison ([Suivre ou annuler une restauration](#backup-pending)). Avec Docker, le conteneur redémarre de lui-même après un démarrage échoué, les données reviennent donc sans vous ; si rien ne redémarre le serveur, démarrez-le vous-même.

Après la restauration :

- 🔑 Tout le monde se reconnecte, sur chaque appareil, avec un compte de la sauvegarde et le mot de passe qu'il avait alors. Le rapport de la vérification nomme les administrateurs de la sauvegarde.
- 🔗 Aucun lien envoyé avant la restauration ne fonctionne plus (invitations, réinitialisations de mot de passe, vérifications d'adresse e-mail), pas même ceux que la sauvegarde contenait encore : envoyez-en de nouveaux.
- 📧 Un compte que la sauvegarde contenait encore en attente de sa vérification d'adresse e-mail perd aussi son lien, et cesse d'attendre : la page de connexion ne peut plus lui envoyer un autre lien, et répond que le compte est désactivé. Un administrateur l'active dans [Utilisateurs et invitations](users.md#actions), et son adresse reste non vérifiée ; ou le supprime ([Supprimer un compte](users.md#delete)), afin que son propriétaire s'inscrive de nouveau et reçoive un nouveau lien. Un tel compte ne s'est jamais connecté, il ne contient donc aucune donnée.
- 🆘 Si personne ne se souvient du mot de passe d'un administrateur à cette époque, la personne qui gère le serveur crée un lien de réinitialisation avec [`user reset-link`](cli_tools.md), ou définit un nouveau mot de passe avec `user reset`. Une fois connecté, un administrateur envoie des liens de réinitialisation aux autres depuis [Utilisateurs et invitations](users.md#reset-links).

Bon à savoir :

- 🚦 Une restauration à la fois : pendant qu'une attend ou est en cours d'application, `backup restore` s'arrête avant la vérification avec `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)` et se termine avec `1`. Elle s'arrête aussi là lorsqu'elle ne peut pas lire l'état de la restauration, puisqu'elle ne peut pas déterminer si une restauration attend : `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, code de sortie `1`, rien n'est vérifié. `--dry-run` fonctionne toujours.
- ❌ Si la confirmation elle-même est refusée, la commande affiche une ligne qui se termine par un code, supprime la copie et se termine avec `1` : `restore_stage_outdated` lorsque LibreFolio a été mis à jour entre la vérification et la confirmation, `restore_stage_expired` lorsque la question a attendu plus de 24 heures, `restore_already_pending` lorsqu'une autre restauration a été confirmée entre-temps. Relancez la commande ; après `restore_stage_outdated`, vérifiez de nouveau l'archive.
- 📍 Exécutez-la là où le serveur s'exécute, dans le conteneur avec Docker : la restauration est enregistrée pour le chemin du répertoire de données, et un serveur qui trouve son répertoire de données sous un autre chemin ne l'applique pas.
- 🔗 Veillez à ce que les quatre dossiers restent de vrais dossiers du répertoire de données : un dossier qui est un lien, ou qui est monté séparément, ne peut pas être échangé. Le démarrage laisse alors les données telles quelles, et enregistre la restauration comme annulée avec `swap_failed`.
- 💽 L'échange n'a pas besoin d'espace propre : la copie créée par la vérification devient les données de l'instance, et les anciennes données sont supprimées une fois le premier démarrage terminé.
- 🗝️ La restauration conserve la clé d'instance de cette installation. Lorsque l'archive contient la clé de l'installation qui l'a créée (une [archive sécurisée](#backup-secure), lorsque LibreFolio a généré cette clé), la vérification a déjà rechiffré ses secrets enregistrés avec la clé de cette installation. Pour toute autre archive d'une autre installation, fournissez la clé de cette installation avec `--instance-key-file`, et la vérification les rechiffre aussi ([La clé d'instance d'une autre installation](#backup-restore-instance-key)). Sinon, ils ne peuvent pas être lus ici : le rapport les compte, pour les saisir de nouveau après la restauration, à moins que vous ne remettiez d'abord la clé de cette installation ([Secrets enregistrés et clé d'instance](configuration_secrets.md#plugin-secrets)). Voir « La clé d'instance se trouve uniquement dans une archive sécurisée » ci-dessus.

### 🗝️ La clé d'instance d'une autre installation {: #backup-restore-instance-key }

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Une archive en clair laisse la clé d'instance de côté, et une archive sécurisée dont la clé provenait de l'environnement fait de même : les secrets de plugin enregistrés qu'elle contient, comme la clé API d'une source de données, ne s'ouvrent qu'avec la clé de l'installation qui l'a créée. `--instance-key-file FILE` fournit cette clé à `backup restore`, avec ou sans `--dry-run` : la vérification rechiffre ces secrets sur la copie avec la clé de cette instance, qui reste telle quelle.

- 📄 Le fichier contient la clé d'instance de l'ancienne installation : une copie de son `secrets/instance.key`, le fichier désigné par sa variable `LIBREFOLIO_INSTANCE_KEY_FILE`, tel quel, ou la valeur de sa variable `LIBREFOLIO_INSTANCE_KEY` écrite dans un fichier comme elle était écrite dans la variable, espaces compris. Seule une marque d'ordre des octets en son début et les sauts de ligne à sa fin sont supprimés, comme pour `--password-file` : une clé qui fonctionnait comme variable fonctionne de la même manière dans le fichier.
- 🔑 La commande le lit d'abord, en tant qu'utilisateur qui l'a lancée, avant de passer au propriétaire du répertoire de données, comme elle lit `--password-file` : avec `docker compose exec`, un secret Docker que seul root peut lire fonctionne. Le fichier suit la même règle que `--password-file`, « Un fichier auquel la commande peut se fier » dans [Une archive sécurisée](#backup-secure) : conservez-le hors du répertoire de données.
- 🙈 La clé n'est jamais affichée. Seule la ligne de commande la prend : l'interface web ne prend jamais de clé, et une restauration depuis Paramètres › Administration › Sauvegarde compte ces secrets comme illisibles.
- 📁 Le rapport indique `Instance key: not included; given with --instance-key-file`, puis `Saved provider keys: <n> re-encrypted with this instance's key`.
- ℹ️ Une archive qui contient sa propre clé est restaurée avec elle, quel que soit le contenu du fichier : le rapport ajoute `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ Une clé qui ne lit aucun des secrets enregistrés n'est pas la clé de l'installation qui a créé la sauvegarde : le rapport ajoute `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, avant la ligne qui les compte, pour les saisir de nouveau après la restauration. Lorsque la clé propre à cette instance ne peut pas être utilisée, ou lorsqu'elle n'a pas encore de clé et que la vérification ne peut pas en créer une, par exemple lorsque `secrets/` ne peut pas être écrit, rien n'est rechiffré, quelle que soit la clé fournie, et la ligne est à la place `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>` : le problème du journal de démarrage `The instance key cannot be used: …` (« Contrôles au démarrage » dans [Variables d'environnement](configuration.md)), ou, sans clé, `<path>: there is no instance key yet, and it could not be created`. Les secrets déjà sous la clé de cette instance, comme dans une archive de cette même instance, sont laissés tels quels, quelle que soit la clé fournie.
- ❌ Elle se termine avec `1`, avant que quoi que ce soit ne soit vérifié, lorsque le fichier ne peut pas fournir la clé : `❌ instance key file: <path> does not exist (instance_key_unreadable)`, ou `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. Une clé de moins de 32 caractères l'arrête avant la création de la copie : `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Suivre ou annuler une restauration {: #backup-pending }

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

`backup pending` ne change rien et se termine avec `0`, sauf lorsqu'elle ne peut pas lire l'état de la restauration : voir [Un état de restauration illisible](#backup-pending-unreadable) ci-dessous. `--json` et `--recover` sont conçus pour les scripts : voir [Pour les scripts](#backup-pending-json). Sinon, elle affiche l'un des éléments suivants :

| Elle affiche | Ce que cela signifie |
| --- | --- |
| `ℹ️ No restore waits for the next start` | Aucune restauration n'a été confirmée, ou la dernière a été abandonnée |
| `⏳ A restore waits for the next start of the server`, then `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmée, pas encore appliquée. `<who>` vaut `cli` pour cette commande, sinon le nom d'utilisateur de l'administrateur qui l'a confirmée |
| `⏳ A restore is being applied by the server` | Un démarrage l'a appliquée et n'est pas encore terminé. Si ce démarrage est mort, le suivant remet les données en place |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | La restauration est terminée |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | La restauration a été annulée, pour la raison ci-dessous |

Lorsqu'un démarrage a trouvé une restauration en attente et ne l'a pas appliquée, une ligne supplémentaire en indique la raison, et la restauration continue d'attendre :

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)` : une sauvegarde était en cours au démarrage du serveur, par exemple un `backup create` depuis la ligne de commande.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)` : le serveur a trouvé son répertoire de données sous un autre chemin que celui où la restauration a été confirmée, par exemple une copie du répertoire de données. Abandonnez-la avec `--cancel`, puis exécutez `backup restore` là où le serveur s'exécute.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)` : un worker a été redémarré alors que les autres continuaient de servir (`--workers`), ou un autre serveur utilise le même répertoire de données. Redémarrez le serveur entier.

| Code | `<reason>` | Que faire |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | Le journal de ce démarrage en donne la cause |
| `swap_interrupted` | `the start that applied it was interrupted` | Rien : un démarrage s'est arrêté pendant l'échange, et le suivant l'a annulé |
| `swap_failed` | `its folders could not be moved into place` | Faites en sorte que les quatre dossiers soient de vrais dossiers du répertoire de données, ni des liens ni des montages séparés |
| `stage_missing` | `its checked copy was gone` | La copie dans `.restore/stage/` a été supprimée ou modifiée : vérifiez de nouveau l'archive |

Une annulation supprime aussi les données restaurées et la copie : pour réessayer, exécutez de nouveau `backup restore`. Si même la remise en place des données échoue, à cause d'une erreur de disque ou de permission par exemple, LibreFolio ne démarre pas : son journal contient `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, et chaque démarrage réessaie.

#### 🧩 Un état de restauration illisible {: #backup-pending-unreadable }

L'état de la restauration, `.restore/restore.json`, peut devenir illisible : son propriétaire ou ses permissions ont changé, une erreur de disque, un lien ou un dossier à sa place, ou un contenu que LibreFolio n'a pas écrit. Une restauration peut alors s'être arrêtée à mi-chemin, et LibreFolio ne peut pas dire quelles données elle détient. `backup pending` l'indique et se termine avec `1` :

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` vaut `io` (le système de fichiers le refuse : redonnez `.restore/` et ses fichiers à l'utilisateur qui exécute LibreFolio, puis exécutez de nouveau `backup pending`, ce qui peut suffire), `not_a_file` ou `invalid`. Tant que l'état ne peut pas être lu, aucune copie vérifiée n'est supprimée, ni par le nettoyage du serveur ni par Paramètres › Administration › Sauvegarde, et aucune restauration ne peut être confirmée.

`backup pending --recover previous`, avec LibreFolio arrêté, remet en place les données d'avant d'après ce qu'indiquent les dossiers : chaque dossier conservé dans `.restore/previous/` retourne à sa place, et celui qu'il remplace va dans `.restore/failed/`. Une restauration qui a été validée n'a conservé aucune donnée d'avant, ses données restent donc. L'état illisible est conservé sous `.restore/restore.json.unreadable-<date>` pour inspection, et n'est plus jamais lu. Démarrez ensuite LibreFolio sur les données d'avant, ou restaurez de nouveau une sauvegarde avec `backup restore`. Pendant que LibreFolio fonctionne, elle s'arrête avec `(restore_in_use)` et se termine avec `5` ; avec un état qu'elle peut lire, ou aucun, elle s'arrête avec `(restore_nothing_to_recover)` et se termine avec `3` : les codes de sortie sont dans le tableau de [Pour les scripts](#backup-pending-json). Exécutée deux fois, la seconde exécution ne change rien.

`--cancel`, identique à `--recover cancel` mais avec les codes de sortie ci-dessous, abandonne la restauration en attente, avec sa copie vérifiée, quelle que soit la personne qui l'a confirmée : `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is`, code de sortie `0`. Si la copie ne peut pas être supprimée, à cause d'une erreur de permission ou de disque par exemple, la restauration est abandonnée malgré tout, code de sortie `0`, avec deux lignes à la place : `✅ The restore waiting for the next start was dropped: the data stays as it is` et `⚠️ Its checked copy could not be removed: it goes when its check expires`. Lorsque la suppression a échoué avec une erreur, le journal au-dessus contient l'avertissement `The copy of a cancelled restore could not be removed: it goes when its check expires` ; une copie laissée sans erreur, comme une copie contenant un dossier en lecture seule, n'en a aucun. LibreFolio réessaie à son premier démarrage une fois que la vérification date de 24 heures. Si la restauration elle-même ne peut pas être abandonnée, à cause d'une erreur de système de fichiers avant que cela ne soit fait (son verrou, ou la suppression de son état) : `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)`, code de sortie `1`. Lorsque l'état de la restauration ne peut pas être lu : la ligne `restore_state_unreadable` de `backup pending`, code de sortie `1`. Lorsqu'aucune restauration n'attend, ou qu'une est déjà en cours d'application : `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)`, code de sortie `1`.

#### 🤖 Pour les scripts : --json et --recover {: #backup-pending-json }

Un script, ou une machine qui atteint le serveur via `ssh`, lit l'état avec `--json` et agit avec `--recover CHOICE`. Les deux sont conçus pour être exécutés sans personne : rien n'est jamais demandé au terminal, et les codes de sortie sont fixes.

**La ligne JSON.** Avec `--json`, `backup pending` écrit exactement une ligne sur stdout : un objet JSON, puis un saut de ligne, sans couleur. Tout ce qu'elle dirait autrement, et les lignes de journal de LibreFolio, vont vers stderr. Elle se termine avec `0` chaque fois que la ligne a été affichée : un état illisible est un état, pas un échec.

| Clé | Valeur |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` ou `unreadable` |
| `reason` | Pourquoi : la raison d'annulation d'un état `rolled_back` (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), ou `io`, `not_a_file`, `invalid` pour un état `unreadable` ; `null` sinon |
| `waiting` | Pourquoi un démarrage n'a pas appliqué une restauration qui attend : `backup_running`, `other_data_directory`, `server_running`, ou `null` |
| `backup_created_at` | Quand la sauvegarde de la restauration a été créée, sous la forme `2026-10-23T03:00:12Z` (UTC) ; `null` sans état, ou avec un état illisible |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` lorsque les données d'avant un échange sont conservées dans `.restore/previous/`, sinon `{"present": false, "at": null}` |
| `choices` | Les mots que `--recover` accepte maintenant, dans le tableau ci-dessous |

Après un `--recover`, la ligne décrit l'état **après** celui-ci et ajoute `recover`, `{"choice": "<word>", "done": true}` ou `false`, et, lorsque le code de sortie n'est pas `0`, `error`, le mot du tableau des codes de sortie.

| `state` | Cela signifie | `choices` |
| --- | --- | --- |
| `none` | Aucune restauration n'a été confirmée, ou la dernière a été abandonnée | aucune |
| `pending` | Une restauration attend le prochain démarrage | `cancel` |
| `in_progress` | Un démarrage l'applique, ou l'a appliquée et n'est pas encore terminé | aucune |
| `committed` | La dernière restauration est terminée | aucune |
| `rolled_back` | La dernière restauration a été annulée, avec sa `reason` | aucune |
| `unreadable` | L'état de la restauration ne peut pas être lu : [Un état de restauration illisible](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

La ligne ne contient jamais de nom d'utilisateur, d'adresse e-mail, de chemin ni d'identifiant : qui a confirmé la restauration, le répertoire de données et la copie vérifiée n'y figurent pas. `safety_copy.at` est le moment où la restauration a été appliquée, ou, avec un état illisible, le moment où `.restore/previous/` a changé pour la dernière fois.

**Les codes de sortie.** `--recover previous` remet en place les données d'avant lorsque l'état ne peut pas être lu, avec LibreFolio arrêté ; `--recover cancel` abandonne la restauration en attente, avec sa copie vérifiée. Les codes de sortie sont les mêmes avec ou sans `--json` :

| Sortie | Quand | `error` dans la ligne |
| --- | --- | --- |
| `0` | Terminé : les données d'avant sont revenues, ou la restauration en attente a été abandonnée | aucune |
| `2` | Une erreur d'utilisation : `--recover` sans choix, `--recover` avec `--cancel`, ou `--json` avec `--cancel` (utilisez `--recover cancel`) | aucune : la ligne n'est pas écrite |
| `3` | Rien à récupérer : aucun état de restauration, ou le choix a déjà été effectué. | `nothing_to_recover` |
| `4` | Le choix n'est pas valide dans cet état, comme `previous` alors que l'état peut être lu, `cancel` alors qu'il ne peut pas l'être, ou un mot qui n'est pas un choix : rien ne change | `choice_not_valid` |
| `5` | Cela a échoué : LibreFolio fonctionne sur ce répertoire de données (`restore_in_use`), un dossier n'a pas pu être remis en place (`restore_apply_failed`), la restauration n'a pas pu être abandonnée (`failed`) : rien n'est déclaré terminé. Avec un répertoire de données manquant, `5` aussi, mais aucune ligne n'est écrite : stdout reste vide et stderr en indique la raison | `restore_in_use`, `restore_apply_failed` ou `failed` |

Exécuté de nouveau, un choix ne change rien : le second `--recover previous` ne trouve aucun état illisible, ne déplace aucun dossier, n'ajoute rien à `.restore/failed/`, et se termine avec `3` ; un second `--recover cancel` fait de même. Un script peut donc répéter `previous` ou `cancel` jusqu'à lire `0` ou `3`.

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

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

`backup decrypt` écrit le zip que contient une [archive sécurisée](#backup-secure) : l'archive que `backup create` écrit sans mot de passe, avec `secrets/instance.key` lorsque l'archive sécurisée contient la clé. `inspect` et `restore` prennent ce zip comme n'importe quel autre, et sa clé rechiffre encore les secrets enregistrés. Pour restaurer une archive sécurisée, vous n'en avez pas besoin : `backup restore` prend le `.lfbk` tel quel.

- 🔑 Elle demande le mot de passe une fois, ou le lit avec `--password-file` ou `--password-stdin` ([Une archive sécurisée](#backup-secure)).
- 🆕 `-o` (`--output`) est obligatoire, et correspond au fichier zip : il ne doit pas encore exister. Un fichier existant est refusé avant que le mot de passe ne soit demandé, `❌ <path> already exists: choose another name`, et rien n'est écrit. Comme avec `create`, un chemin relatif part de la racine du projet.
- 🔒 Le zip contient les données de chaque utilisateur en clair, et seul son propriétaire peut le lire (`0600`) : l'utilisateur qui a lancé la commande, ou l'utilisateur du serveur lorsque la commande est passée à celui-ci. Elle se termine avec `✅ Decrypted: <path> (<size>)` et `🔒 It holds every user's data in clear: keep it private, and remove it once used.` Lorsque l'archive sécurisée contient la clé d'instance, une dernière ligne ajoute `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- 🟢 Elle n'a besoin d'aucun répertoire de données, et fonctionne avec le serveur en marche ou arrêté. Lorsqu'il en existe un et que vous l'exécutez en tant que root, par exemple avec `docker compose exec`, elle lit d'abord un `--password-file`, en tant que root (un secret Docker appartenant à root fonctionne), puis passe au propriétaire du répertoire de données, comme le font les autres commandes : le zip appartient alors à l'utilisateur du serveur, et `-o` doit être un emplacement où cet utilisateur peut écrire ([Sauvegarder avec Docker](#backup-docker)). Si elle ne peut pas changer d'utilisateur, elle s'arrête avant de lire l'archive ou de demander le mot de passe, avec le message des autres commandes : `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ Elle se termine avec `1` lorsqu'elle ne peut pas lire le fichier, par exemple un fichier que seul root peut lire une fois que la commande s'exécute en tant qu'utilisateur du serveur (`❌ Cannot read <path>: <reason> (archive_unreadable)`, avant que le mot de passe ne soit demandé), lorsque le fichier n'est pas une archive sécurisée (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), lorsque le mot de passe ne l'ouvre pas (`wrong_password`), lorsqu'elle est endommagée (`envelope_damaged` : rien n'est laissé à `-o`) ou provient d'un LibreFolio plus récent (`envelope_unsupported`), et lorsqu'elle ne peut pas écrire à `-o` (`❌ Cannot write <path>: <reason>`, une fois le mot de passe fourni : rien n'y est laissé).

### 🚚 Utiliser une archive sur une autre installation

[`backup restore`](#backup-restore) restaure une archive sur l'installation où vous l'exécutez, et conserve les `secrets/` de cette installation. Pour démarrer à la main une autre installation sur les données d'une archive, avec les `secrets/` de l'installation qui l'a créée, par exemple lorsque vous déplacez LibreFolio :

1. **Arrêtez LibreFolio** sur l'installation qui reçoit les données.
2. **Décompressez l'archive dans un [répertoire de données](filesystem.md) vide** (`LibreFolio-data/` avec Docker Compose) : s'il contient quoi que ce soit, déplacez-le d'abord. Rien des anciennes données ne doit se mélanger à celles de l'archive, pas même `app.db-wal` et `app.db-shm` de SQLite. Une archive sécurisée est d'abord déchiffrée dans son zip ([Déchiffrer une archive sécurisée](#backup-decrypt)).
3. **Remettez `secrets/`** dans le répertoire de données, depuis la copie que vous avez sauvegardée séparément. Le zip d'une archive sécurisée qui contient la clé apporte déjà `secrets/instance.key` : donnez au dossier le mode `0700` et au fichier le mode `0600` (`chmod`), sinon le journal de démarrage contient un avertissement.
4. **Démarrez LibreFolio**, la version qui a créé l'archive ou une version plus récente : les migrations en attente s'exécutent d'elles-mêmes au démarrage.

Bon à savoir :

- 🧪 Avant l'étape 1, vérifiez l'archive sur l'installation qui la reçoit, avec `backup restore <archive> --dry-run` ([Essayer une restauration sur une copie](#backup-restore-dry-run)) : sans rien changer, elle vous indique si ce LibreFolio peut prendre l'archive, quelles migrations son démarrage appliquera, et avec quels administrateurs vous vous connecterez.
- ⛔ LibreFolio ne rétrograde jamais une base de données : une archive créée par une version plus récente nécessite cette version ou une version plus récente, et une version plus ancienne ne démarre pas sur elle. `backup inspect` affiche la version qui a créé l'archive, et `backup restore --dry-run` refuse une telle archive avec `revision_unknown`.
- 🧹 Le `manifest.json` laissé à la racine du répertoire de données est inoffensif : vous pouvez le supprimer.
- 👤 Avec Docker, le conteneur attribue le répertoire de données à son utilisateur à chaque démarrage, le propriétaire des fichiers décompressés n'a donc pas d'importance. Sur une installation hôte, décompressez en tant qu'utilisateur qui exécute LibreFolio, afin que les fichiers lui appartiennent.
- 🗝️ La clé d'une archive sécurisée ne fonctionne que là où ni `LIBREFOLIO_INSTANCE_KEY` ni `LIBREFOLIO_INSTANCE_KEY_FILE` ne sont définies : une clé définie à cet endroit l'emporte sur `secrets/instance.key`. Ne la mettez jamais à la place d'une clé déjà utilisée : ce qui a été enregistré sous cette clé deviendrait illisible. Une installation dotée de sa propre clé reprend l'archive avec [`backup restore`](#backup-restore), qui rechiffre les secrets enregistrés.

### 🐳 Sauvegarder avec Docker {: #backup-docker }

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

- 👤 `docker compose exec` s'exécute en tant que root : la commande passe au propriétaire du répertoire de données, `backup decrypt` compris, donc tout ce qu'elle écrit appartient à l'utilisateur du serveur. Si elle ne peut pas changer d'utilisateur, elle s'arrête et vous demande de l'exécuter en tant que cet utilisateur : `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, avec les numéros indiqués dans le message.
- 📂 `-o` et les archives de `inspect` et `restore` sont des chemins à l'intérieur du conteneur, où le répertoire de données est `/app/backend/data/prod-docker`. L'archive affichée par `backup create` se trouve dans un dossier qui lui est propre, par exemple `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`. Pour vérifier une archive qui se trouve sur l'hôte, copiez-la d'abord dans `LibreFolio-data/`, par exemple dans `LibreFolio-data/backups/`. Pour écrire l'archive ailleurs que dans `LibreFolio-data/backups/`, utilisez un dossier monté depuis l'hôte dans lequel l'utilisateur du serveur peut écrire : partout ailleurs, elle reste à l'intérieur du conteneur et est perdue lorsque le conteneur est recréé.
- 🔑 `restore` et `decrypt` lisent aussi l'archive en tant qu'utilisateur du serveur : une archive écrite par `backup create` convient, mais une archive que vous avez copiée vous-même doit être lisible par cet utilisateur, sinon elles s'arrêtent avec `archive_unreadable`. Avec l'image officielle, `sudo chown 1000:1000 <archive>` sur l'hôte l'attribue à cet utilisateur.
- ⌨️ `docker compose exec` fournit à la commande un terminal pour demander. Sans terminal, par exemple avec `docker compose exec -T` dans un script, ajoutez `--yes`.
- 🔐 Pour une [archive sécurisée](#backup-secure), `--encrypt` demande le mot de passe sur ce terminal. Avec `-T`, depuis cron par exemple, fournissez-le avec `--password-file` et un secret Docker, comme `/run/secrets/backup_password` : [l'exemple](backup_restore.md#command-line) dans Sauvegarde, restauration et déplacement de votre instance montre les lignes à ajouter à `docker-compose.yml`. `backup decrypt` passe aussi à l'utilisateur du serveur, son zip appartient donc à cet utilisateur : donnez-lui un `-o` dans lequel cet utilisateur peut écrire, dans `LibreFolio-data/backups/` ou un dossier monté depuis l'hôte, par exemple `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 Une [archive scellée](#backup-sealed) n'a pas besoin de terminal : `docker compose exec -T librefolio python dev.py backup create --sealed` lit `LIBREFOLIO_BACKUP_RECIPIENTS` dans l'environnement du conteneur, que `env_file: .env` remplit ; après une modification de `.env`, `docker compose up -d` recrée le conteneur avec. Pour en ouvrir une dans le conteneur, donnez à `--identity-file` un chemin à l'intérieur de celui-ci ; mieux, ouvrez-la sur votre ordinateur, là où se trouve la clé privée ([Ouvrir une sauvegarde scellée](backup_sealed.md#sealed-open)).
- 🔁 Après un premier démarrage qui échoue sur les données restaurées, le conteneur redémarre de lui-même (`restart: unless-stopped`, dans les deux fichiers compose fournis par LibreFolio), et ce démarrage remet les données dans l'état où elles étaient avant.
- 🔒 Sur l'hôte, les archives appartiennent à l'utilisateur du conteneur, et seul cet utilisateur peut les lire : si votre utilisateur hôte est un autre, copiez-les avec `sudo cp -a`.
- 💻 Depuis une copie des sources, `./dev.py docker exec backup create` fait la même chose.

---

## 🔗 Voir aussi

- 📄 **[Outils en ligne de commande](cli_tools.md)** — Démarrer le serveur, gérer les utilisateurs, maintenir la base de données, …
