# <img src="../../../static/icons/transactions/transfer.png" width="32" style="vertical-align: middle;" /> Transferts & Conversion de devises

Les **Transferts** déplacent des actifs entre des portefeuilles sans vente, tandis que les **Conversions de devises** échangent une devise contre une autre au sein d'un portefeuille.

---

## 🔑 Propriétés Clés

| Propriété | Transfert Entrant | Transfert Sortant | Conversion de devises |
|----------|------------|-------------|---------------|
| **Code** | `TRANSFER_IN` | `TRANSFER_OUT` | `FX_CONVERSION` |
| **Effet sur les liquidités** | — | — | ⬆️⬇️ (échange) |
| **Effet sur l'actif** | ⬆️ Augmente | ⬇️ Diminue | — |
| **Événement fiscal** | Varie selon la juridiction | Varie | Varie |

---

## 🔄 Transfert Entrant / Sortant

Les transferts modélisent le mouvement d'actifs entre des comptes de courtier ou des portefeuilles **sans vente**. Scénarios courants :

- Transfert d'actions d'un courtier à un autre
- Héritage d'actifs
- Contributions en nature vers un type de compte différent (ex: ISA, 401k)

!!! info "Préservation du Prix de Revient"

    Lors du transfert d'actifs, le **prix de revient original** doit être préservé. Le transfert lui-même n'est pas un événement imposable dans la plupart des juridictions (bien que les règles varient).

---

## 💱 Conversion de devises

Échanges de devises au sein d'un portefeuille :

$$
\text{Amount}_{target} = \text{Amount}_{source} \times \text{FX Rate} - \text{Fees}
$$

Les conversions de devises peuvent être :

- **Explicites** : L'utilisateur convertit délibérément des devises (ex: EUR → USD)
- **Implicites** : Le courtier convertit automatiquement lors de l'achat d'un actif libellé en devise étrangère

---

## 📊 Ajustement

Le type de transaction `ADJUSTMENT` est un fourre-tout pour les corrections manuelles des soldes de liquidités ou d'actifs. Cas d'utilisation :

- Correction d'erreurs d'importation
- Enregistrement d'opérations sur titres non couvertes par les types standards
- Configuration du solde initial

---

## 🔗 Liens Connexes

- 🛒 **[Achat & Vente](buy-sell.md)** — Transactions d'actifs standards
- 💵 **[Dépôt & Retrait](deposit-withdrawal.md)** — Mouvements de liquidités
- 💰 **[Taux de change](../../../user/fx/index.md)** — Gestion des taux de change
