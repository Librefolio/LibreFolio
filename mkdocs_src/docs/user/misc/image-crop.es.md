# ✂️ Herramienta de recorte de imágenes

Encuadra, rota y redimensiona una imagen antes de que LibreFolio la guarde.

---

## 🎯 ¿Cuándo aparece?

- 👤 **Foto de perfil** — en **[Perfil](../settings/profile.md)** o en la página de Bienvenida: en el
  selector de imágenes, elige **Subir** y selecciona una imagen.
- 🏦 **Icono de bróker** y 📈 **icono de activo** — el mismo selector, desde el formulario del bróker o del activo.
- 📂 **Página Archivos** — añade imágenes a la lista de subida y luego haz clic en el botón ✏️ **Editar** de una imagen.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Modal de edición de imagen" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## ✂️ Encuadra la imagen

- 📏 **Arrastra** una esquina o un lado del área de recorte para redimensionarla, su interior para moverla y el exterior
  para mover la imagen. El área de recorte siempre permanece dentro de la imagen.
- 🔍 **Zoom** con la rueda del ratón o **+ / −** — el área de recorte se contrae (o se expande) primero y luego
  se aplica zoom a la imagen — o pellizca en una pantalla táctil.
- 🔄 **Rota** 15° cada vez con **↺ / ↻**, y 🪞 **voltea** con ↔ / ↕.
- 👁️ El botón del ojo a la izquierda activa o desactiva una **vista previa redonda**: cómo se ve la imagen en un círculo, como
  tu avatar en la barra lateral.
- 🔁 **Restablecer todo** (arriba a la derecha) deshace el recorte, el zoom, la rotación y el volteo.

---

## 📐 Preajustes

| Preajuste | Tamaño de salida | Forma |
|--------|------|-------------|
| **Avatar** | 200 × 200 px | Cuadrado, vista previa redonda activada |
| **Icono** | 64 × 64 px | Cuadrado, vista previa redonda activada |
| **Personalizado** | Igual que el área de recorte | Libre, o una relación de aspecto a tu elección: 1:1, 16:9, 4:3, 3:4 |

Las fotos de perfil se abren con **Avatar**, los iconos de bróker con **Icono** y las imágenes de la página Archivos con
**Personalizado**; los iconos de activos se recortan en formato cuadrado a 256 × 256 px. Puedes cambiar de preajuste en cualquier momento.

---

## ⚙️ Ajustes de salida

- 🎨 **Formato** — `.png` (sin pérdida, conserva la transparencia), `.jpg` (más pequeño, sin transparencia) o
  `.webp` (mejor compresión), junto al nombre del archivo, el cual también puedes modificar. Una imagen `.jpg` o `.webp`
  conserva su formato; cualquier otra imagen comienza como `.png`.
- 📊 **Calidad** (solo `.jpg` y `.webp`) — **−** / **+** en pasos del 10 %, del 10 % al 100 %: una calidad más baja
  implica un archivo más pequeño.
- 📐 **Salida** — ancho × alto en píxeles, establecidos por el preajuste pero editables. Ambos mantienen la
  proporción con el área de recorte, y no pueden ser mayores que el de ella; **Escala** establece ambos valores a
  la vez.

---

## ✅ Confirmar o cancelar

- **Recortar y subir** guarda la imagen y la usa. En la página Archivos, **Recortar**, en cambio, la coloca en la lista de subida
  (**Restaurar original** ↺ recupera la original), y **Subir** envía la lista.
- **Cancelar** o **✕** cierra la herramienta — tras preguntar, si tienes cambios sin guardar
  (**Descartar y cerrar**). Desde el selector de imágenes, vuelves al selector.

??? info "📄 Archivos que no son imágenes — en la página Archivos"

    Un PDF, un CSV o cualquier otro archivo que no sea una imagen no tiene un paso de recorte: su botón ✏️ abre en cambio un cuadro de diálogo sencillo
    de **Renombrar**.

---

## 🔗 Relacionado

- 🛠️ **[Componentes de carga de archivos y medios](../../developer/frontend/components/core-ui/file-upload.md)** — Cómo está construida la herramienta (para desarrolladores)
