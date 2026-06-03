# 📄 CSV Genérico

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
