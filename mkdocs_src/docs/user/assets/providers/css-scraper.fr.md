# <img src="../../../../../static/cssscraper.png" alt=""> CSS Scraper

Le fournisseur CSS Scraper vous permet d'extraire des données de prix de n'importe quelle page web en utilisant des sélecteurs CSS. Ceci est particulièrement utile pour les instruments non couverts par d'autres fournisseurs, tels que les obligations d'État italiennes (BTP) sur Borsa Italiana.

## 📊 Capacités

- ✅ **Prix actuel** : Extrait le prix d'une page web
- ❌ **Historique** : Non supporté (⚠️ avertissement, pas une erreur)
- ❌ **Recherche** : Non supporté

## 🔧 Configuration

- **Identifiant** : L'URL complète de la page à scraper
- **Type d'identifiant** : `OTHER`
- **Paramètres** :

| Paramètre | Requis | Description | Exemple |
|-----------|:---:|---|---|
| `current_css_selector` | ✅ | Sélecteur CSS pour l'élément du prix | `.summary-value strong` |
| `currency` | ✅ | Code devise ISO 4217 | `EUR` |
| `decimal_format` | ❌ | `us` (1,234.56) ou `eu` (1.234,56) | `eu` |
| `timeout` | ❌ | Timeout HTTP en secondes (par défaut : 30) | `30` |
| `user_agent` | ❌ | En-tête User-Agent personnalisé | `LibreFolio/1.0` |

## 🔎 Comment trouver le sélecteur CSS

### Étape par étape (Chrome)

1. Ouvrez la page contenant le prix dans Chrome
2. Faites un **clic droit** sur la valeur du prix
3. Sélectionnez **Inspecter** (ou appuyez sur `F12`)
4. Dans le panneau Éléments des DevTools, l'élément du prix sera mis en évidence
5. Faites un **clic droit** sur l'élément mis en évidence dans les DevTools
6. Sélectionnez **Copier** → **Copier le sélecteur**
7. Collez-le dans le champ `current_css_selector`

### Étape par étape (Firefox)

1. Ouvrez la page contenant le prix dans Firefox
2. Faites un **clic droit** sur la valeur du prix
3. Sélectionnez **Inspecter l'élément** (ou appuyez sur `F12`)
4. Dans l'Inspecteur, faites un **clic droit** sur l'élément mis en évidence
5. Sélectionnez **Copier** → **Sélecteur CSS**
6. Collez-le dans le champ `current_css_selector`

### 💡 Exemple : Borsa Italiana BTP

Pour un BTP sur Borsa Italiana (ex: `IT0005634800`) :

**URL** (version anglaise) :
```
https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en
```

**Sélecteur CSS** :
```
.summary-value strong
```

**Configuration** :
- Identifiant : `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
- `current_css_selector` : `.summary-value strong`
- `currency` : `EUR`
- `decimal_format` : `us` (la page anglaise utilise le format US : 100.39)

Pour la version italienne, utilisez `decimal_format` : `eu` (la page italienne utilise le format EU : 100,39).

## 🔢 Format décimal

| Format | Exemple | Quand l'utiliser |
|--------|---------|-------------|
| `us` | 1,234.56 | Pages en anglais/US (point comme séparateur décimal) |
| `eu` | 1.234,56 | Pages en italien, allemand ou français (virgule comme séparateur décimal) |

## 🛠️ Dépannage

### "Selector not found"
Le sélecteur CSS ne correspond à aucun élément sur la page. La structure de la page a peut-être changé — inspectez à nouveau et copiez un nouveau sélecteur.

### "Connection timeout"
La page a mis trop de temps à répondre. Essayez d'augmenter le paramètre `timeout` ou vérifiez si l'URL est correcte.

### "Parse error"
Le texte du prix n'a pas pu être analysé comme un nombre. Vérifiez le paramètre `decimal_format` — si la page affiche `100,39`, utilisez `eu` ; si elle affiche `100.39`, utilisez `us`.

### Le prix affiche 0 ou une valeur erronée
Le sélecteur correspond peut-être à un autre élément. Essayez un sélecteur plus spécifique. Utilisez les DevTools pour vérifier exactement quel élément votre sélecteur cible.
