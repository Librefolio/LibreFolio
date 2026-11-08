# 🏠 Sauvegardes : déplacement et dépannage

Cette page du guide des sauvegardes couvre le **déplacement** de LibreFolio d'une installation à une autre (d'un hébergement vers un serveur à vous, ou l'inverse) et ce qu'il faut faire **en cas de problème** avec une sauvegarde ou une restauration.

Le reste du guide commence à [Sauvegarde, restauration et déplacement de votre instance](backup_restore.md).

---

## 🏠 Rapatriez votre LibreFolio {: #bring-home }

Une archive déplace votre LibreFolio d'une installation à une autre. Deux méthodes :

| Méthode | Quand | Où |
| --- | --- | --- |
| **Restauration** | La restauration vérifie l'archive sur une copie avant que quoi que ce soit ne change ; avec Docker, elle prend une sauvegarde sécurisée (`.lfbk`) telle quelle, et c'est la méthode la plus simple | Paramètres › Administration › Sauvegarde, ou `backup restore` ([Restaurer sur cette installation](backup_restore.md#restore)) |
| **À la main** | Le dossier de données de la destination est vide, ou n'existe pas encore : décompressez-y le zip avant le premier démarrage | Terminal du serveur de destination, [ci-dessous](#by-hand) |

Dans les deux cas, la destination utilise la même version de LibreFolio ou une version plus récente ([Jamais de retour en arrière](#never-backwards)).

### ✋ À la main : décompressez avant le premier démarrage {: #by-hand }

À savoir avant de commencer :

- 🔎 **Rien ne vérifie l'archive au préalable.** Une archive endommagée, ou provenant d'un LibreFolio plus récent, se manifeste lorsque le démarrage échoue, et certains dommages n'apparaissent que plus tard, lorsqu'une page lit les données qu'elle touche. Une restauration la vérifie sur une copie avant que quoi que ce soit ne change. Pour vérifier une archive avant de la décompresser à la main, utilisez une installation de LibreFolio qui **tourne déjà** : `backup inspect <archive>` compare chaque fichier avec le manifeste et, pour un zip, n'écrit rien ; `backup restore <archive> --dry-run` effectue toute la vérification d'une restauration, sur une copie (« Vérifier une archive » et « Essayer une restauration sur une copie » dans [Outils d'administration CLI](cli_tools.md)). L'essai à blanc travaille dans le dossier de données de cette installation : ne le pointez jamais vers le dossier vide que vous êtes sur le point de remplir.
- 📖 Les étapes pour toute installation, y compris celle sur l'hôte : « Utiliser une archive sur une autre installation » dans [Outils d'administration CLI](cli_tools.md).

Les étapes, avec Docker Compose :

1. **Serveur source — Paramètres › Administration › Sauvegarde, ou terminal.** Créez une sauvegarde et apportez-la au serveur de destination ([Créer une sauvegarde](backup_restore.md#create)). Si c'est une sauvegarde en clair, apportez aussi le dossier `secrets/` de son dossier de données : l'archive ne le contient pas.

    Résultat : l'archive (`.zip` ou `.lfbk`) est sur le serveur de destination.

2. **Serveur de destination — terminal, dossier de `docker-compose.yml`.** Le dossier de données `LibreFolio-data` doit être vide, ou ne pas encore exister. Si LibreFolio a déjà démarré dessus, arrêtez-le (`docker compose down`) et mettez d'abord `LibreFolio-data` de côté.

    Résultat : aucune autre donnée ne se mélange à celles de l'archive.

3. **Seulement pour une sauvegarde sécurisée (`.lfbk`) — terminal d'une installation où la ligne de commande de LibreFolio est disponible.** Un `.lfbk` n'est pas un zip : transformez-le en zip avec `backup decrypt`.

    ```bash
    # Host installation
    pipenv run ./dev.py backup decrypt librefolio-backup-20261015-121500.lfbk -o librefolio-backup-20261015-121500.zip

    # Docker, in a running LibreFolio container: the paths inside it, and the zip where the container's user can write
    docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
    ```

    Résultat : le zip à décompresser à l'étape 4. À savoir :

    - 🔓 Le mot de passe est demandé au terminal, ou lu avec `--password-file` ou `--password-stdin`.
    - 🚫 Un `-o` qui existe déjà est refusé, et rien n'est écrit : la commande ne remplace jamais un fichier.
    - 🔒 Seul le propriétaire lit le zip (`0600`) : l'utilisateur qui a exécuté la commande ou, avec Docker, l'utilisateur du conteneur.
    - 🗑️ Le zip contient les données de tous les utilisateurs en clair : supprimez-le une fois décompressé.
    - 🔑 Si la sauvegarde contient la clé d'instance, la commande ajoute `🔑 It also holds the instance key: with it, every saved provider key can be read.` : quiconque possède ce zip lit aussi les clés enregistrées des fournisseurs de données.

4. **Serveur de destination — terminal, dossier de `docker-compose.yml`.** Décompressez le zip dans le dossier de données.

    ```bash
    # In the folder of docker-compose.yml, before the first start
    unzip librefolio-backup-20261015-121500.zip -d LibreFolio-data
    ```

    Résultat : `LibreFolio-data/` contient les données de l'archive. Le `manifest.json` laissé là est inoffensif : vous pouvez le supprimer.

5. **Serveur de destination — dossier `LibreFolio-data/secrets/`.** Avant le premier démarrage :

    - 🗝️ **Sauvegarde en clair** : remettez le `secrets/` du serveur source dans `LibreFolio-data/`, et les secrets enregistrés restent lisibles. Sans lui, LibreFolio crée une nouvelle clé d'instance la première fois qu'il en a besoin.
    - 🔐 **Sauvegarde sécurisée qui transporte la clé** : le zip contient déjà `secrets/instance.key`, et les clés enregistrées des fournisseurs de données restent lisibles. Rendez le dossier et le fichier privés, sinon le journal de démarrage contient un avertissement (« Vérifications au démarrage » dans [Variables d'environnement](configuration.md)) :

    ```bash
    chmod 700 LibreFolio-data/secrets
    chmod 600 LibreFolio-data/secrets/instance.key
    ```

    Résultat : la clé d'instance est en place, et rien dans le journal de démarrage ne la concerne.

    !!! warning "⛔ La clé d'une sauvegarde, seulement sur un dossier de données vide"

        N'utilisez la clé d'une sauvegarde que de cette manière : sur un dossier de données vide, sur une installation qui ne définit ni `LIBREFOLIO_INSTANCE_KEY` ni `LIBREFOLIO_INSTANCE_KEY_FILE`. Une clé définie dans cette installation prime sur `secrets/instance.key`, et les clés enregistrées des fournisseurs de données resteraient illisibles.
        Ne la mettez jamais à la place d'une clé déjà utilisée : ce qui a été enregistré sous cette clé deviendrait illisible. Pour transférer une sauvegarde sécurisée vers une installation qui possède sa propre clé, restaurez-la : la restauration rechiffre les clés enregistrées avec la clé de cette installation.

6. **Serveur de destination — terminal, dossier de `docker-compose.yml`.** Premier démarrage, avec la même image que la source ou une image plus récente.

    ```bash
    docker compose up -d
    ```

    Résultat : le démarrage applique lui-même les migrations en attente.

### ⛔ Jamais de retour en arrière {: #never-backwards }

LibreFolio ne ramène jamais une base de données à une version antérieure : utilisez la version qui a créé l'archive, ou une version plus récente. Un LibreFolio plus ancien refuse une archive dont la base de données contient une migration qu'il ne connaît pas.

- 🏷️ `backup inspect` indique quelle version a créé l'archive (`Made by LibreFolio <version>`) ; **Paramètres › À propos** indique la version d'une instance.
- ❌ `backup restore` refuse une telle archive avec `revision_unknown`, avant que quoi que ce soit ne change.
- 🛑 À la main, un LibreFolio plus ancien ne démarre pas sur de telles données : le journal contient `Failed to apply database migrations`, et Docker ne cesse de redémarrer le conteneur. Arrêtez-le avec `docker compose down`.

Mettez d'abord à jour le LibreFolio qui reçoit l'archive ([Mise à jour de LibreFolio](../user/installation.md#updating)), puis restaurez. Avec Docker, l'image `latest` est la version la plus récente.

---

## 🧯 En cas de problème {: #troubleshooting }

### 🔐 Créer une sauvegarde sécurisée {: #secure-problems }

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` | `backup create --encrypt` sans terminal pour poser la question, par exemple dans cron | Indiquez le mot de passe avec `--password-file` ou `--password-stdin` ([Depuis la ligne de commande](backup_restore.md#command-line)) |
| `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: …)`, ou dans Paramètres › Administration › Sauvegarde *Le mot de passe ne respecte pas les règles du mot de passe d'une sauvegarde.* | Les règles sont listées après `password_too_weak:`. Dans Paramètres, **Créer une sauvegarde** reste désactivé tant que toutes les règles ne sont pas respectées ; si les règles d'une sauvegarde ne sont pas venues du serveur (`GET /api/v1/backup/instance/options`), l'indicateur applique celles du mot de passe d'un compte (8 caractères), et le serveur refuse quand même moins de 12 | Choisissez un mot de passe plus long qui respecte toutes les règles. Rien n'a été écrit |
| `❌ The two passwords differ (password_mismatch)` | Le second mot de passe saisi au terminal n'est pas le premier | Relancez la commande |
| `❌ password file: <path> does not exist (password_unreadable)`, ou `cannot be read`, `is empty or blank`, `is not UTF-8 text` | `--password-file` ne peut pas fournir le mot de passe | Corrigez le fichier : le mot de passe seul, en UTF-8. Avec Docker, le chemin à l'intérieur du conteneur, par exemple `/run/secrets/backup_password` |
| `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, ou dans Paramètres › Administration › Sauvegarde *La clé de l'instance est inutilisable : la sauvegarde a été faite sans elle, il faudra donc saisir à nouveau les clés des fournisseurs de données après une restauration.* | `secrets/instance.key` est présent, mais endommagé ou inaccessible, ou plus long que les 4096 octets qu'une restauration peut relire (la clé générée par LibreFolio fait 43 caractères). La sauvegarde est complète, sans la clé | Si le journal de démarrage indique ce qui ne va pas avec la clé, corrigez-le (« Vérifications au démarrage » dans [Variables d'environnement](configuration.md)), puis créez une nouvelle sauvegarde sécurisée. S'il ne dit rien, la clé est trop longue pour être transportée : conservez une copie de `secrets/` avec la sauvegarde, comme pour une sauvegarde en clair |

### 🧾 La vérification refuse l'archive {: #check-refused }

`backup restore`, avec ou sans `--dry-run`, se termine par un refus avec son code entre parenthèses, sans rien changer. Paramètres › Administration › Sauvegarde refuse les mêmes archives et en indique la raison sur la carte, sans le code : *L'archive est endommagée.* pour `archive_damaged`, par exemple.

| Code | Pourquoi | Que faire |
| --- | --- | --- |
| `revision_unknown` | L'archive provient d'un LibreFolio plus récent | Mettez à jour cette installation ([Jamais de retour en arrière](#never-backwards)), puis relancez la commande |
| `manifest_newer_format` | Le format de l'archive est plus récent que celui que ce LibreFolio sait lire | Mettez d'abord LibreFolio à jour |
| `checksum_mismatch`, `archive_damaged`, `missing_entry` | L'archive est endommagée, tronquée ou a été modifiée | `backup inspect` nomme les entrées qui diffèrent. Copiez à nouveau l'archive depuis l'endroit où vous la conservez, ou utilisez-en une autre |
| `database_damaged` | La base de données échoue au contrôle d'intégrité de SQLite, SQLite ne peut pas lire son schéma, ou elle contient du texte qui n'est pas en UTF-8. Paramètres › Administration › Sauvegarde : *La base de données de la sauvegarde est endommagée : elle ne peut pas être restaurée.* | Copiez à nouveau l'archive depuis l'endroit où vous la conservez, ou utilisez-en une autre. Un texte qui n'est pas en UTF-8 signifie qu'un autre programme a écrit dans la base de données (LibreFolio n'y écrit jamais un tel texte), ou que l'archive a été modifiée |
| `database_foreign_objects` | La base de données contient un déclencheur, une vue ou une table virtuelle, que LibreFolio ne crée jamais. Paramètres › Administration › Sauvegarde : *La base de données de la sauvegarde contient des déclencheurs, des vues ou d'autres objets que LibreFolio ne crée jamais : elle ne vient pas de LibreFolio, ou elle a été modifiée, et elle ne peut pas être restaurée.* | L'archive n'a pas été créée par LibreFolio, ou a été modifiée ensuite : utilisez une autre sauvegarde |
| `not_a_backup` | Ce n'est pas une archive écrite par LibreFolio, par exemple un dossier de données zippé à la main | Remettez une telle copie [à la main](#by-hand), dans un dossier de données vide |
| `sealed_backup_needs_key` | Une sauvegarde nocturne scellée (`.tar`) : son mot de passe est à l'intérieur, chiffré pour une clé que la vérification n'a pas. Paramètres › Administration › Sauvegarde : *Ceci est une sauvegarde scellée d'un panneau d'hébergement : son mot de passe est chiffré pour la clé du fournisseur. Extrayez backup.lfbk, ouvrez password.age avec age, puis restaurez backup.lfbk avec ce mot de passe.* | Restaurez-la là où se trouve sa clé privée : `backup restore <archive>.tar --identity-file <key file>` ([Sauvegardes scellées](backup_sealed.md#sealed)) |
| `sealed_no_identity`, `sealed_identity_invalid`, `sealed_tar_invalid`, `sealed_manifest_invalid`, `sealed_password_invalid` | Une [sauvegarde scellée](backup_sealed.md#sealed) fournie avec `--identity-file` qui ne s'ouvre pas | Voir [Créer ou ouvrir une sauvegarde scellée](#sealed-problems) |
| `no_space` | La copie a besoin de plus d'espace libre que le disque du dossier de données n'en a | Libérez de l'espace : l'archive décompressée, plus deux fois sa base de données, plus 64 Mo, et pour une sauvegarde sécurisée, aussi la taille de son `.lfbk` |
| `archive_unreadable` | L'archive ne peut pas être ouverte, le plus souvent parce que l'utilisateur du serveur n'a pas le droit de la lire | Avec Docker et l'image officielle, `sudo chown 1000:1000 <archive>` sur l'hôte la donne à cet utilisateur |
| `restore_already_pending` | Une autre restauration attend le prochain démarrage | Redémarrez LibreFolio pour l'appliquer, ou annulez-la avec `backup pending --cancel` ou **Annuler la restauration** dans Paramètres › Administration › Sauvegarde |
| `wrong_password` | Le mot de passe n'ouvre pas la sauvegarde sécurisée : ce n'est pas celui avec lequel elle a été créée, ou le début du fichier a été modifié. Paramètres › Administration › Sauvegarde le redemande : *Mot de passe erroné, ou le fichier a été modifié : saisissez à nouveau le mot de passe.* | Saisissez-le à nouveau tel qu'il a été choisi, majuscules et minuscules comprises. S'il est correct, copiez à nouveau le fichier depuis l'endroit où vous le conservez |
| `password_required` | Une sauvegarde sécurisée, et aucun mot de passe : la commande n'avait pas de terminal pour poser la question, et ni `--password-file` ni `--password-stdin` | Exécutez la commande dans un terminal, ou indiquez le mot de passe avec l'une des deux options |
| `envelope_damaged` | La sauvegarde sécurisée est endommagée, tronquée ou a été modifiée après sa création | Copiez-la à nouveau depuis l'endroit où vous la conservez, ou utilisez-en une autre : LibreFolio ne lit aucune partie d'un `.lfbk` endommagé |
| `envelope_unsupported` | La sauvegarde sécurisée provient d'un LibreFolio plus récent, ou demande des paramètres que celui-ci n'accepte pas | Mettez d'abord cette installation à jour ([Jamais de retour en arrière](#never-backwards)), puis relancez la commande |

Deux autres messages :

- `❌ No file at <path>` : avec Docker, indiquez le chemin à l'intérieur du conteneur, `/app/backend/data/prod-docker/…`.
- `❌ The backup has no active administrator: after a restore nobody could manage the instance`, ou la même chose dans le rapport de Paramètres › Administration › Sauvegarde, dont la confirmation reste désactivée : sur l'installation d'où vient la sauvegarde, faites d'un compte actif un administrateur, puis créez une nouvelle sauvegarde.

Tous les codes : « Refus — signification des codes » dans [Outils d'administration CLI](cli_tools.md).

Deux avertissements laissent la restauration se poursuivre, mais lisez-les avant de confirmer :

- 🔑 *Votre compte ne fait pas partie des administrateurs de cette sauvegarde : après le redémarrage, vous ne pourrez plus vous connecter avec ce compte.* Uniquement dans le rapport de Paramètres › Administration › Sauvegarde, en rouge. Après la restauration, vous vous connectez avec un compte de la sauvegarde, avec le mot de passe qu'il avait alors : le compte que vous utilisez actuellement n'y figure pas. Avant de confirmer, assurez-vous de connaître le mot de passe de l'un des administrateurs que nomme le rapport ; si vous ne le connaissez pas, utilisez une autre sauvegarde.
- `⚠️ Ledger totals differ from the backup's (<n> lines):`, ou *Les totaux du registre diffèrent de ceux de la sauvegarde sur 2 lignes :* dans le rapport de Paramètres › Administration › Sauvegarde : la trésorerie d'un courtier ou la quantité d'une position dans la copie, une fois à jour, n'est pas celle que la sauvegarde avait enregistrée, parce que des transactions ont été perdues, ajoutées ou modifiées entre les deux (par une migration qui corrige des données, par exemple). Chaque ligne qui suit donne un numéro de courtier, puis un numéro de devise ou d'actif, avec le montant de la sauvegarde avant la flèche et celui de la copie après : les numéros sont ceux des adresses `/brokers/<id>` et `/assets/<id>` de l'application. Comparez ces lignes avec l'instance d'où vient la sauvegarde. L'avertissement ne bloque jamais la restauration : c'est à vous de décider si vous confirmez.

### 🔏 Créer ou ouvrir une sauvegarde scellée {: #sealed-problems }

Pour en créer une, avec `backup create --sealed` ou `--recipient` : rien n'est écrit, et la commande se termine avec le code `1`.

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS is not set: give the recipients there, or with --recipient age1…` | `--sealed` n'a pas trouvé la variable : absente de `.env`, ou le conteneur n'a pas été recréé après son ajout | Définissez-la ([Sceller chaque sauvegarde](backup_sealed.md#sealed-recipients)), puis `docker compose up -d`, ou exécutez la commande depuis le dossier du projet avec `pipenv run`, qui lit `.env` |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: expected age1… as age-keygen prints it (BACKUP_RECIPIENTS_INVALID)`, ou `expected at most 2 recipients, comma-separated (BACKUP_RECIPIENTS_TOO_MANY)`, ou `item 2 repeats an earlier recipient (BACKUP_RECIPIENTS_DUPLICATE)` | La variable contient autre chose qu'une ou deux clés `age1…` distinctes : une clé privée, une clé SSH, une virgule en trop | N'écrivez que les clés publiques, telles que les affichent `keygen` ou `age-keygen -y`. L'onglet **Sécurité** indique la même chose (`backup.recipients`) |
| `❌ A --recipient is not an age recipient: expected age1…, as keygen or age-keygen prints it`, `❌ The same recipient is given twice`, `❌ At most 2 recipients: --recipient twice, while a key is being changed` | Les mêmes règles, pour `--recipient` | Indiquez une ou deux clés publiques différentes |
| `❌ A sealed backup draws a password of its own: --sealed and --recipient go without --encrypt, --password-file or --password-stdin` | Une sauvegarde scellée n'a pas de mot de passe à fournir | Retirez les options de mot de passe |
| `❌ --sealed reads the recipients from LIBREFOLIO_BACKUP_RECIPIENTS: give them there or with --recipient, not both` | `--sealed` et `--recipient` ensemble | Gardez l'un des deux |
| `❌ <path> already exists: a key file is never written over` | `backup keygen` ne remplace jamais une clé : l'ancienne peut encore ouvrir des sauvegardes | Choisissez un autre nom de fichier, ou déplacez d'abord l'ancien fichier si vous êtes sûr qu'aucune sauvegarde n'en a besoin |

Pour en ouvrir une, avec `--identity-file` : la commande ne change rien et se termine avec le code `1`. Elle lit d'abord le fichier de clé, puis le `.tar`.

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| `(sealed_backup_needs_key)` | Un `.tar` fourni sans `--identity-file`, sur la ligne de commande ou dans Paramètres › Administration › Sauvegarde | Indiquez le fichier de clé, ou [ouvrez-la à la main](backup_sealed.md#sealed-by-hand) et restaurez `backup.lfbk` avec son mot de passe |
| `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one` | Un `.zip` ou un `.lfbk` fourni avec `--identity-file` | Retirez `--identity-file` : ces archives s'ouvrent comme d'habitude |
| `❌ The key file cannot be read (sealed_identity_invalid)`, `Line 3 of the key file is not an age key`, `The key file holds no age key` | Le fichier n'est pas une clé privée : la clé publique seule, une clé copiée avec un caractère manquant, ou un fichier que la commande ne peut pas lire | Indiquez le fichier écrit par `keygen` ou `age-keygen`, avec sa ligne `AGE-SECRET-KEY-1…`. Les commentaires (`#`) et les lignes vides peuvent rester |
| `❌ None of the keys given opens the password of this backup (sealed_no_identity)` | La sauvegarde a été scellée pour une autre clé : une clé plus ancienne, avant un [changement de clé](backup_sealed.md#sealed-rotation) | Comparez ses `recipients` (`tar xOf <archive>.tar manifest.json`) avec la ligne `# public key:` de vos fichiers de clé, et indiquez celui qui correspond |
| `(sealed_tar_invalid)`, comme `The archive is cut short` ou `The archive does not hold manifest.json, password.age and backup.lfbk, in this order` | Ce n'est pas le `.tar` écrit par LibreFolio : tronqué par une copie, reconstruit à la main avec `tar cf`, ou ce n'est pas une sauvegarde scellée | Copiez à nouveau l'original depuis l'endroit où vous le conservez, ou utilisez la sauvegarde d'une autre nuit |
| `(sealed_manifest_invalid)`, comme `The manifest does not describe backup.lfbk: its size or SHA-256 differs` | `manifest.json` ou `backup.lfbk` a été modifié | La copie est endommagée : utilisez-en une autre |
| `(sealed_password_invalid)` | La clé a ouvert `password.age`, mais ce qu'il contient n'est pas un mot de passe écrit par LibreFolio | Ce n'est pas une sauvegarde LibreFolio, ou elle a été modifiée : utilisez une autre copie |
| `❌ The password does not open this backup (wrong_password)` | La clé a ouvert le mot de passe, mais ce mot de passe n'ouvre pas `backup.lfbk` : les deux fichiers viennent de sauvegardes différentes, ou l'un a été modifié | Utilisez une autre copie, conservée entière telle que LibreFolio l'a écrite |
| `(envelope_damaged)`, pendant la vérification ou la restauration | Un octet de `backup.lfbk` a été modifié après la création de la sauvegarde : le mot de passe était correct | Utilisez une autre copie : LibreFolio ne lit aucune partie d'un `.lfbk` endommagé |

### 🔁 La restauration n'aboutit pas {: #restart-problems }

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| `backup pending` indique `The state of the restore cannot be read`, `(restore_state_unreadable: <reason>)` | `.restore/restore.json` ne peut pas être utilisé : ses permissions (`io`), un lien ou un dossier à sa place (`not_a_file`), ou un contenu que LibreFolio n'a pas écrit (`invalid`). Une restauration a peut-être été interrompue à mi-chemin. Aucune copie vérifiée n'est supprimée pendant ce temps | Pour `io`, redonnez `.restore/` à l'utilisateur qui exécute LibreFolio et vérifiez à nouveau. Sinon, arrêtez LibreFolio et exécutez `backup pending --recover previous` : les données d'avant reviennent depuis `.restore/previous/`. Démarrez-le ensuite, ou restaurez à nouveau une sauvegarde (« Un état de restauration illisible » dans [Outils d'administration CLI](cli_tools.md)) |
| `backup pending` se termine par `(server_running)` | Au dernier démarrage, un autre processus serveur servait le dossier de données : un worker a redémarré tout seul, ou un second serveur | Redémarrez tout le serveur, jamais un seul worker, et exécutez un seul serveur par dossier de données |
| `backup pending` se termine par `(other_data_directory)` | Le serveur a trouvé son dossier de données sous un autre chemin que celui pour lequel la restauration a été confirmée, par exemple une copie du dossier de données | `backup pending --cancel`, ou **Annuler la restauration** dans Paramètres › Administration › Sauvegarde, puis restaurez à nouveau l'archive : avec `backup restore`, là où le serveur s'exécute |
| `backup pending` se termine par `(backup_running)` | Une sauvegarde était en cours au dernier démarrage | Rien : le prochain démarrage applique la restauration |
| `backup pending` indique que la restauration a été annulée, `(first_start_failed)` | Le premier démarrage sur les données restaurées ne s'est pas terminé | Les données sont telles qu'elles étaient. Le journal de ce démarrage contient la cause : corrigez-la, puis restaurez à nouveau l'archive |
| … annulée, `(swap_interrupted)` | Le démarrage qui a appliqué la restauration a été interrompu, et le suivant l'a annulée | Restaurez à nouveau l'archive |
| … annulée, `(swap_failed)` | Les dossiers n'ont pas pu être mis en place | Faites en sorte que `sqlite/`, `custom-uploads/`, `broker_reports/` et `scenario_catalog/` soient de vrais dossiers du dossier de données, et non des liens ou des montages séparés, puis restaurez à nouveau l'archive |
| … annulée, `(stage_missing)` | La copie vérifiée avait disparu ou changé | Restaurez à nouveau l'archive |
| Un démarrage s'arrête, et son journal indique qu'un autre serveur a appliqué la restauration ou sert le dossier de données | Deux serveurs LibreFolio utilisent le même dossier de données | Arrêtez l'autre, puis redémarrez LibreFolio : `backup pending` indiquera si la restauration a été conservée |
| LibreFolio ne démarre pas, et son journal contient `The data directory is half restored` | La remise en place des données précédentes a échoué elle aussi, à cause par exemple d'une erreur de disque ou de permissions | Corrigez la cause indiquée par le journal : chaque démarrage réessaie |
| `Failed to apply database migrations` après une décompression à la main | Une archive d'un LibreFolio plus récent, ou une migration qui échoue : le journal contient l'erreur | Pour une archive plus récente, `docker compose down`, puis utilisez la version qui l'a créée ou une version plus récente ([Jamais de retour en arrière](#never-backwards)) |

### 🖱️ Ce que dit Paramètres › Administration › Sauvegarde {: #restore-settings-problems }

La fenêtre du redémarrage donne en mots la raison que `backup pending` donne sous forme de code : le tableau indique laquelle, et la ligne de ce code dans [La restauration n'aboutit pas](#restart-problems) indique quoi faire. Sur la carte, **Réessayer** relit l'état de la restauration ; pour envoyer à nouveau une archive, choisissez-la à nouveau.

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| Après **Restaurer et redémarrer**, la page de connexion, sans message | La restauration a fonctionné et a mis fin à toutes les sessions. Ce n'est que dans le cas de la ligne suivante que la page de connexion apparaît alors que la restauration n'a pas abouti | Connectez-vous avec un administrateur de la sauvegarde, avec le mot de passe que le compte avait au moment de la sauvegarde. Si personne ne s'en souvient : [Après une restauration](#after-restore) |
| La page de connexion est apparue, mais une fois connecté, les données sont comme avant | La page n'a pas lu le résultat avec son ticket (rechargement de la page, plus d'une heure d'attente, ou LibreFolio redémarré depuis la ligne de commande plutôt que depuis la page), et LibreFolio s'exécute sans `JWT_SECRET` ([Maintenir les utilisateurs connectés après un redémarrage](index.md#session-persistence)) : chaque démarrage déconnecte tout le monde, même si la restauration n'a pas abouti. Les comptes et mots de passe d'avant permettent toujours de se connecter | Ouvrez **Paramètres › Administration › Sauvegarde** : la carte indique *La dernière restauration a été annulée le …*, ou montre la restauration en attente, avec la raison ; consultez ensuite la ligne de cette raison ci-dessous |
| *LibreFolio n'est pas encore revenu. Si rien ne le redémarre tout seul, démarrez-le vous-même : la restauration est appliquée à ce démarrage.* | LibreFolio n'a pas répondu pendant une minute : rien ne l'a redémarré (pas de superviseur, ou un superviseur qui ne le démarre qu'après un échec, [Qui redémarre LibreFolio](backup_restore.md#supervisors)), ou son démarrage est lent | S'il est arrêté, démarrez-le : `docker compose up -d` avec Docker, ou [démarrez le serveur](cli_tools.md#start-the-server) sur une installation sur l'hôte. La page se met à jour automatiquement une fois que LibreFolio répond |
| *LibreFolio ne s'est pas arrêté. S'il ne redémarre pas tout seul, redémarrez-le vous-même : la restauration est appliquée à ce démarrage.*, une minute après **Restaurer et redémarrer**, avec **Retour à la sauvegarde** | La demande n'a pas arrêté le serveur : la restauration attend toujours le prochain démarrage, et `backup pending` la montre en attente | Redémarrez LibreFolio vous-même : `docker compose restart librefolio` avec Docker, ou arrêtez tout le serveur et [démarrez-le](cli_tools.md#start-the-server) à nouveau. Son démarrage applique la restauration, et la page se met à jour automatiquement. Ou **Retour à la sauvegarde** : la carte montre la restauration en attente, à redémarrer (**Redémarrer et restaurer**) ou à annuler (**Annuler la restauration**) |
| **La restauration n'a pas abouti**, avec *Les données sont comme avant : …* | La restauration a été annulée : *le premier démarrage qui a suivi n'a pas abouti* (`first_start_failed`), *le démarrage qui l'appliquait a été interrompu* (`swap_interrupted`), *ses dossiers n'ont pas pu être mis en place* (`swap_failed`) ou *sa copie vérifiée n'était plus là* (`stage_missing`) | Ce que dit la ligne de ce code. **Retour à la sauvegarde** revient à la carte, qui indique quand la dernière restauration a été annulée, et pourquoi |
| **La restauration n'a pas abouti**, avec *LibreFolio a redémarré, mais la restauration n'a pas été appliquée.* et la raison | Un démarrage a laissé la restauration en attente : *Au dernier démarrage, une sauvegarde était en cours…* (`backup_running`), *Elle a été confirmée pour un autre dossier de données…* (`other_data_directory`) ou *Au dernier démarrage, un autre processus de LibreFolio servait les données…* (`server_running`) | Ce que dit la ligne de ce code. **Retour à la sauvegarde** montre la restauration en attente, avec **Redémarrer et restaurer** et **Annuler la restauration** |
| *L'archive est plus grande que ce que ce LibreFolio accepte (500 Mo).* | L'installation limite les archives téléversées pour une restauration avec `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (`backup_too_large`) | Il n'y a pas de limite sauf si quelqu'un en a défini une : augmentez-la, ou mettez-la à `0`, puis redémarrez ([La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit)). Ou restaurez depuis la ligne de commande, qui n'a pas de limite de téléversement |
| *Décompressée, l'archive est plus grande que ce que ce LibreFolio accepte pour une restauration.* | Les tailles que déclare le manifeste, additionnées, dépassent `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (`unpacked_too_large`). La vérification a refusé l'archive avant de décompresser quoi que ce soit | Il n'y a pas de limite sauf si quelqu'un en a défini une : augmentez-la, mettez-la à `0` ou supprimez-la, puis redémarrez ([La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit)). Ou restaurez depuis la ligne de commande avec `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` devant `backup restore` |
| *LibreFolio ne peut pas lire sa limite de restauration pour l'instant : réessayez plus tard.* | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` n'est pas un nombre entier de mégaoctets (`backup_restore_unavailable`) : aucune vérification ne démarre, et l'archive reste sur le serveur. Le journal contient une erreur, dès le démarrage | Écrivez un nombre entier de mégaoctets, `0` pour aucune limite, ou supprimez la variable, puis redémarrez ; l'onglet **Sécurité** de Paramètres › Administration la nomme (`backup.restore_limit`). Choisissez ensuite à nouveau l'archive |
| L'envoi s'arrête avec *Un proxy placé devant LibreFolio a refusé une archive aussi grande : demandez à la personne qui le gère d'accepter des téléversements plus volumineux, ou restaurez depuis la ligne de commande.*, ou avec *Le serveur ne répond pas : vérifiez la connexion et réessayez.* ou *Le serveur a répondu par une erreur : le journal du serveur donne la cause.*, et le journal de LibreFolio n'en dit rien | Un proxy placé devant LibreFolio a refusé l'archive : Nginx n'accepte que 1 Mo par défaut. Le premier message : le proxy répond *trop volumineux* (HTTP 413) ; les autres : il coupe la connexion ou répond autrement | Laissez le proxy accepter des archives aussi grandes que les vôtres, avec `client_max_body_size` dans Nginx ([La limite de téléversement d'une restauration](backup_restore.md#restore-upload-limit)), ou restaurez depuis la ligne de commande |
| *Pas assez d'espace libre sur le serveur pour cette archive.* | Le disque du dossier de données, ou un quota, est plein (`backup_no_space`) : pendant l'envoi, et alors rien de l'archive n'est conservé (un système de fichiers réseau ou un quota peut ne le signaler qu'à la fin du fichier), ou à la confirmation avec **Restaurer et redémarrer**, et alors rien n'est confirmé et la copie vérifiée reste ; le journal contient `A restore could not be confirmed: not enough free space` | Libérez de l'espace sur le disque du dossier de données, puis choisissez à nouveau l'archive. Après une confirmation, **Réessayer** : le rapport revient, et **Restaurer et redémarrer** confirme à nouveau |
| *Pas assez d'espace libre sur le serveur pour vérifier l'archive.* | Le disque du dossier de données, ou un quota, est plein au démarrage de la vérification, et alors l'archive reste sur le serveur, ou pendant que la vérification crée sa copie (`no_space`) | Libérez de l'espace, autant que l'indique la ligne `no_space` de [La vérification refuse l'archive](#check-refused), puis choisissez à nouveau l'archive |
| *La copie n'a pas pu être écrite : le journal du serveur donne la cause.* | La vérification n'a pas démarré, ou n'a pas écrit sa copie, pour une autre raison que l'espace (`stage_failed`) : le propriétaire ou les permissions d'un dossier de `.restore/`, un disque en lecture seule, une erreur de disque. Le journal contient `A check of a backup archive could not start`, avec l'erreur et la raison du système | Corrigez ce que nomme la ligne du journal, par exemple en redonnant `.restore/` à l'utilisateur qui exécute LibreFolio, puis choisissez à nouveau l'archive |
| *Espace libre insuffisant sur le serveur pour la sauvegarde.*, sur la carte **Sauvegarder l'instance** | Le disque du dossier de données, ou un quota, est plein (`backup_no_space`), au démarrage de la sauvegarde ou pendant son exécution : la sauvegarde est construite dans `backups/`, sur ce disque | Libérez de l'espace sur ce disque, puis **Réessayer**. L'espace nécessaire à une sauvegarde : « Créer une archive » dans [Outils d'administration CLI](cli_tools.md) |
| *La restauration n'a pas pu être confirmée : le journal du serveur donne la cause. Rien n'a changé.*, après **Restaurer et redémarrer** | La confirmation n'a pas été écrite, pour une autre raison que l'espace (`restore_confirm_failed`) : le propriétaire ou les permissions de `.restore/`, un disque en lecture seule, une erreur de disque. Le journal contient `A restore could not be confirmed`, avec l'erreur et la raison du système. Rien n'est confirmé, et la copie vérifiée reste | Corrigez ce que nomme la ligne du journal, par exemple en redonnant `.restore/` à l'utilisateur qui exécute LibreFolio, puis **Réessayer** : le rapport revient, et **Restaurer et redémarrer** confirme à nouveau |
| *La restauration n'a pas pu être annulée : le journal du serveur donne la cause. Elle attend toujours le prochain démarrage.*, après **Annuler la restauration** : la carte montre toujours la restauration en attente, avec **Redémarrer et restaurer** et **Annuler la restauration** | Son état dans `.restore/` n'a pas pu être verrouillé ou supprimé (`restore_cancel_failed`) : le propriétaire ou les permissions, un disque en lecture seule, une erreur de disque. Le journal contient `A pending restore could not be cancelled`, avec l'erreur et la raison du système. Qu'une copie ne puisse pas être supprimée après l'annulation ne constitue pas un tel échec : la restauration est annulée, et le journal contient l'avertissement `The copy of a cancelled restore could not be removed: it goes when its check expires` | Corrigez ce que nomme la ligne du journal, puis **Annuler la restauration** à nouveau, sur la même carte : tant qu'elle n'est pas annulée, le prochain démarrage de LibreFolio applique la restauration. Une copie laissée sur place est supprimée au premier démarrage de LibreFolio une fois que sa vérification a 24 heures |
| *LibreFolio n'a pas pu être redémarré : le journal du serveur donne la cause. La restauration attend toujours le prochain démarrage.*, après **Restaurer et redémarrer** ou **Redémarrer et restaurer** | LibreFolio n'a pas été arrêté : le ticket avec lequel la page lit le résultat n'a pas été écrit (`restore_restart_failed`), à cause d'un disque plein ou du propriétaire ou des permissions de `.restore/`. Le journal contient `The ticket of the restore's outcome could not be written: no restart`. La restauration est confirmée, et attend | Corrigez ce que nomme la ligne du journal, puis **Redémarrer et restaurer**, que la carte montre avec la restauration en attente. Ou redémarrez LibreFolio vous-même, `docker compose restart librefolio` avec Docker : son démarrage applique la restauration |
| *L'état de la restauration ne peut pas être lu : le journal du serveur donne la cause. Une restauration attend peut-être encore le prochain démarrage.* | L'état de la restauration dans `.restore/` ne peut pas être lu (`restore_state_unreadable`) : le propriétaire ou les permissions, par exemple des fichiers écrits par `root`, ou une erreur de disque. On ne sait pas si une restauration attend : confirmer une autre restauration est refusé, et un démarrage qui ne lit pas l'état le laisse tel quel et n'applique rien | Redonnez `.restore/` et ses fichiers à l'utilisateur qui exécute LibreFolio, en les rendant lisibles par lui, puis **Réessayer**. Avec Docker, chaque démarrage du conteneur redonne le dossier de données à cet utilisateur avant que LibreFolio ne lise l'état, si bien qu'une restauration en attente est appliquée à ce démarrage ; les permissions modifiées avec `chmod` restent telles quelles. `backup pending` dit la même chose, avec la raison du système |
| La carte refuse l'archive, par exemple *Ce fichier n'est pas une sauvegarde de LibreFolio.*, *L'archive est endommagée.* ou *La sauvegarde sécurisée est endommagée ou a été modifiée : elle ne peut pas être ouverte.* | La vérification l'a refusée, comme le fait `backup restore` | Voir son code dans [La vérification refuse l'archive](#check-refused) |
| La carte redemande le mot de passe d'une sauvegarde sécurisée : *Mot de passe erroné, ou le fichier a été modifié : saisissez à nouveau le mot de passe.* | Le mot de passe n'ouvre pas la sauvegarde (`wrong_password`) | Saisissez-le à nouveau : l'archive reste sur le serveur et n'est pas renvoyée. Si le mot de passe est correct, le fichier a été modifié : **Annuler**, puis choisissez une bonne copie avec **Choisir une archive…** |

### 🔑 Après une restauration {: #after-restore }

| Ce qui se passe | Que faire |
| --- | --- |
| Personne ne se souvient du mot de passe qu'un administrateur avait dans la sauvegarde | Qui exploite le serveur en définit un nouveau avec `user reset`, ou crée un lien de réinitialisation avec `user reset-link` ([Réinitialiser un mot de passe ou verrouiller un compte](cli_tools.md#reset-a-password-or-lock-an-account)) |
| La page de connexion répond qu'un compte est désactivé : il attendait sa vérification par e-mail | Un administrateur clique sur **Réactiver** sur sa ligne ([Ce que fait chaque action](users.md#actions)), ou le supprime pour que son propriétaire s'inscrive à nouveau ([Supprimer un compte](users.md#delete)) |
| Un lien envoyé avant la restauration ne fonctionne plus | Envoyez une nouvelle invitation ou un nouveau lien de réinitialisation du mot de passe ([Utilisateurs et invitations](users.md)) |
| Un paramètre de plugin secret est signalé comme défini mais illisible, comme l'avait annoncé le rapport de la vérification (*… ne peuvent pas être lues avec la clé de cette instance : saisissez-les à nouveau après la restauration.*) | La sauvegarde ne contenait aucune clé permettant de le lire : une sauvegarde en clair, ou une sauvegarde sécurisée dont l'instance avait une clé définie dans son environnement, ou ne pouvait pas utiliser la sienne. Si vous avez encore l'ancienne clé, remettez-la avant que quiconque ne saisisse à nouveau un secret ; ce n'est que dans le cas contraire que vous devez saisir à nouveau le paramètre dans **Paramètres › Plugins**, où chaque utilisateur saisit le sien ([Ce qui suit](backup_restore.md#what-follows)). Si le journal de démarrage indique que la clé de cette installation ne peut pas être utilisée, corrigez cela d'abord (« Vérifications au démarrage » dans [Variables d'environnement](configuration.md)) |
| Après un déplacement, aucun e-mail n'est envoyé | Définissez les variables d'e-mail sur cette installation, puis redémarrez ([E-mail](email.md)) |

---

## 🔗 Voir aussi

- 📄 **[Sauvegarde, restauration et déplacement de votre instance](backup_restore.md)** — Ce que contient une sauvegarde, créer une sauvegarde, sauvegardes sécurisées, …
- 📄 **[Sauvegardes : sauvegardes scellées](backup_sealed.md)** — Sauvegardes scellées : une clé plutôt qu'un mot de passe
