# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

!!! info "Alpha"

    Estos importadores están en **Alpha**: algunos tipos de filas aún no se han visto en exportaciones reales (ver [Límites](#limits)). Si se rechaza un archivo, o una fila se importa de una forma que parece incorrecta, avísanos en los [issues](https://github.com/Librefolio/LibreFolio/issues) del proyecto.

LibreFolio importa ambas cuentas de **Scalable Capital**: la **cuenta de valores** y la **cuenta remunerada** (*Tagesgeld*, *conto deposito*). LibreFolio no está afiliado a Scalable Capital.

---

## 🏦 Dos cuentas, dos brókers {: #two-brokers }

Cada cuenta se convierte en un bróker propio en LibreFolio, leído por su propio importador:

| Cuenta de Scalable | Importador | Archivos que lee |
|:--|:--|:--|
| Cuenta de valores | **Scalable Capital cuenta de valores** | el archivo de bróker del exportador de LibreFolio, o el propio CSV de Scalable |
| Cuenta remunerada | **Scalable Capital cuenta remunerada** | el archivo de cuenta remunerada del exportador de LibreFolio |

¿Por qué dos brókers? Cada cuenta tiene su propio saldo de efectivo y su propio IBAN, y el dinero que mueves entre ellas es una **transferencia de fondos**, que enlaza dos brókers. Con dos brókers, cada saldo se puede comprobar con la app de Scalable, y cada transferencia se convierte en un par enlazado. Cada importador rechaza el archivo de la otra cuenta e indica el importador que lo lee.

---

## 📤 Qué exportar

### 🧩 Recomendado: el exportador de LibreFolio {: #exporter }

El [exportador de LibreFolio](https://github.com/Librefolio/librefolio-exporter) es una extensión para Chrome, Edge, Brave y los demás navegadores Chromium, versión 120 o posterior. Lee tus transacciones en las páginas de Scalable, en tu navegador, y las guarda como archivos CSV:

- funciona en **todos los planes**, incluido el FREE;
- es la **única forma** de exportar la **cuenta remunerada**;
- añade lo que le falta al propio CSV de Scalable: el **id de transacción** y el **tipo exacto** de cada movimiento.

Antes de instalarlo, lee el [README](https://github.com/Librefolio/librefolio-exporter#readme) del exportador: cubre por completo la instalación y la actualización, la privacidad y los riesgos de una extensión que usa la interfaz interna de la aplicación web de Scalable.

**Instálalo una vez:**

1. Descarga los dos archivos de la [última versión](https://github.com/Librefolio/librefolio-exporter/releases/latest), `librefolio-exporter-<version>.zip` y `librefolio-exporter-<version>.zip.sha256`, en la misma carpeta — por ejemplo `Downloads/chromePlugin`.
2. Comprueba el ZIP desde un terminal. El `cd` va a esa carpeta; el segundo comando compara el ZIP con la huella de su archivo `.sha256`:

    === "macOS"

        ```bash
        cd ~/Downloads/chromePlugin
        shasum -a 256 -c librefolio-exporter-*.zip.sha256
        ```

    === "Linux"

        ```bash
        cd ~/Downloads/chromePlugin
        sha256sum -c librefolio-exporter-*.zip.sha256
        ```

    === "Windows"

        Windows no tiene ningún comando que lea archivos `.sha256`: usa las líneas de PowerShell del [README](https://github.com/Librefolio/librefolio-exporter#readme) del exportador.

    `OK` significa que el ZIP es exactamente el publicado. Ante cualquier otra respuesta, no lo instales: descarga de nuevo ambos archivos.

3. Descomprímelo en esa carpeta: obtienes una carpeta `librefolio-exporter`. Déjala ahí, ya que el navegador carga la extensión desde ella.
4. Abre `chrome://extensions` (`edge://extensions` en Edge), activa el **modo de desarrollador**, haz clic en **Cargar descomprimida** y elige la carpeta `librefolio-exporter`.

**Exporta:**

1. Inicia sesión en Scalable Capital: el botón **LibreFolio** aparece en la esquina inferior derecha de cada página.
2. Haz clic en él, elige las cuentas y el periodo, y luego haz clic en **Exportar CSV**.
3. Obtienes `scalable-broker_<date>_<time>.csv` y `scalable-deposit_<date>_<time>.csv` — juntos en un solo ZIP cuando exportas ambas cuentas. Extrae el ZIP: LibreFolio lee los archivos CSV.

La primera exportación lee todo el historial; las siguientes empiezan desde la última exportación (**Desde la última**), así que solo se leen las transacciones nuevas. Las filas que ya están en LibreFolio vuelven como [probables duplicados](index.md#duplicate-detection) y llegan sin marcar. Puedes renombrar los archivos: LibreFolio reconoce cada uno por sus columnas.

!!! warning "Archivos escritos por el exportador 1.0.0"

    El exportador 1.0.0 escribía la comisión dentro del importe de cada operación. LibreFolio importa esas operaciones tal como están, sin una comisión aparte, y te avisa de ellas. Actualiza el exportador a 1.0.1 o posterior y expórtalas de nuevo. Si ya has importado un archivo así, primero elimina las operaciones que enumeró el aviso: sus importes cambian, por lo que LibreFolio no las reconocería como duplicados.

### 📄 Alternativa: el propio CSV de Scalable {: #scalable-csv }

En los planes **PRIME** y **PRIME+**, Scalable te permite descargar las transacciones de la **cuenta de valores** como un archivo CSV: el importador **Scalable Capital cuenta de valores** lo lee tal como se descarga. Cubre solo la cuenta de valores — la cuenta remunerada siempre necesita el exportador.

Cíñete a una sola fuente por cuenta. Las descripciones que escribe LibreFolio difieren entre las dos fuentes — solo las del exportador llevan el id de transacción —, así que las filas importadas desde una vuelven desde la otra como duplicados *posibles*, aún marcadas: cuando cambies, exporta desde el día siguiente a tu última importación.

---

## ⚙️ Configura los dos brókers {: #set-up }

Crea dos [brókers](../../brokers/index.md), uno por cuenta — por ejemplo *Scalable broker* y *Scalable overnight account* — y elige el **Plugin de importación predeterminado** de cada uno:

| Bróker para | Plugin de importación predeterminado | Icono |
|:--|:--|:--:|
| la cuenta de valores | **Scalable Capital cuenta de valores** | ![El logotipo de Scalable con una insignia de gráfico azul, el icono del importador Scalable Capital cuenta de valores](../../../static/icons/brokers/scalable-broker.png){: width="48" } |
| la cuenta remunerada | **Scalable Capital cuenta remunerada** | ![El logotipo de Scalable con una insignia de hucha naranja, el icono del importador Scalable Capital cuenta remunerada](../../../static/icons/brokers/scalable-deposit.png){: width="48" } |

El bróker entonces muestra el icono del importador por sí mismo: un bróker sin un icono propio muestra el icono de su plugin de importación predeterminado, antes del icono del sitio web de su **URL del portal**, así que deja **URL de icono personalizado** vacío.

---

## 📥 Importar {: #import }

Importa cada archivo en su propio bróker, en la misma importación o en momentos distintos: en el [Asistente de importación](how-to.md), suelta los archivos CSV y asigna cada uno a su bróker.

Si un archivo acaba en el bróker equivocado, el asistente lo dice justo después de la carga. Muestra por qué el plugin predeterminado del bróker no puede leer el archivo y qué bróker sí puede, y ofrece mover el archivo, conservarlo o eliminarlo.

### 🔁 Transferencias entre tus dos cuentas {: #transfers }

El dinero que mueves entre la cuenta de valores y la cuenta remunerada aparece en ambos archivos: un **Retiro** en un bróker y un **Depósito** en el otro, el mismo día y por el mismo importe. Fusiona cada par en una sola **transferencia de fondos**: el espacio de trabajo masivo de la página [Transacciones](../index.md) sugiere los pares, y pregunta antes de **Guardar todo** si no los has revisado.

- **Archivos importados juntos**: las dos mitades se encuentran en el espacio de trabajo, donde un banner verde, *Transacciones complementarias detectadas*, ofrece **Fusionar** cada par — o todos a la vez, con **Fusionar todos (N)**.
- **Archivos importados en momentos distintos**: cuando importas el segundo archivo, el espacio de trabajo encuentra las mitades ya guardadas y muestra el botón 💡: haz clic en él para añadirlas, y luego **Fusionar** cada par desde el banner. Para transferencias guardadas hace mucho tiempo, también puedes marcar las filas de transferencia de ambos brókers en la página **Transacciones** y hacer clic en **Editar**: el banner aparece en el espacio de trabajo.

También puedes enlazar un par a mano: marca sus dos filas en la página **Transacciones** y haz clic en **🔗 Promover par**.

Las dos mitades tienen descripciones distintas, ya que cada una lleva su propio id de transacción: conserva la descripción unida que propone la fusión (en **Fusionar todos**, la opción predeterminada: **Combinar**). Una exportación que se solape con una transferencia ya fusionada entonces trae sus mitades de vuelta como probables duplicados, sin marcar.

### 🤔 ¿Un solo bróker? {: #one-broker-only }

Puedes importar ambos archivos en un solo bróker. La importación funciona, pero:

- cada transferencia entre las cuentas sigue siendo un **Depósito** más un **Retiro**, ya que una transferencia de fondos necesita dos brókers: el dinero que entra y sale parece mayor de lo que es;
- las dos cuentas comparten un único saldo de efectivo, así que ninguna puede comprobarse por sí sola con la app de Scalable.

En cualquier caso, nunca importes el mismo archivo en dos brókers: sus transacciones contarían dos veces.

---

## 📝 Qué se importa {: #what-is-imported }

| En el archivo (`type`) | Se importa como |
|:--|:--|
| `Buy`, `Savings plan` | **Compra**, por el importe del archivo — el valor de las acciones — con la comisión del pedido como **Comisión** y el impuesto como **Impuesto** del mismo valor. Un impuesto devuelto se convierte en un **Depósito** |
| `Sell` | **Venta**, de la misma forma |
| `Distribution` | **Dividendo**, bruto — el importe abonado más el impuesto retenido — con ese impuesto como **Impuesto**; neto cuando el archivo no indica impuesto |
| `Interest` | **Interés**, bruto, con el impuesto retenido como **Impuesto**; neto cuando el archivo no indica impuesto |
| `Deposit`, `Withdrawal` — transferencias bancarias, y transferencias entre tus dos cuentas | **Depósito**, **Retiro** |
| `Fee` | **Comisión** |
| `Taxes` | **Impuesto**; una devolución de impuestos se convierte en un **Depósito** |
| Cualquier otra fila de efectivo, como un bono | **Depósito** o **Retiro**, según el signo de su importe |
| `Security transfer`, `Corporate action` y otros tipos | No se importan: un [aviso](#notices) los enumera |

- **Solo se importan las filas ejecutadas**: un aviso cuenta las demás.
- **Los valores** vienen con su ISIN y su nombre: asigna cada uno a tus activos en el paso **Revisión** del asistente (ver [Asignación de activos](index.md#asset-mapping)).
- **Cada descripción termina con el id de transacción**: `· id …` del exportador, seguido de `· ref …` cuando la fila tiene una referencia; `· ref …` del CSV de Scalable. La comisión y el impuesto de una operación empiezan por `Order fee ·` y `Tax ·`. El id distingue dos movimientos idénticos, y permite que una nueva exportación reconozca las filas ya importadas.
- **Etiquetas**: `import` y `scalable`.
- **Los importes se copian** del archivo, nunca se recalculan ni se convierten — un dividendo o interés bruto es la suma de dos de sus columnas — y la divisa proviene de cada fila.

---

## 🔔 Qué te dice LibreFolio {: #notices }

En el paso **Analizar**, los avisos del importador (⚠️) te dicen qué dejó fuera o leyó de una forma que merece revisarse, cada uno con sus filas:

- **No ejecutadas** — las filas pendientes, canceladas, caducadas o rechazadas no se importan; un pedido ejecutado más tarde llega con la siguiente exportación.
- **Ejecutadas en parte** — los pedidos ejecutados en parte y aún abiertos no se importan todavía: llegan, ejecutados, con una exportación posterior.
- **Reversiones** — las filas que revierten una transacción ya registrada no se importan: revisa esa transacción y corrígela a mano.
- **No importadas** — transferencias de valores, operaciones societarias y tipos que LibreFolio aún no lee: añádelos a mano si mueven acciones o efectivo.
- **Registradas por signo** — filas de efectivo de un tipo desconocido, o con un signo inesperado, se convierten en un depósito o un retiro según el signo de su importe.
- **Devoluciones de impuestos** — se importan como depósitos: en LibreFolio un impuesto siempre saca dinero.
- **Sin detalles de comisión o impuesto** — filas importadas con el importe que muestra Scalable, sin comisión ni impuesto aparte: exporta de nuevo con la opción de incluir comisiones e impuestos.
- **Dividendos netos** — el archivo no indica el impuesto retenido, así que el dividendo se importa tal como se abonó.
- **Transferencias entre tus cuentas** — un recordatorio para importar el archivo de la otra cuenta en su propio bróker y [fusionar cada par](#transfers).
- **Varias cuentas remuneradas** — el archivo contiene más de una: todas sus filas van a este bróker, cuyo saldo es su suma.
- **Comisión dentro del importe** — operaciones de un [archivo del exportador 1.0.0](#exporter), importadas tal como están.
- **Filas ilegibles** — falta una fecha, un importe, una divisa, las acciones o el valor: esas filas no se importan.

---

## ⚠️ Límites {: #limits }

- **Alpha**: todavía no se han visto exportaciones reales de ventas, dividendos, reversiones, cripto o pedidos ejecutados en parte. Revisa esas filas con cuidado después de la importación.
- **Cuéntanoslo**: si se rechaza un archivo o una fila parece incorrecta, abre un [issue](https://github.com/Librefolio/LibreFolio/issues), con las filas afectadas anonimizadas.

## 🔗 Referencia para desarrolladores

→ [Lista de proveedores de BRIM](../../../developer/backend/brim/providers_list.md) · [Decir por qué con un código](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail), los rechazos de los dos importadores
