# 👤 Perfil

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="profile" alt="Perfil">
</div>

La pestaña **Perfil** gestiona tu **identidad** en LibreFolio — quién eres y cómo inicias sesión. Las opciones de visualización (idioma, moneda, tema) se encuentran en **[Preferencias](preferences.md)**; las opciones de toda la instancia, en la **[pestaña Admin](../../admin/settings.md)**.

## 🔒 Bloqueo de edición

La pestaña se abre **bloqueada**: los campos son de solo lectura hasta que hagas clic en el ✏️ **botón de lápiz** de la cabecera. Esto evita ediciones accidentales. Si vuelves a bloquear la pestaña con cambios sin guardar, un diálogo de confirmación pregunta si deseas descartarlos.

Mientras está desbloqueada, cada campo modificado muestra sus propios botones de **guardar** / **deshacer**, y la cabecera ofrece **guardar todo** y **deshacer todo** para acciones masivas.

## 🖼️ Avatar

Pasa el cursor sobre tu avatar (con la pestaña desbloqueada) y haz clic en la superposición de la 📷 cámara para abrir el selector de imágenes: elige una imagen existente de la [biblioteca de Archivos](../files/index.md) o sube una nueva. Las subidas pasan por la **[herramienta de Recorte de imagen](../misc/image-crop.md)** con el ajuste preestablecido *avatar* (recorte cuadrado, vista previa circular).

El avatar se guarda inmediatamente y se utiliza en toda la aplicación allí donde se muestra tu identidad — barra lateral, uso compartido de brókeres y listas de colaboradores.

## ✏️ Nombre de usuario, Correo electrónico, Cuenta creada

- **Nombre de usuario** y **Correo electrónico** son editables (se requiere la pestaña desbloqueada). Los cambios se aplican de inmediato a tus credenciales de inicio de sesión.
- **Cuenta creada** es un campo de solo lectura que muestra tu fecha de registro.

## 🔐 Seguridad

### 🔑 Cambiar contraseña

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Cambiar contraseña">
</div>

El botón **Cambiar contraseña** (siempre disponible, sin necesidad de desbloqueo) abre un modal que requiere:

1. Tu **contraseña actual** (para verificación)
2. Una **nueva contraseña** que cumpla todas las reglas: mínimo 8 caracteres, al menos una letra mayúscula, una letra minúscula, un número y un carácter especial — y debe ser diferente de la actual
3. La **confirmación** de la nueva contraseña

Después de la confirmación, tu sesión permanece activa — no necesitas volver a iniciar sesión.

### 🗑️ Eliminar cuenta

El botón **Eliminar cuenta** elimina permanentemente tu usuario y todo lo que le pertenece. Para confirmar, debes escribir tu **nombre de usuario** en el diálogo. La eliminación es inmediata: se cierra tu sesión y vuelves a la página de inicio de sesión.

!!! warning "Irreversible"

    Eliminar tu cuenta no se puede deshacer: tus brókeres, transacciones y configuración se eliminan con ella. Si eres el **único administrador** de la instancia, se rechaza la eliminación — promueve primero a otro usuario.

---

## 🔗 Relacionados

- 🎛️ **[Preferencias de usuario](preferences.md)** — Idioma, moneda base y tema
- ⚙️ **[Descripción general de Configuración](index.md)** — Resumen general de la configuración
- ℹ️ **[Acerca de](about.md)** — Información de versión, plugins y changelog
- 🛡️ **[Configuración global](../../admin/settings.md)** — Opciones de toda la instancia (admin)
