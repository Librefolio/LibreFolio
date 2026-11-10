# 🔐 Sécurité de la connexion

L'indicateur de sécurité de la connexion dans la barre latérale de LibreFolio vous indique si ce que vous saisissez — votre mot de passe, vos chiffres — circule chiffré entre votre appareil et votre serveur. Il affiche l'un des trois niveaux, **sécurisé**, **réseau local** ou **non sécurisé**, selon l'adresse que vous avez ouverte et le réseau sur lequel vous vous trouvez. Les administrateurs y voient aussi quand les contrôles de sécurité de l'instance nécessitent leur attention : voir [Avertissements de sécurité pour les administrateurs](#security-warnings).

Pour une sécurité maximale, attribuez à LibreFolio une adresse HTTPS et utilisez-la partout, même sur votre réseau domestique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="L'indicateur de sécurité de la connexion en bas de la barre latérale, ouvert sur Connexion : réseau local : sa raison, le fait que toute personne sur le même réseau peut lire le trafic, et le lien Comment se connecter en toute sécurité" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 Les trois niveaux

### 🟢 Connexion : sécurisée {: #connection-secure }

Ce que vous saisissez est chiffré, ou ne quitte jamais le serveur.

<div class="lf-pros-cons" markdown>

| ✅ Avantage | ⚠️ Inconvénient |
|:--|:--|
| Personne en chemin ne peut le lire ou le modifier, pas même sur un Wi-Fi public. | Rien, du point de vue du risque. |

</div>

!!! warning "📱 Tailscale via HTTP en clair et l'application"

    Via Tailscale avec une adresse `http://` en clair, comme `http://100.110.x.x:6040`, votre navigateur ne [installera pas LibreFolio comme application](pwa.md). C'est pourquoi une adresse HTTPS reste préférable : en termes de risque, les deux sont identiques, puisque Tailscale chiffre aussi le trafic.

👉 **Que faire :** rien, continuez d'utiliser cette adresse. Pour l'application, passez à une [adresse HTTPS](#https-address).

??? info "🔍 Quand une connexion est considérée comme sécurisée"

    Les détails donnent l'une des trois raisons :

    - **HTTPS** : toute adresse `https://`. Votre navigateur décide seul, indépendamment de ce que voit le serveur.
    - **Sur le serveur lui-même** : `localhost`, les noms se terminant par `.localhost`, et les adresses de bouclage comme `127.0.0.1` et `::1`. Votre navigateur décide seul : le trafic ne quitte pas cet ordinateur.
    - **VPN (Tailscale)** : une adresse `http://` en clair dans les plages de Tailscale, `100.64.0.0/10` et `fd7a:115c:a1e0::/48`, ou un nom se terminant par `.ts.net`. Tailscale chiffre le trafic entre votre appareil et le serveur. Si le serveur voit plutôt la requête venir d'Internet, le niveau est [réseau local](#connection-local-network), avec la raison *Incertain*.

### 🏠 Connexion : réseau local {: #connection-local-network }

Vous avez ouvert LibreFolio via une adresse `http://` en clair au sein de votre réseau domestique ou professionnel, par exemple à l'adresse `http://192.168.1.100:6040`, l'adresse qu'utilisent les autres appareils après une [installation](installation.md) standard.

<div class="lf-pros-cons" markdown>

| 🤷 Ce dont vous vous contentez | ⚠️ Inconvénient |
|:--|:--|
| Une connexion qui ne demande aucune configuration et dont le trafic reste à l'intérieur de votre réseau. | Rien n'est chiffré : toute personne sur le même réseau, comme un invité sur votre Wi-Fi, pourrait lire le trafic, mot de passe inclus. |

</div>

👉 **Que faire :** utilisez aussi l'[adresse HTTPS](#https-address) à la maison.

Le même niveau apparaît avec une raison commençant par *Incertain* lorsque LibreFolio ne peut pas déterminer où vous vous trouvez réellement : le conseil ne change pas.

??? info "🔍 Quand une connexion est considérée comme réseau local"

    **Une adresse locale utilisant `http://` en clair** : une adresse dans `10.x`, `172.16.x` à `172.31.x`, `192.168.x` ou `169.254.x`, une adresse IPv6 link-local ou locale unique, ou un nom se terminant par `.local`, `.lan`, `.home.arpa` ou `.internal`, ou sans aucun point, comme `http://nas:6040`. Un nom Tailscale MagicDNS court, comme `http://my-server:6040`, n'a pas de point non plus : il est donc pris en compte ici ; l'adresse IP Tailscale ou le nom complet se terminant par `.ts.net` compte comme [sécurisé](#connection-secure).

    **Incertain** : votre navigateur juge l'adresse que vous avez ouverte, puis le serveur indique d'où il voit venir la requête, uniquement le type d'adresse et jamais votre adresse IP. Le serveur peut confirmer le verdict du navigateur ou le rendre incertain, mais ne peut jamais faire qu'une connexion soit considérée comme sécurisée ; tant qu'il n'a pas répondu, le verdict du navigateur prévaut. Lorsque les deux sont en désaccord, le niveau est réseau local et la raison commence par *Incertain* :

    - une adresse d'apparence publique que le serveur voit venir de votre réseau local, de Tailscale ou du serveur lui-même, par exemple via un DNS scindé ou un proxy local ;
    - une adresse locale ou Tailscale que le serveur voit venir d'Internet.

    Le trafic n'est pas chiffré, et LibreFolio ne peut pas déterminer où vous vous trouvez réellement.

### 🔴 Connexion : non sécurisée {: #connection-not-secure }

Vous avez accédé à LibreFolio via une adresse `http://` en clair depuis Internet, par exemple via un port ouvert sur votre routeur. Sur un téléphone, un point rouge sur le bouton de menu vous avertit même lorsque la barre latérale est fermée.

<div class="lf-pros-cons" markdown>

| ✅ Avantage | ⚠️ Inconvénient |
|:--|:--|
| Aucun. | Les mots de passe et les données circulent en clair sur des réseaux que vous ne contrôlez pas : toute personne en chemin pourrait les lire, ou même les modifier. |

</div>

👉 **Que faire :** évitez cette adresse. Si vous exploitez le serveur, attribuez à LibreFolio une [adresse HTTPS](#https-address) et cessez d'exposer HTTP en clair. Changez ensuite votre mot de passe : **Paramètres** → [**Profil**](settings/profile.md) → **Changer le mot de passe**. Cela déconnecte aussi tous les autres appareils connectés à votre compte.

??? info "🔍 Quand une connexion est considérée comme non sécurisée"

    **Une adresse publique utilisant `http://` en clair** : une adresse ou un nom qui n'est ni local, ni Tailscale, ni le serveur lui-même, comme une adresse IP publique ou un nom de domaine tel que `http://myhome.duckdns.org:6040`. Le niveau reste valable lorsque le serveur voit aussi la requête venir d'Internet, ou ne peut pas le déterminer. S'il voit la requête venir de votre réseau local, de Tailscale ou du serveur lui-même, le niveau est [réseau local](#connection-local-network), avec la raison *Incertain*.

---

## 🔒 Comment se connecter en toute sécurité {: #https-address }

Attribuez à LibreFolio une adresse HTTPS, puis n'utilisez que celle-ci. La personne qui exploite le serveur la met en place, de l'une des deux manières suivantes :

- **Tailscale**, sans port ouvert sur votre routeur : Tailscale Serve fournit une adresse HTTPS aux appareils de votre tailnet, et Funnel une adresse publique qui ne nécessite pas Tailscale sur vos appareils. Voir [Exposer en toute sécurité](../admin/service_exposure.md).
- **Un proxy inverse** avec un certificat TLS, comme Caddy, Traefik ou Nginx : voir [Docker avancé](../admin/docker_advanced.md).

Suivez ensuite quelques bonnes habitudes :

- utilisez l'adresse `https://` sur chaque appareil, à la maison aussi ;
- ajoutez-la aux favoris, et mettez à jour les anciens favoris et raccourcis d'écran d'accueil qui pointent encore vers `http://` ;
- si vous n'exploitez pas le serveur, demandez l'adresse à la personne qui l'exploite ;
- vérifiez l'indicateur : il doit afficher **Connexion : sécurisée**.

Si vous exploitez le serveur, [Vérifier la sécurité de la connexion](../admin/connection_checks.md) explique comment vérifier le résultat.

---

## 🛡️ Avertissements de sécurité pour les administrateurs {: #security-warnings }

Si vous êtes administrateur, la même ligne vous indique aussi, sur chaque page, quand les contrôles de sécurité de votre instance nécessitent votre attention : les erreurs et avertissements que **Paramètres** → **Administration** → **Sécurité** répertorie et comptabilise dans son onglet.

- **Un point sur l'icône.** Un petit point se trouve dans le coin du bouclier de la ligne, que la barre latérale soit déployée ou réduite : rouge lorsqu'au moins un contrôle est une erreur, ambre lorsqu'il n'y a que des avertissements.
- **Un lien dans les détails.** Cliquez sur la ligne : après la raison, un lien donne le nombre, comme **2 avertissements de sécurité**, erreurs comprises. Il ouvre l'onglet **Sécurité**, où chaque constat indique ce qui ne va pas, et ferme les détails.
- **Le décompte en texte.** Lorsque la barre latérale est réduite, le survol du bouclier affiche le niveau et le nombre, comme *Connexion : sécurisée — 2 avertissements de sécurité*. Un lecteur d'écran lit la même chose, que la barre latérale soit déployée ou réduite.
- **Sur un téléphone**, la barre latérale est masquée derrière le bouton de menu, donc le bouton porte aussi le point : rouge en cas d'erreur, ou lorsque la connexion est [non sécurisée](#connection-not-secure), ambre avec seulement des avertissements. Ouvrez le menu pour voir la ligne.

Le point suit l'onglet **Sécurité** : les informations ne sont jamais comptées, donc avec seulement des informations, ou rien du tout, il n'y a pas de point. LibreFolio lit les contrôles une fois, lorsqu'il s'ouvre dans votre navigateur : après avoir corrigé un problème sur le serveur et redémarré celui-ci, rechargez la page, ou cliquez sur **Vérifier à nouveau** dans l'onglet. Les autres utilisateurs ne voient jamais le point ni le lien, et leur navigateur ne demande jamais les contrôles. Ce que signifie chaque contrôle, et comment le corriger : « Sécurité » dans [Paramètres globaux](../admin/settings.md#security-tab).

---

## 🧭 Ce que l'indicateur ne fait pas

L'indicateur décrit la connexion que vous utilisez à l'instant, et donne des conseils. Trois choses lui échappent.

**Il ne bloque rien.** C'est un conseil, pas un contrôle. Et comme il décrit la connexion de l'appareil que vous utilisez, le même LibreFolio peut afficher **Connexion : sécurisée** sur votre ordinateur portable et **Connexion : non sécurisée** sur votre téléphone.

**Il ne vérifie pas les certificats.** Un certificat auto-signé que vous avez accepté dans le navigateur affiche **Connexion : sécurisée**. Le trafic est chiffré, mais personne ne garantit que le serveur est réellement le vôtre.

**Il ne peut pas toujours voir où vous êtes.** Lorsque LibreFolio s'exécute dans Docker Desktop et est exposé directement, ou se trouve derrière un proxy qui ne transmet pas votre adresse dans `X-Forwarded-For`, le serveur voit chaque visiteur comme local. Une connexion HTTP en clair depuis Internet affiche alors **Connexion : réseau local**, avec la raison *Incertain*, au lieu de **Connexion : non sécurisée**. Docker Engine sous Linux conserve votre adresse.

Quoi que l'indicateur affiche, le conseil reste le même : utilisez l'adresse HTTPS.

---

## 🔗 Voir aussi

- 🌐 **[Exposer en toute sécurité](../admin/service_exposure.md)** — Tailscale, d'un VPN privé à une adresse HTTPS publique
- 🔍 **[Vérifier la sécurité de la connexion](../admin/connection_checks.md)** — Pour les administrateurs : l'adresse HTTPS, le cookie de session et le proxy inverse
- 🐳 **[Docker avancé](../admin/docker_advanced.md)** — Fichier Compose, variables d'environnement, proxy inverse
- 📝 **[Configuration](../admin/configuration.md)** — Chaque option du fichier `.env`
- 📦 **[Installation avec Docker](installation.md)** — Accès local et distant après l'installation
- 📱 **[Installer comme application (PWA)](pwa.md)** — Nécessite une adresse HTTPS
