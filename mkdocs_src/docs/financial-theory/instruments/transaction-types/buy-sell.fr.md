# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Achat & Vente ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACHAT' alt="Achat">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTE' alt="Vente">
</div>

Les types de transactions les plus fondamentaux : **acheter** augmente vos avoirs et diminue la trésorerie ; **vendre** fait l'inverse et constate un profit ou une perte.

---

## 🔑 Propriétés clés

| Propriété | Achat | Vente |
|----------|-------|-------|
| **Code** | `BUY` | `SELL` |
| **Effet sur la trésorerie** | ⬇️ Diminue | ⬆️ Augmente |
| **Effet sur les actifs** | ⬆️ Augmente les avoirs | ⬇️ Diminue les avoirs |
| **Événement fiscal** | Non | Oui (réalise une plus-value/perte) |

---

## 📊 Comment ça fonctionne

### 🛒 Achat

Lorsque vous achetez un actif, un **lot fiscal** est créé avec :

- **Date** : Quand l'achat a eu lieu
- **Quantité** : Nombre d'actions/unités achetées
- **Prix unitaire** : Prix par action au moment de l'achat
- **Frais** : Tous les frais de transaction (commission, spread, etc.)
- **Coût total** : `quantité × prix_unitaire + frais`

### 💰 Vente

Lorsque vous vendez, LibreFolio associe la vente aux lots fiscaux existants en utilisant la méthode **FIFO (PEPS - Premier Entré, Premier Sorti)** pour déterminer :

$$
\text{Plus-value} = (P_{vente} \times Q) - (P_{achat} \times Q) - \text{Frais}
$$

<div id="fifo-matching"></div>

!!! info "Appariement FIFO"

    LibreFolio calcule l'appariement des lots fiscaux **à l'exécution** — il n'est pas persistant dans la base de données. Cela permet une analyse flexible de scénarios de simulation et un potentiel support futur pour d'autres méthodes d'appariement (LIFO, identification spécifique).

---

## 🔗 Liens connexes

- 📊 **[Coût moyen pondéré (PMP)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Coût moyen par unité sur plusieurs achats
- 🔬 **[Analyse des lots FIFO](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)** — Analyse détaillée par lot fiscal de l'appariement FIFO présenté ci-dessus
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Plus-values, méthodes d'appariement, report de pertes
- 📈 **[Performance](../../fundamentals/returns.md)** — Mesure de la performance des investissements
