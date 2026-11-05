# 🇮🇹 Borsa Italiana

**Borsa Italiana** est la bourse de Milan, gérée par Euronext. Ce fournisseur lit les cours, l’historique des cours et les détails des instruments depuis son site public — aucun compte ni clé API n’est nécessaire.

## 🔍 Ce qu’il propose

- **Cours actuel** : le dernier cours du marché. Pour un fonds commun de placement, sa NAV — uniquement lorsqu’elle est datée d’aujourd’hui.
- **Historique** : ouverture, plus haut, plus bas, clôture et volume quotidiens. Les fonds communs de placement n’ont pas de série passée : chaque NAV est enregistrée à sa propre date, l’historique s’enrichit donc à partir du jour où vous ajoutez le fonds.
- **Recherche** : par nom ou ISIN. Chaque instrument apparaît deux fois, 🇮🇹 et 🇬🇧 — ou uniquement dans votre [langue préférée](#preferred-language) : le drapeau définit la langue de son nom et de sa description. Les indices sont exclus, car vous ne pouvez pas les acheter. Aucun résultat ?
  LibreFolio recherche aussi une page Borsa Italiana correspondante sur le web, sauf si votre administrateur a désactivé cette option.
- **Détails** : nom, type, devise, un secteur et une description (marché, émetteur, échéance, coupon) ; le ticker pour les actions ; pour les fonds, l’ISIN, les caractéristiques du fonds et ses frais.

Il couvre ce que Borsa Italiana répertorie — actions italiennes, ETF et ETC (ETFplus), obligations (MOT, ExtraMOT, EuroTLX) et fonds à capital fixe (MIV) — ainsi que les fonds communs de placement et les SICAV.

## 💱 Devise et type

- La **devise** est celle dans laquelle Borsa Italiana exprime ses cours : EUR pour les ETF et ETC sur ETFplus, même lorsque le fonds lui-même est libellé en USD ; USD pour une obligation négociée en dollars sur EuroTLX. Si LibreFolio ne parvient pas à la lire, il laisse votre devise telle quelle — vérifiez-la avant d’enregistrer.
- **Type** : les ETF, ETC et ETN sont tous importés comme de simples **ETF**. Si vous connaissez la composition du fonds, affinez-le (par exemple **ETF actions** ou **ETF matières premières**) : une [vérification ultérieure avec les données du fournisseur](../create-edit.md#provider-data-comparison) conserve votre choix.
- Les **obligations** se voient attribuer le secteur **Obligations d’État** ou **Obligations d’entreprise** (émetteurs supranationaux : **Financières**) et, lorsque l’émetteur est reconnu, son pays — *États-Unis d’Amérique* devient **USA**.

## ✏️ Configuration

La **Recherche en ligne** remplit tous les champs. Pour configurer le fournisseur à la main, ouvrez l’actif avec **Modifier** (✏️) — ou **+ Ajouter un actif** pour un nouvel actif — et développez **Attribution du fournisseur** :

1. Choisissez **Borsa Italiana** comme **Fournisseur**.
2. Saisissez l’**ISIN** de l’instrument, par exemple `IT0003128367` (ENEL). Chaque page d’instrument sur [borsaitaliana.it](https://www.borsaitaliana.it) l’affiche.
3. Choisissez la **Langue** : 🇬🇧 English ou 🇮🇹 Italiano.
4. Cliquez sur **Tester la configuration**, puis enregistrez.

La **Recherche en ligne** remplit aussi les trois autres paramètres ; ne les définissez à la main que dans les cas suivants.

??? note "🧾 Code interne du fonds — pour un fonds commun de placement ou une SICAV"

    Les fonds communs de placement sont valorisés au moyen du code de fonds propre à Borsa Italiana, et non au moyen de l’ISIN. Trouvez le fonds sur [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) et copiez le code depuis l’adresse de sa page : dans `…/borsa/fondi/dettaglio/2FADB602822.html`, le code est `2FADB602822`. Laissez le champ vide pour tout autre cas.

??? note "🧭 MIC du marché et plateforme — lorsque la page de l’instrument ne s’ouvre pas"

    Certains marchés doivent être nommés explicitement. Ouvrez l’instrument sur borsaitaliana.it : le code situé après l’ISIN dans l’adresse de la page est le **MIC du marché** — dans `…/scheda/US912810TU25-ETLX.html`, il s’agit de `ETLX`. La **Plateforme** n’est nécessaire que sur EuroTLX, où elle vaut `TLX`.

    | Marché | MIC du marché | Plateforme |
    |--------|:---:|:---:|
    | MTA (actions italiennes) | `MTAA` | — |
    | MOT (obligations) | `MOTX` | — |
    | ExtraMOT (obligations) | `XMOT` | — |
    | ETFplus (ETF, ETC) | `ETFP` | — |
    | MIV (fonds à capital fixe) | `MIVX` | — |
    | EuroTLX (obligations) | `ETLX` | `TLX` |

    Par exemple, l’obligation du Trésor américain `US912810TU25` sur EuroTLX fonctionne une fois que le **MIC du marché** est `ETLX` et que la **Plateforme** est `TLX` ; ses cours sont en USD.

### 🌐 Votre langue préférée {: #preferred-language }

Vous choisissez toujours la même langue dans la recherche ? Choisissez-la une fois comme **Langue préférée**, sous **Borsa Italiana** dans **Paramètres › Plugins**, ou avec **Configurer** à côté du fournisseur dans la boîte de dialogue de l’actif. Vos recherches n’affichent alors chaque instrument qu’une seule fois, en 🇮🇹 italien ou en 🇬🇧 anglais. L’option **Les deux langues**, qui est celle par défaut, affiche les deux, l’italien en premier. Le site web est interrogé de la même manière, quel que soit votre choix.

Il s’agit d’un paramètre personnel : il ne modifie que vos propres recherches, jamais un cours ni un actif que vous avez déjà, et la **Langue** d’un actif que vous configurez à la main reste votre choix. Voir [Paramètres des plugins](../../settings/plugins.md#search-preferences).

## 🧾 Fonds communs de placement et NAV

La NAV d’un fonds est publiée une fois par jour, avec un décalage. LibreFolio enregistre chaque NAV à la date à laquelle elle se rapporte, jamais comme cours du jour : jusqu’à l’arrivée de la suivante, le fonds est valorisé au dernier cours connu — cette NAV, ou votre propre transaction si celle-ci est plus récente.

Le code du fonds est conservé sous **Autres identifiants** ; le véritable ISIN reste l’identifiant principal lorsque la page du fonds l’affiche.

## ⚠️ Limites

- LibreFolio espace ses requêtes vers le site web ; la synchronisation de nombreux actifs Borsa Italiana peut donc prendre quelques minutes.
- Un marché que LibreFolio ne sait pas encore lire produit une erreur vous demandant de signaler l’ISIN sur [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Voir aussi

- 📋 **[Vue d’ensemble des actifs](../index.md)** — Gérez votre bibliothèque d’actifs
- 🏦 **[Fournisseurs d’actif](./index.md)** — Autres sources de données
- 📡 **[justETF](./justetf.md)** — Source alternative pour les données ETF
- 🧩 **[Paramètres des plugins](../../settings/plugins.md)** — Votre langue préférée dans la recherche
- 🛠️ **Pour les développeurs : [Fournisseur Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)** — Requêtes, analyse des pages et correspondance des champs
