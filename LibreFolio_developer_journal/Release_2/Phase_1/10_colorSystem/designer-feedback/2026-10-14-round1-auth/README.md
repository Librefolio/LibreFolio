# Designer · giro 1 — schermate di accesso e palette per tutto il progetto (14/10/2026)

> Ricevuto dal developer il 14/10/2026 alle 20:18 e registrato dal coordinatore colori. Il materiale originale è intatto:
>
> - [`note-originali.txt`](note-originali.txt): le note della designer, parola per parola. La parte sul tema scuro,
>   come scrive lei, l'ha preparata con l'aiuto di Gemini.
> - [`render-accesso-chiaro.png`](render-accesso-chiaro.png) (1600×900) e [`render-accesso-scuro.png`](render-accesso-scuro.png)
>   (1024×572): rendering di login e registrazione. Sono illustrativi; i valori validi sono quelli scritti nelle note.
>
> L'analisi della richiesta e il piano per applicarla stanno in [`analisi.md`](analisi.md).
>
> Qui sotto c'è la trascrizione ordinata delle note. Dove sembra diversa dall'originale, vale l'originale.

## Cosa ha guardato

Le schermate della gallery v1.2 `auth/01-login`, `auth/02-register-empty` e `auth/03-register-filled`, in versione mobile.

## Cosa chiede

1. **Rifare i colori di tutto il progetto**, chiaro e scuro, con le regole qui sotto («voglio che con queste regole in
   mente, rifai i colori di tutto il progetto»).
2. **Icone nei campi** di login e registrazione (utente, email, lucchetto), nei due temi.
3. **Togliere il testo «Crea un account»** in cima alla card di registrazione: il pulsante «Registrati» in fondo basta.

## Regole del tema chiaro, «caldo naturale»

- Verde bosco, avorio caldo, sabbia chiara; testi carbone con una lieve componente bruna.
- Il calore viene dallo **sfondo e dalle superfici**, non da tutto. Campi, bordi, testi e stati restano leggibili e
  ordinati.
- Testata e pulsanti: il verde bosco resta, «è già il punto forte dell'identità visiva».
- Sfondo illustrato: colline salvia desaturate, senza nuovi verdi saturi.
- Requisiti della password: fondo verde molto tenue, icone e testo verde scuro, e mai solo il colore a dire se un
  requisito è soddisfatto.

## Regole del tema scuro, «Notte nel Bosco»

- Via i blu notte freddi (`slate`/`gray` di Tailwind): neri e antraciti con un sottotono verde muschio. Testi avorio
  caldo, non bianco puro.
- Card e sfondo con la stessa temperatura del tema chiaro: oggi la card blu notte (~`#111625`) stona con le colline e la
  testata verdi.
- Colline dello sfondo: `#14241E`, `#192E26`, `#1F382F`. Linee del grafico: `#284238`.
- Box dei requisiti della password:
  - fondo `#1A2822`, bordo `#284237`;
  - icone ✓ `#6EE7B7` oppure `#3DD68C`;
  - testo dei requisiti soddisfatti `#B8D8C8`, di quelli non soddisfatti `#758078`.
- Icone dei campi: `#758078`, che diventa `#EAE6DF` quando il campo ha il focus.

## Palette per ruolo

Le colonne «v1.2» riportano i valori della tabella che le abbiamo mandato
([`APRI_QUI.html`](../../designer-package-v1.2/APRI_QUI.html), §3); le colonne «Proposta» riportano i suoi valori.

| Ruolo | v1.2 chiaro | Proposta chiaro | v1.2 scuro | Proposta scuro |
|---|---|---|---|---|
| Sfondo pagina | `#f5f4ef` | `#F7F4ED` | `#0f172a` | `#0F1412` |
| Card login / registrazione, superficie 1 | `#ffffff` | `#FBF8F1` | `#1e293b` | `#171F1C` |
| Superficie secondaria | `#f9fafb` · `#f3f4f6` | `#EEE9DE` | `#334155` | `#1E2824` |
| Menu laterale | `#1a4031` | `#F1EDE3` | `#166534` | `#131A17` |
| Sfondo dei campi | bianco | `#FBF8F1` | — | `#121815` |
| Testo primario | `#111827` | `#292D27` | `#f8fafc` | `#EAE6DF` |
| Testo secondario | `#4b5563` | `#555C53` | `#cbd5e1` | `#A8B0A8` |
| Testo attenuato | `#6b7280` · `#9ca3af` | `#687066` | `#94a3b8` | `#758078` |
| Bordo | `#e5e7eb` | `#DDD5C7` | `#334155` | `#26312C` |
| Bordo dei campi | gray-300 / gray-200 | `#B9AE9B` | `#546175` | `#38463F` |
| Verde marchio (testata) | `#1a4031` | `#1B4334` | `#166534` | `#1B4334` |
| Verde azione (pulsanti) | `#1a4031` | `#1B4334` | `#166534` · `#39af50` · `#00d681` | `#245A46`, hover `#2D6E56` |
| Focus, link attivi | `#1a4031` | `#236B4D` | `#4ade80` | `#469E76` |
| Successo | `#059669` | `#18794E` | `#34d399` | `#3DD68C` |
| Avviso | `#f59e0b` | `#895000` | `#fbbf24` | `#F5A623` |
| Errore | `#ef4444` · `#dc2626` | `#B42332` | `#f87171` | `#F25F5C` |
| Informazione | sky / blue-500 | `#155EEF` | sky-300/400 | `#5899FA` |

**Righe della tabella v1.2 senza proposta:**
- placeholder e disabilitato;
- guadagno e perdita, nel testo e nei grafici;
- neutri dei grafici;
- palette categoriale;
- sfondo delle modali.

Gemini chiudeva offrendo di definire i colori dei grafici e delle tabelle in scuro: la proposta non c'è.
