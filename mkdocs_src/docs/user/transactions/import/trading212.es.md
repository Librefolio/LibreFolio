# <img src="https://www.trading212.com/favicon-32x32.png" alt=""> Trading212

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de ejemplo, pero pueden existir casos límite.

## 📥 Cómo exportar

Para exportar tu extracto de transacciones desde Trading212:

1. Inicia sesión en el [Portal del cliente de Trading212](https://www.trading212.com) (o abre la aplicación en tu dispositivo móvil).
2. Ve a la sección de menú/perfil y haz clic en **Historial**.
3. Haz clic en el botón **Exportar** (normalmente representado por un icono de exportación o de documento en la parte superior de la pestaña de historial).
4. Selecciona las columnas deseadas (asegúrate de que estén seleccionados todos los campos, como ticker, fecha, cantidad, precio y moneda).
5. Elige **CSV** como formato y haz clic en **Exportar**. Guarda el archivo en tu ordenador.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Trading212 Portal - History and CSV Export modal] -->
</div>

## ⚠️ Errores comunes

!!! warning "Transacciones con Pies"

    Trading212 admite "Pies" (cestas de activos gestionados automáticamente). Si operas dentro de un Pie, la exportación registra estas operaciones como transacciones separadas de los activos subyacentes. El analizador de BRIM procesa estas operaciones individuales automáticamente, pero asegúrate de que los saldos de tus Pies estén completamente sincronizados en la cuadrícula de preparación antes de confirmar.

## 📝 Notas

- Admite compras y ventas de acciones/ETF, dividendos, intereses sobre efectivo, depósitos y retiros.
- Se admiten cuentas multidivisa.
- Las transferencias entre tus propias cuentas se omiten sin avisar, ya que no cambian nada.

## 🔀 Desdoblamientos de acciones

Trading212 escribe un desdoblamiento como dos filas, **Stock split close** (las acciones antiguas salen) y **Stock split open** (las acciones nuevas llegan), para el mismo ISIN en el mismo instante. Cuando después del desdoblamiento hay **más** acciones que antes, LibreFolio importa el par como un único **Ajuste** entrante por la diferencia, sin coste.

El importador no puede distinguir un desdoblamiento de una donación o de una escisión, por lo que marca la fila. El final del asistente de importación (el paso **Revisión**) te indica cuántas filas parecen desdoblamientos, y el editor masivo muestra un banner: *N filas pueden ser desdoblamientos de acciones*. Para cada fila, muestra el ticker, las acciones añadidas y la fecha. Como la fila **Stock split close** contiene las acciones que tenías antes, también muestra el **ratio** resultante (por ejemplo, 3 para un desdoblamiento 3 a 1) y las acciones en cartera.

Dos botones te permiten resolverlo:

- **Crear el evento DESDOBLAMIENTO y vincular** abre el pequeño formulario de evento con el tipo ya establecido en **Desdoblamiento** y el ratio rellenado con el sugerido. Puedes cambiarlo: escribe `3` para un desdoblamiento 3 a 1, `0.25` para un desdoblamiento inverso 1 a 4.
- **Vincular a un evento existente** te permite elegir uno de los eventos del activo, si ya has creado el desdoblamiento.

Una vez vinculada la fila, la entrada del banner desaparece. Si aún no se ha elegido el activo de la fila, el banner te pide que lo elijas primero. Para obtener más información sobre los eventos, consulta [Eventos de activos](../../assets/detail/events.md).

!!! note "🔢 Cuando el bróker redondea la cantidad"

    Los brókeres a veces redondean las acciones que registran (por ejemplo, 0.1643 en lugar de 0.16431924). Si la cantidad de la fila difiere de tu posición multiplicada por (el ratio menos uno), el banner lo indica y muestra la diferencia en acciones. La vista **Lotes** sigue el ratio del evento, mientras que el **Panel** y el coste medio siguen la cantidad de la fila. La diferencia es pequeña, pero después de vender toda la posición puede quedar un lote minúsculo que no se puede vender.

!!! warning "Vincula el desdoblamiento a un evento Desdoblamiento"

    Hasta que la fila se vincule a un evento **Desdoblamiento**, las acciones nuevas entran sin coste y diluyen el coste medio del activo. La vista **Lotes** muestra un lote con un coste de 0. Si vendes parte de la posición, LibreFolio vende primero los lotes antiguos y caros al precio posterior al desdoblamiento, por lo que ves una pérdida y, más tarde, una ganancia cuando se agota el lote de coste cero. Un activo sin cotizaciones también permanece sobrevalorado: las acciones nuevas cuentan a valor completo, aunque el precio no se haya dividido. Vincular el evento hace que el coste siga a las acciones antiguas, lo cual es correcto para un desdoblamiento. El archivo no indica si las acciones proceden de un desdoblamiento, una donación o una escisión, así que la elección depende de ti.

## 🚧 Limitaciones conocidas

- **Desdoblamientos que no se importan.** Un desdoblamiento inverso (menos acciones después que antes), un desdoblamiento con el mismo número de acciones y una fila de desdoblamiento sin su par se incluyen en un aviso ámbar, con un enlace para abrir una incidencia en GitHub: añádelos a mano.
- **Las distribuciones de acciones y las conversiones de divisa no se importan.** Las filas **Stock distribution** y **Currency conversion** se incluyen en el mismo aviso: añádelas a mano.
- **¿Algo no cuadra?** Por favor, [abre una incidencia](https://github.com/Librefolio/LibreFolio/issues) con un archivo de ejemplo anonimizado.

## 🔗 Referencia para desarrolladores

→ [Proveedor Trading212 — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
