# 🌊 Onde Sinusoïdale

Un benchmark d'onde sinusoïdale représente une **oscillation périodique**. C'est le seul benchmark non basé sur la croissance dans LibreFolio.

---

## 💡 Signification Financière

Utile pour :

- Modéliser la **saisonnalité** (ex: matières premières agricoles, devises liées au tourisme).
- Fournir une référence visuelle pour des **schémas cycliques** que les traders soupçonnent dans les données.
- Tester le pipeline de rendu avec une forme d'onde analytique connue.

---

## 🔢 Formule Mathématique

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{offset}
$$

où :

- $A$ est l'amplitude (plage crête-à-crête en % de la valeur de base),
- $T$ est la période en jours,
- $y_0$ est la valeur de base (premier point de données),
- $\text{offset}$ est un décalage vertical.

---

## ⚙️ Paramètres

| Paramètre | Clé | Par défaut | Description |
|---|---|---|---|
| Amplitude | `amplitude` | 10 | Plage d'oscillation crête-à-crête en % de la valeur de base. |
| Période | `period` | 365 | Longueur d'un cycle complet en jours. |
| Décalage | `offset` | 0 | Décalage vertical en % de la valeur de base. |

---

## 🔍 Interprétation

Si le prix réel suit approximativement le benchmark sinusoïdal, le marché présente une composante cyclique détectable à cette fréquence. Les écarts par rapport à la sinusoïde suggèrent des chocs non périodiques ou une dérive de tendance. L'ajustement du paramètre de période vous permet de balayer différentes longueurs de cycle — réalisant ainsi une version manuelle de l'analyse spectrale.

:material-link: [Onde sinusoïdale sur Wikipédia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }
