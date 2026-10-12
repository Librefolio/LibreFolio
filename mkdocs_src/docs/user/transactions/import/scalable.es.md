# 📥 ![](../../../static/icons/brokers/scalable.png) Scalable Capital

LibreFolio importa ambas cuentas de **Scalable Capital**: la **cuenta de valores** y la **cuenta remunerada** (*conto deposito*). LibreFolio no está afiliado a Scalable Capital.

---

## 🏦 Dos cuentas, dos brókeres {: #two-brokers }

Cada cuenta se convierte en un bróker propio en LibreFolio, leído por su propio importador. Crea dos [brókeres](../../brokers/index.md), uno por cuenta, y elige el **Plugin de Importación Predeterminado** de cada uno:

| Cuenta de Scalable | Plugin de Importación Predeterminado | Ejemplo de nombre del bróker | Archivos que lee |
|:--|:--|:--|:--|
| Cuenta de valores | ![](../../../static/icons/brokers/scalable-broker.png){: style="width:16px;vertical-align:middle;margin-right:6px" } **Scalable Capital cuenta de valores** | *Scalable broker* | el archivo de bróker del exportador de LibreFolio, o el propio CSV de Scalable |
| Cuenta remunerada | ![](../../../static/icons/brokers/scalable-deposit.png){: style="width:16px;vertical-align:middle;margin-right:6px" } **Scalable Capital cuenta remunerada** | *Scalable overnight account* | el archivo de cuenta remunerada del exportador de LibreFolio |

Deja vacío **URL del Icono Personalizado**: un bróker sin un icono propio muestra el icono de su plugin de importación predeterminado — el de la tabla — antes del icono del sitio web de su **URL del Portal**.

¿Por qué dos brókeres? Cada cuenta tiene su propio saldo de efectivo y su propio IBAN, y el dinero que mueves entre ellas es una **transferencia de fondos**, que enlaza dos brókeres. Con dos brókeres, cada saldo se puede comprobar con la app de Scalable, y cada transferencia se convierte en un par enlazado. Cada importador rechaza el archivo de la otra cuenta e indica el importador que lo lee.

---

## 📤 Cómo exportar {: #exporter }

A octubre de 2026, Scalable solo te deja descargar tus transacciones en los planes **PRIME** y **PRIME+**, y nunca las de la cuenta remunerada. Por eso se creó el [exportador de LibreFolio](https://github.com/Librefolio/librefolio-exporter).

El exportador es una extensión para Chrome, Edge, Brave y los demás navegadores Chromium, versión 120 o posterior. Lee tus transacciones en las páginas de Scalable, en tu navegador, y las guarda como archivos CSV:

- funciona en **todos los planes**, incluido el FREE;
- es la **única forma** de exportar la **cuenta remunerada**;
- añade lo que le falta al propio CSV de Scalable: el **id de transacción** y el **tipo exacto** de cada movimiento.

??? note "🧩 Instala el exportador — una vez, antes de la primera exportación"

    Los detalles actualizados están en el [README](https://github.com/Librefolio/librefolio-exporter#readme) del exportador, que también cubre la actualización, la privacidad y los riesgos de una extensión que usa la interfaz interna de la aplicación web de Scalable: léelo antes de instalarlo. Aquí tienes un resumen de los pasos.

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

---

## 📥 Importar {: #import }

Importa cada archivo en su propio bróker, en la misma importación o en momentos distintos: en el [Asistente de importación](how-to.md), suelta los archivos CSV y asigna cada uno a su bróker. Nunca importes el mismo archivo en dos brókeres: sus transacciones contarían dos veces.

Si un archivo acaba en el bróker equivocado, el asistente lo dice justo después de la carga. Muestra por qué el plugin predeterminado del bróker no puede leer el archivo y qué bróker sí puede, y ofrece mover el archivo, conservarlo o eliminarlo.

### 🔁 Transferencias entre tus dos cuentas {: #transfers }

El dinero que mueves entre la cuenta de valores y la cuenta remunerada aparece en ambos archivos: un **Retiro** en un bróker y un **Depósito** en el otro, el mismo día y por el mismo importe. Fusiona cada par en una sola **transferencia de fondos**: el espacio de trabajo masivo de la página [Transacciones](../index.md) sugiere los pares, y pregunta antes de **Guardar todo** si no los has revisado.

- **Archivos importados juntos**: las dos mitades se encuentran en el espacio de trabajo, donde un banner verde, *Transacciones complementarias detectadas*, ofrece **Unir** cada par — o todos a la vez, con **Unir todos (N)**.
- **Archivos importados en momentos distintos**: cuando importas el segundo archivo, el espacio de trabajo encuentra las mitades ya guardadas y muestra el botón 💡: haz clic en él para añadirlas, y luego pulsa **Unir** en cada par del banner. Para transferencias guardadas hace mucho tiempo, también puedes marcar las filas de transferencia de ambos brókeres en la página **Transacciones** y hacer clic en **Editar**: el banner aparece en el espacio de trabajo.

También puedes enlazar un par a mano: marca sus dos filas en la página **Transacciones** y haz clic en **🔗 Promover par**.

Las dos mitades tienen descripciones distintas, ya que cada una lleva su propio id de transacción: conserva la descripción unida que propone la fusión (en **Unir todos**, la opción predeterminada: **Combinar**). Una exportación que se solape con una transferencia ya fusionada entonces trae sus mitades de vuelta como probables duplicados, sin marcar.

## 🔗 Referencia para desarrolladores

→ [Importadores de Scalable Capital](../../../developer/backend/brim/scalable.md) · [Lista de proveedores de BRIM](../../../developer/backend/brim/providers_list.md) · [Decir por qué con un código](../../../developer/architecture/patterns/brim_plugin_guide.md#cannot-parse-detail), los rechazos de los dos importadores
