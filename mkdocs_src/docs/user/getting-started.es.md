# 🚀 Primeros Pasos

¡Bienvenido a LibreFolio! Esta guía le guiará en el proceso de registro de una cuenta, el inicio de sesión y la creación de su primer bróker: todo lo que necesita para empezar a hacer el seguimiento de su cartera.

---

## 📝 1. Registrar su Cuenta

Navegue a la URL de LibreFolio (por ejemplo, `http://localhost:8000`) y verá la página de inicio de sesión. Haga clic en **Registrarse** para crear una cuenta nueva.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulario de Registro" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Complete sus datos:

- 👤 **Nombre de usuario**: Su nombre de usuario (único en todo el sistema)
- 📧 **Email**: Una dirección de correo electrónico válida
- 🔑 **Contraseña**: Una contraseña segura (el indicador de fuerza le ayudará)

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registro con Fuerza de Contraseña" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primer Usuario = Administrador"

    El primer usuario en registrarse se convierte automáticamente en el **administrador del sistema** (superuser). Este usuario puede gestionar la configuración global, promover a otros usuarios y acceder a todas las funciones de administración.

---

## 🔐 2. Iniciar Sesión

Después de registrarse, será redirigido a la página de inicio de sesión. Introduzca sus credenciales para acceder a su panel de control.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="auth" data-name="01-login" alt="Página de Inicio de Sesión" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🏦 3. Crear su Primer Bróker

Un **Bróker** en LibreFolio representa una cuenta de corretaje: el lugar donde residen sus inversiones (por ejemplo, Interactive Brokers, Degiro, una cuenta bancaria, etc.).

!!! note "¿Por qué necesito un Bróker?"

    Todas las transacciones en LibreFolio están vinculadas a un bróker. Es el contenedor que agrupa sus operaciones, importaciones e informes. Necesita al menos un bróker antes de poder empezar a hacer el seguimiento de cualquier cosa.

### 📋 Pasos

1. Navegue a la página de **Brokers** desde la barra lateral
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="list" alt="Lista de Brókers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
2. Haga clic en el botón **"Nuevo Bróker"**
3. Complete los detalles del bróker:
 - 🏷️ **Nombre**: Un nombre descriptivo (por ejemplo, "Mi Cuenta de Degiro")
 - 💰 **Moneda base**: La moneda de la cuenta (por ejemplo, EUR, USD)
 - 🖼️ **Icono** *(opcional)*: Suba un logotipo o avatar del bróker
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Lista de Brókers" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>
4. Una vez creado, puede hacer clic en un bróker para ver sus detalles, importar informes y gestionar transacciones.
 <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="detail" alt="Detalle del Bróker" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
 </div>

---

## 🔮 4. ¿Qué sigue?

Ahora que tiene una cuenta y un bróker, puede:

- 📤 **[Subir informes del bróker](files/index.md)** — Importe archivos CSV/Excel de su bróker para el procesamiento automático de transacciones
- 🤝 **[Compartir su bróker](brokers/sharing.md)** — Dé acceso a familiares, asesores o contadores
- 💱 **[Configurar tipos de cambio FX](fx/index.md)** — Configure la conversión de moneda para carteras multidivisa
- ⚙️ **[Personalizar configuración](../admin/settings.md)** — Ajuste el idioma, el tema y las preferencias del sistema

!!! tip "Cálculos de Cartera"

    Los brókers también se utilizan para los cálculos de agregación de la cartera. Cuando comparte un bróker con otro usuario y establece un **porcentaje de participación**, el sistema puede calcular la parte de cada usuario del valor total de la cartera. Esta función se encuentra en desarrollo activo.
