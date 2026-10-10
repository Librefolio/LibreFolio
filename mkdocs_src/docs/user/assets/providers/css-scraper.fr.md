# <img src="../../../../static/cssscraper.png" alt=""> Scraper CSS

Le Scraper CSS lit le prix d'un actif depuis n'importe quelle page web publique, à l'aide d'un sélecteur CSS qui pointe
vers le nombre. Utilisez-le lorsqu'aucun autre fournisseur ne couvre l'instrument. Dans la liste **Fournisseur**, il est
appelé **CSS Web Scraper**.

## 🔍 Ce qu'il propose

- ✅ **Prix actuel** : lu depuis la page à chaque synchronisation, dans la devise de votre choix.
- ❌ **Historique** : aucun. Chaque synchronisation enregistre le prix du jour, l'historique s'enrichit donc à partir du jour où vous
  commencez.
- ❌ **Recherche** et **détails** : aucun — vous saisissez vous-même l'adresse de la page et les paramètres.

## 🧩 Configuration

### 1️⃣ Copier le sélecteur CSS du prix

Le sélecteur indique à LibreFolio quel élément de la page contient le prix.

=== "Chrome"

    1. Ouvrez la page et faites un clic droit sur le prix.
    2. Choisissez **Inspecter** (ou appuyez sur `F12`) : DevTools met en surbrillance l'élément du prix.
    3. Faites un clic droit sur l'élément mis en surbrillance, puis **Copier** → **Copier le sélecteur**.

=== "Firefox"

    1. Ouvrez la page et faites un clic droit sur le prix.
    2. Choisissez **Inspecter** (ou appuyez sur `F12`) : l'Inspecteur met en surbrillance l'élément du prix.
    3. Faites un clic droit sur l'élément mis en surbrillance, puis **Copier** → **Sélecteur CSS**.

### 2️⃣ Remplir les paramètres du fournisseur

Dans **Affectation du fournisseur**, choisissez **CSS Web Scraper** et collez l'adresse de la page dans **URL**. Les
paramètres apparaissent sous leurs noms techniques :

| Paramètre | Requis | Valeur à saisir |
|---|:---:|---|
| `current_css_selector` | ✅ | Le sélecteur que vous avez copié, par ex. `.summary-value strong` |
| `currency` | ✅ | La devise du prix, par ex. `EUR` |
| `decimal_format` | — | `us` pour `1,234.56` (par défaut) ou `eu` pour `1.234,56` |
| `timeout` | — | Secondes d'attente pour la page (par défaut `30`) |
| `user_agent` | — | Comment LibreFolio se présente au site (par défaut `LibreFolio/1.0`) |

### 3️⃣ Tester

Cliquez sur **Tester la configuration** : **Prix actuel** doit afficher le nombre que vous voyez sur la page. Le ⚠️ sur
**Historique** est attendu, car ce fournisseur n'en propose pas.

!!! example "Un BTP sur Borsa Italiana"

    - **URL** : `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
    - `current_css_selector` : `.summary-value strong`
    - `currency` : `EUR`
    - `decimal_format` : `us` — la page anglaise affiche `100.39`. La page italienne (`lang=it`)
      affiche `100,39`, donc utilisez `eu` ici.

    Pour les instruments cotés sur Borsa Italiana, le fournisseur [Borsa Italiana](borsa-italiana.md)
    fournit aussi leur historique.

## 🛠️ Dépannage

| Ce que vous voyez | Ce qu'il faut faire |
|---|---|
| **Élément de prix introuvable** | La mise en page a peut-être changé : copiez à nouveau le sélecteur. |
| **Échec de l'analyse syntaxique du prix** | Vérifiez `decimal_format`. L'élément doit contenir uniquement le nombre : les espaces, €, $, £, ¥ et % sont ignorés, les lettres telles que `EUR` ne le sont pas. |
| **Erreur HTTP** ou **Échec de la requête** | Vérifiez l'URL ; augmentez `timeout` pour un site lent. L'erreur 403 signifie que le site refuse les visites automatisées. |
| Un nombre incorrect | Le sélecteur correspond à un autre élément (LibreFolio utilise la première correspondance) : rendez-le plus spécifique. |

## ⚠️ Limites

- LibreFolio lit la page telle que le site l'envoie, sans exécuter ses scripts : un prix renseigné
  par JavaScript ne peut pas être lu, pas plus que les pages protégées par une connexion.
- Lorsque le site change sa mise en page, le sélecteur peut cesser de correspondre : testez à nouveau et copiez-en un nouveau.

## 🔗 Voir aussi

- ✏️ **[Éditeur de données](../detail/data-editor.md)** — Saisir ou corriger les prix à la main
- 🛠️ **Pour les développeurs : [Fournisseur Scraper CSS](../../../developer/backend/assets/provider_cssscraper.md)** — Requête, analyse syntaxique et codes d'erreur
