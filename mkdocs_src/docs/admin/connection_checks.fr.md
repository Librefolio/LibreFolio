# 🔍 Vérification de la sécurité de la connexion

Chaque utilisateur voit, en bas de la barre latérale de LibreFolio, avec quel niveau de sécurité son navigateur communique avec le serveur : **Connexion : sécurisée**, **Connexion : réseau local** ou **Connexion : non sécurisée**. Le guide utilisateur, [Sécurité de la connexion](../user/connection-security.md), leur explique les trois niveaux. Cette page s'adresse à ceux qui administrent le serveur : comment vérifier que votre déploiement offre à ses utilisateurs **Connexion : sécurisée**, et comment y remédier dans le cas contraire.

L'objectif est une adresse HTTPS, fournie par Tailscale Serve ou Funnel
([Exposition sécurisée](service_exposure.md)) ou par un proxy inverse doté d'un certificat
([Derrière un proxy inverse](connection_proxy.md#reverse-proxy)), ainsi qu'un cookie de session marqué `Secure`.

!!! info "📚 Ce guide est réparti sur plusieurs pages"

    Cette page est la liste de vérification : ce qu'affiche l'indicateur, comment consulter le point de vue du serveur et le cookie de session, et que faire lorsqu'une vérification échoue. Si vous exécutez LibreFolio derrière un proxy inverse, [Vérification de la sécurité de la connexion : derrière un proxy inverse](connection_proxy.md) explique les en-têtes qu'il doit envoyer et comment LibreFolio prend connaissance de l'adresse du visiteur.

---

## ✅ Liste de vérification {: #checklist }

Parcourez-la une fois que votre adresse HTTPS fonctionne, puis de nouveau après toute modification du proxy ou du fichier `.env`.
Vous avez besoin d'un compte administrateur et, pour les deux dernières vérifications, d'un téléphone en données mobiles.

1. **Ouvrez l'adresse HTTPS et connectez-vous.** L'indicateur affiche 🟢 **Connexion : sécurisée**, et ses
   détails indiquent que la connexion est chiffrée en HTTPS.
2. **Cherchez la ligne relative au cookie.** Une fois connecté en tant qu'administrateur, les détails affichent cette raison et le
   lien **Comment se connecter en toute sécurité**, ainsi que, lorsque les [contrôles de sécurité](settings.md#security-tab) signalent
   des erreurs ou des avertissements, un lien vers ceux-ci, par exemple **2 avertissements de sécurité**. Une ligne supplémentaire, concernant le
   cookie de session, signifie que LibreFolio ne sait pas que la connexion est en HTTPS : voir
   [Derrière un proxy inverse](connection_proxy.md#reverse-proxy).
3. **Interrogez le serveur.** Dans un nouvel onglet, ouvrez `https://<your address>/api/v1/system/connection` : la
   réponse contient `"cookie_secure":true` ([Le point de vue du serveur](#server-view)).
4. **Examinez le cookie.** Dans les outils de développement du navigateur, le cookie `session` est
   marqué `Secure` ([Le cookie de session](#session-cookie)).
5. **Depuis l'extérieur, ouvrez l'adresse HTTPS.** Sur le téléphone, avec le Wi-Fi désactivé, la page se charge et, une fois
   connecté, l'indicateur affiche 🟢 **Connexion : sécurisée**. Laissez Tailscale désactivé sur le téléphone pour une
   adresse Funnel ou de proxy inverse ; activez-le pour une adresse Tailscale Serve, que seul votre
   tailnet peut ouvrir.
6. **Depuis l'extérieur, essayez le HTTP simple.** Sur le même téléphone, `http://<your public IP or name>:6040`, ou
   votre propre `PORT`, ne se charge pas. Si la page de connexion apparaît, le HTTP simple est ouvert à l'internet :
   ne vous y connectez pas, car le mot de passe circulerait en clair, et fermez le port
   ([Lorsqu'une vérification échoue](#when-a-check-fails)). Quiconque se connecte via cette adresse voit
   🔴 **Connexion : non sécurisée**, ou 🏠 **Connexion : réseau local** avec une raison *Incertaine* lorsque
   le serveur ne peut pas voir d'où viennent les visiteurs ([Limites](#limits)).

Toutes les vérifications ont-elles réussi ? Demandez à vos utilisateurs d'utiliser l'adresse HTTPS sur chaque appareil et de mettre à jour leurs anciens
signets ([Comment se connecter en toute sécurité](../user/connection-security.md#https-address)).

!!! note "📶 Pas encore d'adresse HTTPS ?"

    Aux niveaux 1 ou 2 d'[Exposition sécurisée](service_exposure.md), les utilisateurs atteignent LibreFolio en HTTP
    simple. Vérifiez le niveau obtenu par chaque adresse ([Ce qu'affiche l'indicateur](#indicator)) et que le HTTP
    simple ne se charge pas depuis l'extérieur (vérification 6). Les vérifications du cookie ne s'appliquent pas : en HTTP simple, le
    cookie de session n'est pas `Secure`, et `"cookie_secure":false` est attendu.

---

## 🚦 Ce qu'affiche l'indicateur {: #indicator }

Le navigateur juge l'adresse qu'il a ouverte ; le serveur indique ensuite d'où il voit venir la requête, et peut confirmer ce verdict ou le rendre incertain, mais ne peut jamais le rendre sécurisé. Ce que voient vos utilisateurs selon la manière dont ils atteignent LibreFolio :

| Comment les utilisateurs atteignent LibreFolio | Exemple | Niveau |
| --- | --- | --- |
| Tailscale Serve ou Funnel, ou un proxy inverse avec un certificat | `https://librefolio.your-tailnet.ts.net` | 🟢 **sécurisée** : HTTPS |
| Sur le serveur lui-même | `http://localhost:6040` | 🟢 **sécurisée** : `localhost` |
| IP Tailscale ou nom MagicDNS complet, HTTP simple (niveau 1) | `http://100.a.b.c:6040` | 🟢 **sécurisée** : VPN (Tailscale) |
| Nom MagicDNS court, HTTP simple : un nom sans point compte comme local | `http://your-server:6040` | 🏠 **réseau local** |
| Adresse locale, y compris via un routeur de sous-réseau (niveau 2) | `http://192.168.1.100:6040` | 🏠 **réseau local** |
| Un port ouvert sur le routeur, HTTP simple | `http://myhome.duckdns.org:6040` | 🔴 **non sécurisée** |

Lorsque le serveur ne peut pas voir les adresses de vos visiteurs, la dernière ligne affiche 🏠 **réseau local** avec
une raison *Incertaine* à la place ([Limites](#limits)). Le guide utilisateur donne les règles exactes de chaque
niveau : plages d'adresses, noms et cas *Incertains*
([Sécurité de la connexion](../user/connection-security.md#connection-secure)).

---

## 🔎 Le point de vue du serveur {: #server-view }

L'indicateur demande au serveur comment il voit la connexion, une fois par chargement de page :
`GET /api/v1/system/connection`. Vous pouvez lire la même réponse : une fois connecté, ouvrez cette adresse dans un
nouvel onglet du même navigateur, en remplaçant l'adresse de l'exemple par celle de votre propre LibreFolio :

```text
https://librefolio.your-tailnet.ts.net/api/v1/system/connection
```

Le navigateur affiche une réponse sur une seule ligne, par exemple :

```json
{"client_class":"public","cookie_secure":true}
```

Tout compte fonctionne, pas seulement un administrateur. Une réponse telle que `{"detail":"Not authenticated"}`
signifie qu'il n'y a pas de session à cette adresse : les sessions appartiennent à une adresse, donc se connecter à
`http://192.168.1.100:6040` ne vous connecte pas à l'adresse HTTPS. Et comme l'indicateur n'interroge
qu'une fois par chargement de page, rechargez LibreFolio après une modification pour voir son nouveau verdict.

**`cookie_secure`** indique si un cookie de session défini lors de cette requête serait `Secure`, selon
[`SESSION_COOKIE_SECURE`](#session-cookie). Sur l'adresse HTTPS, il doit être `true` : c'est la valeur `false` qui
fait apparaître la ligne administrateur à propos du cookie ([Derrière un proxy inverse](connection_proxy.md#reverse-proxy)). En HTTP
simple, `false` est attendu.

**`client_class`** indique d'où le serveur voit venir la requête. Il lit la dernière
valeur de `X-Forwarded-For`, celle ajoutée par le proxy le plus proche, lorsqu'il s'agit d'une adresse IP, et sinon
l'adresse de la connexion elle-même. Seule la classe quitte le serveur : l'adresse n'est jamais
renvoyée ni journalisée.

| `client_class` | La requête provient de |
| --- | --- |
| `loopback` | Du serveur lui-même : `127.0.0.0/8` ou `::1` |
| `vpn` | De Tailscale ou Headscale : `100.64.0.0/10` ou `fd7a:115c:a1e0::/48` |
| `lan` | D'un réseau local : `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` ou `fc00::/7` |
| `public` | De toute autre adresse : l'internet |
| `unknown` | Aucune adresse, ou une adresse illisible |

La classe n'est prise en compte qu'en HTTP simple, et pas sur le serveur lui-même (`localhost`) :

- avec une adresse publique dans le navigateur, `public` ou `unknown` confirme **Connexion : non sécurisée**,
  tandis que `loopback`, `vpn` ou `lan` la transforment en **Connexion : réseau local**, comme étant incertaine ;
- avec une adresse locale ou Tailscale dans le navigateur, `public` rend le verdict incertain, et toute autre
  classe le laisse tel quel.

Sur l'adresse HTTPS, la classe ne change rien, mais elle vous indique si le serveur peut voir les
adresses de vos visiteurs : depuis le téléphone en données mobiles, Tailscale désactivé, `public` signifie qu'il le peut, et
`lan` ou `loopback` signifient qu'il ne le peut pas ([Limites](#limits)).

---

## 🍪 Le cookie de session {: #session-cookie }

Le cookie qui maintient un utilisateur connecté s'appelle `session`. LibreFolio le définit à la connexion, toujours
`HttpOnly`, afin que les scripts de la page ne puissent pas le lire, et `SameSite=Lax`. Le fait qu'il soit également `Secure`,
donc envoyé uniquement en HTTPS, dépend de `SESSION_COOKIE_SECURE` dans `.env` :

- **`auto`**, la valeur par défaut : `Secure` lorsque la requête est en HTTPS, soit directement, soit parce que la première
  valeur de `X-Forwarded-Proto` envoyée par un proxy inverse est `https` ;
- **`always`** : toujours `Secure` ;
- **`never`** : jamais `Secure`.

La casse et les espaces autour de la valeur n'ont pas d'importance ; toute autre valeur empêche LibreFolio de démarrer. Pour savoir quand
`always` ou `never` est le bon choix : [Configuration](configuration.md#session-cookie-secure).

L'attribut est décidé à la connexion : le cookie qu'un navigateur détient déjà conserve l'attribut reçu à ce moment-là. Après
avoir corrigé le proxy ou l'option, déconnectez-vous et reconnectez-vous.

Pour voir l'attribut dans le navigateur :

1. Connectez-vous à l'adresse HTTPS.
2. Ouvrez les outils de développement : `F12`, ou faites un clic droit sur la page et choisissez **Inspecter**. Safari ne les affiche
   qu'une fois ses fonctions de développement activées dans ses paramètres.
3. Ouvrez les cookies de votre adresse LibreFolio : **Application** → **Cookies** dans Chrome et Edge,
   **Stockage** → **Cookies** dans Firefox et Safari.
4. Sur la ligne `session`, **Secure** est coché (`true` dans Firefox), ainsi que **HttpOnly** ;
   **SameSite** affiche `Lax`.

La console ne peut pas l'afficher : `document.cookie` omet les cookies `HttpOnly`.

---

## 🛠️ Lorsqu'une vérification échoue {: #when-a-check-fails }

| Ce que vous voyez | Pourquoi | Que faire |
| --- | --- | --- |
| L'adresse HTTPS n'affiche pas **Connexion : sécurisée** | La page n'est pas en HTTPS : la barre d'adresse affiche `http://` | Ouvrez l'adresse `https://`, et faites rediriger `http://` vers celle-ci par le proxy |
| La ligne à propos du cookie de session, ou `"cookie_secure":false` sur l'adresse HTTPS | Le proxy n'envoie pas `X-Forwarded-Proto: https`, ou `SESSION_COOKIE_SECURE` vaut `never` | Corrigez le proxy ([Derrière un proxy inverse](connection_proxy.md#reverse-proxy)) ou remettez l'option sur `auto`, puis rechargez |
| `"cookie_secure":true`, mais le cookie `session` n'est pas `Secure` | Le cookie a été défini avant la correction | Déconnectez-vous et reconnectez-vous |
| `{"detail":"Not authenticated"}` | Aucune session à cette adresse | Connectez-vous à cette adresse, dans le même navigateur |
| Chaque tentative de connexion renvoie à nouveau à la page de connexion | Le cookie est `Secure`, mais le navigateur utilise le HTTP simple : `SESSION_COOKIE_SECURE=always`, ou un proxy qui envoie `X-Forwarded-Proto: https` à un navigateur en HTTP simple | Utilisez l'adresse HTTPS, ou corrigez le proxy : voir [Configuration](configuration.md#session-cookie-secure) |
| Depuis l'extérieur, l'adresse HTTPS ne se charge pas | Une adresse Tailscale Serve est privée ; un nouveau Funnel nécessite une approbation et quelques minutes | Activez Tailscale sur le téléphone, ou utilisez Funnel ; approuvez le Funnel et attendez ([Exposition sécurisée : accès public avec Funnel](service_exposure_funnel.md#step-2-approve-and-wait-for-propagation)) |
| Depuis l'extérieur, le HTTP simple `http://…:6040` se charge | Le port de LibreFolio est ouvert à l'internet : une redirection de port sur le routeur, ou un serveur avec une adresse publique | Fermez-le : supprimez la redirection de port, ou bloquez le port dans le pare-feu du serveur. Tailscale n'a besoin d'aucun port ouvert, et un proxy inverse uniquement du sien |
| `client_class` renvoie `lan` ou `loopback` depuis les données mobiles, ou bien le HTTP simple depuis l'internet affiche **Connexion : réseau local**, *Incertaine* | Le serveur ne peut pas voir d'où viennent les visiteurs | Voir [Limites](#limits) ; avec Nginx, ajoutez la ligne `X-Forwarded-For` |
| Une adresse Tailscale affiche **Connexion : réseau local** | Un nom MagicDNS court n'a pas de point, il compte donc comme local | Utilisez l'IP Tailscale, le nom `.ts.net` complet ou, mieux, l'adresse HTTPS |

---

## ⚠️ Limites {: #limits }

L'indicateur est un conseil, pas un contrôle : il ne bloque rien. Deux limites importent lorsque vous vérifiez un
déploiement.

**Il ne peut pas toujours voir d'où viennent les visiteurs.** Avec Docker Desktop exposé directement, ou derrière un
proxy qui ne transmet pas l'adresse du visiteur dans `X-Forwarded-For`, le serveur voit chaque visiteur
comme local : `lan`, ou `loopback` pour un proxy sur la même machine. Le HTTP simple depuis l'internet affiche alors
**Connexion : réseau local**, comme étant incertaine, au lieu de **Connexion : non sécurisée**. Les adresses HTTPS
ne sont pas concernées : elles affichent **Connexion : sécurisée** dans les deux cas. Docker Engine sous Linux
conserve l'adresse du visiteur en IPv4 ; en IPv6, à moins que le conteneur ne dispose de sa propre adresse IPv6,
les visiteurs IPv6 arrivent via le proxy de Docker, depuis la passerelle du réseau du conteneur, si bien que
tous partagent cette même adresse locale, tant pour l'indicateur que pour les limites par adresse de visiteur,
qui les comptent alors ensemble. Le proxy de Docker n'ajoute aucun en-tête de transfert, si bien que LibreFolio
ne peut pas le détecter : son avertissement concernant un proxy non fiable nécessite un tel en-tête. Un proxy inverse en amont
qui voit l'adresse propre à chaque visiteur, configuré comme l'explique [L'adresse du visiteur](connection_proxy.md#client-address),
l'évite.

**Il ne vérifie pas les certificats.** Un certificat auto-signé qu'un utilisateur a accepté dans le navigateur
affiche **Connexion : sécurisée** : le trafic est chiffré, mais personne ne garantit que le serveur est bien
le vôtre.

Ni l'indicateur ni le cookie de session n'ont besoin d'une liste de proxys de confiance : un
`X-Forwarded-For` falsifié n'égare que l'indicateur de celui qui l'a envoyé, et comme `X-Forwarded-Proto` ne peut
qu'activer `Secure`, un `https` falsifié n'affecte que la connexion de l'expéditeur lui-même. Les limites par
adresse de visiteur sont une autre affaire : voir [L'adresse du visiteur](connection_proxy.md#client-address).

---

## 🔗 Voir aussi

- 📄 **[Vérification de la sécurité de la connexion : derrière un proxy inverse](connection_proxy.md)** — Quels proxys LibreFolio considère comme fiables, l'adresse du visiteur, Tailscale avec Docker
- 🔐 **[Sécurité de la connexion](../user/connection-security.md)** — Le guide utilisateur : les trois niveaux
  et quoi faire à chaque niveau
- 🌐 **[Exposition sécurisée](service_exposure.md)** — Tailscale, d'un VPN privé à une adresse HTTPS
  publique
- 🐳 **[Docker avancé](docker_advanced.md)** — Fichier Compose, variables d'environnement, proxy inverse
- 📝 **[Configuration](configuration.md)** — `SESSION_COOKIE_SECURE` et toutes les autres options de `.env`
