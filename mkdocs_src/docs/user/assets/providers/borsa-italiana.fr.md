# 🇮🇹 Borsa Italiana

**Borsa Italiana** est la bourse de Milan, exploitée par Euronext. Ce fournisseur lit les cours, l'historique
des cours et les détails des instruments depuis son site web public — aucun compte ni clé API n'est nécessaire.

## 🔍 Ce qu'il propose

- **Cours actuel** : le dernier cours du marché. Pour un fonds commun de placement, sa NAV — uniquement lorsqu'elle est datée
  aujourd'hui.
- **Historique** : ouverture, plus haut, plus bas, clôture et volume quotidiens. Les fonds communs de placement n'ont pas de série passée : chaque NAV
  est enregistrée à sa propre date, l'historique s'enrichit donc à partir du jour où vous ajoutez le fonds.
- **Recherche** : par nom ou par ISIN. Chaque instrument apparaît deux fois, 🇮🇹 et 🇬🇧 : le drapeau définit la
  langue de son nom et de sa description. Les indices sont exclus, car vous ne pouvez pas les acheter. Aucun résultat ?
  LibreFolio recherche aussi une page Borsa Italiana correspondante sur le Web, sauf si votre administrateur
  a désactivé cette option.
- **Détails** : nom, type, devise, un secteur et une description (marché, émetteur, échéance, coupon) ;
  le ticker pour les actions ; pour les fonds, l'ISIN, les caractéristiques du fonds et ses frais.

Il couvre ce que Borsa Italiana répertorie — actions italiennes, ETF et ETC (ETFplus), obligations (MOT,
ExtraMOT, EuroTLX) et fonds fermés (MIV) — ainsi que les fonds communs de placement et les SICAV.

## 💱 Devise et type

- **Devise** : celle dans laquelle Borsa Italiana exprime les cours : EUR pour les ETF et ETC sur ETFplus,
  même lorsque le fonds lui-même est libellé en USD ; USD pour une obligation négociée en dollars sur EuroTLX. Si
  LibreFolio ne peut pas la lire, il laisse votre devise telle quelle — vérifiez-la avant d'enregistrer.
- **Type** : les ETF, ETC et ETN arrivent tous en tant que simple **ETF**. Si vous connaissez la composition du fonds,
  affinez-le (par exemple **ETF actions** ou **ETF matières premières**) : une
  [vérification ultérieure par rapport aux données du fournisseur](../create-edit.md#provider-data-comparison) conserve votre choix.
- **Obligations** : elles reçoivent le secteur **Obligations d'État** ou **Obligations d'entreprise** (émetteurs supranationaux :
  **Financières**) et, lorsque l'émetteur est reconnu, son pays — *États-Unis d'Amérique*
  devient **USA**.

## ✏️ Configuration

**Recherche en ligne** remplit tout. Pour configurer le fournisseur manuellement, ouvrez l'actif avec
**Modifier** (✏️) — ou **+ Ajouter un actif** pour un nouvel actif — puis développez **Affectation du fournisseur** :

1. Choisissez **Borsa Italiana** comme **Fournisseur**.
2. Saisissez l'**ISIN** de l'instrument, par exemple `IT0003128367` (ENEL). Chaque page d'instrument sur
   [borsaitaliana.it](https://www.borsaitaliana.it) l'affiche.
3. Choisissez la **Langue** : 🇬🇧 English ou 🇮🇹 Italiano.
4. Cliquez sur **Tester la configuration**, puis enregistrez.

**Recherche en ligne** remplit également les trois autres paramètres ; ne les définissez manuellement que dans ces cas.

??? note "🧾 Code interne du fonds — pour un fonds commun de placement ou une SICAV"

    Les fonds communs de placement sont valorisés par le code du fonds propre à Borsa Italiana, et non par l'ISIN. Trouvez le fonds sur
    [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) et copiez le code
    depuis l'adresse de sa page : dans `…/borsa/fondi/dettaglio/2FADB602822.html`, le code est
    `2FADB602822`. Laissez le champ vide pour tout autre cas.

??? note "🧭 MIC du marché et Plateforme — lorsque la page de l'instrument ne s'ouvre pas"

    Certains marchés doivent être nommés explicitement. Ouvrez l'instrument sur borsaitaliana.it : le code après
    l'ISIN dans l'adresse de la page est le **MIC du marché** — dans `…/scheda/US912810TU25-ETLX.html`, il s'agit de
    `ETLX`. La **Plateforme** n'est nécessaire que sur EuroTLX, où elle vaut `TLX`.

    | Marché | MIC du marché | Plateforme |
    |--------|:---:|:---:|
    | MTA (actions italiennes) | `MTAA` | — |
    | MOT (obligations) | `MOTX` | — |
    | ExtraMOT (obligations) | `XMOT` | — |
    | ETFplus (ETF, ETC) | `ETFP` | — |
    | MIV (fonds fermés) | `MIVX` | — |
    | EuroTLX (obligations) | `ETLX` | `TLX` |

    Par exemple, l'obligation du Trésor américain `US912810TU25` sur EuroTLX fonctionne une fois que le **MIC du marché** est
    `ETLX` et que la **Plateforme** est `TLX` ; ses prix sont en USD.

## 🧾 Fonds communs de placement et NAV

La NAV d'un fonds est publiée une fois par jour, avec un délai. LibreFolio enregistre chaque NAV à la date à laquelle elle
se rapporte, jamais comme cours du jour : jusqu'à l'arrivée de la suivante, le fonds est valorisé au dernier
cours connu — cette NAV, ou votre propre transaction si elle est plus récente.

Le code du fonds est conservé sous **Autres identifiants** ; le véritable ISIN reste l'identifiant principal lorsque
la page du fonds l'affiche.

## ⚠️ Limites

- LibreFolio échelonne ses requêtes vers le site web, donc la synchronisation de nombreux actifs Borsa Italiana peut
  prendre quelques minutes.
- Un marché que LibreFolio ne peut pas encore lire génère une erreur vous demandant de signaler l'ISIN sur
  [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Liens connexes

- 📋 **[Vue d'ensemble des actifs](../index.md)** — Gérez votre bibliothèque d'actifs
- 🏦 **[Fournisseurs d'actifs](./index.md)** — Autres sources de données
- 📡 **[justETF](./justetf.md)** — Source alternative pour les données des ETF
- 🛠️ **Pour les développeurs : [Fournisseur Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)** — Requêtes, analyse des pages et correspondance des champs
