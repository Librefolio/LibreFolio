# ➕ Créer et modifier des actifs

Ajoutez un instrument que vous détenez ou suivez, connectez-le à un fournisseur de prix et maintenez ses informations à jour.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulaire de création manuelle" alt="Modale de création manuelle">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulaire de création automatique de l'assistant d'importation" alt="Créer un actif depuis l'assistant d'importation">
</div>

## 🚀 Créer un actif {: #asset-creation-flows }

=== "Depuis la page Actifs"

    1. Sur la page **Actifs**, cliquez sur **+ Ajouter un actif**.
    2. Dans **Rechercher en ligne**, saisissez un nom, un ticker ou un ISIN et sélectionnez un résultat : LibreFolio remplit le
       formulaire, connecte ce fournisseur et [vérifie ses données](#provider-data-comparison). Aucun résultat ?
       Remplissez le formulaire vous-même.
    3. Vérifiez les champs ci-dessous, puis cliquez sur **Créer l'actif**.

=== "Depuis un import de courtier"

    1. Dans la section **Résoudre les actifs** de l'assistant d'importation, choisissez **Créer un nouvel actif** dans le
       sélecteur du titre.
    2. Le formulaire s'ouvre avec les codes et les noms du rapport. Si le rapport n'a pas de nom, le champ **Nom**
       commence par l'ISIN (ou le ticker).
    3. Cliquez sur l'une des **Suggestions** sous **Rechercher en ligne** pour rechercher le titre, ou remplissez
       le formulaire vous-même. Cliquez ensuite sur **Créer l'actif**.

    Si le résultat que vous sélectionnez porte le même nom que l'un de vos actifs, LibreFolio vous propose d'utiliser cet
    actif à la place ; **L'utiliser et ajouter la clé** enregistre aussi les codes du rapport dessus.

Vérifiez ces champs avant d'enregistrer :

- **Nom** : obligatoire et unique ; un avertissement apparaît si un autre actif l'utilise déjà.
- **Type** : voir [Choisir le type d'actif](#choosing-the-asset-type).
- **Unités par prix** : le nombre d'unités auxquelles se réfère un prix, généralement 1. Les obligations sont cotées sur une base
  100 : LibreFolio le propose lorsque vous choisissez **Obligation**.
- **Devise** : la devise dans laquelle les prix sont cotés. Pour un fonds coté en euros, il s'agit de l'EUR,
  même lorsque le fonds est libellé dans une autre devise.

Après l'enregistrement depuis la page **Actifs**, la confirmation renvoie vers le nouvel actif. Si l'actif a un
fournisseur, son historique de prix commence à se télécharger immédiatement.

## 🗂️ Choisir le type d'actif {: #choosing-the-asset-type }

Le champ **Type** ouvre un menu avec recherche des
[types d'actifs](../../financial-theory/instruments/asset-types/index.md). **ETF** et
**Crowdfunding** sont des familles : ouvrez-en une pour voir d'abord son membre générique (**ETF**, **Crowdfund**),
puis des types spécifiques tels que **ETF actions** ou **Crowdfunding immobilier**. Saisissez quelques lettres pour
rechercher dans les deux niveaux, par nom ou par code (par exemple `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Menu Type avec la famille ETF déployée, chaque type d'ETF spécifique affichant son icône composite">
</div>

**Rechercher en ligne** définit généralement un type général tel que **ETF**. Si vous connaissez la composition du fonds,
précisez-le, par exemple en **ETF actions** : son badge et son icône indiquent alors ce qu'il contient. Une
[vérification ultérieure des données du fournisseur](#provider-data-comparison) conserve votre choix.

## 🔌 Connecter un fournisseur de prix

Sélectionner un résultat de **Rechercher en ligne** connecte son fournisseur pour vous. Pour en configurer un à la main, développez
**Attribution du fournisseur** (décochez d'abord **Aucun fournisseur** s'il est coché) :

1. Choisissez le **Fournisseur**, puis saisissez l'**Identifiant**, son **Type d'identifiant** et les paramètres
   demandés par le fournisseur.
2. Cliquez sur **Tester la configuration** : LibreFolio récupère un **Prix actuel** et quelques jours
   d'**Historique**. ⚠️ signifie que le fournisseur ne propose pas ces données ou n'en a aucune pour le moment (le CSS Scraper
   n'a pas d'historique, par exemple) ; le test réussit quand même. ❌ est une erreur : vérifiez l'identifiant et
   les paramètres.

Un actif a au plus un fournisseur ; cochez **Aucun fournisseur** si vous comptez saisir ses prix vous-même. Voir
[Fournisseurs](providers/index.md) pour ce que chacun propose.

## ⚖️ Vérifier les données du fournisseur {: #provider-data-comparison }

LibreFolio compare les informations du fournisseur avec votre formulaire après avoir sélectionné un résultat de **Rechercher en ligne**,
et lorsque vous cliquez sur **Interroger le fournisseur** : en haut de **Détails de l'actif** pour tout, à côté
des **Identifiants** ou dans un éditeur de distribution pour cette partie uniquement. Il faut un fournisseur et un
identifiant.

- Les champs vides sont remplis, et les codes supplémentaires du fournisseur rejoignent **Autres identifiants**.
- *Le fournisseur n'a pas de données pour : …* nomme une distribution sectorielle ou géographique manquante ; *Toutes les données correspondent
  au fournisseur* signifie qu'il n'y a rien à vérifier.
- Tout élément qui diffère ouvre la boîte de dialogue **Comparaison des données du fournisseur**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-provider-compare" alt="La boîte de dialogue Comparaison des données du fournisseur par-dessus le formulaire Ajouter un actif : la ligne TICKER demandant quel code est le principal, avec le code du fournisseur choisi à la place de celui déjà enregistré, conservé comme code alternatif ; la ligne Type avec ses valeurs actuelles et fournisseur sous forme de badges d'icônes ; la ligne Distribution sectorielle, valeur actuelle contre valeur du fournisseur ; et les boutons Tout sélectionner, Tout désélectionner, Annuler et Appliquer la sélection">
</div>

Chaque ligne de la boîte de dialogue affiche votre **Valeur actuelle** à côté de la **Valeur du fournisseur**, et est cochée
par défaut :

1. Décochez les lignes pour lesquelles vous souhaitez conserver votre valeur (**Tout sélectionner** et **Tout désélectionner** vous aident).
2. Sur une ligne d'identifiant, choisissez le code principal ; l'autre est conservé sous **Autres identifiants** (voir
   [Modifier les identifiants](#one-instrument-several-codes)). Le code du fournisseur est proposé, car il s'agit
   normalement de celui qui est coté.
3. Cliquez sur **Appliquer la sélection**, qui compte les lignes que vous prenez (par exemple *Appliquer la sélection (2/3)*),
   ou sur **Annuler** pour ne rien modifier.

Les valeurs acceptées ne font que remplir le formulaire : elles sont enregistrées lorsque vous sauvegardez l'actif.

- **Votre type affiné est conservé.** Borsa Italiana, par exemple, déclare chaque instrument ETFplus comme un simple **ETF** :
  si vous avez choisi **ETF actions**, cela compte comme un accord et aucune ligne n'apparaît (il en va de même pour
  **Crowdfunding**). Un type *plus spécifique* que le vôtre est tout de même proposé.
- **Chaque question n'est posée qu'une fois.** Lorsqu'un résultat de recherche apporte un ISIN (ou un autre code) différent
  de celui du formulaire, LibreFolio demande d'abord lequel est le principal, et la comparaison ne
  le redemande pas.

## 🛠️ Modifier un actif {: #editing-an-asset }

Sur la [page de détail](detail/index.md) de l'actif, cliquez sur **Modifier** (✏️), changez ce dont vous avez besoin dans le
formulaire **Modifier l'actif**, puis cliquez sur **Enregistrer les modifications**.

Une nouvelle **Devise** pour un actif qui possède déjà des prix implique la suppression de ses prix et
événements enregistrés : lors de l'enregistrement, une boîte de dialogue liste ce qui disparaît (les transactions restent) et propose une sauvegarde. Après
**Supprimer et changer la devise**, les prix sont téléchargés à nouveau depuis le fournisseur, si l'actif en a un.

## 🏷️ Modifier les identifiants {: #one-instrument-several-codes }

Un même titre peut avoir plusieurs codes. LibreFolio conserve **un seul actif** avec tous, sous
**Plus d'informations** dans le formulaire de l'actif :

- **Identifiants** : les codes principaux, un par type (ISIN, ticker…). **Ajouter un identifiant** ajoute une ligne et
  **Interroger le fournisseur** les récupère.
- **Autres identifiants** : tout code supplémentaire ou libellé de courtier. Saisissez-en un et appuyez sur Entrée, virgule, point-virgule
  ou Tabulation. Ces codes sont recherchables et aident à reconnaître l'actif lors d'imports ultérieurs.

!!! tip "Conserver le code coté comme ISIN principal"

    Un prix est la valeur de la dernière transaction, donc seul un code négociable a un prix. Placez ce code dans
    **ISIN** et tout le reste dans **Autres identifiants**, sinon aucun fournisseur ne pourra établir le prix de l'actif.

### 🏛️ Obligations d'État italiennes pour particuliers (BTP Valore, BTP Più, BTP Italia)

Ces obligations sont souscrites sous un ISIN et négociées sous un autre :

| Phase | Code | Rôle |
|---|---|---|
| Souscription à l'émission | l'ISIN « CUM » | Vous donne droit à la **prime de fidélité** si vous conservez jusqu'à l'échéance. **Non négociable**, donc aucun fournisseur ne le cote |
| Marché secondaire | un ISIN différent | Librement négocié et **coté** : c'est celui qui a un prix |

Pour vendre avant l'échéance, l'obligation est convertie vers le code de marché. Conservez les deux codes sur un seul actif :

1. Placez l'**ISIN de marché** dans **ISIN**.
2. Placez l'**ISIN CUM** dans **Autres identifiants**.
3. Enregistrez la **prime de fidélité**, lorsqu'elle est versée, comme une transaction d'**Intérêt** sur cet actif.
   Cela fonctionne aussi après l'échéance : un actif désactivé reste sélectionnable.

Lorsqu'un import apporte le code CUM pour un actif qui détient celui du marché, LibreFolio demande quel
code doit primer et conserve l'autre sous **Autres identifiants**.

## 🗺️ Définir les distributions sectorielles et géographiques

Les fournisseurs remplissent les distributions sectorielles et géographiques lorsqu'ils le peuvent ; pour les autres actifs, définissez-les
vous-même. Elles alimentent les graphiques d'allocation du tableau de bord et l'export IA.

Dans le formulaire de l'actif, développez **Plus d'informations** : sous **Classification**, **Distribution sectorielle** et
**Distribution géographique** comportent une ligne par secteur ou pays, avec son poids en pourcentage.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Distribution sectorielle" alt="Éditeur de distribution sectorielle dans la modale de l'actif">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Distribution géographique" alt="Éditeur de distribution géographique dans la modale de l'actif">
</div>

- **Ajouter un secteur** / **Ajouter un pays** ajoute une ligne : choisissez l'entrée, puis saisissez son poids.
- Le **Total** devient vert à 100 %, ambre lorsqu'il manque quelque chose, rouge lorsque vous dépassez.
- **Équilibrer à 100 %**, une action de ligne, déplace tout l'écart dans cette ligne. **Équilibrer les lignes sélectionnées**
  le répartit entre les lignes sélectionnées, proportionnellement à leurs poids.
- **Supprimer** efface une ligne, **Interroger le fournisseur** récupère la distribution du fournisseur, et **Importer un CSV**
  en charge une depuis un fichier.

### 📥 Importer une distribution depuis un CSV {: #importing-a-distribution-csv }

**Importer un CSV** attend un en-tête `name,weight`, puis une ligne par pays ou secteur, avec les poids en
pourcentage :

```csv
name,weight
USA,60
Italy,40
```

- Les **Noms** doivent correspondre exactement, en ignorant la casse et les espaces environnants. Pays : un code ISO
  (`IT`, `ITA`) ou le nom dans votre langue. Secteurs : la clé de secteur (telle que `Government Bonds`)
  ou le nom dans votre langue.
- Les **Poids** vont de `0` à `100` et doivent totaliser 100 (à 0,005 point près) ; chaque nom apparaît
  une seule fois.
- L'import est **tout ou rien** : une seule mauvaise ligne le bloque. Lorsqu'il réussit, il **remplace** toute la
  distribution.

!!! warning "Virgules décimales"

    Le séparateur, `,` ou `;`, est lu depuis l'en-tête. Avec `,`, la ligne `Italy,12,5` est silencieusement
    lue comme `12`. Utilisez `;` partout (`name;weight`, puis `Italy;12,5`), mettez la valeur entre guillemets
    (`Italy,"12,5"`), ou écrivez `Italy,12.5`.

## 🧲 Fusionner des actifs en double

Si le même instrument a fini sous forme de deux actifs, chacun détient une partie de son historique. Pour en fondre un dans
l'autre :

1. Sur la page **Actifs**, utilisez **Fusionner avec…** sur l'actif qui doit disparaître : le bouton sur
   sa carte, ou le menu contextuel dans le tableau.
2. Choisissez l'actif à conserver (les inactifs aussi) et cliquez sur **Continuer**. Un jour où les deux ont un prix,
   le prix de l'actif conservé l'emporte ; son fournisseur de prix aussi, s'il en a un.
3. Lisez **Ce qui est déplacé** : les décomptes exacts de transactions, prix et événements. Lorsque les deux actifs
   ont un code différent du même type, choisissez celui qui prime.
4. Cliquez sur **Fusionner et supprimer**. Le premier actif est supprimé ; cette action est irréversible.

Aucun identifiant n'est perdu : chaque code de l'actif supprimé remplit un champ vide de l'actif conservé ou rejoint
ses **Autres identifiants**. Les événements identiques sont fusionnés.

Lors d'un import, lorsque deux de vos actifs portent l'ISIN d'un titre, sa carte **Résoudre les actifs**
indique *Deux actifs enregistrés correspondent à ce titre* et propose **Fusionner**. Le simple fait que les noms correspondent ne
le déclenche jamais.

## 🔗 Liens connexes

- 📊 **[Page de détail de l'actif](detail/index.md)** — Consulter et analyser les données d'un actif
- 🔌 **[Fournisseurs](providers/index.md)** — Fournisseurs de prix disponibles
- 🧬 **[Identité de l'actif](../../developer/frontend/components/features/asset-identity.md)** — Pour les développeurs : fonctionnement des identifiants, des comparaisons de fournisseurs et des fusions
