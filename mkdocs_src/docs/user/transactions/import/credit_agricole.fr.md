# 📥 <img src="https://www.credit-agricole.it/favicon.ico" alt=""> Crédit Agricole

Crédit Agricole est à la fois votre **banque et votre courtier**. L'import principal est la **Lista movimenti** du compte : les **deux dernières années** de trésorerie réelle — salaire ou pension, virements, factures, impôts, frais, coupons et dividendes.

## 💳 Exporter les mouvements du compte

### 📄 Étape 1 — Ouvrir la liste des mouvements

Dans la banque en ligne, ouvrez **Conti** dans le menu supérieur et choisissez **Lista movimenti**. Si vous avez plusieurs comptes, sélectionnez le vôtre dans **Seleziona rapporto**.

![Crédit Agricole — accueil, section activité du compte courant](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/01C_CA_HomeContiMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Étape 2 — Choisir la période

Cliquez sur **Ricerca avanzata**, définissez **Data contabile (Dal)** et **Data contabile (Al)** sur la plus large plage autorisée par la banque (deux ans), puis cliquez sur **CERCA**.

![Crédit Agricole — liste des mouvements du compte](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/02C_CA_ListaMovimentiConti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 💾 Étape 3 — Télécharger le fichier

Sous la liste, cliquez sur **SCARICA EXCEL** ou **SCARICA CSV**, et importez le fichier sans l'ouvrir ni le modifier.

![Crédit Agricole — export des mouvements du compte avec avertissement sur la période](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/03C_CA_ExportMovimentiContiConWarning.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

??? warning "✂️ Export par blocs — quand la banque n'affiche que les premiers résultats"

    Lorsque la liste indique **Stai visualizzando i primi … risultati**, elle a été tronquée et les mouvements les plus anciens manquent. Exportez la période par blocs :

    1. Téléchargez le bloc tel quel.
    2. Notez la date de son mouvement le plus **ancien**.
    3. Définissez **Data contabile (Al)** sur cette date, cliquez sur **CERCA** et téléchargez à nouveau.
    4. Répétez jusqu'à ce qu'un bloc atteigne le début de votre période.

    Importez tous les blocs ensemble. Le jour où deux blocs se rejoignent figure dans les deux fichiers : l'étape **Doublons** de l'assistant d'importation n'en conserve qu'une copie ([comment ça marche](how-to.md#only-when-needed)).

### 💰 Étape 4 — Ajouter le solde initial

L'export liste les mouvements, pas la trésorerie que vous possédiez déjà ; la trésorerie du courtier partirait donc de zéro. Lisez **Saldo Iniziale** et **Data dal** en haut de l'export Excel, et ajoutez un **Dépôt** de ce montant à cette date avec le [formulaire de transaction](../form.md).

![Crédit Agricole — ligne « Solde initial » et « Date de début » en haut de l'export](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/04C_CA_SaldoInizialeExportMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

## 🕰️ Historique des titres de plus de deux ans

Votre compte-titres a plus de deux ans ? Un second export, la **Lista movimenti deposito titoli**, récupère ses transactions antérieures, coupons et échéances — uniquement des titres, pas de trésorerie bancaire.

??? note "📦 Ajouter l'historique des titres — quand votre compte-titres a plus de deux ans"

    Exportez-le **après** les mouvements du compte, et faites-le se terminer le jour **avant** leur **Data dal** : les deux fichiers ne se chevauchent alors jamais, et aucune opération n'est comptée deux fois.

    #### 📂 Étape 1 — Ouvrir les mouvements de titres

    Ouvrez **Portafoglio** dans le menu supérieur et choisissez **Lista Movimenti**.

    ![Crédit Agricole — accueil, sélection de la section Compte-titres](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/01_CA_HOME_selezionePagina.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🗓️ Étape 2 — Choisir la période

    Définissez **Data Operazione (Dal)** aussi loin que la banque le permet, et **Data Operazione (Al)** au jour précédant la **Data dal** des mouvements du compte.

    ![Crédit Agricole — liste des mouvements de titres avec sélecteur de période](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/02_CA_ListaMobimentiPeriodo.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💾 Étape 3 — Télécharger le fichier

    Cliquez sur **CERCA**, puis sur **SCARICA EXCEL** ou **SCARICA CSV**, et importez le fichier tel quel.

    ![Crédit Agricole — zone d'export des mouvements de titres](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/03_CA_ExportZone.jpeg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🔄 Ce que ce fichier importe

    | Dans le fichier (**Causale**) | Importé comme |
    |:--------------------------|:------------|
    | `CEDOLA` | **Intérêt** (coupon d'obligation) |
    | `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | **Achat** |
    | `FONDI: RIMBORSO` | **Vente** (rachat de fonds) |
    | `TITOLI SCADUTI` | **Vente** au pair (100), plus **Intérêt** pour tout montant payé au-dessus du pair |
    | `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | **Ajustement** : titres transférés depuis un autre dossier, comme un héritage, à leur valeur comptable et sans trésorerie |

    Toute autre causale est ignorée avec un avertissement. Chaque achat reçoit un **Dépôt** correspondant, et chaque vente, coupon ou prime un **Retrait** correspondant : ce fichier n'ajoute pas de trésorerie propre, et la trésorerie réelle provient des mouvements du compte.

## 🔄 Ce qui est importé

| Dans les mouvements du compte | Importé comme |
|:-------------------------|:------------|
| Salaire ou pension, paiements par carte, factures, retraits en espèces, virements | **Dépôt** ou **Retrait**, selon le signe du montant |
| Coupons et dividendes | **Intérêt** ou **Dividende**, liés au titre lorsque la ligne indique son ISIN ; une retenue indiquée (`RITENUTA`) devient un **Impôt** distinct |
| Intérêts du compte et les frais mensuels (`INTERESSI/COMPETENZE`) | **Intérêt** lorsqu'il est crédité, **Frais** lorsqu'ils sont facturés |
| Commissions et frais | **Frais**, ou **Impôt** pour l'impôt sur les plus-values, les droits de timbre et les retenues |
| Achats et ventes de titres et de fonds | **Achat** ou **Vente** lorsque les coupons de la même obligation donnent la quantité ; sinon, une ligne de trésorerie à compléter |
| Obligations arrivées à échéance ou tirées | **Vente** au pair (100), plus **Intérêt** pour toute prime ; sans le nominal de l'obligation dans le fichier, une **Vente** du montant total, avec un avertissement |
| Un rachat de fonds payé par virement bancaire | Un **Dépôt** à compléter : la banque indique le montant, pas les parts vendues |
| Toute autre opération | **Dépôt** ou **Retrait** selon le signe, listé dans un avis pour que vous puissiez le vérifier |

## ⚠️ Bon à savoir

- **Certaines lignes demandent votre aide** dans l'étape **Corrections** de l'assistant d'importation ([comment ça marche](how-to.md#only-when-needed)) :
    - les transactions sans quantité, et les rachats de fonds : choisissez le type, le titre et la quantité ;
    - les transactions dont le montant peut inclure des intérêts courus et des commissions : ajoutez-les sous **Séparer le prix des frais ?**, d'après votre note de contrat (*nota informativa*) ;
    - les frais qui ne nomment aucun titre : affectez-les, ou conservez-les sur le compte.
- **Les titres sont mis en correspondance par nom.** L'export des titres ne fournit pas d'ISIN : associez chaque titre dans le panneau **Résoudre les actifs** de [Vérification](how-to.md#review).
- **Montants tels qu'écrits**, dans la devise de chaque ligne, sans conversion. Les dates sont les dates d'opération.
- **Messages en italien.** La plupart des avis de l'importateur concernant ces fichiers sont en italien, comme le rapport.

## 🔗 Référence développeur

→ [Importateur Crédit Agricole — Détails d'implémentation](../../../developer/backend/brim/credit_agricole.md)
