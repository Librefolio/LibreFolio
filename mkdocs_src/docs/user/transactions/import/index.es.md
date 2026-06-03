# 📥 Importar desde Bróker (BRIM)

**BRIM** (Broker Report Import Module) le permite importar transacciones directamente desde los archivos de exportación de su bróker, sin necesidad de entrada manual. Cargue un informe CSV y LibreFolio analizará, mapeará e importará todas las transacciones en un solo flujo.

---

## 🚀 Cómo importar

1. Exporte un informe de transacciones desde su bróker (normalmente un archivo CSV; consulte el centro de ayuda de su bróker).
2. En LibreFolio, navegue a su página de **Broker**.
3. Haga clic en el botón **Import** (:material-file-upload:) en el encabezado del bróker.
4. Se abrirá el **Import Modal**.
5. **Arrastre y suelte** o haga clic para seleccionar su archivo.
6. LibreFolio **detecta automáticamente** el formato del bróker y muestra una **vista previa** de las transacciones analizadas.
7. Revise la vista previa: compruebe que las fechas, los importes y los nombres de los activos sean correctos.
8. Haga clic en **Import** para confirmar todas las transacciones.

!!! tip "También puede utilizar la sección de Archivos"

    La sección de **[Archivos](../../files/index.md)** (pestaña BRIM) le permite gestionar los informes de bróker cargados de forma centralizada, volver a importarlos o eliminarlos.

---

## 🏦 Brókers compatibles

| Bróker | Página |
|--------|------|
| Interactive Brokers (IBKR) | [→](ibkr.md) |
| Degiro | [→](degiro.md) |
| eToro | [→](etoro.md) |
| Directa SIM | [→](directa.md) |
| Charles Schwab | [→](schwab.md) |
| Revolut | [→](revolut.md) |
| Coinbase | [→](coinbase.md) |
| Freetrade | [→](freetrade.md) |
| Finpension | [→](finpension.md) |
| Trading212 | [→](trading212.md) |
| Generic CSV | [→](generic-csv.md) |

!!! note "Todos los proveedores están en Beta"

    Los complementos de importación son mantenidos por la comunidad y mejoran con el tiempo. Si un formato de informe específico presenta anomalías, el proveedor **[Generic CSV](generic-csv.md)** permite el mapeo manual de columnas como fallback.

---

## 🗂️ Mapeo de Activos

Durante el paso de vista previa, LibreFolio intenta **emparejar automáticamente** cada nombre de activo de su informe con un activo ya existente en su biblioteca.

- ✅ **Emparejado** — se importará vinculado al activo existente.
- ⚠️ **No emparejado** — seleccione o cree el activo de destino antes de importar.
- ❌ **Error** — la fila no pudo ser analizada.

---

## ♻️ Detección de Duplicados

BRIM comprueba si existen **transacciones duplicadas** basándose en la fecha, el tipo, el activo, la cantidad y el importe. Las filas duplicadas se marcan en la vista previa; puede optar por omitirlas o forzar la importación.

---

## 🔗 Relacionados

- 📋 **[Tabla de Transacciones](../index.md)** — Ver y gestionar transacciones importadas
- 🗂️ **[Archivos](../../files/index.md)** — Gestionar los archivos de informes de bróker cargados
- 🏦 **[Brókers](../../brokers/index.md)** — Configure primero sus cuentas de bróker
