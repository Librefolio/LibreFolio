# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Beta"

    Este complemento está en **Beta** — probado con archivos de muestra, pero pueden existir casos límite.

## 📥 Cómo Exportar

LibreFolio lee exportaciones de Intesa Sanpaolo en formato **CSV** *o* **XLSX** — no es necesario
convertir el archivo, simplemente impórtelo tal como se descarga. Se admiten dos informes diferentes que
cubren dos situaciones distintas:

- La **lista de movimientos** (*lista movimenti*) — la actividad de la cuenta durante un período.
- La **instantánea de cartera** (*patrimonio*) — las tenencias actuales con su
 base de costo fiscal y el saldo en efectivo.

Desde su banca en línea de Intesa Sanpaolo, descargue la lista de movimientos del período que desee
y, si también necesita sembrar posiciones históricas, la instantánea de cartera de su
*Deposito Amministrato*.

## 🧭 ¿Qué archivos debería importar?

=== "Cuenta nueva"

 Si la cuenta se **abrió recientemente** y cada compra está dentro del período
 exportado, importar solo la **lista de movimientos** es suficiente — no hay historial previo que
 reconstruir.

=== "Cuenta con historial (recomendado)"

 Intesa solo exporta aproximadamente **un año** de movimientos y **no** incluye
 las transacciones de compra originales. Para representar posiciones compradas antes, primero importe
 la **instantánea de cartera**: esta siembra la cuenta con

 - un **depósito en efectivo** por la liquidez reportada (cuando la instantánea contiene un saldo en efectivo distinto de cero), y
 - un **ajuste de base de costo por posición** (cantidad de la instantánea, con el
 costo fiscal almacenado como una anulación de base de costo **por unidad**),

 todo fechado en la fecha de la instantánea. Luego importe la **lista de movimientos** para agregar los
 cupones y comisiones recientes.

## 📝 Notas

- **Lista de movimientos** — el analizador asigna etiquetas de operación por palabra clave: *Cedole* → interés,
 *Dividend...* → dividendo, *Commission...* → comisión, y *Ritenut...* / *Imposta...* /
 *Bollo...* → impuesto. Las operaciones diarias de cuenta corriente que puedan aparecer en la misma exportación
 (transferencias, pagos con tarjeta, nómina, etc.) **no se reconocen como actividad de valores y
 se omiten**, con una advertencia — la importación nunca falla por su causa.
- **Sin ISIN en la lista de movimientos** — el valor se toma del campo de texto libre *Dettagli*,
 por lo que los activos se emparejan **por nombre**. La instantánea de cartera *sí* lleva el ISIN.
 Debido a que los dos informes identifican el mismo valor de manera diferente (nombre vs ISIN),
 LibreFolio no los fusionará automáticamente — confirme el activo en el **Paso 4** del asistente.
- **Siembra de instantánea** — cada ajuste almacena `cost_basis_override` como el costo fiscal **por unidad**. Intesa reporta *Controvalore di carico fiscale €* como un valor total de la posición, por lo que LibreFolio lo divide por la cantidad de tenencia antes de almacenarlo. El motor luego multiplica el valor por unidad por la cantidad para reconstruir el costo base total. La fecha de la instantánea es la fecha de cotización más reciente en el informe.
- **Avisos de vencimiento** — si las filas analizadas de Intesa contienen indicios de vencimiento/reembolso, el diálogo de creación de activos puede mostrar un aviso informativo de color ámbar advirtiendo que el valor puede estar vencido o excluido de cotización.
- **Los importes se importan textualmente** en EUR, exactamente como aparecen en el informe. No se realiza
 ninguna conversión de divisa.

## ⛔ Antes de la fecha de apertura del bróker

Cuando su bróker tiene una **fecha de apertura** establecida, los movimientos fechados **estrictamente antes** de esa fecha se marcan en el asistente como **"Antes de la apertura"** y no se pueden importar (su casilla de verificación está deshabilitada). El día de apertura en sí es válido: la verificación implementada es `txDate < info.openedAt`, no `<=`. Esto evita duplicar posiciones que ya están representadas por la siembra de la instantánea. Si una fila se marca incorrectamente, use la acción en línea **Editar fecha del bróker**, luego vuelva a verificar/actualizar para que el asistente evalúe la fecha del bróker actualizada.

## 🔗 Referencia para desarrolladores

→ [Proveedores BRIM — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
