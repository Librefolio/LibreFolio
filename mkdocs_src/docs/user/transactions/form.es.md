# 📝 Formulario de transacción

El formulario de transacción añade o edita una transacción —o un par vinculado— en el [espacio de trabajo masivo](index.md#bulk-workspace). También muestra una transacción en modo de solo lectura cuando haces doble clic en ella en una lista. Solo aparecen los campos que necesita el tipo elegido.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> COMPRA' alt="Compra">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENTA' alt="Venta">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDO' alt="Dividendo">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DEPÓSITO' alt="Depósito">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> AJUSTE' alt="Ajuste">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERENCIA' alt="Transferencia de activos">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSIÓN FX' alt="Conversión FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFERENCIA DE FONDOS' alt="Transferencia de fondos">
</div>

---

## ✍️ Rellenar el formulario

1. Elige el **Tipo** y después el **Bróker**, si aún no está establecido.
2. Completa la sección **Obligatorio**: la **Fecha**, el **Activo** y su cantidad cuando el tipo la tenga, y el importe en efectivo.
3. Abre **Opcional** para las **Etiquetas**, una **Descripción** o, en dividendos, intereses y ajustes, un **Evento vinculado**.
4. Haz clic en **Aplicar** para colocar la fila en el espacio de trabajo; **Guardar todo** en el espacio de trabajo la guarda.

Algunas reglas agilizan la introducción:

- **Los importes son totales** — el importe que guardas es el total pagado o recibido, nunca el precio por acción (*Importe total (no por acción)*). En una compra o una venta puedes escribir cualquiera de los dos: el total o el precio unitario (los botones junto al campo indican cuál), y el formulario calcula el otro — consulta [Total o precio unitario](#unit-price).
- **Escribe números positivos** — el formulario añade el signo menos donde sale dinero o unidades: el pago de una compra, las unidades de una venta, un retiro, una comisión, un impuesto. Solo la cantidad de un **Ajuste** lleva signo: positiva añade unidades, negativa las quita.
- **Comprobaciones sobre la marcha** — una vez rellenados los campos obligatorios, el formulario comprueba la entrada con tu libro mayor y las demás filas del espacio de trabajo, y enumera cualquier problema en la parte superior. El formulario también detecta por sí solo algunos errores: una fecha que no puede leer, o una en el futuro, permanece en pantalla en rojo, y no se usa la fecha anterior en su lugar; una cantidad o un importe con el signo o el formato incorrectos, como una cantidad negativa en una compra, se marca en rojo; y un aviso en la parte superior señala una transferencia con el mismo bróker en ambos lados, o un cambio de divisas con la misma divisa. Hasta que los corrijas, no se comprueba nada, no aparece *válido* y **Aplicar** permanece deshabilitado. **⚡ Validar ahora** los encuentra todos a la vez — consulta [Validar ahora](#validate-now). Las fechas de transacción pueden remontarse hasta el año 1 y llegar hasta mañana, pero el formulario en sí no pasa de hoy. Una fecha anterior a 1900 casi siempre es un error tipográfico, así que el formulario te muestra un aviso ámbar y **Aplicar** permanece deshabilitado hasta que pulses **Sí, la fecha es correcta**; si cambias la fecha, vuelve a preguntar, y una vez confirmada, la fecha se guarda como cualquier otra. Una fecha posterior a mañana se rechaza con un mensaje como *Fecha: No posterior a 2026-10-18*, cuando hoy es 17 de octubre de 2026.
- **¿Falta el bróker o el activo?** — **Crear nuevo** en la lista de brókers, o **Nuevo activo** en la lista de activos, lo crea sin salir del formulario.
- **¿Falta un evento?** — **+ Nuevo evento** en el campo **Evento vinculado** crea el evento del activo y lo vincula. Si el activo ya tiene un evento de ese tipo en esa fecha, no se guarda nada: la ventana muestra ese evento, para usarlo, o para editarlo si lo introdujiste a mano, y nunca lo sobrescribe ([Nuevo evento desde una transacción](../assets/detail/events.md#new-event)).

<div id="cost-basis"></div>

??? info "💰 Coste base de las unidades entrantes — para Ajustes y Transferencias de activos"

    Cuando un **Ajuste** añade unidades, o en el lado receptor de una **Transferencia de activos**, el formulario pregunta cuánto costaron esas unidades:

    - **Automático** — LibreFolio lo calcula como un [precio medio de compra (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md); pulsa **⚡ Validar ahora** para verlo.
    - **Manual** — lo escribes tú.

    Un **Ajuste** que quita unidades no pide coste: no tiene valor. Las unidades solo salen de la cantidad, y lo que costaron cuenta como una pérdida realizada. Para registrar una venta, usa una **Venta**.

    En **Automático**, el PMC se calcula en el bróker de origen de una transferencia, o en el bróker del propio ajuste. Si ese bróker no tiene ninguna unidad del activo el día en que las unidades salen o entran, o solo tiene unidades cuyo coste es desconocido, no hay nada con lo que calcular el PMC: se rechaza **Automático** y no se guarda nada — elige **Manual** y escribe cuánto te costaron esas unidades (0 para un regalo). En **Manual**, el campo no puede quedar vacío: LibreFolio marca la fila y no guarda nada hasta que lo rellenes o cambies a **Automático**; un coste negativo se rechaza de la misma forma — escribe 0 o más. Editar una transacción guardada no es una excepción: si dejas vacío su coste en **Manual**, se rechaza el guardado, porque la transacción necesita un coste base — elige **Automático** o escribe un valor. Escribe 0 para las nuevas acciones de un desdoblamiento de acciones. Para un regalo, en lugar de 0, puedes escribir lo que el donante pagó por esas unidades: así el PMC y la ganancia que te pueden gravar se mantienen más cerca de los valores reales. Las unidades introducidas con un coste de 0 cuentan como gratuitas, no como desconocidas: un PMC **Automático** posterior en su bróker las cuenta a 0. Si falta un tipo de cambio, el enlace **Sincronizar tipos FX** lo obtiene.

---

## 🧮 Total o precio unitario {: #unit-price }

En una **Compra** o una **Venta** (y en cualquier otro tipo individual que tenga tanto una cantidad como un importe en efectivo), la etiqueta del campo de efectivo tiene dos botones pequeños, **Total** y **Precio unitario**. El formulario sigue siendo un único importe y su divisa: los botones solo indican **cómo leer el número que escribiste** en ese campo.

- **Total** (el valor predeterminado) — el número es el importe pagado o recibido. Debajo del campo, el formulario muestra el precio unitario que calcula: *= 83,40 por unidad*.
- **Precio unitario** — el número es el precio de una unidad. Debajo del campo, el formulario muestra el total que calcula: *= 1.000,80 en total*.

Al cambiar de botón se conserva el número que escribiste y se lee de la otra forma. Lo que se guarda es siempre el **total**: con **Precio unitario** activado, el total que se muestra debajo del campo es el que pasa a la transacción. Cuando abres una transacción guardada, el campo muestra el total, con los botones en **Total**.

El cálculo lo hace el propio formulario, de inmediato, sobre los dígitos exactos que escribiste (sin errores de redondeo de números en coma flotante). Usa la misma convención de precios que el resto de la aplicación: la cantidad se divide por el *precio por N unidades* del activo y se multiplica por el precio, de modo que un bono cotizado por 100 funciona tal como se lee su cotización (*= 98,55 por 100 unidades*). El resultado se redondea a lo que se almacena: los importes conservan 6 decimales y los precios unitarios, 12. Los empates se redondean al dígito par (*half-even*). Un valor demasiado largo se marca en rojo, como de costumbre. El precio unitario está en la misma divisa que el importe. El activo y la cantidad deben estar rellenados; sin ellos no se calcula nada y el campo muestra su indicación habitual (qué introducir).

!!! example "Ejemplo"

    Compraste 12 acciones a 83,40. Pulsa **Precio unitario**, escribe *83,40* en el campo de efectivo y debajo leerás *= 1.000,80 en total*. Tu bróker te cobró en realidad 1.000,90: pulsa **Total**, escribe *1.000,90* y debajo leerás *= 83,408333333333 por unidad*. El importe guardado es *1.000,90*.

Cuando abres una transacción guardada solo para consultarla, ves el total y, debajo, el precio unitario calculado a partir del total y la cantidad. Los botones solo aparecen mientras puedes editar.

Los tipos sin cantidad o sin importe, las transferencias y los cambios de divisas no tienen botones. La cuadrícula del [editor masivo](index.md#bulk-workspace) todavía no los tiene.

---

## ⚡ Validar ahora {: #validate-now }

**⚡ Validar ahora** siempre se puede pulsar, incluso en un formulario que acabas de abrir. Púlsalo cuando quieras saber qué falta todavía o qué está mal. Funciona igual para una transacción individual, un par de transferencia y un cambio de divisas.

Cuando lo pulsas, examina el formulario en dos pasos, antes de que nada salga de tu ordenador:

1. **Campos obligatorios** — la fecha, el bróker, el activo y su cantidad cuando el tipo la tenga, y el importe en efectivo. Para un par, también comprueba el otro lado: el bróker receptor y la segunda fecha; y, para un cambio de divisas, ambos importes y ambas divisas.
2. **Lo que escribiste** — una fecha que no se puede leer, una cantidad o un importe que no es un número válido o tiene demasiados dígitos, un signo incorrecto, o la misma divisa o el mismo bróker en ambos lados.

Cada celda incorrecta se vuelve roja de inmediato:

- un valor obligatorio **ausente** recibe un contorno rojo;
- uno **mal escrito** se muestra en rojo en el propio campo.

El foco salta a la primera celda incorrecta, contando desde arriba, y un pequeño contador junto al botón indica cuántos campos hay que corregir. Mientras algo esté mal, no se envía nada al servidor. Cada marca desaparece en cuanto corriges su campo.

Cuando todos los campos son correctos, el botón consulta al servidor, como siempre ha hecho, y muestra *válido* o los problemas que el servidor encuentra en tu libro mayor y en las demás filas del espacio de trabajo.

!!! example "Ejemplo"

    Dejas la cantidad vacía y escribes *abc* como fecha. Pulsa **⚡ Validar ahora**: ambas celdas se vuelven rojas, el foco se sitúa en la fecha, el contador muestra *2 campos necesitan corrección* y no se envía nada. Corrige la fecha y su marca desaparece; rellena la cantidad y el contador se despeja, y la siguiente pulsación consulta al servidor.

---

## 🏷️ Tipos de transacción

La [guía de Teoría financiera](../../financial-theory/instruments/transaction-types/index.md) explica cada tipo en profundidad.

### 🧾 Transacciones individuales

| Tipo | Qué registra | Teoría |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Compra** | Unidades compradas de un activo y el total pagado | [📖 Leer](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Venta** | Unidades vendidas de un activo y el total recibido | [📖 Leer](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividendo** | Efectivo pagado por un activo que tienes | [📖 Leer](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Interés** | Intereses recibidos, con o sin activo | [📖 Leer](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Depósito** | Efectivo que ingresas en el bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Retiro** | Efectivo que sacas del bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Comisión** | Una comisión u otro coste, opcionalmente vinculado a un activo | [📖 Leer](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Impuesto** | Un impuesto pagado, opcionalmente vinculado a un activo | [📖 Leer](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Ajuste** | Unidades añadidas o eliminadas sin efectivo: un desdoblamiento, un regalo, una posición abierta en otro lugar | [📖 Leer](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Transacciones vinculadas {: #composite-transactions }

Una operación vinculada se registra como dos transacciones enlazadas, que el formulario muestra como una sola, con un lado **Desde** y otro **Hasta**. Cada lado tiene su propia fecha, y la flecha **Intercambiar lados** invierte la dirección. En un cambio de divisas, las dos fechas suelen coincidir: difieren cuando el bróker abona la nueva divisa otro día.

| Tipo | Qué registra | Teoría |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Transferencia de activos** | Unidades de un activo movidas entre dos de tus brókers | [📖 Leer](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Transferencia de fondos** | Efectivo movido entre dos de tus brókers, en una sola divisa | [📖 Leer](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Cambio de divisas** | Una divisa convertida en otra, dentro de un mismo bróker | [📖 Leer](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Una transferencia necesita dos brókers diferentes; un cambio de divisas, dos divisas diferentes. También se pueden vincular más adelante dos filas individuales para formar un par, y volver a separar un par — consulta [Vincular o desvincular un par](index.md#link-pairs).

---

## 🔗 Relacionado

- 📋 **[Transacciones](index.md)** — la lista, los filtros y el espacio de trabajo masivo
- 📥 **[Importar desde el bróker](import/index.md)** — omite la introducción manual con una importación BRIM
