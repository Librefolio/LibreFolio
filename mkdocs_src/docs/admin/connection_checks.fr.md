# 🔍 Vérifier la sécurité de la connexion

Chaque utilisateur voit, en bas de la barre latérale de LibreFolio, à quel point son navigateur
dialogue en sécurité avec le serveur : **Connexion : sécurisée**, **Connexion : réseau local** ou
**Connexion : non sécurisée**. Le guide de l'utilisateur, [Sécurité de la connexion](../user/connection-security.md),
lui explique les trois niveaux. Cette page s'adresse à la personne qui gère le serveur : comment
vérifier que votre installation donne à ses utilisateurs **Connexion : sécurisée**, et comment la
corriger quand ce n'est pas le cas.

L'objectif est une adresse HTTPS, fournie par Tailscale Serve ou Funnel
([Exposer en toute sécurité](service_exposure.md)) ou par un proxy inverse avec un certificat
([Derrière un proxy inverse](#reverse-proxy)), et un cookie de session marqué `Secure`.

---

## ✅ Liste de contrôle {: #checklist }

Parcourez-la une fois que votre adresse HTTPS fonctionne, puis de nouveau après chaque modification
du proxy ou de `.env`. Il vous faut un compte administrateur et, pour les deux derniers contrôles,
un téléphone en données mobiles.

1. **Ouvrez l'adresse HTTPS et connectez-vous.** L'indicateur affiche 🟢 **Connexion : sécurisée**,
   et ses détails disent que la connexion est chiffrée en HTTPS.
2. **Cherchez la ligne du cookie.** Connecté en administrateur, les détails n'affichent que cette
   raison et le lien **Comment se connecter en toute sécurité**. Une ligne de plus, sur le cookie de
   session, signifie que LibreFolio ne sait pas qu'il y a du HTTPS : voir
   [Derrière un proxy inverse](#reverse-proxy).
3. **Interrogez le serveur.** Dans un nouvel onglet, ouvrez `https://<your address>/api/v1/system/connection` :
   la réponse contient `"cookie_secure":true` ([Le point de vue du serveur](#server-view)).
4. **Si vous le souhaitez, regardez le cookie.** Dans les outils de développement du navigateur, le
   cookie `session` est marqué `Secure` ([Le cookie de session](#session-cookie)).
5. **Depuis l'extérieur, ouvrez l'adresse HTTPS.** Sur le téléphone, Wi-Fi coupé, la page se charge
   et, une fois connecté, l'indicateur affiche 🟢 **Connexion : sécurisée**. Gardez Tailscale coupé
   sur le téléphone pour une adresse Funnel ou de proxy inverse ; activez-le pour une adresse
   Tailscale Serve, que seul votre tailnet peut ouvrir.
6. **Depuis l'extérieur, essayez le HTTP en clair.** Sur le même téléphone,
   `http://<your public IP or name>:6040`, ou votre propre `PORT`, ne se charge pas. Si la page de
   connexion apparaît, le HTTP en clair est ouvert sur Internet : ne vous y connectez pas, car le mot
   de passe circulerait en clair, et fermez le port ([Quand un contrôle échoue](#when-a-check-fails)).
   Quiconque se connecte par cette adresse voit 🔴 **Connexion : non sécurisée**, ou
   🏠 **Connexion : réseau local** avec une raison *Incertaine* quand le serveur ne peut pas voir
   d'où viennent les visiteurs ([Limites](#limits)).

Tous les contrôles sont passés ? Demandez à vos utilisateurs d'utiliser l'adresse HTTPS sur chaque
appareil et de mettre à jour leurs anciens favoris
([Comment se connecter en toute sécurité](../user/connection-security.md#https-address)).

!!! note "📶 Pas encore d'adresse HTTPS ?"

    Avec le Niveau 1 ou 2 d'[Exposer en toute sécurité](service_exposure.md), les utilisateurs
    atteignent LibreFolio en HTTP en clair. Vérifiez le niveau qu'obtient chaque adresse
    ([Ce que montre l'indicateur](#indicator)) et que le HTTP en clair ne se charge pas depuis
    l'extérieur (contrôle 6). Les contrôles du cookie ne s'appliquent pas : en HTTP en clair, le
    cookie de session n'est pas `Secure`, et `"cookie_secure":false` est attendu.

---

## 🚦 Ce que montre l'indicateur {: #indicator }

Le navigateur juge l'adresse qu'il a ouverte ; le serveur indique ensuite d'où il voit arriver la
requête, et peut confirmer ce verdict ou le rendre incertain, mais jamais le rendre sécurisé. Voici
ce que voient vos utilisateurs, selon la façon dont ils atteignent LibreFolio :

| Comment les utilisateurs atteignent LibreFolio | Exemple | Niveau |
| --- | --- | --- |
| Tailscale Serve ou Funnel, ou un proxy inverse avec un certificat | `https://librefolio.your-tailnet.ts.net` | 🟢 **sécurisée** : HTTPS |
| Sur le serveur lui-même | `http://localhost:6040` | 🟢 **sécurisée** : `localhost` |
| IP Tailscale ou nom MagicDNS complet, HTTP en clair (Niveau 1) | `http://100.a.b.c:6040` | 🟢 **sécurisée** : VPN (Tailscale) |
| Nom MagicDNS court, HTTP en clair : un nom sans point compte comme local | `http://your-server:6040` | 🏠 **réseau local** |
| Adresse locale, y compris via un routeur de sous-réseau (Niveau 2) | `http://192.168.1.100:6040` | 🏠 **réseau local** |
| Un port ouvert sur le routeur, HTTP en clair | `http://myhome.duckdns.org:6040` | 🔴 **non sécurisée** |

Quand le serveur ne peut pas voir les adresses de vos visiteurs, la dernière ligne affiche à la
place 🏠 **réseau local** avec une raison *Incertaine* ([Limites](#limits)). Le guide de
l'utilisateur donne les règles exactes sous chaque niveau : plages d'adresses, noms et cas
*Incertaine* ([Sécurité de la connexion](../user/connection-security.md#connection-secure)).

---

## 🔎 Le point de vue du serveur {: #server-view }

L'indicateur demande au serveur comment il voit la connexion, une fois par chargement de page :
`GET /api/v1/system/connection`. Vous pouvez lire la même réponse : connecté, ouvrez cette adresse
dans un nouvel onglet du même navigateur, avec votre propre adresse LibreFolio à la place de celle
de l'exemple :

```text
https://librefolio.your-tailnet.ts.net/api/v1/system/connection
```

Le navigateur affiche une réponse d'une ligne, par exemple :

```json
{"client_class":"public","cookie_secure":true}
```

N'importe quel compte convient, pas seulement un administrateur. Une réponse comme
`{"detail":"Not authenticated"}` signifie qu'il n'y a pas de session à cette adresse : les sessions
appartiennent à une adresse, donc se connecter sur `http://192.168.1.100:6040` ne vous connecte pas
à l'adresse HTTPS. Et comme l'indicateur ne demande qu'une fois par chargement de page, rechargez
LibreFolio après une modification pour voir son nouveau verdict.

**`cookie_secure`** indique si un cookie de session posé sur cette requête serait `Secure`, selon
[`SESSION_COOKIE_SECURE`](#session-cookie). Sur l'adresse HTTPS, il doit valoir `true` : `false` est
ce qui affiche la ligne destinée à l'administrateur sur le cookie
([Derrière un proxy inverse](#reverse-proxy)). En HTTP en clair, `false` est attendu.

**`client_class`** est l'endroit d'où le serveur voit arriver la requête. Il lit la dernière valeur
de `X-Forwarded-For`, celle qu'a ajoutée le proxy le plus proche, quand c'est une adresse IP, et
sinon l'adresse de la connexion elle-même. Seule la classe sort du serveur : l'adresse n'est jamais
renvoyée ni journalisée.

| `client_class` | La requête vient de |
| --- | --- |
| `loopback` | Le serveur lui-même : `127.0.0.0/8` ou `::1` |
| `vpn` | Tailscale ou Headscale : `100.64.0.0/10` ou `fd7a:115c:a1e0::/48` |
| `lan` | Un réseau local : `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` ou `fc00::/7` |
| `public` | Toute autre adresse : Internet |
| `unknown` | Aucune adresse, ou une adresse illisible |

La classe ne compte qu'en HTTP en clair, et pas sur le serveur lui-même (`localhost`) :

- avec une adresse publique dans le navigateur, `public` ou `unknown` confirme
  **Connexion : non sécurisée**, tandis que `loopback`, `vpn` ou `lan` la changent en
  **Connexion : réseau local**, comme incertaine ;
- avec une adresse locale ou Tailscale dans le navigateur, `public` rend le verdict incertain, et
  toute autre classe le laisse tel quel.

Sur l'adresse HTTPS, la classe ne change rien, mais elle vous dit si le serveur peut voir les
adresses de vos visiteurs : depuis le téléphone en données mobiles, Tailscale coupé, `public`
signifie qu'il le peut, et `lan` ou `loopback` qu'il ne le peut pas ([Limites](#limits)).

---

## 🍪 Le cookie de session {: #session-cookie }

Le cookie qui garde un utilisateur connecté s'appelle `session`. LibreFolio le pose à la connexion,
toujours `HttpOnly`, pour que les scripts de la page ne puissent pas le lire, et `SameSite=Lax`.
S'il est aussi `Secure`, c'est-à-dire envoyé uniquement en HTTPS, cela dépend de
`SESSION_COOKIE_SECURE` dans `.env` :

- **`auto`**, la valeur par défaut : `Secure` quand la requête est en HTTPS, vue directement ou
  parce que la première valeur de `X-Forwarded-Proto` envoyée par un proxy inverse est `https` ;
- **`always`** : toujours `Secure` ;
- **`never`** : jamais `Secure`.

La casse et les espaces autour de la valeur ne comptent pas ; toute autre valeur arrête LibreFolio
au démarrage. Quand `always` ou `never` est le bon choix :
[Configuration](configuration.md#session-cookie-secure).

L'attribut se décide à la connexion : le cookie qu'un navigateur détient déjà garde l'attribut
qu'il a reçu alors. Après avoir corrigé le proxy ou l'option, déconnectez-vous et reconnectez-vous.

Pour voir l'attribut dans le navigateur :

1. Connectez-vous à l'adresse HTTPS.
2. Ouvrez les outils de développement : `F12`, ou clic droit sur la page puis **Inspecter**. Safari
   ne les affiche qu'une fois ses fonctions pour développeurs activées dans ses réglages.
3. Ouvrez les cookies de votre adresse LibreFolio : **Application** → **Cookies** dans Chrome et
   Edge, **Storage** → **Cookies** dans Firefox et Safari (les noms suivent la langue du navigateur).
4. Dans la ligne `session`, **Secure** est coché (`true` dans Firefox), tout comme **HttpOnly** ;
   **SameSite** indique `Lax`.

La console ne peut pas le montrer : `document.cookie` laisse de côté les cookies `HttpOnly`.

---

## 🧰 Derrière un proxy inverse {: #reverse-proxy }

Un proxy inverse reçoit la connexion HTTPS et la transmet à LibreFolio en HTTP en clair, si bien
que LibreFolio n'apprend l'existence du HTTPS, et celle du visiteur, que par les en-têtes du proxy :

- `X-Forwarded-Proto: https` dit que le navigateur utilise HTTPS : avec
  `SESSION_COOKIE_SECURE=auto`, la valeur par défaut, LibreFolio marque alors le cookie de session
  `Secure` ;
- `X-Forwarded-For` porte l'adresse du visiteur, ce qui permet à l'indicateur de voir d'où se
  connectent les utilisateurs.

Tailscale Serve et Funnel, Caddy et Traefik envoient les deux d'eux-mêmes. Nginx a besoin des deux
lignes dans le bloc `location` qui transmet les requêtes à LibreFolio :

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Si le navigateur utilise HTTPS mais que le cookie de session n'est pas marqué `Secure`, parce que
le proxy n'envoie pas `X-Forwarded-Proto` ou parce que `SESSION_COOKIE_SECURE` vaut `never`, les
administrateurs voient une ligne de plus dans les détails de l'indicateur. Le niveau reste
**Connexion : sécurisée**, car la connexion est chiffrée ; seul le cookie n'a pas `Secure` :

> Votre navigateur utilise HTTPS, mais le cookie de session n'est pas marqué Secure. Faites envoyer
> X-Forwarded-Proto par le reverse proxy (Nginx : `proxy_set_header X-Forwarded-Proto $scheme;`),
> ou remettez SESSION_COOKIE_SECURE sur auto s'il vaut never.

Une fois le proxy corrigé, rechargez LibreFolio : la ligne disparaît. Déconnectez-vous ensuite et
reconnectez-vous, pour que le navigateur reçoive un cookie `Secure`.

??? tip "⚙️ Définir plutôt `SESSION_COOKIE_SECURE`"

    Envoyer l'en-tête est la meilleure correction. Si vous n'atteignez LibreFolio qu'en HTTPS, vous
    pouvez à la place ajouter cette ligne à `.env` :

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Redémarrez ensuite LibreFolio : avec Docker, lancez `docker compose up -d` (un simple
    `docker compose restart` garde l'ancien environnement) ; avec une installation sur l'hôte,
    redémarrez `./dev.py server`, qui lit lui aussi `.env`. Déconnectez-vous ensuite et
    reconnectez-vous.

    N'utilisez `never` que pour le rare proxy qui annonce HTTPS alors que le navigateur est en HTTP
    en clair. Voir [Configuration](configuration.md#session-cookie-secure) pour toutes les options.

---

## 🛠️ Quand un contrôle échoue {: #when-a-check-fails }

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| L'adresse HTTPS n'affiche pas **Connexion : sécurisée** | La page n'est pas en HTTPS : la barre d'adresse affiche `http://` | Ouvrez l'adresse `https://`, et faites rediriger `http://` vers elle par le proxy |
| La ligne sur le cookie de session, ou `"cookie_secure":false` sur l'adresse HTTPS | Le proxy n'envoie pas `X-Forwarded-Proto: https`, ou `SESSION_COOKIE_SECURE` vaut `never` | Corrigez le proxy ([Derrière un proxy inverse](#reverse-proxy)) ou remettez l'option sur `auto`, puis rechargez |
| `"cookie_secure":true`, mais le cookie `session` n'est pas `Secure` | Le cookie a été posé avant la correction | Déconnectez-vous et reconnectez-vous |
| `{"detail":"Not authenticated"}` | Pas de session à cette adresse | Connectez-vous à cette adresse, dans le même navigateur |
| Chaque connexion se termine de nouveau sur la page de connexion | Le cookie est `Secure`, mais le navigateur utilise le HTTP en clair : `SESSION_COOKIE_SECURE=always`, ou un proxy qui envoie `X-Forwarded-Proto: https` à un navigateur en HTTP en clair | Utilisez l'adresse HTTPS, ou corrigez le proxy : voir [Configuration](configuration.md#session-cookie-secure) |
| Depuis l'extérieur, l'adresse HTTPS ne se charge pas | Une adresse Tailscale Serve est privée ; un nouveau Funnel demande une approbation et quelques minutes | Activez Tailscale sur le téléphone, ou utilisez Funnel ; approuvez le Funnel et patientez ([Exposer en toute sécurité](service_exposure.md)) |
| Depuis l'extérieur, `http://…:6040` en clair se charge | Le port de LibreFolio est ouvert sur Internet : une redirection de port sur le routeur, ou un serveur avec une adresse publique | Fermez-le : supprimez la redirection de port, ou bloquez le port dans le pare-feu du serveur. Tailscale n'a besoin d'aucun port ouvert, et un proxy inverse seulement du sien |
| `client_class` indique `lan` ou `loopback` en données mobiles, ou le HTTP en clair depuis Internet affiche **Connexion : réseau local**, *Incertaine* | Le serveur ne peut pas voir d'où viennent les visiteurs | Voir [Limites](#limits) ; avec Nginx, ajoutez la ligne `X-Forwarded-For` |
| Une adresse Tailscale affiche **Connexion : réseau local** | Un nom MagicDNS court n'a pas de point, il compte donc comme local | Utilisez l'IP Tailscale, le nom complet `.ts.net` ou, mieux, l'adresse HTTPS |

---

## ⚠️ Limites {: #limits }

L'indicateur est un conseil, pas un contrôle : il ne bloque rien. Deux limites comptent quand vous
vérifiez une installation.

**Il ne voit pas toujours où sont les visiteurs.** Avec Docker Desktop exposé directement, ou
derrière un proxy qui ne transmet pas l'adresse du visiteur dans `X-Forwarded-For`, le serveur voit
chaque visiteur comme local : `lan`, ou `loopback` pour un proxy sur la même machine. Le HTTP en
clair depuis Internet affiche alors **Connexion : réseau local**, comme incertaine, au lieu de
**Connexion : non sécurisée**. Docker Engine sous Linux conserve l'adresse du visiteur. Les
adresses HTTPS ne sont pas concernées : elles affichent **Connexion : sécurisée** dans tous les
cas.

**Il ne vérifie pas les certificats.** Un certificat auto-signé qu'un utilisateur a accepté dans le
navigateur affiche **Connexion : sécurisée** : le trafic est chiffré, mais personne ne garantit que
le serveur est bien le vôtre.

Il n'y a pas de liste de proxys de confiance à configurer. `X-Forwarded-For` n'alimente que
l'indicateur, donc une valeur falsifiée ne trompe que l'indicateur de celui qui l'a envoyée ;
`X-Forwarded-Proto` ne peut qu'activer `Secure`, donc un `https` falsifié ne casse que la connexion
de son expéditeur.

---

## 🔗 Voir aussi

- 🔐 **[Sécurité de la connexion](../user/connection-security.md)** — Le guide de l'utilisateur :
  les trois niveaux et que faire pour chacun
- 🌐 **[Exposer en toute sécurité](service_exposure.md)** — Tailscale, d'un VPN privé à une adresse
  HTTPS publique
- 🐳 **[Docker avancé](docker_advanced.md)** — Fichier Compose, variables d'environnement, proxy
  inverse
- 📝 **[Configuration](configuration.md)** — `SESSION_COOKIE_SECURE` et toutes les autres options de
  `.env`
