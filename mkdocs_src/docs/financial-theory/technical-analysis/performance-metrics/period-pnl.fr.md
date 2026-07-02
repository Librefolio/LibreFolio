# 📊 PnL de Période (Profit and Loss)

*[⬅️ Retour à l'aperçu des indicateurs de performance](index.md)*

## 💡 Qu'est-ce que le PnL de période ?

Le gain ou la perte monétaire absolue générée par votre portefeuille au cours de $[t_0, t_1]$, ajustée en fonction des flux de trésorerie externes.

---

## 🧮 Formule

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \mathrm{ECF}_{[t_0, t_1]}}
$$

Où $\mathrm{ECF}$ = Flux de trésorerie externes nets (dépôts − retraits sur la période).

---

## 🧮 Décomposition

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{Fees} + \mathrm{Other}
$$

| Composante | Définition |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variation des gains/pertes non réalisés sur la période |
| Réalisé | Somme des (produits de vente − prix de revient) pour les ventes (SELL) sur la période |
| Income | DIVIDENDE + INTÉRÊT sur la période |
| Frais | FRAIS + TAXE sur la période |
| Other | Résiduel (effets de change, arrondis) |

---

## 🎯 Contribution par actif

Pour chaque position $(a,b)$ :

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

L'ensemble des positions inclut **toute l'activité** de la période :

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \text{keys(Realized)} \cup \text{keys(Income)} \cup \text{keys(Fees)}
$$

🔗 Voir **[Portfolio Engine — §7 Contribution de Période](portfolio-engine.md#7-period-contribution)** pour plus de détails.

---

## 📝 Exemple

- NAV à $t_0$ : 27 000 €
- Dépôts sur la période : 1 000 €
- NAV à $t_1$ : 33 000 €

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Liens connexes

- 💼 [NAV](nav.md) — résultat final de chaque formule de PnL
- 💸 [Capital déposé](deposited-capital.md) — PnL Total depuis l'origine
- ⚙️ [Portfolio Engine](portfolio-engine.md) — modèle mathématique complet
