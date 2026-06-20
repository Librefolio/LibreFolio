# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV Genérico

El proveedor de **CSV Genérico** es un fallback flexible para los brókers que no cuentan con soporte directo. Permite el mapeo manual de columnas para que pueda importar desde cualquier exportación basada en CSV.

## Cuándo usarlo

- Su bróker no se encuentra en la lista de brókers compatibles.
- Un bróker compatible cambió su formato de exportación y el plugin aún no ha sido actualizado.
- Tiene una hoja de cálculo personalizada que desea importar.

## Cómo funciona

1. Cargue su archivo CSV.
2. LibreFolio muestra las columnas detectadas sin procesar.
3. Mapee cada columna con el campo correspondiente de LibreFolio (fecha, tipo, activo, cantidad, precio, monto, moneda, comisión).
4. Previsualice las filas analizadas y confirme la importación.

!!! tip "Agregar un plugin nativo"

    Si utiliza un bróker con frecuencia, considere contribuir con un plugin nativo. Consulte el [Manual del Desarrollador → Guía del Plugin BRIM](../../../developer/backend/brim/generic_csv.md) para obtener instrucciones.

## 🔗 Referencia para Desarrolladores

→ [Proveedor de CSV Genérico — Detalles de Implementación](../../../developer/backend/brim/generic_csv.md)
