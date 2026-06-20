# 📊 Ratio de Sortino

Le ratio de Sortino est une modification du ratio de Sharpe qui ne pénalise que la **volatilité à la baisse**. Il reconnaît que les investisseurs sont principalement préoccupés par les pertes, et non par les surprises à la hausse.

---

## 🔢 Formule

$$
So = \frac{R_p - R_f}{\sigma_d}
$$

où :

- $R_p$ = rendement du portefeuille (annualisé)
- $R_f$ = taux sans risque (ou rendement minimum acceptable)
- $\sigma_d$ = **écart-type à la baisse** (annualisé)

### 📐 Écart-type à la baisse

$$
\sigma_d = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \min(R_i - R_f, 0)^2}
$$

Seuls les rendements **inférieurs** au seuil contribuent à l'écart-type à la baisse. Les rendements supérieurs au seuil n'ont aucune contribution.

---

## 💡 Interprétation

| Ratio de Sortino | Qualité |
|---|---|
| $< 0$ | Rendements inférieurs au seuil |
| $0 - 1.0$ | Rendement modéré ajusté du risque à la baisse |
| $1.0 - 2.0$ | Bon |
| $> 2.0$ | Excellente gestion du risque à la baisse |

!!! example "Exemple numérique"

    Rendement du portefeuille : 12 %, Taux sans risque : 3 %, Écart-type à la baisse : 10 %

    $$So = \frac{0.12 - 0.03}{0.10} = 0.90$$

    Comparé au ratio de Sharpe (si σ total = 15 %) : $S = 0.60$. Le Sortino est plus élevé car la volatilité à la hausse est exclue.

---

## 📊 Sharpe vs Sortino

| Aspect | Sharpe | Sortino |
|--------|--------|---------|
| **Mesure du risque** | Écart-type total | Écart-type à la baisse uniquement |
| **Pénalise la hausse ?** | Oui ❌ | Non ✅ |
| **Idéal pour** | Distributions de rendements symétriques | Rendements asymétriques / biaisés |
| **Exemple** | Indice de marché large | Stratégies d'options, portefeuilles concentrés |

### 🔑 Quand préférer le Sortino

- **Distributions biaisées** : Stratégies présentant des gains occasionnels importants mais des pertes contrôlées
- **Portefeuilles basés sur des options** : Profils de gains intrinsèquement asymétriques
- **Actions de croissance** : Tendance à avoir des distributions de rendements positivement biaisées
- **Tout investisseur** qui se soucie davantage du risque à la baisse que du risque total

---

## ⚠️ Limitations

!!! warning "Biais lié à la petite taille de l'échantillon"

    L'écart-type à la baisse nécessite un nombre suffisant de points de données inférieurs au seuil. Avec peu de rendements négatifs (par exemple, lors de courtes périodes de marché haussier), l'estimation devient peu fiable et le ratio de Sortino peut être trompeusement élevé.

---

## 🔗 Liens connexes

- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Variante de la volatilité totale
- 📊 **[Volatilité](volatility.md)** — Comprendre l'écart-type
- 📈 **[Max Drawdown](max-drawdown.md)** — Une autre métrique axée sur la baisse
