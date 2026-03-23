# 📉 Indicateurs techniques

Cette page documente les indicateurs d'analyse technique disponibles en superposition sur les graphiques dans le module FX de LibreFolio. Chaque indicateur est expliqué selon deux perspectives complémentaires : l'interprétation **financière** que les traders utilisent au quotidien, et l'équivalent en **traitement du signal** que les ingénieurs en systèmes de commande ou en traitement du signal reconnaîtront instantanément.

!!! info "Pourquoi deux perspectives ?"

    Les marchés financiers ne sont **pas** des systèmes LTI (Linéaires et Invariants dans le Temps) stationnaires — ils sont bruyants, chaotiques, et leur contenu spectral évolue dans le temps. Pourtant, les outils mathématiques que nous appliquons pour extraire tendance, momentum ou volatilité sont *exactement* les mêmes filtres à temps discret enseignés dans tout cours de traitement du signal. Si vous avez déjà conçu un filtre passe-bas de Butterworth ou calculé une variance glissante, vous comprenez déjà ces indicateurs — simplement sous d'autres noms.

---

## ⚡ L'intuition "rapide" vs "lent"

En finance, *rapide* et *lent* se réfèrent à la **constante de temps** ($\tau$) du filtre sous-jacent.

| Propriété | Rapide (petit $N$) | Lent (grand $N$) |
|---|---|---|
| Fréquence de coupure $f_c$ | Plus élevée | Plus basse |
| Rejet du bruit | Médiocre — laisse passer les hautes fréquences | Bon — fort lissage |
| Déphasage | Faible — réagit rapidement | Important — retard significatif |
| $N$ typique | 9, 12, 14 | 26, 50, 200 |

---

## 📉 EMA — Moyenne Mobile Exponentielle { #ema }

### 💡 Signification financière

L'EMA suit la **tendance** en lissant le bruit des prix quotidiens, en accordant plus de poids aux observations récentes qu'aux anciennes. Les traders superposent des EMA de périodes différentes sur un graphique de prix : lorsqu'une EMA à courte période croise *au-dessus* d'une EMA à longue période, cela signale une dynamique haussière (une "croix dorée") ; le croisement inverse signale un ralentissement ("croix de la mort").

### 🔢 Formule mathématique

L'EMA est définie par la récurrence du premier ordre :

$$
EMA_t = \alpha \cdot P_t + (1 - \alpha) \cdot EMA_{t-1}
$$

où $P_t$ est le prix de clôture au temps $t$ et $\alpha$ est le **coefficient de lissage**.

**Correspondance $N$ → $\alpha$.**
Les traders spécifient une "période" $N$ (en jours). Le coefficient est dérivé en égalisant l'*âge moyen* des données entre une EMA et une Moyenne Mobile Simple (SMA) de même fenêtre :

$$
\text{Âge}_{SMA} = \frac{N-1}{2}, \qquad
\text{Âge}_{EMA} = \frac{1-\alpha}{\alpha}
$$

En les égalant :

$$
\alpha = \frac{2}{N+1}
$$

Par exemple, $N = 14 \implies \alpha = 2/15 \approx 0,133$.

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Période ($N$) | `period` | 14 | Fenêtre d'analyse en jours. Plus élevé → plus lisse, plus lent. |
| Décalage | `offset` | 0 | Décalage vertical en pourcentage de la valeur de base. |

### 🎛️ Équivalent en traitement du signal — Filtre passe-bas IIR du premier ordre

La récurrence $y[n] = \alpha\,x[n] + (1-\alpha)\,y[n-1]$ est précisément un **filtre passe-bas IIR (Impulsionnelle Infinie) du premier ordre**. Sa fonction de transfert dans le domaine $z$ est :

$$
H(z) = \frac{\alpha}{1 - (1-\alpha)\,z^{-1}}
$$

La fréquence de coupure à $-3\,\text{dB}$ (normalisée) est :

$$
\omega_c = \cos^{-1}\!\left(1 - \frac{\alpha^2}{2(1-\alpha)}\right)
$$

Lorsque $\alpha$ est petit ($N$ grand), la bande passante se rétrécit dramatiquement, atténuant toute composante autre que la continue (la tendance à long terme).

!!! astuce "Position du pôle"

    Le pôle unique se situe à $z = 1-\alpha$. Pour $N = 200$, $\alpha \approx 0,01$, donc le pôle est à $z = 0,99$ — extrêmement proche du cercle unité, ce qui explique le lissage important et le grand retard de groupe.

:material-link: [EMA sur Wikipédia](https://en.wikipedia.org/wiki/Exponential_smoothing){ target="_blank" }

---

## 📊 MACD — Convergence/Divergence des Moyennes Mobiles { #macd }

### 💡 Signification financière

Le MACD répond à la question : *"La tendance s'accélère-t-elle ou perd-elle de la vitesse ?"* Il ne vous dit **pas** que le prix monte (vous le voyez déjà) ; il vous indique si le *taux de variation* de la tendance est positif ou négatif. Les traders surveillent le croisement de la ligne MACD avec la ligne de signal — un croisement haussier suggère une dynamique croissante, un croisement baissier suggère l'épuisement.

### 🔢 Formules mathématiques

Le système MACD produit trois séries :

1. **Ligne MACD** (sortie passe-bande) :

 $$
 MACD_t = EMA_{rapide}(C_t) - EMA_{lente}(C_t)
 $$

2. **Ligne de signal** (MACD lissé) :

 $$
 Signal_t = EMA_{signal}(MACD_t)
 $$

3. **Histogramme** (delta de momentum) :

 $$
 Histogramme_t = MACD_t - Signal_t
 $$

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Période rapide | `fastPeriod` | 12 | Fenêtre d'EMA à court terme (jours). |
| Période lente | `slowPeriod` | 26 | Fenêtre d'EMA à long terme (jours). |
| Période de signal | `signalPeriod` | 9 | Lissage EMA appliqué à la ligne MACD. |

### 🎛️ Équivalent en traitement du signal — Filtre passe-bande (dérivée lissée)

Soustraire deux filtres passe-bas avec des fréquences de coupure différentes produit un **filtre passe-bande**. $EMA_{rapide} - EMA_{lente}$ annule la composante continue (tendance à long terme partagée par les deux) et supprime le bruit haute fréquence (déjà filtré par les deux EMA). Ce qui reste est la bande de *moyenne fréquence* : l'oscillation de momentum.

Dans le domaine $z$ :

$$
H_{MACD}(z) = H_{rapide}(z) - H_{lente}(z)
 = \frac{\alpha_r}{1-(1-\alpha_r)z^{-1}}
 - \frac{\alpha_l}{1-(1-\alpha_l)z^{-1}}
$$

La Ligne de Signal est une autre application de passe-bas à cette sortie passe-bande — elle agit comme un **filtre adapté**, retardant légèrement le signal pour réduire les détections de croisements faux positifs.

!!! note "Interprétation dérivée"

    Pour de petits $\alpha$, $EMA_{rapide} - EMA_{lente}$ se comporte comme une première dérivée lissée $\frac{d}{dt}[\text{tendance}]$. Lorsque l'histogramme change de signe, la "vitesse" de la tendance change de direction.

:material-link: [MACD sur Wikipédia](https://en.wikipedia.org/wiki/MACD){ target="_blank" }

---

## 💪 RSI — Indice de Force Relative { #rsi }

### 💡 Signification financière

Le RSI mesure si les acheteurs ou les vendeurs ont dominé *récemment*. Il répond à : *"Au cours des $N$ derniers jours, quelle part du mouvement total de prix était haussière vs baissière ?"* Le résultat est **comprimé dans l'intervalle [0, 100]** :

- **RSI > 70** → Surachat — le ressort est étiré, un reflux est statistiquement probable.
- **RSI < 30** → Survente — le ressort est comprimé, un rebond est probable.

### 🔢 Formules mathématiques

1. **Décomposer** les variations quotidiennes en gains et pertes :

 $$
 U_t = \max(P_t - P_{t-1},\; 0), \qquad
 D_t = \max(P_{t-1} - P_t,\; 0)
 $$

2. **Lisser** chaque composant avec une moyenne mobile exponentielle lissée (variante SMMA) :

 $$
 \overline{U} = SMMA_N(U), \qquad
 \overline{D} = SMMA_N(D)
 $$

3. **Rapport de force relative** et normalisation :

 $$
 RS = \frac{\overline{U}}{\overline{D}}, \qquad
 RSI = 100 - \frac{100}{1 + RS}
 $$

La normalisation $100 - 100/(1+RS)$ est une sigmoïde monotonement croissante qui mappe $RS \in [0, \infty)$ vers $RSI \in [0, 100)$.

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Période ($N$) | `period` | 14 | Fenêtre d'analyse pour la SMMA. |
| Surachat | `overbought` | 70 | Seuil de la zone de surachat. |
| Survente | `oversold` | 30 | Seuil de la zone de survente. |

### 🎛️ Équivalent en traitement du signal — Indicateur de cycle de service / de saturation

Imaginez séparer le signal de delta de prix $\Delta P[n]$ en ses composants redressés demi-onde positif et négatif, puis filtrer chacun par un passe-bas. Le RSI est le **rapport de l'enveloppe positive sur l'enveloppe totale**, rééchelonné sur $[0, 100]$.

En termes de systèmes de commande, c'est un **détecteur de saturation** : lorsque la sortie du système (prix) a évolué dans une direction trop longtemps, le RSI signale que l'actionneur (marché) est près de sa butée. Comme tout oscillateur en boucle de rétroaction, plus il s'éloigne de l'équilibre, plus la force de rappel est forte — d'où la propriété de retour à la moyenne que les traders exploitent.

!!! warning "Non-stationnarité"

    Les seuils 70/30 supposent des distributions de rendement approximativement symétriques. Dans des marchés en forte tendance, le RSI peut rester au-dessus de 70 pendant des semaines — c'est un indicateur *probabiliste*, pas déterministe.

:material-link: [RSI sur Wikipédia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }

---

## 📏 Bandes de Bollinger { #bollinger-bands }

### 💡 Signification financière

Les Bandes de Bollinger mesurent dynamiquement la **volatilité** et tracent une **"clôture de normalité" adaptative** autour du prix. Lorsque les bandes sont larges, le marché est volatil ; lorsqu'elles se rapprochent (un "serrement"), une rupture est imminente. Un prix touchant la bande supérieure signale une exubérance statistique ; toucher la bande inférieure signale une chute anormale.

### 🔢 Formules mathématiques

1. **Bande médiane** (espérance) :

 $$
 MB_t = SMA_N(C_t)
 $$

2. **Écart-type** des prix sur la fenêtre d'analyse :

 $$
 \sigma_t = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} (C_{t-i} - MB_t)^2}
 $$

3. **Bandes supérieure et inférieure** :

 $$
 Upper_t = MB_t + k \cdot \sigma_t, \qquad
 Lower_t = MB_t - k \cdot \sigma_t
 $$

Avec $k = 2$, si les rendements étaient normalement distribués, le prix resterait à l'intérieur des bandes ~95,4% du temps. En pratique, les rendements financiers ont des *queues épaisses* (leptokurtose), donc les franchissements sont plus fréquents — mais restent statistiquement significatifs.

### ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Période ($N$) | `period` | 20 | Fenêtre d'analyse pour la SMA. |
| Multiplicateur ($k$) | `multiplier` | 2 | Nombre d'écarts-types. |

### 🎛️ Équivalent en traitement du signal — Suivi d'intervalle de confiance adaptatif

La Bande médiane est un filtre **FIR (Impulsionnelle Finie) de moyenne mobile** — le passe-bas le plus simple avec une fenêtre rectangulaire de longueur $N$. Les bandes ajoutent une **enveloppe variable dans le temps** à $\pm k\sigma$, ce qui est essentiellement une estimation glissante de la variance instantanée du signal.

Dans le langage des filtres adaptatifs, c'est un **suivi d'espérance avec intervalle de confiance adaptatif**. Lorsque la variance $\sigma^2$ baisse (le "serrement"), le système est dans un état basse entropie. Dans les systèmes chaotiques comme les marchés financiers, les périodes basse entropie sont systématiquement suivies d'explosions haute entropie (haute volatilité) — faisant du serrement l'une des configurations les plus surveillées en analyse technique.

!!! info "FIR vs IIR"

    Contrairement à l'EMA (IIR, un pôle), la SMA est un **filtre FIR** avec un retard de groupe parfaitement plat de $(N-1)/2$ échantillons. Elle sacrifie une bande de transition plus large pour éviter la distorsion de phase — idéal pour centrer l'enveloppe de confiance.

:material-link: [Bandes de Bollinger sur Wikipédia](https://en.wikipedia.org/wiki/Bollinger_Bands){ target="_blank" }

---
[Traducteur's Notes]
