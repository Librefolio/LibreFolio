# 🔐 Sécurité de la connexion

L'indicateur de sécurité de la connexion dans la barre latérale de LibreFolio vous indique si ce que vous saisissez — votre mot de passe, vos chiffres — circule chiffré entre votre appareil et votre serveur. Il affiche l'un des trois niveaux, selon l'adresse que vous avez ouverte et le réseau sur lequel vous vous trouvez. Cliquez sur sa ligne pour ouvrir ou fermer ses détails : la raison du niveau et le lien **Comment se connecter en toute sécurité**, qui ouvre cette page.
Lorsque la barre latérale est repliée, le bouclier affiche le niveau lorsque vous le survolez, et un clic ouvre la barre latérale avec les détails.

Pour une sécurité maximale, donnez à LibreFolio une adresse HTTPS et utilisez-la partout, même sur votre réseau domestique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="L'indicateur de sécurité de la connexion en bas de la barre latérale, ouvert sur Connexion : réseau local : sa raison, à savoir que toute personne sur le même réseau peut lire le trafic, et le lien Comment se connecter en toute sécurité" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 Les trois niveaux

### 🟢 Connexion : sécurisée {: #connection-secure }

Vert : ce que vous saisissez est chiffré, ou ne quitte jamais le serveur. Les détails donnent la raison :

- HTTPS : la connexion est chiffrée, et votre navigateur la considère comme sécurisée.
- Sur le serveur lui-même (`localhost`) : le trafic ne quitte pas cet ordinateur.
- VPN (Tailscale) : Tailscale chiffre le trafic entre votre appareil et le serveur, même si
  l'adresse commence par `http://`, par exemple `http://100.110.x.x:6040`.

Avec la raison VPN, l'adresse reste en simple `http://`, donc votre navigateur ne pourra pas
[installer LibreFolio en tant qu'application](pwa.md) à partir de celle-ci : [l'étape 1](#https-address) ajoute HTTPS.

### 🏠 Connexion : réseau local {: #connection-local-network }

Vert clair : vous avez ouvert LibreFolio en simple `http://` à l'intérieur de votre réseau domestique ou professionnel, par
exemple `http://192.168.1.100:6040`, l'adresse que les autres appareils utilisent après une
[installation](installation.md) standard. Le trafic n'est pas chiffré : toute personne sur le même réseau, comme
un invité sur votre Wi-Fi, pourrait le lire, mot de passe inclus. Pour une sécurité optimale, utilisez aussi l'adresse HTTPS
à la maison.

**Connexion : réseau local** apparaît également, avec une raison commençant par *Incertain* dans les détails, lorsque
l'adresse que vous avez ouverte et la source que le serveur voit ne concordent pas : une adresse d'apparence publique que le
serveur voit provenir de votre réseau local (DNS scindé, ou un proxy local), ou une adresse locale ou Tailscale
que le serveur voit provenir d'Internet. Le trafic n'est pas chiffré, et
LibreFolio ne peut pas déterminer où vous vous trouvez réellement : utilisez l'adresse HTTPS.

### 🔴 Connexion : non sécurisée {: #connection-not-secure }

Rouge : vous avez atteint LibreFolio en simple `http://` depuis Internet, par exemple via un port
ouvert sur votre routeur. Les mots de passe et les données circulent en clair sur des réseaux que vous ne contrôlez pas :
toute personne sur le chemin pourrait les lire, ou même les modifier. Sur un téléphone, un point rouge sur le bouton du menu
vous avertit même lorsque la barre latérale est fermée.

Évitez cette adresse. Si vous exploitez le serveur, donnez à LibreFolio une adresse HTTPS
([l'étape 1](#https-address)) et cessez d'exposer du HTTP en clair. Ensuite, changez votre mot de passe :
**Paramètres** → [**Profil**](settings/profile.md) → **Changer le mot de passe**.

??? info "🔍 Comment le niveau est choisi"

    Votre navigateur classe l'adresse que vous avez saisie dans l'une des quatre catégories :

    - cet ordinateur : `localhost` et les adresses de bouclage ;
    - Tailscale : `100.64.0.0/10`, `fd7a:115c:a1e0::/48` et les noms se terminant par `.ts.net` ;
    - réseau local : les adresses `10.x`, `172.16.x` à `172.31.x`, `192.168.x` et `169.254.x`, les adresses IPv6
      link-local et locales uniques, et les noms se terminant par `.local`, `.lan`, `.home.arpa` ou
      `.internal`, ou sans aucun point ;
    - Internet : tout le reste.

    HTTPS est toujours sécurisé. Le HTTP en clair est considéré comme sécurisé pour `localhost`, et pour une adresse Tailscale
    sauf si le serveur voit la requête provenir d'Internet.

    Le serveur classe l'adresse d'où provient chaque requête dans les mêmes catégories et ne rapporte que la
    catégorie, jamais votre adresse IP. Il peut confirmer le verdict du navigateur ou le rendre incertain, mais
    jamais faire qu'une connexion soit considérée comme sécurisée. Tant qu'il n'a pas répondu, le verdict du navigateur prévaut.

---

## 🔒 Comment se connecter en toute sécurité

### 🌐 1. Donnez à LibreFolio une adresse HTTPS {: #https-address }

C'est le travail de la personne qui exploite le serveur : si ce n'est pas vous, demandez-lui l'adresse HTTPS. Deux
façons :

- Tailscale : suivez [Exposer en toute sécurité](../admin/service_exposure.md). Avec son niveau 1 (VPN privé) en place, exécutez `tailscale serve --bg 6040` sur le serveur (ou votre propre `PORT`), puis ouvrez
  `https://<server-name>.your-tailnet.ts.net`. Pour une adresse HTTPS publique qui ne nécessite pas Tailscale
  sur vos appareils, utilisez Funnel (niveaux 3 et 4).
- Un proxy inverse avec un certificat TLS, tel que Caddy, Traefik ou Nginx : voir
  [Docker avancé](../admin/docker_advanced.md).

Tailscale, Caddy et Traefik indiquent à LibreFolio que la connexion est en HTTPS, de leur propre chef ; Nginx a besoin de deux lignes : voir
[Derrière un proxy inverse](#reverse-proxy).

### 🔖 2. Utilisez l'adresse HTTPS partout

Utilisez-la sur chaque appareil, à la maison aussi :

- Mettez `https://…` en favori, pas `http://192.168.x.x:6040`.
- Mettez à jour les anciens favoris et raccourcis d'écran d'accueil qui pointent encore vers `http://`.
- Ouvrez LibreFolio depuis la nouvelle adresse : l'indicateur affiche **Connexion : sécurisée**.

---

## 🧰 Derrière un proxy inverse {: #reverse-proxy }

*Pour les administrateurs.* Un proxy inverse reçoit la connexion HTTPS et la transmet à LibreFolio
en simple HTTP. Ce qui compte ici, c'est le cookie de session qui vous maintient connecté : avec
`SESSION_COOKIE_SECURE=auto`, la valeur par défaut, LibreFolio le marque `Secure` (envoyé uniquement via HTTPS) lorsque
la requête est en HTTPS, soit directement, soit parce que le proxy envoie `X-Forwarded-Proto: https`.

Tailscale Serve et Funnel, Caddy et Traefik envoient cet en-tête de leur propre chef. Caddy et Traefik transmettent aussi
votre adresse dans `X-Forwarded-For`, ce qui permet à l'indicateur de voir d'où vous vous connectez. Nginx
a besoin des deux lignes dans le bloc `location` qui transmet les requêtes à LibreFolio :

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Si votre navigateur utilise HTTPS mais que le cookie de session n'est pas marqué `Secure`, parce que le proxy n'envoie pas
`X-Forwarded-Proto` ou parce que `SESSION_COOKIE_SECURE` vaut `never`, les administrateurs voient une ligne supplémentaire
dans les détails de l'indicateur. Le niveau reste **Connexion : sécurisée**, car la connexion est
chiffrée ; seul le cookie n'a pas `Secure` :

> Votre navigateur utilise HTTPS, mais le cookie de session n'est pas marqué Secure. Faites en sorte que le proxy inverse envoie
> X-Forwarded-Proto (Nginx : `proxy_set_header X-Forwarded-Proto $scheme;`), ou remettez
> SESSION_COOKIE_SECURE sur auto s'il vaut never.

??? tip "⚙️ Définir plutôt `SESSION_COOKIE_SECURE`"

    Envoyer l'en-tête est la meilleure solution. Si vous n'atteignez LibreFolio que via HTTPS, vous pouvez
    plutôt ajouter cette ligne à `.env` :

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Redémarrez ensuite LibreFolio : avec Docker, exécutez `docker compose up -d` (un simple
    `docker compose restart` conserve l'ancien environnement) ; sur une installation sur l'hôte, redémarrez
    `./dev.py server`, qui lit aussi `.env`.

    L'option accepte `auto` (la valeur par défaut), `always` ou `never` ; la casse et les espaces n'ont pas d'importance, et
    toute autre valeur arrête LibreFolio au démarrage. N'utilisez `never` que pour le rare proxy qui prétend
    être en HTTPS alors que le navigateur est en simple HTTP. Voir [Configuration](../admin/configuration.md) pour
    toutes les options.

---

## 🧭 Ce que l'indicateur ne fait pas

- Il ne bloque rien : c'est un conseil, pas un contrôle.
- Il décrit la connexion que vous utilisez à l'instant présent : le même LibreFolio peut afficher
  **Connexion : sécurisée** sur votre ordinateur portable et **Connexion : non sécurisée** sur votre téléphone.
- Il ne vérifie pas les certificats : un certificat auto-signé que vous avez accepté dans le navigateur affiche
  **Connexion : sécurisée**. Le trafic est chiffré, mais personne ne garantit que le serveur est bien le vôtre.
- Il ne peut pas toujours voir où vous êtes. Avec Docker Desktop exposé directement, ou derrière un proxy qui
  ne transmet pas votre adresse dans `X-Forwarded-For`, le serveur voit chaque visiteur comme local : du HTTP en clair
  depuis Internet affiche alors **Connexion : réseau local**, comme incertain, au lieu de
  **Connexion : non sécurisée**. Docker Engine sous Linux conserve votre adresse. Le conseil ne
  change pas : utilisez l'adresse HTTPS.

---

## 🔗 Voir aussi

- 🌐 **[Exposer en toute sécurité](../admin/service_exposure.md)** — Tailscale, d'un VPN privé à une
  adresse HTTPS publique
- 🐳 **[Docker avancé](../admin/docker_advanced.md)** — Fichier Compose, variables d'environnement,
  proxy inverse
- 📝 **[Configuration](../admin/configuration.md)** — Toutes les options du fichier `.env`
- 📦 **[Installation avec Docker](installation.md)** — Accès local et distant après l'installation
- 📱 **[Installer en tant qu'application (PWA)](pwa.md)** — Nécessite une adresse HTTPS
