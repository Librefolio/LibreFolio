# 📖 Valeur Comptable

*[⬅️ Retour à l'aperçu des mesures de performance](index.md)*

## 💡 Qu'est-ce que la Valeur Comptable ?

La **Valeur Comptable** représente le coût comptable historique de votre portefeuille — le montant de capital déployé au prix d'achat, plus les réserves de trésorerie. Elle ne fluctue pas selon les prix du marché.

---

## 🧮 Formule

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Où le Prix de revient ouvert (Open Cost Basis) :

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

🔗 Voir **[Portfolio Engine — §3 État de la Position](portfolio-engine.md#3-etat-de-la-position)** pour la dérivation complète.

---

## ⚖️ Gains/Pertes non réalisés

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

---

## 📝 Exemple

| Composant | Montant |
|-----------|--------|
| Prix de revient ouvert | 27 000 € |
| Trésorerie | 600 € |
| Valeur comptable en transit | 0 € |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

Avec NAV = 33 000 € :

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Liens connexes

- 📊 [PMP](weighted-average-cost.md) — méthode du coût unitaire pour l'OCB
- 💼 [NAV](nav.md) — l'équivalent en valeur de marché
- 📈 [Period PnL](period-pnl.md) — combinaison des gains réalisés et non réalisés
