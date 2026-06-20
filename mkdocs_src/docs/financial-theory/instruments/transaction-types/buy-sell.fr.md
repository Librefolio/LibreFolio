# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Achat & Vente ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> BUY' alt="Buy">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> SELL' alt="Sell">
</div>

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
- **Coût total** : `quantité × prix_unitaire + frais`

### 💰 Vente

Lors d'une vente, LibreFolio associe la vente aux lots existants en utilisant la méthode **FIFO** (First In, First Out) pour déterminer :

$$
\text{Plus-value} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Frais}
$$

!!! info "Appariement FIFO"

    LibreFolio calcule l'appariement des lots à l'**exécution** — celui-ci n'est pas persisté dans la base de données. Cela permet des analyses de scénarios flexibles et un support futur potentiel pour d'autres méthodes d'appariement (LIFO, identification spécifique).

---

## 🔗 Liens connexes

- 📊 **[Coût Moyen Pondéré (CMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Coût moyen par unité sur plusieurs achats
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Plus-values, méthodes d'appariement, report de pertes
- 📈 **[Rendements](../../fundamentals/returns.md)** — Mesurer la performance des investissements
