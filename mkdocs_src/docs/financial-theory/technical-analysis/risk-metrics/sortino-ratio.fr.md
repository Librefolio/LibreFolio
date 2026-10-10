# 📊 Ratio de Sortino

Le ratio de Sortino est une modification du ratio de Sharpe qui ne pénalise que la **volatilité à la baisse**. Il reconnaît que les investisseurs sont principalement préoccupés par les pertes, et non par les surprises à la hausse.

---

## 🔢 Formule {: #formula }

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

où :

- $R_p$ = rendement du portefeuille (annualisé)
- $R_f$ = taux sans risque (ou rendement minimum acceptable)
- $\sigma_d$ = **écart à la baisse** (annualisé)

!!! info "Comment le seuil entre dans le calcul"

    Le seuil — le rendement minimum acceptable — est fourni sous forme de taux **annuel effectif** et converti en taux **effectif par période** via la même conversion que celle utilisée par le ratio de Sharpe :

    $$
    r_{period} = (1 + r_{annual})^{1/f} - 1
    $$

    où $f$ est le même facteur d'annualisation qui met à l'échelle l'écart à la baisse, mesuré à partir des données observées — voir [Annualisation observée](observed-annualization.md). Ce seuil par période est ensuite soustrait de chaque rendement de période, à la fois dans les rendements excédentaires et à l'intérieur de l'écart à la baisse ci-dessous, de sorte qu'une définition unique de ce qui est « acceptable » régit le numérateur et le dénominateur de la même manière.

### 📐 Écart à la baisse {: #downside-deviation }

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Seuls les rendements **inférieurs** au seuil contribuent à l'écart à la baisse. Les rendements supérieurs au seuil contribuent pour zéro.

---

## ⚖️ Deux conventions d'écart à la baisse {: #two-downside-conventions }

Deux grandeurs différentes sont couramment appelées « écart à la baisse », et elles diffèrent de deux manières — l'une négligeable, l'autre décisive.

| | Point de référence | Diviseur |
|---|---|---|
| **Convention du seuil** (utilisée ici) | Un seuil **choisi** — le rendement minimum acceptable | $N$, toutes les observations |
| **Convention de la moyenne** | La **moyenne de l'échantillon de la série elle-même** | $N - 1$, les observations moins une |

**Le diviseur est la différence négligeable.** Lorsque le seuil coïncide avec la moyenne de l'échantillon, les deux résultats ne diffèrent que par le facteur $\sqrt{N/(N-1)}$ — sur une année d'observations quotidiennes, environ deux parties sur mille. C'est un choix de comptabilité, non un changement de sens.

**Le point de référence est celui qui est décisif**, et l'écart qu'il ouvre n'a pas de borne supérieure. Les valeurs suivantes découlent directement des deux définitions appliquées à des séries construites — il s'agit d'arithmétique qu'un lecteur peut reproduire, et non de résultats d'une exécution de LibreFolio :

| Série sur 250 observations | Convention de la moyenne | Convention du seuil (seuil $= 0$) |
|---|---|---|
| **Perd exactement 0,5 % chaque jour** | **0,000000** | **0,005000** |
| Alterne $+1\%$ et $-1\%$ autour de zéro | 0,007085 | 0,007071 |
| Gagne exactement 0,5 % chaque jour | 0,000000 | 0,000000 |

La première ligne est, à elle seule, tout l'argument. Un portefeuille qui perd un demi pour cent **chaque jour pendant un an** ne s'écarte jamais de sa propre moyenne, car sa moyenne *est* cette perte quotidienne — la convention de la moyenne mesure donc son risque à la baisse comme exactement nul. La convention du seuil, interrogée sur la distance dont la série est tombée sous zéro, répond qu'elle est tombée en dessous lors de chacun des 250 jours.

!!! warning "Ce ne sont pas deux estimations de la même grandeur"

    Les deux conventions répondent à des questions différentes. Mesurer par rapport à la moyenne de la série demande *à quel point suis-je irrégulier par rapport à moi-même* ; mesurer par rapport à un seuil choisi demande *de combien je tombe sous ce que j'ai demandé*. Seule la seconde peut signaler que perdre régulièrement constitue un risque — la première, par construction, ne peut pas voir une perte qui ne varie jamais.

    Aucune n'est fausse en général. La convention de la moyenne appartient naturellement à l'optimisation de portefeuille, où la grandeur minimisée est la dispersion autour de la moyenne que l'allocation atteint. La question abordée sur cette page est l'autre : le seuil est quelque chose que l'investisseur énonce à l'avance, et le ratio rapporte le résultat par rapport à celui-ci.

LibreFolio utilise la **convention du seuil avec le diviseur $N$** — la formule donnée ci-dessus. Le seuil est un paramètre explicite de l'analyse et vaut zéro sauf s'il est défini à une autre valeur, donc par défaut la question posée est *de combien le portefeuille est tombé sous le seuil de rentabilité, et son résultat était-il au-dessus*.

---

## 💡 Interprétation {: #interpretation }

| Ratio de Sortino | Signification de la valeur |
|---|---|
| $< 0$ | Le rendement est resté en deçà du seuil : le numérateur est négatif quelle que soit la valeur de l'écart à la baisse |
| $0 - 1,0$ | Moins d'une unité de rendement excédentaire par unité d'écart à la baisse |
| $1,0 - 2,0$ | Une à deux unités de rendement excédentaire par unité d'écart à la baisse |
| $> 2,0$ | Plus de deux unités de rendement excédentaire par unité d'écart à la baisse — rare sur de longues périodes, beaucoup moins sur des périodes courtes et favorables |

!!! warning "Lire l'échelle avant de lire le nombre"

    Ces plages sont exprimées en unités d'écart à la **baisse**, donc un Sortino et un Sharpe ayant la même valeur numérique ne constituent pas la même affirmation au sujet d'un portefeuille. Et comme pour tout ratio de cette famille, la valeur dépend de la fenêtre et de la classe d'actifs sur laquelle elle a été mesurée : une courte période favorable et un cycle de marché complet ne produisent pas des chiffres comparables, même pour le même portefeuille. Le tableau dit ce que le nombre *est*, pas s'il est bon.

!!! example "Exemple numérique"

    Rendement du portefeuille : 12 %, taux sans risque : 3 %, écart à la baisse : 10 %

    $$So = \frac{0{,}12 - 0{,}03}{0{,}10} = 0{,}90$$

    À comparer avec le Sharpe (si σ total = 15 %) : $S = 0{,}60$. Le Sortino est plus élevé car la volatilité à la hausse est exclue.

---

## 📊 Sharpe vs Sortino {: #sharpe-vs-sortino }

| Aspect | Sharpe | Sortino |
|--------|--------|---------|
| **Mesure du risque** | Écart-type total | Écart à la baisse uniquement |
| **Pénalise la hausse ?** | Oui ❌ | Non ✅ |
| **Idéal pour** | Distributions de rendements symétriques | Rendements asymétriques / dissymétriques |
| **Exemple** | Indice de marché large | Stratégies sur options, portefeuilles concentrés |

### 🔑 Quand préférer le Sortino {: #when-to-prefer-sortino }

- **Distributions asymétriques** : stratégies présentant des gains importants occasionnels mais des pertes maîtrisées
- **Portefeuilles d'options** : profils de gains intrinsèquement asymétriques
- **Actions de croissance** : tendent à avoir des distributions de rendements positivement asymétriques
- **Tout investisseur** qui se soucie davantage du risque à la baisse que du risque total

---

## ⚠️ Limites {: #limitations }

!!! warning "Biais de petit échantillon"

    L'écart à la baisse nécessite suffisamment de points de données sous le seuil. Avec peu de rendements négatifs (par exemple, de courtes périodes de marché haussier), l'estimation devient peu fiable et le ratio de Sortino peut être trompeusement élevé.

---

## 🔗 Liens connexes {: #related }

- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Variante sur la volatilité totale
- 📊 **[Volatilité](volatility.md)** — Comprendre l'écart-type
- 📈 **[Perte maximale](max-drawdown.md)** — Une autre mesure axée sur la baisse
