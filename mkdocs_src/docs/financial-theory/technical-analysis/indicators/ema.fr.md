# 📉 EMA — Moyenne Mobile Exponentielle

L'EMA suit la **tendance** en lissant le bruit des prix quotidiens, en accordant plus de poids aux observations récentes qu'aux plus anciennes.

---

## 💡 Signification Financière

Les traders superposent des EMA de différentes périodes sur un graphique de prix : lorsqu'une EMA à courte période croise *à la hausse* une EMA à longue période, cela signale un momentum haussier (un « golden cross ») ; le croisement inverse signale un ralentissement (« death cross »).

---

## 🔢 Formule Mathématique

L'EMA est définie par la récurrence de premier ordre :

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

où $P_t$ est le prix de clôture au temps $t$ et $\alpha$ est le **coefficient de lissage**.

**Correspondance $N$ → $\alpha$.**
Les traders spécifient une « période » $N$ (en jours). Le coefficient est calculé en faisant correspondre l' *âge moyen* des données entre une EMA et une Moyenne Mobile Simple (SMA) de la même fenêtre :

$$
\text{Age}_{SMA} = \frac{N-1}{2}, \qquad
\text{Age}_{EMA} = \frac{1-\alpha}{\alpha}
$$

En les égalisant :

$$
\alpha = \frac{2}{N+1}
$$

Par exemple, $N = 14 \implies \alpha = 2/15 \approx 0,133$.

---

## ⚙️ Paramètres

| Paramètre | Clé | Valeur par défaut | Description |
|---|---|---|---|
| Période ($N$) | `period` | 14 | Fenêtre d'observation en jours. Plus élevée → lissage accru, réactivité moindre. |
| Décalage | `offset` | 0 | Décalage vertical en % de la valeur de base. |

---

## 🎛️ Équivalent en Traitement du Signal — Filtre Passe-Bas RII de Premier Ordre

La récurrence $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ est précisément un **filtre passe-bas RII (Réponse Impulsionnelle Infinie) de premier ordre**. Sa fonction de transfert dans le domaine $z$ est :

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

La fréquence de coupure à $-3\,\text{dB}$ (normalisée) est :

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

Lorsque $\alpha$ est petit ($N$ grand), la bande passante se rétrécit considérablement, atténuant tout sauf la composante DC (la tendance à long terme).

!!! tip "Position du pôle"

    L'unique pôle se situe à $z = 1-\alpha$. Pour $N = 200$, $\alpha \approx 0,01$, donc
    le pôle est à $z = 0,99$ — extrêmement proche du cercle unité, ce qui explique le
    lissage important et le retard de groupe élevé.

:material-link: [EMA sur Wikipédia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }
