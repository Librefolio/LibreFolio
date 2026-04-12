# 📉 Drawdown maximum

Le drawdown maximum (MDD) mesure la **plus forte baisse du sommet au creux** de la valeur d'un portefeuille avant qu'un nouveau sommet ne soit atteint. Il répond à la question : *"Quelle a été la pire perte qu'un investisseur aurait pu subir ?"*

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

Le drawdown maximum est la valeur minimale (la plus négative) de $DD_t$ sur l'ensemble de la période d'observation.

---

## 💡 Interprétation

| Drawdown maximum | Contexte typique |
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

Une métrique tout aussi importante est le **temps de récupération** — le temps nécessaire pour se remettre d'un drawdown et atteindre un nouveau sommet :

$$
T_{recovery} = t_{new\_peak} - t_{trough}
$$

| Classe d'actifs | Temps de récupération typique (après drawdown majeur) |
|-------------|---------------------------------------------|
| Actions US (S&P 500) | 1-5 ans |
| Obligations | Quelques mois à 1-2 ans |
| Cryptomonnaies | Très variable (mois à années) |

!!! warning "Asymétrie des pertes"

    Une perte de 50% nécessite un **gain de 100%** pour récupérer :

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

Un graphique de drawdown représente $DD_t$ au fil du temps. Il est toujours nul ou négatif, touchant zéro à chaque nouveau sommet. La vallée la plus profonde représente le drawdown maximum. Cette visualisation permet de :

- Identifier le **moment** des périodes les plus critiques
- Voir la fréquence à laquelle les drawdowns surviennent
- Comparer les schémas de récupération entre différentes stratégies

---

## 🔗 Liens connexes

- 📊 **[Volatilité](volatility.md)** — L'écart-type ne capture pas la sévérité du drawdown
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Rendement ajusté au risque (utilise la volatilité, pas le drawdown)
- 🔀 **[Diversification](../diversification.md)** — L'outil principal pour réduire le drawdown maximum
