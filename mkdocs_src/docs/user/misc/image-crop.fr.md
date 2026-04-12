# ✂️ Outil de recadrage d'image

LibreFolio inclut un outil d'édition d'image interactif et puissant qui vous permet de recadrer, faire pivoter et redimensionner vos images avant de les téléverser.

---

## 🎯 Quand apparaît-il ?

La fenêtre modale de recadrage d'image s'ouvre automatiquement chaque fois que vous téléversez un fichier image dans LibreFolio :

- 📂 **Page Fichiers** → téléversement de n'importe quelle image (JPEG, PNG, WebP, GIF)
- 👤 **Paramètres du profil** → modification de votre avatar
- 🏦 **Paramètres du courtier** → modification de l'icône d'un courtier

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Fenêtre modale d'édition d'image" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Préréglages

L'outil propose des préréglages pour les cas d'utilisation courants :

| Préréglage | Taille | Rapport d'aspect | Cas d'utilisation |
|--------|------|-------------|----------|
| **Avatar** | 200 × 200 px | 1:1 (carré) | Photos de profil utilisateur |
| **Icône Courtier** | 64 × 64 px | 1:1 (carré) | Logos de courtiers |
| **Personnalisé** | Libre | Libre | Toute taille et tout ratio |

Le préréglage définit automatiquement la contrainte du rapport d'aspect et la taille de sortie.

---

## 🎛️ Commandes

### ✂️ Zone de recadrage

- 📏 **Faites glisser les coins** pour redimensionner la zone de recadrage
- ↔️ **Faites glisser à l'intérieur** de la zone pour la déplacer
- 🔒 La zone de recadrage est **restreinte aux limites de l'image** — vous ne pouvez pas sélectionner d'espace en dehors de l'image

### 🔍 Zoom

- 🖱️ **Molette de la souris** ou **pincement** (sur les appareils tactiles) pour zoomer/dézoomer
- ➕ **Boutons de zoom** (+/−) pour un contrôle précis
- 🎯 Le zoom se centre sur la sélection de recadrage

### 🔄 Rotation

- 🔄 **Boutons de rotation** (↺/↻) pour pivoter par paliers de 15°
- 📍 La rotation s'effectue relativement au centre de la sélection

### 🪞 Retournement

- ↔️ **Retournement horizontal** (↔) — effet miroir gauche-droite
- ↕️ **Retournement vertical** (↕) — effet miroir haut-bas

---

## ⚙️ Paramètres de sortie

Avant de confirmer, vous pouvez ajuster :

- 🎨 **Format de sortie** : PNG (sans perte, transparence), JPEG (plus léger, sans transparence), WebP (moderne, meilleure compression)
- 📊 **Qualité** (JPEG/WebP uniquement) : Curseur de 10% à 100% — une qualité inférieure = un fichier plus petit
- 📐 **Taille de sortie** : Largeur et hauteur en pixels (liées au préréglage, mais modifiables)

!!! tip "Aperçu elliptique"

    Pour les préréglages d'avatar et d'icône, une **superposition elliptique** circulaire est affichée sur la zone de recadrage. Cela vous aide à prévisualiser l'apparence de l'image dans un cadre circulaire (par exemple, les avatars d'utilisateurs dans la barre de navigation).

---

## 🔄 Flux de travail

1. **Téléversez ou glissez-déposez** un fichier image
2. La fenêtre de recadrage s'ouvre avec le préréglage approprié
3. **Ajustez** la zone de recadrage, le zoom et la rotation selon vos besoins
4. **Prévisualisez** le résultat en temps réel
5. Cliquez sur **Téléverser** pour confirmer — l'image recadrée est enregistrée sur le serveur
6. Cliquez sur **Annuler** ou fermez la fenêtre pour abandonner les modifications

!!! info "Fichiers autres que des images"

    Si vous téléversez un fichier qui n'est pas une image (PDF, CSV, etc.), la fenêtre de recadrage est ignorée. À la place, une simple boîte de dialogue de renommage apparaît.
