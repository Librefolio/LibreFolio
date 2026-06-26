# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    Este plugin está en fase **Beta** — ha sido probado con archivos de muestra, pero pueden existir casos excepcionales.

## 📥 Cómo exportar

Para exportar sus transacciones desde Interactive Brokers, siga estos pasos:

1. Inicie sesión en el [Portal del Cliente de Interactive Brokers](https://www.interactivebrokers.com).
2. Navegue a **Reports** en el menú superior y seleccione **Statements**.
3. En la sección **Activity**, haga clic en la tarjeta **Activity Statement**.
4. Seleccione el **Date Range** deseado (por ejemplo, Year to Date, Custom) y elija **CSV** como el formato.
5. Haga clic en **Run** o descargue el informe CSV generado en su ordenador.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Interactive Brokers Portal - Statements & Reports menu] -->
</div>

### ⚙️ Uso de Flex Queries (Recomendado)

Para carteras más avanzadas, puede configurar una **Flex Query** para exportar datos específicos:

1. En **Reports**, vaya a **Flex Queries** y haga clic en el botón **+ (Create)**.
2. Seleccione **Activity Flex Query**.
3. Añada **Trades**, **Cash Transactions** (para dividendos y comisiones) y **Corporate Actions** a la consulta.
4. Establezca el formato en **CSV** y guarde la consulta. Puede ejecutar esta consulta personalizada en cualquier momento.

## ⚠️ Problemas Comunes

!!! warning "Formato de Archivo"

    Asegúrese de exportar como un archivo **CSV**. Los extractos en PDF no son compatibles con el analizador y la carga fallará.

!!! warning "Configuración de Idioma"

    El analizador está diseñado para encabezados CSV en inglés. Asegúrese de que el idioma del Portal del Cliente de IBKR esté configurado en inglés antes de realizar la exportación.

## 📝 Notas

- Compatible con los informes de actividad estándar de IBKR (operaciones, dividendos, retenciones fiscales, comisiones, depósitos, retiradas).
- Se admiten cuentas multi-divisa.
- Las acciones corporativas (divisiones, fusiones) pueden requerir ajustes manuales dentro de la cuadrícula de preparación (staging grid).
