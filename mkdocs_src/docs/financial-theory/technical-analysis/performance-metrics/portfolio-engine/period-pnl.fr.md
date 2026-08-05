# 📊 PnL de la période (Pertes et profits)

*[⬅️ Retour à l'aperçu des indicateurs de performance](../index.md)*

## 💡 Qu'est-ce que le PnL de la période ?

Le résultat monétaire absolu (gain ou perte) généré par votre portefeuille sur $[t_0, t_1]$, ajusté des flux de trésorerie externes.

---

## 🧮 Formule

$$
\boxed{\mathrm{PnL}_{\text{period}} = \mathrm{NAV}(t_1)-\mathrm{NAV}(t_0)-\Delta \mathrm{CapitalBaseline}_{[t_0,t_1]}}
$$

Le delta de la ligne de base provient de `cumulative_external_cash_flow` ; il inclut donc les flux de trésorerie et le capital en nature valorisé des opérations ADJUSTMENT/TRANSFER.

---

## 🧮 Décomposition

$$
\mathrm{PnL}_{\text{period}} = \Delta\mathrm{UGL} + \mathrm{Realized} + \mathrm{Income} - \mathrm{FeesTaxes} + \mathrm{Other}
$$

| Composante | Définition |
|-----------|-----------|
| $\Delta\mathrm{UGL}$ | Variation des plus-values/moins-values latentes sur la période |
| Realized | Somme de (produit de vente − coût de base) pour les opérations SELL de la période |
| Income | DIVIDEND + INTEREST sur la période |
| FeesTaxes | FEE + TAX sur la période |
| Other | Résidu qui équilibre l'identité |

Le résidu est calculé comme suit :

$$
\mathrm{Other} = \mathrm{PnL}_{\text{period}} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

---

## 🎯 Contribution par actif

Pour chaque position $(a,b)$ :

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

L'ensemble des positions comprend **toute l'activité** de la période :

$$
\mathcal{P} = \text{positions avec activité BUY/SELL/ADJUSTMENT/TRANSFER ou quantité limite}
$$

Le rendement annualisé de la période borne le début de sa fenêtre à la date la plus tardive parmi la date de début demandée et la date du plus ancien lot ouvert. Il utilise $|\mathrm{StartValue}|$ comme base d'annualisation, avec repli (fallback) sur le coût de base de fin pour les positions ouvertes en milieu de période. Voir [Rendement annualisé net](net-annualized-return.md).

🔗 Voir **[Moteur de portefeuille — §7 Contribution de la période](index.md#7-period-contribution)** pour plus de détails.

---

## 📝 Exemple

- NAV à $t_0$ : 27 000 €
- Augmentation de la ligne de base du capital sur la période : 1 000 €
- NAV à $t_1$ : 33 000 €

$$
\mathrm{PnL} = 33\,000 - 27\,000 - 1\,000 = +5\,000 \text{ EUR}
$$

---

## 🔗 Voir aussi

- 💼 [NAV](nav.md) — aboutissement de chaque formule de PnL
- 💸 [Capital déposé](deposited-capital.md) — PnL total depuis la création
- ⚙️ [Moteur de portefeuille](index.md) — modèle mathématique complet
