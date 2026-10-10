# 🔄 Synchronisation FX

Les paires associées à un fournisseur obtiennent leurs taux auprès de sources officielles de banques centrales. LibreFolio les télécharge
lorsque vous ajoutez une paire, chaque fois que vous le demandez et — si votre administrateur l'a activé — selon un
calendrier.

---

## 🔄 Synchroniser toutes les paires

1. Sur la [page FX](index.md), choisissez la période dans le sélecteur de date. Sélectionnez **Tout** pour tout
   l'historique.
2. Cliquez sur **Tout synchroniser**. La fenêtre **Synchroniser les taux FX** liste chaque paire avec un fournisseur : les paires qui n'ont que des taux manuels n'ont rien à télécharger.
3. Cliquez sur **Lancer la synchronisation**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="sync-progress" alt="Progression de la synchronisation" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📊 Lire les résultats

- Chaque ligne affiche une paire, le fournisseur qui a répondu, **↓** les taux téléchargés et **Δ** les taux
  qui sont nouveaux ou modifiés.
- Une ligne ambrée signifie que le fournisseur n'a envoyé aucun taux pour la période ; une ligne rouge signifie que la synchronisation a échoué.
  Survolez le message pour le lire en entier, et cliquez sur le bouton ↻ de la ligne pour réessayer cette paire.
- Le résumé en bas indique combien de paires ont été synchronisées et les totaux. **Réessayer les N échecs** relance
  chaque paire en échec.
- Un historique long peut nécessiter plus de temps : si la fenêtre indique *La requête a expiré*, augmentez son
  **Délai d'attente**, puis cliquez sur **Réessayer les N échecs**.

---

## 🎯 Synchroniser une paire

- Sur la page FX, le bouton **Synchroniser** de la carte d'une paire, ou d'une ligne de tableau, télécharge les taux de cette paire
  pour la période sélectionnée. Un message indique le résultat.
- Sur la [page de détail](detail/index.md) de la paire, **Synchroniser** ouvre la fenêtre de synchronisation pour la paire et pour
  toute paire ou actif avec lequel vous la comparez sur le graphique.

**Synchroniser** est grisé pour les paires qui n'ont que des taux manuels.

---

## ⚠️ Ce qu'une synchronisation modifie

- Les dates de la période déjà enregistrées prennent la valeur du fournisseur ; les dates manquantes sont ajoutées.
- Les dates en dehors de la période restent inchangées.
- Si la première route d'une paire échoue, LibreFolio essaie la suivante : voir
  [Configuration du fournisseur](detail/provider.md).

!!! warning "Le fournisseur a le dernier mot"

    Une synchronisation écrase les taux que vous avez modifiés à la main sur sa période. Pour conserver vos propres taux, utilisez une
    paire sans fournisseur (taux manuels uniquement).

??? tip "🕰️ Historique plus ancien manquant — quand le graphique d'une paire commence plus tard que prévu"

    Une paire que vous ajoutez avec un fournisseur télécharge automatiquement tout son historique. Si le graphique d'une paire plus ancienne
    commence plus tard que l'historique du fournisseur, réglez la période sur la page FX sur **Tout** et cliquez sur
    **Tout synchroniser** une fois : LibreFolio télécharge tout ce que les fournisseurs publient, jusqu'à aujourd'hui.

---

## 🕐 Synchronisation automatique

Lorsque votre administrateur active le planificateur en arrière-plan, LibreFolio actualise de lui-même les taux récents de
chaque paire avec un fournisseur, aux heures que celui-ci choisit : voir
[Planificateur de données de marché](../../admin/settings.md#market-data-scheduler).

---

## 🔗 Liens associés

- ➕ **[Ajouter une paire](add-pair.md)** — Routes directes et en chaîne
- 🔌 **[Fournisseurs FX](providers/index.md)** — Les banques centrales auprès desquelles LibreFolio lit les taux
- ⚙️ **[Configuration du fournisseur](detail/provider.md)** — Routes, priorités et fallbacks d'une paire
- 🧑‍💻 Pour les développeurs : **[Configuration et routage FX](../../developer/backend/fx/configuration.md)**
