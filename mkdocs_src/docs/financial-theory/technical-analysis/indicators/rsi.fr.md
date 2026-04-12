# 💪 RSI — Relative Strength Index

Le RSI mesure si les acheteurs ou les vendeurs ont dominé *récemment*. Il répond à la question : *"Au cours des $N$ derniers jours, quelle part du mouvement total du prix a été haussière par rapport à la part baissière ?"*

---

## 💡 Signification Financière

Le résultat est compressé dans une plage de 0 à 100 :

- **RSI > 70** → Suracheté — le ressort est tendu, un repli est statistiquement probable.
- **RSI < 30** → Survendu — le ressort est compressé, un rebond est probable.

---

## 🔢 Formules Mathématiques

1. **Décomposer** les variations quotidiennes en gains et pertes :

 $$
 U_t = \max(P_t - P_{t-1},\; 0), \qquad
 D_t = \max(P_{t-1} - P_t,\; 0)
 $$

2. **Lisser** chaque composante avec une moyenne mobile exponentielle (variante SMMA) :

 $$
 \overline{U} = SMMA_N(U), \qquad
 \overline{D} = SMMA_N(D)
 $$

3. **Force Relative** (ratio RS) et normalisation :

 $$
 RS = \frac{\overline{U}}{\overline{D}}, \qquad
 RSI = 100 - \frac{100}{1 + RS}
 $$

La normalisation $100 - 100/(1+RS)$ est une sigmoïde monotone croissante qui projette $RS \in [0, \infty)$ vers $RSI \in [0, 100)$.

---

## ⚙️ Paramètres

| Paramètre | Clé | Défaut | Description |
|---|---|---|---|
| Période ($N$) | `period` | 14 | Fenêtre d'observation pour la SMMA. |
| Surachat | `overbought` | 70 | Seuil pour la zone de surachat. |
| Survente | `oversold` | 30 | Seuil pour la zone de survente. |

---

## 🎛️ Équivalent en Traitement du Signal — Cycle de Travail / Indicateur de Saturation

Imaginez que vous divisiez le signal du delta des prix $\Delta P[n]$ en ses composantes redressées demi-onde positive et négative, puis que vous appliquiez un filtre passe-bas à chacune. Le RSI est le **ratio de l'enveloppe positive par rapport à l'enveloppe totale**, remis à l'échelle de $[0, 100]$.

En termes de systèmes de contrôle, il s'agit d'un **détecteur de saturation** : lorsque la sortie du système (le prix) s'est déplacée dans une seule direction pendant trop longtemps, le RSI signale que l'actionneur (le marché) est proche de sa saturation. Comme tout oscillateur dans une boucle de rétroaction, plus on s'éloigne de l'équilibre, plus la force de rappel est forte — d'où la propriété de retour à la moyenne qu'exploitent les traders.

!!! warning "Non-stationnarité"

    Les seuils 70/30 supposent des distributions de rendements approximativement symétriques. Dans des marchés fortement tendanciels, le RSI peut rester au-dessus de 70 pendant des semaines — c'est un indicateur *probabiliste*, et non déterministe.

:material-link: [RSI sur Wikipédia](https://en.wikipedia.org/wiki/Relative_strength_index){ target="_blank" }
