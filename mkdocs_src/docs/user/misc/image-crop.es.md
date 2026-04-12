# ✂️ Herramienta de Recorte de Imagen

LibreFolio incluye una potente herramienta interactiva de edición de imágenes que le permite recortar, rotar y cambiar el tamaño de las imágenes antes de subirlas.

---

## 🎯 ¿Cuándo aparece?

El modal de Recorte de Imagen se abre automáticamente siempre que suba un archivo de imagen en LibreFolio:

- 📂 **Página de Archivos** → al subir cualquier imagen (JPEG, PNG, WebP, GIF)
- 👤 **Configuración de perfil** → al cambiar su avatar
- 🏦 **Configuración del bróker** → al cambiar el icono de un bróker

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="media" data-name="image-edit-modal" alt="Modal de Edición de Imagen" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📐 Ajustes preestablecidos

La herramienta ofrece ajustes preestablecidos para los casos de uso más comunes:

| Ajuste | Tamaño | Relación de aspecto | Caso de uso |
|--------|------|-------------|----------|
| **Avatar** | 200 × 200 px | 1:1 (cuadrado) | Fotos de perfil de usuario |
| **Icono de Bróker** | 64 × 64 px | 1:1 (cuadrado) | Logotipos de brókers |
| **Personalizado** | Libre | Libre | Cualquier tamaño y proporción |

El ajuste preestablecido define automáticamente la restricción de la relación de aspecto y el tamaño de salida.

---

## 🎛️ Controles

### ✂️ Área de recorte

- 📏 **Arrastre las esquinas** para cambiar el tamaño del área de recorte
- ↔️ **Arrastre dentro** del área para moverla
- 🔒 El área de recorte está **limitada a los bordes de la imagen** — no puede seleccionar fuera de la imagen

### 🔍 Zoom

- 🖱️ **Rueda del ratón** o **gesto de pinza** (en dispositivos táctiles) para acercar o alejar la imagen
- ➕ **Botones de zoom** (+/−) para un control preciso
- 🎯 El zoom se centra en la selección del recorte

### 🔄 Rotación

- 🔄 **Botones de rotación** (↺/↻) rotan en pasos de 15°
- 📍 La rotación se realiza respecto al centro de la selección

### 🪞 Volteo

- ↔️ **Volteo Horizontal** (↔) — refleja la imagen de izquierda a derecha
- ↕️ **Volteo Vertical** (↕) — refleja la imagen verticalmente

---

## ⚙️ Configuración de salida

Antes de confirmar, puede ajustar:

- 🎨 **Formato de salida**: PNG (sin pérdida, transparencia), JPEG (más pequeño, sin transparencia), WebP (moderno, mejor compresión)
- 📊 **Calidad** (solo JPEG/WebP): Control deslizante del 10% al 100% — menor calidad = archivo más pequeño
- 📐 **Tamaño de salida**: Ancho y alto en píxeles (vinculado al ajuste preestablecido, pero editable)

!!! tip "Vista previa de elipse"

    Para los ajustes de avatar e icono, se muestra una **superposición de elipse** circular sobre el área de recorte. Esto le ayuda a previsualizar cómo se verá la imagen en un marco circular (por ejemplo, los avatares de usuario en la barra de navegación).

---

## 🔄 Flujo de trabajo

1. **Suba o arrastre** un archivo de imagen
2. El modal de recorte se abre con el ajuste preestablecido correspondiente
3. **Ajuste** el área de recorte, el zoom y la rotación según sea necesario
4. **Previsualice** el resultado en tiempo real
5. Haga clic en **Subir** para confirmar — la imagen recortada se guarda en el servidor
6. Haga clic en **Cancelar** o cierre el modal para descartar los cambios

!!! info "Archivos que no son imágenes"

    Si sube un archivo que no es una imagen (PDF, CSV, etc.), el modal de recorte se omite. En su lugar, aparece un diálogo sencillo para renombrar el archivo.
