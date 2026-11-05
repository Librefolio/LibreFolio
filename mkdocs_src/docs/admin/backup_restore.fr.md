# 💾 Sauvegarde, restauration et déplacement de votre instance

Une sauvegarde est une archive contenant l'ensemble de votre LibreFolio : la base de données et les fichiers de chaque utilisateur, dans un zip ordinaire ou, pour une [sauvegarde sécurisée](#secure), chiffrée avec un mot de passe que vous choisissez. Cette page raconte tout : ce que contient l'archive, comment en créer une et la vérifier, comment la protéger par un mot de passe, comment la restaurer, et comment déplacer LibreFolio d'une instance hébergée par quelqu'un pour vous vers votre propre serveur, ou l'inverse. Chaque option et chaque message des commandes se trouvent dans «Sauvegarder l'instance», dans [Outils d'administration CLI](cli_tools.md).

!!! tip "🗓️ Faites-en une avant chaque mise à jour"

    LibreFolio ne ramène jamais une base de données à une version antérieure. Une sauvegarde réalisée avant une mise à jour est votre moyen de revenir à la version que vous aviez : voir [Mettre à jour LibreFolio](../user/installation.md#updating).

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Outre cette page : [Sauvegardes : sauvegardes scellées](backup_sealed.md), [Sauvegardes : déplacement et dépannage](backup_moving.md).

---

## 📦 Ce que contient une sauvegarde {: #contents }

L'archive est un zip qui reprend l'arborescence du [répertoire de données](filesystem.md) : décompressée dans un répertoire de données vide, elle reconstitue votre instance. Une [sauvegarde sécurisée](#secure) est la même archive zip, chiffrée avec un mot de passe dans un fichier `.lfbk`, et une [sauvegarde scellée](backup_sealed.md#sealed) est une sauvegarde sécurisée dont seule une clé privée vous appartenant permet de déchiffrer le mot de passe, dans un fichier `.tar`.

| Dans l'archive | Ce que c'est |
| --- | --- |
| `sqlite/app.db` | La base de données : utilisateurs, courtiers, transactions, actifs, prix, taux de change et paramètres. Une copie cohérente, réalisée pendant que LibreFolio continue de fonctionner |
| `custom-uploads/` | Les fichiers téléversés dans l'application |
| `broker_reports/` | Les rapports de courtiers |
| `scenario_catalog/` | Vos propres scénarios de stress, si vous en avez ajouté |
| `secrets/instance.key` | Uniquement dans une [sauvegarde sécurisée](#secure), et uniquement lorsque LibreFolio a généré la clé d'instance : la clé qui a chiffré les clés enregistrées des fournisseurs de données, afin qu'elles voyagent avec les données. Une restauration ne fait que la lire : l'installation qui reçoit la sauvegarde conserve sa propre clé |
| `manifest.json` | La description de l'archive : la version de LibreFolio qui l'a créée et quand, la révision de migration de la base de données, le nombre de lignes par table, les totaux de contrôle du grand livre (la trésorerie de chaque courtier dans chaque devise et la quantité de chaque position), la taille et la somme de contrôle SHA-256 de chaque fichier, et si l'archive contient la clé d'instance |

Jamais dans l'archive :

- 🔑 `secrets/`, qui contient la clé d'instance : une [sauvegarde sécurisée](#secure) ne transporte que la clé générée par LibreFolio, `secrets/instance.key`, jamais une clé que vous avez définie vous-même avec `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE`. Voir «La clé d'instance» dans [Variables d'environnement](configuration.md) ;
- 📝 `logs/`, et `scheduler_state.json`, la dernière exécution des synchronisations planifiées ;
- 💾 `backups/`, où LibreFolio [conserve les sauvegardes qu'il crée](#kept-backups), et `.restore/`, le dossier de travail d'une restauration ;
- ⚙️ la configuration : `.env` et les variables d'environnement, y compris les paramètres [e-mail](email.md), que LibreFolio conserve uniquement dans l'environnement.

### 🧭 Ce qui suit {: #what-follows }

- 🔒 **Gardez-la privée.** Une archive en clair contient les données de chaque utilisateur et n'est pas chiffrée : gardez-la, ainsi que chaque copie, aussi privée que le serveur lui-même. Une archive [sécurisée](#secure) ne s'ouvre qu'avec son mot de passe : conservez le mot de passe séparément.
- 🗝️ **Secrets enregistrés et clé d'instance.** Ce que LibreFolio a chiffré avec la clé d'instance, comme la clé API d'une source de données enregistrée dans l'application, ne peut être lu qu'avec cette clé.
    - Une [sauvegarde sécurisée](#secure) transporte la clé générée par LibreFolio : sa restauration rechiffre ces secrets avec la clé de l'installation qui la reçoit, et il n'y a rien à faire.
    - Une sauvegarde en clair n'inclut pas la clé ; il en va de même, toujours, pour une sauvegarde [scellée](backup_sealed.md#sealed), ainsi que pour une sauvegarde sécurisée dont la clé provenait de l'environnement (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) ou n'a pas pu être utilisée. Sur une installation dotée d'une autre clé, LibreFolio conserve ces secrets, les signale comme illisibles et n'utilise jamais une valeur erronée : **Paramètres › Plugins** indique sous chacun *Enregistré, mais la clé de cette instance ne peut pas le lire : saisissez-le à nouveau.* Si vous avez encore l'ancienne clé, remettez-la d'abord en place, avant que quiconque ne saisisse à nouveau un secret : arrêtez LibreFolio, remplacez la clé générée par votre copie de `secrets/instance.key`, ou définissez l'ancienne valeur de la variable, puis redémarrez-le («La clé d'instance» dans [Variables d'environnement](configuration.md)). Une installation qui conserve sa propre clé, ou une installation dont les propres secrets sont déjà chiffrés avec sa clé, reprend plutôt l'ancienne clé lors de la restauration : restaurez depuis la ligne de commande avec `--instance-key-file` et votre copie de l'ancienne clé, et la vérification rechiffre ces secrets avec la clé de cette installation («La clé d'instance d'une autre installation» dans [Outils d'administration CLI](cli_tools.md)). Ne saisissez à nouveau les secrets que si l'ancienne clé est perdue : un secret saisi sous la nouvelle clé deviendrait illisible dès que l'ancienne clé sera rétablie.
    - Pour les paramètres de toute l'instance, chaque démarrage journalise aussi l'erreur *Des secrets de plugin enregistrés que la clé d'instance ne peut pas lire : …* avec leur nombre, jusqu'à ce qu'ils soient saisis à nouveau ou que l'ancienne clé soit rétablie. Aucun plugin fourni avec LibreFolio n'en conserve aujourd'hui.
- ⚙️ **Emportez votre configuration.** Conservez une copie de votre `.env` avec les archives : sur une autre installation, redéfinissez les options dont vous avez besoin, y compris celles de l'e-mail ([Où réside la configuration](email.md#where-it-lives)).
- 🏠 **Toute installation peut l'accepter**, si elle exécute la même version de LibreFolio ou une version plus récente, que l'archive ait été créée depuis les Paramètres ou depuis la ligne de commande.

---

## ⬇️ Créer une sauvegarde {: #create }

Trois moyens produisent la même archive :

- **Paramètres › Administration › Sauvegarde**, dans l'application : l'archive est téléchargée sur votre ordinateur. Pour les administrateurs.
- **La ligne de commande**, sur le serveur : `backup create`.

Depuis les Paramètres et depuis la ligne de commande, la sauvegarde peut aussi être [sécurisée](#secure) : le même zip, chiffré avec un mot de passe que vous choisissez. Depuis la ligne de commande, elle peut aussi être [scellée](backup_sealed.md#sealed) : chiffrée avec un mot de passe aléatoire que seule une clé privée vous appartenant permet de déchiffrer, pour les sauvegardes réalisées sans personne au clavier.

Dans tous les cas, LibreFolio continue de fonctionner pendant la sauvegarde, et une seule sauvegarde s'exécute à la fois, quel qu'en soit le déclencheur.

### 🖱️ Depuis Paramètres › Administration › Sauvegarde {: #settings-backup }

1. Ouvrez **Paramètres › Administration › Sauvegarde** : seuls les administrateurs disposent de cet onglet.
2. Dans **Sauvegarder l'instance**, choisissez le type de sauvegarde :
    - **En clair**, le choix proposé par défaut sur la carte : *Un simple .zip : quiconque possède le fichier voit toutes les données, et sur une autre instance, les clés des fournisseurs de données doivent être saisies à nouveau.*
    - **Sécurisée** : *Un .lfbk chiffré avec un mot de passe que vous choisissez : seul ce mot de passe l'ouvre, et un mot de passe perdu ne peut pas être récupéré. Cette sauvegarde transporte aussi les clés des fournisseurs de données.* Voir [Sauvegardes sécurisées](#secure).
3. Pour une sauvegarde sécurisée, saisissez son mot de passe dans **Mot de passe de la sauvegarde**, puis à nouveau dans **Le même mot de passe à nouveau**. Le mot de passe suit les règles données par le serveur, celles d'un mot de passe de compte avec au moins 12 caractères : l'indicateur sous le premier champ les liste au fil de la saisie (*Au moins 12 caractères*, *Une lettre majuscule*, *Une lettre minuscule*, *Un chiffre*, *Un caractère spécial*) et affiche la robustesse du mot de passe. Tant que les deux champs diffèrent, *Les deux mots de passe diffèrent.* s'affiche sous le second, et **Créer une sauvegarde** reste désactivé jusqu'à ce que les deux soient corrects.
4. Cliquez sur **Créer une sauvegarde**. Les champs de mot de passe se vident immédiatement. La carte suit la sauvegarde sur le serveur, phase par phase ; une sauvegarde sécurisée se termine par *Chiffrement avec votre mot de passe*.
5. Lorsqu'elle affiche **Sauvegarde prête**, cliquez sur **Télécharger**. Votre navigateur enregistre l'archive, nommée d'après le moment où la sauvegarde a commencé, en UTC, par exemple `librefolio-backup-20261015-121500.zip`, ou `librefolio-backup-20261015-121500.lfbk` pour une sauvegarde sécurisée, que la carte signale par *Chiffrée avec votre mot de passe : conservez-la en lieu sûr, LibreFolio ne peut pas la récupérer.* Une copie reste sur le serveur, dans la liste des [Sauvegardes conservées sur le serveur](#kept-backups) : vous pourrez aussi la télécharger plus tard depuis cet endroit.

Bon à savoir :

- 🔑 **Conservez le mot de passe d'une sauvegarde sécurisée.** LibreFolio n'en conserve aucune copie, et sans lui personne ne peut ouvrir l'archive, vous compris : conservez-le dans un gestionnaire de mots de passe, séparément de l'archive.
- 💾 L'archive reste sur le serveur jusqu'à ce que vous la supprimiez, ou jusqu'à ce que le [nettoyage automatique](#backup-cleanup) que vous avez configuré la supprime. Une copie sur le même disque que vos données n'est pas une vraie sauvegarde : téléchargez-la et stockez-la ailleurs ([Conserver des copies hors du serveur](#keep-copies)). **Supprimer du serveur** la supprime immédiatement, et **Créer une nouvelle sauvegarde** en lance une autre.
- ⚠️ **La sauvegarde est complète, avec des avertissements** signifie que la base de données n'a pas passé son contrôle d'intégrité ou contient des références rompues, et a été archivée telle quelle, ou que certains fichiers ont été omis, ou, pour une sauvegarde sécurisée, que la clé d'instance n'a pas pu être utilisée et a été omise ([Création d'une sauvegarde sécurisée](backup_moving.md#secure-problems)). L'archive est écrite malgré tout : lisez les avertissements avant de vous y fier.
- 🚦 Pendant qu'une autre sauvegarde s'exécute, lancée depuis l'application ou la ligne de commande, la carte l'indique : réessayez lorsqu'elle se termine. Une sauvegarde lancée depuis cet onglet, ou un autre onglet de l'application, dont la réponse n'est jamais arrivée (la connexion a été interrompue pendant son lancement) n'est pas perdue : le prochain clic sur **Créer une sauvegarde** la trouve en cours d'exécution, la carte la suit, puis propose son téléchargement, comme si elle venait de la lancer. Cela ne vaut que pour une sauvegarde en clair : une sauvegarde sécurisée n'est jamais suivie de cette manière, car seul son propre mot de passe ouvre son archive, et une sauvegarde suivie qui s'avère sécurisée n'est pas proposée, sauf si la carte l'avait lancée elle-même ; dans les deux cas, la carte indique qu'une autre sauvegarde s'exécute. Une carte qui propose déjà une archive continue de la proposer, et indique seulement qu'une autre sauvegarde s'exécute. Une sauvegarde lancée depuis la ligne de commande n'est pas suivie : son archive va ailleurs. La carte n'indique jamais quelle sauvegarde s'exécute ; la console du navigateur le fait (son identifiant et l'endroit où elle a été lancée), si vous avez besoin de la retrouver.

### ⌨️ Depuis la ligne de commande {: #command-line }

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

- 🗃️ Sans `--output`, l'archive reste sur le serveur, dans son propre dossier de `backups/` ([Sauvegardes conservées sur le serveur](#kept-backups)), et la commande affiche son chemin et son `SHA-256:`.
- 📁 `--output` (`-o`) copie l'archive dans un autre dossier qui existe déjà, ou sous un nom de votre choix, et affiche aussi son `SHA-256:` ; rien n'est alors conservé dans `backups/`. Avec Docker, le chemin se trouve à l'intérieur du conteneur : utilisez un dossier monté depuis l'hôte.
- 🔒 Seul le propriétaire de l'archive peut la lire (`0600`) : avec Docker, il s'agit de l'utilisateur du conteneur.
- 🔐 `--encrypt` crée une [sauvegarde sécurisée](#secure), `librefolio-backup-<date>-<time>.lfbk`, et demande son mot de passe deux fois au terminal. Au lieu de le saisir, fournissez-le avec `--password-file FILE`, un fichier qui contient uniquement le mot de passe (les sauts de ligne à sa fin ne comptent pas), comme un secret Docker, ou avec `--password-stdin`, une ligne de l'entrée standard, depuis un tube : dans un terminal, la commande le demande à la place, sans l'afficher, comme sans l'option. L'une ou l'autre rend la sauvegarde sécurisée à elle seule, avec ou sans `--encrypt` ; les deux ne peuvent pas être combinées.
- 🙈 Un mot de passe n'est jamais un argument de la commande : tout utilisateur du serveur peut lire les commandes en cours (`ps`), et le shell les conserve dans son historique. Il n'existe pas d'option `--password`.
- 📏 Le mot de passe suit les règles de Paramètres › Administration › Sauvegarde : au moins 12 caractères, avec une lettre majuscule et une lettre minuscule, un chiffre et un symbole. Un mot de passe qui n'en respecte pas certaines arrête la commande avant toute écriture, avec les règles manquantes : `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Sans terminal, depuis cron ou un script, `--encrypt` seul s'arrête avec `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Chaque option, avertissement et erreur : «Sauvegarder l'instance» et «Sauvegarder avec Docker» dans [Outils d'administration CLI](cli_tools.md).

??? example "🐳 Le mot de passe des sauvegardes comme secret Docker"

    1. Écrivez le mot de passe seul dans un fichier à côté de `docker-compose.yml`, par exemple `backup_password.txt`, jamais dans `LibreFolio-data/` : quiconque aurait les données aurait aussi son mot de passe. Gardez le fichier privé, `chmod 600 backup_password.txt`, et une copie du mot de passe ailleurs : un mot de passe perdu ne peut pas être récupéré.
    2. Ajoutez les lignes marquées à `docker-compose.yml`, et laissez le reste du service tel quel :

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        Si le fichier contient déjà des listes `secrets:`, par exemple pour `JWT_SECRET_FILE` («Secrets dans des fichiers» dans [Variables d'environnement](configuration.md)), ajoutez-y les lignes. Exécutez ensuite `docker compose up -d`, qui recrée le conteneur avec le secret.

    3. Créez la sauvegarde avec le chemin où Docker place le secret dans le conteneur :

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Sauvegardes conservées sur le serveur {: #kept-backups }

Une sauvegarde créée depuis l'application ou la ligne de commande n'est plus supprimée au bout d'une heure : elle reste sur le serveur jusqu'à ce que vous la supprimiez, ou jusqu'à ce que le [nettoyage automatique](#backup-cleanup) la supprime. Chacune possède son propre dossier dans le dossier `backups/` du répertoire de données, nommé d'après le moment où elle a été créée (en UTC), son origine (`ui` pour l'application, `cli` pour la ligne de commande) et un code court qui distingue deux sauvegardes de la même seconde :

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

L'archive à l'intérieur conserve son nom habituel, `.zip`, `.lfbk` ou `.tar`. `backups/.jobs/` ne contient qu'une sauvegarde en cours ou une sauvegarde échouée, qui disparaît au bout d'une heure.

**Paramètres › Administration › Sauvegarde**, sous *Sauvegardes sur ce serveur*, liste chaque sauvegarde conservée. **Fichiers**, dans son onglet **Sauvegardes**, affiche la même liste ; seuls les administrateurs voient l'une ou l'autre. La liste donne, pour chaque sauvegarde :

- 📅 la date et l'heure de sa création, et son origine : l'application ou la ligne de commande ;
- 🔐 son type : en clair ; avec un mot de passe ([sécurisée](#secure)) ; ou [scellée](backup_sealed.md#sealed) ;
- 📏 sa taille, et son SHA-256 : cliquez dessus pour copier la somme de contrôle complète, et comparez-la avec celle du fichier que vous téléchargez ;
- ⬇️ **Télécharger** et 🗑️ **Supprimer**, qui retire la sauvegarde du serveur immédiatement.

!!! warning "💽 Téléchargez-la et stockez-la ailleurs"

    Une sauvegarde qui reste sur le même disque que vos données n'est pas une vraie sauvegarde : lorsque le disque est perdu, les données et leurs sauvegardes disparaissent ensemble. Téléchargez l'archive et conservez-la sur un autre disque, un NAS ou hors site ([Conserver des copies hors du serveur](#keep-copies)).

La liste ne montre que les sauvegardes créées par cette version de LibreFolio. Les fichiers `librefolio-backup-*.zip` isolés que les versions précédentes laissaient dans `backups/` ne sont pas listés et ne sont jamais supprimés par LibreFolio : supprimez-les vous-même lorsque vous n'en avez plus besoin.

### 🧹 Nettoyage automatique {: #backup-cleanup }

Les sauvegardes conservées s'accumulent, et elles résident sur le disque de vos données. Dans la même section **Sauvegardes sur ce serveur** de **Paramètres › Administration › Sauvegarde**, vous définissez deux limites, toutes deux facultatives :

| Limite | Ce qu'elle fait | Désactivée |
| --- | --- | --- |
| Taille totale, en Mo | Lorsque les sauvegardes conservées dépassent ce total, les plus anciennes sont supprimées jusqu'à ce que le reste tienne | `0` |
| Âge maximal, en jours | Une sauvegarde plus ancienne que cette valeur est supprimée | `0` |

- 🛡️ **La dernière sauvegarde est toujours conservée**, quelles que soient les limites : une instance ne se retrouve jamais sans aucune sauvegarde.
- ⏰ Le nettoyage s'exécute après chaque sauvegarde, au démarrage de LibreFolio et environ une fois par heure.
- 🏠 **Auto-hébergé :** les deux limites sont désactivées jusqu'à ce que vous les définissiez.
- 🔍 Seules les sauvegardes de la liste sont nettoyées. Les archives isolées plus anciennes dans `backups/`, une sauvegarde en cours et une sauvegarde échouée ne sont jamais touchées par le nettoyage.
- ⌨️ La ligne de commande laisse ses sauvegardes au même endroit, et les mêmes limites s'y appliquent : voir [Où restent les sauvegardes](cli_backup.md#backup-kept).

### 📊 La barre d'espace disque {: #space-used }

**Fichiers** affiche aux administrateurs une barre, **Espace utilisé**, au-dessus de ses onglets, quel que soit l'onglet ouvert : la place occupée par votre instance. Elle se met à jour lorsque vous cliquez sur **Actualiser** et chaque fois que la liste des sauvegardes conservées change, de sorte qu'une sauvegarde créée ou supprimée s'affiche aussitôt. Sa légende donne la taille de chaque partie :

| Partie | Ce qu'elle compte |
| --- | --- |
| **Base de données** | La base de données et les fichiers qu'elle conserve à côté |
| **Fichiers téléversés** | Les fichiers téléversés dans l'application, comme ceux de la page **Fichiers** |
| **Rapports de courtiers** | Les relevés téléversés pour importer des transactions |
| **Sauvegardes** | Tout ce qui se trouve dans `backups/` : les [sauvegardes conservées sur le serveur](#kept-backups), une sauvegarde en cours et une sauvegarde échouée |
| **Autres fichiers LibreFolio** | Le reste du répertoire de données : journaux, le dossier de travail d'une restauration et autres |

La barre a trois apparences, selon qu'une limite est définie et que le disque est connu :

- 💽 **Aucune limite** (valeur par défaut sur une installation auto-hébergée) : la barre représente tout le disque de vos données. Les parties de LibreFolio sont colorées, **Autre sur le disque** est en gris, et l'espace **Libre** est laissé vide. La ligne sous la barre indique la quantité utilisée par LibreFolio et la taille du disque.
- 📏 **Avec une limite** : la barre représente la limite, et les parties de LibreFolio la remplissent à proportion des données. La ligne sous la barre affiche *utilisé sur la limite*.
- 📁 **Aucune limite et disque inconnu** : LibreFolio ne peut pas interroger le disque, la barre représente donc son propre dossier, réparti en ses parties, sans espace libre.

**Définissez la limite** dans la même barre, dans le champ **Limite d'espace (Mo)** : un nombre entier de mégaoctets, `0` pour aucune limite, puis **Enregistrer**. C'est aussi le [paramètre global](settings.md) *Limite d'espace*, qui n'est pas affiché dans l'onglet Administration : ce champ est l'endroit où le modifier.

- ⚠️ **Au-delà de la limite**, la barre avertit que la limite est dépassée et suggère de supprimer des sauvegardes ou des fichiers, ou d'augmenter la limite. C'est tout : LibreFolio ne supprime rien, et la limite n'empêche ni un téléversement ni une sauvegarde.
- 🔒 **Définie dans la configuration du serveur** : lorsque `LIBREFOLIO_STORAGE_LIMIT_MB` est défini, sa valeur constitue la limite, le champ est grisé et une note indique qu'elle est définie par l'hébergeur de l'instance. Voir [Variables d'environnement](configuration.md). Une valeur que LibreFolio ne peut pas utiliser, qui n'est pas un nombre entier, est ignorée, et le champ fonctionne comme ci-dessus.
- 🧹 **Le nettoyage et la barre fonctionnent ensemble.** Les sauvegardes sont généralement la partie qui grossit : le [nettoyage automatique](#backup-cleanup) les maintient sous contrôle, et chaque sauvegarde que vous supprimez dans **Paramètres › Administration › Sauvegarde** ou dans **Fichiers › Sauvegardes** réduit **Sauvegardes** dans la barre. Lorsque vous approchez de la limite, commencez par là.

### 🗄️ Conserver des copies hors du serveur {: #keep-copies }

`backups/` se trouve dans le répertoire de données, sur le même disque que les données : une sauvegarde conservée là ne survit pas à la perte de ce disque. Une archive téléchargée depuis les Paramètres est déjà hors du serveur. Depuis la ligne de commande, écrivez les archives sur un autre disque, un NAS ou hors site avec `--output`, selon un calendrier.

Une ligne `cron` pour une installation hôte, chaque nuit à 03:30 (`crontab -e`, en tant qu'utilisateur qui exécute LibreFolio) :

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

Avec Docker, ajoutez `-T`, car cron ne donne aucun terminal à la commande. L'archive arrive dans son propre dossier de `LibreFolio-data/backups/`, où le [nettoyage automatique](#backup-cleanup), une fois configuré, empêche le disque de se remplir : copiez-la ailleurs avec votre outil habituel.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

Pour les archives [sécurisées](#secure), ajoutez `--password-file` avec le chemin d'un fichier qui contient le mot de passe, car cron n'a pas de terminal pour le demander ; avec Docker, le secret de l'exemple ci-dessus :

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 Le dossier donné à `--output` doit exister lorsque la commande s'exécute, montez donc d'abord le NAS : un chemin qui n'est pas un dossier existant devient le nom de l'archive elle-même.
- 🔢 La commande affiche ce qu'elle a fait, et se termine avec `1` lorsque l'archive n'est pas à l'endroit demandé : conservez cette sortie, ou faites-en envoyer une copie par courriel par cron.
- 🧭 cron exécute les commandes avec un `PATH` court : s'il ne trouve pas `pipenv` ou `docker`, écrivez le chemin complet, que `command -v pipenv` affiche.
- 🗑️ LibreFolio ne supprime aucune de ces archives : supprimez vous-même les anciennes. Conservez-en plusieurs, et la dernière créée avant chaque mise à jour.
- 🔑 Conservez aussi une copie de `.env`, aussi privée que les archives : aucune archive ne la contient. Conservez également une copie de `secrets/`, sauf si vos archives sont sécurisées : une archive en clair ou [scellée](backup_sealed.md#sealed) omet la clé d'instance, une archive sécurisée transporte la clé générée par LibreFolio.
- 🔏 Pour des archives nocturnes que le serveur lui-même ne peut pas ouvrir, sans fichier de mot de passe sur son disque, voir [Chaque nuit avec cron](backup_sealed.md#sealed-cron), dans Sauvegardes scellées.

### 🧰 Sauvegardes avec restic ou Backrest {: #restic }

LibreFolio écrit l'archive ; un outil de sauvegarde peut ensuite l'envoyer hors site et en conserver un historique. [restic](https://restic.net/) envoie un dossier vers un bucket S3, Backblaze B2, un serveur via SFTP et d'autres emplacements, de manière chiffrée, et oublie les anciennes copies selon une règle que vous lui donnez. [Backrest](https://github.com/garethgeorge/backrest) est une interface web pour restic, avec son propre planificateur. LibreFolio n'a besoin ni de l'un ni de l'autre : ils ne font que lire le dossier dans lequel ses archives sont écrites.

Une recette nocturne pour une installation hôte, avec les variables de restic dans un fichier privé (`chmod 600`) :

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

La ligne crée l'archive, envoie le dossier, conserve sept copies quotidiennes et quatre copies hebdomadaires dans le dépôt, et supprime les archives locales de plus de deux jours. Avec Docker, créez l'archive avec la commande de [Conserver des copies hors du serveur](#keep-copies) et donnez à restic le dossier hôte `LibreFolio-data/backups/`. Avec Backrest, ajoutez un plan sur ce même dossier, avec sa planification et sa rétention, et laissez `backup create` dans cron.

- 🔐 **Le mot de passe de restic est une clé vers toutes vos données.** restic chiffre le dépôt avec lui, mais quiconque le possède lit chaque copie qu'il contient : gardez-le aussi privé que le mot de passe d'une [sauvegarde sécurisée](#secure), et une copie de celui-ci ailleurs. Perdu, le dépôt ne peut plus être lu.
- 🔑 **Pas de clé publique.** restic a besoin de son mot de passe pour écrire comme pour lire, donc le serveur qui envoie les copies peut aussi les lire. Si cela vous importe, envoyez des [sauvegardes scellées](backup_sealed.md#sealed-cron) (`--sealed`) : restic stocke alors des fichiers que seule votre clé privée ouvre, et ni le serveur ni le mot de passe de restic ne les lit. Les [sauvegardes sécurisées](#secure) (`--password-file`) fonctionnent aussi, mais leur mot de passe réside alors dans un fichier sur le même serveur.
- 📦 **Peu à dédupliquer.** Chaque archive est compressée, et une archive sécurisée est chiffrée : deux nuits semblent différentes à restic, qui stocke chaque archive presque entièrement. Prévoyez l'espace du dépôt pour les copies que vous conservez.
- 🧪 **Essayez une restauration avant d'en avoir besoin.** `restic restore latest --target /tmp/librefolio-check`, puis vérifiez l'archive avec [`backup restore --dry-run`](#check).

---

## 🔐 Sauvegardes sécurisées {: #secure }

Une sauvegarde sécurisée est l'archive d'une sauvegarde en clair, chiffrée avec un mot de passe que vous choisissez, dans un fichier propre à LibreFolio : `.lfbk`. Créez-en une depuis [Paramètres › Administration › Sauvegarde](#settings-backup) ou avec `backup create --encrypt` sur la [ligne de commande](#command-line) ; chaque vérification et restauration de cette page l'accepte, une fois son mot de passe fourni.

- 🛡️ **Ce qu'elle protège : le fichier au repos.** Un disque perdu, un ordinateur portable volé, une copie sur un service de cloud ou un NAS : sans le mot de passe, rien ne peut y être lu, ni les données ni les noms des fichiers. Un fichier modifié ou tronqué est détecté à l'ouverture, et refusé.
- 👁️ **Ce qu'elle ne protège pas.** Quiconque connaît le mot de passe lit tout : les données de chaque utilisateur, et les clés des fournisseurs de données. Ne le donnez qu'à ceux qui peuvent restaurer la sauvegarde, et ne le conservez jamais avec le fichier.
- 🗝️ **Ce qu'elle transporte.** Outre les données, la clé d'instance, lorsque LibreFolio l'a générée (`secrets/instance.key`) : les clés enregistrées des fournisseurs de données voyagent avec la sauvegarde, et sa restauration les rechiffre avec la clé de l'installation qui la reçoit, laquelle conserve la sienne. Une clé que vous avez définie vous-même, avec `LIBREFOLIO_INSTANCE_KEY` ou `LIBREFOLIO_INSTANCE_KEY_FILE`, ne sort jamais : celui qui l'a définie la conserve.
- 🆘 **Un mot de passe perdu ne peut pas être récupéré.** LibreFolio n'en conserve aucune copie, et rien d'autre n'ouvre le fichier.
- ⏳ **Lent à deviner.** La clé du fichier est dérivée du mot de passe par scrypt, qui utilise 32 Mio de mémoire et environ un dixième de seconde par essai : rien pour une sauvegarde, assez léger pour un petit serveur, mais lent pour qui essaie les mots de passe les uns après les autres. D'où les règles : au moins 12 caractères, avec une lettre majuscule et une lettre minuscule, un chiffre et un symbole.
- 💽 **Sur le serveur, pendant sa création,** l'archive en clair est écrite d'abord, dans le dossier de travail de la sauvegarde à l'intérieur de `backups/`, que seul l'utilisateur du serveur peut ouvrir ; elle est supprimée dès que le `.lfbk` est écrit, et lorsque la sauvegarde échoue. Une vérification déchiffre la sauvegarde de la même manière, dans un dossier privé du répertoire de données, et supprime l'archive déchiffrée une fois qu'elle l'a utilisée. Une exécution tuée brutalement, par une coupure de courant ou `kill -9`, ne peut pas effectuer le nettoyage : le prochain démarrage de LibreFolio supprime ce qu'elle a laissé en clair, et une sauvegarde interrompue de cette manière doit être refaite. Le dossier d'un `backup inspect` tué de cette manière disparaît au bout d'une heure.

La conception, pour les développeurs : [Sauvegardes sécurisées (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Vérifier une sauvegarde {: #check }

Deux commandes vérifient une archive sans rien modifier. Avec Docker, indiquez le chemin à l'intérieur du conteneur : une archive dans `LibreFolio-data/backups/` se trouve dans `/app/backend/data/prod-docker/backups/` à l'intérieur. Une sauvegarde que LibreFolio [conserve](#kept-backups) se trouve dans son propre dossier, par exemple `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

Sur une installation hôte, exécutez `pipenv run ./dev.py backup …` avec le chemin de l'archive sur l'hôte.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| Elle répond | Si l'archive est intacte : la taille et la somme de contrôle SHA-256 de chaque entrée, comparées au manifeste | Si cette installation peut la restaurer : l'archive décompressée dans une copie, mise à jour et vérifiée |
| Elle affiche | Qui a créé l'archive et quand, la révision de sa base de données, ses lignes et tables, ses fichiers, et si la clé d'instance est incluse | La même chose, plus les migrations qu'une restauration appliquerait, les totaux de contrôle du grand livre de la copie comparés à ceux enregistrés par l'archive, les clés enregistrées des fournisseurs de données rechiffrées avec la clé de cette installation ou à saisir à nouveau, et les administrateurs avec lesquels vous vous connecteriez |
| Elle nécessite | N'importe quel LibreFolio, son serveur en marche ou arrêté : aucun répertoire de données n'est nécessaire, sauf pour une sauvegarde sécurisée, qu'elle y déchiffre | L'installation qui recevrait l'archive, dont le serveur peut continuer de fonctionner, et de l'espace libre dans son répertoire de données : l'archive décompressée, plus deux fois sa base de données, plus 64 Mo |
| Elle se termine par | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Une sauvegarde sécurisée** (`.lfbk`) : les deux commandes demandent d'abord son mot de passe, saisi au terminal ou fourni avec `--password-file FILE` ou `--password-stdin`, comme pour `backup create`. Elles la déchiffrent dans un dossier privé du répertoire de données, que seul l'utilisateur du serveur peut ouvrir, et le suppriment à la fin : le disque doit donc aussi avoir de la place pour l'archive déchiffrée, environ la taille du `.lfbk`. Ce qu'une commande tuée brutalement, par une coupure de courant ou `kill -9`, laisse en clair disparaît au prochain démarrage de LibreFolio : l'archive déchiffrée de `--dry-run` immédiatement, le dossier de `inspect` au bout d'une heure, ce que le prochain `inspect` supprime aussi. Leur rapport ajoute `Secure backup: decrypted with its password`. Un mot de passe erroné les arrête avec `❌ The password does not open this backup (wrong_password)`. Un `.zip` ignore les deux options de mot de passe.
- 🗝️ `--dry-run` indique aussi ce qu'il advient des clés enregistrées des fournisseurs de données, pour toute archive : `Saved provider keys: 2 re-encrypted with this instance's key` lorsque la sauvegarde transporte la clé qui les a chiffrées, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` pour celles qu'elle ne peut pas lire ([Ce qui suit](#what-follows)).
- 🔁 Exécutez `inspect` de temps en temps sur les copies que vous conservez, et `--dry-run` avant un déplacement, sur l'installation qui recevra l'archive.
- 🖱️ **Restaurer une archive**, dans Paramètres › Administration › Sauvegarde, exécute la même vérification que `--dry-run` sur une archive de votre ordinateur : lisez son rapport, puis **Abandonner cette archive**, et rien ne change ([Restaurer depuis Paramètres › Administration › Sauvegarde](#restore-settings)).
- ❌ Un refus se termine par un code entre parenthèses : voir [Quand quelque chose se passe mal](backup_moving.md#troubleshooting). Les listes complètes se trouvent dans «Vérifier une archive» et «Essayer une restauration sur une copie», dans [Outils d'administration CLI](cli_tools.md).

---

## ♻️ Restaurer sur cette installation {: #restore }

Une restauration remplace les données de l'installation par celles de l'archive : la base de données et les fichiers, pour chaque utilisateur. Deux voies y mènent : **Paramètres › Administration › Sauvegarde**, dans l'application, pour les administrateurs, et `backup restore`, sur la ligne de commande du serveur. Les deux vérifient d'abord l'archive sur une copie et ne changent rien avant votre confirmation : le démarrage suivant de LibreFolio l'applique alors. Depuis Paramètres › Administration › Sauvegarde, LibreFolio s'arrête dès que vous confirmez, pour ce démarrage ; sur la ligne de commande, vous le redémarrez quand cela vous convient. Sur une instance hébergée par quelqu'un pour vous, la ligne de commande se trouve sur son serveur : en tant qu'administrateur de cette instance, utilisez Paramètres › Administration › Sauvegarde, ou demandez-lui.

### 🖱️ Restaurer depuis Paramètres › Administration › Sauvegarde {: #restore-settings }

1. **Choisissez l'archive.** Dans **Paramètres › Administration › Sauvegarde**, sous **Sauvegarder l'instance**, la carte **Restaurer une archive** vous rappelle qu'une restauration remplace les données de chaque utilisateur : si vous pourriez vouloir récupérer les données actuelles, [créez d'abord une sauvegarde](#settings-backup). Cliquez sur **Choisir une archive…** et sélectionnez une archive de sauvegarde créée par LibreFolio ici ou sur une autre installation : un `.zip`, ou un `.lfbk` sécurisé. Un `.zip` est envoyé au serveur immédiatement, avec une barre de progression : **Arrêter l'envoi** l'arrête, et rien n'est conservé.
2. **Saisissez son mot de passe**, pour une sauvegarde sécurisée. La carte le demande avant tout envoi : *Une sauvegarde sécurisée : saisissez le mot de passe avec lequel elle a été créée.* Saisissez-le dans **Mot de passe de la sauvegarde** et cliquez sur **Vérifier la sauvegarde** : l'archive est envoyée, avec la même barre de progression, et le mot de passe accompagne la requête qui lance la vérification, laquelle l'essaie aussitôt. Un mot de passe erroné ramène le formulaire, avec *Mot de passe erroné, ou le fichier a été modifié : saisissez à nouveau le mot de passe.* L'archive reste sur le serveur, et la tentative suivante ne l'envoie pas à nouveau. **Annuler** oublie le fichier.
3. **Laissez le serveur la vérifier.** Le serveur vérifie l'archive sur une copie, comme le fait `backup restore --dry-run` ([Vérifier une sauvegarde](#check)) : *Déchiffrement de la sauvegarde*, pour une sauvegarde sécurisée uniquement, *Vérification de l'archive*, *Décompression sur une copie*, *Mise à jour de la base de données de la copie*, *Vérification de la copie*. Rien ne change avant votre confirmation. **Arrêter la vérification** l'abandonne : une vérification encore en cours est abandonnée dès qu'elle se termine.
4. **Lisez le rapport.** Il s'ouvre dans une fenêtre, **Ce que cette restauration ferait** ; une fois fermée, **Lire le rapport** le rouvre. Il donne :
    - qui a créé l'archive, avec quelle version de LibreFolio, et quand ;
    - sa base de données : à la version de ce LibreFolio, ou amenée à celle-ci sur la copie, avec les migrations listées, et les corrections appliquées à la copie ;
    - les fichiers et leur taille, la taille de la base de données, et les tables dont la mise à jour a modifié les lignes ;
    - si la sauvegarde transporte la clé de l'instance dont elle provient : dans tous les cas, ce LibreFolio conserve la sienne ;
    - les clés enregistrées des fournisseurs de données : combien sont rechiffrées avec la clé de ce LibreFolio, par exemple *2 clés enregistrées de fournisseurs de données sont rechiffrées avec la clé de cette instance.*, et combien il ne peut pas lire, à saisir à nouveau après la restauration, par exemple *1 clé enregistrée d'un fournisseur de données ne peut pas être lue avec la clé de cette instance : saisissez-la à nouveau après la restauration.* ([Ce qui suit](#what-follows)) ;
    - les totaux du grand livre : identiques à ceux du moment de la création de la sauvegarde, différents sur les lignes listées ([comment les lire](backup_moving.md#check-refused)), non enregistrés, enregistrés par une autre version de la méthode, ou illisibles ;
    - les administrateurs de la sauvegarde, avec *Après la restauration, vous vous connectez avec l'un d'eux, avec le mot de passe de l'époque ; toute session ouverte maintenant se termine.*
    - *Les invitations et liens envoyés avant la restauration auront expiré : renvoyez-les si nécessaire.*
    - les avertissements, qui laissent la restauration se poursuivre, et l'élément bloquant, qui l'interdit : une sauvegarde sans administrateur actif ;
    - jusqu'à quand la copie vérifiée est conservée : 24 heures après la vérification.

    **Abandonner cette archive** abandonne la vérification et sa copie : rien n'est restauré.

5. **Saisissez le mot.** La fenêtre affiche un mot choisi au hasard, un vrai mot de 6 à 10 lettres dans la langue de l'interface. Saisissez-le à la main dans le champ situé en dessous : le champ refuse le texte collé ou déposé. Le mot protège contre un clic hâtif, pas contre un administrateur : l'API et la ligne de commande s'en passent. Pour une archive qui ne peut pas être restaurée, le champ et le bouton restent désactivés.
6. **Restaurer et redémarrer.** Une fois le mot saisi, **Restaurer et redémarrer** confirme la restauration et arrête LibreFolio immédiatement, pour tout le monde. Une fenêtre recouvre la page, **LibreFolio redémarre** : *Son démarrage applique la restauration. Cette page attend son retour.* LibreFolio ne se redémarre pas lui-même : ce qui le supervise le fait ([Qui redémarre LibreFolio](#supervisors)), et ce démarrage applique la restauration ([Ce que fait le démarrage suivant](#next-start)).

Une fois que LibreFolio répond à nouveau, la page montre comment cela s'est passé :

- ✅ **Cela a fonctionné** : la page va à la page de connexion, sans message, car toutes les sessions ont pris fin. Connectez-vous avec un administrateur de la sauvegarde, avec le mot de passe que le compte avait au moment de la sauvegarde : la première page habituelle affiche les données restaurées. Une restauration réussie ne laisse aucune ligne sur la carte.
- ↩️ **Elle n'a pas abouti** : la fenêtre affiche **La restauration n'a pas abouti**, avec la raison, et **Retour à Sauvegarde** revient à la carte, après la page de connexion si le redémarrage a mis fin à votre session, ou à la page de blocage sur une instance bloquée entre-temps. *Les données sont comme avant : …* signifie que la restauration a été annulée : la carte indique alors quand, et pourquoi. *LibreFolio a redémarré, mais la restauration n'a pas été appliquée.* signifie qu'un démarrage l'a laissée en attente, pour la raison qui suit. Que faire : [Ce qu'affiche Paramètres › Administration › Sauvegarde](backup_moving.md#restore-settings-problems).
- ⏳ **Cela prend du temps** : après une minute sans le serveur, la fenêtre ajoute *LibreFolio n'est pas encore revenu. Si rien ne le redémarre tout seul, redémarrez-le vous-même : la restauration est appliquée à ce démarrage.* Si LibreFolio ne s'arrête pas du tout, après une minute la fenêtre indique *LibreFolio ne s'est pas arrêté. S'il ne redémarre pas tout seul, redémarrez-le vous-même : la restauration est appliquée à ce démarrage.*, et propose **Retour à Sauvegarde** : voir [Ce qu'affiche Paramètres › Administration › Sauvegarde](backup_moving.md#restore-settings-problems).

La page lit le résultat grâce à un ticket à usage unique reçu par sa requête de redémarrage, valable une heure et conservé uniquement dans la mémoire de l'onglet : il ne nécessite aucune session, de sorte que la fenêtre indique le résultat quelle que soit votre configuration. Sans ce ticket, après un rechargement de la page, plus d'une heure d'attente, ou un LibreFolio redémarré depuis la ligne de commande plutôt que depuis cette page, la page se fonde sur sa session : sans `JWT_SECRET`, qui déconnecte tout le monde à chaque démarrage ([Garder les utilisateurs connectés après un redémarrage](index.md#session-persistence)), elle va alors à la page de connexion quel que soit le résultat, et **Paramètres › Administration › Sauvegarde** indique, une fois que vous êtes connecté, si la restauration a abouti.

Une restauration confirmée et pas encore appliquée s'affiche sur la carte à la place de **Choisir une archive…** : une restauration confirmée depuis la ligne de commande, ou ici lorsque LibreFolio ne s'est pas arrêté ou qu'un démarrage l'a laissée en attente. La carte affiche **Une restauration attend le prochain démarrage de LibreFolio**, avec la sauvegarde, qui l'a confirmée (`cli` depuis la ligne de commande) et quand, pourquoi un démarrage l'a laissée en attente le cas échéant, et *Redémarrer arrête LibreFolio pour tout le monde ; son démarrage suivant applique la restauration et met fin à toutes les sessions.*

- **Redémarrer maintenant et restaurer** arrête LibreFolio, comme le fait **Restaurer et redémarrer**, et la page l'attend de la même manière.
- **Annuler la restauration** l'abandonne avec sa copie vérifiée, comme le fait `backup pending --cancel` : les données restent telles quelles.

Pendant qu'un démarrage applique la restauration, la carte affiche *Un démarrage de LibreFolio applique la restauration.*

Bon à savoir :

- 👑 Seuls les administrateurs disposent de l'onglet, et une seule restauration s'exécute à la fois : une seule archive est vérifiée à la fois, où que la vérification ait commencé, ici, dans un autre onglet ou sur la ligne de commande (*Une autre archive est en cours de vérification : réessayez lorsqu'elle se termine.*), et une restauration en attente prend la place de **Choisir une archive…**.
- 📏 Lorsque l'installation limite la taille des archives, la carte l'indique, par exemple *Archives jusqu'à 500 Mo.*, et refuse un fichier plus volumineux avant tout envoi. La limite est `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, en mégaoctets de 1024 × 1024 octets : aucune par défaut sur votre propre installation ([La limite de téléversement d'une restauration](#restore-upload-limit)).
- 💽 Le disque du répertoire de données doit avoir de la place pour l'archive et, pendant sa vérification, pour sa copie, ainsi que, pour une sauvegarde sécurisée, pour son archive déchiffrée : [Vérifier une sauvegarde](#check) indique la quantité nécessaire.
- 🔑 Le mot de passe d'une sauvegarde sécurisée n'est envoyé au serveur qu'avec la requête qui lance la vérification, laquelle l'essaie aussitôt : il n'est jamais stocké, écrit dans le journal ni renvoyé. Le champ se vide dès que vous le soumettez.
- 🔄 Un rechargement de la page, dans le même onglet, continue de suivre la vérification et son rapport. La copie vérifiée est conservée 24 heures : passé ce délai, la confirmation répond *La vérification est trop ancienne : vérifiez à nouveau l'archive.*
- 🚪 La restauration met fin à toutes les sessions, chacun se reconnecte avec un compte de la sauvegarde, et les liens envoyés avant elle cessent de fonctionner : voir [Ce que fait le démarrage suivant](#next-start).
- ❌ Un téléversement, une vérification ou une confirmation refusés, ou un serveur qui ne répond pas, s'affichent sur la carte avec la raison. **Réessayer** relit l'état de la restauration ; pour renvoyer une archive, choisissez-la à nouveau avec **Choisir une archive…**. La vérification refuse les mêmes archives que la ligne de commande : voir [La vérification refuse l'archive](backup_moving.md#check-refused).
- 🖥️ Si rien ne redémarre LibreFolio, comme une installation hôte démarrée à la main, [démarrez le serveur](cli_tools.md#start-the-server) vous-même une fois qu'il s'est arrêté : la page l'attend.

### 📤 La limite de téléversement d'une restauration {: #restore-upload-limit }

Pour vérifier une archive en vue d'une restauration, un administrateur la téléverse sur l'instance depuis
Paramètres › Administration › Sauvegarde
([Restaurer depuis Paramètres › Administration › Sauvegarde](backup_restore.md#restore-settings)), via
`PUT /api/v1/backup/restore/upload` ; l'instance la vérifie ensuite sur une copie, comme le fait
`backup restore --dry-run` sur la [ligne de commande](cli_tools.md). `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` plafonne la taille des
archives qu'un administrateur peut téléverser.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Plus grande archive acceptée |
| --- | --- |
| Non défini, ou vide | Aucune limite |
| `0` | Aucune limite |
| Un nombre entier, par exemple `2048` | Ce nombre de mégaoctets, de 1024 × 1024 octets chacun |

```bash
LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
```

- Définissez-la dans l'environnement du conteneur ou dans `.env`, puis redémarrez LibreFolio.
- Une archive dépassant la limite répond `413`, avec le code `backup_too_large` et la limite dans
  `limit_mb` : avant toute écriture lorsque la requête annonce sa taille, sinon dès que
  le téléversement dépasse la limite. Rien n'en est conservé.
- Un proxy devant LibreFolio doit laisser passer au moins autant : Nginx avec
  `client_max_body_size`, dont la valeur par défaut n'est que de 1 Mo (`client_max_body_size 2048m;` correspond à
  l'exemple ci-dessus), et votre CDN, s'il limite la taille d'une requête. Un `413` sans le
  code `backup_too_large` provient du proxy, pas de LibreFolio.
- Une valeur autre qu'un nombre entier, comme `500MB` ou `-1`, n'arrête pas le serveur : le journal de démarrage
  contient déjà une erreur, `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` est
  `backup.upload_limit`), puis chaque téléversement répond `503` avec le code `backup_upload_unavailable`, et
  le journal contient une erreur qui nomme la variable : `The upload limit of a restore cannot be read`.
- Le disque du répertoire de données doit avoir de la place pour l'archive et, pendant sa vérification, pour sa copie
  décompressée également (quantité : «Essayer une restauration sur une copie» dans [Outils d'administration CLI](cli_tools.md)) : à court de
  place, le téléversement répond `507` avec le code `backup_no_space`, également lorsque le disque ne se déclare
  plein qu'à la fin du fichier, comme peut le faire un système de fichiers réseau ou un quota. La vérification répond avec
  son propre code, `no_space` : un `507` lorsqu'elle ne peut même pas démarrer, un refus de l'archive une fois lancée.
  Un téléversement qui ne peut pas être écrit pour une autre raison répond `500` avec le code
  `backup_upload_failed`, et le journal en contient la cause.
- Un administrateur lit la limite en vigueur dans `upload_limit_mb` de
  `GET /api/v1/backup/restore/status` : `0` pour aucune limite, `null` lorsque la valeur ne peut pas être lue.
  Paramètres › Administration › Sauvegarde l'affiche sur sa carte de restauration, par exemple *Archives jusqu'à 500 Mo.*,
  et refuse un fichier plus volumineux avant de l'envoyer.

La limite de téléversement borne l'archive telle qu'elle est envoyée, compressée : un zip peut se décompresser en bien plus que sa
propre taille, et la vérification le décompresse sur le disque du répertoire de données.
`LIBREFOLIO_BACKUP_MAX_RESTORE_MB` borne la taille décompressée d'une archive, d'après les tailles que son manifeste
déclare, avant que la vérification ne décompresse quoi que ce soit.

| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | Plus grande taille décompressée d'une archive |
| --- | --- |
| Non défini, ou vide | Aucune limite |
| `0` | Aucune limite |
| Un nombre entier, par exemple `16384` | Ce nombre de mégaoctets, de 1024 × 1024 octets chacun |

- Une archive dépassant la limite est refusée avant toute décompression : la vérification échoue avec le code
  `unpacked_too_large`, et rien de sa copie n'est conservé. Une archive sécurisée est d'abord déchiffrée, ce qui
  occupe environ sa propre taille, puis mesurée de la même manière.
- Une valeur que vous définissez l'emporte toujours, `0` compris. `backup restore` sur la ligne de commande suit la même
  limite ; celui qui exploite le serveur la lève pour une commande avec `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0`
  devant elle («Essayer une restauration sur une copie» dans [Outils d'administration CLI](cli_tools.md)).
- Une valeur autre qu'un nombre entier n'arrête pas le serveur : le journal de démarrage contient déjà une erreur,
  `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` est `backup.restore_limit`), puis chaque
  vérification, `POST /api/v1/backup/restore/stage`, répond `503` avec le code
  `backup_restore_unavailable`, l'archive est conservée, et le journal contient une erreur.

### ⌨️ Restaurer depuis la ligne de commande {: #restore-command }

Exécutez-la là où le serveur s'exécute, dans le conteneur avec Docker :

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 L'étape 1 exécute la même vérification que `--dry-run` et affiche le même rapport, puis vous demande de saisir `restore`. Rien ne change encore : LibreFolio continue de fonctionner sur ses données, et la restauration attend le prochain démarrage.
- 🖥️ Sur une installation hôte, exécutez `pipenv run ./dev.py backup restore <archive>`, puis arrêtez tout le serveur et [redémarrez-le](cli_tools.md#start-the-server) : ne redémarrez jamais un seul worker.
- ⏳ Une fois LibreFolio de nouveau opérationnel, `backup pending` indique `✅ The last restore was applied on …`. Avant le redémarrage, `backup pending --cancel` abandonne la restauration en attente, avec sa copie vérifiée.
- 🤖 Dans un script, `--yes` confirme sans demander.
- 🔐 Pour une sauvegarde sécurisée (`.lfbk`), `backup restore` demande son mot de passe avant la vérification, ou le lit avec `--password-file` ou `--password-stdin`, comme le fait `inspect` ([Vérifier une sauvegarde](#check)) : dans un script, fournissez l'un des deux ainsi que `--yes`.
- 📖 Plus d'informations : «Restaurer une archive» et «Suivre ou annuler une restauration» dans [Outils d'administration CLI](cli_tools.md).

### 🔄 Ce que fait le démarrage suivant {: #next-start }

- 🔀 **L'échange.** La base de données et les trois dossiers de fichiers sont échangés avec la copie vérifiée : un renommage par dossier, instantané quelle que soit sa taille. `secrets/`, `logs/`, `scheduler_state.json` et `backups/` restent tels quels, de sorte que l'installation conserve sa propre clé d'instance. La clé qu'une sauvegarde sécurisée transporte n'est jamais mise à sa place : la vérification a déjà rechiffré les clés enregistrées des fournisseurs de données sur la copie, avec la clé de cette installation.
- 🚪 **Toutes les sessions se terminent.** Chacun se reconnecte, sur chaque appareil, avec un compte de la sauvegarde et le mot de passe qu'il avait alors.
- 🔗 **Les liens à usage unique sont révoqués.** Aucun lien d'invitation, de réinitialisation de mot de passe ou de vérification d'e-mail envoyé auparavant ne fonctionne plus, pas même ceux que la sauvegarde contenait : envoyez-en de nouveaux. Un compte encore en attente de sa vérification d'e-mail cesse d'attendre : lorsque son propriétaire demande un nouveau lien à la page de connexion, la page répond que le compte est désactivé. Un administrateur le réactive avec **Réactiver** ([Ce que fait chaque action](users.md#actions)), ou le supprime ([Supprimer un compte](users.md#delete)) afin que son propriétaire s'inscrive à nouveau.
- ✅ **Le premier démarrage doit aboutir.** Ce n'est qu'ensuite que la restauration est entérinée et les anciennes données supprimées. Si ce démarrage échoue, sur une migration qui échoue ou un fichier endommagé, le démarrage suivant remet les anciennes données en place de lui-même, et `backup pending`, comme la carte dans Paramètres › Administration › Sauvegarde, indique que la restauration a été annulée, avec la raison.

### 🔌 Qui redémarre LibreFolio {: #supervisors }

Vous lancez la restauration vous-même : avec le redémarrage de la ligne de commande, ou avec **Restaurer et redémarrer** dans Paramètres › Administration › Sauvegarde, qui arrête LibreFolio. Rien dans LibreFolio ne redémarre le serveur : ce qui le supervise le fait, après cet arrêt, et après un premier démarrage qui échoue, afin que le démarrage suivant ramène les données.

| Superviseur | Redémarre LibreFolio de lui-même |
| --- | --- |
| Docker Compose | Avec `restart: unless-stopped`, dans les deux fichiers compose fournis par LibreFolio |
| systemd | Avec `Restart=always` |
| Aucun | Non : démarrez LibreFolio vous-même, et la restauration, ou le retour en arrière, se produit à ce démarrage |

**Restaurer et redémarrer** arrête LibreFolio proprement : une politique qui ne le redémarre qu'après un échec, comme `on-failure`, ne le redémarre pas après cet arrêt.

---

## 🔗 Voir aussi

- 📄 **[Sauvegardes : sauvegardes scellées](backup_sealed.md)** — Sauvegardes scellées : une clé au lieu d'un mot de passe
- 📄 **[Sauvegardes : déplacement et dépannage](backup_moving.md)** — Ramenez votre LibreFolio chez vous, quand quelque chose se passe mal
- 🛠️ **[Outils d'administration CLI](cli_tools.md)** — «Sauvegarder l'instance» : chaque option et message de `backup create`, `inspect`, `restore`, `decrypt` et `pending`, et «Sauvegarder avec Docker»
- 📂 **[Structure du système de fichiers](filesystem.md)** — Le répertoire de données, `secrets/`, et une copie faite à la main
- 🐳 **[Installation avec Docker](../user/installation.md)** — Installer LibreFolio, et le mettre à jour
- 👥 **[Utilisateurs et invitations](users.md)** — Réactiver ou supprimer des comptes, et envoyer de nouveaux liens
- 📧 **[E-mail](email.md)** — Les variables d'e-mail, qu'aucune archive ne contient
- 📝 **[Variables d'environnement](configuration.md)** — «La clé d'instance», et chaque option de `.env`
- 🧑‍💻 Pour les développeurs : **[Restaurer une sauvegarde](../developer/architecture/security.md#backup-restore)** — L'échange, le journal, l'annulation et le redémarrage
- 🧑‍💻 Pour les développeurs : **[Sauvegardes sécurisées (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — L'enveloppe, le mot de passe et la clé d'instance qu'une sauvegarde sécurisée transporte
- 🧑‍💻 Pour les développeurs : **[Sauvegardes scellées (`.tar`)](../developer/architecture/security.md#sealed-backups)** — Les trois membres, age via `pyrage`, et le lecteur strict
