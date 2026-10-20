# 📥 <img src="https://danskebank.fi/favicon.ico" alt=""> Danske Bank

!!! info "Alpha"

    Cet importateur est en **Alpha** : il a été conçu à partir des exports d'un seul compte, partagés dans [l'issue #26](https://github.com/Librefolio/LibreFolio/issues/26). Si vos fichiers sont différents, ou si une ligne est importée d'une manière qui semble incorrecte, merci d'ouvrir une nouvelle issue en mentionnant #26.

LibreFolio importe le **compte d'épargne-actions** (*osakesäästötili*) de **Danske Bank Finland**. La banque le divise en **deux exports**, et aucun n'est suffisant à lui seul :

- les **opérations sur titres** (XLSX) : opérations, dividendes et scissions, avec les quantités et les prix — mais sans dépôts, retraits ni solde ;
- le **relevé du compte espèces** (CSV) : chaque mouvement de trésorerie et le solde — mais sans quantités.

Vous les importez donc **ensemble** : LibreFolio les lit comme un seul **lot de rapports**, associe chaque opération à son paiement et vérifie ses soldes par rapport à ceux de la banque.

---

## 📤 Quoi exporter

| Export (nom dans LibreFolio) | Où dans l'eBanking | Format | Jusqu'à quand remonter |
|:--|:--|:--|:--|
| **Opérations sur titres** (`Transactions.xlsx`) | **Sijoitukset → Tapahtumat** | XLSX | au plus **un an** par export |
| **Relevé du compte espèces** | les transactions du compte espèces de votre compte d'épargne-actions | CSV | jusqu'à **cinq ans** |

- Opérations sur titres : **l'année entière** que la banque autorise.
- Relevé du compte espèces : la même période, à partir de la veille, et idéalement **quelques jours après** sa fin — les opérations sont réglées quelques jours ouvrés après leur réalisation.
- Importez les fichiers **tels que téléchargés**, sans les réenregistrer dans Excel.

---

## 🧺 Importer les deux fichiers ensemble

1. Ouvrez l'**[Assistant d'importation](how-to.md)**, déposez **les deux** fichiers dans **Téléverser**, affectez-les à votre courtier Danske Bank et cliquez sur **Suivant : Sélectionner**.
2. Dans **Sélectionner**, les deux fichiers forment **une seule carte**, déjà cochée : vérifiez qu'elle indique **Complet**. Une note sur la carte vous indique ce que cet import va faire.
3. Cliquez sur **Analyser** : LibreFolio fusionne les deux fichiers en un **fichier combiné** et l'analyse comme une seule ligne. Son détail, **Rapprochement titres ↔ espèces**, montre comment les opérations ont été associées à leurs paiements, et pourquoi une ligne a été écartée.
4. Continuez comme d'habitude jusqu'à **Importer N transactions**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-card" alt="Carte du lot de rapports Danske Bank dans Select Files : un tableau par type d'export, la chronologie des fichiers et Read as dans son en-tête" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-pairing" alt="Détail Parse du lot : Matching securities ↔ cash, avec les puces de résultat et les raisons avec leur nombre de lignes" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Les fichiers importés ensemble depuis la page [Fichiers](../../files/index.md#broker-reports) ou les **Rapports téléversés** d'un courtier forment eux aussi un lot de rapports.

Les exports importés avec une version de LibreFolio antérieure à 1.2 ne font partie d'aucun lot de rapports et ne peuvent pas être lus seuls : l'assistant d'importation garde **Analyser** désactivé tant que l'un d'eux est sélectionné. Importez à nouveau tous les exports du lot ensemble, en une seule fois, puis sélectionnez ce lot ; les anciennes copies peuvent être supprimées.

### 🧩 Si un fichier manque

- Vous n'avez déposé qu'un seul fichier ? **Suivant : Sélectionner** vous maintient sur **Téléverser**, en nommant l'export manquant et sa période : déposez-le là — il rejoint le **même lot** — et cliquez à nouveau sur **Suivant : Sélectionner**.
- Vous continuez sans lui ? La carte affiche **Il manque un fichier** et propose **Téléverser le fichier manquant**. Pendant ce temps, le lot coché bloque **Analyser** : décochez-le pour importer d'abord vos autres fichiers.
- Les fichiers importés à des moments différents **ne se rejoignent jamais** : importez à nouveau le fichier manquant avec **Téléverser le fichier manquant** sur la bonne carte, puis supprimez la copie isolée précédente.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-missing" alt="Carte de lot dans Select Files affichant A file is missing : le relevé du compte espèces manquant, la période qu'il doit couvrir et Upload the missing file" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🔀 Comment le lot est lu {: #how-the-set-is-read }

Normalement, il n'y a rien à modifier : **Lu comme**, dans l'en-tête de la carte, affiche **Danske Bank (détecté)**. Si un fichier n'appartient pas au lot — par exemple, un relevé d'un autre compte importé par erreur — choisissez **Retirer du lot** dans son menu **⋮** : le fichier se déplace, sans plugin, sous **Autres fichiers de ce courtier**, où vous le décochez. Pour le remettre, choisissez *Danske Bank* dans sa colonne **Plugin** à cet endroit (le choix apparaît une fois le fichier coché).

**Lire les fichiers un par un** est inutile ici, car aucun autre importateur ne lit ces exports : si vous l'avez choisi, remettez chaque fichier de la même manière. Un lot coché seulement en partie — sa case à cocher affiche un tiret — bloque **Analyser** : cliquez une fois sur la case pour décocher le lot, deux fois pour le cocher entièrement.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-read-as" alt="Carte de lot avec la liste Lu comme ouverte : Danske Bank (détecté), sélectionné, et Lire les fichiers un par un" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-report-set-file-menu" alt="Carte de lot Danske Bank dans Select Files avec le menu ⋮ du relevé du compte espèces ouvert : Preview, Remove from the set et Delete" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🗓️ Importer au moins une fois par an

L'export des titres ne remonte qu'à un an, importez donc **au moins une fois par an**, chaque nouvel export de titres remontant jusqu'à là où le précédent s'est arrêté. Les chevauchements ne posent pas problème : ce que LibreFolio détient déjà est masqué dans la **Révision** (*N already in LibreFolio (hidden)*) ou arrive décoché en tant que [doublon](index.md#duplicate-detection). Vous avez sauté plus d'un an ? Voir [Gaps](#gaps).

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
| `Korko…` (intérêts) | **Intérêt** |
| Tout autre crédit (seul votre propre argent peut être versé) | **Dépôt** — un avis les liste |
| `Jakautuminen, vanha` / `uusi` (une scission) | **Ajustements** sans trésorerie — voir [Demergers](#demergers) |

- Chaque transaction reçoit sa **date de valeur** (le jour où l'argent ou les actions ont bougé) et son montant en **euros**, tel que la banque l'a écrit.
- Les fichiers ne donnent ni ISIN ni ticker : confirmez chaque titre dans le [mappage des actifs](index.md#asset-mapping) de l'assistant d'importation.
- **Aucune ligne ne se perd** : une ligne exclue — un paiement manquant, une opération réglée après la fin du relevé… — reste comptée dans le détail du lot, avec son motif, et les avis de l'importateur, en **finnois** comme les fichiers, listent celles à vérifier. Vérifiez les opérations appariées qu'un avis signale parce que leurs noms diffèrent.

### 💶 Les frais sont inclus dans les montants des opérations

Les fichiers donnent **un total par opération**, commission incluse, donc l'étape **Corrections** demande, pour chaque achat et chaque vente :

- **Séparer le prix des frais ?**, puis **Appliquer la correction** — pour un titre libellé en euros, LibreFolio propose la commission probable ; le chiffre exact figure sur la confirmation d'opération dans l'eBanking ;
- ou **Garder tel quel** : l'opération conserve son montant entier (votre trésorerie est correcte dans les deux cas).

Chaque opération nécessite un choix ; **Conserver les N lignes restantes telles quelles** règle le reste en un clic.

### ✂️ Scissions {: #demergers }

Une scission (`Jakautuminen`) arrive sous forme d'**ajustements sans trésorerie** : l'ancienne ligne (`vanha`) retire vos anciennes actions, chaque nouvelle ligne (`uusi`) en ajoute de nouvelles. Dans l'éditeur, chaque nouvelle ligne a besoin de son **coût par action** (**Enregistrer Tout** l'attend) : le coût de vos anciennes actions × le pourcentage de la ligne publié par l'administration fiscale finlandaise ([vero.fi](https://www.vero.fi/)), divisé par son nombre d'actions.

---

## 🏁 Premier import : s'aligner avec la banque {: #first-import-align-with-the-bank }

Lors du premier import, tout ce qui précède le premier jour de votre export de titres est résumé en un **point de départ** à la fin de la veille ; à partir de là, chaque mouvement est importé un par un. La carte du lot vous indique la date.

Après la **Révision**, **Importer N transactions** peut ouvrir **Aligner avec la banque** : il compare ce que LibreFolio détiendra avec ce que la banque déclare, et propose ce qui comble l'écart — un **Dépôt** ou un **Retrait** qui amène la trésorerie au solde du relevé du compte espèces, et un **Ajustement** pour chaque position que vos fichiers prouvent.

1. Les cartes en haut affichent chaque point — le **Point de départ**, un point **Après la période manquante** par [lacune](#gaps), le [Contrôle de fin de période](#end-of-period-check). Cliquez sur l'une pour voir sa comparaison et uniquement ses corrections ; cliquez à nouveau pour les voir toutes.
2. Les corrections, étiquetées `gap_fix`, sont **sélectionnées par défaut** : décochez celles que vous ne voulez pas (ou utilisez **Tout sélectionner**, **Sélectionner visibles**, **Tout désélectionner**), puis cliquez sur **Continuer**.
3. Dans l'éditeur, saisissez le **coût par action** de chaque position marquée *coût à saisir* — le site web de la banque affiche le prix d'achat moyen de chaque position. **Enregistrer Tout** l'attend.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="import-wizard-gapfix-step" alt="Align with the bank : les cartes Starting point, After the gap et End-of-period check au-dessus des corrections proposées étiquetées gap_fix" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

L'étape ne s'ouvre **que lorsqu'il y a quelque chose à montrer** — généralement pas après un import annuel qui chevauche le précédent. L'historique que vous avez saisi à la main compte : seule la différence est proposée. Si la comparaison avec la banque échoue, vous pouvez **Continuer** sans corrections.

### ✅ End-of-period check

La dernière carte compare votre trésorerie avec le solde du relevé à la fin de la dernière période de titres : **Concorde** ou **Ne concorde pas**. Elle n'est **jamais corrigée** : votre prochain import apportera les opérations des derniers jours, absentes de votre trésorerie jusque-là. Si elle ne correspond pas, ajoutez à la main le mouvement que l'import a omis (voir le détail du lot dans **Analyser**).

---

## 🕳️ Lacunes entre les exports de titres {: #gaps }

Une **lacune** est une période qu'aucun export de titres ne couvre alors que le relevé du compte espèces y montre des opérations — vous avez sauté plus d'un an, ou laissé un trou entre deux exports de titres. Sans quantités, ces opérations ne peuvent pas être reconstruites :

- les dépôts, retraits, impôts, frais et intérêts de la lacune sont importés avec leur propre date ;
- ses opérations sont résumées dans les corrections **Après la période manquante** ;
- les titres achetés ou vendus dans la lacune doivent être vérifiés sur le site web de la banque et corrigés à la main.

La carte du lot vous avertit d'un tel trou : si la banque dispose encore de cette période, exportez-la et importez-la avec les autres.

---

## ⚠️ Limites {: #limits }

- **Titres qui ne se manifestent jamais** : les positions ne sont prouvées que par un dividende, l'ancienne ligne d'une scission, ou une vente d'un nombre d'actions supérieur à celui que vous avez acheté (*at least N*). Un titre qui n'a pas bougé et n'a versé aucun dividende ne peut pas être détecté : vérifiez vos positions sur le site web de la banque et ajoutez à la main celles qui manquent.
- **Capital investi** : une correction de position négative, ou l'ancienne ligne d'une scission, retire des actions sans réduire votre capital investi.
- **Pas de retour en arrière** : un export de titres antérieur à l'historique que LibreFolio détient pour le courtier n'est pas importé ; la carte du lot le précise.
- **Corrections antérieures** : si un nouveau lot couvre la date d'une correction `gap_fix` importée auparavant, supprimez cette correction après l'import, comme le demande la carte — sinon la trésorerie est comptée deux fois.

## 🔗 Référence développeur

→ [Importateur Danske Bank (référence développeur)](../../../developer/backend/brim/danske_bank.md)
