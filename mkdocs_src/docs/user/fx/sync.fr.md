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

1. Récupère les taux à partir de l'API du fournisseur configuré (BCE, Fed, BOE, BNS, etc.)
2. **Écrase** les points de données existants dans la plage de dates téléchargée avec les valeurs du fournisseur — le fournisseur est considéré comme la source faisant autorité
3. Ajoute de nouveaux points pour les dates non encore présentes dans la base de données
4. Si le fournisseur principal échoue, le système bascule automatiquement vers le fournisseur suivant

Après la synchronisation, vous verrez le nombre de **points téléchargés** et combien étaient **réellement nouveaux** (non déjà présents dans la base de données).

!!! warning "Le fournisseur fait autorité"
    Resynchroniser une paire écrasera toute valeur modifiée manuellement dans la plage synchronisée. Pour préserver les modifications manuelles, configurez la paire avec le fournisseur MANUAL (pas de source de données automatique).

!!! info "Précision des conversions en chaîne"
    Lors de l'utilisation de routes en chaîne (ex. RON → EUR → JPY), chaque conversion intermédiaire introduit une erreur d'arrondi minimale. Bien que négligeable dans la plupart des cas, les taux convertis en chaîne peuvent légèrement différer des cotations directes du marché.

---

## 🌐 Chaînes d'approvisionnement des données

Pour les utilisateurs avancés : LibreFolio utilise un **système de routage** sophistiqué pour les données de change. Chaque paire de devises peut avoir plusieurs fournisseurs configurés avec des priorités et des chaînes de secours.

Cela signifie :

- 🔄 Si votre fournisseur principal (ex. BCE) est indisponible, le système bascule vers le fournisseur suivant (ex. Fed)
- 🔀 Les paires exotiques utilisent des chaînes multi-étapes via des devises intermédiaires (ex. RON → EUR → JPY)
- ⚙️ Vous pouvez personnaliser le fournisseur à utiliser pour chaque paire

Pour la liste des fournisseurs pris en charge, consultez la [Liste des fournisseurs de taux de change](../../developer/backend/fx/providers_list.md).

Pour les détails techniques sur l'algorithme de routage et la configuration, consultez la documentation développeur : [Configuration et routage des taux de change](../../developer/backend/fx/configuration.md).
