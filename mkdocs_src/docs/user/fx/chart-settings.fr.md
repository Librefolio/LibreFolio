# ⚙️ Paramètres du graphique

La fenêtre **Paramètres du graphique** modifie l'apparence des graphiques et les superpositions qu'ils dessinent. Elle sert à la fois à la [liste FX](index.md) et à la [liste des actifs](../assets/index.md), et chaque liste conserve ses propres paramètres : modifier les graphiques FX n'affecte jamais les graphiques des actifs.

---

## 🔓 Ouvrir les paramètres du graphique

- 🌐 **Pour tous les graphiques** — cliquez sur **Paramètres** (⚙️) dans la barre d'outils de la liste. La fenêtre s'intitule
  **Paramètres du graphique**. Son application remplace les paramètres personnalisés de chaque graphique de la liste, pages
  de détail incluses, et la fenêtre vous en avertit.
- 🎯 **Pour un seul graphique** — cliquez sur le ⚙️ d'une carte. La fenêtre s'intitule **Paramètres du graphique (locaux)**, et
  ses paramètres ne s'appliquent qu'à ce graphique.

!!! note "Les pages de détail utilisent des panneaux intégrés"

    Sur une [page de détail d'une paire](detail/index.md) (et sur une page de détail d'un actif), ⚙️ sur le graphique ouvre
    les mêmes paramètres d'apparence dans un panneau, et le panneau **Signaux** au-dessus du graphique contient les
    superpositions. Ce sont les paramètres locaux de la carte.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Fenêtre modale des paramètres du graphique" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Aperçu avant d'appliquer

La fenêtre affiche un graphique d'aperçu avec son propre interrupteur **Abs** / **%**. Vos graphiques ne changent que lorsque
vous cliquez sur **Appliquer** ; **Annuler** demande confirmation avant d'abandonner vos modifications.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Fenêtre modale des paramètres du graphique avec l'aperçu en direct">
</div>

- 🌐 **Pour tous les graphiques**, l'aperçu dessine une courbe de démonstration. Le serveur calcule les indicateurs sur celle-ci,
  afin qu'ils s'affichent exactement comme ils apparaîtront sur vos graphiques réels.
- 🎯 **Pour un seul graphique**, l'aperçu utilise les données réelles de ce graphique. Les indicateurs affichent les derniers
  paramètres appliqués jusqu'à ce que vous cliquiez sur **Appliquer**, et une bannière vous le rappelle.

---

## 🎨 Apparence

| Paramètre | Ce qu'il fait |
|---------|--------------|
| **Couleurs de la ligne de base** | Vert au-dessus, rouge en dessous du début de la période |
| **Remplissage de la zone** | Dégradé sous la ligne |
| **Lignes de grille** | Grille horizontale en pointillés |
| **Dégradé obsolète** | Estompe les jours sans nouvelle valeur, qui répètent une valeur antérieure |

### 📏 Plages d'axes

**Échelle de l'axe Y** a une ligne pour chaque axe du graphique : l'axe principal (le taux, ou le pourcentage
en vue %) et une pour chaque échelle d'indicateur, telle que l'**axe RSI**. Les indicateurs qui partagent une
échelle partagent une ligne.

- **Auto** adapte les données sur cet axe.
- **Inclure 0** adapte les données et affiche également zéro.
- **Personnalisé** utilise les **Min** et **Max** que vous saisissez.

Les vues **Abs** et **%** conservent des plages distinctes : basculez l'aperçu sur **%** pour définir
celle du pourcentage.

---

## 📈 Signaux de superposition

Ajoutez des superpositions à partir de trois menus déroulants, comme dans le [panneau Signaux](detail/signals.md) de la page de détail :

- 🧮 **Indicateurs techniques** — 9 indicateurs fonctionnent sur les taux FX (les graphiques d'actifs en proposent davantage), regroupés par
  famille avec une zone de recherche. Les mathématiques se trouvent dans
  [Indicateurs techniques — Théorie financière](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Comparaison de données** — une autre paire FX ou un actif sur le même graphique.
- 📐 **Benchmarks synthétiques** — benchmarks synthétiques construits à partir de paramètres seuls, et non de données de marché :
  [Linéaire](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
  [Composé](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) et
  [Onde sinusoïdale](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

Chaque signal devient une carte avec ses paramètres, un lien 📖 vers sa page théorique et, une fois calculé, une
icône de diagnostics.

---

## 💾 Où les paramètres sont enregistrés

- Les paramètres du graphique sont enregistrés dans **ce navigateur**, pour votre utilisateur, séparément pour les listes FX et d'actifs. Les paramètres propres à un graphique se superposent à ceux de sa liste.
- Ils ne sont pas stockés sur le serveur : un autre navigateur ou appareil démarre avec les valeurs par défaut, et
  l'effacement des données de navigation de ce site les réinitialise.
- La période sélectionnée n'est pas un paramètre de graphique : les pages du même onglet de navigateur la partagent.
