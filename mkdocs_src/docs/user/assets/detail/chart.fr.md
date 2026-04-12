# 📈 Graphique Interactif

Le graphique de prix est l'élément central de la page de détail de l'actif, fournissant un historique visuel du prix de l'actif au fil du temps.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Graphique du prix de l'actif" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Barre de Filtres

La barre de filtres située au-dessus du graphique propose des commandes pour personnaliser la vue :

### 📅 Plage de Dates

Sélectionnez une fenêtre temporelle pour les données du graphique :

- **Préréglages** : 1W, 1M, 3M, 6M, 1Y, ALL
- **Personnalisé** : choisissez une date de début et de fin à l'aide du sélecteur de calendrier

### 💱 Sélecteur de Devise

Affichez les prix en :

- La **devise native** de l'actif (ex : USD pour Apple)
- La **devise de base de votre portefeuille** (ex : EUR) — convertie automatiquement via les taux de change

### 📊 Interrupteur Absolu / Pourcentage

- **Absolu** : affiche les valeurs de prix réelles
- **Pourcentage** (%) : affiche la variation en pourcentage depuis le premier point de données de la plage sélectionnée

### 📅 Marqueurs d'Événements

Les dividendes, divisions d'actions, paiements d'intérêts et autres [événements d'actifs](events.md) apparaissent sous forme de marqueurs colorés sur le graphique :

- 💰 **Dividende** — distribution de liquidités
- 💵 **Intérêt** — paiement d'intérêts
- 📊 **Split** — division d'actions
- 📝 **Ajustement de Prix** — dépréciation ou réévaluation
- 🏁 **Règlement à Échéance** — l'actif est arrivé à échéance

Survolez un marqueur pour voir les détails de l'événement (date, type, valeur).

---

## 🎨 Esthétique

Cliquez sur le bouton **Paramètres** (⚙️) pour utiliser l'interrupteur du panneau d'esthétique permettant la personnalisation du graphique (couleur de la ligne, style, etc.).

---

## 🔗 Liens Associés

- 📊 **[Signaux](signals.md)** — Superposer des indicateurs techniques
- 📐 **[Mesures](measures.md)** — Mesurer les différences de prix
- 📅 **[Événements](events.md)** — Comprendre les marqueurs d'événements
