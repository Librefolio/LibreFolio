# 📏 Bandes de Bollinger

Les Bandes de Bollinger mesurent dynamiquement la **volatilité** et tracent une « barrière de normalité » adaptative autour du prix.

---

## 💡 Signification Financière

Lorsque les bandes sont larges, le marché est volatil ; lorsqu'elles se resserrent (squeeze), une cassure est imminente. Un prix touchant la bande supérieure signale une exubérance statistique ; un prix touchant la bande inférieure signale une baisse anormale.

---

## 🔢 Formules Mathématiques

1. **Bande Centrale** (valeur attendue) :

 $$
 MB_t = SMA_N(C_t)
 $$

2. **Écart-type** des prix sur la fenêtre :

 $$
 \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
 $$

3. **Bandes Supérieure et Inférieure** :

 $$
 Upper_t = MB_t + k \cdot \sigma_t, \qquad
 Lower_t = MB_t - k \cdot \sigma_t
 $$

Avec $k = 2$, si les rendements étaient distribués normalement, le prix resterait à l'intérieur des bandes environ 95,4 % du temps. En pratique, les rendements financiers présentent des *queues épaisses* (leptokurtosis), donc les franchissements sont plus fréquents — mais restent statistiquement significatifs.

---

## ⚙️ Paramètres

| Paramètre | Clé | Valeur par défaut | Description |
|---|---|---|---|
| Période ($N$) | `period` | 20 | Fenêtre SMA pour la valeur attendue. |
| Multiplicateur ($k$) | `multiplier` | 2 | Nombre d'écarts-types. |

---

## 🎛️ Équivalent en Traitement du Signal — Suiveur d'Intervalle de Confiance Adaptatif

La Bande Centrale est un **filtre à moyenne mobile FIR (Finite Impulse Response)** — le filtre passe-bas le plus simple avec une fenêtre rectangulaire de longueur $N$. Les bandes ajoutent une **enveloppe variant dans le temps** à $\pm k\sigma$, ce qui est essentiellement une estimation glissante de la variance instantanée du signal.

Dans le langage des filtres adaptatifs, il s'agit d'un **suiveur de valeur attendue avec un intervalle de confiance adaptatif**. Lorsque la variance $\sigma^2$ chute (le « Bollinger Squeeze »), le système est dans un état de faible entropie. Dans les systèmes chaotiques comme les marchés financiers, les périodes de faible entropie sont systématiquement suivies d'explosions à haute entropie (haute volatilité) — faisant du squeeze l'une des configurations les plus surveillées en analyse technique.

!!! info "FIR vs IIR"

    Contrairement à l'EMA (IIR, un pôle), la SMA est un **filtre FIR** avec un
    retard de groupe parfaitement plat de $(N-1)/2$ échantillons. Elle sacrifie
    une bande de transition plus large au profit d'une absence de distorsion de phase —
    idéal pour centrer l'enveloppe de confiance.

:material-link: [Bandes de Bollinger sur Wikipédia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }
