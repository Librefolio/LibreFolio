# ➕ Crear y editar activos

Añade un instrumento que poseas o sigas, conéctalo a un proveedor de precios y mantén sus datos correctos.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-create" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="create-modal" data-title="➕ Formulario de creación manual" alt="Formulario de creación manual">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="create-wizard-modal" data-title="🧙 Formulario de autocreación del asistente de importación" alt="Crear activo desde el asistente">
</div>

## 🚀 Crear un activo {: #asset-creation-flows }

=== "Desde la página Activos"

    1. En la página **Activos**, haz clic en **+ Añadir activo**.
    2. En **Buscar en línea**, escribe un nombre, un ticker o un ISIN y elige un resultado: LibreFolio rellena el
       formulario, conecta ese proveedor y [comprueba sus datos](#provider-data-comparison). ¿No hay resultados?
       Rellena el formulario tú mismo.
    3. Revisa los campos de abajo y haz clic en **Crear activo**.

=== "Desde una importación de bróker"

    1. En la sección **Resolver activos** del asistente de importación, elige **Crear nuevo activo** en el
       selector del valor.
    2. El formulario se abre con los códigos y nombres del informe. Si el informe no tiene nombre, **Nombre**
       empieza por el ISIN (o el ticker).
    3. Haz clic en una de las **Sugerencias** bajo **Buscar en línea** para buscar el valor, o rellena
       el formulario tú mismo. Después, haz clic en **Crear activo**.

    Si el resultado que eliges tiene el mismo nombre que uno de tus activos, LibreFolio te ofrece usar ese
    activo en su lugar; **Usarlo y añadir la clave** también guarda los códigos del informe en él.

Revisa estos campos antes de guardar:

- **Nombre**: obligatorio y único; aparece un aviso si otro activo ya lo usa.
- **Tipo**: consulta [Elegir el tipo de activo](#choosing-the-asset-type).
- **Unidades por precio**: a cuántas unidades se refiere un precio, normalmente 1. Los bonos se cotizan por
  100: LibreFolio lo propone cuando eliges **Bono**.
- **Divisa**: la divisa en la que se cotizan los precios. Para un fondo cotizado en euros, es EUR,
  aunque el fondo esté denominado en otra divisa.

Tras guardar desde la página **Activos**, la confirmación enlaza con el nuevo activo. Si el activo tiene un
proveedor, su historial de precios empieza a descargarse de inmediato.

## 🗂️ Elegir el tipo de activo {: #choosing-the-asset-type }

El campo **Tipo** abre un menú con búsqueda de
[tipos de activo](../../financial-theory/instruments/asset-types/index.md). **ETF** y
**Crowdfunding** son familias: abre una para ver primero su miembro genérico (**ETF**, **Crowdfund**)
y después los específicos, como **Equity ETF** o **Real estate crowdfunding**. Escribe unas letras para
buscar en ambos niveles, por nombre o por código (por ejemplo, `etf_bond`).

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="type-picker-open" alt="Menú de tipos con la familia ETF expandida, cada tipo de ETF específico mostrando su icono compuesto">
</div>

**Buscar en línea** normalmente asigna un tipo general como **ETF**. Si sabes qué contiene el fondo,
refínalo, por ejemplo a **Equity ETF**: su distintivo e icono mostrarán entonces lo que contiene. Una
[comprobación posterior con los datos del proveedor](#provider-data-comparison) respeta tu elección.

## 🔌 Conectar un proveedor de precios

Elegir un resultado de **Buscar en línea** conecta su proveedor por ti. Para configurarlo a mano, despliega
**Asignación de proveedor** (desmarca antes **Sin proveedor** si está marcado):

1. Elige el **Proveedor** e introduce el **Identificador**, su **Tipo de identificador** y cualquier configuración
   que pida el proveedor.
2. Haz clic en **Probar configuración**: LibreFolio obtiene un **Precio actual** y unos días de
   **Historial**. ⚠️ significa que el proveedor no ofrece esos datos o ahora mismo no tiene ninguno (CSS Scraper
   no tiene historial, por ejemplo); la prueba se supera igualmente. ❌ es un error: revisa el identificador y
   la configuración.

Un activo tiene como máximo un proveedor; marca **Sin proveedor** si vas a introducir tú mismo sus precios. Consulta
[Proveedores](providers/index.md) para saber qué ofrece cada uno.

## ⚖️ Comprobar los datos del proveedor {: #provider-data-comparison }

LibreFolio compara los datos del proveedor con tu formulario después de elegir un resultado de **Buscar en línea**
y cuando haces clic en **Consultar al proveedor**: en la parte superior de **Detalles del activo** para todo,
junto a **Identificadores** o en un editor de distribuciones solo para esa parte. Necesita un proveedor y un
identificador.

- Los campos vacíos se rellenan, y los códigos adicionales del proveedor se añaden a **Otros identificadores**.
- *El proveedor no tiene datos para: …* indica la distribución sectorial o geográfica que falta; *Todos los datos coinciden
  con el proveedor* significa que no hay nada que revisar.
- Todo lo que difiere abre el diálogo **Comparación de datos del proveedor**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="create-provider-compare" alt="El diálogo Comparación de datos del proveedor sobre el formulario Añadir activo: la fila TICKER preguntando qué código es el principal, con el código del proveedor elegido frente al ya guardado, que se conserva como alternativo; la fila Tipo con sus valores actual y del proveedor como distintivos de icono; la fila Distribución sectorial, actual frente al proveedor; y Seleccionar todo, Deseleccionar todo, Cancelar y Aplicar seleccionados">
</div>

Cada fila del diálogo muestra tu **Valor actual** junto al **Valor del proveedor**, y empieza marcada:

1. Desmarca las filas en las que quieras conservar tu valor (**Seleccionar todo** y **Deseleccionar todo** te ayudan).
2. En una fila de identificador, elige el código principal; el otro se conserva en **Otros identificadores** (consulta
   [Editar identificadores](#one-instrument-several-codes)). Se propone el código del proveedor, ya que normalmente es
   el cotizado.
3. Haz clic en **Aplicar seleccionados**, que cuenta las filas que aceptas (por ejemplo, *Aplicar seleccionados (2/3)*),
   o en **Cancelar** para no cambiar nada.

Los valores aceptados solo rellenan el formulario: se guardan cuando guardas el activo.

- **Tu tipo refinado se conserva.** Borsa Italiana, por ejemplo, informa todos los instrumentos de ETFplus como
  **ETF** sin más: si elegiste **Equity ETF**, eso cuenta como coincidencia y no aparece ninguna fila (lo mismo
  ocurre con **Crowdfunding**). Un tipo *más específico* que el tuyo sí se ofrece.
- **Cada pregunta se hace una sola vez.** Cuando un resultado de búsqueda trae un ISIN (u otro código) distinto
  del que hay en el formulario, LibreFolio pregunta primero cuál es el principal, y la comparación no vuelve a
  preguntarlo.

## 🛠️ Editar un activo {: #editing-an-asset }

En la [página de detalle](detail/index.md) del activo, haz clic en **Editar** (✏️), cambia lo que necesites en el
formulario **Editar activo** y haz clic en **Guardar cambios**.

Una **Divisa** nueva para un activo que ya tiene precios implica eliminar sus precios y eventos almacenados: al
guardar, un diálogo enumera lo que se elimina (las transacciones se mantienen) y ofrece una copia de seguridad. Tras
**Eliminar y cambiar divisa**, los precios se vuelven a descargar del proveedor, si lo hay.

## 🏷️ Editar identificadores {: #one-instrument-several-codes }

Un mismo valor puede tener varios códigos. LibreFolio mantiene **un solo activo** con todos ellos, en
**Más información** del formulario del activo:

- **Identificadores**: los códigos principales, uno por tipo (ISIN, ticker…). **Añadir identificador** añade una fila y
  **Consultar al proveedor** los obtiene.
- **Otros identificadores**: cualquier código extra o etiqueta del bróker. Escribe uno y pulsa Intro, coma, punto y coma
  o Tabulador. Estos códigos son buscables y ayudan a reconocer el activo en importaciones posteriores.

!!! tip "Mantén el código cotizado como ISIN principal"

    Un precio es el valor de la última negociación, así que solo un código negociable tiene precio. Pon ese código en
    **ISIN** y todo lo demás en **Otros identificadores**, o ningún proveedor podrá poner precio al activo.

### 🏛️ Bonos del Estado italianos para minoristas (BTP Valore, BTP Più, BTP Italia)

Estos bonos se suscriben con un ISIN y se negocian con otro:

| Fase | Código | Qué hace |
|---|---|---|
| Suscripción en la emisión | el ISIN «CUM» | Te da derecho a la **prima de fidelidad** si mantienes el bono hasta el vencimiento. **No es negociable**, así que ningún proveedor lo cotiza |
| Mercado secundario | un ISIN distinto | Se negocia libremente y **se cotiza**: este es el que tiene precio |

Para vender antes del vencimiento, el bono se convierte al código de mercado. Mantén ambos códigos en un mismo activo:

1. Pon el **ISIN de mercado** en **ISIN**.
2. Pon el **ISIN «CUM»** en **Otros identificadores**.
3. Registra la **prima de fidelidad**, cuando se pague, como una transacción de **Interés** en ese activo.
   Esto también funciona después del vencimiento: un activo desactivado sigue siendo seleccionable.

Cuando una importación trae el código «CUM» para un activo que ya tiene el de mercado, LibreFolio pregunta qué
código debe encabezar y conserva el otro en **Otros identificadores**.

## 🗺️ Configurar las distribuciones por sector y país

Los proveedores rellenan las distribuciones sectorial y geográfica cuando pueden; para otros activos, configúralas
tú mismo. Alimentan los gráficos de asignación del panel y la exportación IA.

En el formulario del activo, despliega **Más información**: en **Clasificación**, **Distribución sectorial** y
**Distribución geográfica** listan una fila por sector o país, con su peso en porcentaje.

<div class="lf-screenshot-carousel" data-carousel="carousel-assets-distribution-editors" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="assets" data-name="distribution-editor-sector" data-title="🏭 Distribución sectorial" alt="Editor de distribución sectorial en el modal del activo">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="distribution-editor-geographic" data-title="🌍 Distribución geográfica" alt="Editor de distribución geográfica en el modal del activo">
</div>

- **Añadir sector** / **Añadir país** añade una fila: elige la entrada y luego escribe su peso.
- El **Total** se pone verde al 100 %, ámbar cuando falta algo y rojo cuando te pasas.
- **Equilibrar al 100 %**, una acción de fila, traslada toda la diferencia a esa fila. **Equilibrar filas seleccionadas**
  la reparte entre las filas seleccionadas, en proporción a sus pesos.
- **Eliminar** borra una fila, **Consultar al proveedor** obtiene la distribución del proveedor e **Importar CSV**
  carga una desde un archivo.

### 📥 Importar una distribución desde CSV {: #importing-a-distribution-csv }

**Importar CSV** espera una cabecera `name,weight` y luego una fila por país o sector, con los pesos en
porcentaje:

```csv
name,weight
USA,60
Italy,40
```

- Los **nombres** deben coincidir exactamente, sin distinguir mayúsculas y minúsculas ni espacios alrededor. Países: un código
  ISO (`IT`, `ITA`) o el nombre en tu idioma. Sectores: la clave del sector (como `Government Bonds`)
  o el nombre en tu idioma.
- Los **pesos** van de `0` a `100` y deben sumar 100 (con un margen de 0,005 puntos); cada nombre aparece
  una sola vez.
- La importación es **todo o nada**: una fila incorrecta la bloquea. Cuando tiene éxito, **reemplaza** toda
  la distribución.

!!! warning "Comas decimales"

    El separador, `,` o `;`, se lee de la cabecera. Con `,`, la fila `Italy,12,5` se lee
    silenciosamente como `12`. Usa `;` en todo (`name;weight`, y luego `Italy;12,5`), entrecomilla el valor
    (`Italy,"12,5"`) o escribe `Italy,12.5`.

## 🧲 Fusionar activos duplicados

Si el mismo instrumento acabó como dos activos, cada uno guarda parte de su historial. Para integrar uno en
el otro:

1. En la página **Activos**, usa **Fusionar con…** en el activo que debe desaparecer: el botón de su tarjeta
   o el menú del clic derecho en la tabla.
2. Elige el activo que quieres conservar (también los inactivos) y haz clic en **Continuar**. En un día en que ambos
   tengan precio, gana el precio del activo conservado; también gana su proveedor de precios, si tiene uno.
3. Lee **Qué se traslada**: los recuentos exactos de transacciones, precios y eventos. Cuando ambos activos
   tengan un código distinto del mismo tipo, elige el que encabeza.
4. Haz clic en **Fusionar y eliminar**. El primer activo se elimina; esto no se puede deshacer.

No se pierde ningún identificador: cada código del activo eliminado rellena un campo vacío del conservado o se añade a
sus **Otros identificadores**. Los eventos idénticos se fusionan.

Durante una importación, cuando dos de tus activos llevan el ISIN de un valor, su tarjeta **Resolver activos**
dice *Dos activos guardados coinciden con este valor* y ofrece **Fusionar**. Que los nombres coincidan por sí solos
nunca lo activa.

## 🔗 Relacionado

- 📊 **[Página de detalle del activo](detail/index.md)** — Consulta y analiza los datos del activo
- 🔌 **[Proveedores](providers/index.md)** — Proveedores de precios disponibles
- 🧬 **[Identidad del activo](../../developer/frontend/components/features/asset-identity.md)** — Para desarrolladores: cómo funcionan los identificadores, las comparaciones de proveedores y las fusiones
