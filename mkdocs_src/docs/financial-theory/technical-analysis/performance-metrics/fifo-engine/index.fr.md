# 🧬 FIFO Engine — Lot Lifecycle & Matching Model

## 💡 Aperçu

Alors que le [Prix Moyen Pondéré (PMP)](../weighted-average-cost.md) fusionne chaque acquisition d'une position en une moyenne continue, le moteur FIFO de LibreFolio conserve la trace de **lots individuels** — un par lot d'acquisition — tout au long de leur cycle de vie : ouverture, clôtures partielles, transferts entre courtiers, divisions et clôture définitive.

Cette page décrit le **fonctionnement** de ce moteur : comment les lots sont créés, appariés et clôturés. Pour les **métriques** dérivées de ce moteur (Rendement Ouvert/Total, mise à l'échelle qbq, allocation des revenus, un exemple pratique), voir [Analyse des Lots FIFO](fifo-lot-analysis.md).

Le moteur FIFO est indépendant du flux de prix. Il rejoue les quantités, lots, fragments, transferts et fermetures réalisées. Les niveaux de valorisation courants résident à l'extérieur : [Résolution des Prix](../portfolio-engine/price-resolution.md) et `LotsAnalysisService` fournissent les cours de référence/courants et le comportement au coût estimé.

!!! info "Deux moteurs, deux questions"

    Le [Moteur de Portefeuille](../index.md) (basé sur le PMP) répond à la question : _"Quel est mon coût de base consolidé pour cette position ?"_

    Le moteur FIFO répond à une question structurellement différente : _"Quel lot spécifique d'unités suis-je en train de vendre, et comment ce lot exact a-t-il performé ?"_

---

## 🧱 Qu'est-ce qu'un Lot ?

Un **lot** est un lot d'acquisition économique pour un actif : un seul ACHAT, le reliquat ouvert d'un ajustement d'inventaire, ou un transfert entrant qui conserve son coût de base d'origine. Un lot conserve sa propre identité pendant toute sa vie, même lorsqu'il se déplace entre courtiers ou se divise en plusieurs parties.

| Propriété | Signification |
|----------|---------------|
| Direction | `LONG` (acheté en premier) ou `SHORT` (vendu en premier, uniquement lorsque le courtier autorise la vente à découvert) |
| Date et courtier d'ouverture | Où et quand le lot a été créé |
| Quantité et coût d'origine | Fixés à l'ouverture, ensuite modifiés uniquement par les divisions — jamais par les transferts |
| Quantité ouverte | Quelle partie du lot n'a **pas** encore été appariée par une transaction opposée |
| Conservation | Quel courtier (ou courtiers, dans le temps) détient actuellement la quantité ouverte |
| Prix de référence | `reference_unit_price` plus `reference_price_source` (`exact`, `fallback`, `none`) |

---

## 🔁 États du Cycle de Vie d'un Lot

| État | Signification |
|------|---------------|
| **OUVERT** | Rien n'a encore été apparié — la totalité de la quantité d'origine est toujours détenue |
| **PARTIELLEMENT_CLOS** | Une partie, mais pas la totalité, du lot a été appariée par des transactions opposées ultérieures |
| **CLOS** | La totalité du lot a été appariée — il ne reste rien d'ouvert |

Un lot passe d'OUVERT → PARTIELLEMENT_CLOS → CLOS strictement dans le temps au fur et à mesure que l'appariement le consomme ; il ne se rouvre jamais. Indépendamment de ce cycle de vie, un lot peut également être étiqueté :

- **EN_TRANSIT** — une partie de sa quantité ouverte est actuellement en cours de transfert entre courtiers
- **DISTRIBUÉ** — sa quantité ouverte est actuellement répartie sur plusieurs lieux de conservation à la fois
- **DÉGRADÉ** — un problème de qualité de données a été enregistré pour ce lot spécifique (voir [Qualité des Données](#data-quality-best-effort-not-all-or-nothing) ci-dessous)

---

## 📅 Traitement Chronologique des Événements

LibreFolio rejoue chaque transaction pour un actif **dans l'ordre chronologique**, en classant chacune dans un type d'événement :

| Événement | Effet |
|-----------|-------|
| ACHAT | Ferme d'abord tout lot SHORT ouvert sur ce courtier ; tout reliquat ouvre un nouveau lot LONG |
| VENTE | Ferme les lots LONG ouverts dans l'ordre FIFO sur ce courtier ; tout reliquat ouvre un nouveau lot SHORT uniquement lorsque le courtier autorise la vente à découvert |
| Ajustement entrée/sortie | Même logique d'appariement que ACHAT/VENTE, à coût nul |
| DIVISION | Redimensionne la quantité et le coût unitaire pour chaque lot ouvert de l'actif |
| Transfert (départ / arrivée) | Déplace la conservation de la quantité ouverte d'un lot d'un courtier à un autre |

!!! info "Ordre le même jour"

    Lorsque plusieurs événements tombent à la même date, LibreFolio les traite toujours dans un ordre fixe — départs de transfert, puis arrivées de transfert, puis divisions, puis achats/ventes/ajustements ordinaires — afin que les transferts et les divisions du même jour voient toujours un état de conservation cohérent.

---

## ⛏️ Appariement FIFO

Lorsqu'un événement de clôture (une VENTE, ou la branche de direction opposée d'un ajustement) doit consommer une quantité $Q$, LibreFolio s'apparie toujours contre le **lot encore ouvert le plus ancien en premier**, sur ce même courtier :

$$
\text{OrdreAppariement} = \text{trier par } (\text{DateOuverture}, \text{IdLot})
$$

Il parcourt cette liste ordonnée, en fermant la quantité du lot le plus ancien jusqu'à ce que $Q$ soit entièrement apparié, en ne passant au lot suivant le plus ancien qu'une fois le lot actuel épuisé. Le profit ou la perte réalisé est calculé **par pièce appariée**, en utilisant le prix porté par le fragment exact du lot consommé :

$$
\text{PnLRéalisé}_{\text{LONG}} = \text{QuantitéAppariée} \times (\text{PrixClôture} - \text{CoûtUnitaireLot})
$$

$$
\text{PnLRéalisé}_{\text{SHORT}} = \text{QuantitéAppariée} \times (\text{CoûtUnitaireLot} - \text{PrixClôture})
$$

C'est pourquoi deux lots du même actif, achetés à des moments et à des prix différents, peuvent afficher des résultats réalisés très différents même s'ils sont appariés plus tard le même jour au même prix — voir l'exemple pratique dans [Analyse des Lots FIFO](fifo-lot-analysis.md).

---

## ✂️ Divisions — Redimensionnement Quantité/Prix

Une division d'action (ou division inversée) avec un ratio $r$ redimensionne chaque fragment **actuellement ouvert** de chaque lot concerné :

$$
\text{NouvelleQuantité} = \text{Quantité} \times r
\qquad
\text{NouveauCoûtUnitaire} = \frac{\text{CoûtUnitaire}}{r}
$$

Le coût économique de la position est invariant à travers une division — seules la quantité et le coût unitaire changent, dans des directions opposées, donc $\text{Quantité} \times \text{CoûtUnitaire}$ reste constant pour chaque lot.

---

## 🚚 Transferts — Mouvement de Conservation, Pas une Vente

Un transfert entre courtiers est modélisé comme un **changement de conservation**, jamais comme une cession :

- **Départ** — LibreFolio extrait la quantité transférée du courtier source dans l'ordre FIFO. Si le transfert prend plus d'un jour pour se régler, il ouvre un fragment temporaire **en transit** de conservation en attendant.
- **Arrivée** — À l'arrivée, le fragment en transit se ferme et un fragment équivalent se rouvre chez le courtier de destination, en reprenant la **même quantité et le même coût unitaire**.

L'identité du lot, sa date d'ouverture et son coût d'origine ne changent jamais à cause d'un transfert — seulement *l'endroit* où il est actuellement détenu. Aucun profit ou perte n'est jamais réalisé par un transfert.

Cet historique de conservation — quel courtier (ou en transit) détenait la quantité ouverte d'un lot, et combien, à chaque instant — est exactement ce qui alimente la chronologie **Durée de Vie du Lot et Conservation** dans le [panneau d'Analyse des Lots FIFO](../../../../user/dashboard/positions.md#fifo-lots-analysis) : chaque segment de barre est coloré par le courtier de conservation qui le détient, et son épaisseur reflète la quantité détenue pendant ce segment.

---

## ⚠️ Qualité des Données : Au Mieux, Pas de Tout ou Rien {: #data-quality-best-effort-not-all-or-nothing }

Si l'historique des transactions contient quelque chose que le moteur ne peut pas résoudre complètement — par exemple une transaction de clôture sans lot ouvert correspondant chez ce courtier, ou un transfert dont la branche associée est manquante — LibreFolio **n'abandonne pas** tout le calcul. Il enregistre le problème spécifique, marque le(s) lot(s) concerné(s) comme dégradé(s) et continue de traiter le reste de l'historique avec les meilleures données disponibles.

Le résultat global est ensuite marqué **complet** ou **dégradé** dans son ensemble, mais les graphiques et tableaux construits sur un résultat dégradé s'affichent toujours normalement pour chaque lot qui **n'a pas** été affecté. Vous pouvez voir cela reflété comme une bannière de qualité de données dans le [panneau d'Analyse des Lots FIFO](../../../../user/dashboard/positions.md#fifo-lots-analysis).

---

## 🔗 Liens connexes

- 🔬 **[Analyse des Lots FIFO](fifo-lot-analysis.md)** — Métriques dérivées de ce moteur : Rendement Ouvert/Total par lot, mise à l'échelle qbq, allocation des revenus, exemple pratique
- 🧭 **[Résolution des Prix](../portfolio-engine/price-resolution.md)** — Niveaux de valorisation utilisés par le service des lots
- ⚙️ **[Moteur de Portefeuille](../index.md)** — Le moteur complémentaire basé sur l'agrégat/PMP, et comment les deux sont liés
- 📊 **[Prix Moyen Pondéré (PMP)](../weighted-average-cost.md)** — Coût de base consolidé au niveau de la position
- 🧬 **[Moteur de Lot FIFO (Manuel du Développeur)](../../../../developer/backend/transactions/fifo_lot_engine.md)** — Plongée approfondie dans l'implémentation : classes, répartition des événements, contraintes au niveau du code
- 📈 **[Aperçu des Métriques de Performance](../index.md)** — Toutes les métriques de performance en un coup d'œil
