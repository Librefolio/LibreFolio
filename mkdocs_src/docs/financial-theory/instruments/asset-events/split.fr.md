# ✂️ Division d'actions (Split)

Une **division d'actions** (ou regroupement d'actions / reverse split) est une opération sur titres qui modifie le nombre d'actions en circulation tout en maintenant la capitalisation boursière totale constante.

---

## 📖 Définition

Lors d'une division d'actions, une société divise ses actions existantes en plusieurs nouvelles actions. La **valeur totale** de la position d'un investisseur reste la même — seuls le nombre d'actions et le prix par action changent.

### Division (Forward Split)

L'entreprise augmente le nombre d'actions. Chaque action existante devient plusieurs actions à un prix proportionnellement plus bas.

| Ratio | Signification |
|-------|---------|
| **2:1** | Chaque action devient 2 actions à moitié prix |
| **3:1** | Chaque action devient 3 actions au tiers du prix |
| **4:1** | Chaque action devient 4 actions au quart du prix |
| **10:1** | Chaque action devient 10 actions au dixième du prix |

### Regroupement (Reverse Split)

L'entreprise réduit le nombre d'actions. Plusieurs actions existantes fusionnent en un nombre réduit d'actions à un prix proportionnellement plus élevé.

| Ratio | Signification |
|-------|---------|
| **1:2** | 2 actions deviennent 1 action au double du prix |
| **1:10** | 10 actions deviennent 1 action à 10× le prix |
| **1:20** | 20 actions deviennent 1 action à 20× le prix |

---

## 📉 Impact sur le prix du marché

Une division entraîne un **changement de prix immédiat et proportionnel** qui est mathématiquement neutre :

$$
P_{\text{after}} = \frac{P_{\text{before}}}{\text{split ratio}}
$$

$$
Q_{\text{after}} = Q_{\text{before}} \times \text{split ratio}
$$

Où $P$ est le prix par action et $Q$ la quantité d'actions.

!!! example "Exemple : Division Apple 4:1 (août 2020)"

    - **Avant division** : 100 actions × 500 $ = 50 000 $ de valeur totale
    - **Après division** : 400 actions × 125 $ = 50 000 $ de valeur totale
    - **Changement de prix** : −75 % (mais valeur de la position inchangée)

!!! example "Exemple : Regroupement 1:10"

    - **Avant** : 1 000 actions × 0,50 $ = 500 $ de valeur totale
    - **Après** : 100 actions × 5,00 $ = 500 $ de valeur totale
    - **Raison** : L'entreprise souhaite relever le prix de l'action au-dessus des exigences minimales de cotation de la place boursière

---

## 📊 Pourquoi les entreprises procèdent-elles à des divisions

### Divisions (Forward splits)

- **Accessibilité** : Un prix d'action plus bas rend le titre plus accessible aux investisseurs particuliers
- **Liquidité** : Un plus grand nombre d'actions en circulation peut augmenter le volume d'échanges
- **Psychologie** : Un prix nominal plus bas peut attirer davantage d'acheteurs
- **Options** : Un prix d'action plus bas réduit le capital nécessaire pour les contrats d'options (100 actions par contrat)

### Regroupements (Reverse splits)

- **Conformité de cotation** : Les bourses exigent des prix d'action minimums (ex : 1,00 $ sur le NASDAQ)
- **Perception institutionnelle** : Certains fonds ont des exigences de prix minimums
- **Souvent un signal d'alarme** : Les regroupements sont fréquemment associés à des entreprises en difficulté

---

## 📈 Ajustement du prix historique

Lors de l'analyse des prix historiques à travers les divisions, les fournisseurs de données fournissent généralement des **prix ajustés** — tous les prix historiques sont divisés par le ratio de division cumulé afin que le graphique affiche une ligne lisse.

Par exemple, si Apple valait 100 $ avant une division 4:1, le prix historique ajusté devient 25 $ pour correspondre à l'échelle après division.

---

## 🧮 Comment LibreFolio gère les divisions

Dans LibreFolio, un événement `SPLIT` est enregistré avec :

- **Date** : La date d'entrée en vigueur de la division
- **Montant** : Le ratio de division (ex : `2` pour une division 2:1, `0.1` pour un regroupement 1:10)
- **Notes** : Description facultative (ex : "division 4:1")

Les événements de division apparaissent comme des **marqueurs sur le graphique** et aident à expliquer les discontinuités soudaines de prix. Lors de l'utilisation de **prix ajustés** provenant de fournisseurs comme Yahoo Finance, la division est déjà prise en compte dans les données de prix.

---

## 🔗 Liens connexes

- 📅 **[Aperçu des événements liés aux actifs](index.md)** — Tous les types d'événements
- 💸 **[Types de transactions](../transaction-types/index.md)** — Comment les divisions affectent les transactions du portefeuille
- 📚 **[Types d'actifs](../asset-types/index.md)** — Types d'actifs pouvant faire l'objet d'une division
