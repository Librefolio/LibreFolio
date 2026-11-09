# ⚙️ Paramètres globaux

Les paramètres globaux s’appliquent à toute l’instance et à chaque utilisateur. Ils sont stockés dans la base de données.
Seuls les administrateurs disposent de l’onglet pour les voir et les modifier. Ils ne sont pas secrets : l’application les lit pour chaque utilisateur connecté (la limite de téléversement, les valeurs par défaut des [Préférences](../user/settings/preferences.md)…) et tout utilisateur connecté peut les lire via l’API.

Certains ont une variable dans le fichier `.env` qui les fixe ou qui passe en premier : la colonne **Où** de chaque tableau l’indique.

---

## 🗂️ Paramètres › Administration {: #administration }

**Où :** **Paramètres** (icône d’engrenage dans la barre latérale) › **Administration**, à l’extrémité droite de la barre d’onglets sur un écran large. Seuls les administrateurs ont ce groupe.
Cliquez sur **Administration** : cela ouvre **Paramètres globaux** et une deuxième rangée d’onglets sous la première.

| Onglet | À quoi il sert |
|---|---|
| ⚙️ **Paramètres globaux** | Les paramètres de cette page |
| 👥 **Utilisateurs** | Les comptes, les invitations et les liens de réinitialisation du mot de passe : [Utilisateurs et invitations](users.md) |
| 💾 **Sauvegarde** | Toute l’instance dans une archive, et sa restauration : [Sauvegarde, restauration et déplacement](backup_restore.md) |
| ✉️ **E-mail** | Si LibreFolio peut envoyer des e-mails, et un e-mail de test : [E-mail](email.md) |
| 🛡️ **Sécurité** | Comment l’instance est configurée et ce qui demande votre attention : [Sécurité](#security-tab), ci-dessous |

- 👤 Un utilisateur qui n’est pas administrateur n’a ni le groupe ni ses onglets : ses **Paramètres** se terminent par **À propos**, et un lien vers un onglet du groupe ouvre son **Profil**.
- 🔁 Cliquez sur **Administration** alors qu’un de ses onglets est ouvert : cet onglet reste ouvert.
- 🔗 Chaque onglet a sa propre adresse, pour un favori ou un lien : `/settings/admin/global`, `/settings/admin/users`, `/settings/admin/backup`, `/settings/admin/email`, `/settings/admin/security` ; `/settings/admin` ouvre le premier onglet du groupe. L’adresse suit l’onglet ouvert, et **Précédent** ramène à l’onglet d’avant.
- 🔢 Un nombre sur **Sécurité**, répété sur **Administration**, compte les erreurs et les avertissements des [contrôles de sécurité](#security-tab).
- 📱 Sur un téléphone, les onglets n’affichent que leurs icônes ; le titre de la page nomme l’onglet ouvert.

---

## ✏️ Modifier un paramètre

### 🔓 1. Déverrouiller l’onglet

**Où :** **Paramètres › Administration › Paramètres globaux**. Le panneau regroupe les paramètres par catégorie.
Cliquez sur l’**icône de verrou** (🔒) dans l’en-tête.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Paramètres globaux" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Modifier et enregistrer

- Rien n’est écrit tant que vous ne cliquez pas sur **Enregistrer** à côté d’un paramètre ou sur **Tout enregistrer** dans l’en-tête. **Annuler** et **Tout annuler** rétablissent les valeurs enregistrées.
- **Réinitialiser par défaut** et **Tout réinitialiser par défaut** remplissent les valeurs par défaut, prêtes à être enregistrées.
- Les valeurs enregistrées s’appliquent immédiatement, sans redémarrage.

??? note "🔒 Verrouiller avec des modifications non enregistrées — quand une boîte de dialogue demande d’abord"

    Cliquez sur le verrou avec des modifications non enregistrées : une boîte de dialogue demande s’il faut les abandonner. **Annuler** conserve vos modifications ; **Abandonner** rétablit les valeurs enregistrées et verrouille l’onglet.

??? tip "💻 Paramètres manquants — les recréer depuis la ligne de commande"

    Chaque démarrage du serveur recrée les paramètres manquants avec leur valeur par défaut. Pour le faire sans redémarrage, **dans le terminal du serveur**, avec l’[outil en ligne de commande](cli_tools.md) :

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    Les valeurs que vous avez modifiées sont conservées.

---

## 📋 Ce que fait chaque paramètre

**Où :** la catégorie indiquée de l’onglet **Paramètres globaux**.

| Où | Paramètre | Valeur par défaut | Ce qu’il fait — quand le modifier |
|---|---|---|---|
| ⏳ Session | **Durée de session** | 24 heures | Combien de temps les utilisateurs restent connectés. Raccourcissez-la sur des appareils partagés. Une nouvelle valeur s’applique à partir de la prochaine connexion de chaque utilisateur. |
| 🛡️ Sécurité | **Inscription** | Sur invitation | Qui peut créer un compte : **Ouverte**, **Sur invitation** ou **Fermée**. **Ouverte** laisse entrer quiconque atteint la page de connexion : évitez-la si l’instance est joignable depuis Internet. Modes, avertissement et `LIBREFOLIO_REGISTRATION` : [Qui peut s’inscrire](#registration). |
| 🛡️ Sécurité | **Exiger la vérification de l’e-mail** | Désactivé | Les nouveaux comptes doivent ouvrir un lien envoyé à leur adresse avant de pouvoir se connecter ; le premier compte n’attend jamais, et les comptes existants ne sont pas concernés. Il ne peut être activé que lorsque l’e-mail fonctionne et que `LIBREFOLIO_PUBLIC_URL` peut être utilisée : jusque-là, l’interrupteur est grisé. Voir *Vérification de l’e-mail* dans [E-mail](email.md). |
| 🔄 Tâche de mise à jour | **Planificateur activé** | Activé | Active ou désactive les mises à jour automatiques des prix et des taux de change : [Planificateur des données de marché](#market-data-scheduler). |
| 🧠 Mémoire | **Taille maximale de téléversement de fichier** | 10 Mo | Le plus gros fichier que les utilisateurs peuvent téléverser, rapports de courtier inclus. Augmentez-la si un export volumineux est refusé. |
| 🧠 Mémoire | **Espace total de LibreFolio (Mo)** | `0`, aucune limite | Le nombre maximal de mégaoctets que l’instance peut occuper : c’est la ligne par rapport à laquelle la barre d’occupation de l’espace de **Fichiers** est dessinée. `0` signifie aucune limite : la barre affiche alors le disque. Le même champ se trouve sous cette barre, dans **Avancé**. `LIBREFOLIO_STORAGE_LIMIT_MB`, lorsqu’elle est définie, l’emporte et le verrouille : le champ est en lecture seule et indique qu’il est fixé par l’hébergeur de l’instance ([Variables d’environnement](configuration.md)). **Ouvrir les paramètres**, sur un refus de la limite, ouvre cet onglet avec la ligne mise en évidence ; l’onglet reste verrouillé. Voir [La barre d’occupation de l’espace](backup_restore.md#space-used). |
| 🌍 Valeurs par défaut | **Devise par défaut** | `EUR` | La devise dans laquelle les nouveaux utilisateurs déclarent leurs données. Avant le premier enregistrement, `LIBREFOLIO_DEFAULT_CURRENCY` décide (ci-dessous). |
| 🌍 Valeurs par défaut | **Langue par défaut** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` ou 🇪🇸 `es`. C’est aussi la langue des e-mails envoyés aux personnes qui n’ont pas encore de compte. Avant le premier enregistrement, `LIBREFOLIO_DEFAULT_LANGUAGE` décide (ci-dessous). |
| 🌍 Valeurs par défaut | **Thème par défaut** | `auto` | ☀️ `light`, 🌙 `dark` ou 🖥️ `auto`, qui suit l’appareil. S'applique à chaque utilisateur qui n'a pas choisi de thème propre, pas seulement aux nouveaux ; une modification les atteint à leur prochaine connexion. |
| 🌍 Valeurs par défaut | **Forme de ligne des graphiques par défaut** | `segments` | `segments`, `steps` ou `spline` (courbe lissée). S'applique à chaque utilisateur qui n'a pas choisi de forme propre ; une modification les atteint à leur prochain chargement de page. |

**Dans le fichier `.env`**, deux variables décident, si elles sont définies, uniquement jusqu’à ce que vous enregistriez le paramètre pour la première fois : à partir du premier enregistrement, votre valeur l’emporte, même lorsqu’il s’agit de nouveau de la valeur par défaut (`EUR`, `en`). Voir [Variables d’environnement](configuration_accounts.md#accounts).

```env
LIBREFOLIO_DEFAULT_CURRENCY=EUR
LIBREFOLIO_DEFAULT_LANGUAGE=en
```

Les nouveaux utilisateurs partent des trois valeurs par défaut : la [configuration d’accueil](../user/getting-started.md#welcome-setup) affiche leur langue et leur devise préremplies. Modifier une valeur par défaut plus tard ne touche pas aux [Préférences](../user/settings/preferences.md) des utilisateurs existants.

---

## 🚪 Qui peut s’inscrire {: #registration }

**Où :** **Paramètres globaux › Sécurité › Inscription**, ou l’onglet [Utilisateurs](users.md#registration), à côté de **Inviter** : le mode y est enregistré aussitôt, une confirmation n’étant demandée que pour **Ouverte**.

| Mode | Qui peut créer un compte |
|---|---|
| 🌐 **Ouverte** | Quiconque atteint la page de connexion, avec **S’inscrire ici**. |
| ✉️ **Sur invitation** (par défaut) | Uniquement les personnes disposant d’un lien d’invitation. Créez un lien par personne depuis l’onglet [Utilisateurs](users.md#invitations) ou depuis la [ligne de commande](cli_tools.md#invite), puis envoyez-le. La page de connexion n’affiche pas **S’inscrire ici**. |
| 🔒 **Fermée** | Personne, pas même avec un lien d’invitation. La page de connexion n’affiche pas **S’inscrire ici**. |

- 👑 Le premier compte d’une nouvelle instance peut toujours être créé, quel que soit le mode : voir l’avertissement ci-dessous.
- 🆕 Une nouvelle instance démarre en **Sur invitation**. Une instance mise à niveau depuis une version antérieure conserve le mode qu’elle avait : celle qui était **Ouverte**, la valeur par défaut auparavant, reste **Ouverte** jusqu’à ce que vous la changiez (**Réinitialiser par défaut** propose **Sur invitation**). Une fois que tout le monde a un compte, choisissez **Sur invitation** ou **Fermée**.
- ✉️ Un lien d’invitation fonctionne une seule fois, pendant 7 jours, et peut faire du nouveau compte un administrateur. Avec **Ouverte**, personne n’en a besoin, mais un lien confère tout de même son rôle.
- 💻 Quel que soit le mode, la [ligne de commande](cli_tools.md) peut créer des comptes avec `user create`.
- 📏 Avec une limite d’utilisateurs, personne ne peut s’inscrire sans invitation une fois l’instance pleine : [Quand l’instance est pleine](configuration_accounts.md#user-limit).
- 🔒 **Dans le fichier `.env`**, `LIBREFOLIO_REGISTRATION` fixe le mode : le champ l’affiche aux deux endroits, ne peut pas être modifié et indique *Défini sur le serveur par LIBREFOLIO_REGISTRATION : modifiez-le à cet endroit*. **Tout réinitialiser par défaut** ne le touche pas. Voir [Comptes et inscriptions](configuration_accounts.md#accounts).
- ⬆️ Ce paramètre remplace l’interrupteur **Activer l’inscription** des versions antérieures ; la mise à niveau conserve votre choix : un interrupteur activé devient **Ouverte**, un interrupteur désactivé devient **Fermée**.

!!! warning "🆕 Une nouvelle instance : créez d’abord votre compte"

    Tant que le premier compte n’existe pas, quiconque atteint la page de connexion peut le créer avec **S’inscrire ici**, quel que soit le mode, `LIBREFOLIO_REGISTRATION` inclus, et ce compte devient l’administrateur. Inscrivez-vous dès que le serveur est démarré, avant de le rendre joignable depuis Internet. À partir du deuxième compte, le mode s’applique : avec **Sur invitation**, la valeur par défaut, la page de connexion n’affiche plus **S’inscrire ici**.

    Ou créez le premier administrateur **dans le terminal du serveur**, sans navigateur ([ligne de commande](cli_tools.md)) :

    ```bash
    pipenv run ./dev.py user create <username> <email> <password>
    ```

    Avec Docker : `docker compose exec librefolio python dev.py user create <username> <email> <password>`.

    Ou définissez `LIBREFOLIO_ADMIN_EMAIL` **dans le fichier `.env`** avant le premier démarrage : LibreFolio crée lui-même l’administrateur, avec un lien de configuration pour vous, et personne ne peut s’inscrire à sa place ([L’administrateur initial](configuration_accounts.md#initial-admin)).

### 📢 L’avertissement d’inscription ouverte {: #open-registration-warning }

Tant que l’**Inscription** est **Ouverte**, un administrateur qui ouvre LibreFolio à une adresse hors du réseau local lit, au-dessus des pages de l’application :

*L’inscription est ouverte et cette instance est joignable depuis l’extérieur de votre réseau local : quiconque la trouve peut créer un compte.*

Son lien, **Modifier qui peut s’inscrire**, ouvre **Paramètres › Administration › Paramètres globaux**. Lorsque `LIBREFOLIO_REGISTRATION` fixe le mode, l’avertissement nomme cette variable à la place et n’a pas de lien : seule la configuration du serveur (fichier `.env`) peut le changer ([Comptes et inscriptions](configuration_accounts.md#accounts)).

- 👑 Seuls les administrateurs le voient.
- 🌐 Votre navigateur décide, à partir du nom ou de l’adresse IP dans sa barre d’adresse (le port n’a pas d’importance). Rien n’est envoyé au serveur, et rien ne vérifie si l’instance est réellement joignable depuis Internet. Ces adresses comptent comme locales, sans avertissement :
    - `localhost`, et tout nom se terminant par `.localhost` ;
    - un nom sans point, tel que `nas`, et tout nom se terminant par `.local`, `.lan`, `.home.arpa` ou `.internal` ;
    - les adresses IPv4 de `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` et `100.64.0.0/10` (NAT de niveau opérateur, la plage où Tailscale numérote ses appareils) ;
    - l’adresse IPv6 `::1`, et celles de `fc00::/7` et `fe80::/10` ; une adresse IPv4 écrite en IPv6, telle que `::ffff:192.168.1.10`, compte comme l’adresse IPv4 qu’elle transporte.

    Les majuscules et un point final ne changent rien. Toute autre adresse compte comme extérieure, y compris les noms Tailscale se terminant par `.ts.net` : Tailscale Funnel peut les publier sur Internet.
- ✖️ Le bouton de fermeture le masque jusqu’au prochain chargement de la page.
- 🔄 Il disparaît dès que le mode n’est plus **Ouverte** : enregistrer l’**Inscription** le met à jour aussitôt.
- 🛡️ L’onglet [Sécurité](#security-tab) liste le même avertissement parmi ses constats, tant qu’il subsiste, même après que vous l’avez fermé.

Comment il décide, pour les développeurs : [L’avertissement d’inscription ouverte](../developer/architecture/security.md#open-registration-warning).

---

## 🕐 Planificateur des données de marché {: #market-data-scheduler }

Le planificateur met à jour les prix et les taux de change tout seul, même lorsque personne n’est connecté :

- 💰 **Rafraîchissement du prix actuel** — toutes les quelques minutes, le dernier prix de chaque actif actif disposant d’un fournisseur de prix.
- 📊 **Synchronisation de l’historique** — aux jours et heures que vous choisissez, les prix quotidiens de ces actifs et les taux de chaque paire FX disposant d’un fournisseur, sur au moins l’**horizon de rétrospection**, pour combler les lacunes. Si le dernier prix ou taux enregistré est plus ancien, elle remonte jusqu’à ce jour, dans la limite d’un an ; un actif sans aucun prix enregistré ne reçoit que l’horizon : le planificateur ne télécharge jamais tout un historique. Les paires avec uniquement des taux manuels sont ignorées.

Serveur éteint ou en veille à l’heure de la synchronisation : la synchronisation manquée s’exécute dès que le serveur est de retour, sans attendre l’heure suivante. Un serveur éteint pendant des semaines comble toute sa lacune.

### ⚙️ Configurer la planification

**Où :** **Paramètres globaux › Tâche de mise à jour › Configuration de la planification › Configurer…**, avec l’onglet déverrouillé. La boîte de dialogue possède son propre bouton **Enregistrer**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale de configuration du planificateur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Champ | Valeur par défaut | Ce qu’il définit |
|---|---|---|
| **Fuseau horaire** | `UTC` | Le fuseau horaire des heures et des jours ci-dessous ; l’horloge UTC du serveur est affichée à côté. Avant le premier enregistrement de la planification, `LIBREFOLIO_DEFAULT_TIMEZONE` **dans le fichier `.env`** décide, si elle est définie ; à partir du premier enregistrement, votre valeur l’emporte, même lorsqu’il s’agit de nouveau de `UTC` ([Variables d’environnement](configuration_accounts.md#accounts)). |
| **Rafraîchir toutes les** | 10 minutes | Fréquence de rafraîchissement des prix actuels, de 1 à 1440 minutes. |
| **Heures de synchronisation** | `06:00`, `23:00` | Quand la synchronisation de l’historique s’exécute ; **Ajouter une heure** ajoute un créneau. |
| **Jours de synchronisation** | Lun. à Sam. | Les jours de la synchronisation de l’historique. |
| **Horizon de rétrospection** | 14 jours | Combien de jours passés chaque synchronisation vérifie au minimum, de 1 à 365. Elle remonte plus loin, dans la limite d’un an, lorsque le dernier prix ou taux enregistré est plus ancien. |

Conservez au moins une heure et un jour. Une synchronisation après la clôture des marchés (par exemple `22:00`) obtient les données les plus complètes.

??? warning "🌍 Changer le fuseau horaire — les tâches se déplacent dans le temps"

    Les heures et les jours conservent leurs valeurs mais sont comptés dans le nouveau fuseau horaire : les tâches s’exécutent à un autre moment. Elles suivent aussi l’heure d’été du fuseau : `06:00` dans `Europe/Rome` s’exécute à 05:00 UTC en hiver et à 04:00 UTC en été.

### 📜 Lire le journal du planificateur

**Où :** **Paramètres globaux › Tâche de mise à jour › État du planificateur**. Seuls les administrateurs peuvent lire l’état et le journal.

La ligne affiche le dernier rafraîchissement du prix actuel, avec un point pour son résultat. Tant qu’une nouvelle tentative est en attente, une ligne supplémentaire en donne l’heure : **Échec : prochaine tentative à …** après un rafraîchissement qui n’a pas pu se terminer, sinon **Éléments en pause réessayés à …** pour les prix différés parce que leur fournisseur était en pause.
Cliquez sur la ligne (ou sur **Détails…**) : le **Journal d’exécution du planificateur** s’ouvre.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale du journal du planificateur" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Chaque entrée correspond à une exécution : tâche, heure, durée et nombre d’éléments réussis. 🟢 **OK** : tous, ou rien à faire ; 🟡 **Partiel** : certains ont échoué, ou ont été différés parce que leur fournisseur s’est mis en pause après trop de requêtes ; 🔴 **Erreur** : aucun n’a réussi et aucun n’a été différé.
- Cliquez sur une entrée : chaque actif ou paire FX, son fournisseur et les prix modifiés (**Delta**). Survolez une erreur pour la lire en entier ; double-cliquez dessus (appui long sur un téléphone) pour la copier.
- Un élément différé affiche une icône de pause et **Différé : fournisseur en pause** : survolez le libellé pour lire le message du fournisseur. L’entrée compte les éléments différés avec ⏸, à côté de ✓ et ✗ (par exemple `3/5 ✓ · 1 ⏸ · 1 ✗`), et **Nouvelle tentative à** dans l’en-tête donne l’heure de la nouvelle tentative.
- Filtrez par tâche, état ou période, de la dernière heure aux 30 derniers jours. Seules les exécutions les plus récentes sont conservées.

---

## ⏸️ Pauses des fournisseurs {: #provider-pauses }

Lorsqu’un fournisseur de prix ou de taux (Yahoo Finance, la Banque centrale européenne…) répond « trop de requêtes » (HTTP 429), LibreFolio le met en pause : jusqu’à la fin de la pause, aucune requête ne l’atteint, ni du [planificateur des données de marché](settings.md#market-data-scheduler) ni d’un utilisateur. Une pause s’applique à tous les utilisateurs et à toutes les tâches du serveur.

Les pauses sont activées par défaut. `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0` les désactive, comme avant la version 1.3.

**Où :** **dans le fichier `.env`** (ou dans l’environnement du conteneur). Voici les valeurs par défaut :

```env
LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=60
LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS=3600
```

| Variable | Valeur par défaut | Ce qu’elle fait |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La première pause, en secondes, doublée à chaque refus consécutif : un nombre entier de `0` à `86400` (un jour). `0` désactive les pauses. |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pause la plus longue atteinte par le doublement, en secondes : un nombre entier de `1` à `86400`, et pas inférieur à la première pause tant que les pauses sont activées. Le `Retry-After` d’un fournisseur peut encore demander davantage, jusqu’à un jour. |

Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.

- Une valeur que LibreFolio ne peut pas utiliser n’arrête pas le serveur : le journal contient une erreur ([Dans le journal](#provider-pauses-log)) et les deux valeurs par défaut s’appliquent, 60 et 3600 : les pauses restent activées.
- Lorsque les pauses sont désactivées, chaque requête est de nouveau adressée au fournisseur ; le planificateur compte toujours une requête refusée comme différée ([ci-dessous](#provider-pauses-effects)).

### ⏱️ Combien de temps dure une pause {: #provider-pauses-length }

- **Le premier refus** met le fournisseur en pause pendant `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, 60 secondes par défaut.
- **Chaque refus consécutif** double la pause, jusqu’à `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`. Avec les valeurs par défaut : 2 minutes, puis 4, 8, 16 et 32, puis une heure à chaque nouveau refus. Les requêtes refusées ensemble comptent comme un seul refus.
- **Un `Retry-After`**, lorsque le fournisseur en envoie un, est la pause la plus courte que LibreFolio applique : il est respecté même au-delà de la pause la plus longue, jusqu’à un jour.
- **Un supplément aléatoire** allant jusqu’à 10 % est ajouté à chaque pause, sans jamais dépasser un jour.
- **Lorsqu’une pause se termine**, une requête passe pour tester le fournisseur ; les autres comptent toujours comme en pause jusqu’à ce qu’elle ait un résultat, une minute au plus. Une réponse met fin à la série : le refus suivant repart de la première pause. Il en va de même pour un refus qui survient, depuis la fin de la pause précédente, après un intervalle plus long que la pause la plus longue.
- **Une pause s’applique à tout le fournisseur**, sauf avec le CSS Scraper : un site qui refuse ne met en pause que les pages de ce site ; les autres sites sont toujours lus.

### 👀 Qui attend, et ce que vous voyez {: #provider-pauses-effects }

| Où | Pendant une pause |
| --- | --- |
| 🕐 [Planificateur des données de marché](settings.md#market-data-scheduler) | Les actifs et paires FX d’un fournisseur en pause sont **différés** : ni mis à jour ni en échec, et leur tâche est **Partielle**. La tâche s’exécute de nouveau lorsque la première de ces pauses se termine, ou à son heure habituelle si celle-ci arrive avant. Comment **État du planificateur** et **Journal d’exécution du planificateur** l’affichent : « Lire le journal du planificateur », ci-dessus. |
| 💰 Prix live, dans la liste des actifs et sur la page d’un actif | Le dernier prix stocké reste, sans nouveau message. Lorsque tous les actifs interrogés par la page ont leur fournisseur en pause, la page ne se réinterroge d’elle-même qu’une fois la première de ces pauses terminée ; tant qu’un fournisseur répond encore, le rafraîchissement continue et LibreFolio n’appelle pas ceux qui sont en pause. Après un rafraîchissement qui échoue, le suivant attend deux fois plus longtemps, et ainsi de suite jusqu’à dix minutes, jusqu’à ce que l’un fonctionne de nouveau. |
| 🔌 **Tester la configuration**, dans la boîte de dialogue de l’actif | ⚠️ *En pause pour trop de requêtes jusqu’à …*, avec l’heure de fin de la pause ; le test réussit quand même. Voir [Connecter un fournisseur de prix](../user/assets/create-edit.md). |
| 🔎 Recherche d’actifs | Un fournisseur en pause ne donne aucun résultat jusqu’à la fin de sa pause ; les autres répondent comme d’habitude. |
| 💱 Taux de change | Un fournisseur en pause compte comme une route qui a échoué : une paire disposant d’une autre route y obtient son taux, comme lorsqu’une banque centrale ne répond pas ([Configuration du fournisseur](../user/fx/detail/provider.md)). Sinon, le planificateur diffère la paire, comme il le fait pour un actif. |

### 💤 En mémoire {: #provider-pauses-memory }

- **Chaque processus serveur conserve ses pauses en mémoire.** Un redémarrage les oublie, un déploiement inclus. Avec plusieurs processus serveur (`--workers N`), chacun apprend une pause à partir d’un refus qui lui est propre ; l’image Docker en exécute un.

### 📋 Dans le journal {: #provider-pauses-log }

| Niveau | Le journal indique | Quand |
| --- | --- | --- |
| ⚠️ `warning` | `Provider refused for too many requests: paused`, avec `domain` (`asset` ou `fx`), `provider`, `scope` (le site, avec le CSS Scraper), `wait_s`, les secondes de pause à venir, et `retry_after`, l’attente demandée par le fournisseur, le cas échéant | Un fournisseur a refusé une requête |
| ℹ️ `info` | `Provider answering again after a pause`, avec `refusals`, les refus consécutifs avant cela | La première réponse après une pause |
| ❌ `error` | `Provider pause settings cannot be used: the defaults apply`, avec `variable`, `code` (`PROVIDER_COOLDOWN_BASE_INVALID` ou `PROVIDER_COOLDOWN_MAX_INVALID`) et `reason` | L’une des deux variables a une valeur inutilisable : une fois par processus serveur, la première fois que LibreFolio s’apprête à appeler un fournisseur |

Au niveau `DEBUG`, `Provider call skipped: paused after too many requests`, avec `wait_s`, marque chaque requête qu’une pause a empêchée d’être envoyée. Les lignes du planificateur, `Scheduler: current-price refresh` et `Scheduler: history sync`, donnent les éléments différés dans `deferred`, avec `retry_at`.

---

## 🗄️ Caches du serveur {: #server-caches }

LibreFolio conserve en mémoire les réponses récentes des fournisseurs et les résultats calculés.

**Où :** **Paramètres globaux › Mémoire › État du cache**, à la fin de la catégorie. Le panneau liste chaque cache avec sa **Taille / Max** et sa **TTL** (durée de conservation d’une entrée). Cliquez sur un en-tête de colonne pour trier ; **Rafraîchir** met à jour les chiffres.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Panneau des caches du serveur dans les Paramètres globaux (catégorie Mémoire)">
</div>

Le panneau affiche ses chiffres, que l’onglet soit verrouillé ou non. Une fois l’onglet déverrouillé, **Vider** vide un cache et **Tout vider** tous les caches, pour forcer des données fraîches sans redémarrage. Un redémarrage vide aussi tous les caches.

!!! warning "Vider un cache ralentit la récupération suivante"

    Les deux actions demandent d’abord une confirmation. Après un vidage, la prochaine requête pour ces données repart vers les fournisseurs : attendez-vous à un ralentissement semblable à un redémarrage du serveur, le temps que les caches se remplissent à nouveau.

??? note "🧵 Plusieurs workers — lorsque le serveur s’exécute avec `--workers`"

    Chaque processus worker possède ses propres caches. Le panneau affiche et vide ceux du worker qui a répondu ; redémarrez le serveur pour les vider tous.

---

## 🛡️ Sécurité {: #security-tab }

**Où :** **Paramètres › Administration › Sécurité**. Seuls les administrateurs ont cet onglet. Il vérifie comment l’instance est configurée et liste d’abord ce qui demande votre attention.
Il ne s’agit pas de la catégorie 🛡️ **Sécurité** des Paramètres globaux, qui contient **Inscription** et **Exiger la vérification de l’e-mail**.

### 🚦 Ce qu’il liste {: #security-findings }

Chaque constat indique ce qui ne va pas, avec une icône et une couleur : ❌ une **erreur**, ⚠️ un **avertissement** ou ℹ️ une **information**. Les erreurs viennent d’abord, puis les avertissements, puis les informations ; à gravité égale, l’ordre de ce tableau.

| Contrôle | Un constat lorsque | Son lien |
|---|---|---|
| Clé de signature de session | ℹ️ La clé est aléatoire : chaque redémarrage déconnecte tout le monde ; définissez `JWT_SECRET` pour rester connecté. ⚠️ La clé fait moins de 32 caractères. ❌ Son `JWT_SECRET_FILE` ne peut pas être lu | — |
| Secrets définis deux fois | ⚠️ Un secret est défini à la fois directement et via sa variable `_FILE` : la valeur directe l’emporte | — |
| Clé de l’instance | ❌ Elle ne peut pas être utilisée. ⚠️ Son dossier ou son fichier est accessible à d’autres utilisateurs | — |
| Cookie de session | ⚠️ `SESSION_COOKIE_SECURE=never` : le cookie circule aussi en HTTP simple | — |
| Adresse du visiteur | ⚠️ Depuis le démarrage, des requêtes sont passées par un proxy inverse auquel LibreFolio ne fait pas confiance : les limites par adresse de visiteur ne s’y appliquent pas. ℹ️ Depuis le démarrage, des en-têtes de transfert provenant d’une adresse publique ont été ignorés. Que faire : [L’adresse du visiteur](connection_proxy.md#client-address) | — |
| Niveau de journalisation | ℹ️ `DEBUG` ou `TRACE` | — |
| Mode test | ❌ `LIBREFOLIO_TEST_MODE` est activé en dehors des propres exécutions de test de LibreFolio : des fournisseurs de données qui n’existent que pour les tests sont servis et les données sont conservées dans le dossier de données de test | — |
| Limite de téléversement d’une restauration | ❌ `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` ne peut pas être utilisée (un nombre entier de mégaoctets, `0` pour aucune limite) : les téléversements de restauration sont refusés jusqu’à ce qu’elle soit corrigée. Réussit avec une limite, par exemple *Une restauration accepte des archives allant jusqu’à 500 Mo.*, ou sans limite | — |
| Taille décompressée d’une restauration | ❌ `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` ne peut pas être utilisée (un nombre entier de mégaoctets, `0` pour aucune limite) : les contrôles de restauration sont refusés jusqu’à ce qu’elle soit corrigée. Réussit avec une limite, par exemple *Un contrôle de restauration accepte des archives dont la taille décompressée atteint 4000 Mo.*, ou sans limite | — |
| Connexions échouées | ⚠️ La limite est désactivée : `LIBREFOLIO_LOGIN_LIMIT=off` | — |
| Serveur d’e-mail | ❌ Une valeur `LIBREFOLIO_SMTP_*` ne peut pas être utilisée : l’e-mail reste désactivé jusqu’à ce qu’elle soit corrigée | **Ouvrir l’onglet E-mail** |
| Chiffrement des e-mails | ⚠️ Les e-mails, leurs liens et le mot de passe SMTP circulent non chiffrés vers un serveur hors de votre réseau local | **Ouvrir l’onglet E-mail** |
| Liens dans les e-mails | ℹ️ L’e-mail fonctionne, mais `LIBREFOLIO_PUBLIC_URL` n’est pas définie. ⚠️ `LIBREFOLIO_PUBLIC_URL` ne peut pas servir au début d’un lien | **Ouvrir l’onglet E-mail** |
| Secrets des plugins | ❌ Les secrets de plugins à l’échelle de l’instance ne peuvent pas être lus avec la clé de l’instance | **Ouvrir les paramètres des plugins**, dans **Paramètres › Plugins** |
| Inscription ouverte, vérifiée par votre navigateur | ⚠️ L’**Inscription** est **Ouverte** et vous avez atteint LibreFolio à une adresse hors de votre réseau local, comme pour [l’avertissement au-dessus des pages](#open-registration-warning) | **Modifier qui peut s’inscrire**, dans **Paramètres globaux**. Aucun lorsque `LIBREFOLIO_REGISTRATION` fixe le mode : le constat nomme cette variable à la place |
| Un script bloqué, vérifié par votre navigateur | ⚠️ Un script que LibreFolio n’a pas envoyé, ajouté par un proxy, un CDN ou une extension de navigateur, a été bloqué dans cet onglet du navigateur : le constat nomme ses sources. Il disparaît lorsque vous fermez l’onglet. À corriger non pas sur le serveur, mais dans le proxy, le CDN ou l’extension : [Un script que vous n’avez pas envoyé](configuration_security.md#csp-blocked-script) | — |

Chaque ligne possède un bouton d’aide, choisi selon qui peut résoudre le contrôle :

- 📖 **Guide** : vous pouvez le résoudre vous-même, sur le serveur. Le bouton, affiché aussi sur les contrôles réussis, ouvre la page de ce guide qui explique ce contrôle, dans un nouvel onglet et dans votre langue lorsqu’elle est traduite.

Un contrôle qui n’a ni page dédiée ni support n’a pas de bouton.

Les constats sans lien se corrigent dans la configuration du serveur (**fichier `.env`**) et nécessitent un redémarrage : ce qu’il faut faire pour chacun se trouve dans le tableau des « Contrôles au démarrage » dans [Configuration](configuration.md), où le journal du serveur rapporte les mêmes contrôles.

### 🔢 Le nombre sur l’onglet {: #security-badge }

**Sécurité** affiche le nombre d’erreurs et d’avertissements qu’il liste ; **Administration** affiche le même nombre, visible depuis chaque onglet des Paramètres. Les informations sont listées mais jamais comptées : avec des informations uniquement, il n’y a pas de nombre, et l’onglet n’indique pas non plus *Rien ne requiert votre attention.*

En dehors des Paramètres, le même décompte vous suit sur chaque page, sous la forme d’un point sur la ligne de connexion en bas de la barre latérale : rouge avec au moins une erreur, ambre avec seulement des avertissements, aucun avec seulement des informations. Cliquez sur la ligne : après sa raison, les détails renvoient vers cet onglet avec le décompte, par exemple **2 avertissements de sécurité**, erreurs comprises. Sur un téléphone, le bouton de menu porte aussi le point. À quoi cela ressemble : [Avertissements de sécurité pour les administrateurs](../user/connection-security.md#security-warnings).

### 🔄 Quand il effectue les contrôles {: #security-refresh }

LibreFolio lit les contrôles une fois, dès qu’il s’ouvre dans votre navigateur, quelle que soit la page : la ligne de connexion de la barre latérale les demande, de sorte que le point et le nombre sur l’onglet sont déjà là lorsque vous ouvrez **Paramètres**. Si cette lecture échoue, ouvrir **Paramètres** réessaie. Les contrôles restent les mêmes pendant que vous utilisez l’application : après avoir modifié la configuration du serveur (fichier `.env`) et l’avoir redémarré, cliquez sur **Vérifier à nouveau**, en haut de l’onglet, ou rechargez la page. Le constat d’inscription ouverte suit immédiatement l’**Inscription** : l’enregistrer dans les Paramètres globaux met à jour la liste, le nombre et le point.

- ⏳ Jusqu’à la première réponse, l’onglet affiche des lignes de remplacement.
- ⚠️ Lorsque les contrôles ne peuvent pas être lus, l’onglet indique *Les contrôles de sécurité n’ont pas pu être chargés.*, avec **Réessayer**. Après un **Vérifier à nouveau** qui échoue, les derniers résultats restent listés en dessous.

### ✅ Contrôles réussis {: #security-passed }

Sans aucun constat, l’onglet indique *Rien ne requiert votre attention.* Sous les constats, une section repliée, **N contrôles réussis**, liste les contrôles qui ont réussi, chacun avec sa propre phrase (par exemple *Les sessions sont signées avec une clé définie par l’administrateur.*) : cliquez dessus pour la déplier. Un e-mail désactivé, ou envoyé non chiffré à un serveur de votre propre réseau, compte comme réussi et l’indique à cet endroit.

---

## 🔗 Voir aussi

- 📝 **[Variables d’environnement](configuration.md)** — Les paramètres qui résident plutôt dans le fichier `.env`
- 👥 **[Utilisateurs et invitations](users.md)** — Les comptes de l’instance, les invitations et les liens de réinitialisation du mot de passe
- 👤 **[Préférences utilisateur](../user/settings/preferences.md)** — Ce que chaque utilisateur peut modifier pour lui-même
- 🧑‍💻 Pour les développeurs : **[Système de paramètres](../developer/architecture/settings.md)**,
  **[Registre des caches](../developer/architecture/settings_cache.md)**,
  **[Planificateur des données de marché](../developer/backend/scheduler.md)** et
  **[Contrôles de configuration](../developer/architecture/security.md#configuration-checks)**
