# 📥 <img src="https://www.credit-agricole.it/favicon.ico" alt=""> Crédit Agricole

Crédit Agricole est à la fois **banque et courtier** : sur le même compte, vous conservez vos **liquidités** (salaire ou retraite, virements, factures, impôts) et vos **titres**. Pour cette raison, l'importation principale à effectuer est la **Liste des Mouvements de Compte** : c'est le relevé de compte complet et il apporte les **liquidités réelles** dans LibreFolio — virements, factures, retraite, **impôts**, **frais**, ainsi que les **coupons et dividendes** effectivement crédités. Téléchargez le fichier, importez-le tel quel et le plugin reconnaît automatiquement le format.

Le relevé de compte couvre les **2 dernières années**. Si votre compte titres est **plus ancien** et que vous souhaitez en récupérer l'**historique**, dépliez la section ci-dessous **avant** de procéder.

??? note "📦 Compte titres de plus de 2 ans ? Récupérer l'historique (optionnel)"

    Le relevé de compte s'arrête à **2 ans**. Si le dossier titres est plus ancien, ajoutez une seconde exportation — la **Liste des Mouvements du Dépôt Titres** — qui remonte beaucoup plus loin et récupère au moins l'**historique des titres** (quantités, prix, coupons, échéances) **antérieur** à cette période. Il s'agit **uniquement de titres** : il ne **contient pas** les flux de trésorerie du compte courant (virements, factures, impôts…), qui restent dans la Liste des Mouvements de Compte. La trésorerie de cette exportation est **auto-équilibrée** pour ne pas fausser les soldes.

    **Comment les combiner sans doublons.** Exportez d'abord la **Liste des Mouvements de Compte** et notez sa date de début (**"Date du"**). Exportez ensuite la **Liste des Mouvements du Dépôt Titres** **tronquée** de manière à ce qu'elle se termine le jour **précédant** le début des mouvements de compte : les deux fichiers **ne se chevauchent pas** et la même opération n'est pas comptée deux fois.

    #### 📂 Étape 1 — Ouvrir le dossier titres

    Depuis la banque en ligne, accédez à la section **Dépôt Titres** et allez dans la liste des mouvements.

    ![Crédit Agricole — accueil, sélection de la section Dépôt Titres](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/01_CA_HOME_selezionePagina.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🗓️ Étape 2 — Sélectionner la période

    Remontez aussi loin que possible, puis tronquez au début des mouvements de compte (voir le conseil ci-dessus).

    ![Crédit Agricole — liste des mouvements titres avec sélecteur de période](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/02_CA_ListaMobimentiPeriodo.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💾 Étape 3 — Exporter

    Exportez et importez le fichier dans LibreFolio sans l'ouvrir ni le modifier.

    ![Crédit Agricole — zone d'exportation des mouvements titres](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/03_CA_ExportZone.jpeg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💰 Étape 4 — Solde initial (dépôt manuel)

    Nécessaire pour obtenir des **soldes de trésorerie totaux corrects** : aucune des deux exportations ne reporte le solde de départ sous forme de mouvement, donc sans cette étape, la trésorerie absolue démarre à zéro au début de la période exportée et reste décalée.

    **Comment l'obtenir.** Le **Solde Initial** se lit à deux endroits équivalents (c'est la même valeur) : en haut du **fichier Excel** de la *Liste des Mouvements de Compte* et également **au début de l'exportation sur la page web** — la même page depuis laquelle vous exportez les mouvements de compte. C'est la valeur (ex. `2984,99 EUR`) à la date **"Date du"** (ex. `01/07/2024`).

    Le plugin ne le crée **pas** automatiquement : lors de l'importation, **créez manuellement une transaction de dépôt de trésorerie** égale à ce **Solde Initial**, avec une **date** égale à la **"Date du"**. Cela permet de conserver une trésorerie absolue exacte même si l'exportation ne couvre qu'une période partielle.

    ![Crédit Agricole — ligne "Solde Initial" et "Date du" en haut de l'exportation](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/04C_CA_SaldoInizialeExportMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    **Comment les opérations sur titres sont associées.** Le rapport n'indique que le **nom** du titre (`Nome`), pas l'ISIN : les actifs sont associés par leur nom — confirmez l'actif à l'**Étape 4** de l'assistant s'il n'est pas reconnu.

    | Type de transaction | Importé comme |
    |:--------------------|:--------------|
    | `CEDOLA` | **Coupon** d'obligation → intérêt (la valeur nominale dans la colonne quantité est ignorée) |
    | `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | **Achat** avec **dépôt** automatique d'un montant équivalent |
    | `FONDI: RIMBORSO` | **Vente** (rachat de fonds) avec **retrait** automatique d'un montant équivalent |
    | `TITOLI SCADUTI` | **Échéance** d'obligation : **vente au pair (100)** + une ligne **intérêt** pour tout montant supérieur au pair |
    | `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | **Transfert entrant** depuis une succession → **ajustement** sans trésorerie avec prix de revient par unité |

    Les montants sont importés **textuellement** dans la devise du rapport : aucune conversion, la colonne *Taux de change* est ignorée. La date utilisée est la *Date d'opération*.

    **Modèle de trésorerie (titres).** S'agissant d'une exportation dédiée aux titres, LibreFolio conserve un solde de trésorerie **neutre** via des contreparties automatiques (tag `auto_cash`) : chaque **achat** reçoit un **dépôt** d'un montant égal, chaque **vente**/**coupon**/**intérêt d'échéance** reçoit un **retrait** d'un montant égal. Ainsi, l'exportation de titres **n'accumule pas de trésorerie fantôme** — la vraie trésorerie provient de la Liste des Mouvements de Compte.

## 💳 Comment importer — Liste des Mouvements de Compte

C'est l'importation **principale** : le relevé avec la **trésorerie réelle** (virements, factures, retraite, impôts, frais, coupons et dividendes crédités). Couvre les **2 dernières années**.

### 📄 Étape 1 — Ouvrir les mouvements de compte

Depuis la banque en ligne, accédez à la section **compte courant** et allez dans la liste des mouvements.

![Crédit Agricole — accueil, section mouvements du compte courant](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/01C_CA_HomeContiMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Étape 2 — Sélectionner la période

Cliquez sur **Recherche avancée** pour ouvrir les filtres de date, puis définissez la période la plus large autorisée (l'exportation de compte est limitée à **2 ans**).

![Crédit Agricole — liste des mouvements du compte](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/02C_CA_ListaMovimentiConti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 💾 Étape 3 — Exporter

Téléchargez la liste et importez-la dans LibreFolio sans la modifier.

![Crédit Agricole — exportation des mouvements de compte avec avertissement sur la période](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/03C_CA_ExportMovimentiContiConWarning.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

!!! warning "Si l'avertissement sur la période maximale apparaît"

    Crédit Agricole limite le nombre de lignes/mois que vous pouvez exporter en une seule fois. Si l'avertissement apparaît, **divisez l'exportation en plusieurs sous-blocs** jusqu'à couvrir tous les mois manquants :

    1. Exportez le bloc tel qu'il est affiché.
    2. Consultez la **dernière (plus ancienne)** transaction du bloc venant d'être téléchargé et notez sa date.
    3. Revenez au sélecteur de période et définissez comme **date de fin ("au")** la date de cette dernière transaction.
    4. Exportez le nouveau bloc et **répétez** à partir de l'étape 2 jusqu'à atteindre la période souhaitée.
    5. Importez **tous** les fichiers exportés dans LibreFolio.

### 📝 Comment les transactions de compte sont associées

Les **libellés d'opérations** du compte sont catégorisés comme suit :

| Type d'opération | Importé comme |
|:-----------------|:--------------|
| Coupons / dividendes crédités | **Intérêt** (coupon) ou **Dividende** si la description identifie un titre avec **ISIN** ; sinon **intérêt** |
| Intérêts / avoirs | **Intérêt** (montant positif) |
| Cotisation compte, commissions, frais de gestion, frais de détachement de coupon | **Frais** (sortie de trésorerie) |
| Plus-values, droits de timbre, précompte mobilier, D.Lgs 461 | **Taxe** (sortie de trésorerie) |
| Achat/vente de titres/fonds, titres échus ou tirés | **Dépôt/Retrait** selon le signe + **avertissement** de risque de double comptabilisation |
| Retraite/salaires, POS, factures, retraits, virements, autres | **Dépôt** (montant > 0) / **Retrait** (montant < 0) selon le signe |

## 🔗 Référence pour développeurs

→ [Fournisseurs BRIM — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)
