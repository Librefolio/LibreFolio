# 📧 E-mail

LibreFolio envoie des e-mails via un serveur SMTP que vous indiquez dans quelques variables d'environnement.
L'e-mail est **facultatif** : sans lui, rien ne change, rien n'est envoyé, et les liens d'invitation et de
réinitialisation de mot de passe sont copiés à la main.

Ce que LibreFolio envoie :

- **Un e-mail de test**, qu'un administrateur envoie à sa propre adresse depuis
  **Paramètres › Administration › E-mail**.
- **Les liens d'invitation et de réinitialisation de mot de passe créés par un administrateur**, avec **Envoyer par e-mail** dans
  leurs boîtes de dialogue : [Liens envoyés par un administrateur](email_flows.md#admin-links).
- **Un lien de réinitialisation pour un mot de passe oublié**, à toute personne qui en demande un depuis la page de
  connexion : [Mots de passe oubliés](email_flows.md#forgot-password).
- **Le lien de configuration de l'administrateur initial**, une seule fois, lorsque LibreFolio crée cet administrateur
  à partir de `LIBREFOLIO_ADMIN_EMAIL` et génère le lien lui-même : [L'administrateur initial](configuration_accounts.md#initial-admin).
- **Un lien pour confirmer l'adresse e-mail d'un nouveau compte**, lorsque **Vérification Email Requise** est
  activée : [Vérification de l'adresse e-mail](email_flows.md#verification).
- **Un message à l'ancienne adresse** lorsqu'une personne modifie l'adresse e-mail de son compte :
  [Changements d'adresse e-mail](email_flows.md#email-change-notice).

Les e-mails contenant un lien ont aussi besoin de `LIBREFOLIO_PUBLIC_URL` : [E-mails avec un lien](email_flows.md#public-url).

Pour configurer l'e-mail :

1. **Dans le `.env` de LibreFolio**, section `# Email` : écrivez les variables `LIBREFOLIO_SMTP_*`, au moins le serveur et
   l'expéditeur, ainsi que l'identifiant de connexion lorsque le serveur en demande un. Copiez l'[exemple](#examples) de votre cas.
2. **Dans le même `.env`**, pour les e-mails contenant un lien : `LIBREFOLIO_PUBLIC_URL` ([E-mails avec un lien](email_flows.md#public-url)).
3. **Depuis un terminal** : redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.
4. **Dans LibreFolio**, **Paramètres › Administration › E-mail** : l'état indique **Prêt**. Envoyez-vous
   un [e-mail de test](#test-email).

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Cette page explique la configuration de l'e-mail : les variables, des exemples pour les serveurs usuels, l'onglet **E-mail** des Paramètres et son e-mail de test. Le reste du guide :

    - [E-mail : liens et messages](email_flows.md) : les e-mails contenant un lien, les mots de passe oubliés, leurs limites, la vérification de l'adresse e-mail et le message de changement d'adresse.
    - [E-mail : quand cela ne fonctionne pas](email_troubleshooting.md) : les erreurs, ce que dit le journal et les notes de sécurité de la configuration SMTP.

---

## 🔐 Où se trouve la configuration {: #where-it-lives }

**Uniquement dans des variables d'environnement**, écrites dans `.env` comme les autres [options](configuration.md) : `./dev.py` et
Docker Compose (`env_file: .env`) les transmettent au serveur. Le mot de passe aussi dans un fichier secret.

- **Jamais stockée.** Elle n'est pas dans la base de données, et une sauvegarde de LibreFolio ne la contient pas : conservez votre propre copie de
  `.env` et du fichier de mot de passe.
- **Jamais affichée.** Aucune page de l'interface n'affiche le serveur, le port, l'utilisateur, l'expéditeur ou le mot de passe.
  [Paramètres › Administration › E-mail](#email-tab) indique si l'e-mail fonctionne et, sinon, quelle variable
  corriger ; parmi les valeurs `LIBREFOLIO_SMTP_*`, il n'affiche que la limite horaire.
- **Public : uniquement si l'e-mail est prêt.** `/api/v1/system/instance`, que toute personne pouvant joindre le serveur peut lire,
  indique `"available": true` lorsque l'état est **Prêt** et `"links": true` lorsque, en plus, les e-mails peuvent
  contenir un lien ([E-mails avec un lien](email_flows.md#public-url)). Rien d'autre.
- **Redémarrez après une modification.** Avec Docker Compose, exécutez `docker compose up -d`.

Pour désactiver l'e-mail : **dans `.env`**, supprimez `LIBREFOLIO_SMTP_HOST` ou laissez-la vide, puis redémarrez. Les autres
variables peuvent rester : sans serveur, LibreFolio les ignore.

---

## 📋 Les variables {: #variables }

**Dans `.env`**, section `# Email`. `.env.example` les liste, commentées : copiez les lignes dont vous avez besoin.

| Variable | Valeur par défaut | Valeurs acceptées |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` | _non défini_ : e-mail désactivé | Le serveur SMTP : un nom d'hôte, tel que `smtp.example.com`, ou une adresse IP, et rien d'autre : pas de `smtp://`, pas de `user@`, pas de `:587`, pas de chemin. Une adresse IPv6 sans crochets, par exemple `fd00::25`. |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | `starttls`, `tls` ou `none`, en majuscules ou non : [Modes de chiffrement](#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` avec `starttls`, `465` avec `tls`, `25` avec `none` | Un nombre entier de 1 à 65535. Ne le définissez que si le serveur utilise un autre port que celui de son mode. |
| `LIBREFOLIO_SMTP_USER` | _non défini_ : pas d'identifiant de connexion | L'identifiant de connexion de votre compte sur le serveur SMTP. |
| `LIBREFOLIO_SMTP_PASSWORD` | _non défini_ | Le mot de passe de cet identifiant, utilisé exactement tel qu'il est écrit, espaces compris. Ou `LIBREFOLIO_SMTP_PASSWORD_FILE` : le chemin d'un fichier qui le contient. |
| `LIBREFOLIO_SMTP_FROM` | _requis_ avec un serveur | L'expéditeur : une adresse, avec ou sans nom, par exemple `LibreFolio <noreply@example.com>` ou `noreply@example.com`. |
| `LIBREFOLIO_SMTP_REPLY_TO` | _non défini_ : les réponses vont à l'expéditeur | L'adresse vers laquelle vont les réponses. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Combien d'e-mails LibreFolio peut envoyer en une heure, par processus serveur : un nombre entier, au moins 1. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Combien d'e-mails d'inscription une adresse cliente peut déclencher en une heure, par processus serveur : un nombre entier, au moins 1. Au-delà de la limite, les nouveaux comptes sont créés et attendent, mais leurs e-mails sont retenus : [Limites des e-mails de vérification](email_flows.md#verification-limits). Ce n'est pas une variable SMTP (son nom ne commence pas par `LIBREFOLIO_SMTP_`), mais elle est contrôlée avec elles et lue uniquement lorsqu'un serveur est défini. |

- **Vide équivaut à non défini** : une valeur vide, ou composée uniquement d'espaces, compte comme non définie.
- **L'identifiant de connexion va de pair avec le mot de passe** : `LIBREFOLIO_SMTP_USER` avec un mot de passe, ou ni l'un ni
  l'autre pour un serveur qui accepte le courrier sans identifiant.
- **Le mot de passe dans un fichier** : `LIBREFOLIO_SMTP_PASSWORD_FILE` suit les règles de [Secrets dans des fichiers](configuration_secrets.md#secret-files).
  Le mot de passe est le texte du fichier tel quel, quels que soient les caractères qu'il contient, sans les sauts de ligne
  à sa fin. Définissez l'un des deux seulement : lorsque les deux sont définis, `LIBREFOLIO_SMTP_PASSWORD` l'emporte, le fichier est
  ignoré et le journal de démarrage contient un avertissement. Contrairement à `JWT_SECRET_FILE`, un fichier de mot de passe
  illisible n'arrête pas le serveur : l'e-mail reste désactivé jusqu'à ce qu'il soit corrigé.
- **Les limites horaires sont comptées par processus serveur**, sur les 60 dernières minutes, en mémoire :
  `LIBREFOLIO_SMTP_MAX_PER_HOUR` et `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` de la même manière. Un redémarrage
  repart de zéro. `./dev.py server --workers 4` exécute quatre processus, chacun avec son propre compteur :
  l'instance peut envoyer jusqu'à quatre fois la limite ([Démarrer le serveur](cli_tools.md#start-the-server)).
  L'image Docker exécute un seul processus.

### 🔑 Modes de chiffrement {: #encryption-modes }

| `LIBREFOLIO_SMTP_TLS` | Ce qu'il fait | Port habituel |
| --- | --- | --- |
| `starttls` (par défaut) | Se connecte, puis passe au chiffrement avant d'envoyer quoi que ce soit. Un serveur qui ne le propose pas est refusé : rien ne sort en clair. | 587 |
| `tls` | Chiffré dès le premier octet, aussi appelé SSL/TLS ou SMTPS. | 465 |
| `none` | Aucun chiffrement : les messages, les liens et le mot de passe circulent en clair. Uniquement pour un relais sur la même machine ou sur votre réseau local. | 25 |

- Avec `starttls` et `tls`, LibreFolio vérifie le certificat du serveur : il doit être valide et émis pour le
  nom indiqué dans `LIBREFOLIO_SMTP_HOST`. Écrivez le nom pour lequel le certificat est émis, généralement pas l'adresse IP.
- Le port suit le mode, et non l'inverse : `LIBREFOLIO_SMTP_PORT=465` seul conserve `starttls`, ce qu'un
  serveur sur le port 465 n'attend pas. Pour le port 465, définissez `LIBREFOLIO_SMTP_TLS=tls`.

---

## 💡 Exemples {: #examples }

**Dans le `.env` de LibreFolio**, dans la section qui commence par `# Email` : le `.env.example` de cette version
la contient. Si votre `.env` est ancien et n'a pas cette section, ajoutez à sa fin le bloc de l'exemple.
Remplacez `smtp.example.com`, les adresses et le mot de passe par les vôtres, puis redémarrez LibreFolio.

=== "Docker Compose + fichier secret"

    Le mot de passe reste hors de `.env` et hors de l'environnement du conteneur, dans un secret Docker.

    1. **Dans un fichier à côté de `docker-compose.yml`**, par exemple `smtp_password.txt` : enregistrez le mot de passe. Un saut
       de ligne à sa fin ne compte pas ; les espaces, oui.
    2. **Depuis un terminal**, dans le même dossier : le conteneur voit le fichier avec le propriétaire et les permissions qu'il a
       sur l'hôte ; autorisez donc l'utilisateur qui exécute LibreFolio à le lire. Avec l'image officielle, c'est `1000:1000` :

        ```bash
        sudo chown 1000:1000 smtp_password.txt
        sudo chmod 600 smtp_password.txt
        ```

        Une image que vous avez construite vous-même peut utiliser d'autres identifiants : indiquez-les dans la commande `chown`
        ([Docker avancé](docker_advanced.md)).

    3. **Dans `docker-compose.yml`** : ajoutez les lignes marquées et conservez le reste du service tel quel. Si le
       fichier contient déjà des listes `secrets:`, comme l'exemple `JWT_SECRET_FILE` de [Secrets](configuration_secrets.md#secrets),
       ajoutez-y les nouvelles lignes :

        ```yaml
        services:
          librefolio:
            secrets:                         # added
              - smtp_password                # added
        secrets:                             # added
          smtp_password:                     # added
            file: ./smtp_password.txt        # added
        ```

    4. **Dans `.env`** : ajoutez les variables. Si une ligne `LIBREFOLIO_SMTP_PASSWORD` a une valeur, supprimez-la :
       elle l'emporterait sur le fichier.

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.example.com
        LIBREFOLIO_SMTP_USER=noreply@example.com
        LIBREFOLIO_SMTP_PASSWORD_FILE=/run/secrets/smtp_password
        LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
        ```

        Ni `LIBREFOLIO_SMTP_TLS` ni port : `starttls` sur le port 587 est la valeur par défaut.

    5. **Depuis un terminal** : exécutez `docker compose up -d`. L'état dans
       [Paramètres › Administration › E-mail](#email-tab) indique **Prêt**.

=== "Fournisseur de messagerie"

    Votre compte sur le serveur SMTP d'un fournisseur de messagerie.

    1. **Dans `.env`**, section `# Email` :

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.example.com
        LIBREFOLIO_SMTP_USER=you@example.com
        LIBREFOLIO_SMTP_PASSWORD=your-app-password
        LIBREFOLIO_SMTP_FROM=LibreFolio <you@example.com>
        ```

        - C'est `starttls` sur le port 587, les valeurs par défaut. Si le fournisseur indique le port 465, ajoutez
          `LIBREFOLIO_SMTP_TLS=tls` : le port suit.
        - Utilisez un **mot de passe d'application**, et non le mot de passe avec lequel vous vous connectez : le fournisseur le crée pour une seule
          application et vous pouvez le révoquer sans toucher à votre compte.
        - Les pages d'aide du fournisseur donnent le nom du serveur, le port et le chiffrement, et indiquent quelles adresses
          d'expéditeur votre compte peut utiliser.
        - Mieux encore, conservez le mot de passe dans un fichier, comme dans l'onglet Docker Compose.

    2. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`. L'état dans
       [Paramètres › Administration › E-mail](#email-tab) indique **Prêt**.

=== "Gmail"

    Votre compte Gmail, ou un compte Google Workspace, via le serveur SMTP de Gmail. LibreFolio se connecte uniquement avec
    un utilisateur et un mot de passe, pas avec « Se connecter avec Google » : il vous faut un **mot de passe d'application**, et non le mot de passe de votre
    compte Google.

    1. **Dans votre compte Google** : activez la **validation en deux étapes**, si elle ne l'est pas déjà. Les mots de passe d'application
       n'existent qu'avec elle.
    2. **Sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)** : créez un mot de passe
       d'application, avec un nom tel que `LibreFolio`. Google l'affiche sous la forme d'un code de 16 caractères, en quatre groupes
       de quatre : copiez-le. Si la page n'offre aucun moyen d'en créer un,
       la [page d'aide de Google](https://support.google.com/accounts/answer/185833) en explique la raison. Un compte professionnel ou
       scolaire peut nécessiter l'intervention de son administrateur.
    3. **Dans `.env`**, section **Email**, ou à sa fin si votre `.env` n'en a pas :

        ```env
        # =============================================================================
        # Email config gmail
        # =============================================================================
        LIBREFOLIO_SMTP_HOST=smtp.gmail.com
        LIBREFOLIO_SMTP_USER=you@gmail.com
        LIBREFOLIO_SMTP_PASSWORD=abcdefghijklmnop
        LIBREFOLIO_SMTP_FROM=LibreFolio <you@gmail.com>
        ```

        - `you@gmail.com` représente votre adresse Gmail complète, ou votre adresse professionnelle avec Google Workspace.
        - `abcdefghijklmnop` représente le mot de passe d'application : ses 16 caractères **sans les espaces**, car LibreFolio
          utilise le mot de passe exactement tel qu'il est écrit, espaces compris. Mieux encore, conservez-le dans un fichier de mot
          de passe, comme dans l'onglet Docker Compose, là aussi sans les espaces.
        - **Les espaces sont acceptés dans l'expéditeur, pas dans le mot de passe.**
        - L'expéditeur est la même adresse, avec ou sans nom devant. Gmail n'envoie qu'à partir de votre adresse, ou
          d'une adresse que vous avez ajoutée et confirmée sous **Envoyer des e-mails en tant que** dans les paramètres de Gmail.
        - Ni `LIBREFOLIO_SMTP_TLS` ni port : `starttls` sur le port 587 est la valeur par défaut, et l'un des deux modes de Gmail.
          Pour l'autre, le port 465, ajoutez `LIBREFOLIO_SMTP_TLS=tls` : le port suit.

    4. Redémarrez LibreFolio. Avec Docker Compose, exécutez `docker compose up -d`.
    5. **Dans LibreFolio**, **Paramètres › Administration › E-mail** : l'état indique **Prêt**. Cliquez sur
       **Envoyer un e-mail de test** : il part vers l'adresse de votre compte ([L'e-mail de test](#test-email)).

    Pour que cela continue de fonctionner :

    - Un compte Gmail personnel envoie environ 500 e-mails par jour : au-delà, Gmail refuse pendant une période de 1 à 24
      heures. Un compte Google Workspace dispose de 2 000 e-mails par jour via `smtp.gmail.com`. Ce sont les
      [limites de Google](https://support.google.com/mail/answer/22839), et Google peut les modifier. Lorsque Gmail
      refuse, l'e-mail de test et le journal signalent le refus ([Erreurs d'envoi](email_troubleshooting.md#sending-errors)).
    - La limite de LibreFolio est de 50 e-mails par heure par défaut : jusqu'à 1 200 par jour. Pour
      rester sous la limite personnelle, **dans `.env`**, ajoutez `LIBREFOLIO_SMTP_MAX_PER_HOUR=20`, soit 480 par
      jour, et redémarrez. Le comptage est effectué par processus serveur : [Les variables](#variables).
    - Google révoque les mots de passe d'application lorsque vous changez le mot de passe de votre compte Google : créez-en un nouveau,
      écrivez-le à la place de l'ancien dans `.env` et redémarrez. Supprimer le mot de passe d'application, sur la page où
      vous l'avez créé, empêche également LibreFolio d'envoyer des e-mails.

=== "Relais local"

    Un relais tel que Postfix, sur la même machine ou sur votre réseau, accepte le courrier sans identifiant et le distribue pour
    LibreFolio. Trois cas ; dans chacun, les variables vont **dans `.env`**, section `# Email`, puis redémarrez.

    **LibreFolio sur l'hôte, le relais sur la même machine :**

    ```env
    LIBREFOLIO_SMTP_HOST=localhost
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    **LibreFolio dans Docker, le relais dans un autre conteneur sur le même réseau Docker**, ici un service Compose
    nommé `smtp-relay` :

    ```env
    LIBREFOLIO_SMTP_HOST=smtp-relay
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    **LibreFolio dans Docker, le relais sur l'hôte :** à l'intérieur d'un conteneur, `localhost` désigne le conteneur, pas l'hôte.

    1. **Dans `docker-compose.yml`** : ajoutez les lignes marquées.

        ```yaml
        services:
          librefolio:
            extra_hosts:                                # added
              - "host.docker.internal:host-gateway"     # added
        ```

    2. **Dans `.env`** : `LIBREFOLIO_SMTP_HOST=host.docker.internal`, avec `LIBREFOLIO_SMTP_TLS=none` et l'expéditeur
       comme ci-dessus.
    3. **Dans le relais** : autorisez-le à accepter le courrier provenant du réseau Docker (dans Postfix : `inet_interfaces` et `mynetworks`).

    Dans tous les cas :

    - Le port 25 est la valeur par défaut avec `none` : ne définissez `LIBREFOLIO_SMTP_PORT` que si le relais écoute sur un autre port.
    - Ni utilisateur ni mot de passe : un relais sans identifiant n'en demande pas.
    - Le relais distribue le courrier : il doit être autorisé à envoyer pour le domaine de `LIBREFOLIO_SMTP_FROM`.
    - `none` envoie en clair : ne l'utilisez que vers votre propre machine ou votre propre réseau. Vers tout autre serveur,
      Paramètres › Administration › E-mail et le journal de démarrage affichent un [avertissement](email_troubleshooting.md#security).

---

## 🖥️ Paramètres › Administration › E-mail {: #email-tab }

**Dans LibreFolio** : **Paramètres** (icône d'engrenage dans la barre latérale) › **Administration** › l'onglet
**E-mail**, après **Sauvegarde** (sur un téléphone : l'icône de bouclier, puis l'icône d'enveloppe). Seuls les administrateurs
le voient. L'icône de livre en haut ouvre cette page.

### 🚦 L'état {: #state }

| État | Ce que cela signifie | Ce qu'affiche l'onglet |
| --- | --- | --- |
| **Désactivé** | `LIBREFOLIO_SMTP_HOST` n'est pas définie : rien n'est envoyé. C'est la valeur par défaut. | Une courte explication et un renvoi vers ce guide. |
| **Prêt** | Toutes les variables peuvent être utilisées. | Les e-mails restants cette heure-ci, les messages applicables, l'adresse à partir de laquelle commencent les liens envoyés par e-mail et [sa vérification](#links-check), ainsi que **Envoyer un e-mail de test**. |
| **Ne fonctionne pas** | Une variable ne peut pas être utilisée : l'e-mail reste désactivé jusqu'à ce qu'elle soit corrigée. | Le problème, avec le nom de la variable en cause, et un rappel de redémarrer après la correction. |

!!! note "✅ Prêt ne signifie pas qu'un e-mail a déjà été délivré"

    **Prêt** signifie que toutes les variables peuvent être utilisées. LibreFolio ne contacte le serveur qu'au moment d'envoyer
    un e-mail : seul un e-mail de test prouve que le serveur accepte votre courrier.

- **Ne fonctionne pas** nomme un problème à la fois, le premier qu'il trouve : corrigez-le dans `.env`, redémarrez, puis
  regardez de nouveau. [Problèmes de configuration](email_troubleshooting.md#configuration-problems) indique quoi
  vérifier pour chacun.
- Avec **Prêt**, l'onglet compte les e-mails restants, par exemple **Il reste 48 e-mails sur 50 pour cette heure** : les
  60 dernières minutes, et non l'heure pleine. Lorsqu'il n'en reste aucun, il indique dans combien de minutes le prochain peut partir.
  Avec plusieurs processus serveur, chacun compte les siens : l'onglet affiche le compteur du processus
  qui a répondu.
- L'avertissement de chiffrement apparaît lorsque `LIBREFOLIO_SMTP_TLS=none` pointe vers un serveur extérieur à votre
  réseau local : [Notes de sécurité](email_troubleshooting.md#security).
- Un message concernant `LIBREFOLIO_PUBLIC_URL` apparaît lorsqu'elle n'est pas définie (information : les e-mails fonctionnent, mais aucun
  e-mail contenant un lien ne peut partir) ou qu'elle ne peut pas servir de base à un lien (avertissement) :
  [E-mails avec un lien](email_flows.md#public-url).

### 🧭 L'adresse dans les liens envoyés par e-mail {: #links-check }

Avec l'état **Prêt** et une `LIBREFOLIO_PUBLIC_URL` utilisable, l'onglet affiche *Les liens des e-mails commencent
par …*, suivi de cette adresse, et vérifie depuis ce navigateur que **cette** instance y répond. C'est la même
vérification signée que dans les boîtes de dialogue d'invitation et de réinitialisation ([L'adresse serveur d'un lien](users.md#server-address)).

| Message | Ce que cela signifie |
| --- | --- |
| *Vérification depuis cet appareil que cette instance répond à cette adresse…* | La vérification est en cours. |
| *Cette instance répond à cette adresse, depuis cet appareil.* | Parfait : les liens atteignent cette instance de LibreFolio, au moins depuis ici. |
| *Depuis cet appareil, un autre serveur répond à cette adresse, pas cette instance.* … | Quelque chose y répond, mais pas cette instance de LibreFolio. |
| *Cet appareil ne parvient pas à joindre cette instance à cette adresse.* … | Aucune réponse que ce navigateur ait pu lire : une adresse erronée ou fermée, un nom que cet appareil ne résout pas, aucune réponse en 8 secondes, un navigateur qui bloque l'accès d'une page publique à une adresse locale ou qui demande d'abord votre autorisation, ou une version plus ancienne de LibreFolio qui ne sait pas répondre à la vérification. |
| *Cette page utilise https:// alors que LIBREFOLIO_PUBLIC_URL commence par http://* … | Ce navigateur ne peut pas vérifier une adresse `http://` depuis une page `https://`, et les liens des e-mails circuleraient sans chiffrement : définissez la variable avec l'adresse `https://`. |
| *Ce navigateur ne parvient pas à lire LIBREFOLIO_PUBLIC_URL comme une adresse* … | Le navigateur lit les adresses un peu plus strictement que le serveur : les liens risquent de ne pas s'ouvrir. Vérifiez la valeur. |

!!! warning "📱 Cet appareil uniquement"

    La vérification s'exécute depuis le navigateur que vous utilisez : elle indique donc ce que voit cet appareil. Un VPN,
    une adresse IP directe, son DNS ou son réseau peuvent différer de ceux de vos utilisateurs : après un
    avertissement, vérifiez depuis un autre appareil avant de modifier la variable. **Vérifier à nouveau** relance la
    vérification, par exemple après un changement de réseau.

- La vérification s'exécute une fois à l'ouverture de l'onglet, pas après chaque e-mail de test. **Vérifier à nouveau** apparaît
  avec un avertissement.
- Rien n'est vérifié avec l'état **Désactivé** ou **Ne fonctionne pas**, ni lorsque `LIBREFOLIO_PUBLIC_URL`
  n'est pas définie ou ne peut pas être utilisée, ce que signale le message ci-dessus.

### ✉️ L'e-mail de test {: #test-email }

**Dans LibreFolio**, **Paramètres › Administration › E-mail**, avec l'état **Prêt** : **Envoyer un e-mail de test**
vous envoie un e-mail.

- **À votre adresse** : l'e-mail de votre compte, comme dans [Profil](../user/settings/profile.md). Aucun champ
  ne permet d'en saisir une autre.
- **Dans votre langue** : celle de vos [Préférences](../user/settings/preferences.md), sinon la
  **Langue par Défaut** de l'instance ([Paramètres globaux](settings.md)), sinon l'anglais.
- **Ce qu'il contient** : son objet est **LibreFolio test email** en anglais. Le message nomme votre instance par
  l'adresse avec laquelle votre navigateur l'a atteinte, et non par `LIBREFOLIO_PUBLIC_URL`, et indique que, si vous pouvez le
  lire, LibreFolio peut envoyer des e-mails. Il est fourni en texte brut avec une version HTML.
- **Il compte dans la limite horaire**, même lorsque le serveur le refuse.

Le résultat apparaît sous le bouton. **E-mail de test envoyé à votre adresse** : le serveur SMTP a accepté le
message ; vérifiez votre boîte de réception et le dossier de spam. Sinon, l'onglet indique ce qui a échoué :
[Erreurs d'envoi](email_troubleshooting.md#sending-errors). Pendant que LibreFolio dialogue avec le serveur, le bouton
affiche **Envoi…** : LibreFolio attend jusqu'à 20 secondes à chaque étape, si bien qu'un serveur qui ne
répond pas met du temps à échouer.

---

## 🔗 Voir aussi

- 📄 **[E-mail : liens et messages](email_flows.md)** — E-mails contenant un lien, liens envoyés par un administrateur, mots de passe oubliés, …
- 📄 **[E-mail : quand cela ne fonctionne pas](email_troubleshooting.md)** — Quand cela ne fonctionne pas, notes de sécurité
- 📝 **[Configuration](configuration.md)** — Le fichier `.env` et ses principales options, ainsi que
  `LIBREFOLIO_PUBLIC_URL`
- 🔐 **[Configuration : secrets et paramètres des plugins](configuration_secrets.md)** — Secrets dans des fichiers,
  comme le mot de passe SMTP
- 🩺 **[Configuration : contrôles et protections](configuration_security.md)** — Les contrôles au démarrage
- ⚙️ **[Paramètres globaux](settings.md)** — L'interrupteur **Vérification Email Requise**
- 👥 **[Utilisateurs et invitations](users.md)** — Comptes en attente et comment en laisser entrer un
- 🛠️ **[Outils en ligne de commande](cli_tools.md)** — Liens d'invitation et de réinitialisation de mot de passe depuis la ligne
  de commande
- 🐳 **[Docker avancé](docker_advanced.md)** — Le fichier Compose et l'utilisateur qui exécute LibreFolio
  dans le conteneur
- 📂 **[Structure du système de fichiers](filesystem.md)** — Où est conservé le journal
- 👤 **[Profil](../user/settings/profile.md)** — L'adresse e-mail de votre compte
- 🧑‍💻 Pour les développeurs : **[Service d'e-mail (SMTP)](../developer/backend/email.md)** — Comment le service
  fonctionne à l'intérieur
