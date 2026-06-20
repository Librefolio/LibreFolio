# <img src="../../static/scheduled_investment.png" alt=""> Fournisseur d'Investissement à échéancier

Le fournisseur d'Investissement à échéancier (Scheduled Investment) est conçu pour les instruments à revenu fixe dont la valeur est calculée à partir d'un calendrier de taux d'intérêt plutôt que sur les prix du marché. Les exemples incluent les comptes d'épargne, les dépôts à terme et les obligations d'État avec des taux de coupon connus.

## 📊 Capacités

- ✅ **Prix actuel** : Calculé de manière déterministe à partir de la valeur initiale + calendrier d'intérêts + événements de l'actif
- ✅ **Historique** : Courbe de valeur historique complète basée sur l'accumulation des intérêts
- ✅ **Événements de l'actif** : Génère des événements INTEREST et PRICE_ADJUSTMENT
- ❌ **Recherche** : Non applicable

## 🔧 Configuration

- **Identifiant** : Auto-généré (aucun identifiant manuel requis)
- **Type d'identifiant** : `AUTO_GENERATED`
- **Paramètres** : Configurés via l'**Éditeur de calendrier d'intérêts** (composant UI personnalisé)

### Champs requis

| Champ | Description |
|-------|-------------|
| **Valeur Initiale** | Le principal / la valeur nominale de l'investissement (ex: 10000) |
| **Devise** | Code devise ISO 4217 (ex: EUR, USD) |

## 📋 Éditeur de calendrier d'intérêts

L'éditeur vous permet de définir plusieurs périodes de taux d'intérêt :

| Champ | Description |
|-------|-------------|
| **Période** | Date de début et de fin (les deux incluses) |
| **Taux %** | Taux d'intérêt annuel en pourcentage (ex: 5.00 = 5%) |
| **Capitalisation** | Intérêts simples ou composés |
| **Fréq. Cap.** | Fréquence de capitalisation (Annuelle, Semestrielle, Trimestrielle, Mensuelle, Quotidienne) |
| **Comptage des jours** | Convention de comptage des jours (ACT/365, ACT/360, 30/360, ACT/ACT) |

### ⚡ Intérêts de retard

Vous pouvez activer les **Intérêts de retard** pour définir un taux de pénalité appliqué après la fin de la dernière période programmée. Un **délai de grâce** configurable (en jours) détermine le moment où les intérêts de retard commencent à s'accumuler.

## 📋 Événements de l'actif

Les événements de l'actif décrivent des éléments qui affectent l'actif globalement (et non des transactions au niveau du portefeuille) :

| Type d'événement | Effet sur le prix | Description |
|-----------|----------------|-------------|
| **INTEREST** | Le prix baisse de la valeur de l'événement | Versement d'intérêts — l'utilisateur a reçu des liquidités, donc la valeur de l'actif diminue |
| **PRICE_ADJUSTMENT** | Changement algébrique | Dépréciation (négative) ou appréciation (positive) de la valeur de l'actif |

Les événements sont configurés dans l'éditeur et affectent le prix calculé à partir de leur date.

## 🧮 Comment la valeur est calculée

1. Partez de `initial_value` comme principal de base
2. Pour chaque période d'intérêt, calculez les intérêts courus en fonction du taux, du type de capitalisation et de la convention de comptage des jours
3. Appliquez les événements de l'actif : les événements INTEREST réduisent le prix, les événements PRICE_ADJUSTMENT le modifient algébriquement
4. La valeur actuelle = `initial_value` + intérêts courus - Σ(événements INTEREST) + Σ(événements PRICE_ADJUSTMENT)

!!! note "Moteur Purement Déterministe"

    Le fournisseur est complètement déterministe — pour une configuration identique, il produit toujours les mêmes prix. Il n'accède PAS à la base de données et ne lit pas les transactions. Toutes les entrées proviennent de `provider_params`.

## 🎯 Cas d'utilisation

- **Comptes d'épargne** avec taux d'intérêt fixes ou variables
- **Dépôts à terme** (CD/Depositi vincolati)
- **Obligations d'État** où vous souhaitez suivre les intérêts courus plutôt que le prix du marché
- **Prêts de crowdfunding** (prêts P2P) avec calendriers d'intérêts connus
- **Tout instrument** disposant d'un calendrier de taux d'intérêt connu
