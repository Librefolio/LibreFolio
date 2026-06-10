# 📐 Ratio de Sharpe

Le ratio de Sharpe est la mesure de **rendement ajusté au risque** la plus largement utilisée. Il mesure le montant du rendement excédentaire que vous recevez par unité de volatilité totale.

---

## 🔢 Formule

$$
S = \frac{R_p - R_f}{\sigma_p}
$$

où :

- $R_p$ = rendement du portefeuille (annualisé)
- $R_f$ = taux sans risque (ex: taux des bons du Trésor)
- $\sigma_p$ = écart-type du portefeuille (annualisé)

---

## 💡 Interprétation

| Ratio de Sharpe | Qualité |
|---|---|
| $< 0$ | Le portefeuille a sous-performé par rapport au taux sans risque |
| $0 - 0.5$ | Rendement ajusté au risque sous-optimal |
| $0.5 - 1.0$ | Acceptable |
| $1.0 - 2.0$ | Bon |
| $> 2.0$ | Excellent (rare sur de longues périodes) |

!!! example "Exemple numérique"

    Rendement du portefeuille : 12 %, Taux sans risque : 3 %, Volatilité : 15 %

    $$S = \frac{0.12 - 0.03}{0.15} = 0.60$$

    Pour chaque 1 % de volatilité, le portefeuille a généré 0,60 % de rendement excédentaire.

---

## ⚙️ Annualisation

Lorsqu'il est calculé à partir de rendements quotidiens :

$$
S_{annual} = S_{daily} \times \sqrt{252}
$$

où 252 est le nombre typique de jours de bourse par an. Cela suppose que les rendements sont IID (indépendants et identiquement distribués) — une approximation qui ne s'applique plus pour les rendements autocorrélés.

---

## ⚠️ Limitations

### 📊 Pénalité symétrique

Le ratio de Sharpe pénalise la **volatilité à la hausse** autant que la volatilité à la baisse. Un actif qui connaît fréquemment des pics à la hausse (très souhaitable !) aura un ratio de Sharpe inférieur à un actif ayant le même rendement mais moins de mouvements haussiers.

→ Pour les distributions de rendements asymétriques, préférez le **[Ratio de Sortino](sortino-ratio.md)**.

### 📈 Sensibilité aux valeurs aberrantes

Quelques rendements extrêmes peuvent fausser considérablement l'écart-type, rendant le ratio de Sharpe instable sur de courtes périodes.

### 🔄 Dépendance à la période

Le ratio de Sharpe peut varier considérablement selon la fenêtre d'observation. Une stratégie avec un excellent ratio de Sharpe sur 5 ans peut avoir un mauvais ratio sur 1 an (ou inversement).

---

## 🔗 Liens connexes

- 📊 **[Ratio de Sortino](sortino-ratio.md)** — Variante basée uniquement sur la volatilité à la baisse
- 📊 **[Volatilité](volatility.md)** — Le dénominateur du ratio de Sharpe
- 📈 **[Rendements](../../fundamentals/returns.md)** — Le numérateur du ratio de Sharpe
