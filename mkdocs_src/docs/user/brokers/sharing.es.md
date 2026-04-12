# 🤝 Compartir Bróker

LibreFolio le permite compartir el acceso a sus cuentas de corretaje con otros usuarios. Esto es útil para familias, asesores financieros o contadores que necesiten visibilidad de su cartera.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="sharing-modal" alt="Modal de Compartir Bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 📋 Cómo Compartir

1. Navegue a la página de detalles de un bróker
2. Haga clic en el botón **Compartir** (:material-share-variant:) en el encabezado
3. Se abrirá el **Modal de Compartir Bróker**
4. **Busque** al usuario por su nombre de usuario
5. **Seleccione un rol** (Visor, Editor o Propietario)
6. **Establezca el porcentaje de participación** (arrastre el deslizador o escriba el valor)
7. Haga clic en **Guardar** para aplicar los cambios

!!! warning "Solo los Propietarios pueden gestionar el acceso"

    Debe ser el **Propietario** del bróker para agregar, eliminar o modificar el acceso de otros usuarios.

---

## 🛡️ Roles de Acceso

Cuando comparte un bróker, asigna un **rol** que determina qué puede hacer el otro usuario:

| Función | Visor | Editor | Propietario |
|:-------------------------------------|:------:|:------:|:-----:|
| **Ver Detalles del Bróker** | ✅ | ✅ | ✅ |
| **Ver Transacciones** | ✅ | ✅ | ✅ |
| **Ver Reportes y Gráficos** | ✅ | ✅ | ✅ |
| **Agregar/Editar Transacciones** | ❌ | ✅ | ✅ |
| **Importar Archivos (BRIM)** | ❌ | ✅ | ✅ |
| **Editar Configuración del Bróker** | ❌ | ✅ | ✅ |
| **Gestionar Acceso (Agregar/Eliminar Usuarios)** | ❌ | ❌ | ✅ |
| **Eliminar Bróker** | ❌ | ❌ | ✅ |

- 👁️ **Visor**: Acceso de solo lectura. Ideal para contadores o familiares que solo necesitan ver los datos.
- ✏️ **Editor**: Puede gestionar las operaciones diarias (transacciones, importaciones) pero no puede eliminar el bróker ni cambiar los accesos.
- 👑 **Propietario**: Control total. Puede hacer todo, incluyendo agregar o eliminar otros usuarios.

---

## 📊 Porcentaje de Participación

Cada usuario con acceso a un bróker tiene un **porcentaje de participación** (0% a 100%). Esto representa cuánto del valor de la cartera del bróker pertenece a ese usuario.

!!! example "Cuenta Conjunta"

    Usted y su cónyuge comparten una cuenta de corretaje al 50/50:

    - Usted (Propietario): **50%**
    - Cónyuge (Editor): **50%**

    Al calcular el valor total de la cartera, el sistema cuenta el 50% del valor de este bróker para cada uno de ustedes.

!!! example "Asesor Financiero"

    Su asesor financiero necesita ver su cartera pero no es dueño de ninguna parte de ella:

    - Usted (Propietario): **100%**
    - Asesor (Visor): **0%**

La suma de todos los porcentajes de participación de un bróker **no debe exceder el 100%**, pero puede ser menor (por ejemplo, una cuenta en copropiedad donde el copropietario no esté en el sistema).

---

## 💡 Escenarios Comunes

| Escenario | Configuración Sugerida |
|----------|----------------|
| **Cónyuge / Pareja** | Editor o co-Propietario, 50% de participación cada uno |
| **Asesor Financiero** | Visor, 0% de participación |
| **Contador** | Visor, 0% de participación |
| **Familiar** | Visor o Editor, % de participación personalizado |

!!! note "Agregación de Cartera"

    El porcentaje de participación está diseñado para futuras funciones de agregación de cartera. Cuando estas se implementen, el panel de control de cada usuario mostrará su parte proporcional de todos los brókers a los que tenga acceso.
