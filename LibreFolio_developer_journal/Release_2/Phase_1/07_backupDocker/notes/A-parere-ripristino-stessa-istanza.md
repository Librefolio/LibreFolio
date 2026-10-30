# Parere di sicurezza di A — ripristino notturno «della stessa istanza» (26/10/2026)

Domanda del coordinatore cloud: nessuna revoca della password quando il pannello ripristina una copia sigillata L3
della stessa istanza.

**No, il sigillo da solo non basta.** I tre segni si possono produrre dall'esterno:
- *stessi destinatari*: la busta è cifrata verso una chiave **pubblica**; chi la conosce può fabbricare una busta valida;
- *stessa chiave d'istanza*: sta dentro l'archivio (`instance_key_included` nel manifest), la dichiara il file stesso;
- *id dell'istanza e origine nel manifest*: scritti da chi prepara il file.

Il caso ostile resta intero: chi può scrivere nel deposito delle copie mette un titolare con un hash di password che
conosce e, senza revoca, entra come amministratore pagante. La firma L2 autentica l'**ordine** di ripristinare, non il
**contenuto** del file.

**Che cosa basterebbe:** una prova che sta fuori dal file e viene registrata al momento del backup. Il cloud, quando
prende la copia, annota fuori dal deposito l'impronta SHA-256 dell'archivio sigillato. Al
ripristino notturno passa quell'impronta nell'ordine firmato; l'istanza ricalcola l'impronta dell'archivio ricevuto e
salta la revoca **solo se coincide**. Altrimenti, o se l'impronta manca, si fa il trattamento di oggi.

Condizioni:
1. solo sul canale del pannello, mai dall'app, dalla CLI o da altro;
2. solo nel profilo `managed`, con il titolare del backup unico segnato e con l'indirizzo di `LIBREFOLIO_ADMIN_EMAIL`;
3. l'impronta copre l'archivio intero, non solo il manifest;
4. nessuna eccezione perché il file «sembra» lo stesso: decide solo l'impronta;
5. una riga nel log, «ripristino della stessa copia: password mantenuta», senza indirizzi;
6. un test ostile: archivio con il titolare manomesso e un'impronta vecchia → revoca come oggi.
