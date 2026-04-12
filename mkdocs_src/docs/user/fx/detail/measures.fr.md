# 📐 Mesures

Le panneau de Mesures fournit un **outil de mesure par clic** pour analyser les mouvements de taux entre deux points quelconques sur le graphique.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Panneau de mesures FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Mode d'emploi

1. Cliquez sur l'interrupteur **Measures** (📏) dans la barre d'outils du graphique
2. Le panneau de mesures s'ouvre sous le graphique
3. **Cliquez** sur un point de départ sur le graphique — cela définit la date et le taux de début
4. **Cliquez** sur un point d'arrivée — cela définit la date et le taux de fin
5. Le panneau affiche immédiatement les indicateurs calculés entre les deux points

---

## 📊 Indicateurs calculés

Pour chaque mesure, le panneau affiche :

| Indicateur | Description | Exemple |
|--------|-------------|---------|
| **Plage de dates** | Dates De → À | 15 janv. 2024 → 20 mars 2024 |
| **Jours** | Jours calendaires entre les deux points | 65 jours |
| **Delta (Δ)** | Variation absolue du taux | +0,0342 |
| **Pourcentage (%)** | Variation relative en pourcentage | +3,12% |
| **Rendement annualisé** | Rendement annuel projeté basé sur la période mesurée | +17,8% p.a. |

!!! info "📚 Rendement annualisé"

    Le rendement annualisé utilise la formule du **Taux de Croissance Annuel Composé (CAGR)**. Pour une explication complète incluant les rendements logarithmiques, la capitalisation et le choix de la méthode à utiliser, consultez :

    :material-book-open-variant: **[Rendements et taux de croissance — Théorie financière](../../../financial-theory/fundamentals/returns.md)**

---

## 🔁 Mesures multiples

Vous pouvez effectuer plusieurs mesures à la suite — chaque nouvelle paire de clics remplace la mesure précédente. Cela vous permet de comparer rapidement les mouvements sur différentes fenêtres temporelles.

---

## 💡 Conseils

- 🔍 **Zoomez** avant de mesurer pour une meilleure précision sur les points de clic
- 📰 Utilisez les mesures pour comparer les mouvements de taux **avant/après un événement** (par exemple, avant et après une annonce d'une banque centrale)
- ⚠️ Le rendement annualisé est plus significatif pour des périodes de **30 jours et plus** — des périodes très courtes peuvent produire des chiffres annualisés trompeurs
