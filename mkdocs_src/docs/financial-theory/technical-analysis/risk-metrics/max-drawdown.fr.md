# 📉 Perte maximale

La perte maximale (MDD) mesure la **plus grande baisse entre un sommet et un point bas** de la valeur d'un portefeuille avant qu'un nouveau sommet ne soit établi. Il répond à la question : *« Quelle a été la pire perte qu'un investisseur aurait pu subir ? »*

---

## 🔢 Formule {: #formula }

$$
MDD = \frac{Trough - Peak}{Peak} = \min_{t} \left( \frac{V_t - \max_{\tau \leq t} V_\tau}{\max_{\tau \leq t} V_\tau} \right)
$$

où $V_t$ est la valeur du portefeuille au temps $t$.

Le repli à un instant $t$ quelconque est :

$$
DD_t = \frac{V_t - V_{peak}}{V_{peak}}
$$

La perte maximale est la valeur minimale (la plus négative) de $DD_t$ sur toute la période d'observation.

---

## 💡 Interprétation {: #interpretation }

| Perte maximale | Contexte typique |
|---|---|
| $-5\%$ à $-10\%$ | Correction normale, portefeuille bien diversifié |
| $-10\%$ à $-20\%$ | Correction significative |
| $-20\%$ à $-30\%$ | Territoire de marché baissier |
| $-30\%$ à $-50\%$ | Marché baissier sévère (2008, COVID-2020) |
| $> -50\%$ | Catastrophique (positions concentrées, crypto) |

!!! example "Exemple numérique"

    Séquence de valeur du portefeuille : 100 → 120 → 90 → 110 → 130

    - Sommet : 120
    - Point bas : 90
    - MDD : $(90 - 120) / 120 = -25\%$
    - Récupération : retour à 120, puis nouveau sommet à 130

---

## ⏱️ Temps de récupération {: #recovery-time }

Une mesure tout aussi importante est le **temps de récupération** — combien de temps le portefeuille est resté sous un sommet qu'il avait déjà atteint. Le chronomètre démarre au **sommet**, et non au point bas : il commence le jour où le portefeuille quitte son plus haut atteint et ne s'arrête que lorsque ce niveau est à nouveau atteint.

$$
T_{recovery} = t_{recovery} - t_{peak}
$$

La baisse fait donc partie du décompte, et la durée est exprimée en **jours calendaires** entre ces deux dates. Le pire épisode est toujours rapporté avec son état, et l'état détermine ce qui peut encore être dit à son sujet :

| État de récupération | Ce que cela signifie | Ce qui l'accompagne |
|---|---|---|
| *récupéré* | Le sommet précédent a été atteint à nouveau | Dates du sommet, du point bas et de récupération ; la durée est définitive |
| *ouvert* | Le sommet n'a pas été atteint à nouveau durant la période observée | Dates du sommet et du point bas, et **aucune date de récupération** ; la durée est toujours en cours |
| *sans repli* | Le portefeuille n'a jamais clôturé sous un sommet précédent | Aucune date et aucune fraction récupérée ; la profondeur et la durée sont nulles |

Il ne s'agit pas de conventions de présentation : ces combinaisons sont imposées sur le résultat lui-même, de sorte qu'un épisode ouvert ne peut pas porter de date de récupération, et qu'un épisode qui n'a jamais eu lieu ne peut pas porter de récupération partielle.

!!! info "Quand le repli est encore ouvert"

    Si le sommet n'a pas été atteint à nouveau à la fin de la période observée, il n'y a pas de date de récupération, et la durée est mesurée jusqu'à la dernière observation :

    $$
    T_{open} = t_{last} - t_{peak}
    $$

    Ce chiffre **augmente chaque jour qui passe** tant que le portefeuille reste sous le sommet : le chiffre n'est pas instable, l'épisode n'est simplement pas encore terminé.

    Un épisode ouvert porte également une **fraction récupérée** comprise entre $0$ et $1$ : quelle part de la chute, mesurée depuis le point bas, a déjà été remontée. C'est une lecture de progression plutôt qu'un verdict — la part de la descente qui a été annulée jusqu'ici — et c'est le chiffre qui répond à la question que se pose réellement un investisseur encore sous le sommet.

!!! warning "Pourquoi le décompte commence au sommet"

    Mesurer uniquement la remontée — du point bas à un nouveau sommet — donne toujours un nombre **plus petit**, car cela écarte la baisse elle-même. Mais l'investisseur était déjà sous son plus haut atteint pendant que le portefeuille chutait : cette portion n'est pas un prélude à la perte, c'est la perte en train de se produire. Commencer le décompte au sommet rapporte toute la période passée sous le sommet, qui est la période que l'investisseur a réellement dû traverser.

Contexte historique, par classe d'actifs :

| Classe d'actifs | Temps de récupération typique (après un repli majeur) |
|-------------|---------------------------------------------|
| Actions américaines (S&P 500) | 1 à 5 ans |
| Obligations | De quelques mois à 1 ou 2 ans |
| Crypto | Très variable (de quelques mois à plusieurs années) |

Ces chiffres relèvent de l'histoire générale des marchés, et non d'une mesure LibreFolio, et la base sur laquelle ils ont été comptés n'est pas précisée — les temps de récupération publiés sont parfois mesurés depuis le point bas, parfois depuis le sommet. Ils ne sont donc **pas directement comparables** avec la durée rapportée ci-dessus, qui compte toujours depuis le sommet et couvre donc une période plus longue qu'un chiffre basé sur le point bas pour le même épisode.

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

Le tableau ci-dessus présente l'arithmétique générale de l'asymétrie, tabulée selon la profondeur de la perte **maximale**. Le chiffre que le système calcule applique cette même formule au repli **actuel** : il répond à la question de savoir quel gain est nécessaire pour revenir au sommet *depuis la position actuelle du portefeuille*, ce qui est la seule version de la question sur laquelle on peut agir. Les deux lectures ne coïncident que lorsque le portefeuille se trouve à son point le plus bas historique — voir [Repli actuel](current-drawdown.md).

---

## 📊 Graphique de repli {: #drawdown-chart }

Un graphique de repli représente $DD_t$ en fonction du temps. Il est toujours nul ou négatif, et touche zéro à chaque nouveau sommet. La vallée la plus profonde est la perte maximale. Cette visualisation permet facilement de :

- Identifier le **moment** des pires périodes
- Voir à quelle fréquence les replis se produisent
- Comparer les schémas de récupération entre différentes stratégies

---

## 🔗 Voir aussi {: #related }

- 📊 **[Volatilité](volatility.md)** — L'écart-type ne capture pas la gravité du repli
- 📐 **[Ratio de Sharpe](sharpe-ratio.md)** — Rendement ajusté au risque (utilise la volatilité, pas le repli)
- 🔀 **[Diversification](../../portfolio-theory/diversification.md)** — Le principal outil pour réduire la perte maximale
