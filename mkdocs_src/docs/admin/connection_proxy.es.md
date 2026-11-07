# 🧰 Comprobación de la seguridad de la conexión: detrás de un proxy inverso

Esta página es para ejecutar LibreFolio **detrás de un proxy inverso** como Nginx, Caddy, Traefik o
Tailscale Serve: las cabeceras que el proxy debe enviar para que la conexión cuente como segura, en qué proxy
confía LibreFolio y cómo averigua la dirección de cada visitante.

Para ver lo que obtienen tus usuarios, con el indicador, la vista del servidor y la cookie de sesión, empieza por
[Comprobación de la seguridad de la conexión](connection_checks.md).

---

## 🧰 Detrás de un proxy inverso {: #reverse-proxy }

Un proxy inverso recibe la conexión HTTPS y la pasa a LibreFolio por HTTP sin cifrar, así que
LibreFolio se entera del HTTPS, y del visitante, solo por las cabeceras del proxy:

- `X-Forwarded-Proto: https` indica que el navegador usa HTTPS: con `SESSION_COOKIE_SECURE=auto`,
  el valor predeterminado, LibreFolio marca entonces la cookie de sesión como `Secure`;
- `X-Forwarded-For` lleva la dirección del visitante, lo que permite al indicador ver desde dónde se conectan
  los usuarios.

Tailscale Serve y Funnel, Caddy y Traefik envían ambas cabeceras por su cuenta. Nginx necesita ambas líneas en el
bloque `location` que pasa las solicitudes a LibreFolio:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Si el navegador usa HTTPS pero la cookie de sesión no está marcada como `Secure`, porque el proxy no
envía `X-Forwarded-Proto` o porque `SESSION_COOKIE_SECURE` está en `never`, los administradores ven una línea más
en los detalles del indicador. El nivel sigue siendo **Conexión: segura**, porque la conexión está
cifrada; solo a la cookie le falta `Secure`:

> Tu navegador usa HTTPS, pero la cookie de sesión no está marcada como Secure. Haz que el proxy inverso envíe
> X-Forwarded-Proto (Nginx: `proxy_set_header X-Forwarded-Proto $scheme;`), o vuelve a poner
> SESSION_COOKIE_SECURE en auto si está en never.

Una vez corregido el proxy, recarga LibreFolio: la línea desaparece. Luego cierra sesión y vuelve a iniciarla,
para que el navegador reciba una cookie `Secure`.

??? tip "⚙️ Establece `SESSION_COOKIE_SECURE` en su lugar"

    Enviar la cabecera es la mejor solución. Si solo accedes a LibreFolio por HTTPS, puedes, en su lugar, añadir esta línea a `.env`:

    ```bash
    SESSION_COOKIE_SECURE=always
    ```

    Después, reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`; en una instalación en el host, reinicia
    `./dev.py server`, que también lee `.env`. Luego cierra sesión y vuelve a iniciarla.

    Usa `never` solo para el raro proxy que afirma usar HTTPS mientras el navegador está en HTTP sin cifrar. Consulta
    [Configuración](configuration.md#session-cookie-secure) para ver todas las opciones.

### 🧭 La dirección del visitante {: #client-address }

LibreFolio limita algunas solicitudes por dirección del visitante: los inicios de sesión fallidos
([Inicios de sesión fallidos](configuration_accounts.md#login-limit)), los correos de registro, **Enviar el enlace de nuevo**
y las contraseñas olvidadas ([Correo electrónico](email.md)). Detrás de un proxy inverso, las conexiones proceden del
proxy: a menos que LibreFolio averigüe la dirección de cada visitante, todos comparten la del proxy y un
único recuento. Para los inicios de sesión es donde más importa: 50 inicios de sesión fallidos a través del proxy, vengan de quien vengan,
harían que se rechazara cualquier inicio de sesión a través de él, incluidas las contraseñas correctas, durante hasta 15 minutos. Eso
sigue siendo cierto detrás de un proxy en una dirección pública. Detrás de uno en una dirección local, como un contenedor de proxy
delante de la imagen de Docker, LibreFolio deja fuera del recuento por dirección los inicios de sesión a través de él, y solo los cuenta el límite por nombre de usuario o dirección de correo electrónico: consulta
[Cuando LibreFolio no confía en tu proxy](#untrusted-proxy), más abajo. En cualquier caso, la solución es
permitir que LibreFolio averigüe la dirección de cada visitante, de una de las dos formas siguientes.

De serie, la dirección que cuenta es la de la conexión, tal como la proporciona uvicorn, el servidor web de LibreFolio.
uvicorn toma la dirección del visitante de `X-Forwarded-For` solo cuando la conexión procede
de una dirección incluida en `FORWARDED_ALLOW_IPS`, `127.0.0.1` cuando esa variable no está definida:
[Contraseñas olvidadas](email_flows.md#forgot-password), en la guía de correo electrónico, explica cómo incluir tu proxy allí.

Si tu proxy escribe la dirección del visitante en una cabecera propia, en su lugar indica esa cabecera en
`LIBREFOLIO_CLIENT_IP_HEADER`, en `.env` o en el entorno del contenedor:

```bash
LIBREFOLIO_CLIENT_IP_HEADER=Fly-Client-IP
```

| Tu proxy | La cabecera | Qué configurar |
| --- | --- | --- |
| Fly.io | `Fly-Client-IP` | Nada: la define el proxy de Fly. |
| Nginx | `X-Real-IP` | Añade `proxy_set_header X-Real-IP $remote_addr;` al bloque `location` que pasa las solicitudes a LibreFolio. |

!!! warning "🚧 Solo cuando todas las solicitudes pasan por el proxy"

    LibreFolio confía en la cabecera, la envíe quien la envíe. Define la variable solo si tus visitantes pueden
    llegar a LibreFolio únicamente a través de ese proxy: un visitante que llegue directamente a él, en su propio puerto
    (`PORT`, 6040 por defecto) o por cualquier otra ruta, puede enviar la cabecera y elegir cualquier dirección, para
    saltarse los límites o agotar los de otra persona.

- **Reinicia después de un cambio**: LibreFolio lee la variable una vez por proceso del servidor. Con Docker,
  ejecuta `docker compose up -d`; en una
  instalación en el host, reinicia `./dev.py server`.
- **La cabecera debe contener una sola dirección, escrita por el propio proxy**: nunca un valor que el proxy transmita
  desde el visitante. Se rechazan `X-Forwarded-For` y `Forwarded`: contienen una lista cuya primera
  dirección elige el visitante. Para `X-Forwarded-For`, incluye tu proxy en `FORWARDED_ALLOW_IPS`
  en su lugar.
- **Un valor incorrecto detiene el servidor al arrancar**, con un error que nombra la variable: una de
  esas dos cabeceras, o un valor que no es el nombre de una cabecera, como un nombre con un espacio o
  con un `:` en él. El uso de mayúsculas o minúsculas y los espacios alrededor del nombre no importan; un valor vacío equivale a no
  definirla.
- **Una solicitud sin la cabecera** cuenta con la dirección de la conexión.
- **Una cabecera que LibreFolio no puede usar**, porque la solicitud la lleva dos veces o porque la cabecera contiene una lista, una
  dirección con un puerto o cualquier cosa que no sea una única dirección IP, también cuenta con la dirección de la conexión.
  El registro muestra entonces una advertencia por proceso del servidor,
  `Client address header unusable: using the connection's address`, con el nombre de la cabecera en
  `header`, cuántas veces la llevó la solicitud en `lines` y la longitud total de esas líneas en `length`,
  nunca el valor en sí: comprueba cómo establece tu proxy la cabecera.
- **Otro proxy delante de Fly.io**, como Cloudflare: `Fly-Client-IP` contiene entonces la dirección de ese proxy,
  no la del visitante.
- **Ningún perfil la define**: la
  cabecera depende del proxy delante de cada instancia.
- **El indicador no la usa**: sigue leyendo `X-Forwarded-For`, como
  explica [La vista del servidor](connection_checks.md#server-view).

#### 🕵️ Cuando LibreFolio no confía en tu proxy {: #untrusted-proxy }

LibreFolio no confía en tu proxy cuando no averigua la dirección del visitante ni mediante
`FORWARDED_ALLOW_IPS` ni mediante `LIBREFOLIO_CLIENT_IP_HEADER`: no puede distinguir a los visitantes
detrás del proxy, y sus límites por dirección del visitante tampoco. Reconoce ese tipo de
proxy por sus solicitudes: proceden de una dirección local (`loopback`, `lan` o `vpn` en
[La vista del servidor](connection_checks.md#server-view), como `172.18.0.2` en una red de Docker) y llevan una cabecera
de reenvío (`X-Forwarded-For`, `Forwarded` o `X-Real-IP`) que no proporcionó a LibreFolio ninguna dirección de visitante.
Entonces:

- **Los límites por dirección del visitante dejan fuera esas solicitudes**, para que un visitante no pueda bloquear
  a todos. Los límites por cuenta o por dirección de correo electrónico sí las cuentan.
- **El registro muestra una advertencia por proceso del servidor**, la primera vez que una solicitud de ese tipo alcanza un límite por
  dirección del visitante:
  `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`,
  con los nombres de las cabeceras en `headers`, como `X-Forwarded-For, X-Real-IP`, nunca una
  dirección.
- **Las comprobaciones de seguridad** también lo notifican, como una advertencia de `platform.client_address`. Esta comprobación
  indica qué ha encontrado el servidor desde su último arranque: tras un reinicio aparece como `ok` hasta que vuelve a llegar una
  solicitud de ese tipo, así que nunca aparece entre las [comprobaciones de inicio](configuration_security.md#startup-checks).
- **Para corregirlo**, incluye tu proxy en `FORWARDED_ALLOW_IPS`, como explica [Contraseñas olvidadas](email_flows.md#forgot-password)
  en la guía de correo electrónico, o indica la cabecera que establece él mismo en
  `LIBREFOLIO_CLIENT_IP_HEADER`, como se ha indicado antes, si todas las solicitudes pasan por él. Detrás de Tailscale Serve o
  Funnel con la imagen de Docker, sigue [Tailscale Serve y Funnel con Docker](#tailscale). En
  `FORWARDED_ALLOW_IPS`, indica la dirección del proxy tal como la ve LibreFolio: con Docker, la dirección del contenedor
  del proxy, o su red de Docker, como `FORWARDED_ALLOW_IPS=172.18.0.0/16`
  (`docker network inspect`, con el nombre de la red, muestra ambas), aunque toda una red incluye
  su puerta de enlace, que también es la dirección de las conexiones hechas en el propio servidor
  ([ver más abajo](#tailscale)). Confía solo en direcciones que use únicamente tu proxy. Define cualquiera de las dos variables
  en `.env` o en el entorno del contenedor, y luego reinicia, como se ha indicado antes: con Docker,
  `docker compose up -d`. ¿No hay ningún proxy tuyo delante de LibreFolio? Entonces la cabecera la envió un visitante de tu propia
  red o VPN o, con Docker Desktop expuesto directamente, cualquier visitante, o cualquier
  visitante IPv6 al que el proxy de Docker dé paso ([Límites](connection_checks.md#limits)): no incluyas nada.

**Las cabeceras de reenvío procedentes de una dirección pública** solo reciben un `info`, en el registro una vez por proceso del servidor,
`Forwarding headers from a public address were ignored: if a proxy on a public address forwards the requests, list it in FORWARDED_ALLOW_IPS`,
también con `headers`, y en las comprobaciones de seguridad, donde `platform.client_address` sigue siendo una advertencia si
también se encontró un proxy como el anterior. Esas solicitudes siguen contando con la dirección de la conexión. Son
inofensivas cuando ningún proxy tuyo tiene una dirección pública: un visitante, o un proxy suyo, puede añadir
tales cabeceras.

#### 🐳 Tailscale Serve y Funnel con Docker {: #tailscale }

Tailscale Serve y Funnel pasan la dirección del visitante en `X-Forwarded-For`: la dirección de Tailscale
del dispositivo, `100.x.y.z`, o, a través de Funnel, la dirección del visitante en internet. Escriben
la cabecera ellos mismos, en lugar de cualquier cabecera que haya enviado el visitante. Con HTTPS —el valor predeterminado de Serve y
la única forma de Funnel—, también envían `X-Forwarded-Proto: https`; con `tailscale serve --http=…`
no envían ninguna, y con razón, ya que el navegador también está en HTTP sin cifrar.

Con la imagen de Docker, LibreFolio no puede usar esa dirección de serie. Las dos configuraciones de Tailscale de
[Exposición segura](service_exposure.md), tanto en el servidor como en
[contenedores sidecar](service_exposure_funnel.md#level-4-multi-funnel-with-docker-sidecars), llegan a su contenedor a través de Docker, así que sus solicitudes proceden
de la puerta de enlace de la red de Docker del contenedor, como `172.28.0.1`, en la que uvicorn no
confía:

- **En el servidor**, `tailscale serve --bg 6040` (la dirección HTTPS del nivel 1) o
  `tailscale funnel --bg 6040` (nivel 3) pasa las solicitudes a `http://127.0.0.1:6040`, y
  el propio proxy de Docker se las entrega al contenedor;
- **En contenedores sidecar** (nivel 4), socat las pasa a la dirección LAN del servidor y
  al puerto publicado de LibreFolio.

Así que LibreFolio advierte sobre un proxy en el que no confía, [como se ha indicado antes](#untrusted-proxy), y sus límites
por dirección del visitante dejan fuera todas esas solicitudes. Si, en cambio, está instalado en el host, sin Docker,
LibreFolio no necesita nada para `tailscale serve` o `tailscale funnel` en el mismo servidor: ve
que sus solicitudes proceden de `127.0.0.1`, en la que uvicorn confía de forma predeterminada.

Para permitir que LibreFolio vea a cada visitante, trabaja en el servidor, en la carpeta que contiene
`docker-compose.yml` y `.env`:

1. **Encuentra la puerta de enlace** de la red de Docker de LibreFolio:

    ```bash
    docker inspect --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' librefolio
    ```

    Imprime una dirección como `172.28.0.1`; `librefolio` es el nombre que `docker-compose.yml` da
    al contenedor (`container_name`). `docker network inspect <network>` muestra la misma puerta de enlace
    en `IPAM` → `Config` → `Gateway`, junto a la `Subnet` de la red: `docker network ls` lista
    las redes, y la propia de un proyecto de Compose es `<project>_default`.

    Para asegurarte de que las solicitudes de Tailscale proceden de ella, abre LibreFolio en su dirección de Tailscale
    y luego lee las últimas líneas de su registro:

    ```bash
    docker compose logs --tail 20 librefolio
    ```

    uvicorn registra cada solicitud en una línea que muestra la dirección que ve y, a continuación, la solicitud. A través de
    Tailscale, esa dirección es la de la puerta de enlace:

    ```text
    172.28.0.1:<port> - "GET … HTTP/1.1" 200 OK
    ```

    Las líneas de `/api/v1/system/health` son la comprobación de estado de Docker, hecha dentro del contenedor:
    déjalas de lado.

2. **Incluye la puerta de enlace en `FORWARDED_ALLOW_IPS`.** Añade esta línea a `.env`, con tu propia puerta de enlace:

    ```bash
    FORWARDED_ALLOW_IPS=172.28.0.1
    ```

    Si `.env` ya define la variable, para otro proxy, añade la puerta de enlace al final de su lista,
    después de una coma.

3. **Reinicia LibreFolio**, para que su contenedor reciba el nuevo entorno:

    ```bash
    docker compose up -d
    ```

4. **Comprueba.** Vuelve a abrir LibreFolio en su dirección de Tailscale y luego lee el registro como en el paso 1. Las
   líneas de tus solicitudes ahora muestran la dirección del dispositivo en lugar de la de la puerta de enlace (a través de
   Funnel, la dirección pública del visitante), seguida del puerto `0`:

    ```text
    100.x.y.z:0 - "GET … HTTP/1.1" 200 OK
    ```

    La advertencia de `platform.client_address` deja de volver a aparecer. No obstante, esa comprobación indica qué ha encontrado el servidor
    desde su último arranque, así que aparece como `ok` después del reinicio en cualquier caso: la línea del registro
    es la prueba real.

Tres cosas que tener en cuenta sobre confiar en la puerta de enlace:

- **La puerta de enlace exacta es la opción más restrictiva**, pero Compose puede asignar a la red otra subred
  cuando la vuelve a crear (`docker compose down`, y luego `docker compose up -d`): vuelve a comprobar la puerta de enlace
  después de ese cambio.
- **`FORWARDED_ALLOW_IPS=172.16.0.0/12` sobrevive a eso**, ya que cubre todas las redes de Docker desde
  `172.16` hasta `172.31`. Pero confía en todas las redes de Docker del servidor, y no cubre las
  redes `192.168.x.x` que Docker asigna cuando aquellas se agotan.
- **La puerta de enlace no es exclusiva de Tailscale.** También es la dirección de todas las conexiones hechas en el
  propio servidor a través del puerto publicado, y de los visitantes IPv6 a los que el proxy de Docker da paso
  ([Límites](connection_checks.md#limits)): confiar en ella les permite elegir la dirección que los límites usan para contar.
    - Si llegas a LibreFolio **solo** a través de `tailscale serve` o `tailscale funnel` en el
      servidor, publica el puerto solo en el loopback, para que nada fuera del servidor pueda llegar
      a él: en `docker-compose.yml`, en `ports:`, cambia `"${PORT:-6040}:6040"` por
      `"127.0.0.1:${PORT:-6040}:6040"`, y luego ejecuta `docker compose up -d`.
    - No hagas esto con el nivel 4 ni con las direcciones HTTP sin cifrar de los niveles 1 y 2: llegan al puerto
      a través de la dirección LAN o de Tailscale del servidor.

---

## 🔗 Relacionado

- 📄 **[Comprobación de la seguridad de la conexión](connection_checks.md)** — Lista de comprobación, Qué muestra el indicador, La vista del servidor, …
