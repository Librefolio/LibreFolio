# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    Este plugin está en **Beta** — se ha probado con archivos de ejemplo, pero pueden existir casos límite.

## 📥 Cómo exportar

Para exportar tu historial de transacciones de acciones/criptomonedas desde Revolut:

1. Abre tu **aplicación móvil de Revolut** o inicia sesión a través del cliente web.
2. Ve a la pestaña **Invest** (o Acciones/Cripto).
3. Toca **... (Más)** junto al saldo de tu cartera y, a continuación, selecciona **Extractos**.
4. Selecciona la cuenta deseada (por ejemplo, la cuenta de Acciones) y toca **Extracto de transacciones**.
5. Establece el período de tiempo, elige **CSV** como formato y exporta. Transfiere el archivo a tu ordenador.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Marcador de posición de captura: aplicación de Revolut — selección de extractos en Invest y exportación CSV] -->
</div>

## ⚠️ Errores habituales

!!! warning "Cuenta de trading vs. cuenta principal"

    Asegúrate de exportar el extracto desde la subcuenta **Invest/Trading**. El extracto de la tarjeta de débito principal de Revolut usa un formato de archivo completamente distinto y este plugin no puede analizarlo.

## 📝 Notas

- Admite operaciones de acciones, compras de criptomonedas, dividendos pagados, comisiones de custodia y transferencias de fondos.
- Gestiona automáticamente importes en varias divisas dentro del mismo archivo.
- Las transferencias entre tus propias cuentas se omiten discretamente, ya que no cambian nada.

## 🔀 Desdoblamientos de acciones {: #stock-splits }

En un archivo de **Invest**, una fila **STOCK SPLIT** con una **Quantity** positiva se importa como un **Ajuste** entrante de las acciones añadidas (la **Quantity** de la fila es el número de acciones nuevas, no el total después del desdoblamiento), sin coste alguno.

El importador no puede distinguir un desdoblamiento de una entrega gratuita de acciones o de una escisión, por lo que marca la fila. El final del asistente de importación (el paso **Revisión**) te indica cuántas filas parecen desdoblamientos, y el editor masivo muestra un banner: *N filas pueden ser desdoblamientos de acciones*. Para cada fila muestra el ticker, las acciones añadidas y la fecha. Cuando las filas anteriores en el archivo indican cuántas acciones tenías antes del desdoblamiento, también muestra el **ratio** resultante (por ejemplo, 3 para un desdoblamiento 3 por 1) y las acciones en cartera.

Dos botones te permiten resolverlo:

- **Crear el evento de DESDOBLAMIENTO y vincularlo** abre el pequeño formulario de evento con el tipo ya establecido en **Desdoblamiento** y el ratio rellenado con el sugerido. Puedes cambiarlo: escribe `3` para un desdoblamiento 3 por 1, `0.25` para un desdoblamiento inverso 1 por 4.
- **Vincular a un evento existente** te permite elegir uno de los eventos del activo, si ya has creado el desdoblamiento.

Una vez que la fila está vinculada, la entrada del banner desaparece. Si aún no se ha elegido el activo de la fila, el banner te pide que lo elijas primero. Para obtener más información sobre los eventos, consulta [Eventos de activos](../../assets/detail/events.md).

!!! note "🔢 Cuando el bróker redondea la cantidad"

    Los brókeres a veces redondean las acciones que registran (por ejemplo, 0.1643 en lugar de 0.16431924). Si la cantidad de la fila difiere de tu posición multiplicada por (el ratio menos uno), el banner lo indica y muestra la diferencia en acciones. La vista **Lotes** sigue el ratio del evento, mientras que el **Panel** y el coste medio siguen la cantidad de la fila. La diferencia es pequeña, pero tras vender toda la posición puede quedar un lote minúsculo que no se puede vender.

!!! warning "Vincula el desdoblamiento a un evento Desdoblamiento"

    Hasta que la fila esté vinculada a un evento **Desdoblamiento**, las nuevas acciones entran sin coste y diluyen el coste medio del activo. La vista **Lotes** muestra un lote con un coste de 0. Si vendes parte de la posición, LibreFolio vende primero los lotes antiguos y caros al precio posterior al desdoblamiento, por lo que verás una pérdida, y más adelante una ganancia cuando se consuma el lote de coste cero. Un activo sin cotizaciones también permanece sobrevalorado: las nuevas acciones cuentan a valor completo, aunque el precio no se haya dividido. Vincular el evento hace que el coste siga a las acciones antiguas, lo cual es correcto para un desdoblamiento. El archivo no indica si las acciones proceden de un desdoblamiento, una entrega gratuita o una escisión, así que la elección es tuya.

## 🚧 Limitaciones conocidas

- **Los desdoblamientos inversos no se importan.** Una fila **STOCK SPLIT** con una **Quantity** negativa, cero o ausente (o sin ticker) se incluye en un aviso ámbar, con un enlace para abrir una incidencia en GitHub: añádela manualmente.
- **Solo archivos de Invest.** Los desdoblamientos de acciones se leen en los extractos de Invest, no en los de Cripto.
- **¿Algo no cuadra?** Abre una [incidencia](https://github.com/Librefolio/LibreFolio/issues) con un archivo de ejemplo anonimizado.

## 🔗 Referencia para desarrolladores

→ [Proveedor de Revolut — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
