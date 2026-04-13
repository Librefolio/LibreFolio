# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Dépôts & Retraits

Les **dépôts** et les **retraits** suivent les mouvements de liquidités entrant et sortant d'un compte courtier. Ils n'impliquent aucun actif — seul le solde de trésorerie change.

---

## 🔑 Propriétés Clés

| Propriété | Dépôt | Retrait |
|----------|---------|------------|
| **Code** | `DEPOSIT` | `WITHDRAWAL` |
| **Effet sur la trésorerie** | ⬆️ Augmente le solde | ⬇️ Diminue le solde |
| **Effet sur l'actif** | — | — |
| **Événement fiscal** | Non | Non |

---

## 📊 Pourquoi sont-ils importants ?

### 📐 Rendement pondéré par les flux

Les dépôts et les retraits sont essentiels pour calculer le **rendement pondéré par les flux** (MWR / IRR). Sans le suivi des flux de trésorerie, il est impossible de distinguer les rendements générés par le portefeuille des rendements résultant de l'ajout ou du retrait de liquidités.

$$
0 = \sum_{i=0}^{n} \frac{CF_i}{(1 + r)^{t_i}}
$$

où $CF_i$ représente chaque flux de trésorerie (dépôts positifs, retraits négatifs, valeur finale positive).

### 📊 Rendement Pondéré dans le Temps

Le **rendement pondéré dans le temps** (TWR) élimine l'effet des flux de trésorerie en calculant les rendements entre chaque événement de flux de trésorerie et en les enchaînant :

$$
R_{TWR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

Cela donne une mesure de performance "pure" du portefeuille, indépendante du moment des dépôts ou retraits.

---

## 🔗 Liens Connexes

- 📈 **[Rendements & Taux de Croissance](../../fundamentals/returns.md)** — Calcul TWR vs MWR
- 🛒 **[Achat & Vente](buy-sell.md)** — Transactions utilisant les liquidités déposées
