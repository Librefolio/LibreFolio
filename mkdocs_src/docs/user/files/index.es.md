# 📁 Archivos y subidas

La página **Archivos** guarda todo lo que se ha subido a LibreFolio, en dos pestañas:

- **Recursos estáticos** — avatares, iconos de brókeres y otras imágenes o documentos, visibles para todos los usuarios;
- **Informes del bróker** — los archivos de extractos desde los que importas transacciones, visibles solo para las personas con acceso a su bróker.

---

## 🖼️ Recursos estáticos

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Pestaña de Archivos estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Aquí encuentras los **avatares** de los usuarios, los **iconos** de los brókeres y cualquier **imagen o documento** compartido por los usuarios. Todos los que tienen una cuenta de LibreFolio pueden verlos.

- Cambia entre la vista de **lista** y de **cuadrícula**: la cuadrícula muestra previsualizaciones de las imágenes.
- En la lista, haz clic con el botón derecho en un archivo para **Previsualizar**, **Copiar enlace**, **Descargar** o **Eliminar**. Solo puedes eliminar los archivos que hayas subido tú; un administrador puede eliminar cualquiera.
- **Previsualizar** muestra un PDF en un visor de solo lectura: puedes leerlo, buscarlo y copiar su texto, pero no editarlo, anotarlo ni imprimirlo; para conservar el archivo, usa **Descargar**. Un PDF protegido con contraseña pide su contraseña, que permanece en tu navegador: nunca se envía al servidor ni se guarda, y desaparece en cuanto se cierra la previsualización.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista de cuadrícula de Archivos estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Subir un archivo

1. Haz clic en **Subir** y luego suelta archivos sobre el área o haz clic en ella para examinar.
2. Antes de subir, puedes hacer clic en ✏️ **Editar** en una imagen para recortarla con la [herramienta de recorte de imagen](../misc/image-crop.md) y luego confirmar con **Recortar**; en cualquier otro archivo, ✏️ **Renombrar** cambia su nombre. **Restaurar original** devuelve un archivo tal como lo seleccionaste.
3. Haz clic en **Subir**.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zona para soltar archivos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📊 Informes del bróker {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Pestaña de Informes del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Estos son los extractos exportados por tus brókeres, a la espera de ser importados o ya importados. Ves los informes de todos los brókeres a los que puedes acceder, ya sea como Propietario, Editor o Lector.

La columna **Estado** te indica en qué situación está cada archivo:

- **Subido** — almacenado, aún no analizado;
- **Analizado** — el Asistente de importación lo leyó correctamente;
- **Fallido** — el análisis falló; el archivo permanece aquí para que puedas revisarlo o reportarlo.

### 📤 Subir un informe del bróker

1. En **Informes del bróker**, haz clic en **Subir** y elige archivos CSV o Excel.
2. En **Asignar brókeres**, elige el bróker de cada archivo, o uno para todos con **Asignar todos a**. **Crear nuevo** añade un bróker al momento; si solo puedes editar un bróker, ya está elegido.
3. Haz clic en **Subir**. Los archivos se almacenan, pero **todavía no se importa nada**.

Para importarlos, abre el [Asistente de importación](../transactions/import/index.md) (**Transacciones** → **Importar**): su paso **Seleccionar archivos** enumera los informes que has subido.

El bróker que elijas solo decide qué cuenta recibe las transacciones. El importador reconoce el formato del archivo por sí mismo, y un mismo plugin de importación puede leer las exportaciones de varios brókeres.

### ⚙️ Gestionar informes

Haz clic con el botón derecho en un informe para **Previsualizar**, **Descargar** o **Eliminar**, o marca varios para eliminarlos juntos. Eliminar un informe nunca elimina las transacciones ya importadas desde él.

### 🧩 Conjuntos de informes {: #report-sets }

Algunos bancos dividen una cuenta en varias exportaciones: [Danske Bank](../transactions/import/danske-bank.md), por ejemplo, necesita una exportación de movimientos de valores y un extracto de la cuenta de efectivo. Las exportaciones de un banco de este tipo que subes **juntas** forman un **conjunto de informes**, y LibreFolio las importa como una sola, mediante un **archivo combinado** que construye a partir de ellas. La columna **Conjunto de informes** te indica en qué situación está cada archivo (la misma columna aparece en los **Informes subidos** de un bróker):

| Insignia | Significado |
|:--|:--|
| **Conjunto de ‹fecha›** | El archivo pertenece al conjunto subido en esa fecha, junto con las demás exportaciones del conjunto. |
| **Incompleto** | Al conjunto aún le falta una exportación requerida: pasa el cursor sobre la insignia para ver cuál. Añádela desde la tarjeta del conjunto en el Asistente de importación, con **Subir el archivo que falta**. |
| **Combinado** | El archivo que LibreFolio construyó a partir de las exportaciones de un conjunto — el que la importación lee realmente. Pasa el cursor sobre la insignia para ver los archivos a partir de los cuales se construyó y cuáles de ellos se han eliminado desde entonces. |
| **Usado en un archivo combinado** | Esta exportación pasó a formar parte de un archivo combinado de su conjunto. |
| **Para recombinar** | El importador ha cambiado desde que se construyó el archivo combinado: analizar el conjunto de nuevo lo reconstruye. |

Puedes previsualizar, descargar y eliminar estos archivos como cualquier otro informe. Eliminar una exportación de un conjunto deja su archivo combinado en su sitio, pero para importar el conjunto de nuevo primero tienes que volver a subir esa exportación en él.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Pestaña de Informes del bróker con archivos de Danske Bank, sus insignias de Conjunto de informes y el filtro Subido por abierto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Quién subió cada archivo {: #uploaded-by }

Ambas pestañas muestran quién subió cada archivo en la columna **Subido por**, con el avatar y el nombre de la persona:

- haz clic en el encabezado de la columna para ordenar por quien lo subió;
- abre su filtro para quedarte solo con los archivos de una o varias personas: márcalas en la lista o búscalas por nombre;
- un archivo para el que no se registró quién lo subió muestra *Usuario que lo subió no registrado*.

El filtro también se aplica a la vista de cuadrícula de **Recursos estáticos**. Se guarda en la dirección de la página, así que un marcador o un enlace compartido se abre con el mismo filtro.

---

## 🔒 Acceso y límites

- 🌐 **Recursos estáticos** — cualquier usuario con sesión iniciada puede verlos.
- 🔐 **Informes del bróker** — solo los usuarios con acceso al bróker pueden verlos; subir y eliminar requiere acceso de Propietario o Editor.
- 📏 **Tamaño** — hasta el límite que el administrador establece en [Configuración global](../../admin/settings.md): 10 MB salvo que se cambie.
- 🚫 **Tipos de archivo** — los programas y scripts (como archivos `.exe`, `.sh` o `.py`) se rechazan como recursos estáticos; los informes del bróker deben ser archivos CSV o Excel.

Dónde se almacenan los archivos en el servidor se describe en [Estructura del sistema de archivos](../../admin/filesystem.md).
