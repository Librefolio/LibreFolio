# 📉 Max Drawdown

Le Max Drawdown (MDD) mesure la **baisse la plus importante** de la valeur du portefeuille entre un sommet et un creux, avant qu'un nouveau sommet ne soit établi. Il répond à la question : *"Quelle a été la pire perte qu'un investisseur aurait pu subir ?"*

---

## 🔢 Formule

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

où $V_t$ est la valeur du portefeuille au temps $t$.

Le drawdown à tout moment $t$ est :

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

Le max drawdown est la valeur minimale (la plus négative) de $DD_t$ sur toute la période d'observation.

---

## 💡 Interprétation

| Max Drawdown | Contexte typique |
|---|---|
| $-5\%$ à $-10\%$ | Correction normale, portefeuille bien diversifié |
| $-10\%$ à $-20\%$ | Correction significative |
| $-20\%$ à $-30\%$ | Zone de marché baissier |
| $-30\%$ à $-50\%$ | Marché baissier sévère (2008, COVID-2020) |
| $> -50\%$ | Catastrophique (positions concentrées, crypto) |

!!! example "Exemple numérique"

    Séquence de valeur du portefeuille : 100 → 120 → 90 → 110 → 130

    - Sommet (Peak) : 120
    - Creux (Trough) : 90
    - MDD : $(90 - 120) / 120 = -25\%$
    - Récupération : retour à 120, puis nouveau sommet à 130

---

## ⏱️ Temps de récupération

Une mesure tout aussi importante est le **temps de récupération** — la durée nécessaire pour se remettre du drawdown et atteindre un nouveau sommet :

$$
T_{recovery} = t_{new\_peak} - t_{trough}
$$

| Classe d'actifs | Temps de récupération typique (après un drawdown majeur) |
|-------------|---------------------------------------------|
| Actions US (S&P 500) | 1-5 ans |
| Obligations | Quelques mois à 1-2 ans |
| Crypto | Très variable (mois à années) |

!!! warning "Asymétrie des pertes"

    Une perte de 50 % nécessite un **gain de 100 %** pour être récupérée :

    $$
    \text{Gain requis} = \frac{1}{1 + MDD} - 1
    $$

    <div style="display: flex; justify-content: center;">

    | Perte | Gain requis |
    |:----:|:-------------:|
    | -10% | +11.1% |
    | -25% | +33.3% |
    | -50% | +100% |
    | -75% | +300% |

    </div>

---

## 📊 Graphique de Drawdown

Un graphique de drawdown trace $DD_t$ au fil du temps. Il est toujours nul ou négatif, touchant zéro à chaque nouveau sommet. La vallée la plus profonde représente le max drawdown. Cette visualisation permet de :

- Identifier la **chronologie** des périodes les plus critiques
- Voir la fréquence d'apparition des drawdowns
- Comparer les modèles de récupération entre différentes stratégies

---

## 🔗 Liens connexes

- 📊 **[Volatilité](volatility.md)** — L'écart-type ne capture pas la sévérité du drawdown
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Rendement ajusté au risque (utilise la volatilité, pas le drawdown)
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Le principal outil pour réduire le max drawdown
