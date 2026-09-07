# ⚙️ Configuración del bróker y Exportación IA

La pestaña **Info** alberga la configuración de metadatos, los controles de seguridad, la herramienta de Exportación IA acotada y el panel de configuración de uso compartido.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vista de información y uso compartido del bróker">
</div>

---

## ⚙️ Metadatos y Configuración

La columna izquierda de la pestaña Info muestra las propiedades clave y las reglas de validación de este bróker:

- **Estado del bróker**: Muestra si la cuenta está actualmente `Active`. Los brókeres inactivos se ocultan de los menús desplegables, pero sus valores históricos se conservan en los gráficos.
- **Fechas**: Muestra cuándo se abrió la cuenta y cuándo se creó en LibreFolio.
- **Moneda base**: La moneda base de la cuenta (todas las transacciones y valoraciones se convierten internamente a esta moneda utilizando tipos de cambio históricos para los informes locales).
- **Permitir sobregiro de efectivo**: Un interruptor para omitir los errores de saldo negativo. Cuando está deshabilitado, LibreFolio bloquea las transacciones (como compras o retiros) que resultarían en un saldo de efectivo negativo.
- **Permitir posiciones cortas**: Un interruptor para autorizar cantidades negativas de activos. Cuando está deshabilitado, se bloquea vender más del tamaño de su posición abierta actual.

---

## 🧠 Exportación IA Acotada

En la parte superior derecha de la barra de herramientas del bróker, **Exportación IA** (:material-brain:) abre tres tareas dedicadas de bróker, no prompts de cartera filtrados:

- **Revisión del bróker**
- **Rendimiento del bróker y factores de mercado**
- **Estrategias de Compensación de Pérdidas de Capital**

La instantánea del backend se limita al bróker seleccionado y puede incluir su efectivo, posiciones, actividad, rendimiento, costos, concentración y lotes FIFO según la tarea seleccionada. Las comprobaciones de acceso del lado del servidor impiden exportar un bróker al que el usuario actual no puede acceder. LibreFolio solo copia el resultado al portapapeles; revise los datos financieros sensibles antes de compartirlos. Consulte [Exportación IA del bróker](../ai-export/broker.md) o la [Descripción general de la Exportación IA](../ai-export/index.md).

---

## 🤝 Panel de Uso Compartido de Acceso

La columna derecha de la pestaña Info alberga el gestor integrado de **uso compartido del bróker**. Aquí puede:

- Invitar a otros usuarios por su correo electrónico o nombre de usuario.
- Definir su permiso de rol (Propietario, Editor, Visor).
- Configurar los porcentajes de propiedad.

Para una explicación detallada de las reglas de uso compartido, los roles y la lógica de porcentajes, consulte la página dedicada **[Broker Sharing](sharing.md)**.
