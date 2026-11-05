# ➕ Crear y editar activos

Añade un instrumento que poseas o sigas, conéctalo a un proveedor de precios y mantén sus datos correctos.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulario de creación manual" alt="Modal de creación manual">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulario de creación automática del asistente de importación" alt="Crear activo desde el asistente">
</div>

## 🚀 Crear un activo {: #asset-creation-flows }

=== "Desde la página Activos"

    1. En la página **Activos**, haz clic en **+ Añadir activo**.
    2. En **Buscar en línea**, escribe un nombre, ticker o ISIN y elige un resultado: LibreFolio completa el
       formulario, conecta ese proveedor y [comprueba sus datos](#provider-data-comparison). ¿Ningún resultado?
       Completa el formulario tú mismo y notifica la búsqueda con [**Házanoslo saber**](#let-us-know).
    3. Revisa los campos de abajo y haz clic en **Crear activo**.

=== "Desde una importación de bróker"

    1. En la sección **Resolver activos** del asistente de importación, elige **Crear nuevo activo** en el selector del valor.
    2. El formulario se abre con los códigos y nombres del informe. Si el informe no tiene nombre, **Nombre** empieza por el ISIN (o el ticker).
    3. Haz clic en una de las **Sugerencias** de **Buscar en línea** para buscar el valor, o completa el formulario tú mismo. Después, haz clic en **Crear activo**.

    Si el resultado que eliges tiene el mismo nombre que uno de tus activos, LibreFolio ofrece usar ese
    activo en su lugar; **Usarlo y añadir la clave** también guarda los códigos del informe en él.

Revisa estos campos antes de guardar:

- **Nombre**: obligatorio y único; aparece una advertencia si otro activo ya lo usa.
- **Tipo**: consulta [Elegir el tipo de activo](#choosing-the-asset-type).
- **Unidades por precio individual**: a cuántas unidades se refiere un precio, normalmente 1, y 100 para la mayoría de los bonos. Elegir un resultado de **Buscar en línea** fija ese valor, igual que fija el nombre: en el valor que sugiera el proveedor, si sugiere alguno, con una nota bajo el campo que explica por qué ([Yahoo Finance](providers/yahoo-finance.md) sugiere 100 para un valor londinense cotizado en peniques, por ejemplo), o, en caso contrario, en 100 para un **Bono** y 1 para cualquier otro tipo. También fija ese valor en **Editar activo**, sobre el valor guardado, que solo cambia cuando guardas. Escribir en el campo elimina la nota. Elegir el **Tipo** tú mismo deja el campo como está; para un **Bono**, una indicación te recuerda que los bonos suelen cotizar por 100.
- **Divisa**: la divisa en la que se cotizan los precios. Para un fondo cotizado en euros, es EUR, incluso cuando el fondo está denominado en otra divisa.

Después de guardar desde la página **Activos**, la confirmación enlaza al nuevo activo. Si el activo tiene un proveedor, su historial de precios empieza a descargarse de inmediato.

## 🔎 Resultados de la búsqueda en línea {: #search-online-results }

**Buscar en línea** consulta a todos los proveedores a la vez y ordena sus resultados a medida que llegan: primero las fuentes **premium** (aquellas que tu instancia avala, como datos con licencia), después las de la **comunidad**, y cada grupo por prioridad. Ninguno de los proveedores que vienen con LibreFolio es premium, y todos tienen la misma prioridad: los resultados aparecen según responden los proveedores, a menos que tu administrador [cambie el orden](../../admin/configuration_accounts.md#provider-order).

Cuando la búsqueda incluyó una fuente premium, la lista tiene dos partes:

- **Premium**: los resultados de las fuentes premium, o *No hay resultados de las fuentes premium.*
- **Fuentes no premium (comunidad) · N resultados**, cerrada. Al abrirla, primero se muestra una advertencia: son fuentes de terceros, LibreFolio no avala sus precios ni sus datos, y elegir una se aplica solo a este activo. La sección vuelve a estar cerrada la próxima vez que abras el formulario.

### 📨 ¿No lo encuentras? Házanoslo saber {: #let-us-know }

Una vez que una búsqueda ha terminado, sea cual sea su resultado, incluso tras un error o un tiempo de espera agotado, la lista ofrece *¿No lo encuentras?* **Házanoslo saber** (entre las dos partes, cuando hay dos), siempre que la aplicación sepa adónde enviar el informe. El informe va a quien da soporte a tu instancia. Si la lista se ha cerrado, haz clic en el cuadro de búsqueda para volver a mostrarla; vaciar el cuadro hace que se olvide la búsqueda.

Adónde lleva el enlace depende de la dirección de soporte de tu instancia; su información emergente te indica cuál es:

| Dirección de soporte | Qué hace **Házanoslo saber** |
|---|---|
| Una dirección de correo electrónico | Se abre tu aplicación de correo con un mensaje cuyo asunto y detalles ya están rellenados |
| Una página web | La página se abre en una nueva pestaña con el asunto y los detalles en su dirección, para que un formulario de soporte pueda rellenarse solo. Los detalles también se copian, listos para pegar allí; un mensaje confirma la copia o indica que ha fallado |
| Ninguna (opción predeterminada), en una instancia autoalojada | Se abre una nueva incidencia de GitHub en una pestaña nueva, ya rellenada. Es **pública**: revísala antes de enviarla |

El enlace no aparece, incluso con una dirección de soporte, cuando la aplicación no pudo leer la configuración de tu instancia; recargar la página lo intenta de nuevo.

Los detalles están en inglés: el texto que buscaste; cada proveedor consultado y su resultado (cuántos resultados, *sin respuesta*, o un error, con su código cuando lo tiene; nunca el mensaje del error); los identificadores que ya están en el formulario, y su divisa y tipo, a menos que sigan siendo los valores predeterminados de un formulario nuevo y vacío (tu divisa base y Acción); tu versión de LibreFolio, el perfil de la instancia y el idioma de la aplicación. Por lo tanto, cuando editas un activo, los detalles incluyen los identificadores propios del activo (ISIN, ticker…), su divisa y su tipo, tal como los muestra el formulario. Nunca incluyen quién eres, una dirección de correo electrónico, la dirección de tu instancia ni ningún dato de cartera. Tú mismo envías el informe, desde tu propio dispositivo: nunca pasa por el servidor de LibreFolio.

## 🗂️ Elegir el tipo de activo {: #choosing-the-asset-type }

El campo **Tipo** abre un menú con búsqueda de [tipos de activo](../../financial-theory/instruments/asset-types/index.md). **ETF** y **Crowdfunding** son familias: abre una para ver primero su miembro genérico (**ETF**, **Crowdfund**) y después los específicos, como **ETF de renta variable** o **Crowdfunding inmobiliario**. Escribe unas pocas letras para buscar en ambos niveles, por nombre o código (por ejemplo, `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Menú de tipos con la familia ETF expandida, cada tipo específico de ETF mostrando su icono compuesto">
</div>

**Buscar en línea** suele establecer un tipo general como **ETF**. Si sabes qué contiene el fondo, refínalo, por ejemplo a **ETF de renta variable**: entonces su insignia e icono muestran qué contiene. Una [comprobación posterior con los datos del proveedor](#provider-data-comparison) mantiene tu elección.

## 🔌 Conectar un proveedor de precios

Elegir un resultado de **Buscar en línea** conecta su proveedor por ti. Para configurar uno manualmente, expande **Asignación de proveedor** (desmarca primero **Sin proveedor** si está marcado):

1. Elige el **Proveedor** y, después, introduce el **Identificador**, su **Tipo de identificador** y cualquier configuración que solicite el proveedor.
2. Haz clic en **Probar configuración**: LibreFolio obtiene un **Precio actual** y unos pocos días de **Historial**. ⚠️ significa que el proveedor no ofrece esos datos o no tiene ninguno ahora mismo (CSS Scraper no tiene historial, por ejemplo); la prueba se supera igualmente. ❌ es un error: revisa el identificador y la configuración. Cuando **Historial** responde, aunque sea con ⚠️, una nota recuerda que la prueba solo lee los últimos días: un activo nuevo recibe todo su historial de precios cuando se crea.

⚠️ *En pausa por demasiadas solicitudes hasta …* significa que el proveedor ha rechazado las solicitudes de LibreFolio porque había demasiadas: LibreFolio no vuelve a intentarlo hasta la hora mostrada, en tu hora local, con la fecha si la pausa termina otro día. Es posible que tu configuración sea correcta, así que la prueba se supera igualmente. Cuando no se conoce el final de la pausa, ves *Demasiadas solicitudes: inténtalo más tarde*. Mientras tanto, la lista de Activos y la página del activo siguen mostrando el último precio guardado.

Un activo tiene como máximo un proveedor; marca **Sin proveedor** si vas a introducir sus precios tú mismo. Consulta [Proveedores](providers/index.md) para saber qué ofrece cada uno.

## ⚖️ Comprobar los datos del proveedor {: #provider-data-comparison }

LibreFolio compara los detalles del proveedor con tu formulario después de que elijas un resultado de **Buscar en línea**, y cuando haces clic en **Preguntar al proveedor**: en la parte superior de **Detalles del activo** para todo, junto a **Identificadores** o en un editor de distribución solo para esa parte. Necesita un proveedor y un identificador.

- Los campos vacíos se rellenan, y los códigos adicionales del proveedor se añaden a **Otros identificadores**.
- *El proveedor no tiene datos para: …* indica una distribución sectorial o geográfica que falta; *Todos los datos coinciden con el proveedor* significa que no hay nada que revisar.
- Cualquier diferencia abre el diálogo **Comparación de datos del proveedor**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-provider-compare" alt="El diálogo Comparación de datos del proveedor sobre el formulario Añadir activo: la fila TICKER preguntando cuál es el código principal, con el código del proveedor elegido en lugar del ya guardado, que se conserva como alternativo; la fila Tipo con sus valores actual y del proveedor como insignias de icono; la fila Distribución sectorial, actual frente a proveedor; y Seleccionar todo, Deseleccionar todo, Cancelar y Aplicar seleccionados">
</div>

Cada fila del diálogo muestra tu **Valor actual** junto al **Valor del proveedor**, y empieza marcada:

1. Desmarca las filas en las que quieras conservar tu valor (**Seleccionar todo** y **Deseleccionar todo** te ayudan).
2. En una fila de identificador, elige el código principal; el otro se conserva en **Otros identificadores** (consulta [Editar identificadores](#one-instrument-several-codes)). Se propone el código del proveedor, ya que normalmente es el cotizado.
3. Haz clic en **Aplicar seleccionados**, que cuenta las filas que aceptas (por ejemplo, *Aplicar seleccionados (2/3)*), o en **Cancelar** para no cambiar nada.

Los valores aceptados solo rellenan el formulario: se guardan cuando guardas el activo.

- **Tu tipo refinado se conserva.** Borsa Italiana, por ejemplo, clasifica todos los instrumentos de ETFplus simplemente como **ETF**: si elegiste **ETF de renta variable**, eso cuenta como coincidencia y no aparece ninguna fila (lo mismo ocurre con **Crowdfunding**). Un tipo *más específico* que el tuyo se sigue ofreciendo.
- **Cada pregunta se hace una vez.** Cuando un resultado de búsqueda trae un ISIN (u otro código) distinto del que hay en el formulario, LibreFolio primero pregunta cuál es el principal, y la comparación no vuelve a preguntar.
- **Las unidades por precio individual se proponen, nunca se rellenan.** Una comprobación completa (tras elegir un resultado de búsqueda, o con **Preguntar al proveedor** en la parte superior de **Detalles del activo**) compara ese valor con la sugerencia del proveedor o, si no la hay, con 100 para un bono y 1 para cualquier otro tipo (el tipo que proponga el proveedor, si propone otro). Una diferencia es una fila marcada en **Detalles del activo**, con una nota que indica el motivo: la sugerencia del proveedor, o que los bonos suelen cotizar por 100 (una fila que proponga el 1 habitual no tiene ninguna). Desmárcala para conservar tu valor. Si una comprobación vuelve sin la sugerencia del proveedor (por ejemplo, porque tardó demasiado), la que dio antes para el mismo proveedor e identificador, en el resultado de búsqueda o en una comprobación anterior, sigue contando: LibreFolio no propone deshacerla.

## 🛠️ Editar un activo {: #editing-an-asset }

En la [página de detalles](detail/index.md) del activo, haz clic en **Editar** (✏️), cambia lo que necesites en el formulario **Editar activo** y haz clic en **Guardar cambios**.

### 💱 Cambiar la divisa {: #changing-the-currency }

Siempre se permite una nueva **Divisa**, pero los precios y los eventos se guardan en la divisa en la que se cotizaron, así que los anteriores no pueden quedarse junto a los nuevos. Cambiar la divisa elimina parte de lo que está guardado para el activo y conserva el resto:

| Guardado para el activo | Después del cambio |
|----------------------|------------------|
| Su **historial de precios** | Se elimina |
| Sus **dividendos, intereses y otros eventos**, tanto los que introdujiste como los que generó el proveedor | Se eliminan |
| Tus **transacciones** | Siempre **se conservan**. Las que están vinculadas a un evento eliminado se quedan, pero pierden ese vínculo |
| Sus **desdoblamientos** | **Se conservan**, y también las transacciones vinculadas a ellos: los ajustes de un desdoblamiento conservan su vínculo y su coste |

Los desdoblamientos son una proporción, no una cantidad de dinero, así que significan lo mismo en cualquier divisa.

Antes de guardar nada, el formulario pregunta al servidor qué se eliminaría. Si la respuesta no se puede leer, el formulario muestra el error y no guarda nada. Si no se eliminaría nada (el activo aún no tiene precios, eventos ni transacciones vinculadas), el cambio simplemente se guarda. Si se eliminaría algo, un diálogo **Cambiar divisa del activo** lo enumera:

- los **puntos de precio** que se eliminarán, con el periodo que cubren;
- los **eventos manuales** y los **eventos generados por el proveedor** que se eliminarán;
- las transacciones que **pierden su vínculo con un evento eliminado** (las transacciones en sí se conservan);
- los **eventos de desdoblamiento** que se quedan, con las transacciones vinculadas a ellos.

No se elimina nada hasta que hagas clic en **Eliminar y cambiar divisa**; **Cancelar** deja el activo como estaba. El diálogo también te permite descargar primero una **copia de seguridad** de los precios y de los eventos (CSV o JSON), cuando los haya.

Después del cambio, si el activo tiene un proveedor y tenía precios, se descargan de nuevo del proveedor, desde la fecha más antigua que tenías, en la nueva divisa. Sin proveedor, vuelves a importar los precios tú mismo. Las transacciones que perdieron el vínculo con un evento se pueden volver a vincular de una vez: consulta [Volver a vincular eventos](../transactions/index.md#relink-events).

Cambiar o quitar el proveedor tiene sus propias reglas, que se explican a continuación.

### 🔄 Cambiar o quitar el proveedor {: #changing-or-removing-the-provider }

Algunos cambios de proveedor descartan datos que LibreFolio tenía guardados. Antes de guardar, el formulario pregunta al servidor qué se eliminaría y, si se eliminaría algo, muestra **una** confirmación que da las cifras. No se elimina nada hasta que confirmes; **Cancelar** deja el activo como estaba.

| Qué cambias | Qué se elimina |
|-----------------|-----------------|
| Nueva configuración de un plan de [Inversión programada](providers/scheduled-investment.md) | Todos los precios del activo y los eventos que generó el plan: se generan de nuevo a partir de la nueva configuración |
| Otro proveedor, cuando el activo estaba en un plan de Inversión programada | Lo mismo: todos los precios y los eventos que generó el plan; después, el nuevo proveedor proporciona el historial |
| **Sin proveedor** | Los eventos que generó el proveedor (sus dividendos, desdoblamientos o cupones). Los precios que ya tienes se **conservan** |
| Otro proveedor en línea, o nueva configuración para uno en línea (Yahoo Finance, justETF…); un primer proveedor para un activo que no tenía ninguno | Nada, y no se hace ninguna pregunta |

Por ejemplo, al cambiar de un plan a Yahoo Finance se pregunta:

> El historial de este activo fue generado por Inversión programada. Cambiar a Yahoo Finance
> elimina 1.240 puntos de precio y 6 eventos generados por el proveedor. 3 transacciones pierden su
> vínculo con un evento eliminado (las transacciones en sí se conservan). […] Los eventos manuales se conservan.
> Esto no se puede deshacer. ¿Continuar?

Qué significa el diálogo:

- **Los puntos de precio y los eventos** se cuentan tal como están guardados ahora mismo. Los precios incluyen cualquiera que hayas introducido tú mismo, cuando cambian la configuración de un plan o el proveedor; con **Sin proveedor** se quedan.
- **Las transacciones nunca se eliminan.** Una transacción que registraste para un evento eliminado, como un dividendo o un cupón, se queda en tu cartera pero pierde su vínculo: su campo **Evento vinculado** queda vacío. El diálogo cuenta todas esas transacciones, incluidas las de brókers que no puedes ver, y no las nombra.
- **Los eventos que añadiste tú mismo se quedan**, con sus vínculos.
- Si no se perdería nada, o no se pudo obtener el recuento, el formulario guarda sin diálogo.

⚠️ **Un caso se rechaza.** Si un desdoblamiento generado por el proveedor tiene ajustes vinculados sin un [coste de compra](../transactions/form.md), no se realizan el cambio ni la eliminación: sin el desdoblamiento, esas unidades contarían como compradas a un precio desconocido. El formulario muestra el mensaje en lugar del diálogo, nombra el desdoblamiento por su fecha, y el resto de tu edición se guarda. Asigna un coste de compra a esos ajustes y después vuelve a cambiar el proveedor.

## 🏷️ Editar identificadores {: #one-instrument-several-codes }

Un valor puede tener varios códigos. LibreFolio mantiene **un solo activo** con todos ellos, en **Más información** del formulario del activo:

- **Identificadores**: los códigos principales, uno por tipo (ISIN, ticker…). **Añadir identificador** añade una fila y **Preguntar al proveedor** los obtiene.
- **Otros identificadores**: cualquier código adicional o etiqueta de bróker. Escribe uno y pulsa Intro, coma, punto y coma o Tabulador. Estos códigos se pueden buscar y ayudan a reconocer el activo en importaciones posteriores.

!!! tip "Mantén el código cotizado como ISIN principal"

    Un precio es el valor de la última operación, así que solo un código negociable tiene precio. Pon ese código en
    **ISIN** y todo lo demás en **Otros identificadores**, o ningún proveedor podrá ponerle precio al activo.

### 🏛️ Bonos del Estado italianos para inversores minoristas (BTP Valore, BTP Più, BTP Italia)

Estos bonos se suscriben con un ISIN y se negocian con otro:

| Fase | Código | Qué hace |
|---|---|---|
| Suscripción en la emisión | el ISIN "CUM" | Te da derecho a la **prima de fidelidad** si mantienes el bono hasta el vencimiento. **No es negociable**, así que ningún proveedor lo cotiza |
| Mercado secundario | un ISIN diferente | Se negocia libremente y **se cotiza**: este es el que tiene precio |

Para vender antes del vencimiento, el bono se convierte al código de mercado. Mantén ambos códigos en un mismo activo:

1. Pon el **ISIN de mercado** en **ISIN**.
2. Pon el **ISIN CUM** en **Otros identificadores**.
3. Registra la **prima de fidelidad**, cuando se pague, como una transacción de **Interés** en ese activo. Esto también funciona después del vencimiento: un activo desactivado sigue siendo seleccionable.

Cuando una importación trae el código CUM para un activo que tiene el de mercado, LibreFolio pregunta cuál debe ser el código principal y conserva el otro en **Otros identificadores**.

## 🗺️ Configurar distribuciones por sector y país

Los proveedores rellenan las distribuciones sectoriales y geográficas cuando pueden; para otros activos, configúralas tú mismo. Alimentan los gráficos de asignación del panel y la exportación IA.

En el formulario del activo, expande **Más información**: en **Clasificación**, **Distribución sectorial** y **Distribución geográfica** se muestra una fila por sector o país, con su peso en porcentaje.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Distribución sectorial" alt="Editor de distribución sectorial en el modal del activo">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Distribución geográfica" alt="Editor de distribución geográfica en el modal del activo">
</div>

- **Añadir sector** / **Añadir país** añade una fila: elige la entrada y después escribe su peso.
- El **Total** se vuelve verde al 100%, ámbar cuando falta algo y rojo cuando te pasas.
- **Equilibrar al 100%**, una acción de fila, traslada toda la diferencia a esa fila. **Equilibrar filas seleccionadas** la reparte entre las filas seleccionadas, en proporción a sus pesos.
- **Eliminar** borra una fila, **Preguntar al proveedor** obtiene la distribución del proveedor y **Importar CSV** carga una desde un archivo.

### 📥 Importar una distribución desde CSV {: #importing-a-distribution-csv }

**Importar CSV** espera una cabecera `name,weight` y después una fila por país o sector, con los pesos en porcentaje:

```csv
name,weight
USA,60
Italy,40
```

- Los **nombres** deben coincidir exactamente, ignorando mayúsculas y minúsculas y los espacios de alrededor. Países: un código ISO (`IT`, `ITA`) o el nombre en tu idioma. Sectores: la clave del sector (como `Government Bonds`) o el nombre en tu idioma.
- Los **pesos** van de `0` a `100` y deben sumar 100 (con una tolerancia de 0,005 puntos); cada nombre aparece una vez.
- La importación es **todo o nada**: una fila incorrecta la bloquea. Cuando tiene éxito, **reemplaza** toda la distribución.

!!! warning "Comas decimales"

    El separador, `,` o `;`, se lee de la cabecera. Con `,`, la fila `Italy,12,5` se lee
    sin avisar como `12`. Usa `;` en todo (`name;weight`, luego `Italy;12,5`), entrecomilla el valor
    (`Italy,"12,5"`), o escribe `Italy,12.5`.

## 🧲 Fusionar activos duplicados

Si el mismo instrumento acabó como dos activos, cada uno contiene parte de su historial. Para integrar uno en el otro:

1. En la página **Activos**, usa **Fusionar con…** en el activo que deba desaparecer: el botón de su tarjeta o el menú contextual de la tabla.
2. Elige el activo que quieres conservar (también los inactivos) y haz clic en **Continuar**. En un día en que ambos tengan precio, prevalece el precio del activo conservado; también prevalece su proveedor de precios, si tiene uno.
3. Lee **Qué se traslada**: los recuentos exactos de transacciones, precios y eventos. Cuando ambos activos tengan un código diferente del mismo tipo, elige el que deba ser el principal.
4. Haz clic en **Fusionar y eliminar**. El primer activo se elimina; esto no se puede deshacer.

No se pierde ningún identificador: cada código del activo eliminado rellena un campo vacío del activo conservado o se añade a sus **Otros identificadores**. Los eventos idénticos se fusionan.

Durante una importación, cuando dos de tus activos llevan el ISIN de un valor, su tarjeta **Resolver activos** indica *Dos activos guardados coinciden con este valor* y ofrece **Fusionar**. El mero hecho de que los nombres coincidan nunca lo activa.

## 🔗 Relacionado

- 📊 **[Página de detalles del activo](detail/index.md)** — Consulta y analiza los datos del activo
- 🔌 **[Proveedores](providers/index.md)** — Proveedores de precios disponibles
- 🧬 **[Identidad del activo](../../developer/frontend/components/features/asset-identity.md)** — Para desarrolladores: cómo funcionan los identificadores, las comparaciones de proveedores y las fusiones
