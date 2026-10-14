# 🔌 Fournisseurs FX

LibreFolio télécharge les taux de change auprès des banques centrales — gratuitement et sans clé API. Une paire de devises peut avoir plusieurs sources classées par ordre de priorité : si la première échoue lors d'une synchronisation, la suivante prend le relais.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon ECB">
            <span class="card-title" style="margin: 0;">Banque centrale européenne (ECB)</span>
        </div>
        <span class="card-desc">Taux de change de référence quotidiens de l'ECB, devise de base EUR.</span>
    </a>
    <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon FED">
            <span class="card-title" style="margin: 0;">Réserve fédérale (FED)</span>
        </div>
        <span class="card-desc">Taux de change de la base de données FRED, devise de base USD.</span>
    </a>
    <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon BOE">
            <span class="card-title" style="margin: 0;">Banque d'Angleterre (BOE)</span>
        </div>
        <span class="card-desc">Taux de référence quotidiens de la BOE, devise de base GBP.</span>
    </a>
    <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon SNB">
            <span class="card-title" style="margin: 0;">Banque nationale suisse (SNB)</span>
        </div>
        <span class="card-desc">Taux moyens mensuels stables du franc suisse fournis par la SNB, devise de base CHF.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Demander un nouveau plugin</span>
     </div>
     <span class="card-desc">Votre source de taux de change est absente ? Demandez un nouveau plugin ou contribuez au code !</span>
    </a>
    </div>

## 📊 Comparaison des fournisseurs

Chaque banque centrale cote les autres devises par rapport à la sienne, la **devise de base**.

| <span style="min-width: 320px;">Fournisseur</span> | Devise de base | <span style="min-width: 220px;">Fréquence de mise à jour</span> | Idéal pour |
|:---|:---:|:---|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **ECB** (Banque centrale européenne) | EUR 🇪🇺 | Quotidien, vers 16 h 00 CET les jours ouvrables de l'ECB | Les paires en euros et les principales devises mondiales |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Réserve fédérale FRED) | USD 🇺🇸 | Quotidien, les jours ouvrables aux États-Unis | Les paires en dollars américains |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Banque d'Angleterre) | GBP 🇬🇧 | Quotidien, les jours ouvrables au Royaume-Uni | Les paires en livres sterling |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Banque nationale suisse) | CHF 🇨🇭 | Moyennes mensuelles, une valeur par mois | Les paires en francs suisses, quand un taux mensuel suffit |

## 🎯 Fonctionnement du routage et du fallback

1. 🛤️ **Route directe** : une banque centrale cote la paire — par ex. EUR/USD auprès de l'ECB.
2. 🔀 **Route en chaîne** : aucune banque ne cote la paire, donc LibreFolio combine des étapes — par ex. RON/USD en RON → EUR → USD, les deux étapes provenant de l'ECB. Une chaîne n'obtient un taux que les jours où chaque étape en a un.
3. 🔄 **Fallback** : avec plusieurs routes, une synchronisation les essaie par ordre de priorité et utilise la première qui fonctionne.
4. ✍️ **Manuel** : aucune route pour votre paire ? Enregistrez-la sans fournisseur et saisissez les taux vous-même dans l'[éditeur de données](../detail/data-editor.md).

Vous choisissez les routes lorsque vous [ajoutez une paire](../add-pair.md), et les modifiez par la suite avec le bouton [Fournisseurs](../detail/provider.md) de la paire.

!!! warning "SNB : un taux par mois"

    La SNB publie des moyennes mensuelles, datées du 1er de chaque mois. Une paire qui l'utilise obtient un taux par mois, et une chaîne passant par la SNB n'a des taux que ces jours-là.

## 🔗 Voir aussi

- 🛠️ **Pour les développeurs : [Fournisseurs FX](../../../developer/backend/fx/providers/index.md)** — API, séries et formats de cotation
