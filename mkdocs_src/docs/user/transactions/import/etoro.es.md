# <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    Este plugin está en fase **Beta**: ha sido probado con archivos de muestra, pero podrían existir casos límite.

## 📥 Cómo Exportar

Para exportar su historial de transacciones desde eToro:

1. Inicie sesión en su [cuenta de eToro](https://www.etoro.com).
2. Haga clic en **Cartera (Portfolio)** en la barra lateral izquierda y luego haga clic en el icono del reloj para abrir **Historial (History)**.
3. Haga clic en el icono del engranaje de configuración en la parte superior derecha y seleccione **Estado de cuenta (Account Statement)**.
4. Elija la fecha de inicio y fin para su estado de cuenta y luego haga clic en **Crear (Create)**.
5. Seleccione la opción de exportación **Excel** o **CSV**. Guarde el archivo en su computadora.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## ⚠️ Problemas Comunes

!!! warning "No utilice estados de cuenta en PDF"

    eToro permite descargar los estados de cuenta como PDF. Los archivos PDF no pueden ser procesados por el importador BRIM. Asegúrese de seleccionar el formato de hoja de cálculo (XLSX o CSV).

!!! warning "CFD frente a Activos Reales"

    eToro admite tanto CFD (contratos por diferencias) como activos reales. El analizador importará las transacciones de CFD, pero debido a que los CFD no representan acciones subyacentes, la base de costo y la lógica WAC podrían requerir una validación manual en la cuadrícula de transacciones.

## 📝 Notas

- Admite operaciones con acciones, ETF, criptomonedas y CFD, dividendos pagados, depósitos, retiros y ajustes de comisiones.
- Todos los valores en los archivos exportados de eToro están denominados en USD.

## 🔗 Referencia para Desarrolladores

→ [eToro Provider — Detalles de Implementación](../../../developer/backend/brim/providers_list.md)
