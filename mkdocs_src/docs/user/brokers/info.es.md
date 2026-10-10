# ⚙️ Configuración e información del bróker

La pestaña **Info** de un bróker muestra los detalles de la cuenta a la izquierda y quién puede acceder a él a la derecha.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vista de información y uso compartido del bróker">
</div>

---

## 📋 Detalles de la cuenta

La tarjeta **Detalles** enumera:

- **Cuenta activa** — **✓ Activa**, o **✗ Cerrada** para una cuenta que ya no usas. Un bróker cerrado conserva su historial en tus gráficos.
- **Cuenta abierta** — cuándo abriste la cuenta, si introdujiste esa fecha.
- **Permitir compra apalancada** y **Permitir ventas en corto** — las dos opciones de negociación, explicadas a continuación.
- **Creado en el sistema** — cuándo se añadió el bróker a LibreFolio.

Para cambiarlos, haz clic en **Editar** en la barra de herramientas del bróker (Propietarios y Editores).

---

## 🛡️ Opciones de negociación {: #trading-options }

Ambas opciones están desactivadas para un bróker nuevo, y en ese caso LibreFolio te protege contra saldos imposibles:

- con **Permitir compra apalancada** desactivada, se rechaza un guardado si dejaría el efectivo de una divisa por debajo de cero;
- con **Permitir ventas en corto** desactivada, se rechaza un guardado si dejaría la cantidad de un activo por debajo de cero.

Activa una opción para una cuenta de margen, o para registrar ventas en corto.

??? note "📅 Cómo se comprueban los saldos — cuándo se rechaza un guardado"

    Para cada divisa $c$ y cada activo $i$ del bróker, LibreFolio examina el saldo al **final de cada día** $d$, después de todas las transacciones de ese día:

    $$
    C_c(d) = \sum_{\text{date}_t \le d} a_t \ge 0 \qquad\qquad Q_i(d) = \sum_{\text{date}_t \le d} q_t \ge 0
    $$

    Aquí $a_t$ es el importe en efectivo de cada transacción $t$ en la divisa $c$, y $q_t$ la cantidad de cada transacción del activo $i$. El dinero que entra y sale el mismo día se compensa, pero un depósito realizado más tarde no arregla un día que ya cerró por debajo de cero.

    Un guardado rechazado aparece en el espacio de trabajo bajo *Esta configuración provoca inconsistencias en los datos*, con la divisa o el activo, la fecha y enlaces a las filas del espacio de trabajo implicadas.

---

## 🤝 Compartir el bróker

La columna derecha contiene el panel **Compartir bróker**; **Compartir bróker** en la barra de herramientas también te trae aquí. Solo un Propietario puede cambiarlo: todos los demás lo ven en modo de solo lectura.

Para dar acceso a alguien:

1. Haz clic en **+** (**Añadir usuario**) bajo el gráfico de propietarios y busca a la persona **por nombre de usuario**.
2. Elige el **Rol** — **Lector** por defecto, **Editor** o **Propietario** — y, para un Propietario, el **Porcentaje de propiedad**. Después haz clic en **Añadir usuario**.
3. Haz clic en **Guardar configuración**: nada cambia antes de que lo hagas.

Guarda antes de cambiar de pestaña: en la pestaña Info, los cambios sin guardar se descartan sin preguntar.

En **Tu acceso** también puedes **Abandonar bróker**, o **Cambiar a lector** si eres un Editor. Los roles y las cuotas de propiedad se explican en [Uso compartido del bróker](sharing.md).

---

## 🔗 Relacionado

- 🧠 **[Exportación IA del bróker](../ai-export/broker.md)** — **Exportación IA** se encuentra en la barra de herramientas del bróker y funciona desde todas las pestañas.
- 🏦 **[Brókers](index.md)** — crear un bróker y sus campos opcionales.
