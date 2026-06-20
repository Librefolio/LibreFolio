# <img src="https://www.directa.it/favicon.ico" alt=""> Directa SIM

!!! info "Beta"

    Este plugin está en **Beta** — probado con archivos de muestra, pero pueden existir casos aislados.

## 📥 Cómo Exportar

Para exportar sus transacciones desde Directa SIM:

1. Inicie sesión en su [Portal Directa](https://www.directatrading.com) (utilizando la interfaz dLite o Classic).
2. Vaya a **INFO** u **Operazioni** en el menú principal, luego seleccione **Movimenti** (Movimientos de Efectivo) o **Tabella Ordini** (Historial de Órdenes).
3. Seleccione el rango de fechas que desea exportar.
4. Haga clic en el icono de descarga **CSV** o en el botón de exportación en la parte superior derecha de la tabla.
5. Guarde el archivo directamente sin abrirlo ni modificarlo en Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Directa SIM Portal - Movimenti Cash / Transazioni CSV export page] -->
</div>

## ⚠️ Errores Comunes

!!! warning "Filas de Encabezado"

    Los archivos de Directa SIM contienen un bloque de encabezado de metadatos (normalmente 9 líneas) antes de la tabla de datos real. El analizador está diseñado para omitir este bloque automáticamente. **No elimine estas líneas de encabezado manualmente**, de lo contrario, el analizador no podrá encontrar las columnas de datos correctas.

!!! warning "Aviso sobre el delimitador"

    Las exportaciones de Directa utilizan el punto y coma `;` como delimitador y el formato numérico estándar italiano (coma `,` para los decimales). El analizador procesa estos ajustes automáticamente. Evite guardar el CSV a través de software que convierta estos delimitadores (como abrir y guardar en Microsoft Excel sin la configuración de texto sin formato).

## 📝 Notas

- Compatible con operaciones con acciones, bonos y ETF, dividendos, impuestos (ritenute fiscali) y comisiones de transacción.
- Las operaciones de la cuenta están denominadas en EUR.

## 🔗 Referencia para Desarrolladores

→ [Proveedor Directa SIM — Detalles de Implementación](../../../developer/backend/brim/providers_list.md)
