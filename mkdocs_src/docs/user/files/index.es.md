# 📁 Archivos y subidas

La página **Archivos** guarda todo lo subido a LibreFolio, en dos pestañas:

- **Recursos estáticos** — avatares, iconos de brókeres y otras imágenes o documentos, cada uno **compartido** con todos los usuarios o **personal para quien lo subió**;
- **Informes del bróker** — los archivos de extractos desde los que importas transacciones, visibles solo para las personas con acceso a su bróker.

Los administradores también ven una tercera pestaña, [Copias de seguridad](#backups-tab), y una barra con el [espacio que ocupa la instancia](#space-used).

---

## 🖼️ Recursos estáticos

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-tab" alt="Pestaña de archivos estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Aquí encuentras los **avatares** de los usuarios, los **iconos** de los brókeres y las **imágenes y documentos** subidos por los usuarios: los compartidos, que puede ver cualquiera con una cuenta de LibreFolio, y los personales, que solo puedes ver tú y los administradores (consulta [Compartido o personal](#visibility)).

- Cambia entre la vista de **lista** y de **cuadrícula**: la cuadrícula muestra vistas previas de las imágenes.
- En la lista, haz clic derecho en un archivo y elige **Vista previa**, **Copiar enlace**, **Descargar** o **Eliminar**. Solo puedes eliminar los archivos que hayas subido, así que **Eliminar** aparece solo en ellos; un administrador puede eliminar cualquiera. Marca varios archivos para eliminarlos juntos: los archivos de otros usuarios se quedan donde están, y un aviso te lo indica.
- La **Vista previa** muestra un PDF en un visor de solo lectura: puedes leerlo, buscar en él y copiar su texto, pero no editarlo, anotarlo ni imprimirlo; para conservar el archivo, usa **Descargar**. Un PDF protegido con contraseña pide su contraseña, que permanece en tu navegador: nunca se envía al servidor ni se guarda, y desaparece cuando se cierra la vista previa.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="static-grid" alt="Vista de cuadrícula de archivos estáticos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### ⬆️ Subir un archivo

1. Haz clic en **Subir**, luego suelta archivos en el área o haz clic en ella para examinar.
2. Antes de subirlos, puedes hacer clic en ✏️ **Editar** en una imagen para recortarla con la [herramienta de recorte de imágenes](../misc/image-crop.md) y luego confirmar con **Recortar**; en cualquier otro archivo, ✏️ **Cambiar nombre** modifica su nombre. **Restaurar original** devuelve un archivo al estado en que lo seleccionaste.
3. Haz clic en **Subir**. Los archivos son **personales**: solo los ves tú y los administradores, hasta que los [compartas](#visibility).

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="media" data-name="file-uploader-empty" alt="Zona para soltar archivos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👥 Compartido o personal {: #visibility }

Cada recurso estático es **Compartido** o **Personal**, como muestra su insignia en la columna **Visibilidad** de la lista:

- **Compartido** — puede verlo todo usuario que haya iniciado sesión;
- **Personal** — solo pueden verlo la persona que lo subió y los administradores. Los demás usuarios no lo encuentran en su lista y no pueden abrirlo, previsualizarlo ni descargarlo.

Un archivo que subes es:

- **personal** cuando lo subes desde esta página;
- **compartido** cuando lo subes desde un selector de imágenes (tu foto de perfil, en **Perfil** o en la página de bienvenida; un icono de bróker; un icono de activo), porque los demás usuarios ven la imagen donde la usas.

Los archivos subidos con una versión anterior de LibreFolio son compartidos si son imágenes; de lo contrario, son personales.

Puedes cambiar la visibilidad de los archivos que hayas subido; un administrador puede cambiarla en cualquier archivo:

- en la lista, haz clic derecho en el archivo: un archivo personal ofrece **Compartir con todos**, y uno compartido, **Hacer personal**;
- en la cuadrícula, usa el mismo interruptor en la tarjeta del archivo: 👥 lo comparte, 🔒 lo hace personal.

Compartir es inmediato. **Hacer personal** te pide confirmación primero: los demás usuarios pierden el archivo, también donde aparece como icono o foto.

El filtro **Visibilidad**, en el encabezado de la columna, conserva solo los archivos compartidos o solo los personales. Al igual que el filtro [Subido por](#uploaded-by), también se aplica a la vista de cuadrícula y se guarda en la dirección de la página.

La pestaña **Existentes** de un selector de imágenes muestra las imágenes compartidas y tus propias imágenes personales, incluso para un administrador. Si eliges allí una de tus imágenes personales, esta pasa a ser compartida, y un aviso te lo indica: los demás usuarios podrán verla donde la uses.

---

## 📊 Informes del bróker {: #broker-reports }

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-tab" alt="Pestaña de informes del bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Estos son los extractos exportados por tus brókeres, pendientes de importar o ya importados. Ves los informes de todos los brókeres a los que puedes acceder, como Propietario, Editor o Lector. Los informes que una versión anterior de LibreFolio guardó sin un bróker aparecen solo aquí: para los administradores, y para la persona que los subió cuando LibreFolio registró quién lo hizo.

La columna **Estado** te indica en qué situación está cada archivo:

- **Subido** — guardado, aún sin analizar;
- **Analizado** — el asistente de importación lo leyó correctamente;
- **Fallido** — el análisis falló; el archivo se queda aquí para que puedas revisarlo o informar de ello.

### 📤 Subir un informe del bróker

1. En **Informes del bróker**, haz clic en **Subir** y elige archivos CSV o Excel.
2. En **Asignar brókeres**, elige el bróker de cada archivo, o uno para todos con **Asignar todos a**. **Crear nuevo** añade un bróker al momento; si solo puedes editar un bróker, ya está elegido.
3. Haz clic en **Subir**. Los archivos se guardan, pero **todavía no se importa nada**.

Para importarlos, abre el [asistente de importación](../transactions/import/index.md) (**Transacciones** → **Importar**): su paso **Seleccionar archivos** muestra los informes que hayas subido.

El bróker que elijas solo decide qué cuenta recibe las transacciones. El importador reconoce el formato del archivo por sí solo, y un complemento de importación puede leer las exportaciones de varios brókeres.

### ⚙️ Gestionar informes

Haz clic derecho en un informe y elige **Vista previa**, **Descargar** o **Eliminar**, o marca varios para eliminarlos juntos. **Eliminar** aparece solo en los informes que puedes eliminar, y al eliminar varios los demás se quedan donde están, con un aviso. Eliminar un informe nunca elimina las transacciones ya importadas desde él.

### 🧩 Conjuntos de informes {: #report-sets }

Algunos bancos dividen una cuenta en varias exportaciones: [Danske Bank](../transactions/import/danske-bank.md), por ejemplo, necesita una exportación de valores y un extracto de la cuenta de efectivo. Las exportaciones de un banco de este tipo que subas **juntas** forman un **conjunto de informes**, y LibreFolio las importa como un solo conjunto, mediante un **archivo combinado** que construye a partir de ellas. La columna **Conjunto de informes** te indica en qué situación está cada archivo (la misma columna aparece en los **Informes subidos** de un bróker):

| Insignia | Significado |
|:--|:--|
| **Conjunto de ‹fecha›** | El archivo pertenece al conjunto subido en esa fecha, junto con las demás exportaciones del conjunto. |
| **Incompleto** | Al conjunto todavía le falta una exportación necesaria: pasa el cursor sobre la insignia para ver cuál. Añádela desde la tarjeta del conjunto en el asistente de importación, con **Subir el archivo que falta**. |
| **Combinado** | El archivo que LibreFolio construyó a partir de las exportaciones de un conjunto: el que la importación lee realmente. Pasa el cursor sobre la insignia para ver los archivos a partir de los cuales se construyó, y cuáles de ellos se han eliminado desde entonces. |
| **Usado en un archivo combinado** | Esta exportación se usó en un archivo combinado de su conjunto. |
| **Para recombinar** | El importador ha cambiado desde que se construyó el archivo combinado: volver a analizar el conjunto lo reconstruye. |

Puedes previsualizar, descargar y eliminar estos archivos como cualquier otro informe. Eliminar una exportación de un conjunto deja su archivo combinado en su lugar, pero para volver a importar el conjunto primero debes volver a subir esa exportación al conjunto.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="files" data-name="brim-report-sets" alt="Pestaña Informes del bróker con archivos de Danske Bank, sus insignias de conjunto de informes y el filtro Subido por abierto" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👤 Quién subió cada archivo {: #uploaded-by }

Ambas pestañas muestran quién subió cada archivo en la columna **Subido por**, con el avatar y el nombre de la persona:

- haz clic en el encabezado de la columna para ordenar por quien subió;
- abre su filtro para conservar solo los archivos de una o varias personas: márcalas en la lista o búscalas por nombre;
- un archivo del que no se registró quién lo subió muestra *Autor de la subida no registrado*.

El filtro también se aplica a la vista de cuadrícula de **Recursos estáticos**. Se guarda en la dirección de la página, así que un marcador o un enlace compartido se abre con el mismo filtro.

---

## 🛠️ Para administradores {: #admin-files }

Solo los administradores ven lo que sigue; los demás usuarios no encuentran ninguna de las dos cosas en la página.

### 📊 El espacio usado {: #space-used }

Por encima de las pestañas, una barra muestra cuánto espacio ocupa la instancia, dividido entre la **base de datos**, los **archivos subidos**, los **informes del bróker**, las **copias de seguridad** y los **otros archivos de LibreFolio**. Si no se ha establecido un límite, se dibuja respecto al disco, con los otros archivos del disco en gris; si hay un límite, respecto a ese límite. Bajo la barra, en el panel cerrado **Avanzado**, estableces el **Espacio total de LibreFolio (MB)**, `0` para no tener límite. Más allá del límite la barra te avisa, y LibreFolio rechaza un archivo o informe nuevo que se sumaría, diciendo a cuánto subir el espacio total; no se elimina nada. La barra se vuelve a leer con **Actualizar**. Cómo leerla y qué establece el límite: [La barra de espacio](../../admin/backup_restore.md#space-used).

### 🗃️ La pestaña Copias de seguridad {: #backups-tab }

La pestaña **Copias de seguridad** enumera las copias de seguridad que LibreFolio conserva en el servidor, con su fecha, origen, tipo y tamaño. Para cada una puedes **Descargar** o **Eliminar**. La misma lista está en **Configuración › Administración › Copia de seguridad**, donde también configuras la limpieza automática: consulta [Copias de seguridad conservadas en el servidor](../../admin/backup_restore.md#kept-backups).

---

## 🔒 Acceso y límites

- 🌐 **Recursos estáticos** — todo usuario que haya iniciado sesión puede ver los compartidos; un archivo personal, solo la persona que lo subió y los administradores (consulta [Compartido o personal](#visibility)). Eliminar un archivo y cambiar su visibilidad corresponden a quien lo subió y a un administrador.
- 🔐 **Informes del bróker** — solo pueden verlos los usuarios con acceso al bróker; subir y eliminar requieren acceso de Propietario o Editor. Un administrador puede ver y eliminar todos los informes.
- 📏 **Tamaño** — hasta el límite que el administrador establece en [Configuración global](../../admin/settings.md): 10 MB salvo que se cambie.
- 🚫 **Tipos de archivo** — los programas y scripts (como archivos `.exe`, `.sh` o `.py`) se rechazan como recursos estáticos; los informes del bróker deben ser archivos CSV o Excel.

Dónde se almacenan los archivos en el servidor se describe en [Estructura del sistema de archivos](../../admin/filesystem.md).
