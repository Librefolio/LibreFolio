# 🔌 Fournisseurs FX

LibreFolio synchronise automatiquement les taux de change en utilisant les flux officiels des banques centrales. Chaque paire de devises que vous configurez peut disposer d'une liste prioritaire de sources, créant ainsi un système de fallback robuste si un service devient indisponible.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de la BCE">
 <span class="card-title" style="margin: 0;">Banque Centrale Européenne (BCE)</span>
 </div>
 <span class="card-desc">Taux de change de référence quotidiens de la BCE, devise de base EUR.</span>
 </a>
 <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de la FED">
 <span class="card-title" style="margin: 0;">Réserve Fédérale (FED)</span>
 </div>
 <span class="card-desc">Taux de change de la base de données FRED, devise de base USD.</span>
 </a>
 <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de la BOE">
 <span class="card-title" style="margin: 0;">Banque d'Angleterre (BOE)</span>
 </div>
 <span class="card-desc">Taux de référence quotidiens de la BOE, devise de base GBP.</span>
 </a>
 <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de la SNB">
 <span class="card-title" style="margin: 0;">Banque Nationale Suisse (SNB)</span>
 </div>
 <span class="card-desc">Taux quotidiens stables du franc suisse fournis par la SNB, devise de base CHF.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
  <div style="display: flex; align-items: center; gap: 0.75rem;">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
  <span class="card-title" style="margin: 0;">Demander un Nouveau Plugin</span>
  </div>
  <span class="card-desc">Votre fournisseur de taux de change manque ? Demandez un nouveau plugin ou contribuez !</span>
 </a>
 </div>

## 📊 Comparaison des fournisseurs

| <span style="min-width: 320px;">Fournisseur</span> | Devise de base | Devises supportées | <span style="min-width: 220px;">Fréquence de mise à jour</span> | Clé API | Notes |
|:---|:---:|:---:|:---:|:---:|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BCE** (Banque Centrale Européenne) | EUR 🇪🇺 | ~45 | Quotidienne, ~16:00 CET | Non requise | Fournisseur principal pour les paires basées sur l'Euro et les principales devises mondiales. |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Federal Reserve FRED) | USD 🇺🇸 | ~20 | Quotidienne, jours ouvrés US | Non requise | Meilleur fallback pour les paires basées sur le Dollar US. |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Bank of England) | GBP 🇬🇧 | ~15 | Quotidienne, jours ouvrés UK | Non requise | Bonne couverture pour les paires basées sur la Livre Sterling. |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Banque Nationale Suisse) | CHF 🇨🇭 | ~10 | Quotidienne, jours ouvrés suisses | Non requise | Cotations très stables pour les paires en Franc Suisse. |

## 🎯 Fonctionnement du routage et du fallback

LibreFolio ne vous limite pas à une source unique. Lors de la gestion des taux de change :

1. 🛤️ **Routes directes** : Si un taux direct existe (ex: EUR/USD via la BCE), LibreFolio le récupère.
2. 🔀 **Routes en chaîne** : Si aucun fournisseur direct ne supporte votre paire (ex: EUR/RON), LibreFolio peut la convertir automatiquement via une chaîne (ex: EUR → USD → RON).
3. 🔄 **Fallback automatique** : Si votre fournisseur principal échoue lors de la synchronisation (ex: délai d'attente réseau), LibreFolio tente automatiquement le fournisseur suivant configuré.
4. ✍️ **Saisie manuelle** : Pour les paires de devises qui ne sont supportées par aucune banque centrale, vous pouvez régler le fournisseur sur `MANUAL` pour saisir les taux vous-même.
