# 🚀 Primeros pasos

¡Bienvenido a LibreFolio! Esta guía te acompaña en el proceso de crear una cuenta, iniciar sesión e importar tu primer extracto de bróker para llenar tu panel de control al instante.

---

## 📝 1. Registra tu cuenta

Ve a la URL de LibreFolio (por ejemplo, `http://localhost:6040`) y verás la página de inicio de sesión. Haz clic en **Registrarse** para crear una nueva cuenta.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulario de registro" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Completa tus datos:

- 👤 **Usuario**: tu nombre para mostrar (único en todo el sistema)
- 📧 **Correo electrónico**: una dirección de correo válida
- 🔑 **Contraseña**: una contraseña segura (el indicador de fortaleza te ayuda)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registro con indicador de fortaleza de contraseña" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primer usuario = Administrador"

    El primer usuario que se registre se convierte automáticamente en el **administrador del sistema** (superusuario). Este usuario puede gestionar la configuración global, promover a otros usuarios y acceder a todas las funciones de administración.

---

## 🔐 2. Inicia sesión

Después de registrarte, serás redirigido a la página de inicio de sesión. Introduce tus credenciales para acceder a tu panel de control.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Página de inicio de sesión" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Importa tu primer extracto (crea el bróker y los activos sobre la marcha)

La primera vez que inicies sesión, verás un panel de control vacío, sin datos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Panel de control vacío" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

En LibreFolio, la forma más rápida de empezar es importando directamente tu historial de transacciones. No necesitas configurar brókers ni activos de antemano: el sistema los creará automáticamente por ti durante el proceso de importación.

### 📋 Pasos

1. **Abre el asistente de importación**: Ve a la página de **[Transacciones](transactions/index.md)** desde el menú de la barra lateral y haz clic en el botón **"Importar"** (:material-file-upload:). También puedes empezar desde la página de detalle de un bróker; en ese caso, el bróker ya viene preseleccionado.

2. **Sube tu extracto**: Arrastra el archivo de informe de tu bróker (`.csv`, `.xlsx` o `.xls`) al primer paso del asistente — aquí funciona arrastrar y soltar — y asígnalo a un bróker, creándolo **sobre la marcha** si es nuevo. Este paso es opcional: los informes subidos en sesiones anteriores ya están almacenados, y el siguiente paso los lista.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Paso de carga del asistente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

3. **Selecciona archivos y analiza**: Elige exactamente qué informes almacenados quieres importar. Cada archivo recibe su analizador preseleccionado según el complemento de importación predeterminado del bróker (se puede cambiar por archivo — usa **CSV genérico** para un formato desconocido); luego LibreFolio lee y valida cada fila. Un resumen consolidado muestra lo que realmente se importará: transacciones, valores distintos, problemas de validación, asuntos pendientes, advertencias y posibles duplicados.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Paso de análisis del asistente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

4. **Pasos adicionales, solo cuando sean necesarios**: Dependiendo de lo que contengan tus archivos, pueden aparecer hasta tres pasos más: **Unificar activos** (el mismo valor encontrado con diferentes nombres o códigos), **Correcciones** (filas que el analizador no pudo leer por completo) y **Duplicados** (el mismo movimiento presente en dos archivos importados juntos). Un informe limpio de un solo archivo se salta todos estos pasos.

5. **Revisa e importa**: Asocia cada instrumento con tu biblioteca de activos — o créalo **sobre la marcha** con los detalles precargados desde el extracto — y revisa los indicadores por fila: los duplicados (contra tu libro mayor existente, o copias exactas pendientes en esta importación) aparecen desmarcados, y las filas fechadas antes de la fecha de apertura del bróker se excluyen automáticamente. Para más información, consulta la guía **[Importación desde bróker - Asignación de activos](transactions/import/index.md#asset-mapping)**.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Paso de revisión del asistente: Resolución de activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

6. **Guarda desde el editor masivo**: Al hacer clic en **Importar N transacciones**, las filas seleccionadas se envían al editor masivo como filas nuevas; todavía no se guarda nada. Dales un último vistazo y haz clic en **Guardar todo** para confirmarlas en tu cartera.

!!! tip "No es necesario volver a subir"

    Los informes que subiste en sesiones anteriores ya aparecen en el paso **Seleccionar archivos** del asistente: solo tienes que volver a marcarlos. También puedes previsualizar o eliminar informes almacenados desde la página **[Archivos y subidas](files/index.md#broker-reports)**.

Para ver la guía completa, consulta **[Cómo importar transacciones](transactions/import/how-to.md)**; para conocer los brókers y formatos de archivo compatibles, consulta **[Importación desde bróker](transactions/import/index.md)**.

---

## 📈 4. Vuelve al Panel de control

Después de importar correctamente tu extracto, vuelve al **Panel de control**.

LibreFolio calcula las métricas de tu cartera, la asignación de activos (por tipo, sector y geografía) y el historial de rendimiento en tiempo real. ¡Ahora puedes ver toda tu situación financiera representada de forma gráfica!

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vista principal del panel de control" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 5. ¿Qué sigue?

Ahora que tu cartera tiene datos, puedes:

- 🤝 **[Comparte tu bróker](brokers/sharing.md)** — Da acceso a familiares o asesores.
- 💱 **[Configura los tipos de cambio (FX)](fx/index.md)** — Configura la conversión de divisa para carteras multidivisa.
- ⚙️ **[Personaliza la configuración](../admin/settings.md)** — Ajusta el idioma, el tema y las preferencias del sistema.
