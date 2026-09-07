# ⚙️ Paramètres du graphique

La fenêtre modale **Paramètres du graphique** personnalise l'apparence des graphiques et les signaux de superposition. Cette même fenêtre modale est utilisée pour les pages [Liste FX](index.md) et [Actifs](../assets/index.md), avec des **paramètres indépendants par périmètre** — modifier les valeurs par défaut FX n'affecte jamais les graphiques d'actifs, et inversement.

---

## 🔓 Accéder aux paramètres du graphique

La fenêtre modale s'ouvre depuis les pages de liste, en deux variantes :

- 🌐 **Global** — le bouton de paramètres (⚙️) dans la barre d'outils de la page de liste. Ces paramètres deviennent la valeur par défaut pour chaque graphique du périmètre ; les appliquer remplace toutes les personnalisations par carte (la fenêtre modale vous en avertit).
- 🎯 **Local** — le bouton de paramètres (⚙️) sur n'importe quelle carte de paire ou d'actif. Ces paramètres remplacent les paramètres globaux uniquement pour cette carte.

!!! note "Les pages de détail utilisent des panneaux intégrés"

    Sur la [page de détail de la paire](detail/index.md) (et sur les pages de détail
    des actifs), le bouton ⚙️ active un **panneau d'apparence** intégré et le
    bouton 📈 active le **panneau de signaux** intégré — mêmes paramètres,
    même stockage par élément, pas de fenêtre modale.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Chart Settings Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Aperçu en direct

La fenêtre modale affiche toujours un **graphique d'aperçu** avec un interrupteur Abs/%, afin que vous voyiez l'effet de chaque modification avant de l'appliquer :

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Chart settings modal with the live preview">
</div>

- 🌐 **Mode global** — l'aperçu dessine une courbe de démonstration synthétique. Les indicateurs backend ne peuvent pas s'exécuter dans le navigateur ; la fenêtre modale demande donc au serveur de les calculer en direct sur cette courbe : ce que vous voyez correspond à ce que les graphiques réels afficheront.
- 🎯 **Mode local** — l'aperçu utilise les **données de prix réelles** de la carte. Les indicateurs backend affichent la dernière configuration appliquée ; une bannière vous rappelle de cliquer sur Appliquer pour les actualiser.

---

## 🎛️ Paramètres disponibles

### 🎨 Apparence

| Paramètre | Description |
|---------|-------------|
| **Couleurs de la ligne de base** | Colore la ligne en vert au-dessus / rouge en dessous de la ligne de base |
| **Remplissage de zone** | Remplissage en dégradé sous la ligne |
| **Lignes de grille** | Grille horizontale en pointillés |
| **Dégradé des données obsolètes** | Estompe les données anciennes vers l'arrière-plan |
| **Échelle de l'axe Y** | Auto, Inclure 0, ou une plage min/max personnalisée |

### 📈 Signaux de superposition

La fenêtre modale gère les mêmes signaux de superposition que le [panneau Signaux](detail/signals.md) de la page de détail, ajoutés à partir de trois menus déroulants de catégories :

- 🧮 **Indicateurs techniques** — le catalogue de plugins backend du périmètre actuel : **9 indicateurs compatibles FX** ici, 22 sur le périmètre Actifs. Le menu déroulant est une arborescence avec recherche, groupée par famille (tendance, momentum, volatilité, …). Les mathématiques derrière chaque indicateur sont décrites dans [Indicateurs techniques — Théorie financière](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Comparaison de données** — superposer une autre paire FX configurée ou un actif sur le même graphique.
- 📐 **Benchmarks synthétiques** — des courbes de référence générées par paramètres ([Linéaire](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Composé](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), [Onde sinusoïdale](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md)). Elles sont de pures mathématiques — ni paniers personnalisés, ni données de marché.

Chaque signal configuré devient une carte avec des paramètres intégrés, un lien 📖 vers sa page de théorie, et des diagnostics par signal une fois qu'il a été calculé.

---

## 💾 Persistance

Les paramètres des graphiques sont stockés localement dans le `localStorage` de votre navigateur, séparément pour les périmètres FX et Actifs, avec des personnalisations par carte qui priment sur les valeurs par défaut du périmètre. Ils persistent entre les sessions — même après avoir fermé et rouvert le navigateur — et ne seront perdus que si vous videz le cache/stockage de votre navigateur ou si le stockage expire (selon le navigateur, généralement de quelques mois à quelques années).
