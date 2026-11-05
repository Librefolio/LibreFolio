# ➕ Créer et modifier des actifs

Ajoutez un instrument que vous détenez ou suivez, associez-le à un fournisseur de prix et veillez à l'exactitude de ses informations.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulaire de création manuelle" alt="Fenêtre modale de création manuelle">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulaire de création automatique de l'assistant d'importation" alt="Créer un actif depuis l'assistant">
</div>

## 🚀 Créer un actif {: #asset-creation-flows }

=== "Depuis la page Actifs"

    1. Sur la page **Actifs**, cliquez sur **+ Ajouter un actif**.
    2. Dans **Rechercher en ligne**, saisissez un nom, un ticker ou un ISIN et choisissez un résultat : LibreFolio remplit le
       formulaire, associe ce fournisseur et [vérifie ses données](#provider-data-comparison). Aucun résultat ?
       Remplissez le formulaire vous-même et signalez la recherche avec [**Faites-le-nous savoir**](#let-us-know).
    3. Vérifiez les champs ci-dessous, puis cliquez sur **Créer un actif**.

=== "Depuis un import de courtier"

    1. Dans la section **Résoudre les actifs** de l'assistant d'importation, choisissez **Créer un nouvel actif** dans le
       sélecteur du titre.
    2. Le formulaire s'ouvre avec les codes et les noms du rapport. Si le rapport n'a pas de nom, le champ **Nom**
       est initialisé avec l'ISIN (ou le ticker).
    3. Cliquez sur l'une des **Suggestions** sous **Rechercher en ligne** pour rechercher le titre, ou remplissez
       le formulaire vous-même. Cliquez ensuite sur **Créer un actif**.

    Si le résultat choisi porte le même nom que l'un de vos actifs, LibreFolio propose d'utiliser cet
    actif à la place ; **L'utiliser et ajouter la clé** enregistre aussi les codes du rapport sur celui-ci.

Vérifiez ces champs avant d'enregistrer :

- **Nom** : obligatoire et unique ; un avertissement apparaît si un autre actif l'utilise déjà.
- **Type** : voir [Choisir le type d'actif](#choosing-the-asset-type).
- **Unités par prix unitaire** : combien d'unités un prix représente, généralement 1, et 100 pour la plupart
  des obligations. Choisir un résultat de **Rechercher en ligne** le définit, tout comme il définit le nom :
  selon la suggestion du fournisseur si celui-ci en propose une, avec une note sous le champ expliquant pourquoi
  ([Yahoo Finance](providers/yahoo-finance.md) suggère 100 pour une ligne londonienne cotée en pence, par
  exemple), sinon à 100 pour une **Obligation** et à 1 pour tout autre type. Il en va de même dans **Modifier l'actif**,
  par-dessus la valeur enregistrée, qui ne change qu'au moment de l'enregistrement. Saisir une valeur dans le champ supprime la
  note. Choisir vous-même le **Type** laisse le champ tel quel ; pour une **Obligation**, une indication rappelle
  que les obligations sont généralement cotées pour 100.
- **Devise** : la devise dans laquelle les prix sont cotés. Pour un fonds coté en euros, il s'agit de l'EUR,
  même lorsque le fonds est libellé dans une autre devise.

Après l'enregistrement depuis la page **Actifs**, la confirmation renvoie vers le nouvel actif. Si l'actif a un
fournisseur, l'historique de ses prix commence à être téléchargé immédiatement.

## 🔎 Résultats de la recherche en ligne {: #search-online-results }

**Rechercher en ligne** interroge tous les fournisseurs en même temps et trie leurs résultats à mesure qu'ils arrivent :
d'abord les sources **premium** (celles que votre instance cautionne, comme des données sous licence), puis les
sources **communautaires**, chaque groupe étant trié par priorité. Aucun des fournisseurs livrés avec LibreFolio n'est
premium, et tous ont la même priorité : les résultats apparaissent au fur et à mesure des réponses, sauf si votre
administrateur [modifie l'ordre](../../admin/configuration_accounts.md#provider-order).

Lorsque la recherche a inclus une source premium, la liste comporte deux parties :

- **Premium** : les résultats des sources premium, ou *Aucun résultat provenant des sources premium.*
- **Sources non premium (communauté) · N résultats**, repliée. Son ouverture affiche d'abord un avertissement : ces
  sources sont des sources tierces, LibreFolio ne garantit pas leurs prix ni leurs données, et en choisir une
  ne s'applique qu'à cet actif. La section est de nouveau repliée la prochaine fois que vous ouvrez le formulaire.

### 📨 Vous ne le trouvez pas ? Faites-le-nous savoir {: #let-us-know }

Une fois une recherche terminée, quel que soit son résultat, même après une erreur ou un dépassement de délai, la liste propose
*Vous ne le trouvez pas ?* **Faites-le-nous savoir** (entre les deux parties, lorsqu'il y en a deux), tant que l'application
sait où envoyer le rapport. Le rapport est envoyé à la personne qui assure le support de votre instance. Si la liste est
repliée, cliquez dans le champ de recherche pour la faire réapparaître ; vider le champ efface la recherche.

La destination du lien dépend de l'adresse de support de votre instance ; son infobulle vous l'indique :

| Adresse de support | Ce que fait **Faites-le-nous savoir** |
|---|---|
| Une adresse e-mail | Votre application de messagerie s'ouvre avec un message dont l'objet et les détails sont déjà remplis |
| Une page web | La page s'ouvre dans un nouvel onglet avec l'objet et les détails dans son adresse, afin qu'un formulaire de support puisse se remplir automatiquement. Les détails sont également copiés, prêts à être collés ; un message confirme la copie ou signale son échec |
| Aucune (par défaut), sur une instance auto-hébergée | Une nouvelle issue GitHub s'ouvre dans un nouvel onglet, déjà remplie. Elle est **publique** : relisez-la avant de l'envoyer |

Le lien est absent, même avec une adresse de support, lorsque l'application n'a pas pu lire la configuration de votre instance ;
rechargez la page pour réessayer.

Les détails sont en anglais : le texte que vous avez recherché ; chaque fournisseur interrogé et son résultat (nombre de
résultats, *aucune réponse*, ou une erreur, avec son code lorsqu'elle en a un ; jamais le message de l'erreur) ; les
identifiants déjà présents dans le formulaire, ainsi que sa devise et son type, sauf s'il s'agit encore des valeurs par défaut d'un
formulaire nouveau et vide (votre devise de base et Action) ; votre version de LibreFolio, le profil de l'instance et la langue de l'application. Lorsque vous modifiez un actif, les détails incluent donc
les identifiants propres à l'actif (ISIN, ticker…), sa devise et son type, tels que le formulaire les affiche.
Ils n'incluent jamais votre identité, une adresse e-mail, l'adresse de votre instance ni aucune donnée de portefeuille.
Vous envoyez le rapport vous-même, depuis votre propre appareil : il ne passe jamais par le serveur LibreFolio.

## 🗂️ Choisir le type d'actif {: #choosing-the-asset-type }

Le champ **Type** ouvre un menu avec recherche des
[types d'actif](../../financial-theory/instruments/asset-types/index.md). **ETF** et
**Financement participatif** sont des familles : ouvrez-en une pour voir d'abord son membre générique (**ETF**, **Crowdfund**),
puis des types spécifiques comme **ETF actions** ou **Financement participatif immobilier**. Saisissez quelques lettres pour
rechercher aux deux niveaux, par nom ou par code (par exemple `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Menu Type avec la famille ETF déployée, chaque type d'ETF spécifique affichant son icône composite">
</div>

**Rechercher en ligne** définit généralement un type général comme **ETF**. Si vous savez ce que contient le fonds,
affinez-le, par exemple en **ETF actions** : son badge et son icône indiquent alors ce qu'il contient. Une
[vérification ultérieure par rapport aux données du fournisseur](#provider-data-comparison) conserve votre choix.

## 🔌 Associer un fournisseur de prix

Choisir un résultat de **Rechercher en ligne** associe automatiquement son fournisseur. Pour en configurer un manuellement, déployez
**Affectation du fournisseur** (décochez d'abord **Aucun fournisseur** s'il est coché) :

1. Choisissez le **Fournisseur**, puis saisissez l'**Identifiant**, son **Type d'identifiant** et les éventuels paramètres
   demandés par le fournisseur.
2. Cliquez sur **Tester la configuration** : LibreFolio récupère un **Prix actuel** et quelques jours d'**Historique**. ⚠️ signifie que le fournisseur ne propose pas ces données ou n'en a aucune pour le moment (CSS Scraper
   n'a pas d'historique, par exemple) ; le test réussit quand même. ❌ signale une erreur : vérifiez l'identifiant et
   les paramètres. Lorsque l'**Historique** répond, y compris ⚠️, une note rappelle que le test ne lit que
   les derniers jours : un nouvel actif obtient tout son historique de prix lors de sa création.

⚠️ *Suspendu pour cause de trop nombreuses requêtes jusqu'à …* signifie que le fournisseur a refusé les requêtes de LibreFolio
parce qu'elles étaient trop nombreuses : LibreFolio ne le sollicite plus jusqu'à l'heure indiquée, dans votre heure locale,
avec la date si la pause se termine un autre jour. Vos paramètres peuvent très bien être corrects, donc le test réussit quand même.
Lorsque la fin de la pause n'est pas connue, vous voyez *Trop de requêtes : réessayez plus tard*.
Pendant ce temps, la liste des actifs et la page de l'actif continuent d'afficher le dernier prix enregistré.

Un actif a au plus un fournisseur ; cochez **Aucun fournisseur** si vous saisissez vous-même ses prix. Consultez
[Fournisseurs](providers/index.md) pour découvrir ce que propose chacun.

## ⚖️ Vérifier les données du fournisseur {: #provider-data-comparison }

LibreFolio compare les informations du fournisseur avec votre formulaire après que vous avez choisi un résultat de **Rechercher en ligne**,
et lorsque vous cliquez sur **Demander au fournisseur** : en haut de **Détails de l'actif** pour tout, à côté des **Identifiants** ou dans un éditeur de distribution pour cette partie uniquement. Il faut un fournisseur et un
identifiant.

- Les champs vides sont remplis, et les codes supplémentaires du fournisseur rejoignent **Autres identifiants**.
- *Le fournisseur n'a pas de données pour : …* indique une distribution sectorielle ou géographique manquante ; *Toutes les données correspondent
  au fournisseur* signifie qu'il n'y a rien à vérifier.
- Toute différence ouvre la boîte de dialogue **Comparaison des données du fournisseur**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-provider-compare" alt="La boîte de dialogue Comparaison des données du fournisseur par-dessus le formulaire Ajouter un actif : la ligne TICKER demandant quel code est le principal, avec le code du fournisseur choisi à la place de celui déjà enregistré, qui est conservé comme alternatif ; la ligne Type avec sa valeur actuelle et celle du fournisseur sous forme de badges d'icônes ; la ligne Distribution sectorielle, valeur actuelle face à celle du fournisseur ; et Tout sélectionner, Tout désélectionner, Annuler et Appliquer la sélection">
</div>

Chaque ligne de la boîte de dialogue affiche votre **Valeur actuelle** à côté de la **Valeur du fournisseur**, et est
cochée au départ :

1. Décochez les lignes pour lesquelles vous souhaitez conserver votre valeur (**Tout sélectionner** et **Tout désélectionner** vous y aident).
2. Sur une ligne d'identifiant, choisissez le code principal ; l'autre est conservé sous **Autres identifiants** (voir
   [Modifier les identifiants](#one-instrument-several-codes)). Le code du fournisseur est proposé, car c'est
   normalement celui qui est coté.
3. Cliquez sur **Appliquer la sélection**, qui compte les lignes retenues (par exemple *Appliquer la sélection (2/3)*),
   ou sur **Annuler** pour ne rien modifier.

Les valeurs acceptées ne font que remplir le formulaire : elles sont enregistrées lorsque vous enregistrez l'actif.

- **Votre type affiné est conservé.** Borsa Italiana, par exemple, déclare chaque instrument ETFplus comme
  un simple **ETF** : si vous avez choisi **ETF actions**, cela est considéré comme concordant et aucune ligne n'apparaît (il en va
  de même pour **Financement participatif**). Un type *plus spécifique* que le vôtre est tout de même proposé.
- **Chaque question n'est posée qu'une fois.** Lorsqu'un résultat de recherche apporte un ISIN (ou un autre code)
  différent de celui du formulaire, LibreFolio demande d'abord lequel est le principal, et la comparaison ne le
  redemande plus.
- **Les unités par prix unitaire sont proposées, jamais remplies.** Une vérification complète (après le choix d'un résultat de recherche, ou avec **Demander au fournisseur** en haut de **Détails de l'actif**) compare cette valeur à la suggestion du fournisseur ou, en l'absence de suggestion, à 100 pour une obligation et à 1 pour tout autre type (le type proposé par le fournisseur, s'il en propose un autre). Une différence apparaît comme une ligne cochée sous **Détails de l'actif**, avec une
  note qui en donne la raison : la suggestion du fournisseur, ou le fait que les obligations sont généralement cotées pour 100 (une
  ligne qui propose la valeur habituelle de 1 n'en a pas). Décochez-la pour conserver votre valeur. Si une vérification revient sans
  la suggestion du fournisseur (elle a mis trop de temps, par exemple), celle qu'il a donnée auparavant pour le même
  fournisseur et le même identifiant, dans le résultat de recherche ou lors d'une vérification antérieure, compte toujours : LibreFolio ne
  propose pas de l'annuler.

## 🛠️ Modifier un actif {: #editing-an-asset }

Sur la [page de détail](detail/index.md) de l'actif, cliquez sur **Modifier** (✏️), effectuez les changements nécessaires dans le
formulaire **Modifier l'actif**, puis cliquez sur **Enregistrer les modifications**.

### 💱 Changer la devise {: #changing-the-currency }

Une nouvelle **Devise** est toujours autorisée, mais les prix et les événements sont stockés dans la devise dans laquelle ils ont été libellés ;
les anciens ne peuvent donc pas rester à côté des nouveaux. Changer la devise supprime une partie de ce qui est
stocké pour l'actif et conserve le reste :

| Stocké pour l'actif | Après le changement |
|----------------------|------------------|
| Son **historique de prix** | Supprimé |
| Ses **dividendes, intérêts et autres événements**, ceux que vous avez saisis et ceux générés par le fournisseur | Supprimés |
| Vos **transactions** | Toujours **conservées**. Celles liées à un événement supprimé restent, mais perdent ce lien |
| Ses **divisions** | **Conservées**, tout comme les transactions qui y sont liées : les ajustements d'une division conservent leur lien et leur coût |

Les divisions sont des ratios, pas des montants d'argent ; elles ont donc la même signification dans toute devise.

Avant tout enregistrement, le formulaire demande au serveur ce qui serait supprimé. Si la réponse ne peut pas être lue, le formulaire
affiche l'erreur et n'enregistre rien. Si rien ne serait supprimé (l'actif n'a encore ni prix, ni événements, ni transactions liées), le changement est simplement enregistré. Si quelque chose serait supprimé, une boîte de dialogue **Changer la devise de l'actif**
le liste :

- les **points de prix** qui seront supprimés, avec la période qu'ils couvrent ;
- les **événements manuels** et les **événements générés par le fournisseur** qui seront supprimés ;
- les transactions qui **perdent leur lien avec un événement supprimé** (les transactions elles-mêmes sont conservées) ;
- les **événements de division** qui restent, avec les transactions qui y sont liées.

Rien n'est supprimé tant que vous n'avez pas cliqué sur **Supprimer et changer la devise** ; **Annuler** laisse l'actif tel qu'il était.
La boîte de dialogue vous permet également de télécharger d'abord une **sauvegarde** des prix et des événements (CSV ou JSON), lorsqu'il en existe.

Après le changement, si l'actif a un fournisseur et qu'il avait des prix, ceux-ci sont de nouveau téléchargés depuis le
fournisseur, à partir de la date la plus ancienne que vous aviez, dans la nouvelle devise. Sans fournisseur, vous importez à nouveau les prix
vous-même. Les transactions qui ont perdu le lien avec un événement peuvent être reliées de nouveau en une seule fois : voir
[Relier à nouveau les événements](../transactions/index.md#relink-events).

Changer ou supprimer le fournisseur obéit à ses propres règles, ci-dessous.

### 🔄 Changer ou supprimer le fournisseur {: #changing-or-removing-the-provider }

Certains changements de fournisseur suppriment des données que LibreFolio avait stockées. Avant l'enregistrement, le formulaire demande au
serveur ce qui serait supprimé et, si quelque chose le serait, il affiche **une** confirmation qui en donne les chiffres.
Rien n'est supprimé tant que vous ne confirmez pas ; **Annuler** laisse l'actif tel qu'il était.

| Ce que vous changez | Ce qui est supprimé |
|-----------------|-----------------|
| De nouveaux paramètres pour un plan d'[investissement programmé](providers/scheduled-investment.md) | Tous les prix de l'actif et les événements générés par le plan : ils sont générés de nouveau à partir des nouveaux paramètres |
| Un autre fournisseur, lorsque l'actif utilisait un plan d'investissement programmé | La même chose : tous les prix et les événements générés par le plan ; le nouveau fournisseur fournit ensuite l'historique |
| **Aucun fournisseur** | Les événements générés par le fournisseur (ses dividendes, divisions ou coupons). Les prix dont vous disposez déjà sont **conservés** |
| Un autre fournisseur en ligne, ou de nouveaux paramètres pour un fournisseur en ligne (Yahoo Finance, justETF…) ; un premier fournisseur pour un actif qui n'en avait aucun | Rien, et aucune question n'est posée |

Par exemple, passer d'un plan à Yahoo Finance demande :

> L'historique de cet actif a été généré par investissement programmé. Passer à Yahoo Finance
> supprime 1 240 points de prix et 6 événements générés par le fournisseur. 3 transactions perdent
> leur lien avec un événement supprimé (les transactions elles-mêmes sont conservées). […] Les événements manuels sont conservés.
> Cette action est irréversible. Continuer ?

Ce que signifie la boîte de dialogue :

- **Les points de prix et les événements** sont comptés tels qu'ils sont stockés à cet instant. Les prix incluent ceux que vous avez saisis
  vous-même, lorsque les paramètres d'un plan changent ou que le fournisseur change ; avec **Aucun fournisseur**, ils restent.
- **Les transactions ne sont jamais supprimées.** Une transaction que vous avez enregistrée contre un événement supprimé, comme un
  dividende ou un coupon, reste dans votre portefeuille mais perd son lien : son champ **Événement lié**
  est vide. La boîte de dialogue compte toutes ces transactions, y compris celles sur des courtiers
  que vous ne pouvez pas voir, et ne les nomme pas.
- **Les événements que vous avez ajoutés vous-même restent**, avec leurs liens.
- Si rien ne serait perdu, ou si le décompte n'a pas pu être obtenu, le formulaire enregistre sans boîte de dialogue.

⚠️ **Un cas est refusé.** Si une division générée par le fournisseur a des ajustements liés sans
[coût d'achat](../transactions/form.md), le changement ou la suppression n'est pas effectué : une fois la division supprimée,
ces unités seraient considérées comme achetées à un prix inconnu. Le formulaire affiche le message à la place de la
boîte de dialogue, nomme la division par sa date, et le reste de votre modification est enregistré. Attribuez un
coût d'achat à ces ajustements, puis changez de nouveau le fournisseur.

## 🏷️ Modifier les identifiants {: #one-instrument-several-codes }

Un même titre peut avoir plusieurs codes. LibreFolio conserve **un seul actif** avec tous ces codes, sous
**Informations complémentaires** dans le formulaire de l'actif :

- **Identifiants** : les codes principaux, un par type (ISIN, ticker…). **Ajouter un identifiant** ajoute une ligne et
  **Demander au fournisseur** les récupère.
- **Autres identifiants** : tout code supplémentaire ou libellé de courtier. Saisissez-en un et appuyez sur Entrée, virgule, point-virgule
  ou Tabulation. Ces codes sont recherchables et aident à reconnaître l'actif lors d'imports ultérieurs.

!!! tip "Conservez le code coté comme ISIN principal"

    Un prix est la valeur de la dernière opération ; seul un code négociable a donc un prix. Placez ce code dans
    **ISIN** et tout le reste dans **Autres identifiants**, sinon aucun fournisseur ne pourra coter l'actif.

### 🏛️ Obligations d'État italiennes pour particuliers (BTP Valore, BTP Più, BTP Italia)

Ces obligations sont souscrites sous un ISIN et négociées sous un autre :

| Phase | Code | Ce qu'il fait |
|---|---|---|
| Souscription à l'émission | l'ISIN « CUM » | Vous ouvre droit à la **prime de fidélité** si vous conservez jusqu'à l'échéance. **Non négociable**, donc aucun fournisseur ne le cote |
| Marché secondaire | un ISIN différent | Négocié librement et **coté** : c'est celui qui a un prix |

Pour vendre avant l'échéance, l'obligation est convertie vers le code du marché. Conservez les deux codes sur un seul actif :

1. Placez l'**ISIN du marché** dans **ISIN**.
2. Placez l'**ISIN CUM** dans **Autres identifiants**.
3. Enregistrez la **prime de fidélité**, lorsqu'elle est versée, comme une transaction **Intérêt** sur cet actif.
   Cela fonctionne aussi après l'échéance : un actif désactivé reste sélectionnable.

Lorsqu'un import apporte le code CUM pour un actif qui possède celui du marché, LibreFolio demande quel code doit être principal et conserve l'autre sous **Autres identifiants**.

## 🗺️ Définir les distributions sectorielles et géographiques

Les fournisseurs renseignent les distributions sectorielles et géographiques lorsqu'ils le peuvent ; pour les autres actifs, définissez-les
vous-même. Elles alimentent les graphiques d'allocation du tableau de bord et l'export IA.

Dans le formulaire de l'actif, déployez **Informations complémentaires** : sous **Classification**, **Distribution sectorielle** et
**Distribution géographique** affichent une ligne par secteur ou pays, avec son poids en pourcentage.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Distribution sectorielle" alt="Éditeur de distribution sectorielle dans la fenêtre modale de l'actif">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Distribution géographique" alt="Éditeur de distribution géographique dans la fenêtre modale de l'actif">
</div>

- **Ajouter un secteur** / **Ajouter un pays** ajoute une ligne : choisissez l'entrée, puis saisissez son poids.
- Le **Total** devient vert à 100 %, ambre lorsqu'il manque quelque chose, rouge lorsque vous dépassez.
- **Équilibrer à 100 %**, une action de ligne, reporte tout l'écart sur cette ligne. **Équilibrer les lignes sélectionnées**
  le répartit entre les lignes sélectionnées, proportionnellement à leurs poids.
- **Supprimer** efface une ligne, **Demander au fournisseur** récupère la distribution du fournisseur, et **Importer un CSV**
  en charge une depuis un fichier.

### 📥 Importer une distribution depuis un CSV {: #importing-a-distribution-csv }

**Importer un CSV** attend un en-tête `name,weight`, puis une ligne par pays ou secteur, avec les poids en
pourcentage :

```csv
name,weight
USA,60
Italy,40
```

- Les **noms** doivent correspondre exactement, sans tenir compte de la casse ni des espaces environnants. Pays : un code ISO
  (`IT`, `ITA`) ou le nom dans votre langue. Secteurs : la clé du secteur (par exemple `Government Bonds`)
  ou le nom dans votre langue.
- Les **poids** vont de `0` à `100` et doivent totaliser 100 (à 0,005 point près) ; chaque nom apparaît
  une fois.
- L'import est **tout ou rien** : une seule ligne incorrecte le bloque. Lorsqu'il réussit, il **remplace** toute la distribution.

!!! warning "Virgules décimales"

    Le séparateur, `,` ou `;`, est lu dans l'en-tête. Avec `,`, la ligne `Italy,12,5` est lue sans avertissement
    comme `12`. Utilisez `;` partout (`name;weight`, puis `Italy;12,5`), mettez la valeur entre guillemets
    (`Italy,"12,5"`), ou écrivez `Italy,12.5`.

## 🧲 Fusionner des actifs en double

Si le même instrument a fini par donner deux actifs, chacun détient une partie de son historique. Pour fusionner l'un dans
l'autre :

1. Sur la page **Actifs**, utilisez **Fusionner avec…** sur l'actif qui doit disparaître : le bouton sur
   sa carte, ou le menu contextuel dans le tableau.
2. Choisissez l'actif à conserver (y compris les actifs inactifs) et cliquez sur **Continuer**. Pour un jour où les deux ont un prix,
   le prix de l'actif conservé l'emporte ; de même pour son fournisseur de prix, s'il en a un.
3. Lisez **Ce qui est déplacé** : les décomptes exacts des transactions, des prix et des événements. Lorsque les deux actifs
   ont un code différent du même type, choisissez celui qui doit être principal.
4. Cliquez sur **Fusionner et supprimer**. Le premier actif est supprimé ; cette action est irréversible.

Aucun identifiant n'est perdu : chaque code de l'actif supprimé remplit un champ vide de l'actif conservé ou rejoint
ses **Autres identifiants**. Les événements identiques sont fusionnés.

Lors d'un import, lorsque deux de vos actifs portent l'ISIN d'un même titre, sa carte **Résoudre les actifs**
indique *Deux actifs enregistrés correspondent à ce titre* et propose **Fusionner**. La seule correspondance des noms ne le
déclenche jamais.

## 🔗 Voir aussi

- 📊 **[Page de détail de l'actif](detail/index.md)** — Consulter et analyser les données de l'actif
- 🔌 **[Fournisseurs](providers/index.md)** — Fournisseurs de prix disponibles
- 🧬 **[Identité de l'actif](../../developer/frontend/components/features/asset-identity.md)** — Pour les développeurs : comment fonctionnent les identifiants, les comparaisons avec le fournisseur et les fusions
