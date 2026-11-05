# 🧰 Vérification de la sécurité de la connexion : derrière un proxy inverse

Cette page concerne l’exécution de LibreFolio **derrière un proxy inverse** tel que Nginx, Caddy, Traefik ou
Tailscale Serve : les en-têtes que le proxy doit envoyer pour que la connexion soit considérée comme sécurisée, à quel proxy
LibreFolio fait confiance, et comment il apprend l’adresse de chaque visiteur.

Pour voir ce que vos utilisateurs obtiennent, avec l’indicateur, la vue du serveur et le cookie de session, commencez par
[Vérification de la sécurité de la connexion](connection_checks.md).

---

## 🧰 Derrière un proxy inverse {: #reverse-proxy }

Un proxy inverse reçoit la connexion HTTPS et la transmet à LibreFolio en HTTP simple ; LibreFolio n’apprend donc
le HTTPS, ainsi que l’identité du visiteur, qu’à partir des en-têtes du proxy :

- `X-Forwarded-Proto: https` indique que le navigateur utilise HTTPS : avec `SESSION_COOKIE_SECURE=auto`,
  la valeur par défaut, LibreFolio marque alors le cookie de session comme `Secure` ;
- `X-Forwarded-For` transporte l’adresse du visiteur, ce qui permet à l’indicateur de voir depuis où les utilisateurs se connectent.

Tailscale Serve et Funnel, Caddy et Traefik envoient les deux d’eux-mêmes. Nginx a besoin des deux lignes dans le
bloc `location` qui transmet les requêtes à LibreFolio :

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Si le navigateur utilise HTTPS mais que le cookie de session n’est pas marqué `Secure`, parce que le proxy n’envoie pas
`X-Forwarded-Proto` ou parce que `SESSION_COOKIE_SECURE` vaut `never`, les administrateurs voient une ligne supplémentaire
dans les détails de l’indicateur. Le niveau reste **Connexion : sécurisée**, car la connexion est chiffrée ; seul le cookie n’a pas `Secure` :

> Votre navigateur utilise HTTPS, mais le cookie de session n’est pas marqué Secure. Faites envoyer
> X-Forwarded-Proto par le proxy inverse (Nginx : `proxy_set_header X-Forwarded-Proto $scheme;`), ou remettez
> SESSION_COOKIE_SECURE à auto s’il vaut never.

Une fois le proxy corrigé, rechargez LibreFolio : la ligne disparaît. Déconnectez-vous ensuite puis reconnectez-vous,
afin que le navigateur reçoive un cookie `Secure`.

??? tip "⚙️ Définir plutôt `SESSION_COOKIE_SECURE`"

    Envoyer l’en-tête est la meilleure solution. Si vous n’atteignez LibreFolio qu’en HTTPS, vous pouvez
    plutôt ajouter cette ligne à `.env` :

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Redémarrez ensuite LibreFolio : avec Docker, exécutez `docker compose up -d` (un simple
    `docker compose restart` conserve l’ancien environnement) ; sur une installation sur l’hôte, redémarrez
    `./dev.py server`, qui lit aussi `.env`. Déconnectez-vous ensuite puis reconnectez-vous.

    N’utilisez `never` que pour le rare proxy qui prétend utiliser HTTPS alors que le navigateur est en HTTP simple. Voir
    [Configuration](configuration.md#session-cookie-secure) pour toutes les options.

### 🧭 L’adresse du visiteur {: #client-address }

LibreFolio limite certaines requêtes par adresse de visiteur : les tentatives de connexion échouées
([Connexions échouées](configuration_accounts.md#login-limit)), les e-mails d’inscription, **Renvoyer le lien**
et les mots de passe oubliés ([E-mail](email.md)). Derrière un proxy inverse, les connexions proviennent du
proxy : à moins que LibreFolio n’apprenne l’adresse de chaque visiteur, toutes partagent celle du proxy, et un
seul et même décompte. Pour les tentatives de connexion, c’est ce qui importe le plus : 50 tentatives de connexion échouées via le proxy, de n’importe qui,
refuseraient toute tentative de connexion passant par lui, y compris avec les bons mots de passe, pendant jusqu’à 15 minutes. Cela
reste vrai derrière un proxy sur une adresse publique. Derrière un proxy sur une adresse locale, comme un conteneur
proxy devant l’image Docker, LibreFolio exclut alors les tentatives de connexion passant par lui du décompte
par adresse, et seule la limite par nom d’utilisateur ou par adresse e-mail les compte : voir
[Quand LibreFolio ne fait pas confiance à votre proxy](#untrusted-proxy), ci-dessous. Dans un cas comme dans l’autre, la solution consiste à
permettre à LibreFolio d’apprendre l’adresse de chaque visiteur, de l’une des deux manières suivantes.

Par défaut, l’adresse prise en compte est celle de la connexion, telle que la fournit uvicorn, le serveur web de LibreFolio.
uvicorn ne récupère l’adresse du visiteur depuis `X-Forwarded-For` que lorsque la connexion provient
d’une adresse listée dans `FORWARDED_ALLOW_IPS`, soit `127.0.0.1` lorsque cette variable n’est pas définie :
[Mots de passe oubliés](email_flows.md#forgot-password), dans le guide des e-mails, explique comment y lister votre proxy.

Si votre proxy écrit plutôt l’adresse du visiteur dans un en-tête qui lui est propre, indiquez cet en-tête dans
`LIBREFOLIO_CLIENT_IP_HEADER`, dans `.env` ou dans l’environnement du conteneur :

```bash
LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP
```

| Votre proxy | L’en-tête | Ce qu’il faut configurer |
| --- | --- | --- |
| Fly.io | `Fly-Client-IP` | Rien : le proxy de Fly définit cet en-tête. |
| Nginx | `X-Real-IP` | Ajoutez `proxy_set_header X-Real-IP $remote_addr;` au bloc `location` qui transmet les requêtes à LibreFolio. |

!!! warning "🚧 Uniquement lorsque chaque requête passe par le proxy"

    LibreFolio fait confiance à l’en-tête, quel que soit son émetteur. Ne définissez la variable que si vos visiteurs ne peuvent
    atteindre LibreFolio qu’à travers ce proxy : un visiteur qui l’atteint directement, sur son propre port
    (`PORT`, 6040 par défaut) ou par tout autre chemin, peut envoyer l’en-tête et choisir n’importe quelle adresse, pour
    contourner les limites ou consommer le quota de quelqu’un d’autre.

- **Redémarrer après un changement** : LibreFolio lit la variable une fois par processus serveur. Avec Docker,
  exécutez `docker compose up -d` (un simple `docker compose restart` conserve l’ancien environnement) ; sur une
  installation sur l’hôte, redémarrez `./dev.py server`.
- **L’en-tête doit contenir une seule adresse, écrite par le proxy lui-même** : jamais une valeur que le proxy transmet
  depuis le visiteur. `X-Forwarded-For` et `Forwarded` sont refusés : ils contiennent une liste dont la première
  adresse est choisie par le visiteur. Pour `X-Forwarded-For`, listez plutôt votre proxy dans `FORWARDED_ALLOW_IPS`.
- **Une valeur incorrecte empêche le serveur de démarrer**, avec une erreur qui nomme la variable : l’un de
  ces deux en-têtes, ou une valeur qui n’est pas le nom d’un en-tête, comme un nom contenant un espace ou
  un `:`. La casse et les espaces autour du nom n’ont pas d’importance ; une valeur vide équivaut à ne pas
  définir la variable.
- **Une requête sans l’en-tête** est comptée avec l’adresse de la connexion.
- **Un en-tête que LibreFolio ne peut pas utiliser**, parce que la requête le contient deux fois ou qu’il contient une liste, une
  adresse avec un port ou autre chose qu’une seule adresse IP : la requête est alors elle aussi comptée avec l’adresse de la connexion.
  Le journal contient alors un avertissement par processus serveur,
  `Client address header unusable: using the connection's address`, avec le nom de l’en-tête dans
  `header`, le nombre de fois où la requête l’a contenu dans `lines` et leur longueur totale dans `length`,
  jamais la valeur elle-même : vérifiez comment votre proxy définit l’en-tête.
- **Un autre proxy devant Fly.io**, comme Cloudflare : `Fly-Client-IP` contient alors l’adresse de ce proxy,
  et non celle du visiteur.
- **Aucun profil ne définit cette variable** : l’en-tête dépend du proxy devant chaque instance.
- **L’indicateur ne l’utilise pas** : il continue de lire `X-Forwarded-For`, comme
  l’explique [La vue du serveur](connection_checks.md#server-view).

#### 🕵️ Quand LibreFolio ne fait pas confiance à votre proxy {: #untrusted-proxy }

LibreFolio ne fait pas confiance à votre proxy lorsqu’il n’apprend l’adresse du visiteur ni via
`FORWARDED_ALLOW_IPS` ni via `LIBREFOLIO_CLIENT_IP_HEADER` : il ne peut pas distinguer les visiteurs
derrière le proxy, et ses limites par adresse de visiteur ne le peuvent pas non plus. Il reconnaît un tel
proxy à ses requêtes : elles proviennent d’une adresse locale (`loopback`, `lan` ou `vpn` dans
[La vue du serveur](connection_checks.md#server-view), par exemple `172.18.0.2` sur un réseau Docker) et portent un en-tête de transfert
(`X-Forwarded-For`, `Forwarded` ou `X-Real-IP`) qui n’a donné à LibreFolio aucune adresse de visiteur.
Alors :

- **Les limites par adresse de visiteur excluent ces requêtes**, afin qu’un seul visiteur ne puisse pas bloquer
  tout le monde. Les limites par compte ou par adresse e-mail les comptent toujours.
- **Le journal contient un avertissement par processus serveur**, la première fois qu’une telle requête rencontre une limite par
  adresse de visiteur :
  `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`,
  avec les noms des en-têtes dans `headers`, par exemple `X-Forwarded-For, X-Real-IP`, jamais une
  adresse.
- **Les contrôles de sécurité** le signalent aussi, sous forme d’avertissement de `platform.client_address`. Ce contrôle
  indique ce que le serveur a rencontré depuis son dernier démarrage : après un redémarrage, il affiche `ok` jusqu’à ce qu’une telle
  requête se reproduise ; il n’apparaît donc jamais parmi les [contrôles au démarrage](configuration_security.md#startup-checks).
- **Pour corriger cela**, listez votre proxy dans `FORWARDED_ALLOW_IPS`, comme l’explique [Mots de passe oubliés](email_flows.md#forgot-password)
  dans le guide des e-mails, ou nommez l’en-tête qu’il définit lui-même dans
  `LIBREFOLIO_CLIENT_IP_HEADER`, comme ci-dessus, si chaque requête le traverse. Derrière Tailscale Serve ou
  Funnel avec l’image Docker, suivez [Tailscale Serve et Funnel avec Docker](#tailscale). Dans
  `FORWARDED_ALLOW_IPS`, indiquez l’adresse du proxy telle que LibreFolio la voit : avec Docker, l’adresse du conteneur
  proxy, ou celle de son réseau Docker, par exemple `FORWARDED_ALLOW_IPS=172.18.0.0/16`
  (`docker network inspect`, avec le nom du réseau, affiche les deux), bien qu’un réseau entier inclue
  sa passerelle, qui est aussi l’adresse des connexions établies sur le serveur lui-même
  ([voir ci-dessous](#tailscale)). Ne faites confiance qu’aux adresses utilisées uniquement par votre proxy. Définissez l’une ou l’autre variable
  dans `.env` ou dans l’environnement du conteneur, puis redémarrez, comme ci-dessus : avec Docker,
  `docker compose up -d`. Aucun proxy de votre côté devant LibreFolio ? Alors un visiteur de votre propre
  réseau ou VPN a envoyé l’en-tête, ou, avec Docker Desktop exposé directement, n’importe quel visiteur, ou n’importe quel
  visiteur IPv6 que le proxy de Docker relaie ([Limites](connection_checks.md#limits)) : ne listez rien.

**Les en-têtes de transfert provenant d’une adresse publique** ne produisent qu’une entrée de niveau `info` : dans le journal, une fois par processus serveur,
`Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS`,
avec `headers` également ; et dans les contrôles de sécurité, où `platform.client_address` reste un avertissement si
un proxy comme ci-dessus a aussi été rencontré. Ces requêtes continuent d’être comptées avec l’adresse de la connexion. Elles sont
inoffensives lorsqu’aucun proxy de votre côté n’a d’adresse publique : un visiteur, ou son propre proxy, peut ajouter
de tels en-têtes.

#### 🐳 Tailscale Serve et Funnel avec Docker {: #tailscale }

Tailscale Serve et Funnel transmettent l’adresse du visiteur dans `X-Forwarded-For` : l’adresse Tailscale
de l’appareil, `100.x.y.z`, ou, via Funnel, l’adresse du visiteur sur Internet. Ils
écrivent l’en-tête eux-mêmes, à la place de celui que le visiteur aurait envoyé. En HTTPS, le mode par défaut de Serve et
le seul mode de Funnel, ils envoient aussi `X-Forwarded-Proto: https` ; avec `tailscale serve --http=…`
ils n’en envoient aucun, à juste titre, puisque le navigateur est aussi en HTTP simple.

Avec l’image Docker, LibreFolio ne peut pas utiliser cette adresse par défaut. Les deux configurations Tailscale
d’[Exposition sécurisée](service_exposure.md), sur le serveur et dans des
[conteneurs sidecar](service_exposure_funnel.md#level-4-multi-funnel-with-docker-sidecars), atteignent son conteneur via Docker ; leurs requêtes proviennent donc
de la passerelle du réseau Docker du conteneur, par exemple `172.28.0.1`, à laquelle uvicorn ne fait pas
confiance :

- **Sur le serveur**, `tailscale serve --bg 6040` (l’adresse HTTPS du niveau 1) ou
  `tailscale funnel --bg 6040` (niveau 3) transmet les requêtes à `http://127.0.0.1:6040`, et
  le proxy de Docker les remet au conteneur ;
- **Dans des conteneurs sidecar** (niveau 4), socat les transmet à l’adresse LAN du serveur et
  au port publié de LibreFolio.

Ainsi, LibreFolio signale un proxy auquel il ne fait pas confiance, [comme ci-dessus](#untrusted-proxy), et ses limites
par adresse de visiteur excluent toutes ces requêtes. Installé directement sur l’hôte, sans Docker,
LibreFolio n’a besoin de rien pour `tailscale serve` ou `tailscale funnel` sur le même serveur : il voit
leurs requêtes provenir de `127.0.0.1`, adresse à laquelle uvicorn fait confiance par défaut.

Pour permettre à LibreFolio de voir chaque visiteur, travaillez sur le serveur, dans le dossier qui contient
`docker-compose.yml` et `.env` :

1. **Trouvez la passerelle** du réseau Docker de LibreFolio :

    ```bash
    docker inspect --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' librefolio
    ```

    Elle affiche une adresse telle que `172.28.0.1` ; `librefolio` est le nom que `docker-compose.yml` donne
    au conteneur (`container_name`). `docker network inspect <network>` affiche la même passerelle
    sous `IPAM` → `Config` → `Gateway`, à côté du `Subnet` du réseau : `docker network ls` liste
    les réseaux, et celui propre à un projet Compose est `<project>_default`.

    Pour vérifier que les requêtes de Tailscale proviennent bien de cette passerelle, ouvrez LibreFolio à son adresse Tailscale,
    puis lisez les dernières lignes de son journal :

    ```bash
    docker compose logs --tail 20 librefolio
    ```

    uvicorn journalise chaque requête sur une ligne qui donne l’adresse qu’il voit, puis la requête. Via
    Tailscale, cette adresse est celle de la passerelle :

    ```text
    172.28.0.1:<port> - "GET … HTTP/1.1" 200 OK
    ```

    Les lignes concernant `/api/v1/system/health` correspondent au contrôle de santé de Docker, effectué à l’intérieur du conteneur :
    ignorez-les.

2. **Listez la passerelle dans `FORWARDED_ALLOW_IPS`.** Ajoutez cette ligne à `.env`, avec votre propre passerelle :

    ```bash
    FORWARDED_ALLOW_IPS=172.28.0.1
    ```

    Si `.env` définit déjà la variable, pour un autre proxy, ajoutez la passerelle à la fin de sa liste,
    après une virgule.

3. **Redémarrez LibreFolio**, afin que son conteneur prenne en compte le nouvel environnement :

    ```bash
    docker compose up -d
    ```

    Un simple `docker compose restart` conserve l’ancien environnement.

4. **Vérifiez.** Ouvrez de nouveau LibreFolio à son adresse Tailscale, puis lisez le journal comme à l’étape 1. Les
   lignes de vos requêtes affichent maintenant l’adresse de l’appareil à la place de celle de la passerelle (via
   Funnel, l’adresse publique du visiteur), suivie du port `0` :

    ```text
    100.x.y.z:0 - "GET … HTTP/1.1" 200 OK
    ```

    L’avertissement de `platform.client_address` cesse de réapparaître. Ce contrôle indique toutefois ce que le serveur
    a rencontré depuis son dernier démarrage ; il affiche donc `ok` après le redémarrage dans tous les cas : la ligne
    de journal constitue la véritable preuve.

Trois points à garder en tête concernant la confiance accordée à la passerelle :

- **La passerelle exacte est le choix le plus restrictif**, mais Compose peut attribuer un autre sous-réseau
  au réseau lorsqu’il le recrée (`docker compose down`, puis `docker compose up -d`) : vérifiez de nouveau la passerelle
  après un tel changement.
- **`FORWARDED_ALLOW_IPS=172.16.0.0/12` y résiste**, puisqu’il couvre tous les réseaux Docker de
  `172.16` à `172.31`. Mais il fait confiance à tous les réseaux Docker du serveur, et il ne couvre pas les
  réseaux `192.168.x.x` que Docker attribue une fois ceux-ci épuisés.
- **La passerelle n’est pas propre à Tailscale.** C’est aussi l’adresse de chaque connexion établie sur le
  serveur lui-même via le port publié, et des visiteurs IPv6 que le proxy de Docker relaie
  ([Limites](connection_checks.md#limits)) : lui faire confiance leur permet de choisir l’adresse prise en compte par les limites.
    - Si vous atteignez LibreFolio **uniquement** via `tailscale serve` ou `tailscale funnel` sur le
      serveur, publiez le port sur la boucle locale uniquement, afin que rien à l’extérieur du serveur ne puisse l’atteindre
      : dans `docker-compose.yml`, sous `ports:`, remplacez `"${PORT:-6040}:6040"` par
      `"127.0.0.1:${PORT:-6040}:6040"`, puis exécutez `docker compose up -d`.
    - Pas avec le niveau 4, ni avec les adresses HTTP simples des niveaux 1 et 2 : elles atteignent le port
      via l’adresse LAN ou Tailscale du serveur.

---

## 🔗 Voir aussi

- 📄 **[Vérification de la sécurité de la connexion](connection_checks.md)** — Liste de vérification, Ce que l’indicateur affiche, La vue du serveur, …
