# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    Cet importateur est en **Alpha** : il a été construit à partir des exports d'un seul compte, partagés dans [l'issue #26](https://github.com/Librefolio/LibreFolio/issues/26). Si vos fichiers diffèrent, ou si une ligne est importée d'une manière qui semble incorrecte, veuillez ouvrir une nouvelle issue et mentionner #26.

LibreFolio importe le **compte d'épargne en actions** (*osakesäästötili*) de **Danske Bank Finlande**. La banque le divise en **deux exports**, et aucun ne suffit à lui seul :

- les **opérations sur titres** (XLSX) : les transactions, les dividendes et les scissions, avec les quantités et les prix — mais pas les dépôts, les retraits ni le solde ;
- le **relevé du compte espèces** (CSV) : chaque mouvement d'espèces et le solde — mais pas les quantités.

Vous les téléversez donc **ensemble** : LibreFolio les lit comme un seul **lot de rapports**, associe chaque transaction à son paiement et vérifie ses soldes par rapport à ceux de la banque.

---

## 📤 Ce qu'il faut exporter {: #what-to-export }

| Export (nom dans LibreFolio) | Où dans l'eBanking | Format | Jusqu'où remonter |
|:--|:--|:--|:--|
| **Opérations sur titres** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | au plus **un an** par export |
| **Relevé du compte espèces** | les transactions du compte espèces de votre compte d'épargne en actions | CSV | jusqu'à **cinq ans** |

- Opérations sur titres : **toute l'année** que la banque autorise.
- Relevé du compte espèces : la même période, à partir de la veille, et idéalement **quelques jours au-delà** de sa fin — les transactions sont réglées quelques jours ouvrés après leur réalisation.
- Importez les fichiers **tels que téléchargés**, sans les réenregistrer dans Excel.

---

## 🧺 Téléversez les deux fichiers ensemble

1. Ouvrez l'**[assistant d'importation](how-to.md)**, déposez **les deux** fichiers dans **Téléverser**, affectez-les à votre courtier Danske Bank et cliquez sur **Suivant : Sélectionner les fichiers**.
2. Dans **Sélectionner les fichiers**, les deux fichiers forment **une seule carte**, déjà cochée : vérifiez qu'elle indique **Complet**. Une note sur la carte vous indique ce que fera cet import.
3. Cliquez sur **Analyser** : LibreFolio fusionne les deux fichiers en un **fichier combiné** et l'analyse comme une seule ligne. Son détail, **Correspondance titres ↔ espèces**, montre comment les transactions ont été associées à leurs paiements, et pourquoi une ligne a été écartée.
4. Poursuivez comme d'habitude jusqu'à **Importer N transactions**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Carte du lot de rapports Danske Bank dans Sélectionner les fichiers : un tableau par type d'export, la chronologie des fichiers et Lire comme dans son en-tête" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Détail d'analyse du lot : Correspondance titres ↔ espèces, avec les pastilles de résultat et les raisons avec leur nombre de lignes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les fichiers téléversés ensemble depuis la page [Fichiers](../../files/index.md#broker-reports) ou via le formulaire **Rapports téléversés** d'un courtier forment eux aussi un lot.

Les exports téléversés avec une version de LibreFolio antérieure à 1.2 n'appartiennent à aucun lot et ne peuvent pas être lus seuls : l'assistant laisse **Analyser** désactivé tant que l'un d'eux est sélectionné. Téléversez à nouveau tous les exports du lot ensemble, en une seule fois, puis sélectionnez ce lot ; les anciennes copies peuvent être supprimées.

### 🧩 Si un fichier manque

- Vous n'avez déposé qu'un seul fichier ? **Suivant : Sélectionner les fichiers** vous maintient sur **Téléverser**, en nommant l'export manquant et sa période : déposez-le ici — il rejoint le **même lot** — et cliquez à nouveau sur **Suivant : Sélectionner les fichiers**.
- Vous continuez sans lui ? La carte affiche **Un fichier manque** et propose **Téléverser le fichier manquant**. Pendant ce temps, le lot coché bloque **Analyser** : décochez-le pour importer d'abord vos autres fichiers.
- Les fichiers téléversés à des moments différents **ne rejoignent jamais le même lot** : téléversez à nouveau le fichier manquant avec **Téléverser le fichier manquant** sur la bonne carte, puis supprimez l'ancienne copie isolée.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Carte du lot dans Sélectionner les fichiers affichant Un fichier manque : le relevé du compte espèces manquant, la période qu'il doit couvrir et Téléverser le fichier manquant" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 Comment le lot est lu {: #how-the-set-is-read }

Normalement, il n'y a rien à modifier : **Lire comme**, dans l'en-tête de la carte, affiche **Danske Bank (détecté)**. Si un fichier n'appartient pas au lot — par exemple, un relevé d'un autre compte téléversé par erreur — choisissez **Retirer du lot** dans son menu **⋮** : le fichier est déplacé, sans plugin, vers **Autres fichiers de ce courtier**, où vous le décochez. Pour le remettre, choisissez *Danske Bank* dans sa colonne **Plugin** à cet endroit (le choix apparaît une fois le fichier coché).

**Lire les fichiers un par un** ne sert à rien ici, car aucun autre importateur ne lit ces exports : si vous l'avez choisi, remettez chaque fichier de la même manière. Un lot coché en partie seulement — sa case à cocher affiche un tiret — bloque **Analyser** : cliquez une fois sur la case pour décocher le lot, deux fois pour le cocher entièrement.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Carte du lot avec la liste Lire comme ouverte : Danske Bank (détecté), sélectionné, et Lire les fichiers un par un" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Carte du lot Danske Bank dans Sélectionner les fichiers avec le menu ⋮ du relevé du compte espèces ouvert : Aperçu, Retirer du lot et Supprimer" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🗓️ Importez au moins une fois par an

L'export sur titres ne remonte qu'à un an ; importez donc **au moins une fois par an**, chaque nouvel export sur titres remontant jusqu'où le précédent s'arrêtait. Les chevauchements ne posent pas de problème : ce que LibreFolio détient déjà est masqué dans la **Vérification** (*N déjà dans LibreFolio (masqués)*) ou arrive décoché comme [doublon](index.md#duplicate-detection). Vous avez sauté plus d'un an ? Voir [Lacunes](#gaps).

!!! warning "Lots importés avec LibreFolio 1.2"

    LibreFolio 1.2 enregistrait chaque transaction au jour du mouvement d'argent ; il l'enregistre désormais au jour où vous l'avez réalisée, quelques jours plus tôt. Importées à nouveau, ces transactions ne seraient pas reconnues comme doublons et compteraient deux fois. Il faut donc, une fois, supprimer toutes les transactions Danske Bank créées par ces imports — y compris les corrections étiquetées `gap_fix` — et importer à nouveau tout le lot, ou n'importer qu'à partir du lendemain du dernier jour déjà importé : commencez l'export sur titres à cette date, et le relevé du compte espèces la veille, comme l'indique [Ce qu'il faut exporter](#what-to-export). À partir de là, les chevauchements redeviennent sans problème.

---

## 📝 Ce qui est importé

| Dans vos fichiers | Importé comme |
|:--|:--|
| Un achat (`Määrä` positif) et son paiement `Osto …` | **Achat** |
| Une vente (`Määrä` négatif) et son paiement `Myynti …` | **Vente** |
| `Tuotto` et son crédit | **Dividende** |
| `Nosto osakesäästötililtä` | **Retrait** |
| `Vero osakesäästötililtä` | **Impôt** |
| `Palvelumaksu…` (frais de service) | **Frais** |
| `Korko…` (intérêts) | **Intérêts** |
| Tout autre crédit (seul votre propre argent peut être versé) | **Dépôt** — un avis les liste |
| `Jakautuminen, vanha` / `uusi` (une scission) | **Ajustements** sans espèces — voir [Scissions](#demergers) |

- Chaque transaction est enregistrée au **jour où vous l'avez réalisée** (`Kauppapäivä`, la date de la transaction) : un achat effectué le 27 est un achat du 27, même si la banque déplace l'argent quelques jours ouvrés plus tard. Les dividendes et les scissions prennent eux aussi leur date dans l'export sur titres ; les dépôts, retraits, impôts, frais et intérêts gardent leur date dans le relevé du compte espèces. Les montants sont en **euros**, tels que la banque les a écrits.
- Les fichiers ne donnent ni ISIN ni ticker : confirmez chaque titre dans le [mappage des actifs](index.md#asset-mapping) de l'assistant.
- **Chaque ligne est prise en compte** : une ligne écartée — un paiement manquant, une transaction réglée après la fin du relevé du compte espèces… — est tout de même comptée dans le détail du lot, avec sa raison, et listée dans les avis de l'importateur, en **finnois** comme les fichiers. Deux cas sont traités différemment :
    - Les **réservations** (`Varaus` dans le relevé du compte espèces) sont des montants réservés que la banque remplace par le mouvement comptabilisé, et c'est ce mouvement qui est importé. Elles sont comptées dans le détail du lot comme *réservées, non comptabilisées*, mais ne figurent pas dans les avis : il n'y a rien à vérifier.
    - **Un statut que LibreFolio ne connaît pas** : une ligne dont le `Tila` n'est ni exécuté (`Toteutettu`) ni comptabilisé (`Toteutunut`) — un ordre non exécuté, par exemple — est écartée avec un **avertissement** et un lien pour **ouvrir une issue sur GitHub**. Merci d'en ouvrir une, en indiquant le `Tila` que vous voyez, afin que l'importateur apprenne à le gérer. En attendant, si l'une de ces lignes est un mouvement réel, ajoutez-le à la main.
- Vérifiez les transactions appariées qu'un avis signale parce que leurs noms diffèrent.

### 💶 Les frais sont inclus dans les montants des transactions

Les fichiers donnent **un total par transaction**, commission incluse ; l'étape **Corrections** demande donc, pour chaque achat et chaque vente :

- **Séparer le prix des frais ?**, puis **Appliquer la correction** — pour un titre libellé en euros, LibreFolio suggère la commission probable ; le montant exact figure sur la confirmation de transaction dans l'eBanking ;
- ou **Conserver tel qu'enregistré** : la transaction garde son montant total (votre trésorerie est juste dans les deux cas).

Chaque transaction nécessite un choix ; **Conserver les N lignes restantes telles quelles** règle le reste en un clic.

### ✂️ Scissions {: #demergers }

Une scission (`Jakautuminen`) arrive sous forme d'**ajustements sans espèces** : l'ancienne ligne (`vanha`) retire vos anciennes actions, chaque nouvelle ligne (`uusi`) en ajoute de nouvelles. Dans l'éditeur, chaque nouvelle ligne a besoin de son **coût par action** (**Tout enregistrer** l'attend) : le coût de vos anciennes actions × le pourcentage de la ligne publié par l'administration fiscale finlandaise ([vero.fi](https://www.vero.fi/)), divisé par son nombre d'actions.

---

## 🏁 Premier import : s'aligner sur la banque {: #first-import-align-with-the-bank }

Lors du premier import, tout ce qui précède le premier jour de votre export sur titres est résumé dans un **point de départ** à la fin de la journée précédente ; ensuite, chaque mouvement est importé un par un. La carte du lot vous indique la date.

Après la **Vérification**, **Importer N transactions** peut ouvrir **S'aligner sur la banque** : il compare ce que LibreFolio détiendra avec ce que la banque déclare, et propose ce qui comble l'écart — un **Dépôt** ou un **Retrait** qui amène la trésorerie au solde du relevé du compte espèces, et un **Ajustement** pour chaque position que vos fichiers prouvent.

LibreFolio enregistre une transaction au jour où vous l'avez réalisée, tandis que le solde de la banque ne change qu'au règlement de la transaction, quelques jours ouvrés plus tard. Chaque comparaison compte donc les transactions importées déjà réalisées mais pas encore réglées ce jour-là, et les deux côtés parlent de la même chose.

1. Les cartes en haut montrent chaque point — le **Point de départ**, un point **Après la lacune** pour chaque [lacune](#gaps), la [Vérification de fin de période](#end-of-period-check). Cliquez sur l'une pour voir sa comparaison et seulement ses corrections ; cliquez à nouveau dessus pour les voir toutes.
2. Les corrections, étiquetées `gap_fix`, sont **sélectionnées par défaut** : décochez celles que vous ne voulez pas (ou utilisez **Tout sélectionner**, **Sélectionner les visibles**, **Tout désélectionner**), puis cliquez sur **Continuer**.
3. Dans l'éditeur, saisissez le **coût par action** de chaque position marquée *coût à saisir* — le site web de la banque indique le prix d'achat moyen de chaque position. **Tout enregistrer** l'attend.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="S'aligner sur la banque : les cartes Point de départ, Après la lacune et Vérification de fin de période au-dessus des corrections proposées étiquetées gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

L'étape ne s'ouvre **que s'il y a quelque chose à montrer** — généralement pas après un import annuel qui chevauche le précédent. L'historique saisi à la main compte : seule la différence est proposée. Si la comparaison avec la banque échoue, vous pouvez **Continuer** sans corrections.

### 📅 Si votre relevé du compte espèces commence plus tard {: #cash-statement-starts-later }

Si votre relevé du compte espèces commence **après** le premier jour de votre export sur titres, le point de départ tombe tout de même la veille de l'export sur titres, et reprend le solde à partir duquel votre relevé du compte espèces commence.

- Une transaction réalisée avant le début du relevé du compte espèces et réglée à l'intérieur de celui-ci est importée comme d'habitude, au jour où vous l'avez réalisée.
- Une transaction déjà réglée avant le début du relevé du compte espèces ne figure pas dans le relevé et ne peut donc pas être importée individuellement : un avis la liste, et le détail du lot la compte comme *réglée avant le début du relevé du compte espèces*. Son argent est déjà dans le solde à partir duquel le relevé commence ; elle aboutit donc dans le point de départ, quelques jours avant le jour où vous l'avez réalisée. Ses actions aussi, lorsque vos fichiers prouvent la position — un dividende, par exemple ; sinon, vérifiez ce titre sur le site web de la banque (voir [Limites](#limits)).

Pour que chaque transaction soit importée à son propre jour, exportez le relevé du compte espèces à partir de la veille de l'export sur titres, comme l'indique [Ce qu'il faut exporter](#what-to-export).

### ✅ Vérification de fin de période {: #end-of-period-check }

La dernière carte compare votre trésorerie avec le solde du relevé du compte espèces à la fin de la dernière période de titres — en comptant, comme les autres points, les transactions importées réalisées mais pas encore réglées ce jour-là : **Correspond** ou **Ne correspond pas**. Elle n'est **jamais corrigée** : votre prochain import apportera les transactions des derniers jours, absentes de votre trésorerie jusque-là. Si elle ne correspond pas, ajoutez à la main le mouvement que l'import a omis (voir le détail du lot dans **Analyser**).

---

## 🕳️ Lacunes entre les exports sur titres {: #gaps }

Une **lacune** est une période qu'aucun export sur titres ne couvre alors que le relevé du compte espèces y montre des transactions — vous avez sauté plus d'un an, ou laissé un trou entre deux exports sur titres. Sans quantités, ces transactions ne peuvent pas être reconstituées :

- les dépôts, retraits, impôts, frais et intérêts de la lacune sont importés avec leur propre date ;
- ses transactions sont résumées dans les corrections **Après la lacune** ;
- les titres achetés ou vendus pendant la lacune doivent être vérifiés sur le site web de la banque et corrigés à la main.

La carte du lot vous avertit d'un tel trou : si la banque possède encore cette période, exportez-la et téléversez-la avec les autres.

---

## ⚠️ Limites {: #limits }

- **Titres qui n'apparaissent jamais** : les positions ne sont prouvées que par un dividende, l'ancienne ligne d'une scission ou une vente de plus d'actions que vous n'en avez acheté (*au moins N*). Un titre qui n'a pas bougé et n'a versé aucun dividende reste invisible : vérifiez vos positions sur le site web de la banque et ajoutez les manquantes à la main.
- **Capital investi** : une correction de position négative, ou l'ancienne ligne d'une scission, retire des actions sans réduire votre capital investi.
- **Pas de retour en arrière** : un export sur titres antérieur à l'historique que LibreFolio détient pour le courtier n'est pas importé ; la carte du lot le signale.
- **Corrections antérieures** : si un nouveau lot couvre la date d'une correction `gap_fix` importée auparavant, supprimez cette correction après l'import, comme la carte le demande — sinon la trésorerie compte deux fois.

## 🔗 Référence développeur

→ [Importateur Danske Bank (référence développeur)](../../../developer/backend/brim/danske_bank.md)
