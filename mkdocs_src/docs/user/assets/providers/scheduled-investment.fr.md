# <img src="../../../../static/scheduled_investment.png" alt=""> Investissement programmé

Le fournisseur Investissement programmé calcule la valeur d'un actif à partir de son calendrier
d'intérêts plutôt qu'en lisant un prix de marché. Utilisez-le pour les comptes d'épargne, les dépôts
à terme, les prêts P2P ou de crowdfunding, et les obligations que vous suivez via leurs intérêts
courus. Dans la liste **Fournisseur**, il s'appelle **Calculateur d'investissement programmé**.

## 🔍 Ce qu'il propose

- ✅ **Prix actuel** et **historique**, calculés à partir de votre calendrier : aucun site web n'est
  interrogé, et le même calendrier donne toujours les mêmes valeurs.
- ✅ **Événements** : avec **Générer le coupon**, les versements d'intérêts et un règlement final à
  l'échéance, plus les événements que vous ajoutez vous-même.
- ❌ **Recherche** et **détails** : non applicables. Il n'y a pas non plus d'identifiant à saisir :
  LibreFolio en crée un pour vous.

## 📋 Éditeur de calendrier d'intérêts {: #interest-schedule-editor }

Choisir le fournisseur dans **Affectation du fournisseur** ouvre l'éditeur **Calendrier
d'intérêts**. Commencez par les paramètres valables pour l'ensemble du calendrier :

- **Valeur initiale** et **Devise** : le montant investi, ou la valeur nominale — par ex. 10 000 EUR.
- **Type d'intérêt** : **Simple** ou **Composé** — voir
  [Comment la valeur est calculée](#how-value-is-calculated).
- **Décompte des jours** : la façon dont les jours d'une année sont comptés — **ACT/365**,
  **ACT/360**, **ACT/ACT** ou **30/360**. Voir
  [Conventions de décompte des jours](../../../financial-theory/fundamentals/day-count.md).

Ajoutez ensuite les périodes avec **Ajouter la première période**, puis **Ajouter une période**
pour les suivantes :

| Colonne | Ce qu'il faut saisir |
|---|---|
| **Période** | Date de début et date de fin, toutes deux incluses |
| **Taux %** | Le taux annuel en pourcentage : `5.00` signifie 5 % par an |
| **Fréquence** | La fréquence à laquelle les intérêts arrivent à échéance : Quotidienne, Hebdomadaire, Mensuelle, Trimestrielle, Semestrielle ou Annuelle |
| **Générer le coupon** | Cochez cette case pour verser les intérêts courus à chaque date d'échéance |

Les périodes doivent se suivre, sans lacunes ni chevauchements. **Scinder** coupe une période en
deux ; sélectionnez des périodes voisines et cliquez sur **Fusionner** pour les réunir.

### ⚡ Intérêts de retard {: #late-interest }

Pour un prêt remboursé en retard, activez **⚡ Intérêts de retard** sous les périodes : l'actif
continue de croître après la fin de la dernière période. Une ligne de retard apparaît avec son
propre **Taux %**, sa **Fréquence** et son **Générer le coupon**. Cliquez sur sa période pour
définir les jours de grâce, et choisissez **Simple** ou **Composé** (par défaut) à côté de
l'interrupteur.

- Pendant les jours de grâce, les intérêts continuent de courir au taux de la dernière période.
- Passé ce délai, le taux de retard s'applique.

### 📅 Événements de l'actif

Ajoutez des événements ponctuels avec **Ajouter un événement** : une **Date**, un **Type**, une
**Valeur** et des **Notes** facultatives. Chaque événement est pris en compte à partir de sa date.

| Type | Effet sur la valeur |
|---|---|
| **Intérêt** | Un versement d'intérêts que vous avez reçu : la valeur diminue de ce montant |
| **Ajustement de prix** | Une dépréciation (négative) ou une revalorisation (positive) |

## 🧮 Comment la valeur est calculée {: #how-value-is-calculated }

LibreFolio parcourt le calendrier jour par jour. Au jour $d$, la valeur est

$$
V(d) = V_0 + I(d) - \sum \text{Événements d'intérêt} + \sum \text{Ajustements de prix}
$$

où $V_0$ est la **Valeur initiale**, $I(d)$ les intérêts courus jusqu'ici, et les sommes couvrent
les événements jusqu'au jour $d$. Chaque jour ajoute des intérêts au taux annuel de la période $r$
sur $\Delta t$, soit la part d'un jour dans l'année selon le **Décompte des jours** (par exemple
$1/365$ avec ACT/365) :

- **Simple** — les intérêts portent uniquement sur la valeur initiale : $\Delta I = V_0 \, r \, \Delta t$
- **Composé** — les intérêts portent aussi sur les intérêts déjà courus : $\Delta I = (V_0 + I) \, r \, \Delta t$

Avec **Générer le coupon**, à chaque date d'échéance, le gain $V(d) - V_0$, lorsqu'il est positif,
est versé sous forme d'événement d'intérêt : la valeur repart de $V_0$, et $I$ ainsi que les sommes
repartent de zéro.

- **Avant la première période**, la valeur est la Valeur initiale.
- **Après la dernière période**, elle reste à son montant final, sauf si les intérêts de retard sont
  activés. Avec **Générer le coupon** sur la dernière période et sans intérêts de retard, un
  événement de règlement à l'échéance clôture l'actif à ce montant.
- **Le graphique** reçoit un point à chaque date de **Fréquence** : choisissez **Quotidienne** pour
  une courbe lissée.

??? example "🧮 Un prêt de 10 000 € à 5 %, avec un coupon chaque mois"

    Intérêts simples, ACT/365, une période commençant le 1er janvier, **Fréquence** Mensuelle,
    **Générer le coupon** cochée. La première date d'échéance est le 1er février, 31 jours plus tard :
    le prêt a rapporté environ 42,47 € ($10\,000 \times 0.05 \times 31/365$). Ce montant est versé
    sous forme d'événement d'intérêt, et la valeur revient à 10 000 € pour croître à nouveau en
    février.

## 🔗 Voir aussi

- 📅 **[Événements de l'actif](../detail/events.md)** — Comment les événements apparaissent sur le graphique de l'actif
- 🛠️ **Pour les développeurs : [Fournisseur d'investissement programmé](../../../developer/backend/assets/provider_scheduled_investment.md)** — Moteur, événements et mise en cache
