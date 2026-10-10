---
title: Herramientas
description: Qué es una Herramienta, las herramientas disponibles hoy y cómo abrir una.
---

# 🧰 Herramientas

Una **Herramienta** es un cálculo independiente: tú proporcionas los datos para una operación y esta devuelve un resultado o un error estructurado. No es una instrucción para modificar tu cartera.

La plataforma de Herramientas es **experimental**. Actualmente el catálogo ofrece exactamente
**una** herramienta:

| Herramienta | Qué hace |
|---|---|
| [asignador PAC](pac-allocator/index.md) | Planifica qué compras acercan una asignación lo más cerca posible de su objetivo, usando el efectivo y las aportaciones disponibles ahora. |

Su tarjeta abre un planificador guiado. Su propia página explica cómo usarla y qué
hace el motor de cálculo que tiene detrás.

!!! note "Se retiró una segunda herramienta"

    Anteriormente, el catálogo ofrecía un Rebalanceador de cartera junto al asignador
    PAC. Ambos eran prototipos y ambos se eliminaron. Hasta ahora solo se ha
    reconstruido el asignador PAC, por lo que un marcador a la página de
    documentación del Rebalanceador ya no conduce a ninguna página.

## 🖱️ Abrir una herramienta

Abre **Herramientas** desde la barra lateral para ver el catálogo como una cuadrícula de tarjetas. Para una herramienta lista para usar, **toda la tarjeta** es clicable, no solo su título o un icono; un indicador de flecha la marca como que se puede abrir. Una herramienta cuya interfaz falta carece de ambas cosas, y en su lugar indica su situación en la tarjeta.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="tools" data-name="hub" alt="Catálogo de Herramientas con la tarjeta del asignador PAC, su par de versiones y las acciones Documentación y Recargar">
</div>

Tanto el catálogo como una herramienta abierta muestran:

- una acción **Documentación** que enlaza a la página de esa herramienta, con una etiqueta que aparece junto al icono en pantallas anchas y se reduce a un control solo con icono en pantallas estrechas;
- una acción **Recargar** que recarga el catálogo (desde el hub) o la interfaz de la herramienta actual (desde una herramienta abierta), con el mismo comportamiento adaptativo de solo icono; recargar una herramienta abierta primero pide confirmación (**¿Recargar herramienta?**), porque sustituye la interfaz y descarta su borrador actual;
- el par de compatibilidad de la herramienta, `Backend/API <contract_version> · UI <ui.version>`, sin ningún número de compilación o de implementación separado que se muestre junto a él.

Cuando algunas entradas del catálogo o interfaces no están disponibles, el hub indica cuántas son y remite a **Configuración → Acerca de → Diagnóstico de plugins**.

## ℹ️ Conviene saber

- **Una herramienta nunca cambia tu cartera.** No registra ninguna transacción, no cursa ninguna orden y
  no guarda nada en tu cartera: actuar según su resultado depende de ti.
- **¿Servidor ocupado o se ha alcanzado un límite de tiempo?** No obtienes ningún resultado, y eso no dice nada sobre tus
  cifras: espera un momento e inténtalo de nuevo.
- **¿Falta una herramienta o no se puede abrir?** Consulta **Configuración → Acerca de → Diagnóstico de plugins**:
  su panel **Herramientas** indica, herramienta por herramienta, si está disponible y, si no lo está, por qué. Consulta
  [Acerca de](../settings/about.md).
