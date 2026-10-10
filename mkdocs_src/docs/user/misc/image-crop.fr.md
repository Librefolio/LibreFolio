# ✂️ Outil de recadrage d'image

Cadrez, faites pivoter et redimensionnez une image avant que LibreFolio ne l'enregistre.

---

## 🎯 Quand apparaît-il ?

- 👤 **Photo de profil** — dans **[Profil](../settings/profile.md)** ou sur la page d'accueil : dans le
  sélecteur d'image, choisissez **Téléverser** et sélectionnez une image.
- 🏦 **Icône de courtier** et 📈 **icône d'actif** — le même sélecteur, depuis le formulaire de courtier ou d'actif.
- 📂 **Page Fichiers** — ajoutez des images à la liste de téléversement, puis cliquez sur le bouton ✏️ **Modifier** d'une image.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Modale de modification d'image" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ✂️ Cadrer l'image

- 📏 **Faites glisser** un coin ou un côté de la zone de recadrage pour la redimensionner, l'intérieur pour la déplacer, l'extérieur
  pour déplacer l'image. La zone de recadrage reste toujours à l'intérieur de l'image.
- 🔍 **Zoomez** avec la molette de la souris ou **+ / −** — la zone de recadrage se resserre (ou s'élargit) d'abord, puis
  l'image zoome — ou pincez sur un écran tactile.
- 🔄 **Faites pivoter** par pas de 15° avec **↺ / ↻**, et 🪞 **retournez** avec ↔ / ↕.
- 👁️ Le bouton œil à gauche bascule un **aperçu rond** : l'aspect de l'image dans un cercle, comme
  votre avatar dans la barre latérale.
- 🔁 **Tout réinitialiser** (en haut à droite) annule le recadrage, le zoom, la rotation et le retournement.

---

## 📐 Préréglages

| Préréglage | Taille de sortie | Forme |
|--------|------|-------------|
| **Avatar** | 200 × 200 px | Carré, aperçu rond activé |
| **Icône** | 64 × 64 px | Carré, aperçu rond activé |
| **Personnalisé** | Identique à la zone de recadrage | Libre, ou un ratio de votre choix : 1:1, 16:9, 4:3, 3:4 |

Les photos de profil s'ouvrent avec **Avatar**, les icônes de courtier avec **Icône** et les images de la page Fichiers avec
**Personnalisé** ; les icônes d'actif sont recadrées en carré à 256 × 256 px. Vous pouvez changer de préréglage à tout moment.

---

## ⚙️ Paramètres de sortie

- 🎨 **Format** — `.png` (sans perte, conserve la transparence), `.jpg` (plus petit, sans transparence) ou
  `.webp` (meilleure compression), à côté du nom de fichier, que vous pouvez aussi modifier. Une image
  `.jpg` ou `.webp` conserve son format ; tout autre format démarre en `.png`.
- 📊 **Qualité** (`.jpg` et `.webp` uniquement) — **−** / **+** par pas de 10 %, de 10 % à 100 % : une qualité
  inférieure signifie un fichier plus petit.
- 📐 **Sortie** — largeur × hauteur en pixels, définies par le préréglage mais modifiables. La largeur et la hauteur restent
  proportionnelles à la zone de recadrage, et vous ne pouvez pas leur attribuer des valeurs supérieures à celles de cette zone ; **Échelle** définit les deux en
  même temps.

---

## ✅ Confirmer ou annuler

- **Recadrer et téléverser** enregistre l'image et l'utilise. Sur la page Fichiers, **Recadrer** l'ajoute plutôt à la liste de téléversement
  (**Restaurer l'original** ↺ ramène l'original), et **Téléverser** envoie la liste.
- **Annuler** ou **✕** ferme l'outil — après demande, si vous avez des modifications non enregistrées
  (**Abandonner et fermer**). Depuis le sélecteur d'image, vous revenez au sélecteur.

??? info "📄 Fichiers non image — sur la page Fichiers"

    Un PDF, un CSV ou tout autre fichier non image n'a pas d'étape de recadrage : son bouton ✏️ ouvre une simple
    boîte de dialogue **Renommer** à la place.

---

## 🔗 Voir aussi

- 🛠️ **[Composants de téléversement de fichiers et de médias](../../developer/frontend/components/core-ui/file-upload.md)** — Comment l'outil est construit (pour les développeurs)
