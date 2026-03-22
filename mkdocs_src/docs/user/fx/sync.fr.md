# 🔄 Synchronisation FX

Une fois qu'une paire de devises est configurée avec un fournisseur de données, LibreFolio peut **synchroniser automatiquement** les taux de change à partir des sources officielles des banques centrales.

---

## 🔄 Tout synchroniser

Depuis la page de la liste des taux de change, utilisez le bouton **Tout synchroniser** pour synchroniser toutes les paires configurées en une seule fois :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Sync Progress" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La fenêtre de synchronisation affiche :

- 📊 **Progression** pour chaque paire en cours de synchronisation
- ✅ **Indicateurs de statut** (succès, erreur, ignoré)
- 🆕 **Nombre de nouveaux points de données** pour chaque paire

---

## 🎯 Synchronisation d'une paire individuelle

Vous pouvez également synchroniser une seule paire depuis sa [page de détail](detail/index.md) à l'aide du bouton de synchronisation. Cela est utile lorsque vous souhaitez mettre à jour uniquement une paire spécifique.

---

## ⚙️ Fonctionnement de la synchronisation

Le processus de synchronisation :

1. Récupère les taux à partir de l'API du fournisseur sélectionné (BCE, Fed, Banque d'Angleterre, BNS, etc.)
2. Stocke les nouveaux points de données dans la base de données locale
3. Ignore les dates qui existent déjà (pas de doublons)
4. Si le fournisseur principal échoue, le système bascule automatiquement vers le fournisseur configuré suivant

!!! tip "Pas de données en double"
 Resynchroniser une paire est toujours sans risque — les données existantes ne sont jamais écrasées ni dupliquées.

---

## 🌐 Chaînes d'approvisionnement des données

Pour les utilisateurs avancés : LibreFolio utilise un **système de routage** sophistiqué pour les données de change. Chaque paire de devises peut avoir plusieurs fournisseurs configurés avec des priorités et des chaînes de secours.

Cela signifie :

- 🔄 Si votre fournisseur principal (ex. BCE) est indisponible, le système bascule vers le fournisseur suivant (ex. Fed)
- 🔀 Les paires exotiques utilisent des chaînes multi-étapes via des devises intermédiaires (ex. RON → EUR → JPY)
- ⚙️ Vous pouvez personnaliser le fournisseur à utiliser pour chaque paire

Pour la liste des fournisseurs pris en charge, consultez la [Liste des fournisseurs de taux de change](../../developer/backend/fx/providers_list.md).

Pour les détails techniques sur l'algorithme de routage et la configuration, consultez la documentation développeur : [Configuration et routage des taux de change](../../developer/backend/fx/configuration.md).

 **FX** (Foreign Exchange) : Acronyme anglais désignant le marché des changes ou les opérations de devises. Utilisé couramment dans le contexte financier international, même en français.

 **Paires exotiques** : En forex, paires de devises qui ne font pas partie des "majors" (USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD). Elles impliquent généralement une devise majeure et une devise mineure, ou deux devises mineures, et sont moins liquides.

 **Point de données** : Ici, une valeur de taux de change enregistrée pour une date spécifique (une cotation). Chaque point de données constitue une entrée dans la série temporelle.

 **Acronymes des banques centrales** : 
 - **Fed** : Réserve fédérale américaine, banque centrale des États-Unis. Le sigle "Fed" est couramment utilisé en français.
 - **BNS** : Banque nationale suisse, banque centrale de la Suisse. Le sigle "BNS" est l'acronyme officiel en français, mais moins répandu que "SNB" dans la documentation technique internationale.
