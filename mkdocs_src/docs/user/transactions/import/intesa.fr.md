# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Beta"

    Ce plugin est en **version bêta** — testé avec des exemples de fichiers, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

LibreFolio lit les exports Intesa Sanpaolo au format **CSV** *ou* **XLSX** — vous n'avez pas besoin de
convertir le fichier, importez-le simplement tel qu'il a été téléchargé. Deux rapports différents sont pris en charge et
couvrent deux situations distinctes :

- La **liste des mouvements** (*lista movimenti*) — les opérations du compte pour une période donnée.
- **L'instantané du portefeuille** (*patrimonio*) — les titres détenus actuellement avec leur
 base de coût fiscal et le solde de trésorerie.

Depuis votre banque en ligne Intesa Sanpaolo, téléchargez la liste des mouvements pour la période souhaitée
et, si vous avez également besoin d'initialiser les positions historiques, l'instantané du portefeuille de votre
*Compte Titres*.

## 🧭 Quels fichiers dois-je importer ?

=== "Compte tout neuf"

 Si le compte a été **ouvert récemment** et que chaque achat est inclus dans la période
 exportée, importer uniquement la **liste des mouvements** suffit — il n'y a pas d'historique
 antérieur à reconstituer.

=== "Compte avec historique (recommandé)"

 Intesa exporte uniquement environ **un an** de mouvements et **n'inclut pas**
 les transactions d'achat d'origine. Pour représenter les positions achetées plus tôt, importez d'abord
 l'**instantané du portefeuille** : il initialise le compte avec

 - un **dépôt de trésorerie** pour la liquidité déclarée (lorsque l'instantané contient un solde de trésorerie non nul), et
 - un **ajustement de la base de coût par position** (quantité issue de l'instantané, avec le
 coût fiscal stocké comme une **surcharge de la base de coût par unité**),

 tous datés à la date de l'instantané. Importez ensuite la **liste des mouvements** pour ajouter les
 coupons et frais récents.

## 📝 Remarques

- **Liste des mouvements** — l'analyseur associe les libellés d'opérations par mot-clé : *Cedole* → intérêts,
 *Dividend...* → dividende, *Commission...* → frais, et *Ritenut...* / *Imposta...* /
 *Bollo...* → taxe. Les opérations courantes de compte courant qui peuvent apparaître dans le même export
 (virements, paiements par carte, salaire, etc.) **ne sont pas reconnues comme des activités sur titres et sont ignorées**,
 avec un avertissement — l'import n'échoue jamais à cause d'elles.
- **Pas d'ISIN dans la liste des mouvements** — le titre est extrait du champ texte libre *Dettagli*,
 les actifs sont donc associés **par nom**. L'instantané du portefeuille, lui, *porte* l'ISIN.
 Comme les deux rapports identifient le même titre différemment (nom vs ISIN), LibreFolio
 ne les fusionnera pas automatiquement — confirmez l'actif à **l'Étape 4** de l'assistant.
- **Initialisation par instantané** — chaque ajustement stocke `cost_basis_override` comme le coût fiscal **par unité**. Intesa indique *Controvalore di carico fiscale €* comme une valeur totale de la position, donc LibreFolio la divise par la quantité détenue avant de la stocker. Le moteur multiplie ensuite la valeur par unité par la quantité pour reconstituer la base de coût totale. La date de l'instantané est la date de cours la plus récente du rapport.
- **Avis d'échéance** — si les lignes Intesa analysées contiennent des indications d'échéance/remboursement, la boîte de dialogue de création d'actif peut afficher un avis consultatif de couleur ambre avertissant que le titre peut être arrivé à échéance ou radié.
- **Les montants sont importés textuellement** en EUR, exactement comme ils apparaissent dans le rapport. Aucune
 conversion de devise n'est effectuée.

## ⛔ Avant la date d'ouverture du courtier

Lorsque votre courtier a une **date d'ouverture** définie, les mouvements datés **strictement avant** cette date sont signalés dans l'assistant comme **"Avant ouverture"** et ne peuvent pas être importés (leur case à cocher est désactivée). La date d'ouverture elle-même est valide : la vérification intégrée est `txDate < info.openedAt`, pas `<=`. Cela évite de dupliquer les positions déjà représentées par l'initialisation de l'instantané. Si une ligne est signalée de manière incorrecte, utilisez l'action intégrée **Modifier la date du courtier**, puis recochez/actualisez pour que l'assistant évalue la date du courtier mise à jour.

## 🔗 Référence pour les développeurs

→ [Fournisseurs BRIM — détails d'implémentation](../../../developer/backend/brim/providers_list.md)
