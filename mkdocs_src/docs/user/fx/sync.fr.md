# 🔄 Synchronisation FX

Une fois qu'une paire de devises est configurée avec un fournisseur de données, LibreFolio peut **synchroniser automatiquement** les taux de change à partir de sources officielles de banques centrales.

---

## 🔄 Tout synchroniser

Depuis la page de liste FX, utilisez le bouton **Tout synchroniser** pour synchroniser toutes les paires configurées d'un seul coup :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progression de la synchronisation" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La fenêtre modale de synchronisation affiche :

- 📊 La **progression** pour chaque paire en cours de synchronisation
- ✅ Les indicateurs de **statut** (succès, erreur, ignoré)
- 🆕 Le nombre de **nouveaux points de données** pour chaque paire

---

## 🎯 Synchronisation d'une paire individuelle

Vous pouvez également synchroniser une seule paire depuis sa [page de détails](detail/index.md) en utilisant le bouton de synchronisation. Cela est utile si vous souhaitez mettre à jour uniquement une paire spécifique.

---

## ⚙️ Fonctionnement de la synchronisation

Le processus de synchronisation :

1. Récupère les taux via l'API du fournisseur configuré (ECB, FED, BOE, SNB, etc.)
2. **Écrase** les points de données existants dans la plage de dates téléchargée avec les valeurs du fournisseur — le fournisseur est considéré comme la source faisant autorité
3. Ajoute de nouveaux points de données pour les dates qui ne sont pas encore présentes dans la base de données
4. Si le fournisseur primaire échoue, le système effectue un fallback automatique vers le fournisseur suivant configuré

Après la synchronisation, vous verrez le nombre de **points téléchargés** et combien étaient **réellement nouveaux** (non présents précédemment dans la base de données).

!!! warning "Le fournisseur fait autorité"

    La resynchronisation d'une paire écrasera toutes les valeurs modifiées manuellement dans la plage de dates synchronisée. Si vous devez préserver des modifications manuelles, envisagez d'utiliser une paire configurée avec le fournisseur MANUAL (aucune source de données automatique).

!!! info "Précision de la conversion en chaîne"

    Lors de l'utilisation de routes en chaîne (ex: RON → EUR → JPY), chaque conversion intermédiaire introduit une erreur d'arrondi minimale. Bien que négligeable pour la plupart des usages, sachez que les taux convertis en chaîne peuvent différer légèrement des cotations directes du marché.

---

## 🌐 Chaînes de données

Pour les utilisateurs avancés : LibreFolio utilise un **système de routage** sophistiqué pour les données FX. Chaque paire de devises peut avoir plusieurs fournisseurs configurés avec des priorités et des chaînes de fallback.

Cela signifie que :

- 🔄 Si votre fournisseur primaire (ex: ECB) est indisponible, le système effectue un fallback vers le fournisseur suivant (ex: FED)
- 🔀 Les paires exotiques utilisent des chaînes multi-étapes via des devises intermédiaires (ex: RON → EUR → JPY)
- ⚙️ Vous pouvez personnaliser le fournisseur à utiliser pour chaque paire

Pour la liste des fournisseurs supportés, consultez les [Fournisseurs FX](providers/index.md).

Pour les détails techniques sur l'algorithme de routage et la configuration, consultez la documentation développeur : [Configuration & Routage FX](../../developer/backend/fx/configuration.md).
