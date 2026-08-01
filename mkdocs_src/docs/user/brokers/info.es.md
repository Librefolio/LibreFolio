# ⚙️ Configuración del bróker & Exportación IA

La pestaña **Info** alberga la configuración de metadatos, controles de seguridad, la herramienta de Exportación IA acotada, y el panel de configuración de uso compartido.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vista de Información y Uso Compartido del Bróker">
</div>

---

## ⚙️ Metadatos y Configuración

La columna izquierda de la pestaña Info muestra las propiedades clave y las reglas de validación para este bróker:

- **Estado del Bróker**: Muestra si la cuenta está actualmente `Activa`. Los brókeres inactivos se ocultan en los menús desplegables de listas, pero sus valores históricos se conservan en los gráficos.
- **Fechas**: Muestra cuándo se abrió la cuenta y cuándo se creó en LibreFolio.
- **Moneda Base**: La moneda base de la cuenta (todas las transacciones y valoraciones se convierten internamente a esta moneda para los informes locales utilizando tipos de cambio históricos).
- **Permitir Sobregiro de Efectivo**: Un interruptor para eludir los errores de saldo negativo. Cuando está desactivado, LibreFolio bloquea las transacciones (como compras o retiros) que resultarían en un saldo de efectivo negativo.
- **Permitir Posiciones Cortas**: Un interruptor para autorizar cantidades negativas de activos. Cuando está desactivado, se bloquea la venta de más activos de los que tienes en tu posición abierta actual.

---

## 🧠 Exportación IA Acotada

En la parte superior derecha de la barra de herramientas del bróker,
**Exportación de IA** (:material-brain:) abre cuatro tareas de Bróker dedicadas,
no prompts de Cartera filtrados:

- **Análisis del bróker**
- **Eficiencia de costes del bróker**
- **Concentración en el bróker**
- **Análisis de lotes FIFO**

La instantánea del backend se limita al bróker seleccionado y puede incluir su
efectivo, posiciones, actividad, rendimiento, costes, concentración y lotes FIFO
según la tarea elegida. Los controles de acceso del servidor impiden exportar un
bróker al que el usuario actual no tenga acceso. LibreFolio solo copia el
resultado al portapapeles; revisa los datos financieros sensibles antes de
compartirlos. Consulta la
[guía de Exportación de IA](../ai-export/index.md).

---

## 🤝 Panel de Acceso Compartido

La columna derecha de la pestaña Info alberga el gestor de **Uso Compartido del Bróker** integrado. Aquí puedes:

- Invitar a otros usuarios por su correo electrónico o nombre de usuario.
- Definir su permiso de rol (Propietario, Editor, Visor).
- Configurar los porcentajes de propiedad.

Para una explicación detallada de las reglas de uso compartido, roles y la lógica de porcentajes, consulta la página dedicada **[Uso Compartido del Bróker](sharing.md)**.
