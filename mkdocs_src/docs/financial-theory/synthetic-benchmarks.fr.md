# 🎯 Courbes de référence théoriques

LibreFolio peut superposer des **courbes de référence théoriques** sur n'importe quel graphique de devises. Contrairement aux indicateurs techniques (qui sont calculés *à partir* des données de marché), les courbes de référence théoriques sont générées mathématiquement et servent de **lignes de référence visuelles** — « et si le prix avait suivi cette trajectoire idéale ? »

Elles sont inestimables pour :

- Comparer les rendements réels à un taux de croissance cible.
- Visualiser à quoi ressemblerait un plan d'investissement rigoureux.
- Ajouter des références oscillantes ou cycliques pour l'analyse de la saisonnalité.

---

## 📈 Croissance Linéaire { #linear-growth }

### 💡 Signification Financière

Une courbe de référence de croissance linéaire représente les **intérêts simples** — la valeur augmente d'un montant absolu fixe à chaque période. Cela modélise le scénario où vous **ne réinvestissez pas** vos revenus (dividendes, intérêts, coupons) : les versements en espèces sont reçus mais mis de côté, seul le capital initial génère des rendements.

Si au contraire vous **réinvestissez** ces revenus — manuellement ou automatiquement via des instruments capitalisants (ex. ETF capitalisants, qui réinvestissent les dividendes en interne et bénéficient du [report d'imposition](taxation.md#tax-deferral-advantage)) — vous devriez observer une **[croissance composée](#compound-growth)**, où les rendements génèrent à leur tour des rendements.

En pratique, l'écart entre croissance linéaire et composée s'élargit considérablement sur les horizons longs. C'est pourquoi la référence Linéaire apparaît comme une droite tandis que la référence Composée courbe vers le haut de façon exponentielle.

!!! abstract "Plus-values et moins-values"

    Lorsqu'un actif est vendu au-dessus de son prix d'achat, la différence est une **plus-value** ; en dessous, une **moins-value**. Chaque juridiction a ses propres règles concernant les taux d'imposition, les seuils de durée de détention, la durée du report des pertes et les méthodes d'appariement (FIFO, LIFO, identification spécifique). Pour un aperçu théorique, voir [Fiscalité & Efficience Fiscale](taxation.md).

### 🔢 Formule Mathématique

$$
y(t) = y_0 \cdot (1 + r \cdot t)
$$

où :

- $y_0$ est la valeur de départ (premier point de données du graphique),
- $r$ est le taux de croissance annuel (exprimé en décimal, par ex. 0,07 pour 7%),
- $t$ est le temps en années depuis le début.

Ceci équivaut à la formule des **intérêts simples** $A = P(1 + rt)$, où $t$ est exprimé en années selon la [Convention de décompte des jours] applicable.

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Taux Annuel | `annualRate` | 5 | Taux de croissance en pourcentage par an. |
| Décalage | `offset` | 0 | Décalage vertical en % de la valeur de base. |

### 🔍 Interprétation

La ligne est parfaitement droite sur une échelle linéaire. Tout point où le prix réel est *au-dessus* de la ligne signifie que l'actif a surperformé la cible ; tout point *en dessous* signifie une sous-performance. Comme la croissance est de type additif, la ligne se courbe vers le bas sur une échelle logarithmique — ce qui permet de la distinguer facilement d'une croissance composée.

:material-link: [Intérêts Simples sur Wikipédia](https://fr.wikipedia.org/wiki/Int%C3%A8r%C3%AAt_simple){ target="_blank" }

---

## 📊 Croissance Composée { #compound-growth }

### 💡 Signification Financière

Une courbe de référence de croissance composée représente les **intérêts composés** — la valeur croît de manière exponentielle, ce qui signifie que les rendements sont réinvestis. C'est le modèle de croissance naturel pour la plupart des actifs financiers et l'hypothèse standard dans l'analyse des flux de trésorerie actualisés (DCF).

### 🔢 Formule Mathématique

$$
y(t) = y_0 \cdot (1 + r)^t
$$

où :

- $y_0$ est la valeur de départ,
- $r$ est le taux de croissance annuel (décimal),
- $t$ est le temps en années depuis le début.

Ceci équivaut à la formule des **intérêts composés** $A = P(1 + r)^t$ avec capitalisation annuelle. La formule généralisée avec $n$ périodes de capitalisation par an est :

$$
A = P \cdot \left(1 + \frac{r}{n}\right)^{n \cdot t}
$$

Le backend de LibreFolio prend en charge les fréquences de capitalisation suivantes : **Annuelle** ($n=1$), **Semestrielle** ($n=2$), **Trimestrielle** ($n=4$), **Mensuelle** ($n=12$), **Quotidienne** ($n=365$), et **Continue** ($n \to \infty$).

Lorsque $n \to \infty$ (capitalisation continue) :

$$
A = P \cdot e^{r \cdot t}
$$

### 🔄 Calcul Itératif (Pas Journalier)

Dans LibreFolio, la courbe composée est calculée de manière **itérative** plutôt que d'appeler `pow()` pour chaque point de données. Ceci est à la fois plus efficace et instructif :

$$
\text{facteurQuotidien} = (1 + r)^{1/365}
$$

Puis, pour chaque jour successif :

$$
y_{i+1} = y_i \cdot \text{facteurQuotidien}
$$

Cela est mathématiquement équivalent à la forme close $y_0(1+r)^t$ mais remplace $N$ opérations puissance coûteuses par $N$ multiplications simples — le même principe que celui utilisé par les banques pour l'accumulation journalière des intérêts composés.

!!! tip "Règle du 72"

    Un raccourci mental rapide : un investissement qui croît à $r$% par an doublera approximativement en $72 / r$ années. À 7% → ~10,3 ans.

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Taux Annuel | `annualRate` | 7 | Taux de croissance **composé** en pourcentage par an. |
| Décalage | `offset` | 0 | Décalage vertical en % de la valeur de base. |

### 🔍 Interprétation

La courbe est droite sur une échelle **logarithmique** — c'est le signe révélateur d'une croissance exponentielle. Superposer une référence composée sur un graphique en échelle log est la méthode la plus claire pour juger si un actif croît plus vite ou plus lentement qu'un taux cible.

:material-link: [Intérêts Composés sur Wikipédia](https://fr.wikipedia.org/wiki/Int%C3%A9r%C3%AAt_compos%C3%A9){ target="_blank" }

---

## 🌊 Courbe sinusoïdale { #sine-wave }

### 💡 Signification Financière

Une courbe de référence sinusoïdale représente une **oscillation périodique**. Elle est utile pour :

- Modéliser la **saisonnalité** (par ex. les matières premières agricoles, les devises liées au tourisme).
- Fournir une référence visuelle pour les **schémas cycliques** que les traders suspectent dans les données.
- Tester la chaîne de rendu avec une forme d'onde analytique connue.

### 🔢 Formule Mathématique

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{décalage}
$$

où :

- $A$ est l'amplitude (amplitude pic-à-pic en pourcentage de la valeur de base),
- $T$ est la période en jours,
- $y_0$ est la valeur de base (premier point de données),
- $\text{décalage}$ est un décalage vertical.

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Amplitude | `amplitude` | 10 | Amplitude pic-à-pic en pourcentage de la valeur de base. |
| Période | `period` | 365 | Longueur du cycle complet en jours. |
| Décalage | `offset` | 0 | Décalage vertical en pourcentage de la valeur de base. |

### 🔍 Interprétation

Si le prix réel suit approximativement la référence sinusoïdale, le marché présente une composante cyclique détectable à cette fréquence. Les écarts par rapport à la sinusoïde suggèrent des chocs non périodiques ou une dérive de tendance. L'ajustement du paramètre de période permet de balayer différentes longueurs de cycle — ce qui équivaut effectivement à une analyse spectrale manuelle.

:material-link: [Onde sinusoïdale sur Wikipédia](https://fr.wikipedia.org/wiki/Onde_sinuso%C3%AFdale){ target="_blank" }
