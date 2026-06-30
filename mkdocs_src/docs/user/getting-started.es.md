# 🚀 Primeros Pasos

¡Bienvenido a LibreFolio! Esta guía le acompañará en el registro de una cuenta, el inicio de sesión y la importación de su primer extracto de bróker para poblar instantáneamente su panel.

---

## 📝 1. Registre su Cuenta

Vaya a la URL de LibreFolio (por ejemplo, `http://localhost:6040`) y verá la página de inicio de sesión. Haga clic en **Register** para crear una nueva cuenta.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Registration Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Complete sus datos:

- 👤 **Username**: Su nombre de visualización (único en el sistema)
- 📧 **Email**: Una dirección de correo electrónico válida
- 🔑 **Password**: Una contraseña segura (el indicador de seguridad le ayudará)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registration with Password Strength" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primer Usuario = Admin"

    El primer usuario en registrarse se convierte automáticamente en el **administrador del sistema** (superusuario). Este usuario puede gestionar la configuración global, promover a otros usuarios y acceder a todas las funciones de administración.

---

## 🔐 2. Inicie Sesión

Después de registrarse, será redirigido a la página de inicio de sesión. Ingrese sus credenciales para acceder a su panel de control.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Login Page" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Importe su Primer Extracto (Cree Bróker y Activos al Vuelo)

En su primer inicio de sesión, tendrá un panel vacío sin datos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Panel Vacío" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

En LibreFolio, la forma más rápida de comenzar es importando directamente su historial de transacciones. No es necesario configurar brókers o activos previamente: ¡el sistema los creará automáticamente durante el proceso de importación!

### 📋 Pasos

1. **Cargue el Extracto**: Vaya a la página de **[Transacciones](transactions/index.md)** desde el menú lateral. Haga clic en el botón **"Import"** (:material-file-upload:) o simplemente arrastre y suelte el archivo del informe de su bróker (CSV o PDF) directamente en la página.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Asistente Paso 1: Cargar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

2. **Configuración del Analizador**: El asistente detectará automáticamente el formato del extracto. Puede verificar la configuración (como el formato de fecha y delimitadores) y configurar las opciones de fallback si está cargando un informe CSV genérico.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step2" alt="Asistente Paso 2: Configuración del Analizador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    !!! tip "Reprocesar estados de cuenta existentes"
    
        También puede volver a procesar (re-process) cualquier estado de cuenta previamente cargado directamente desde la página **[Files & Uploads](files/index.md#broker-reports)**. Esto es especialmente útil después de la actualización de un complemento de importación o si borró accidentalmente algunas transacciones y desea restaurarlas.

3. **Análisis y Lectura**: El sistema lee, valida y procesa las filas del extracto. Verá una barra de progreso que indica la velocidad y el estado de la lectura.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Asistente Paso 3: Análisis" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Resolución de Bróker y Activos**: Si el informe contiene una cuenta de bróker o activos (como ETF o acciones) que aún no existen en LibreFolio, el sistema los marcará. Puede buscar los existentes o crearlos **al vuelo** (on-the-fly) directamente en el asistente con detalles precompletados del extracto. Para más detalles, consulte la guía **[Import from Broker - Asset Mapping](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Asistente Paso 4: Resolución" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Detección de Duplicados**: El asistente compara las transacciones del informe con su historial existente. Agrupa las posibles coincidencias en dos insignias de estado de la interfaz de usuario basándose en 4 niveles de confianza:
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-duplicate" alt="Asistente Paso 5: Detección de Duplicados" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    | Insignia UI | Nivel de Confianza | Criterios / Reglas de Emparejamiento |
    | :--- | :--- | :--- |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY_WITH_ASSET` | Los campos básicos y la descripción coinciden, y el activo se ha resuelto automáticamente (duplicado altamente seguro). |
    | <span style="background-color: rgba(217, 119, 6, 0.15); color: #d97706; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">⚠️ LIKELY</span> | `LIKELY` | Los campos básicos y la descripción coinciden, pero el activo no está resuelto. |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE_WITH_ASSET` | Los campos básicos coinciden y el activo se ha resuelto automáticamente (pero la descripción difiere o está vacía). |
    | <span style="background-color: rgba(37, 99, 235, 0.15); color: #2563eb; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">ℹ️ POSSIBLE</span> | `POSSIBLE` | Los campos básicos (tipo, fecha, cantidad, monto) coinciden, pero el activo no está resuelto. |
    | <span style="background-color: rgba(16, 185, 129, 0.15); color: #10b981; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">✅ ÚNICO</span> | — | La transacción no tiene coincidencias en la base de datos y se considera nueva (duplicado descartado). |
    | <span style="background-color: rgba(239, 68, 68, 0.15); color: #ef4444; padding: 2px 8px; border-radius: 12px; font-weight: 600; font-size: 0.85em; white-space: nowrap;">❌ NO RESUELTO</span> | — | El bróker o el instrumento financiero no se han emparejado con entidades existentes en la base de datos (requiere resolución en el Paso 4 antes de importar). |

    Para más detalles sobre las reglas y la configuración de duplicados, consulte la sección **[Import from Broker - Duplicate Detection](transactions/import/index.md#duplicate-detection)**.

6. **Revisión Final y Carga**: Revise la lista de transacciones procesadas. Una vez que verifique que todo está correcto, haga clic en **Import** para guardar todas las transacciones en su cartera.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-bulk-staging" alt="Asistente Paso 6: Revisión General" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>
    
    La tabla de revisión muestra las siguientes columnas:

    - **Date**: La fecha de ejecución de la transacción.
    - **Type**: El tipo de operación financiera (COMPRA, VENTA, DIVIDENDO, DEPÓSITO, etc.).
    - **Asset**: El activo emparejado de su biblioteca.
    - **Quantity**: El número de unidades o acciones negociadas.
    - **Price**: El precio unitario del activo.
    - **Net Amount**: El impacto total de efectivo (positivo o negativo) en la cuenta.
    - **Fees/Taxes**: Comisiones del bróker o impuestos de transacción incluidos.
    
    Para configuraciones avanzadas o errores de validación en la carga, consulte la página **[Import from Broker](transactions/import/index.md)**.

---

## 📈 4. Retorno al Panel (Dashboard)

Después de importar con éxito su extracto, regrese al **Dashboard**.

LibreFolio calculará en tiempo real todas las métricas de su cartera, la asignación de activos (por tipo, sector, área geográfica) y el historial de rendimiento. ¡Ahora finalmente puede ver toda la situación actual de su cartera visualizada gráficamente!

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Dashboard Main View" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. ¿Qué Sigue?

Ahora que su cartera está poblada, puede:

- 🤝 **[Compartir su bróker](brokers/sharing.md)** — Conceda acceso a familiares o asesores.
- 💱 **[Configurar tasas de cambio](fx/index.md)** — Configure la conversión de divisas para carteras multidivisa.
- ⚙️ **[Personalizar configuración](../admin/settings.md)** — Ajuste el idioma, tema y preferencias del sistema.
