# 🔍 Comprobar la seguridad de la conexión

Cada usuario ve, en la parte inferior de la barra lateral de LibreFolio, lo segura que es la
comunicación entre su navegador y el servidor: **Conexión: segura**, **Conexión: red local** o
**Conexión: no segura**. La guía del usuario, [Seguridad de la conexión](../user/connection-security.md),
le explica los tres niveles. Esta página es para quien gestiona el servidor: cómo comprobar que tu
instalación da a sus usuarios **Conexión: segura**, y cómo corregirla cuando no es así.

El objetivo es una dirección HTTPS, de Tailscale Serve o Funnel
([Exponer de forma segura](service_exposure.md)) o de un proxy inverso con un certificado
([Detrás de un proxy inverso](#reverse-proxy)), y una cookie de sesión marcada como `Secure`.

---

## ✅ Lista de comprobación {: #checklist }

Recórrela una vez que tu dirección HTTPS funcione, y de nuevo tras cualquier cambio en el proxy o en
`.env`. Necesitas una cuenta de administrador y, para las dos últimas comprobaciones, un teléfono con
datos móviles.

1. **Abre la dirección HTTPS e inicia sesión.** El indicador muestra 🟢 **Conexión: segura**, y sus
   detalles dicen que la conexión está cifrada con HTTPS.
2. **Busca la línea de la cookie.** Con la sesión de administrador, los detalles muestran solo ese
   motivo y el enlace **Cómo conectarse de forma segura**. Una línea más, sobre la cookie de sesión,
   significa que LibreFolio no sabe que hay HTTPS: consulta [Detrás de un proxy inverso](#reverse-proxy).
3. **Pregunta al servidor.** En una pestaña nueva, abre `https://<your address>/api/v1/system/connection`:
   la respuesta contiene `"cookie_secure":true` ([El punto de vista del servidor](#server-view)).
4. **Si quieres, mira la cookie.** En las herramientas para desarrolladores del navegador, la cookie
   `session` está marcada como `Secure` ([La cookie de sesión](#session-cookie)).
5. **Desde fuera, abre la dirección HTTPS.** En el teléfono, con el Wi-Fi apagado, la página carga
   y, una vez iniciada la sesión, el indicador muestra 🟢 **Conexión: segura**. Mantén Tailscale
   apagado en el teléfono para una dirección de Funnel o de proxy inverso; enciéndelo para una
   dirección de Tailscale Serve, que solo tu tailnet puede abrir.
6. **Desde fuera, prueba HTTP sin cifrar.** En el mismo teléfono, `http://<your public IP or name>:6040`,
   o tu propio `PORT`, no carga. Si aparece la página de inicio de sesión, HTTP sin cifrar está
   abierto a internet: no inicies sesión ahí, porque la contraseña viajaría en texto claro, y cierra
   el puerto ([Cuando una comprobación falla](#when-a-check-fails)). Quien inicie sesión por esa
   dirección ve 🔴 **Conexión: no segura**, o 🏠 **Conexión: red local** con un motivo *Incierta*
   cuando el servidor no puede ver de dónde llegan los visitantes ([Límites](#limits)).

¿Todas las comprobaciones superadas? Pide a tus usuarios que usen la dirección HTTPS en todos los
dispositivos y que actualicen sus marcadores antiguos
([Cómo conectarse de forma segura](../user/connection-security.md#https-address)).

!!! note "📶 ¿Todavía sin dirección HTTPS?"

    Con el Nivel 1 o 2 de [Exponer de forma segura](service_exposure.md), los usuarios llegan a
    LibreFolio por HTTP sin cifrar. Comprueba el nivel que obtiene cada dirección
    ([Lo que muestra el indicador](#indicator)) y que HTTP sin cifrar no cargue desde fuera
    (comprobación 6). Las comprobaciones de la cookie no se aplican: por HTTP sin cifrar la cookie de
    sesión no es `Secure`, y `"cookie_secure":false` es lo esperado.

---

## 🚦 Lo que muestra el indicador {: #indicator }

El navegador juzga la dirección que abrió; luego el servidor informa de dónde ve llegar la
solicitud, y puede confirmar ese veredicto o hacerlo incierto, pero nunca hacerlo seguro. Esto es lo
que ven tus usuarios, según cómo llegan a LibreFolio:

| Cómo llegan los usuarios a LibreFolio | Ejemplo | Nivel |
| --- | --- | --- |
| Tailscale Serve o Funnel, o un proxy inverso con un certificado | `https://librefolio.your-tailnet.ts.net` | 🟢 **segura**: HTTPS |
| En el propio servidor | `http://localhost:6040` | 🟢 **segura**: `localhost` |
| IP de Tailscale o nombre MagicDNS completo, HTTP sin cifrar (Nivel 1) | `http://100.a.b.c:6040` | 🟢 **segura**: VPN (Tailscale) |
| Nombre MagicDNS corto, HTTP sin cifrar: un nombre sin punto cuenta como local | `http://your-server:6040` | 🏠 **red local** |
| Dirección local, también a través de un subnet router (Nivel 2) | `http://192.168.1.100:6040` | 🏠 **red local** |
| Un puerto abierto en el router, HTTP sin cifrar | `http://myhome.duckdns.org:6040` | 🔴 **no segura** |

Cuando el servidor no puede ver las direcciones de tus visitantes, la última fila muestra en su
lugar 🏠 **red local** con un motivo *Incierta* ([Límites](#limits)). La guía del usuario da las
reglas exactas bajo cada nivel: rangos de direcciones, nombres y casos *Incierta*
([Seguridad de la conexión](../user/connection-security.md#connection-secure)).

---

## 🔎 El punto de vista del servidor {: #server-view }

El indicador pregunta al servidor cómo ve la conexión, una vez por cada carga de la página:
`GET /api/v1/system/connection`. Puedes leer la misma respuesta: con la sesión iniciada, abre esta
dirección en una pestaña nueva del mismo navegador, con tu propia dirección de LibreFolio en lugar de
la del ejemplo:

```text
https://librefolio.your-tailnet.ts.net/api/v1/system/connection
```

El navegador muestra una respuesta de una línea, por ejemplo:

```json
{"client_class":"public","cookie_secure":true}
```

Sirve cualquier cuenta, no solo una de administrador. Una respuesta como
`{"detail":"Not authenticated"}` significa que no hay sesión en esa dirección: las sesiones
pertenecen a una dirección, así que iniciar sesión en `http://192.168.1.100:6040` no te deja con la
sesión iniciada en la dirección HTTPS. Y como el indicador pregunta solo una vez por carga de la
página, recarga LibreFolio tras un cambio para ver su nuevo veredicto.

**`cookie_secure`** dice si una cookie de sesión establecida en esta solicitud sería `Secure`,
según [`SESSION_COOKIE_SECURE`](#session-cookie). En la dirección HTTPS debe ser `true`: `false` es
lo que muestra la línea para el administrador sobre la cookie
([Detrás de un proxy inverso](#reverse-proxy)). Por HTTP sin cifrar, `false` es lo esperado.

**`client_class`** es de dónde ve el servidor llegar la solicitud. Lee el último valor de
`X-Forwarded-For`, el que añadió el proxy más cercano, cuando es una dirección IP, y si no, la
dirección de la propia conexión. Del servidor sale solo la clase: la dirección nunca se devuelve ni
se registra.

| `client_class` | La solicitud llega desde |
| --- | --- |
| `loopback` | El propio servidor: `127.0.0.0/8` o `::1` |
| `vpn` | Tailscale o Headscale: `100.64.0.0/10` o `fd7a:115c:a1e0::/48` |
| `lan` | Una red local: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fe80::/10` o `fc00::/7` |
| `public` | Cualquier otra dirección: internet |
| `unknown` | Ninguna dirección, o una que no se puede leer |

La clase solo cuenta por HTTP sin cifrar, y no en el propio servidor (`localhost`):

- con una dirección pública en el navegador, `public` o `unknown` confirma **Conexión: no segura**,
  mientras que `loopback`, `vpn` o `lan` la convierten en **Conexión: red local**, como incierta;
- con una dirección local o de Tailscale en el navegador, `public` hace incierto el veredicto, y
  cualquier otra clase lo deja como está.

En la dirección HTTPS la clase no cambia nada, pero te dice si el servidor puede ver las direcciones
de tus visitantes: desde el teléfono con datos móviles, con Tailscale apagado, `public` significa que
puede, y `lan` o `loopback` que no puede ([Límites](#limits)).

---

## 🍪 La cookie de sesión {: #session-cookie }

La cookie que mantiene la sesión de un usuario se llama `session`. LibreFolio la establece al
iniciar sesión, siempre `HttpOnly`, para que los scripts de la página no puedan leerla, y
`SameSite=Lax`. Si además es `Secure`, es decir, enviada solo por HTTPS, depende de
`SESSION_COOKIE_SECURE` en `.env`:

- **`auto`**, el valor predeterminado: `Secure` cuando la solicitud es HTTPS, vista directamente o
  porque el primer valor de `X-Forwarded-Proto` enviado por un proxy inverso es `https`;
- **`always`**: siempre `Secure`;
- **`never`**: nunca `Secure`.

Las mayúsculas y los espacios alrededor del valor no importan; cualquier otro valor detiene
LibreFolio al arrancar. Cuándo `always` o `never` son la elección correcta:
[Configuración](configuration.md#session-cookie-secure).

El atributo se decide al iniciar sesión: la cookie que un navegador ya tiene conserva el atributo
que recibió entonces. Después de corregir el proxy o la opción, cierra la sesión y vuelve a
iniciarla.

Para ver el atributo en el navegador:

1. Inicia sesión en la dirección HTTPS.
2. Abre las herramientas para desarrolladores: `F12`, o clic derecho en la página y **Inspeccionar**.
   Safari solo las muestra una vez activadas sus funciones para desarrolladores en sus ajustes.
3. Abre las cookies de tu dirección de LibreFolio: **Application** → **Cookies** en Chrome y Edge,
   **Storage** → **Cookies** en Firefox y Safari (los nombres siguen el idioma del navegador).
4. En la fila `session`, **Secure** está marcada (`true` en Firefox), y también **HttpOnly**;
   **SameSite** indica `Lax`.

La consola no puede mostrarlo: `document.cookie` deja fuera las cookies `HttpOnly`.

---

## 🧰 Detrás de un proxy inverso {: #reverse-proxy }

Un proxy inverso recibe la conexión HTTPS y la pasa a LibreFolio por HTTP sin cifrar, así que
LibreFolio solo sabe del HTTPS, y del visitante, por las cabeceras del proxy:

- `X-Forwarded-Proto: https` dice que el navegador usa HTTPS: con `SESSION_COOKIE_SECURE=auto`, el
  valor predeterminado, LibreFolio marca entonces la cookie de sesión como `Secure`;
- `X-Forwarded-For` lleva la dirección del visitante, lo que permite al indicador ver desde dónde se
  conectan los usuarios.

Tailscale Serve y Funnel, Caddy y Traefik envían ambas por sí solos. Nginx necesita las dos líneas en
el bloque `location` que pasa las solicitudes a LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Si el navegador usa HTTPS pero la cookie de sesión no está marcada como `Secure`, porque el proxy no
envía `X-Forwarded-Proto` o porque `SESSION_COOKIE_SECURE` es `never`, los administradores ven una
línea más en los detalles del indicador. El nivel sigue siendo **Conexión: segura**, porque la
conexión está cifrada; solo a la cookie le falta `Secure`:

> Tu navegador usa HTTPS, pero la cookie de sesión no está marcada como Secure. Haz que el proxy
> inverso envíe X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), o vuelve
> a poner SESSION_COOKIE_SECURE en auto si está en never.

Una vez corregido el proxy, recarga LibreFolio: la línea desaparece. Después cierra la sesión y
vuelve a iniciarla, para que el navegador reciba una cookie `Secure`.

??? tip "⚙️ Configura `SESSION_COOKIE_SECURE` en su lugar"

    Enviar la cabecera es la mejor corrección. Si solo llegas a LibreFolio por HTTPS, puedes en su
    lugar añadir esta línea a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Después reinicia LibreFolio: con Docker, ejecuta `docker compose up -d` (un simple
    `docker compose restart` conserva el entorno anterior); en una instalación en el host, reinicia
    `./dev.py server`, que también lee `.env`. Después cierra la sesión y vuelve a iniciarla.

    Usa `never` solo para el raro proxy que declara HTTPS mientras el navegador está en HTTP sin
    cifrar. Consulta [Configuración](configuration.md#session-cookie-secure) para todas las opciones.

---

## 🛠️ Cuando una comprobación falla {: #when-a-check-fails }

| Lo que ves | Por qué | Qué hacer |
| --- | --- | --- |
| La dirección HTTPS no muestra **Conexión: segura** | La página no está en HTTPS: la barra de direcciones muestra `http://` | Abre la dirección `https://`, y haz que el proxy redirija `http://` a ella |
| La línea sobre la cookie de sesión, o `"cookie_secure":false` en la dirección HTTPS | El proxy no envía `X-Forwarded-Proto: https`, o `SESSION_COOKIE_SECURE` es `never` | Corrige el proxy ([Detrás de un proxy inverso](#reverse-proxy)) o vuelve a poner la opción en `auto`, y recarga |
| `"cookie_secure":true`, pero la cookie `session` no es `Secure` | La cookie se estableció antes de la corrección | Cierra la sesión y vuelve a iniciarla |
| `{"detail":"Not authenticated"}` | No hay sesión en esta dirección | Inicia sesión en esta dirección, en el mismo navegador |
| Cada inicio de sesión vuelve a acabar en la página de inicio de sesión | La cookie es `Secure`, pero el navegador usa HTTP sin cifrar: `SESSION_COOKIE_SECURE=always`, o un proxy que envía `X-Forwarded-Proto: https` a un navegador en HTTP sin cifrar | Usa la dirección HTTPS, o corrige el proxy: consulta [Configuración](configuration.md#session-cookie-secure) |
| Desde fuera, la dirección HTTPS no carga | Una dirección de Tailscale Serve es privada; un Funnel nuevo necesita aprobación y unos minutos | Enciende Tailscale en el teléfono, o usa Funnel; aprueba el Funnel y espera ([Exponer de forma segura](service_exposure.md)) |
| Desde fuera, `http://…:6040` sin cifrar carga | El puerto de LibreFolio está abierto a internet: una redirección de puertos en el router, o un servidor con una dirección pública | Ciérralo: elimina la redirección de puertos, o bloquea el puerto en el cortafuegos del servidor. Tailscale no necesita puertos abiertos, y un proxy inverso solo el suyo |
| `client_class` indica `lan` o `loopback` desde los datos móviles, o HTTP sin cifrar desde internet muestra **Conexión: red local**, *Incierta* | El servidor no puede ver de dónde llegan los visitantes | Consulta [Límites](#limits); con Nginx, añade la línea `X-Forwarded-For` |
| Una dirección de Tailscale muestra **Conexión: red local** | Un nombre MagicDNS corto no tiene punto, así que cuenta como local | Usa la IP de Tailscale, el nombre completo `.ts.net` o, mejor, la dirección HTTPS |

---

## ⚠️ Límites {: #limits }

El indicador es un consejo, no un control: no bloquea nada. Dos límites importan cuando compruebas
una instalación.

**No siempre ve dónde están los visitantes.** Con Docker Desktop expuesto directamente, o detrás de
un proxy que no pasa la dirección del visitante en `X-Forwarded-For`, el servidor ve a todos los
visitantes como locales: `lan`, o `loopback` para un proxy en la misma máquina. HTTP sin cifrar
desde internet muestra entonces **Conexión: red local**, como incierta, en lugar de
**Conexión: no segura**. Docker Engine en Linux conserva la dirección del visitante. Las
direcciones HTTPS no se ven afectadas: muestran **Conexión: segura** en cualquier caso.

**No comprueba los certificados.** Un certificado autofirmado que un usuario aceptó en el navegador
muestra **Conexión: segura**: el tráfico está cifrado, pero nadie garantiza que el servidor sea
realmente el tuyo.

No hay una lista de proxies de confianza que configurar. `X-Forwarded-For` solo alimenta el
indicador, así que un valor falsificado solo engaña al indicador de quien lo envió;
`X-Forwarded-Proto` solo puede activar `Secure`, así que un `https` falsificado solo rompe el inicio
de sesión de quien lo envió.

---

## 🔗 Relacionado

- 🔐 **[Seguridad de la conexión](../user/connection-security.md)** — La guía del usuario: los tres
  niveles y qué hacer en cada uno
- 🌐 **[Exponer de forma segura](service_exposure.md)** — Tailscale, desde una VPN privada hasta una
  dirección HTTPS pública
- 🐳 **[Docker avanzado](docker_advanced.md)** — Archivo Compose, variables de entorno, proxy inverso
- 📝 **[Configuración](configuration.md)** — `SESSION_COOKIE_SECURE` y todas las demás opciones de
  `.env`
