# ✂️ Herramienta de Recorte de Imágenes

LibreFolio incluye una potente herramienta interactiva de edición de imágenes que te permite recortar, rotar y cambiar el tamaño de las imágenes antes de subirlas.

---

## 🎯 ¿Cuándo aparece?

La ventana modal de recorte de imágenes se abre automáticamente cada vez que subes un archivo de imagen en LibreFolio:

- 📂 **Página de archivos** → subir cualquier imagen (JPEG, PNG, WebP, GIF)
- 👤 **Configuración de perfil** → cambiar tu avatar
- 🏦 **Configuración de bróker** → cambiar el icono de un bróker

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Ventana de edición de imagen" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Predefinidos

La herramienta ofrece predefinidos para casos de uso comunes:

| Predefinido | Tamaño | Relación de aspecto | Caso de uso |
|----------------|--------|---------------------|-------------|
| **Avatar** | 200 × 200 px | 1:1 (cuadrado) | Imágenes de perfil de usuario |
| **Icono de bróker** | 64 × 64 px | 1:1 (cuadrado) | Logotipos de brókers |
| **Personalizado** | Libre | Libre | Cualquier tamaño y relación |

El predefinido establece automáticamente la restricción de relación de aspecto y el tamaño de salida.

---

## 🎛️ Controles

### ✂️ Área de recorte

- 📏 **Arrastra las esquinas** para cambiar el tamaño del área de recorte
- ↔️ **Arrastra dentro** del área para moverla
- 🔒 El área de recorte está **restringida a los límites de la imagen** — no puedes seleccionar fuera de la imagen

### 🔍 Zoom

- 🖱️ **Rueda del ratón** o **pellizco** (en dispositivos táctiles) para acercar/alejar
- ➕ **Botones de zoom** (+/−) para control preciso
- 🎯 El zoom se centra en la selección de recorte

### 🔄 Rotación

- 🔄 **Botones de rotación** (↺/↻) rotan en pasos de 15°
- 📍 La rotación ocurre relativa al centro de la selección

### 🪞 Voltear

- ↔️ **Voltear Horizontalmente** (↔) — refleja la imagen de izquierda a derecha
- ↕️ **Voltear Verticalmente** (↕) — refleja la imagen de arriba a abajo

---

## ⚙️ Configuración de salida

Antes de confirmar, puedes ajustar:

- 🎨 **Formato de salida**: PNG (sin pérdida, transparencia), JPEG (más pequeño, sin transparencia), WebP (moderno, mejor compresión)
- 📊 **Calidad** (solo JPEG/WebP): Deslizador de 10% a 100% — menor calidad = archivo más pequeño
- 📐 **Tamaño de salida**: Ancho y alto en píxeles (asociado al predefinido, pero editable)

!!! tip "Vista previa circular"
    Para los predefinidos de avatar e icono, se muestra una **superposición circular** en el área de recorte. Esto te ayuda a previsualizar cómo se verá la imagen en un marco circular (p. ej., avatares de usuario en la barra de navegación).

---

## 🔄 Flujo de trabajo

1. **Sube o arrastra** un archivo de imagen
2. Se abre la ventana modal de recorte con el predefinido apropiado
3. **Ajusta** el área de recorte, zoom, rotación según sea necesario
4. **Previsualiza** el resultado en tiempo real
5. Haz clic en **Subir** para confirmar — la imagen recortada se guarda en el servidor
6. Haz clic en **Cancelar** o cierra la ventana modal para descartar los cambios

!!! info "Archivos que no son imágenes"
    Si subes un archivo que no es una imagen (PDF, CSV, etc.), se omite la ventana modal de recorte. En su lugar, aparece un simple cuadro de diálogo para renombrar.
