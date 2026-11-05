# 🧩 Configuración de plugins

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="plugins" alt="Configuración de plugins">
</div>

La pestaña **Plugins** contiene lo que solicitan las fuentes de precios y de tipos de cambio: la clave de API de una fuente de datos de pago, una región o una preferencia tuya. Abre **Configuración** (el icono de engranaje de la barra lateral), luego la pestaña **Plugins**, después de **Preferencias** (en un teléfono, la pestaña con el icono de pieza de puzle). Todos los usuarios la tienen; lo que puedes cambiar allí depende de [a quién pertenece la configuración](#personal-and-instance). El icono de libro de su parte superior abre esta página.

Solo se enumeran los plugins que solicitan algo, bajo **Precios** para los [proveedores de precios](../assets/providers/index.md) y bajo **Tipos de cambio** para los [proveedores de tipos de cambio](../fx/providers/index.md), con cada encabezado después del icono de su familia (un gráfico de columnas para precios, monedas para tipos de cambio); un encabezado sin ese tipo de plugin se omite. De los plugins incluidos con LibreFolio, dos tienen hoy un elemento de configuración, cada uno una preferencia de búsqueda personal: **JustETF** y **Borsa Italiana** (consulta [Preferencias de búsqueda](#search-preferences)). Un plugin añadido a tu instalación puede solicitar más. La pestaña también tiene un grupo **Herramientas**, para las [Herramientas](../tools/index.md) que tienen su propia configuración; ninguna de ellas tiene configuración todavía, así que hoy no lo verás. Cuando ningún plugin solicita nada, la pestaña indica *Ningún plugin instalado solicita configuración.*

## 🧾 Un plugin, un formulario {: #form }

Cada plugin tiene un formulario propio: su icono y su nombre (una pieza de puzle cuando el plugin no tiene icono), una [insignia](#configured) que indica si puede funcionar y, después, su configuración. Cada elemento de configuración muestra su nombre, una **\*** roja cuando es obligatorio, a quién pertenece — **Personal** o **Toda la instancia** — y qué hace.

- Cambia lo que necesites y luego haz clic en **Guardar** al final del formulario de ese plugin: cada plugin se guarda por separado. **Descartar** descarta los cambios que no hayas guardado.
- **Guardar** conserva todos los cambios del plugin, o ninguno: cuando se rechaza uno, no se guarda nada y el elemento de configuración en cuestión explica por qué.
- Antes de guardar, LibreFolio comprueba lo que has escrito con las reglas del plugin — un número, un número entero, un mínimo o un máximo, una longitud, una de las opciones — y muestra debajo del elemento de configuración qué está mal, por ejemplo *Al menos 8 caracteres*. **Guardar** permanece deshabilitado hasta que se corrija.
- Un cambio guardado se muestra en el propio elemento de configuración, sin ningún mensaje. Un plugin cuya configuración no puedas cambiar no tiene botones.

??? note "💬 Cuando un guardado no se completa"

    | Mensaje | Qué ocurrió |
    |---|---|
    | *No se guardó nada: revisa la configuración de abajo.* | Se rechazó un elemento de configuración. Debajo: *El valor no es válido para este elemento de configuración.*, *Solo un administrador puede cambiar este elemento de configuración.*, *Una variable del servidor lo establece: no se puede cambiar aquí.* o *Este elemento de configuración ya no existe: recarga la página.* |
    | *Esta configuración cambió mientras tanto: se ha vuelto a cargar; guarda de nuevo.* | Alguien guardó la misma configuración en el mismo momento: no se guardó nada de lo tuyo. Revisa los valores mostrados y vuelve a guardar. |
    | *No se pueden guardar los secretos: no se puede usar la clave de esta instancia (consulta las comprobaciones de configuración).* | No se guardó nada: no se puede cifrar un secreto. Un administrador puede encontrar la causa en las [comprobaciones de inicio](../../admin/configuration_security.md#startup-checks). |
    | *No se pudo guardar la configuración.* | No hay respuesta del servidor: inténtalo de nuevo. |

---

## 👥 Configuración personal y de toda la instancia {: #personal-and-instance }

Junto a su nombre, cada elemento de configuración indica a quién pertenece:

| | **Personal** | **Toda la instancia** |
|---|---|---|
| **Su valor** | El tuyo: cada usuario tiene el suyo | Uno para todos en este LibreFolio |
| **Quién lo cambia** | Tú | Un administrador |
| **Quién lo ve** | Solo tú: ni siquiera un administrador | Todos; los usuarios que no son administradores lo ven en solo lectura, con *Solo un administrador puede cambiarlo.* De un secreto, solo ven si está establecido |
| **Qué cambia** | Lo que LibreFolio hace solo para ti: tus búsquedas y las comprobaciones del proveedor en el diálogo del activo, como **Probar configuración** | Todo lo que hace el plugin, incluidos los precios y los tipos de cambio |

Los precios, los historiales de precios y los tipos de cambio son compartidos por todos, así que nunca dependen de la elección de un usuario: para ellos, un elemento de configuración personal siempre toma el valor predeterminado del plugin.

!!! info "🛡️ Para administradores"

    Aquí cambias la configuración de toda la instancia, igual que los demás cambian la suya personal. Un elemento de configuración de toda la instancia también puede establecerse mediante la configuración del servidor: consulta [Establecido por el servidor](#set-by-the-server) y [Configuración de plugins](../../admin/configuration_secrets.md#plugin-settings) en el manual de administradores para obtener información sobre las variables.

---

## 🔐 Secretos {: #secrets }

Algunos elementos de configuración son secretos, como una clave de API. Un secreto es de solo escritura:

- **Escríbelo y luego guarda.** Lo que escribiste se envía una vez y luego se elimina de la página: a partir de entonces, el elemento de configuración solo muestra *Establecido el* con la fecha y la hora en que se guardó, nunca el secreto en sí, ni siquiera para ti. El campo está marcado como una contraseña nueva, de modo que el navegador no lo rellena con una de tus contraseñas guardadas.
- **Reemplazar** abre el campo para un nuevo valor; **Cancelar** conserva el guardado.
- **Borrar** elimina el secreto cuando haces clic en **Guardar** (*Se eliminará cuando guardes.*); **Deshacer** lo conserva.

Los usuarios que no son administradores ven un secreto de toda la instancia como *Establecido el …* (*Establecido* cuando lo [establece el servidor](#set-by-the-server)) o *No establecido*, y nada más. LibreFolio mantiene cifrado un secreto guardado: consulta [Secretos guardados y la clave de la instancia](../../admin/configuration_secrets.md#plugin-secrets).

---

## 🔒 Establecido por el servidor {: #set-by-the-server }

Un administrador también puede establecer un elemento de configuración de toda la instancia mediante la configuración del servidor, con una variable de entorno. El elemento de configuración muestra entonces su valor en solo lectura, un secreto solo como *Establecido*, con :material-lock-outline: *Establecido por el servidor*: nadie puede cambiarlo aquí, ni siquiera un administrador. Los administradores también ven el nombre de la variable: *Establecido por la variable del servidor*, seguido de dicho nombre.

Para cambiar un elemento de configuración así, un administrador cambia la variable y reinicia LibreFolio: consulta [Una variable bloquea el elemento de configuración](../../admin/configuration_secrets.md#plugin-variable-lock).

---

## ↩️ Volver al valor predeterminado {: #use-the-default }

Una vez que hayas guardado un valor propio en un elemento de configuración que puedes cambiar, **Usar el valor predeterminado** aparece debajo. Elimina el valor guardado cuando haces clic en **Guardar**, y el elemento de configuración vuelve al valor predeterminado del plugin: *El valor guardado se eliminará cuando guardes: se aplica el valor predeterminado.*, con **Deshacer**. Vaciar un campo de texto que muestra un valor guardado hace lo mismo. Un secreto no tiene valor predeterminado: **Borrar** lo elimina ([Secretos](#secrets)).

---

## ⚠️ Cuando un elemento de configuración tiene un problema {: #problems }

| El elemento de configuración dice | Qué ocurrió | Qué hacer |
|---|---|---|
| *La variable del servidor … no es válida: el plugin permanece sin configurar hasta que se corrija.* | La variable que lo establece contiene un valor que el elemento de configuración rechaza, o indica un archivo que no se puede leer. LibreFolio nunca recurre a un valor guardado ni al valor predeterminado. Los administradores ven el nombre de la variable | Un administrador corrige la variable y reinicia LibreFolio |
| *El valor guardado ya no es válido: se aplica el valor predeterminado.* | El plugin ya no acepta el valor guardado anteriormente, por ejemplo después de una actualización | Vuelve a elegir un valor y guárdalo, o déjalo: mientras tanto, se aplica el valor predeterminado |
| *Guardado, pero la clave de esta instancia no puede leerlo. Si un administrador puede restaurar la clave anterior, eso tiene prioridad; de lo contrario, vuelve a introducirlo.* | Un secreto guardado ya no se puede leer porque la clave de cifrado de la instancia ha cambiado. LibreFolio lo conserva, pero nunca lo usa | Si un administrador aún puede restaurar la clave anterior de la instancia, eso tiene prioridad: un secreto guardado con la nueva clave dejaría de poder leerse una vez restaurada la clave anterior (consulta [Secretos guardados y la clave de la instancia](../../admin/configuration_secrets.md#plugin-secrets)). De lo contrario, vuelve a escribir el secreto y guárdalo; en el caso de un secreto de toda la instancia, lo hace un administrador |

---

## 🚦 Configurado o por configurar {: #configured }

La insignia junto al nombre de cada plugin indica si puede funcionar:

- **Configurado**: cada elemento de configuración obligatorio tiene un valor que LibreFolio puede usar.
- **Por configurar**: un elemento de configuración obligatorio no tiene un valor utilizable —nunca se ha establecido, o es un secreto que ya no se puede leer— o una variable del servidor que establece uno de sus elementos de configuración no es válida.

LibreFolio no llama a un plugin que está **Por configurar**: sus precios o tipos de cambio no se actualizan, una búsqueda indica que debe configurarse y **Probar configuración** falla con ❌ *Este proveedor debe configurarse antes de usarse*. Los plugins incluidos con LibreFolio no necesitan ningún elemento de configuración para funcionar: **JustETF** y **Borsa Italiana** siempre están **Configurados**.

---

## 🛠️ Configurar desde un activo {: #configure }

No tienes que salir de un activo para cambiar la configuración de su proveedor: **Configurar** abre el mismo formulario que esta pestaña, para ese proveedor de precios, sobre el diálogo en el que estás.

- **En el diálogo del activo** (**+ Añadir activo**, o **Editar** en un activo), en **Asignación de proveedor**: cuando el proveedor elegido tiene configuración, **Configurar** aparece junto a su :material-help-circle-outline: enlace de ayuda —en un teléfono, solo su icono :material-tune:—. Cuando el proveedor aún no puede funcionar, **Por configurar** también se muestra allí. Después de guardar, la insignia se actualiza y el activo que estás editando queda como estaba.
- **En Búsqueda en línea**: cuando un proveedor debe configurarse antes de poder buscar, la lista de resultados empieza con una línea *… debe configurarse antes de poder buscar*, con el nombre del proveedor, y su propio botón **Configurar**. Una vez que guardas, la búsqueda se ejecuta de nuevo. Así, un proveedor que no pudo buscar nunca se confunde con uno que no encontró nada.

---

## 🔎 Preferencias de búsqueda: JustETF y Borsa Italiana {: #search-preferences }

Ambas son configuraciones de tipo **Personal**, y ambas muestran todo hasta que elijas lo contrario. Solo eligen qué filas enumeran tus propias búsquedas: no cambian ningún precio, ni tampoco ningún activo que ya tengas. Tampoco desaparece ningún instrumento: cada uno existe en todas las monedas o idiomas, así que una preferencia solo conserva una de sus filas.

| Plugin | Elemento de configuración | Opciones | Qué cambia en **Búsqueda en línea** |
|---|---|---|---|
| **JustETF** | **Moneda preferida** | **Todas las monedas** (el valor predeterminado), 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF, 🇬🇧 GBP | Con una moneda, cada fondo aparece una vez, en esa moneda. Con **Todas las monedas**, cada fondo aparece cuatro veces, una por moneda |
| **Borsa Italiana** | **Idioma preferido** | **Ambos idiomas** (el valor predeterminado), 🇮🇹 Italiano, 🇬🇧 Inglés | Con un idioma, cada instrumento aparece una vez, en ese idioma: aquel en el que aparecen su nombre y sus detalles. Con **Ambos idiomas**, primero italiano y luego inglés. El sitio web de Borsa Italiana se busca de la misma manera independientemente de lo que elijas |

Configúralas aquí, en **JustETF** y **Borsa Italiana**, o con **Configurar** en el diálogo del activo mientras ese proveedor esté elegido.

### 👑 La corona en los resultados de JustETF {: #crown }

👑 marca la moneda propia de un fondo, aquella en la que se calcula su NAV —no necesariamente aquella en la que operas—. Siempre que un resultado la muestra, una línea al final de la lista lo indica: *👑 la moneda propia del fondo*. Con una moneda preferida, 👑 aparece solo en los fondos calculados en esa moneda: con 🇪🇺 EUR, un fondo calculado en dólares estadounidenses muestra solo 🇪🇺.

Cómo funciona la moneda de un activo de justETF: [Elegir la moneda en la búsqueda](../assets/providers/justetf.md).

---

## 🔗 Relacionado

- 🎛️ **[Preferencias del usuario](preferences.md)** — Idioma, moneda base, tema y guías
- ⚙️ **[Resumen de la configuración](index.md)** — Cada pestaña de Configuración
- 📡 **[justETF](../assets/providers/justetf.md)** y 🇮🇹 **[Borsa Italiana](../assets/providers/borsa-italiana.md)** — Los dos proveedores con una preferencia de búsqueda
- 🛠️ **[Configuración de plugins para administradores](../../admin/configuration_secrets.md#plugin-settings)** — Las variables del servidor, la clave de la instancia y el cifrado de los secretos
- 🧩 **[Configuración de plugins para desarrolladores](../../developer/architecture/patterns/plugin_settings.md)** — Cómo declara un plugin su configuración
