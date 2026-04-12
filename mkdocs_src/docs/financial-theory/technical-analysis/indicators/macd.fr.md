# 📊 MACD — Moving Average Convergence Divergence

Le MACD répond à la question : *"La tendance s'accélère-t-elle ou s'essouffle-t-elle ?"* Il indique si le *taux de variation* de la tendance est positif ou négatif.

---

## 💡 Signification Financière

Les traders surveillent le croisement de la ligne MACD et de la ligne de signal — un croisement haussier suggère une augmentation du momentum, tandis qu'un croisement baissier suggère un épuisement. Le MACD n'indique **pas** que le prix augmente (vous pouvez déjà le voir) ; il vous indique si le momentum augmente ou diminue.

---

## 🔢 Formules Mathématiques

Le système MACD produit trois séries :

1. **Ligne MACD** (la sortie passe-bande) :

 $$
 MACD_t = EMA_{fast}(C_t) - EMA_{slow}(C_t)
 $$

2. **Ligne de signal** (MACD lissé) :

 $$
 Signal_t = EMA_{signal}(MACD_t)
 $$

3. **Histogramme** (delta du momentum) :

 $$
 Histogram_t = MACD_t - Signal_t
 $$

---

## ⚙️ Paramètres

| Paramètre | Clé | Par défaut | Description |
|---|---|---|---|
| Période courte | `fastPeriod` | 12 | Fenêtre EMA à court terme (jours). |
| Période longue | `slowPeriod` | 26 | Fenêtre EMA à long terme (jours). |
| Période de signal | `signalPeriod` | 9 | Lissage EMA appliqué à la ligne MACD. |

---

## 🎛️ Équivalent en Traitement du Signal — Filtre Passe-Bande (Dérivée Lissée)

La soustraction de deux filtres passe-bas avec des fréquences de coupure différentes produit un **filtre passe-bande**. $EMA_{fast} - EMA_{slow}$ annule la composante continue (la tendance à long terme commune aux deux) et supprime le bruit haute fréquence (déjà filtré par les deux EMA). Ce qui reste est la bande de *fréquences moyennes* : l'oscillation du momentum.

Dans le domaine $z$ :

$$
H_{MACD}(z) = H_{fast}(z) - H_{slow}(z)
 = \frac{\alpha_f}{1-(1-\alpha_f)z^{-1}}
 - \frac{\alpha_s}{1-(1-\alpha_s)z^{-1}}
$$

La ligne de signal est un autre filtre passe-bas appliqué à cette sortie passe-bande — elle agit comme un **filtre adapté**, retardant légèrement le signal pour réduire les faux positifs lors de la détection des croisements.

!!! note "Derivative interpretation"

    Pour un $\alpha$ faible, $EMA_{fast} - EMA_{slow}$ se comporte comme une première
    dérivée lissée $\frac{d}{dt}[\text{tendance}]$. Lorsque l'histogramme change de signe, la
    "vélocité" de la tendance change de direction.

:material-link: [MACD sur Wikipedia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }
