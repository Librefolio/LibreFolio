# 💾 Sauvegarde, restauration et déplacement de votre instance

Une sauvegarde est une archive qui contient tout votre LibreFolio : la base de données et les fichiers de chaque utilisateur. C'est un zip ordinaire ou, pour une [sauvegarde sécurisée](#secure), un `.lfbk` chiffré avec un mot de passe que vous choisissez.

Vous trouverez ici :

- [ce que contient l'archive](#contents) et [ce qui suit](#what-follows) ;
- comment en [créer une](#create), depuis l'application ou depuis la ligne de commande, et comment [garder des copies hors du serveur](#keep-copies) ;
- comment la [vérifier](#check) et comment la [restaurer](#restore), depuis l'application ou depuis la ligne de commande.

Chaque option et chaque message des commandes : «Sauvegarder l'instance», dans [Outils d'administration CLI](cli_tools.md).

!!! tip "🗓️ Faites-en une avant chaque mise à jour"

    LibreFolio ne ramène jamais une base de données à une version antérieure. Une sauvegarde réalisée avant une mise à jour est votre moyen de revenir à la version que vous aviez : voir [Mettre à jour LibreFolio](../user/installation.md#updating).

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Outre cette page : [Sauvegardes : sauvegardes scellées](backup_sealed.md), [Sauvegardes : déplacement et dépannage](backup_moving.md).

---

## 📦 Ce que contient une sauvegarde {: #contents }

L'archive est un zip qui reprend l'arborescence du [répertoire de données](filesystem.md) : décompressée dans un répertoire de données vide, elle reconstitue votre instance. Une [sauvegarde sécurisée](#secure) est le même zip, chiffré avec un mot de passe, dans un fichier `.lfbk`. Une [sauvegarde scellée](backup_sealed.md#sealed) est une sauvegarde sécurisée dont le mot de passe ne s'ouvre qu'avec une clé privée qui vous appartient, dans un fichier `.tar`.

| Dans l'archive | Ce que c'est |
| --- | --- |
| `sqlite/app.db` | La base de données : utilisateurs, courtiers, transactions, actifs, prix, taux de change et paramètres. Une copie cohérente, réalisée pendant que LibreFolio continue de fonctionner |
| `custom-uploads/` | Les fichiers téléversés dans l'application |
| `broker_reports/` | Les rapports de courtiers |
| `scenario_catalog/` | Vos scénarios de stress, si vous en avez ajouté |
| `secrets/instance.key` | Uniquement dans une [sauvegarde sécurisée](#secure), et uniquement si LibreFolio a généré la clé d'instance : la clé qui chiffre les clés enregistrées des fournisseurs de données. Une restauration ne fait que la lire : l'installation qui reçoit la sauvegarde conserve la sienne |
| `manifest.json` | La description de l'archive : version de LibreFolio et date de création, révision de migration de la base de données, nombre de lignes par table, totaux de contrôle du grand livre (la trésorerie de chaque courtier par devise et la quantité de chaque position), taille et somme de contrôle SHA-256 de chaque fichier, et si l'archive contient la clé d'instance |

Jamais dans l'archive :

- 🔑 `secrets/` : une [sauvegarde sécurisée](#secure) ne transporte que la clé générée par LibreFolio, `secrets/instance.key`, jamais une clé que vous avez définie vous-même avec `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE` («La clé d'instance» dans [Variables d'environnement](configuration.md)) ;
- 📝 `logs/` et `scheduler_state.json` (la dernière exécution des synchronisations planifiées) ;
- 💾 `backups/`, où LibreFolio [conserve les sauvegardes qu'il crée](#kept-backups), et `.restore/`, le dossier de travail d'une restauration ;
- ⚙️ la configuration : `.env` et les variables d'environnement, y compris les paramètres [e-mail](email.md), qui vivent uniquement dans l'environnement.

### 🧭 Ce qui suit {: #what-follows }

- 🔒 **Gardez-la privée.** Une archive en clair contient les données de chaque utilisateur, non chiffrées : gardez-la, ainsi que chaque copie, aussi privée que le serveur lui-même. Une archive [sécurisée](#secure) ne s'ouvre qu'avec son mot de passe : conservez le mot de passe séparément de l'archive.
- ⚙️ **Emportez votre configuration.** Conservez une copie de votre `.env` avec les archives : sur une autre installation, redéfinissez les options dont vous avez besoin, y compris celles de l'e-mail ([Où réside la configuration](email.md#where-it-lives)).
- 🏠 **Toute installation peut l'accepter**, depuis les Paramètres ou depuis la ligne de commande, si elle exécute la même version de LibreFolio ou une version plus récente, quelle que soit la personne qui a créé l'archive.
- 🗝️ **Secrets enregistrés et clé d'instance.** Ce que LibreFolio a chiffré avec la clé d'instance, comme la clé API d'une source de données enregistrée dans l'application, ne peut être lu qu'avec cette clé :

| Sauvegarde | La clé d'instance | Restaurée sur une installation dotée d'une autre clé |
| --- | --- | --- |
| [Sécurisée](#secure), clé générée par LibreFolio | Voyage avec les données | Les secrets sont rechiffrés avec la clé de l'installation qui la reçoit : rien à faire |
| En clair ; [scellée](backup_sealed.md#sealed) ; sécurisée avec une clé provenant de l'environnement (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) ou inutilisable | Reste dehors | Les secrets restent enregistrés mais illisibles ; LibreFolio n'utilise jamais une valeur erronée. **Paramètres › Plugins** l'indique sous chacun : *Enregistré, mais la clé de cette instance ne peut pas le lire : saisissez-le à nouveau.* |

Si vous avez encore l'ancienne clé, remettez-la en place **avant** que quiconque ne saisisse à nouveau un secret : un secret saisi sous la nouvelle clé deviendrait illisible dès que l'ancienne clé serait rétablie. Ne saisissez à nouveau les secrets que si l'ancienne clé est perdue.

1. Arrêtez LibreFolio.
2. **Sur le serveur, dans `secrets/` du répertoire de données** : mettez votre copie de `secrets/instance.key` à la place de celle qui a été générée. Ou, **dans `.env`**, définissez à nouveau l'ancienne valeur de la variable («La clé d'instance» dans [Variables d'environnement](configuration.md)).
3. Redémarrez LibreFolio.

Si l'installation conserve sa propre clé, ou si ses secrets sont déjà chiffrés avec sa clé, elle reprend l'ancienne clé lors de la restauration : **depuis la ligne de commande**, restaurez avec `--instance-key-file` et votre copie de l'ancienne clé ; la vérification rechiffre ces secrets avec la clé de cette installation («La clé d'instance d'une autre installation» dans [Outils d'administration CLI](cli_tools.md)).

Pour les paramètres de toute l'instance, chaque démarrage journalise l'erreur *Des secrets de plugin enregistrés que la clé d'instance ne peut pas lire : …*, avec leur nombre, jusqu'à ce qu'ils soient saisis à nouveau ou que l'ancienne clé soit rétablie. Aucun plugin fourni avec LibreFolio n'en conserve aujourd'hui.

---

## ⬇️ Créer une sauvegarde {: #create }

Deux moyens produisent la même archive :

| Où | Ce que vous obtenez |
| --- | --- |
| **Paramètres › Administration › Sauvegarde**, dans l'application (administrateurs) | L'archive téléchargée sur votre ordinateur, et une copie [conservée sur le serveur](#kept-backups) |
| **Terminal sur le serveur** : `backup create` | L'archive sur le serveur, ou là où vous l'indiquez avec `--output` |

Dans les deux cas, la sauvegarde peut être [sécurisée](#secure) : le même zip, chiffré avec un mot de passe que vous choisissez. Uniquement depuis la ligne de commande, elle peut être [scellée](backup_sealed.md#sealed) : chiffrée avec un mot de passe aléatoire que seule une clé privée qui vous appartient ouvre, pour les sauvegardes réalisées sans personne au clavier.

LibreFolio continue de fonctionner pendant la sauvegarde. Une seule sauvegarde s'exécute à la fois, quelle que soit la personne qui l'a lancée.

### 🖱️ Depuis Paramètres › Administration › Sauvegarde {: #settings-backup }

1. Ouvrez **Paramètres › Administration › Sauvegarde** (seuls les administrateurs disposent de cet onglet), section **Sauvegarder l'instance**.
2. Choisissez le type :
    - **En clair** (par défaut) : *Un simple .zip : qui possède le fichier voit toutes les données, et sur une autre instance les clés des fournisseurs de données doivent être saisies à nouveau.*
    - **Sécurisée** : *Un .lfbk chiffré avec un mot de passe que vous choisissez : seul ce mot de passe l'ouvre, et un mot de passe perdu ne peut pas être récupéré. Il emporte aussi les clés des fournisseurs de données.* Voir [Sauvegardes sécurisées](#secure).
3. Pour une sauvegarde sécurisée, saisissez le mot de passe dans **Mot de passe de la sauvegarde**, puis à nouveau dans **Le même mot de passe, à nouveau**. Les règles d'un mot de passe de compte s'appliquent, fournies par le serveur : l'indicateur sous le premier champ les liste au fil de la saisie (*Au moins 12 caractères*, *Une lettre majuscule*, *Une lettre minuscule*, *Un chiffre*, *Un caractère spécial*) et montre sa robustesse. Tant que les deux champs diffèrent, *Les deux mots de passe sont différents.* s'affiche et **Créer une sauvegarde** reste désactivé.
4. Cliquez sur **Créer une sauvegarde**. Les champs de mot de passe se vident aussitôt ; la carte suit la sauvegarde phase par phase (une sauvegarde sécurisée se termine par *Chiffrement avec votre mot de passe*).
5. À **Sauvegarde prête**, cliquez sur **Télécharger**. Le navigateur enregistre `librefolio-backup-20261015-121500.zip` (date et heure de début, en UTC), ou `.lfbk` pour une sauvegarde sécurisée, que la carte signale par *Chiffrée avec votre mot de passe : conservez-le bien, LibreFolio ne peut pas la récupérer.*

À savoir :

- 🔑 **Conservez le mot de passe d'une sauvegarde sécurisée** dans un gestionnaire de mots de passe, séparément de l'archive : LibreFolio n'en garde aucune copie, et sans lui personne n'ouvre l'archive, vous compris.
- 💾 Une copie reste sur le serveur, dans la liste des [sauvegardes conservées sur le serveur](#kept-backups), jusqu'à ce que vous la supprimiez ou que le [nettoyage automatique](#backup-cleanup) la retire : vous pouvez aussi la télécharger plus tard depuis cette liste. Une copie sur le même disque que les données n'est pas une vraie sauvegarde : conservez-en une ailleurs ([Garder des copies hors du serveur](#keep-copies)). **Supprimer du serveur** la retire aussitôt ; **Créer une nouvelle sauvegarde** en lance une autre.
- ⚠️ **Sauvegarde terminée, avec des avertissements** : la base de données a échoué au contrôle d'intégrité ou contient des références invalides et a été archivée telle quelle ; ou certains fichiers ont été exclus ; ou, pour une sauvegarde sécurisée, la clé d'instance n'a pas pu être utilisée et a été laissée de côté ([Créer une sauvegarde sécurisée](backup_moving.md#secure-problems)). L'archive est écrite malgré tout : lisez les avertissements avant de vous y fier.
- 🚦 **Une autre sauvegarde est en cours** (depuis l'application ou la ligne de commande) : la carte l'indique, réessayez quand elle sera terminée.

Ce que fait la carte d'une sauvegarde déjà en cours :

| Sauvegarde en cours | La carte |
| --- | --- |
| En clair, lancée depuis cet onglet de l'application ou un autre, dont la réponse n'est jamais arrivée (connexion coupée au démarrage) | Pas perdue : le prochain **Créer une sauvegarde** la retrouve, la suit et propose son téléchargement |
| Sécurisée, non lancée depuis cet onglet | Jamais suivie : seul son mot de passe ouvre l'archive. La carte indique qu'une autre sauvegarde est en cours |
| N'importe laquelle, alors que la carte propose déjà une archive | Elle continue de proposer la sienne et indique seulement qu'une autre sauvegarde est en cours |
| Lancée depuis la ligne de commande | Non suivie : son archive va ailleurs |

La carte n'indique jamais quelle sauvegarde est en cours : la console du navigateur le fait (identifiant et origine).

### ⌨️ Depuis la ligne de commande {: #command-line }

**Dans le terminal du serveur**, depuis le dossier qui contient `docker-compose.yml` (Docker) ou depuis le dossier de LibreFolio (installation sur l'hôte) :

```bash
# Docker: l'archive apparaît dans son propre dossier de ./LibreFolio-data/backups/ sur l'hôte
docker compose exec librefolio python dev.py backup create

# Installation sur l'hôte: l'archive va dans son propre dossier de backups/ du répertoire de données
pipenv run ./dev.py backup create

# Une sauvegarde sécurisée (.lfbk): le mot de passe est demandé deux fois
docker compose exec librefolio python dev.py backup create --encrypt
```

La commande affiche le chemin de l'archive et son `SHA-256:`.

- 🗃️ Sans `--output`, l'archive reste sur le serveur, dans un dossier qui lui est propre à l'intérieur de `backups/` ([Sauvegardes conservées sur le serveur](#kept-backups)).
- 📁 `--output` (`-o`) copie l'archive dans un autre dossier qui existe déjà, ou sous un nom de votre choix ; rien ne reste dans `backups/`. Avec Docker, le chemin est à l'intérieur du conteneur : utilisez un dossier monté depuis l'hôte.
- 🔒 Seul le propriétaire de l'archive peut la lire (`0600`) : avec Docker, l'utilisateur du conteneur.
- 🔐 `--encrypt` crée une [sauvegarde sécurisée](#secure), `librefolio-backup-<date>-<time>.lfbk`, et demande deux fois le mot de passe au terminal. À la place : `--password-file FILE`, un fichier qui contient le mot de passe seul (les retours à la ligne en fin de fichier ne comptent pas), comme un secret Docker ; ou `--password-stdin`, une ligne de l'entrée standard provenant d'un tube (à un terminal, la commande le demande sans l'afficher). L'une ou l'autre rend la sauvegarde sécurisée à elle seule, avec ou sans `--encrypt` ; on ne les utilise pas ensemble.
- 🙈 Il n'y a pas de `--password` : tous les utilisateurs du serveur lisent les commandes en cours d'exécution (`ps`), et le shell les garde dans son historique.
- 📏 Règles du mot de passe, comme dans Paramètres › Administration › Sauvegarde : au moins 12 caractères, une majuscule, une minuscule, un chiffre et un symbole. Sinon la commande s'arrête avant d'écrire quoi que ce soit : `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Sans terminal (cron, script), `--encrypt` seul s'arrête : `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Chaque option, avertissement et erreur : «Sauvegarder l'instance» et «Sauvegarder avec Docker» dans [Outils d'administration CLI](cli_tools.md).

??? example "🐳 Le mot de passe des sauvegardes comme secret Docker"

    1. **À côté de `docker-compose.yml`**, écrivez le mot de passe seul dans un fichier, tel que `backup_password.txt`, jamais dans `LibreFolio-data/` (quiconque aurait les données aurait aussi le mot de passe). Puis `chmod 600 backup_password.txt`, et gardez une copie du mot de passe ailleurs : perdu, il ne peut pas être récupéré.
    2. **Dans `docker-compose.yml`**, ajoutez les lignes marquées et laissez le reste du service tel quel. Si le fichier a déjà des listes `secrets:`, par exemple pour `JWT_SECRET_FILE` («Secrets dans des fichiers» dans [Variables d'environnement](configuration.md)), ajoutez-y les lignes.

        ```yaml
        services:
          librefolio:
            secrets:                              # ajouté
              - backup_password                   # ajouté
        secrets:                                  # ajouté
          backup_password:                        # ajouté
            file: ./backup_password.txt           # ajouté
        ```

        Exécutez `docker compose up -d` : le conteneur est recréé avec le secret.

    3. **Dans le terminal du serveur**, faites la sauvegarde avec le chemin du secret dans le conteneur :

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Sauvegardes conservées sur le serveur {: #kept-backups }

Une sauvegarde faite depuis l'application ou la ligne de commande n'est plus supprimée au bout d'une heure : elle reste sur le serveur jusqu'à ce que vous la supprimiez, ou que le [nettoyage automatique](#backup-cleanup) la retire. Chacune a son propre dossier dans `backups/` du répertoire de données : moment de création (UTC), origine (`ui` application, `cli` ligne de commande) et un court code qui distingue deux sauvegardes de la même seconde. L'archive à l'intérieur garde son nom habituel, `.zip`, `.lfbk` ou `.tar` :

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

`backups/.jobs/` ne contient qu'une sauvegarde en cours ou une sauvegarde qui a échoué, supprimée au bout d'une heure.

**Où les voir** : **Paramètres › Administration › Sauvegarde**, sous *Sauvegardes sur ce serveur*, ou **Fichiers › Sauvegardes**, la même liste ; administrateurs uniquement. **Actualiser**, en haut de la liste, la relit : une sauvegarde faite depuis la ligne de commande n'apparaît qu'alors. Pour chaque sauvegarde :

- 📅 date et heure de création, et origine : application ou ligne de commande ;
- 🔐 type : simple, avec mot de passe ([sécurisée](#secure)) ou [scellée](backup_sealed.md#sealed) ;
- 📏 taille et SHA-256 : cliquez pour copier la somme de contrôle entière et la comparer à celle du fichier téléchargé ;
- 📦 **Une fois restaurée** : l'espace qu'occupent ses contenus une fois restaurés, non compressés, c'est-à-dire ce que prendra une restauration ; survolez-le pour ses parties : la base de données, les fichiers téléversés, les rapports des courtiers et les autres fichiers. Une sauvegarde faite avant que LibreFolio ne l'enregistre affiche «—» ;
- ⬇️ **Télécharger** et 🗑️ **Supprimer**, qui retire aussitôt la sauvegarde du serveur.

!!! warning "💽 Téléchargez-la et gardez-la ailleurs"

    Une sauvegarde qui reste sur le même disque que vos données n'est pas une vraie sauvegarde : quand le disque est perdu, les données et leurs sauvegardes partent ensemble. Téléchargez l'archive et gardez-la sur un autre disque, un NAS ou hors site ([Garder des copies hors du serveur](#keep-copies)).

La liste ne montre que les sauvegardes faites par cette version de LibreFolio. Les fichiers `librefolio-backup-*.zip` isolés des versions précédentes dans `backups/` ne sont pas listés et LibreFolio ne les supprime jamais : supprimez-les vous-même quand vous n'en avez plus besoin.

### 🧹 Nettoyage automatique {: #backup-cleanup }

**Dans le panneau fermé Nettoyage automatique**, dans la section **Sauvegardes sur ce serveur** de **Paramètres › Administration › Sauvegarde** ou de **Fichiers › Sauvegardes**, vous réglez deux limites, toutes deux facultatives :

| Limite | Ce qu'elle fait | Désactivée |
| --- | --- | --- |
| Taille totale, en Mo | Quand les sauvegardes conservées pèsent davantage, les plus anciennes sont supprimées jusqu'à ce que le reste tienne | `0` |
| Âge maximal, en jours | Une sauvegarde plus ancienne est supprimée | `0` |

- 🛡️ **La dernière sauvegarde est toujours conservée**, quelles que soient les limites.
- ⏰ Le nettoyage s'exécute après chaque sauvegarde et au démarrage de LibreFolio, au plus une fois par heure : une modification enregistrée s'applique dans l'heure.
- 🏠 **Auto-hébergé :** les deux limites sont désactivées tant que vous ne les définissez pas.
- 🔍 Seules les sauvegardes de la liste sont nettoyées : jamais les anciennes archives isolées de `backups/`, une sauvegarde en cours ou une sauvegarde qui a échoué.
- ⌨️ Les sauvegardes de la ligne de commande restent au même endroit et suivent les mêmes limites : [Où restent les sauvegardes](cli_backup.md#backup-kept).

### 📊 La barre d'espace {: #space-used }

**Dans Fichiers**, au-dessus des onglets, les administrateurs voient la barre **Espace occupé** : la place que prend votre instance. Elle se met à jour avec **Actualiser** et chaque fois que la liste des sauvegardes conservées change. La légende donne la taille de chaque partie :

| Partie | Ce qu'elle compte |
| --- | --- |
| **Base de données** | La base de données et les fichiers qu'elle garde à côté |
| **Fichiers téléversés** | Les fichiers téléversés dans l'application, comme ceux de la page **Fichiers** |
| **Relevés des courtiers** | Les relevés téléversés pour importer des transactions |
| **Sauvegardes** | Tout ce qui est dans `backups/` : les [sauvegardes conservées sur le serveur](#kept-backups), une sauvegarde en cours et une sauvegarde qui a échoué |
| **Restauration en attente** | Une [restauration](#restore) pas encore terminée ni abandonnée : l'archive téléversée et sa version décompressée |
| **Autres fichiers de LibreFolio** | Le reste du répertoire de données : journaux, état et similaires |

Trois aspects de la barre :

| Situation | La barre | La ligne dessous |
| --- | --- | --- |
| 💽 **Pas de limite** (par défaut en auto-hébergement) | Tout le disque des données : les parties de LibreFolio en couleur, **Autres sur le disque** en gris, **Libre** vide | Combien LibreFolio utilise du disque |
| 📏 **Avec une limite** | La limite, remplie jusqu'où vont les données | *utilisé sur limite* |
| 📁 **Pas de limite et disque inconnu** (LibreFolio ne peut pas le demander) | Le seul dossier de LibreFolio, découpé en ses parties, sans espace libre | — |

**Définissez la limite** dans **Fichiers › Avancé** (panneau fermé sous la barre), champ **Espace total de LibreFolio (Mo)** : un nombre entier de mégaoctets, `0` pour aucune limite, puis **Enregistrer** ; un avis vert le confirme. C'est l'espace maximal que LibreFolio peut occuper au total. Le même champ se trouve dans **Paramètres › Administration › [Paramètres globaux](settings.md)**, catégorie **Mémoire** : l'un ou l'autre endroit le modifie.

- 🚧 **Au-delà de la limite**, LibreFolio refuse ce qui ajouterait des données : un fichier téléversé, un relevé de courtier, une sauvegarde lancée à la main (après avoir essayé le [nettoyage automatique](#backup-cleanup)) et une [restauration](#restore) dont le résultat la dépasserait. Le message indique à quelle valeur porter l'espace total et, si le disque manque de place, combien il faut encore de libre. Jamais bloqués : transactions, prix et base de données, les sauvegardes d'un panneau d'hébergement et de la ligne de commande (le nettoyage les suit) et une restauration déjà confirmée. La limite ne supprime rien par elle-même.
- ⚠️ La barre avertit que la limite est dépassée et suggère de supprimer des sauvegardes ou des fichiers, ou de relever la limite. Elle devient alors vos données, pour qu'aucune partie ne soit laissée de côté : un repère *Limite 20 Mo* montre où tombe la limite, les lignes rouges au-delà de combien vous la dépassez.
- 💬 **Un refus est annoncé là où vous êtes** : dans la fenêtre de téléversement ou d'import, ou sur la carte de sauvegarde. Un administrateur y trouve **Ouvrir les paramètres**, qui ouvre **Paramètres › Administration › Paramètres globaux** avec la ligne **Espace total de LibreFolio (Mo)** en vue et mise en évidence : déverrouillez l'onglet pour la modifier ; un utilisateur lit combien d'espace libérer, ou de le demander à un administrateur. Avec une limite fixée par la personne qui héberge l'instance, le message dit de la lui demander.
- 🔒 **Définie dans la configuration du serveur** : avec `LIBREFOLIO_STORAGE_LIMIT_MB` dans l'environnement, sa valeur est la limite, le champ est en lecture seule, ici et dans Paramètres globaux, et une note indique qu'elle est fixée par la personne qui héberge l'instance ([Variables d'environnement](configuration.md)). Une valeur qui n'est pas un nombre entier est ignorée et le champ fonctionne comme ci-dessus.
- 🧹 **Nettoyage et barre travaillent ensemble.** En général ce sont les sauvegardes qui grossissent : le [nettoyage automatique](#backup-cleanup) les maîtrise, et chaque sauvegarde supprimée dans **Paramètres › Administration › Sauvegarde** ou dans **Fichiers › Sauvegardes** raccourcit **Sauvegardes** dans la barre. Près de la limite, commencez par là.

### 🗄️ Garder des copies hors du serveur {: #keep-copies }

`backups/` se trouve dans le répertoire de données, sur le même disque : une sauvegarde qui s'y trouve ne survit pas à la perte du disque. Une archive téléchargée depuis les Paramètres est déjà hors du serveur. Depuis la ligne de commande, écrivez les archives sur un autre disque, un NAS ou hors site avec `--output`, selon un calendrier.

**Dans le `crontab` de l'utilisateur qui exécute LibreFolio** (`crontab -e`), installation sur l'hôte, chaque nuit à 03:30 :

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

**Avec Docker**, ajoutez `-T` (cron ne donne aucun terminal à la commande). L'archive arrive dans un dossier qui lui est propre de `LibreFolio-data/backups/`, où le [nettoyage automatique](#backup-cleanup), une fois réglé, évite que le disque se remplisse : copiez-la ailleurs avec votre outil habituel.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

**Archives [sécurisées](#secure)** : ajoutez `--password-file` avec un fichier qui contient le mot de passe (cron n'a pas de terminal pour le demander). Avec Docker, le secret de l'exemple ci-dessus :

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 Le dossier de `--output` doit exister quand la commande s'exécute : montez d'abord le NAS. Un chemin qui n'est pas un dossier existant devient le nom de l'archive.
- 🔢 La commande affiche ce qu'elle a fait et se termine avec `1` quand l'archive n'est pas là où vous l'avez demandé : gardez la sortie, ou faites-la envoyer par e-mail par cron.
- 🧭 cron a un `PATH` court : s'il ne trouve pas `pipenv` ou `docker`, écrivez le chemin complet (`command -v pipenv` l'affiche).
- 🗑️ LibreFolio ne supprime aucune de ces archives : retirez vous-même les anciennes. Gardez-en plusieurs, et la dernière faite avant chaque mise à jour.
- 🔑 Gardez aussi une copie de `.env`, aussi privée que les archives : aucune archive ne la contient. Et une copie de `secrets/`, sauf si vos archives sont sécurisées : une archive en clair ou [scellée](backup_sealed.md#sealed) laisse de côté la clé d'instance ([Ce qui suit](#what-follows)).
- 🔏 Des archives nocturnes que le serveur lui-même ne peut pas ouvrir, sans fichier de mot de passe sur son disque : [Chaque nuit avec cron](backup_sealed.md#sealed-cron), dans Sauvegardes scellées.

### 🧰 Sauvegardes avec restic ou Backrest {: #restic }

LibreFolio écrit l'archive ; un outil de sauvegarde l'emmène hors site et en garde l'historique. [restic](https://restic.net/) copie un dossier, chiffré, vers S3, Backblaze B2, SFTP et d'autres, et oublie les anciennes copies selon une règle de votre choix. [Backrest](https://github.com/garethgeorge/backrest) est une interface web pour restic, avec son propre planificateur. LibreFolio n'a besoin ni de l'un ni de l'autre : ils ne font que lire le dossier de ses archives.

Recette nocturne, installation sur l'hôte. **Dans un fichier privé** (`chmod 600`), les variables de restic :

```bash
# /etc/librefolio-restic.env: où vont les copies, et le fichier avec le mot de passe de restic
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

**Dans le `crontab`** :

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

La ligne crée l'archive, envoie le dossier, garde sept copies quotidiennes et quatre hebdomadaires dans le dépôt et supprime les archives locales de plus de deux jours. Avec Docker, créez l'archive avec la commande de [Garder des copies hors du serveur](#keep-copies) et donnez à restic le dossier de l'hôte `LibreFolio-data/backups/`. Avec Backrest, ajoutez un plan sur ce dossier, avec son calendrier et sa rétention, et laissez `backup create` dans cron.

- 🔐 **Le mot de passe de restic est une clé de toutes vos données** : qui le détient lit chaque copie. Aussi privé que le mot de passe d'une [sauvegarde sécurisée](#secure), avec une copie ailleurs : perdu, le dépôt ne peut plus être lu.
- 🔑 **Pas de clé publique.** restic utilise son mot de passe pour écrire comme pour lire : le serveur qui envoie les copies peut aussi les lire. Si c'est un problème, envoyez des [sauvegardes scellées](backup_sealed.md#sealed-cron) (`--sealed`) : seule votre clé privée les ouvre, ni le serveur ni le mot de passe de restic. Les [sauvegardes sécurisées](#secure) (`--password-file`) conviennent aussi, mais leur mot de passe se trouve dans un fichier sur le même serveur.
- 📦 **Peu à dédupliquer.** Chaque archive est compressée, une archive sécurisée est chiffrée : restic stocke chaque archive presque entière. Prévoyez l'espace du dépôt pour les copies que vous gardez.
- 🧪 **Essayez une restauration avant d'en avoir besoin.** `restic restore latest --target /tmp/librefolio-check`, puis vérifiez l'archive avec [`backup restore --dry-run`](#check).

---

## 🔐 Sauvegardes sécurisées {: #secure }

Une sauvegarde sécurisée est l'archive d'une sauvegarde en clair, chiffrée avec un mot de passe que vous choisissez, dans un fichier propre à LibreFolio : `.lfbk`. Vous la créez depuis [Paramètres › Administration › Sauvegarde](#settings-backup) ou avec `backup create --encrypt` en [ligne de commande](#command-line) ; toutes les vérifications et restaurations de cette page l'acceptent, avec son mot de passe.

- 🛡️ **Elle protège le fichier au repos.** Disque perdu, ordinateur portable volé, copie sur un cloud ou un NAS : sans le mot de passe rien ne peut être lu, ni les données ni les noms des fichiers. Un fichier modifié ou tronqué est détecté à l'ouverture et refusé.
- 👁️ **Elle ne protège pas de qui connaît le mot de passe** : cette personne lit tout, les données de chaque utilisateur et les clés des fournisseurs de données. Ne le donnez qu'à qui peut restaurer la sauvegarde, jamais avec le fichier.
- 🗝️ **Elle emporte la clé d'instance**, si LibreFolio l'a générée (`secrets/instance.key`) : les clés enregistrées des fournisseurs de données voyagent avec la sauvegarde, et la restauration les rechiffre avec la clé de l'installation qui la reçoit, qui garde la sienne. Une clé que vous avez définie vous-même (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) ne sort jamais.
- 🆘 **Un mot de passe perdu ne peut pas être récupéré.** LibreFolio n'en garde aucune copie, et rien d'autre n'ouvre le fichier.
- ⏳ **Lente à deviner.** La clé du fichier dérive du mot de passe par scrypt : 32 MiB de mémoire et environ un dixième de seconde par essai, rien pour une sauvegarde, lent pour qui essaie des mots de passe l'un après l'autre. D'où les règles : au moins 12 caractères, une majuscule, une minuscule, un chiffre et un symbole.
- 💽 **Sur le serveur, pendant qu'elle est créée,** l'archive en clair est d'abord écrite, dans le dossier de travail de la sauvegarde à l'intérieur de `backups/`, que seul l'utilisateur du serveur peut ouvrir ; elle est supprimée dès que le `.lfbk` est écrit, et quand la sauvegarde échoue. Après une interruption brutale (coupure de courant, `kill -9`), le prochain démarrage de LibreFolio supprime ce qui était resté en clair, et la sauvegarde doit être refaite. Une vérification déchiffre la sauvegarde de la même façon : [Vérifier une sauvegarde](#check).

La conception, pour les développeurs : [Sauvegardes sécurisées (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Vérifier une sauvegarde {: #check }

Deux commandes vérifient une archive sans rien modifier. **Dans le terminal du serveur**, à l'intérieur du conteneur avec Docker : une archive de `LibreFolio-data/backups/` s'y trouve dans `/app/backend/data/prod-docker/backups/`, et une sauvegarde [conservée](#kept-backups) est dans son propre dossier, tel que `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# L'archive est-elle entière, et que contient-elle ?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Cette installation peut-elle la restaurer ? Une restauration essayée sur une copie
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# Une sauvegarde sécurisée: les mêmes commandes demandent d'abord son mot de passe
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

Installation sur l'hôte : `pipenv run ./dev.py backup …` avec le chemin de l'archive sur l'hôte.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| Il répond | Si l'archive est entière : taille et SHA-256 de chaque entrée, comparés au manifeste | Si cette installation peut la restaurer : archive décompressée dans une copie, mise à jour et vérifiée |
| Il montre | Qui a créé l'archive et quand, révision de la base de données, lignes et tables, fichiers, si la clé d'instance est incluse | La même chose, plus : les migrations qu'une restauration appliquerait, les totaux du grand livre de la copie comparés à ceux de l'archive, les clés des fournisseurs rechiffrées avec la clé de cette installation ou à saisir à nouveau, les administrateurs avec lesquels vous vous connecteriez |
| Il lui faut | N'importe quel LibreFolio, serveur démarré ou arrêté ; pas de répertoire de données, sauf pour une sauvegarde sécurisée, qu'il y déchiffre | L'installation qui recevrait l'archive (le serveur peut continuer de tourner) et de la place libre dans son répertoire de données : archive décompressée + deux fois sa base de données + 64 Mo |
| Il se termine par | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Sauvegarde sécurisée** (`.lfbk`) : les deux demandent d'abord le mot de passe, au terminal ou avec `--password-file FILE` / `--password-stdin`, comme `backup create`. Elles la déchiffrent dans un dossier privé du répertoire de données, que seul l'utilisateur du serveur peut ouvrir, et suppriment l'archive déchiffrée à la fin : il faut aussi de la place pour cela, environ la taille du `.lfbk`. Après une interruption brutale (coupure de courant, `kill -9`), le prochain démarrage de LibreFolio supprime ce qui était resté en clair : l'archive de `--dry-run` aussitôt, le dossier de `inspect` au bout d'une heure, que le prochain `inspect` supprime aussi. Le rapport ajoute `Secure backup: decrypted with its password`. Mot de passe erroné : `❌ The password does not open this backup (wrong_password)`. Un `.zip` ignore les deux options.
- 🗝️ `--dry-run` indique ce que deviennent les clés enregistrées des fournisseurs de données, pour n'importe quelle archive : `Saved provider keys: 2 re-encrypted with this instance's key` si la sauvegarde contient la clé qui les a chiffrées, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` pour celles qu'il ne peut pas lire ([Ce qui suit](#what-follows)).
- 🔁 Exécutez `inspect` de temps en temps sur les copies que vous gardez, et `--dry-run` avant un déplacement, sur l'installation qui recevra l'archive.
- 🖱️ **Restaurer une archive**, dans Paramètres › Administration › Sauvegarde, exécute la même vérification que `--dry-run` sur une archive de votre ordinateur : lisez le rapport, puis **Abandonner cette archive**, et rien ne change ([Restaurer depuis Paramètres › Administration › Sauvegarde](#restore-settings)).
- ❌ Un refus se termine par un code entre parenthèses : [Quand quelque chose ne va pas](backup_moving.md#troubleshooting). Listes complètes dans «Vérifier une archive» et «Essayer une restauration sur une copie», dans [Outils d'administration CLI](cli_tools.md).

---

## ♻️ Restaurer sur cette installation {: #restore }

Une restauration remplace les données de l'installation par celles de l'archive : base de données et fichiers, pour chaque utilisateur. Deux moyens, qui vérifient d'abord l'archive sur une copie et ne changent rien tant que vous n'avez pas confirmé ; le prochain démarrage de LibreFolio applique la restauration :

| Où | Qui | Après confirmation |
| --- | --- | --- |
| **Paramètres › Administration › Sauvegarde**, dans l'application | Les administrateurs | LibreFolio s'arrête aussitôt, pour ce démarrage |
| **Terminal sur le serveur** : `backup restore` | Qui a accès au serveur | Vous le redémarrez quand cela vous convient |

Sur une instance que quelqu'un héberge pour vous, la ligne de commande est sur son serveur : utilisez Paramètres › Administration › Sauvegarde, ou demandez-lui.

### 🖱️ Restaurer depuis Paramètres › Administration › Sauvegarde {: #restore-settings }

1. **Choisissez l'archive.** Dans **Paramètres › Administration › Sauvegarde**, sous **Sauvegarder l'instance**, la carte **Restaurer une archive** vous rappelle qu'une restauration remplace les données de chaque utilisateur : si vous pourriez vouloir les récupérer, [faites d'abord une sauvegarde](#settings-backup). **Choisir une archive…** → un `.zip` ou un `.lfbk` sécurisé créé par LibreFolio, ici ou ailleurs. La fenêtre **Restaurer une archive** s'ouvre, et les étapes suivantes s'y déroulent : un `.zip` part aussitôt vers le serveur, avec une barre de progression : **Arrêter l'envoi** l'interrompt, rien n'est conservé.

    **Ou prenez une sauvegarde que le serveur conserve** : **Restaurer** sur sa ligne dans la liste des [sauvegardes conservées sur le serveur](#kept-backups), ici ou dans **Fichiers › Sauvegardes**, ouvre la fenêtre **Restaurer une sauvegarde**, sans autre confirmation : le serveur prend cette sauvegarde comme archive, sans téléchargement ni téléversement, et les étapes suivantes, rapport compris, se déroulent dans cette fenêtre. Fermez-la, ou choisissez **Je déciderai plus tard** dans le rapport : la vérification attend sur la carte **Restaurer une archive**, avec **Reprendre** et **Écarter**. Une sauvegarde scellée d'un panneau d'hébergement ne s'ouvre qu'avec la clé privée de ses destinataires : elle n'est pas restaurée ici.

2. **Saisissez le mot de passe**, pour une sauvegarde sécurisée : la fenêtre le demande avant d'envoyer quoi que ce soit (*Une sauvegarde sécurisée : saisissez le mot de passe avec lequel elle a été faite.*). Remplissez **Mot de passe de la sauvegarde** et cliquez sur **Vérifier la sauvegarde** : l'archive est envoyée, et le mot de passe part avec la requête qui lance la vérification, qui l'essaie aussitôt. Mot de passe erroné → *Mot de passe erroné, ou le fichier a été modifié : saisissez à nouveau le mot de passe.* ; l'archive reste sur le serveur et l'essai suivant ne la renvoie pas. **Annuler** oublie le fichier.
3. **Laissez-la se vérifier.** Le serveur vérifie l'archive sur une copie, comme le fait `backup restore --dry-run` ([Vérifier une sauvegarde](#check)) : *Déchiffrement de la sauvegarde* (sécurisée uniquement), *Vérification de l'archive*, *Extraction sur une copie*, *Mise à jour de la base de données de la copie*, *Vérification de la copie*. Rien ne change tant que vous n'avez pas confirmé. **Arrêter la vérification** l'abandonne (une vérification encore en cours est abandonnée dès qu'elle se termine).
4. **Lisez le rapport**, dans la fenêtre **Ce que ferait cette restauration** : la fermer garde la vérification pour plus tard, comme le fait **Je déciderai plus tard**. Fermer la fenêtre pendant la vérification la garde aussi : la vérification continue, et **Reprendre** la suit à nouveau. Ce qu'il dit : ci-dessous.
5. **Saisissez le mot.** La fenêtre montre un vrai mot, tiré au hasard, de 6 à 10 lettres dans la langue de l'interface. Saisissez-le à la main dans le champ en dessous : le champ refuse le texte collé ou déposé. Le mot protège d'un clic hâtif, pas d'un administrateur : l'API et la ligne de commande s'en passent. Pour une archive qui ne peut pas être restaurée, ni le mot ni **Restaurer et redémarrer** n'apparaissent : seulement le bouton qui l'abandonne.
6. **Restaurer et redémarrer.** Il confirme la restauration et arrête LibreFolio aussitôt, pour tout le monde. Une fenêtre recouvre la page, **LibreFolio redémarre** : *Son démarrage applique la restauration. Cette page attend son retour.* LibreFolio ne redémarre pas tout seul : ce qui le supervise le fait ([Qui redémarre LibreFolio](#supervisors)), et ce démarrage applique la restauration ([Ce que fait le prochain démarrage](#next-start)).

#### 📋 Ce que dit le rapport

- qui a créé l'archive, avec quelle version de LibreFolio et quand ;
- la base de données : à la version de ce LibreFolio, ou amenée à celle-ci sur la copie, avec les migrations listées et les corrections appliquées à la copie ;
- les fichiers et leur taille, la taille de la base de données et les tables dont la mise à jour a changé les lignes ; et une barre de ce que contient la sauvegarde : la base de données, les fichiers téléversés, les relevés des courtiers et les autres fichiers ;
- si la sauvegarde contient la clé de l'instance d'où elle vient : dans les deux cas, ce LibreFolio garde la sienne ;
- les clés enregistrées des fournisseurs de données : combien sont rechiffrées avec la clé de ce LibreFolio (*2 clés enregistrées de fournisseurs de données sont rechiffrées avec la clé de cette instance.*) et combien sont illisibles, à saisir à nouveau après la restauration (*1 clé enregistrée d'un fournisseur de données ne peut pas être lue avec la clé de cette instance : saisissez-la à nouveau après la restauration.*) ([Ce qui suit](#what-follows)) ;
- les totaux du grand livre : identiques à ceux du moment de la sauvegarde, différents sur les lignes listées ([comment les lire](backup_moving.md#check-refused)), non enregistrés, enregistrés par une autre version de la méthode ou illisibles ;
- les administrateurs de la sauvegarde, avec *Après la restauration, on se connecte avec l'un d'eux, avec le mot de passe de l'époque ; toutes les sessions ouvertes maintenant se ferment.*
- *Les invitations et les liens envoyés avant la restauration auront expiré : renvoyez-les si nécessaire.*
- chaque administrateur avec la photo de son compte dans la sauvegarde, et **Vérifier un mot de passe avant de restaurer** : choisissez-en un, saisissez son mot de passe et cliquez sur **Vérifier**. Réponse : *Vous vous connecterez avec ce mot de passe après la restauration.*, ou *Ce n'est pas son mot de passe.* Le mot de passe est comparé uniquement à la sauvegarde : jamais stocké, écrit dans le journal ni renvoyé ;
- les avertissements, qui laissent continuer, et les blocages, qui interdisent la restauration : une sauvegarde sans administrateur actif, et une restauration qui dépasserait la [limite d'espace](#space-used), avec la valeur à laquelle la porter ; une telle vérification rend aussitôt sa place, et le rapport reste à l'écran jusqu'à ce que vous le fermiez ;
- jusqu'à quand l'archive téléversée est conservée : 24 heures après la vérification.

Sous le rapport : **Abandonner cette archive** abandonne la vérification et sa copie, rien n'est restauré. **Je déciderai plus tard** ferme la fenêtre et garde la vérification : la carte **Restaurer une archive** affiche *Une restauration attend votre décision jusqu'au …*, avec **Reprendre**, qui rouvre le même rapport, et **Écarter**, depuis n'importe quel onglet ou appareil d'un administrateur.

#### 🏁 Comment cela s'est passé

Quand LibreFolio répond à nouveau, la page montre le résultat :

| Résultat | Ce que vous voyez | Que faire |
| --- | --- | --- |
| ✅ **Ça a marché** | La page de connexion, sans message : toutes les sessions ont pris fin. Une restauration réussie ne laisse aucune ligne sur la carte | Connectez-vous avec un administrateur de la sauvegarde, avec le mot de passe qu'il avait quand la sauvegarde a été faite : la première page montre les données restaurées |
| ↩️ **Ça n'a pas abouti** | **La restauration n'a pas abouti**, avec la raison. *Les données sont comme avant : …* = annulée, la carte dit quand et pourquoi. *LibreFolio a redémarré, mais la restauration n'a pas été appliquée.* = un démarrage l'a laissée en attente, pour la raison qui suit | **Retour à la sauvegarde** ramène à la carte (après la page de connexion si le redémarrage a mis fin à votre session, ou à la page de blocage sur une instance bloquée entre-temps). Puis [Ce que dit Paramètres › Administration › Sauvegarde](backup_moving.md#restore-settings-problems) |
| ⏳ **Ça prend du temps** | Après une minute sans le serveur : *LibreFolio n'est pas encore revenu. Si rien ne le redémarre tout seul, démarrez-le vous-même : la restauration est appliquée à ce démarrage.* Si LibreFolio ne s'arrête pas du tout, après une minute : *LibreFolio ne s'est pas arrêté. S'il ne redémarre pas tout seul, redémarrez-le vous-même : la restauration est appliquée à ce démarrage.*, avec **Retour à la sauvegarde** | [Ce que dit Paramètres › Administration › Sauvegarde](backup_moving.md#restore-settings-problems) |

La page lit le résultat avec un ticket à usage unique reçu de la requête de redémarrage, valable une heure et conservé uniquement dans la mémoire de l'onglet : aucune session n'est nécessaire. Sans le ticket (page rechargée, plus d'une heure d'attente, redémarrage depuis la ligne de commande plutôt que d'ici), la page se fie à sa session : sans `JWT_SECRET`, qui déconnecte tout le monde à chaque démarrage ([Garder les utilisateurs connectés après un redémarrage](index.md#session-persistence)), elle va à la page de connexion quel que soit le résultat, et **Paramètres › Administration › Sauvegarde** indique, une fois que vous êtes connecté, si la restauration a abouti.

#### ⏳ Une restauration en attente

Une restauration confirmée et pas encore appliquée prend la place de **Choisir une archive…** : une restauration confirmée depuis la ligne de commande, ou ici quand LibreFolio ne s'est pas arrêté ou qu'un démarrage l'a laissée en attente. La carte affiche **Une restauration attend le prochain démarrage de LibreFolio**, avec la sauvegarde, qui l'a confirmée (`cli` depuis la ligne de commande) et quand, la raison si un démarrage l'a laissée en attente, et *Le redémarrage arrête LibreFolio pour tout le monde ; son prochain démarrage applique la restauration et ferme toutes les sessions.*

| Bouton | Ce qu'il fait |
| --- | --- |
| **Redémarrer et restaurer** | Arrête LibreFolio, comme **Restaurer et redémarrer** ; la page l'attend de la même façon |
| **Annuler la restauration** | L'abandonne avec sa copie vérifiée, comme `backup pending --cancel` : les données restent telles quelles |

Pendant qu'un démarrage applique la restauration, la carte affiche *Un démarrage de LibreFolio applique la restauration.*

À savoir :

- 👑 Seuls les administrateurs ont l'onglet. Une seule restauration à la fois : une seule archive est vérifiée à la fois, où que la vérification ait été lancée, ici, dans un autre onglet ou en ligne de commande (*Une autre archive est en cours de vérification : réessayez quand elle sera terminée.*).
- 📏 Si l'installation limite la taille des archives (`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, aucune par défaut), la carte l'indique (*Archives jusqu'à 500 Mo.*) et refuse un fichier plus grand avant d'envoyer quoi que ce soit : [La limite de téléversement d'une restauration](#restore-upload-limit).
- 💽 Le disque du répertoire de données a besoin de place pour l'archive, pour sa copie pendant la vérification et, pour une sauvegarde sécurisée, pour l'archive déchiffrée : combien, dans [Vérifier une sauvegarde](#check).
- 📦 Pendant la vérification, l'archive occupe sa taille sur le serveur, que la carte indique pendant le téléversement, plus sa version décompressée ; les deux comptent dans la limite d'espace jusqu'à ce que la restauration se termine ou soit abandonnée.
- 🔑 Le mot de passe d'une sauvegarde sécurisée ne va au serveur qu'avec la requête qui lance la vérification, qui l'essaie aussitôt : jamais stocké, écrit dans le journal ni renvoyé. Le champ se vide dès que vous l'envoyez.
- 🔄 Un rechargement de la page continue de suivre la vérification et le rapport, et tout autre onglet ou appareil d'un administrateur la reprend depuis l'onglet Sauvegarde. L'archive téléversée est conservée 24 heures : ensuite, la confirmation répond *La vérification est trop ancienne : vérifiez de nouveau l'archive.*
- 🚪 La restauration met fin à toutes les sessions, tout le monde se reconnecte avec un compte de la sauvegarde, et les liens envoyés avant cessent de fonctionner : [Ce que fait le prochain démarrage](#next-start).
- ❌ Un téléversement, une vérification ou une confirmation refusés, ou un serveur qui ne répond pas, s'affichent sur la carte avec la raison. **Réessayer** relit l'état de la restauration ; pour envoyer à nouveau une archive, **Choisir une archive…**. La vérification refuse les mêmes archives que la ligne de commande : [La vérification refuse l'archive](backup_moving.md#check-refused).
- 🖥️ Si rien ne redémarre LibreFolio, comme une installation sur l'hôte lancée à la main, [démarrez le serveur](cli_tools.md#start-the-server) vous-même une fois qu'il s'est arrêté : la page l'attend.

### 📤 La limite de téléversement d'une restauration {: #restore-upload-limit }

Un administrateur téléverse l'archive depuis Paramètres › Administration › Sauvegarde ([Restaurer depuis Paramètres › Administration › Sauvegarde](backup_restore.md#restore-settings)), via `PUT /api/v1/backup/restore/upload`, et l'instance la vérifie sur une copie, comme le fait `backup restore --dry-run` en [ligne de commande](cli_tools.md). Deux variables limitent sa taille.

**`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`** limite l'archive telle qu'elle est envoyée, compressée :

| Valeur | Plus grande archive acceptée |
| --- | --- |
| Non définie, ou vide | Aucune limite |
| `0` | Aucune limite |
| Un nombre entier, tel que `2048` | Ce nombre de mégaoctets, de 1024 × 1024 octets chacun |

1. **Dans `.env`**, ou dans l'environnement du conteneur :

    ```bash
    LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
    ```

2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.
3. **Dans la configuration du proxy** placé devant LibreFolio, laissez passer au moins autant : Nginx avec `client_max_body_size`, par défaut seulement 1 Mo (`client_max_body_size 2048m;` correspond à l'exemple), et votre CDN, s'il limite la taille d'une requête.

La limite en vigueur se lit dans `upload_limit_mb` de `GET /api/v1/backup/restore/status` : `0` aucune limite, `null` valeur illisible. Paramètres › Administration › Sauvegarde l'affiche sur la carte de restauration (*Archives jusqu'à 500 Mo.*) et refuse un fichier plus grand avant de l'envoyer.

| Le téléversement répond | Code | Quand |
| --- | --- | --- |
| `413` | `backup_too_large`, avec la limite dans `limit_mb` | Archive au-delà de la limite : avant d'écrire quoi que ce soit si la requête annonce sa taille, sinon dès que le téléversement dépasse la limite. Rien n'est conservé |
| `413` sans `backup_too_large` | — | Il vient du proxy, pas de LibreFolio |
| `503` | `backup_upload_unavailable` | Valeur qui n'est pas un nombre entier (`500MB`, `-1`) : le serveur ne s'arrête pas, mais le journal de démarrage contient déjà `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` vaut `backup.upload_limit`) et chaque téléversement ajoute au journal une erreur qui nomme la variable : `The upload limit of a restore cannot be read` |
| `507` | `backup_no_space` | Le disque du répertoire de données n'a pas de place pour l'archive et, pendant la vérification, pour sa copie décompressée (combien : «Essayer une restauration sur une copie» dans [Outils d'administration CLI](cli_tools.md)) ; aussi quand le disque ne se déclare plein qu'à la fin du fichier, comme peut le faire un système de fichiers réseau ou un quota. La vérification a son propre code, `no_space` : `507` si elle ne peut même pas démarrer, refus de l'archive une fois qu'elle s'exécute |
| `500` | `backup_upload_failed` | Le téléversement ne peut pas être écrit pour une autre raison ; le journal contient la cause |

**`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`** limite la taille décompressée, d'après les tailles que déclare le manifeste, avant que la vérification ne décompresse quoi que ce soit : un zip peut se décompresser en bien plus que sa taille, sur le disque du répertoire de données.

| Valeur | Plus grande taille décompressée d'une archive |
| --- | --- |
| Non définie, ou vide | Aucune limite |
| `0` | Aucune limite |
| Un nombre entier, tel que `16384` | Ce nombre de mégaoctets, de 1024 × 1024 octets chacun |

- Une archive au-delà de la limite est refusée avant que quoi que ce soit ne soit décompressé : la vérification échoue avec le code `unpacked_too_large`, rien de la copie ne reste. Une archive sécurisée est d'abord déchiffrée (environ sa taille), puis mesurée de la même façon.
- Une valeur que vous définissez l'emporte toujours, `0` compris. `backup restore` en ligne de commande suit la même limite ; qui exécute le serveur la lève pour une commande avec `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` devant elle («Essayer une restauration sur une copie» dans [Outils d'administration CLI](cli_tools.md)).
- Une valeur qui n'est pas un nombre entier n'arrête pas le serveur : le journal de démarrage contient déjà `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` vaut `backup.restore_limit`), puis chaque vérification, `POST /api/v1/backup/restore/stage`, répond `503` avec le code `backup_restore_unavailable`, l'archive est conservée et le journal contient une erreur.

### ⌨️ Restaurer depuis la ligne de commande {: #restore-command }

**Dans le terminal du serveur**, là où LibreFolio s'exécute : dans le conteneur avec Docker.

```bash
# 1. Vérifier l'archive sur une copie, lire le rapport, puis taper "restore" pour confirmer
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Redémarrer LibreFolio: son prochain démarrage applique la restauration
docker compose restart librefolio

# 3. Voir comment cela s'est passé
docker compose exec librefolio python dev.py backup pending
```

- 🧪 L'étape 1 exécute la même vérification que `--dry-run`, montre le même rapport, puis vous demande de taper `restore`. Rien ne change encore : LibreFolio continue de tourner sur ses données, la restauration attend le prochain démarrage.
- 🖥️ Installation sur l'hôte : `pipenv run ./dev.py backup restore <archive>`, puis arrêtez tout le serveur et [démarrez-le](cli_tools.md#start-the-server) à nouveau : jamais un seul worker.
- ⏳ Une fois LibreFolio reparti, `backup pending` affiche `✅ The last restore was applied on …`. Avant le redémarrage, `backup pending --cancel` abandonne la restauration en attente, avec sa copie vérifiée.
- 🤖 Dans un script, `--yes` confirme sans demander.
- 🔐 Sauvegarde sécurisée (`.lfbk`) : `backup restore` demande le mot de passe avant la vérification, ou le lit avec `--password-file` ou `--password-stdin`, comme le fait `inspect` ([Vérifier une sauvegarde](#check)) : dans un script, l'un des deux avec `--yes`.
- 📖 Plus de détails : «Restaurer une archive» et «Suivre ou annuler une restauration» dans [Outils d'administration CLI](cli_tools.md).

### 🔄 Ce que fait le prochain démarrage {: #next-start }

- 🔀 **L'échange.** La base de données et les trois dossiers de fichiers changent de place avec la copie vérifiée, en un instant quelle que soit la taille. `secrets/`, `logs/`, `scheduler_state.json` et `backups/` restent tels quels : l'installation garde sa propre clé d'instance. La clé qu'emporte une sauvegarde sécurisée n'est jamais mise à sa place : la vérification a déjà rechiffré les clés des fournisseurs de données sur la copie, avec la clé de cette installation.
- 🚪 **Toutes les sessions prennent fin.** Tout le monde se reconnecte, sur chaque appareil, avec un compte de la sauvegarde et le mot de passe qu'il avait alors.
- 🔗 **Les liens à usage unique sont révoqués.** Aucun lien d'invitation, de réinitialisation de mot de passe ou de vérification d'e-mail envoyé avant ne fonctionne plus, pas même ceux de la sauvegarde : envoyez-en de nouveaux. Un compte encore en attente de sa vérification d'e-mail cesse d'attendre : quand son propriétaire demande un nouveau lien à la page de connexion, la page répond que le compte est désactivé. Un administrateur le réactive avec **Réactiver** ([Ce que fait chaque action](users.md#actions)) ou le supprime ([Supprimer un compte](users.md#delete)) pour que son propriétaire s'inscrive à nouveau.
- ✅ **Le premier démarrage doit aboutir.** C'est alors seulement que la restauration est conservée et que les anciennes données sont supprimées. S'il échoue (migration en échec, fichier endommagé), le démarrage suivant remet seul les anciennes données en place, et `backup pending`, comme la carte dans Paramètres › Administration › Sauvegarde, indique que le retour en arrière a été fait, avec la raison.

### 🔌 Qui redémarre LibreFolio {: #supervisors }

Vous lancez la restauration : avec le redémarrage de la ligne de commande, ou avec **Restaurer et redémarrer** dans Paramètres › Administration › Sauvegarde, qui arrête LibreFolio. Rien dans LibreFolio ne redémarre le serveur : ce qui le supervise le fait, après cet arrêt et après un premier démarrage qui échoue, de sorte que le démarrage suivant remette les données en place.

| Superviseur | Redémarre LibreFolio tout seul |
| --- | --- |
| Docker Compose | Avec `restart: unless-stopped`, dans les deux fichiers compose fournis par LibreFolio |
| systemd | Avec `Restart=always` |
| Aucun | Non : démarrez LibreFolio vous-même, et la restauration, ou le retour en arrière, a lieu à ce démarrage |

**Restaurer et redémarrer** arrête LibreFolio proprement : une politique qui ne redémarre qu'après un échec, comme `on-failure`, ne le démarre pas après cet arrêt.

---

## 🔗 Voir aussi

- 📄 **[Sauvegardes : sauvegardes scellées](backup_sealed.md)** — Sauvegardes scellées : une clé au lieu d'un mot de passe
- 📄 **[Sauvegardes : déplacement et dépannage](backup_moving.md)** — Ramener votre LibreFolio chez vous, quand quelque chose ne va pas
- 🛠️ **[Outils d'administration CLI](cli_tools.md)** — «Sauvegarder l'instance» : chaque option et chaque message de `backup create`, `inspect`, `restore`, `decrypt` et `pending`, et «Sauvegarder avec Docker»
- 📂 **[Structure du système de fichiers](filesystem.md)** — Le répertoire de données, `secrets/` et une copie faite à la main
- 🐳 **[Installation avec Docker](../user/installation.md)** — Installer LibreFolio et le mettre à jour
- 👥 **[Utilisateurs et invitations](users.md)** — Réactiver ou supprimer des comptes et envoyer de nouveaux liens
- 📧 **[E-mail](email.md)** — Les variables e-mail, qu'aucune archive ne contient
- 📝 **[Variables d'environnement](configuration.md)** — «La clé d'instance» et chaque option de `.env`
- 🧑‍💻 Pour les développeurs : **[Restaurer une sauvegarde](../developer/architecture/security.md#backup-restore)** — L'échange, le journal, le retour en arrière et le redémarrage
- 🧑‍💻 Pour les développeurs : **[Sauvegardes sécurisées (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — L'enveloppe, le mot de passe et la clé d'instance qu'emporte une sauvegarde sécurisée
- 🧑‍💻 Pour les développeurs : **[Sauvegardes scellées (`.tar`)](../developer/architecture/security.md#sealed-backups)** — Les trois membres, age via `pyrage` et le lecteur strict
