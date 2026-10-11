# 🔐 Seguridad de la conexión

El indicador de seguridad de la conexión en la barra lateral de LibreFolio te dice si lo que escribes —tu contraseña, tus cifras— viaja cifrado entre tu dispositivo y tu servidor. Muestra uno de tres niveles, según la dirección que abriste y la red en la que estés. Haz clic en su fila para abrir o cerrar sus detalles: el motivo del nivel y el enlace **Cómo conectarse de forma segura**, que abre esta página.
Con la barra lateral contraída, el escudo muestra el nivel al pasar el cursor por encima, y al hacer clic se abre la barra lateral con los detalles.

Para máxima seguridad, asigna a LibreFolio una dirección HTTPS y úsala en todas partes, incluso en tu red doméstica.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="security" data-name="connection-indicator" alt="El indicador de seguridad de la conexión en la parte inferior de la barra lateral, abierto en Conexión: red local: su motivo, que cualquiera en la misma red puede leer el tráfico, y el enlace Cómo conectarse de forma segura" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🚦 Los tres niveles

### 🟢 Conexión: segura {: #connection-secure }

Verde: lo que escribes está cifrado, o nunca sale del servidor. Los detalles dan el motivo:

- HTTPS: la conexión está cifrada, y tu navegador la considera segura.
- En el propio servidor (`localhost`): el tráfico no sale de ese equipo.
- VPN (Tailscale): Tailscale cifra el tráfico entre tu dispositivo y el servidor, aunque la dirección empiece por `http://`, por ejemplo `http://100.110.x.x:6040`.

Con el motivo de VPN, la dirección sigue siendo `http://` sin cifrar, así que tu navegador no
[instalará LibreFolio como aplicación](pwa.md) desde ella: el [paso 1](#https-address) añade HTTPS.

### 🏠 Conexión: red local {: #connection-local-network }

Verde claro: abriste LibreFolio por `http://` sin cifrar dentro de tu red doméstica o de oficina, por
ejemplo `http://192.168.1.100:6040`, la dirección que usan otros dispositivos tras una
[instalación](installation.md) estándar. El tráfico no está cifrado: cualquiera en la misma red, como
un invitado en tu Wi-Fi, podría leerlo, contraseña incluida. Para la mejor seguridad, usa también la
dirección HTTPS en casa.

**Conexión: red local** también aparece, con un motivo que empieza por *Poco claro* en los detalles, cuando
la dirección que abriste y el origen que ve el servidor no coinciden: una dirección con aspecto público que el
servidor ve provenir de tu red local (DNS dividido, o un proxy local), o una dirección local o de Tailscale
que el servidor ve provenir de internet. El tráfico no está cifrado, y
LibreFolio no puede saber dónde estás realmente: usa la dirección HTTPS.

### 🔴 Conexión: no segura {: #connection-not-secure }

Rojo: llegaste a LibreFolio por `http://` sin cifrar desde internet, por ejemplo a través de un puerto
abierto en tu router. Las contraseñas y los datos viajan en texto plano por redes que no controlas:
cualquiera en el camino podría leerlos, o incluso cambiarlos. En un teléfono, un punto rojo en el botón
de menú te advierte incluso mientras la barra lateral está cerrada.

Evita esta dirección. Si ejecutas el servidor, asigna a LibreFolio una dirección HTTPS
([paso 1](#https-address)) y deja de exponer HTTP sin cifrar. Luego cambia tu contraseña:
**Configuración** → [**Perfil**](settings/profile.md) → **Cambiar contraseña**.

??? info "🔍 Cómo se elige el nivel"

    Tu navegador clasifica la dirección que escribiste en uno de cuatro tipos:

    - este equipo: `localhost` y direcciones de bucle invertido;
    - Tailscale: `100.64.0.0/10`, `fd7a:115c:a1e0::/48` y nombres que terminan en `.ts.net`;
    - red local: direcciones `10.x`, `172.16.x` a `172.31.x`, `192.168.x` y `169.254.x`, direcciones IPv6
      de enlace local y locales únicas, y nombres que terminan en `.local`, `.lan`, `.home.arpa` o
      `.internal`, o sin ningún punto;
    - internet: todo lo demás.

    HTTPS siempre es seguro. HTTP sin cifrar cuenta como seguro para `localhost`, y para una dirección de Tailscale
    a menos que el servidor vea que la solicitud proviene de internet.

    El servidor clasifica la dirección desde la que proviene cada solicitud en los mismos tipos e informa solo el
    tipo, nunca tu dirección IP. Puede confirmar el veredicto del navegador o hacerlo incierto, pero
    nunca hacer que una conexión cuente como segura. Hasta que responda, prevalece el veredicto del navegador.

---

## 🔒 Cómo conectarse de forma segura

### 🌐 1. Asigna a LibreFolio una dirección HTTPS {: #https-address }

Esto es tarea de quien ejecuta el servidor: si no eres tú, pídele la dirección HTTPS. Dos
formas:

- Tailscale: sigue [Exponer de forma segura](../admin/service_exposure.md). Con su Nivel 1 (VPN privada) configurado, ejecuta `tailscale serve --bg 6040` en el servidor (o tu propio `PORT`), y luego abre
  `https://<server-name>.your-tailnet.ts.net`. Para una dirección HTTPS pública que no necesite Tailscale
  en tus dispositivos, usa Funnel (Niveles 3 y 4).
- Un proxy inverso con un certificado TLS, como Caddy, Traefik o Nginx: consulta
  [Docker avanzado](../admin/docker_advanced.md).

Tailscale, Caddy y Traefik informan a LibreFolio sobre HTTPS por sí solos; Nginx necesita dos líneas: consulta
[Detrás de un proxy inverso](#reverse-proxy).

### 🔖 2. Usa la dirección HTTPS en todas partes

Úsala en todos los dispositivos, también en casa:

- Marca como favorito `https://…`, no `http://192.168.x.x:6040`.
- Actualiza los marcadores antiguos y los accesos directos de la pantalla de inicio que todavía apunten a `http://`.
- Abre LibreFolio desde la nueva dirección: el indicador muestra **Conexión: segura**.

---

## 🧰 Detrás de un proxy inverso {: #reverse-proxy }

*Para administradores.* Un proxy inverso recibe la conexión HTTPS y la pasa a LibreFolio
por HTTP sin cifrar. Lo que importa ahí es la cookie de sesión que te mantiene conectado: con
`SESSION_COOKIE_SECURE=auto`, el valor predeterminado, LibreFolio la marca como `Secure` (se envía solo por HTTPS) cuando
la solicitud es HTTPS, ya sea directamente o porque el proxy envía `X-Forwarded-Proto: https`.

Tailscale Serve y Funnel, Caddy y Traefik envían ese encabezado por sí solos. Caddy y Traefik también
pasan tu dirección en `X-Forwarded-For`, lo que permite que el indicador vea desde dónde te conectas. Nginx
necesita ambas líneas en el bloque `location` que pasa las solicitudes a LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Si tu navegador usa HTTPS pero la cookie de sesión no está marcada como `Secure`, porque el proxy no
envía `X-Forwarded-Proto` o porque `SESSION_COOKIE_SECURE` es `never`, los administradores ven una línea más
en los detalles del indicador. El nivel sigue siendo **Conexión: segura**, porque la conexión está
cifrada; solo la cookie carece de `Secure`:

> Tu navegador usa HTTPS, pero la cookie de sesión no está marcada como Secure. Haz que el proxy inverso envíe
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), o vuelve a poner
> SESSION_COOKIE_SECURE en auto si está en never.

??? tip "⚙️ Configura `SESSION_COOKIE_SECURE` en su lugar"

    Enviar el encabezado es la mejor solución. Si solo accedes a LibreFolio por HTTPS, puedes
    añadir esta línea a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Luego reinicia LibreFolio: con Docker, ejecuta `docker compose up -d` (un simple
    `docker compose restart` mantiene el entorno antiguo); en una instalación en host, reinicia
    `./dev.py server`, que también lee `.env`.

    La opción acepta `auto` (el valor predeterminado), `always` o `never`; no distingue entre mayúsculas y minúsculas ni espacios, y
    cualquier otro valor impide que LibreFolio se inicie. Usa `never` solo para el raro proxy que afirma usar
    HTTPS mientras el navegador está en HTTP sin cifrar. Consulta [Configuración](../admin/configuration.md) para
    todas las opciones.

---

## 🧭 Lo que el indicador no hace

- No bloquea nada: es un aviso, no una comprobación.
- Describe la conexión que estás usando en este momento: el mismo LibreFolio puede mostrar
  **Conexión: segura** en tu portátil y **Conexión: no segura** en tu teléfono.
- No comprueba los certificados: un certificado autofirmado que aceptaste en el navegador muestra
  **Conexión: segura**. El tráfico está cifrado, pero nadie garantiza que el servidor sea realmente
  tuyo.
- No siempre puede ver dónde estás. Con Docker Desktop expuesto directamente, o detrás de un proxy que
  no pasa tu dirección en `X-Forwarded-For`, el servidor ve a cada visitante como local: HTTP sin cifrar desde internet entonces muestra
  **Conexión: red local**, como poco clara, en lugar de **Conexión: no segura**. Docker Engine en Linux conserva tu dirección. El consejo no
  cambia: usa la dirección HTTPS.

---

## 🔗 Relacionado

- 🌐 **[Exponer de forma segura](../admin/service_exposure.md)** — Tailscale, desde una VPN privada hasta una
  dirección HTTPS pública
- 🐳 **[Docker avanzado](../admin/docker_advanced.md)** — Archivo Compose, variables de entorno,
  proxy inverso
- 📝 **[Configuración](../admin/configuration.md)** — Todas las opciones del archivo `.env`
- 📦 **[Instalación con Docker](installation.md)** — Acceso local y remoto después de instalar
- 📱 **[Instalar como aplicación (PWA)](pwa.md)** — Requiere una dirección HTTPS
