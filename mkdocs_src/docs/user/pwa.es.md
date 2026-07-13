# 📱 Instalar como Aplicación (PWA)

LibreFolio puede instalarse como una **Aplicación Web Progresiva (PWA)** en tu dispositivo. Esto te brinda una experiencia similar a la de una aplicación: modo de pantalla completa, sin barra de direcciones del navegador y un icono en la pantalla de inicio, sin necesidad de descargarla de una tienda de aplicaciones.

---

## ✅ Qué Obtienes

| Característica | Descripción |
|---------|-------------|
| **Modo de pantalla completa** | Sin barra de direcciones ni elementos superfluos de la interfaz del navegador |
| **Icono en la pantalla de inicio** | Inicia LibreFolio como una aplicación nativa |
| **Sin interferencia de gestos** | Desplazamiento hacia atrás y zoom de doble toque desactivados |
| **Sesión persistente** | Permanece conectado entre inicios de sesión |

!!! note "Online Only"

    La PWA de LibreFolio requiere una conexión de red activa. No existe un modo offline; tus datos residen en tu servidor.

---

## 📲 Cómo Instalar

### Android (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Busca el botón **"Instalar aplicación"** en el menú de **Ayuda y soporte** (icono ❓ arriba a la derecha)
3. Pulsa **Instalar** cuando se te solicite
4. LibreFolio aparecerá en tu pantalla de inicio

!!! tip "Alternative method"

    Si el botón de Instalación no aparece, pulsa el **menú ⋮ del navegador → "Agregar a la pantalla de inicio"** o **"Instalar aplicación"**.

### iOS (Safari)

1. Abre LibreFolio en **Safari** (obligatorio; otros navegadores no soportan PWA en iOS)
2. Pulsa el botón **Compartir** (cuadrado con flecha)
3. Desplázate hacia abajo y pulsa **"Agregar a la pantalla de inicio"**
4. Pulsa **Agregar**

!!! warning "iOS Limitation"

    El aviso de instalación automática no está disponible en iOS. Utiliza el menú de Compartir como se describe anteriormente. El menú de Ayuda mostrará instrucciones si estás en un dispositivo iOS.

### Escritorio (Chrome / Edge)

1. Abre LibreFolio en Chrome o Edge
2. Haz clic en el botón **"Instalar aplicación"** en el menú de Ayuda y soporte
3. O haz clic en el icono de instalación (⊕) en la barra de direcciones del navegador
4. LibreFolio se abre en su propia ventana

---

## 🌐 HTTP vs HTTPS

<table style="width: 100%; border-collapse: collapse; margin-top: 1rem; margin-bottom: 1rem;">
 <thead>
 <tr style="background-color: #f3f4f6;">
 <th style="width: 45%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Configuración</th>
 <th style="width: 25%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Instalación PWA</th>
 <th style="width: 30%; padding: 10px; border: 1px solid #e5e7eb; text-align: left; font-weight: bold;">Aviso automático</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>https://</code> (Tailscale, reverse proxy)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Soporte completo</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Chrome muestra el banner</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap;"><code>http://localhost</code></td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Funciona</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb;">✅ Funciona</td>
 </tr>
 <tr>
 <td style="padding: 10px; border: 1px solid #e5e7eb; white-space: nowrap; background-color: rgba(244, 67, 54, 0.04);"><code>http://192.168.x.x</code> (LAN)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ No disponible (se requiere HTTPS)</td>
 <td style="padding: 10px; border: 1px solid #e5e7eb; background-color: rgba(244, 67, 54, 0.04);">❌ Sin aviso automático</td>
 </tr>
 </tbody>
</table>

!!! warning "HTTPS Connection Requirement for PWA"

    Para instalar LibreFolio como una PWA, **los navegadores modernos requieren estrictamente una conexión segura HTTPS** (excepto cuando se accede a través de `localhost` o `127.0.0.1` para desarrollo local).

    Si abres LibreFolio a través de HTTP simple en tu red local (por ejemplo, `http://192.168.1.100:6040`), la instalación de la PWA no estará disponible y la aplicación no podrá ejecutarse en modo autónomo.

    Puedes elegir cualquier método que prefieras para habilitar HTTPS en tu instancia, pero recomendamos encarecidamente nuestra guía sencilla y gratuita: **[Guía de Exposición de Tailscale](../admin/tailscale_exposure.md)**. Te proporciona una URL HTTPS segura sin configurar certificados SSL ni abrir puertos del router.

---

## 🔧 Solución de Problemas

| Problema | Solución |
|---------|----------|
| El botón de Instalación no aparece | Es posible que ya esté instalada, o estés accediendo a través de HTTP en una red local (LAN) |
| iOS: no hay opción de instalar | Debes usar **Safari**; Chrome/Firefox en iOS no soportan PWA |
| La aplicación no se actualiza | Cierra y vuelve a abrir la aplicación; siempre obtiene la versión más reciente |
| Sesión perdida después de actualizar | Inicia sesión nuevamente; esto es normal tras reinicios del servidor |
