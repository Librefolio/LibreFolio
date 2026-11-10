# 🧩 Paramètres des plugins

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="plugins" alt="Paramètres des plugins">
</div>

L'onglet **Plugins** regroupe ce que les sources de prix et de taux de change demandent : la clé API
d'une source de données payante, une région ou une préférence qui vous est propre. Ouvrez
**Paramètres** (icône d'engrenage dans la barre latérale), puis l'onglet **Plugins**, après
**Préférences** (sur un téléphone, l'onglet avec l'icône de pièce de puzzle). Chaque utilisateur
dispose de cet onglet ; ce que vous pouvez y modifier dépend du [propriétaire du paramètre](#personal-and-instance).
L'icône de livre en haut de cet onglet ouvre cette page.

Seuls les plugins qui demandent quelque chose sont listés, sous **Prix** pour les
[fournisseurs de prix](../assets/providers/index.md) et **Taux de change** pour les
[fournisseurs de taux de change](../fx/providers/index.md), chaque titre étant précédé de l'icône de
sa famille (un diagramme en colonnes pour les prix, des pièces pour les taux de change) ; un titre
qui ne contient aucun plugin de ce type est omis. Parmi les plugins livrés avec LibreFolio, deux ont
aujourd'hui un paramètre, chacun une préférence de recherche personnelle : **JustETF** et
**Borsa Italiana** (voir [Préférences de recherche](#search-preferences)). Un plugin ajouté à votre
installation peut en demander davantage. L'onglet comporte aussi un groupe **Outils**, pour les
[Outils](../tools/index.md) qui ont leurs propres paramètres ; aucun d'eux n'en a pour l'instant,
vous ne le verrez donc pas aujourd'hui. Quand aucun plugin ne demande rien, l'onglet affiche
*Aucun plugin installé ne demande de paramètres.*

## 🧾 Un plugin, un formulaire {: #form }

Chaque plugin a son propre formulaire : son icône et son nom (une pièce de puzzle quand le plugin n'a
pas d'icône), un [badge](#configured) qui indique s'il peut fonctionner, puis ses paramètres. Chaque
paramètre affiche son nom, un **\*** rouge lorsqu'il est obligatoire, à qui il appartient —
**Personnel** ou **Toute l'instance** — et ce qu'il fait.

- Modifiez ce dont vous avez besoin, puis cliquez sur **Enregistrer** en bas du formulaire de ce
  plugin : chaque plugin est enregistré séparément. **Abandonner** annule les modifications que vous
  n'avez pas enregistrées.
- **Enregistrer** conserve toutes les modifications du plugin, ou aucune : lorsque l'une d'elles est
  refusée, rien n'est enregistré, et le paramètre en cause en indique la raison.
- Avant d'enregistrer, LibreFolio vérifie ce que vous avez saisi au regard des règles du plugin — un
  nombre, un nombre entier, un minimum ou un maximum, une longueur, l'une des options — et indique
  sous le paramètre ce qui ne va pas, par exemple *Au moins 8 caractères*. **Enregistrer** reste
  désactivé jusqu'à correction.
- Une modification enregistrée apparaît dans le paramètre lui-même, sans message. Un plugin dont vous
  ne pouvez pas modifier les paramètres n'a aucun bouton.

??? note "💬 Quand un enregistrement n'aboutit pas"

    | Message | Ce qui s'est passé |
    |---|---|
    | *Rien n'a été enregistré : vérifiez les paramètres ci-dessous.* | Un paramètre a été refusé. En dessous : *La valeur n'est pas valide pour ce paramètre.*, *Seul un administrateur peut modifier ce paramètre.*, *Une variable du serveur le définit : il ne peut pas être modifié ici.* ou *Ce paramètre n'existe plus : rechargez la page.* |
    | *Ces paramètres ont changé entre-temps : ils ont été rechargés, enregistrez à nouveau.* | Quelqu'un a enregistré les mêmes paramètres au même moment : rien de ce que vous avez fait n'a été enregistré. Vérifiez les valeurs affichées, puis enregistrez à nouveau. |
    | *Les secrets ne peuvent pas être enregistrés : la clé de cette instance ne peut pas être utilisée (voir les vérifications de configuration).* | Rien n'a été enregistré : un secret ne peut pas être chiffré. Un administrateur trouve la cause dans les [vérifications au démarrage](../../admin/configuration_security.md#startup-checks). |
    | *Les paramètres n'ont pas pu être enregistrés.* | Pas de réponse du serveur : réessayez. |

---

## 👥 Paramètres personnels et paramètres de toute l'instance {: #personal-and-instance }

À côté de son nom, chaque paramètre indique à qui il appartient :

| | **Personnel** | **Toute l'instance** |
|---|---|---|
| **Sa valeur** | La vôtre : chaque utilisateur a la sienne | Une seule pour tout le monde sur ce LibreFolio |
| **Qui le modifie** | Vous | Un administrateur |
| **Qui le voit** | Vous seul : pas même un administrateur | Tout le monde ; les utilisateurs qui ne sont pas administrateurs le voient en lecture seule, avec *Seul un administrateur peut le modifier.* D'un secret, ils ne voient que s'il est défini |
| **Ce qu'il change** | Ce que LibreFolio fait pour vous seul : vos recherches et les vérifications du fournisseur dans la boîte de dialogue de l'actif, comme **Tester la configuration** | Tout ce que fait le plugin, prix et taux de change compris |

Les prix, les historiques de prix et les taux de change sont partagés par tout le monde : ils ne
dépendent donc jamais du choix d'un seul utilisateur. Pour eux, un paramètre personnel prend toujours
la valeur par défaut du plugin.

!!! info "🛡️ Pour les administrateurs"

    Vous modifiez ici les paramètres de toute l'instance, comme tout le monde modifie les siens. Un
    paramètre de toute l'instance peut aussi être fourni par la configuration du serveur : voir
    [Défini par le serveur](#set-by-the-server), et, pour les variables,
    [Paramètres des plugins](../../admin/configuration_secrets.md#plugin-settings) dans le manuel des
    administrateurs.

---

## 🔐 Secrets {: #secrets }

Certains paramètres sont des secrets, comme une clé API. Un secret est en écriture seule :

- **Saisissez-le, puis enregistrez.** Ce que vous avez saisi est envoyé une fois, puis retiré de la
  page : dès lors, le paramètre n'affiche plus que la mention *Défini le*, suivie de la date et de
  l'heure de l'enregistrement, jamais le secret lui-même — pas même pour vous. Le champ est marqué
  comme un nouveau mot de passe, afin que le navigateur ne le remplisse pas avec l'un de vos mots de
  passe enregistrés.
- **Remplacer** ouvre le champ pour une nouvelle valeur ; **Annuler** conserve celle qui est
  enregistrée.
- **Effacer** supprime le secret lorsque vous cliquez sur **Enregistrer** (*Il sera supprimé lors de
  l'enregistrement.*) ; **Annuler** le conserve.

Les utilisateurs qui ne sont pas administrateurs voient un secret de toute l'instance comme
*Défini le …* (*Défini* quand le [serveur le définit](#set-by-the-server)) ou *Non défini*, et rien
d'autre. LibreFolio conserve un secret enregistré sous forme chiffrée : voir
[Secrets enregistrés et clé de l'instance](../../admin/configuration_secrets.md#plugin-secrets).

---

## 🔒 Défini par le serveur {: #set-by-the-server }

Un administrateur peut aussi fournir un paramètre de toute l'instance par la configuration du serveur,
au moyen d'une variable d'environnement. Le paramètre affiche alors sa valeur en lecture seule, un
secret seulement comme *Défini*, avec :material-lock-outline: *Défini par le serveur* : personne ne
peut le modifier ici, pas même un administrateur. Les administrateurs voient aussi le nom de la
variable : la mention *Défini par la variable du serveur* est suivie de ce nom.

Pour modifier un tel paramètre, un administrateur change la variable et redémarre LibreFolio : voir
[Une variable verrouille le paramètre](../../admin/configuration_secrets.md#plugin-variable-lock).

---

## ↩️ Revenir à la valeur par défaut {: #use-the-default }

Une fois que vous avez enregistré une valeur qui vous est propre dans un paramètre que vous pouvez
modifier, **Utiliser la valeur par défaut** apparaît en dessous. Cela supprime la valeur enregistrée
lorsque vous cliquez sur **Enregistrer**, et le paramètre revient à la valeur par défaut du plugin :
*La valeur enregistrée sera supprimée lors de l'enregistrement : la valeur par défaut s'applique.*,
avec **Annuler**. Vider un champ de texte qui affiche une valeur enregistrée produit le même effet.
Un secret n'a pas de valeur par défaut : **Effacer** le supprime ([Secrets](#secrets)).

---

## ⚠️ Quand un paramètre pose problème {: #problems }

| Le paramètre indique | Ce qui s'est passé | Que faire |
|---|---|---|
| *La variable du serveur … n'est pas valide : le plugin reste non configuré jusqu'à sa correction.* | La variable qui le définit contient une valeur que le paramètre refuse, ou désigne un fichier qui ne peut pas être lu. LibreFolio ne se rabat jamais sur une valeur enregistrée ni sur la valeur par défaut. Les administrateurs voient le nom de la variable | Un administrateur corrige la variable et redémarre LibreFolio |
| *La valeur enregistrée n'est plus valide : la valeur par défaut s'applique.* | Le plugin n'accepte plus la valeur enregistrée auparavant, après une mise à jour par exemple | Choisissez à nouveau une valeur et enregistrez-la, ou laissez-la : la valeur par défaut s'applique entre-temps |
| *Enregistré, mais la clé de cette instance ne peut pas le lire. Si un administrateur peut remettre l'ancienne clé, cela prime ; sinon, saisissez-le à nouveau.* | Un secret enregistré ne peut plus être lu, car la clé de chiffrement de l'instance a changé. LibreFolio le conserve, mais ne l'utilise jamais | Si un administrateur peut encore remettre l'ancienne clé de l'instance, cela prime : un secret enregistré sous la nouvelle clé deviendrait illisible une fois l'ancienne clé rétablie (voir [Secrets enregistrés et clé de l'instance](../../admin/configuration_secrets.md#plugin-secrets)). Sinon, saisissez à nouveau le secret et enregistrez-le ; pour un secret de toute l'instance, c'est un administrateur qui le fait |

---

## 🚦 Configuré ou à configurer {: #configured }

Le badge à côté du nom de chaque plugin indique s'il peut fonctionner :

- **Configuré** : chaque paramètre obligatoire a une valeur que LibreFolio peut utiliser.
- **À configurer** : un paramètre obligatoire n'a aucune valeur utilisable — jamais défini, ou un
  secret qui ne peut plus être lu — ou une variable du serveur qui définit l'un de ses paramètres
  n'est pas valide.

LibreFolio n'appelle pas un plugin qui est **À configurer** : ses prix ou ses taux de change ne sont
pas mis à jour, une recherche indique qu'il doit être configuré, et **Tester la configuration** échoue
avec ❌ *Ce fournisseur doit être configuré avant utilisation*. Les plugins livrés avec LibreFolio
n'ont besoin d'aucun paramètre pour fonctionner : **JustETF** et **Borsa Italiana** sont toujours
**Configurés**.

---

## 🛠️ Configurer, depuis un actif {: #configure }

Vous n'êtes pas obligé de quitter un actif pour modifier les paramètres de son fournisseur :
**Configurer** ouvre le même formulaire que cet onglet, pour ce seul fournisseur de prix, par-dessus
la boîte de dialogue dans laquelle vous vous trouvez.

- **Dans la boîte de dialogue de l'actif** (**+ Ajouter un actif**, ou **Modifier** sur un actif), sous
  **Attribution du fournisseur** : lorsque le fournisseur choisi a des paramètres, **Configurer** se
  trouve à côté de son lien d'aide :material-help-circle-outline: — sur un téléphone, son icône
  :material-tune: seule. Quand le fournisseur ne peut pas encore fonctionner, **À configurer**
  s'affiche là aussi. Après un enregistrement, le badge se met à jour, et l'actif que vous modifiez
  reste tel qu'il était.
- **Dans la recherche en ligne** : lorsqu'un fournisseur doit être configuré avant de pouvoir
  effectuer une recherche, la liste des résultats commence par une ligne *… doit être configuré avant
  de pouvoir effectuer une recherche*, nommant le fournisseur, et son propre bouton **Configurer**.
  Une fois que vous avez enregistré, la recherche est relancée. Ainsi, un fournisseur qui n'a pas pu
  chercher n'est jamais confondu avec un fournisseur qui n'a rien trouvé.

---

## 🔎 Préférences de recherche : JustETF et Borsa Italiana {: #search-preferences }

Les deux sont des paramètres **Personnels**, et tous deux affichent tout tant que vous ne choisissez
pas autre chose. Ils ne choisissent que les lignes que vos propres recherches listent : aucun prix ne
change, et aucun actif que vous possédez déjà ne change non plus. Aucun instrument ne disparaît non
plus : chacun existe dans toutes les devises ou toutes les langues, une préférence ne conserve donc
qu'une de ses lignes.

| Plugin | Paramètre | Choix | Ce que cela change dans **Recherche en ligne** |
|---|---|---|---|
| **JustETF** | **Devise préférée** | **Toutes les devises** (la valeur par défaut), 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF, 🇬🇧 GBP | Avec une devise, chaque fonds apparaît une fois, dans cette devise. Avec **Toutes les devises**, chaque fonds apparaît quatre fois, une fois par devise |
| **Borsa Italiana** | **Langue préférée** | **Les deux langues** (la valeur par défaut), 🇮🇹 Italien, 🇬🇧 Anglais | Avec une langue, chaque instrument apparaît une fois, dans cette langue : celle de son nom et de ses détails. Avec **Les deux langues**, l'italien d'abord, puis l'anglais. Le site de Borsa Italiana est interrogé de la même manière quel que soit votre choix |

Définissez-les ici, sous **JustETF** et **Borsa Italiana**, ou avec **Configurer** dans la boîte de
dialogue de l'actif lorsque ce fournisseur est choisi.

### 👑 La couronne dans les résultats JustETF {: #crown }

👑 marque la devise propre d'un fonds, celle dans laquelle sa NAV est calculée — pas nécessairement
celle dans laquelle vous négociez. Chaque fois qu'un résultat l'affiche, une ligne en bas de la liste
le précise : *👑 la devise propre du fonds*. Avec une devise préférée, 👑 n'apparaît que sur les fonds
calculés dans cette devise : avec 🇪🇺 EUR, un fonds calculé en dollars américains affiche 🇪🇺 seul.

Fonctionnement de la devise d'un actif justETF : [Choisir la devise lors de la recherche](../assets/providers/justetf.md).

---

## 🔗 Voir aussi

- 🎛️ **[Préférences utilisateur](preferences.md)** — Langue, devise de base, thème et guides
- ⚙️ **[Vue d'ensemble des paramètres](index.md)** — Chaque onglet de Paramètres
- 📡 **[justETF](../assets/providers/justetf.md)** et 🇮🇹 **[Borsa Italiana](../assets/providers/borsa-italiana.md)** — Les deux fournisseurs dotés d'une préférence de recherche
- 🛠️ **[Paramètres des plugins pour les administrateurs](../../admin/configuration_secrets.md#plugin-settings)** — Les variables du serveur, la clé de l'instance et le chiffrement des secrets
- 🧩 **[Paramètres des plugins pour les développeurs](../../developer/architecture/patterns/plugin_settings.md)** — Comment un plugin déclare ses paramètres
