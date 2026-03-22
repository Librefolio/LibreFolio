# ✂️ Outil de recadrage d'image

LibreFolio inclut un outil de recadrage d'image interactif et puissant qui vous permet de recadrer, faire pivoter et redimensionner les images avant de les importer.

---

## 🎯 Quand apparaît-il ?

La fenêtre de recadrage s'ouvre automatiquement lorsque vous importez une image dans LibreFolio :

- 📂 **Page Fichiers** → import d'une image (JPEG, PNG, WebP, GIF)
- 👤 **Paramètres du profil** → modification de votre avatar
- 🏦 **Paramètres du courtier** → changement de l'icône d'un courtier

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Fenêtre d'édition d'image" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Paramètres prédéfinis

L'outil propose des paramètres prédéfinis pour les cas d'utilisation courants :

| Paramètre | Taille | Ratio | Cas d'utilisation |
|----------|--------|-------|------------------|
| **Avatar** | 200 × 200 px | 1:1 (carré) | Images de profil utilisateur |
| **Icône de courtier** | 64 × 64 px | 1:1 (carré) | Logos de courtiers |
| **Personnalisé** | Libre | Libre | Taille et ratio quelconques |

Le paramètre prédéfini définit automatiquement la contrainte de proportions et la taille de sortie.

---

## 🎛️ Contrôles

### ✂️ Zone de recadrage

- 📏 **Glissez les coins** pour redimensionner la zone de recadrage
- ↔️ **Glissez à l'intérieur** de la zone pour la déplacer
- 🔒 La zone de recadrage est confinée à l'image — vous ne pouvez pas sélectionner en dehors de l'image

### 🔍 Zoom

- 🖱️ **Molette de la souris** ou **pincement** (sur les appareils tactiles) pour zoomer/dézoomer
- ➕ **Boutons de zoom** (+/−) pour un contrôle précis
- 🎯 Le zoom est centré sur la zone de recadrage.

### 🔄 Rotation

- 🔄 **Boutons de rotation** (↺/↻) font pivoter l'image par incréments de 15°.
- 📍 La rotation s'effectue par rapport au centre de la sélection.

### 🪞 Retourner

- ↔️ **Retourner horizontalement** (↔) — inverse l'image de gauche à droite
- ↕️ **Retourner verticalement** (↕) — inverse l'image de haut en bas

---

## ⚙️ Paramètres de sortie

Avant de confirmer, vous pouvez ajuster :

- 🎨 **Format de sortie** : PNG (sans perte, transparence), JPEG (plus petit, pas de transparence), WebP (moderne, meilleure compression)
- 📊 **Qualité** (JPEG/WebP uniquement) : curseur de 10% à 100% — qualité inférieure = fichier plus petit
- 📐 **Taille de sortie** : largeur et hauteur en pixels (liées au paramètre prédéfini mais modifiables)

!!! tip "Aperçu elliptique"
    Pour les paramètres prédéfinis Avatar et Icône de courtier, une superposition elliptique est affichée sur la zone de recadrage. Cela vous aide à prévisualiser l'apparence de l'image dans un cadre circulaire (par exemple, les avatars utilisateur dans la barre de navigation).

---

## 🔄 Processus

1. **Importez ou déposez** un fichier image
2. La fenêtre de recadrage s'ouvre avec le paramètre prédéfini approprié
3. **Ajustez** la zone de recadrage, le zoom, la rotation si nécessaire
4. **Prévisualisez** le résultat en temps réel
5. Cliquez sur **Téléverser** pour confirmer — l'image recadrée est enregistrée sur le serveur
6. Cliquez sur **Annuler** ou fermez la fenêtre pour ignorer les modifications

!!! info "Fichiers qui ne sont pas des images"
    Si vous importez un fichier qui n'est pas une image (PDF, CSV, etc.), la fenêtre de recadrage est ignorée. À la place, une simple boîte de dialogue de renommage apparaît.
