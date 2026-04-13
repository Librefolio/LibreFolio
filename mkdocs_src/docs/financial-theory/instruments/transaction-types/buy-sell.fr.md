# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Achat & Vente

Les types de transactions les plus fondamentaux : l'**achat** augmente vos positions et diminue vos liquidités ; la **vente** fait l'inverse et réalise une plus-value ou une moins-value.

---

## 🔑 Propriétés Clés

| Propriété | Achat | Vente |
|----------|-----|------|
| **Code** | `BUY` | `SELL` |
| **Effet sur les liquidités** | ⬇️ Diminue | ⬆️ Augmente |
| **Effet sur l'actif** | ⬆️ Augmente les positions | ⬇️ Diminue les positions |
| **Événement fiscal** | Non | Oui (réalise une plus-value/moins-value) |

---

## 📊 Fonctionnement

### 🛒 Achat

Lorsque vous achetez un actif, un **lot** est créé avec :

- **Date** : Date à laquelle l'achat a eu lieu
- **Quantité** : Nombre d'actions/unités achetées
- **Prix unitaire** : Prix par action au moment de l'achat
- **Frais** : Tous les frais de transaction (commission, spread, etc.)
- **Coût total** : `quantity × unit_price + fees`

### 💰 Vente

Lorsque vous vendez, LibreFolio associe la vente aux lots existants en utilisant la méthode **FIFO** (First In, First Out) pour déterminer :

$$
\text{Plus-value} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Fees}
$$

!!! info "Appariement FIFO"

    LibreFolio calcule l'appariement des lots au **moment de l'exécution** — il n'est pas persisté dans la base de données. Cela permet des analyses de scénarios (« what-if ») flexibles et un support futur potentiel pour d'autres méthodes d'appariement (LIFO, identification spécifique).

---

## 📐 Prix de Revient (Cost Basis)

Le prix de revient de vos positions est le montant total que vous avez payé, frais inclus :

$$
\text{Prix de revient} = \sum_{i} (Q_i \times P_i + F_i)
$$

Ceci est utilisé pour calculer le P&L non réalisé à tout moment :

$$
\text{P\&L non réalisé} = \text{Valeur actuelle} - \text{Prix de revient}
$$

---

## 🔗 Liens connexes

- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Plus-values, méthodes d'appariement, report de pertes
- 📈 **[Rendements](../../fundamentals/returns.md)** — Mesure de la performance des investissements
