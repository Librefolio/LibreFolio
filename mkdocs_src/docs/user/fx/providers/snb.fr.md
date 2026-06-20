# <img src="https://data.snb.ch/favicon.ico" alt=""> Banque Nationale Suisse (BNS)

Le fournisseur **Banque Nationale Suisse (BNS)** publie quotidiennement les taux de change pour le franc suisse (CHF). Ce fournisseur est extrêmement stable et précis, ce qui en fait une source précieuse pour les actifs basés en CHF.

## 📊 Fonctionnalités

- ✅ **Prix actuel** : Taux de référence mis à jour quotidiennement
- ✅ **Historique** : Taux quotidiens historiques
- ❌ **Recherche** : Pas de recherche d'actifs (taux FX uniquement)

## 🔧 Spécifications

- **Devise de base** : CHF 🇨🇭
- **Fréquence de mise à jour** : Quotidienne les jours ouvrables suisses
- **Clé API** : Non requise (API publique du portail de données de la BNS)

## 💰 Devises prises en charge

La BNS fournit des taux de change pour une liste sélectionnée de devises majeures :

- **Devises prises en charge** : USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, AUD 🇦🇺, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳

## 📝 Notes importantes

- **Cotation de devises multi-unités** : La BNS cote certaines devises par tranches de **100 unités** (par ex. le yen japonais, la couronne suédoise, la couronne norvégienne, la couronne danoise) au lieu d'une seule unité. Par exemple, le taux est affiché comme `100 JPY = 0.58 CHF`. **LibreFolio détecte et normalise automatiquement ces taux** en valeurs par unité pour garantir que vos transactions soient calculées correctement.
- **Jours fériés** : Les taux ne sont pas publiés les jours fériés bancaires suisses ni les week-ends.
