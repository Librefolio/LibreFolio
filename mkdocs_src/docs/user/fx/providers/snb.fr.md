# <img src="https://data.snb.ch/favicon.ico" alt=""> Banque nationale suisse (SNB)

Le fournisseur **Banque nationale suisse (SNB)** publie des taux de change **moyens mensuels** pour le franc suisse (CHF), récupérés depuis le portail public de données de la SNB. C'est une source stable et faisant autorité pour les actifs libellés en CHF.

!!! warning "Données mensuelles uniquement — pas de taux quotidiens"

    La SNB ne propose **pas** de jeu de données de taux quotidiens : chaque valeur est la **moyenne d'un mois calendaire**, enregistrée au **1er de ce mois**. Dans les chaînes de conversion, un taux n'est calculé que pour les dates où **tous** les fournisseurs impliqués disposent de données ; le chaînage via la SNB donne donc un point par mois. Si vous avez besoin de taux CHF au jour le jour, utilisez un autre fournisseur (p. ex. ECB ou FED) pour la paire.

## 📊 Fonctionnalités

- ✅ **Prix actuel** : dernière moyenne mensuelle disponible
- ✅ **Historique** : moyennes mensuelles historiques
- ❌ **Recherche** : aucune recherche d'actifs (taux de change uniquement)

## 🔧 Spécifications

- **Devise de base** : CHF 🇨🇭
- **Fréquence de mise à jour** : mensuelle — les nouvelles moyennes sont publiées vers le 2e jour ouvrable du mois suivant
- **Clé API** : non requise (API publique du portail de données de la SNB)

## 💰 Devises prises en charge

La SNB couvre environ **25 devises** face au CHF ; LibreFolio charge dynamiquement la liste exacte depuis le portail de données de la SNB. La liste comprend :

- **Majeures** : USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CNY 🇨🇳
- **Mondiales** : CAD 🇨🇦, AUD 🇦🇺, et d'autres devises du monde

## 📝 Notes importantes

- **Cotation en multi-unités** : la SNB cote certaines devises par **100 unités** au lieu d'une unité (p. ex. `100 JPY = x CHF`). **LibreFolio détecte et normalise automatiquement ces taux** en valeurs par unité afin que vos transactions soient calculées correctement.
- **Un point par mois** : les taux sont datés du 1er de chaque mois. Les conversions aux dates situées entre deux points mensuels utilisent le taux disponible le plus récent (remplissage rétroactif).
