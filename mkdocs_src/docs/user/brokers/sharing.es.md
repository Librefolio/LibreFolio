# 🤝 Compartir bróker

LibreFolio te permite compartir el acceso a tus cuentas de corretaje con otros usuarios. Esto es útil para familias, asesores financieros o contadores que necesitan visibilidad sobre tu cartera.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Broker Sharing Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Cómo compartir

Solo un **Propietario** del bróker puede gestionar el acceso. Puedes abrir el panel para compartir de dos maneras:

- **Desde la lista de brókers**: haz clic en el icono **Compartir** (:material-share-variant:) en la tarjeta del bróker — se abre el **Modal de Compartir**.
- **Desde la página de detalle del bróker**: haz clic en el botón **Compartir** del encabezado — llegarás a la pestaña **Información**, que aloja el panel para compartir.

Luego:

1. **Busca** al usuario por nombre de usuario
2. **Selecciona un rol** (Visor, Editor o Propietario)
3. **Define el porcentaje de participación** — solo para el rol de *Propietario* (arrastra el control deslizante o escribe un valor; los Visores y Editores siempre llevan un 0%)
4. Haz clic en **Guardar** para aplicar los cambios

!!! warning "Solo los Propietarios pueden gestionar el acceso"

    Debes ser **Propietario** del bróker para añadir, eliminar o modificar el acceso de otros usuarios. Quienes no son propietarios ven el mismo panel en modo de solo lectura.

---

## 🛡️ Roles de acceso

Al compartir un bróker, asignas un **rol** que determina qué puede hacer el otro usuario:

| Característica | Visor | Editor | Propietario |
|:-------------------------------------|:------:|:------:|:-----:|
| **Ver detalles del bróker** | ✅ | ✅ | ✅ |
| **Ver transacciones** | ✅ | ✅ | ✅ |
| **Ver informes y gráficos** | ✅ | ✅ | ✅ |
| **Añadir/editar transacciones** | ❌ | ✅ | ✅ |
| **Importar archivos (BRIM)** | ❌ | ✅ | ✅ |
| **Editar configuración del bróker** | ❌ | ✅ | ✅ |
| **Gestionar acceso (añadir/eliminar usuarios)** | ❌ | ❌ | ✅ |
| **Eliminar bróker** | ❌ | ❌ | ✅ |

- 👁️ **Visor**: acceso de solo lectura. Ideal para contadores o familiares que solo necesitan ver los datos.
- ✏️ **Editor**: puede gestionar las operaciones del día a día (transacciones, importaciones), pero no puede eliminar el bróker ni cambiar los accesos.
- 👑 **Propietario**: control total. Puede hacerlo todo, incluido añadir o eliminar a otros usuarios. Un bróker puede tener **más de un Propietario** — consulta el porcentaje de participación a continuación.

---

## 📊 Porcentaje de participación

Cada **Propietario** de un bróker tiene un **porcentaje de participación** (del 0% al 100%). Este representa qué parte del valor de la cartera del bróker pertenece a ese propietario. Los Visores y Editores siempre llevan un 0% — el esquema rechaza cualquier participación distinta de cero para ellos.

!!! example "Cuenta conjunta"

    Tú y tu cónyuge son copropietarios de una cuenta de corretaje al 50/50. Ambos son Propietarios:

    - Tú (Propietario): **50%**
    - Cónyuge (Propietario): **50%**

    Cada uno de ustedes ve el 50% del valor de este bróker contabilizado en su propio panel de control.

!!! example "Asesor financiero"

    Tu asesor financiero necesita ver tu cartera, pero no posee ninguna parte de ella:

    - Tú (Propietario): **100%**
    - Asesor (Visor): **0%**

La suma de todos los porcentajes de participación de un bróker **no debe superar el 100%**, pero puede ser menor (por ejemplo, una cuenta en copropiedad en la que el copropietario no está en el sistema). El panel muestra los totales de **Asignado** y **Disponible** mientras editas.

!!! note "Agregación de cartera"

    El porcentaje de participación **ya está aplicado** a la agregación de tu cartera: el panel de control y las estadísticas a nivel de cartera escalan cada importe de un bróker compartido según tu participación en la propiedad. Un Propietario con un 50% ve la mitad del valor, de los ingresos y del P&L de ese bróker contabilizada en sus totales. Los Visores y Editores, cuya participación siempre es 0% por regla, ven en su lugar los importes **completos** del bróker; la participación solo escala lo que *posees*.

---

## 🚪 Salir de un bróker compartido (Autoservicio)

Nunca necesitas la intervención de un Propietario para salir de un bróker al que tengas acceso. En el panel para compartir, la sección **Tu acceso** te permite:

- **Salir del bróker** — elimina tu propio acceso de inmediato. El bróker desaparece de tus listas.
- **Cambiar a visor** — un Editor puede degradarse a Visor; un Propietario puede volver a ascenderlo más tarde.

!!! danger "Último Propietario: salir elimina el bróker"

    Si eres el **único Propietario** restante, la acción de salida se convierte en **Salir y eliminar el bróker**: salir *elimina permanentemente el bróker junto con todas sus transacciones y archivos de informes importados*. Esto no se puede deshacer. Si no es lo que quieres, asigna primero a otro usuario como Propietario y luego sal.

---

## 💡 Escenarios comunes

| Escenario | Configuración sugerida |
|----------|----------------|
| **Cónyuge / Pareja** | Dos Propietarios, 50% cada uno |
| **Asesor financiero** | Visor, 0% de participación |
| **Contador** | Visor, 0% de participación |
| **Familiar** | Visor o Editor, 0% de participación |
