# 🔐 Sécurité de la connexion

L'indicateur de sécurité de la connexion, dans la barre latérale de LibreFolio, vous dit si ce que
vous saisissez — votre mot de passe, vos montants — circule chiffré entre votre appareil et votre
serveur. Il affiche l'un de trois niveaux, **sécurisée**, **réseau local** ou **non sécurisée**,
selon l'adresse que vous avez ouverte et le réseau sur lequel vous êtes.

Pour une sécurité maximale, donnez à LibreFolio une adresse HTTPS et utilisez-la partout, même sur
votre réseau domestique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="L'indicateur de sécurité de la connexion en bas de la barre latérale, ouvert sur Connexion : réseau local : sa raison, à savoir que toute personne sur le même réseau peut lire le trafic, et le lien Comment se connecter en toute sécurité" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 Les trois niveaux

### 🟢 Connexion : sécurisée {: #connection-secure }

Ce que vous saisissez est chiffré, ou ne quitte jamais le serveur.

<div class="lf-pros-cons" markdown>

| ✅ Avantage | ⚠️ Inconvénient |
|:--|:--|
| Personne sur le trajet ne peut le lire ni le modifier, même sur un Wi-Fi public. | Aucun, du point de vue du risque. |

</div>

!!! warning "📱 Tailscale en HTTP en clair et l'application"

    Via Tailscale avec une adresse en simple `http://`, comme `http://100.110.x.x:6040`, votre
    navigateur n'[installera pas LibreFolio comme application](pwa.md). C'est pourquoi une adresse
    HTTPS reste préférable : du point de vue du risque, les deux se valent, car Tailscale chiffre
    aussi le trafic.

👉 **Que faire :** rien, continuez à utiliser cette adresse. Pour l'application, passez à une
[adresse HTTPS](#https-address).

??? info "🔍 Quand une connexion est sécurisée"

    Les détails donnent l'une de trois raisons :

    - **HTTPS** : toute adresse `https://`. Votre navigateur décide seul, quoi que voie le serveur.
    - **Sur le serveur lui-même** : `localhost`, les noms qui se terminent par `.localhost` et les
      adresses de bouclage comme `127.0.0.1` et `::1`. Votre navigateur décide seul : le trafic ne
      quitte pas cet ordinateur.
    - **VPN (Tailscale)** : une adresse en simple `http://` dans les plages de Tailscale,
      `100.64.0.0/10` et `fd7a:115c:a1e0::/48`, ou un nom qui se termine par `.ts.net`. Tailscale
      chiffre le trafic entre votre appareil et le serveur. Si le serveur voit au contraire la
      requête arriver d'Internet, le niveau est [réseau local](#connection-local-network), comme
      incertain.

### 🏠 Connexion : réseau local {: #connection-local-network }

Vous avez ouvert LibreFolio en simple `http://` à l'intérieur de votre réseau domestique ou
professionnel, par exemple à `http://192.168.1.100:6040`, l'adresse qu'utilisent les autres
appareils après une [installation](installation.md) standard.

<div class="lf-pros-cons" markdown>

| 🤷 Vous vous contentez de | ⚠️ Inconvénient |
|:--|:--|
| Une connexion qui ne demande aucune configuration, et dont le trafic reste à l'intérieur de votre réseau. | Rien n'est chiffré : toute personne sur le même réseau, comme un invité sur votre Wi-Fi, pourrait lire le trafic, mot de passe compris. |

</div>

👉 **Que faire :** utilisez l'[adresse HTTPS](#https-address) à la maison aussi.

Le même niveau apparaît avec une raison commençant par *Incertaine* quand LibreFolio ne peut pas
savoir où vous êtes vraiment : le conseil ne change pas.

??? info "🔍 Quand une connexion est en réseau local"

    **Une adresse locale en simple `http://`** : une adresse en `10.x`, de `172.16.x` à `172.31.x`,
    en `192.168.x` ou en `169.254.x`, une adresse IPv6 de lien local ou locale unique, ou un nom qui
    se termine par `.local`, `.lan`, `.home.arpa` ou `.internal`, ou sans aucun point, comme
    `http://nas:6040`. Un nom MagicDNS court de Tailscale, comme `http://my-server:6040`, n'a pas
    de point non plus, il compte donc ici : l'IP Tailscale ou le nom complet qui se termine par
    `.ts.net` compte comme [sécurisé](#connection-secure).

    **Incertaine** : votre navigateur juge l'adresse que vous avez ouverte, puis le serveur indique
    d'où il voit arriver la requête, seulement le type d'adresse et jamais votre adresse IP. Le
    serveur peut confirmer le verdict du navigateur ou le rendre incertain, mais jamais faire
    compter une connexion comme sécurisée ; tant qu'il ne répond pas, le verdict du navigateur
    tient. Quand les deux ne concordent pas, le niveau est réseau local et la raison commence par
    *Incertaine* :

    - une adresse qui semble publique, que le serveur voit arriver de votre réseau local, de
      Tailscale ou du serveur lui-même, par exemple via un split DNS ou un proxy local ;
    - une adresse locale ou Tailscale que le serveur voit arriver d'Internet.

    Le trafic n'est pas chiffré, et LibreFolio ne peut pas savoir où vous êtes vraiment.

### 🔴 Connexion : non sécurisée {: #connection-not-secure }

Vous avez atteint LibreFolio en simple `http://` depuis Internet, par exemple via un port ouvert sur
votre routeur. Sur un téléphone, un point rouge sur le bouton du menu vous avertit même quand la
barre latérale est fermée.

<div class="lf-pros-cons" markdown>

| ✅ Avantage | ⚠️ Inconvénient |
|:--|:--|
| Aucun. | Les mots de passe et les données circulent en clair sur des réseaux que vous ne contrôlez pas : n'importe qui sur le trajet pourrait les lire, voire les modifier. |

</div>

👉 **Que faire :** évitez cette adresse. Si vous gérez le serveur, donnez à LibreFolio une
[adresse HTTPS](#https-address) et cessez d'exposer le HTTP en clair. Changez ensuite votre mot de
passe : **Paramètres** → [**Profil**](settings/profile.md) → **Changer le mot de passe**. Cela déconnecte aussi
tous les autres appareils connectés à votre compte.

??? info "🔍 Quand une connexion n'est pas sécurisée"

    **Une adresse publique en simple `http://`** : une adresse ou un nom qui n'est ni local, ni
    Tailscale, ni le serveur lui-même, comme une IP publique ou un nom de domaine comme
    `http://myhome.duckdns.org:6040`. Le niveau tient quand le serveur voit lui aussi la requête
    arriver d'Internet, ou ne peut pas le dire. S'il la voit arriver de votre réseau local, de
    Tailscale ou du serveur lui-même, le niveau est [réseau local](#connection-local-network), comme
    incertain.

---

## 🔒 Comment se connecter en toute sécurité {: #https-address }

Donnez à LibreFolio une adresse HTTPS, puis n'utilisez plus que celle-ci. La personne qui gère le
serveur la met en place, de l'une de ces deux façons :

- **Tailscale**, sans ouvrir de port sur votre routeur : Tailscale Serve donne une adresse HTTPS
  aux appareils de votre tailnet, et Funnel une adresse publique qui ne demande pas Tailscale sur
  vos appareils. Voir [Exposer en toute sécurité](../admin/service_exposure.md).
- **Un proxy inverse** avec un certificat TLS, comme Caddy, Traefik ou Nginx : voir
  [Docker avancé](../admin/docker_advanced.md).

Suivez ensuite quelques bonnes habitudes :

- utilisez l'adresse `https://` sur chaque appareil, à la maison aussi ;
- mettez-la en favori, et mettez à jour les anciens favoris et les raccourcis de l'écran d'accueil
  qui pointent encore vers `http://` ;
- si vous ne gérez pas le serveur, demandez l'adresse à la personne qui le gère ;
- regardez l'indicateur : il doit afficher **Connexion : sécurisée**.

Si vous gérez le serveur, [Vérifier la sécurité de la connexion](../admin/connection_checks.md)
montre comment contrôler le résultat.

---

## 🧭 Ce que l'indicateur ne fait pas

L'indicateur décrit la connexion que vous utilisez à l'instant, et vous conseille. Trois choses
échappent à son rôle.

**Il ne bloque rien.** C'est un conseil, pas un contrôle. Et comme il décrit la connexion de
l'appareil que vous utilisez, le même LibreFolio peut afficher **Connexion : sécurisée** sur votre
ordinateur portable et **Connexion : non sécurisée** sur votre téléphone.

**Il ne vérifie pas les certificats.** Un certificat auto-signé que vous avez accepté dans le
navigateur affiche **Connexion : sécurisée**. Le trafic est chiffré, mais personne ne garantit que
le serveur est bien le vôtre.

**Il ne voit pas toujours où vous êtes.** Quand LibreFolio tourne dans Docker Desktop et est exposé
directement, ou se trouve derrière un proxy qui ne transmet pas votre adresse dans
`X-Forwarded-For`, le serveur voit chaque visiteur comme local. Le HTTP en clair depuis Internet
affiche alors **Connexion : réseau local**, comme incertaine, au lieu de
**Connexion : non sécurisée**. Docker Engine sous Linux conserve votre adresse.

Quoi qu'affiche l'indicateur, le conseil reste le même : utilisez l'adresse HTTPS.

---

## 🔗 Voir aussi

- 🌐 **[Exposer en toute sécurité](../admin/service_exposure.md)** — Tailscale, d'un VPN privé à une
  adresse HTTPS publique
- 🔍 **[Vérifier la sécurité de la connexion](../admin/connection_checks.md)** — Pour les
  administrateurs : l'adresse HTTPS, le cookie de session et le proxy inverse
- 🐳 **[Docker avancé](../admin/docker_advanced.md)** — Fichier Compose, variables d'environnement,
  proxy inverse
- 📝 **[Configuration](../admin/configuration.md)** — Toutes les options du fichier `.env`
- 📦 **[Installation avec Docker](installation.md)** — Accès local et distant après l'installation
- 📱 **[Installer en tant qu'application (PWA)](pwa.md)** — Nécessite une adresse HTTPS
