# 📐 Mesures

Le panneau Mesures fournit un **outil de mesure point à point** pour analyser les mouvements de taux entre deux points quelconques du graphique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Panneau Mesures FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Comment l'utiliser

1. Cliquez sur le bouton bascule **Mesures** (📏) dans la barre d'outils du graphique
2. Le panneau des mesures s'ouvre sous le graphique
3. **Cliquez** sur un point de départ sur le graphique — cela définit la date et le taux de départ
4. **Cliquez** sur un point d'arrivée — cela définit la date et le taux d'arrivée
5. Le panneau affiche immédiatement les métriques calculées entre les deux points

---

## 📊 Métriques calculées

Pour chaque mesure, le panneau affiche :

| Métrique | Description | Exemple |
|----------|-------------|---------|
| **Plage de dates** | Dates De → À | 15 janv. 2024 → 20 mars 2024 |
| **Jours** | Jours calendaires entre les deux points | 65 jours |
| **Delta (Δ)** | Variation absolue du taux | +0,0342 |
| **Pourcentage (%)** | Variation en pourcentage | +3,12% |
| **Rendement annualisé** | Rendement annuel projeté basé sur la période mesurée | +17,8% p.a. |

!!! info "📚 Rendement annualisé"
    Le rendement annualisé utilise la formule du **Taux de croissance annuel composé (CAGR)**. Pour une explication complète incluant les rendements logarithmiques, la composition, et quand utiliser quelle méthode, consultez :

    :material-book-open-variant: **[Rendements & Taux de croissance — Théorie financière](../../../financial-theory/returns.md)**

---

## 🔁 Mesures multiples

Vous pouvez effectuer plusieurs mesures en séquence — chaque nouvelle paire de clics remplace la mesure précédente. Cela permet de comparer rapidement les mouvements sur différentes fenêtres temporelles.

---

## 💡 Conseils

- 🔍 **Zoomez** avant de mesurer pour une meilleure précision des points de clic
- 📰 Utilisez les mesures pour comparer les mouvements de taux **avant/après un événement** (par exemple, avant et après une annonce de banque centrale)
- ⚠️ Le rendement annualisé est le plus pertinent pour les périodes de **30 jours ou plus** — les périodes très courtes peuvent produire des chiffres annualisés trompeurs
