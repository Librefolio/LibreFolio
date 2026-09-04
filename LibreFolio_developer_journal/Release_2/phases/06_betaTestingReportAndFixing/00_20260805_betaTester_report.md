Alfy, [05.08.2026 16:28]
su windows nella docker version le bandiere nel sito per la selezione lingue non compaiono, al loro posto hanno ripreso ad esserci le lettere della nazione, verificare css con il font.
In oltre nella documentazione non sono caricate le immagini, né quelle del server (che forse è perché non si sono finite di generare) ne dà GitHub (e questo è strano perché il fallback esiste apposta)

Alfy, [05.08.2026 16:38]
i caricamenti dei file avvengono sequenzialmente pare, e anche il parsing, sarebbe utile farli in parallelo

Alfy, [05.08.2026 16:38]
nel riepilogo analisi il tipo di transazione ha ancora il nome in inglese

Alfy, [05.08.2026 16:40]
nel riepilogo analisi bisogna sottrarre, in caso di risoluzione di duplicati, le transsazioni rimosse

Alfy, [05.08.2026 16:40]
nell'avviso dei 36 righe di successione, la parola gamba non fa capire bene che si tratta di un trasferimento titoli di cui tracciamo solo una metà

Alfy, [05.08.2026 16:43]
nella importa transazioni non è chiaro il secondo numero 14(37?) non è chiaro cosa è il 14 e cosa il 37, forse va diviso il sotto titolo è 14 asset unici, 37 da risolvere, ma non ho capito il 37 da risolvere

Alfy, [05.08.2026 16:46]
ho capito cosa è l 37, stavo importando 3 file e la somma degli asset fa proprio 37, bisogna fare un set e non contare i duplicati
In oltre arrivati allo step 4, anche se sono lo stesso asset, in alcuni compare l'isin e in altri no, dipende certamente dal file, bisogna necessariamente accorpare gli asset prima.

Alfy, [05.08.2026 16:51]
in credit agricole il warning sul trasferimento titoli dovrebbe dire anche le righe coinvolte, e in generale dovrebbe elencare le righe o l'intervallo coinvolte

aggiungere un livello info all'import, il warning non è sufficiente

Alfy, [05.08.2026 16:53]
in italiano scrivere nello step 4 della revisione N TX non fa capire che TX è transazione, magari possiamo mettere un emoji con una riga

Alfy, [05.08.2026 17:01]
il warning sul prezzo corrente nel fondo di borsa italiana è in inglese sempre, dovrebbe dipendere dalla lingua usata, quindi se scegliamo italiano, anche i warning dovrebbero esserlo

Alfy, [05.08.2026 17:10]
nel file dei movimenti che comprende 2025, al giorno 5/11/2025 era presente questa riga:
SOTTOSC SICAV ORD.:2025/003955841 AMUNDI PIO GLOB EQ G
Rappresentava l'acquisto o meglio sottoscrizione a un fondo di investimento che il plugin non sta vedendo, da correggere (riga 211 del file)

Alfy, [05.08.2026 17:19]
con un asset, mi è comparsa la modale che chiedeva se assegnare, sostituire e assegnare e annulla, ma cliccando annulla, non si è deselezionato l'asset tornando neutro
in oltre l'errore dell'isin non era dovuto al fatto che l'asset già esisteva, ma che l'isin dell'import è diverso dall'isin del provider, quindi sarebbe dovuto comparire lì

essendo poi che l'asset era uno dei btp cum, quindi all'emissione, quello del provider è quello liberamente scambiabile, io in generale aggiungerei un opzione che dice di mettere come altro identificativo l'identificativo del report

Alfy, [05.08.2026 17:24]
sarebbe utile avere l'edit asset in ogni card dello stato 4 dell'import dopo averlo assegnato

Alfy, [05.08.2026 17:30]
se poi ho un isin che è dentro gli altri identificatori, non deve comparire la modale per sostituire l'isin, perchè è già consumato da un altro identificatore

Alfy, [05.08.2026 17:37]
non facendo selezionare un disattivato, una transazione finita non si può altrimenti importare! grave perchè costringe a creare un secondo asset uguale

Alfy, [05.08.2026 17:39]
in oltre andando sull'asset disattivo, non posso riportarlo attivo, con il modifica, e vedo che anche export ai è disattivo, e questo è sbagliato

Alfy, [05.08.2026 17:47]
da capire perchè, dopo aver assegnato tutti gli asset, le transazioni uniche non si sono selezionate tutte (o comunque via via che si assegnavano)

Alfy, [05.08.2026 17:54]
in aggiungi transazione non prende la , e il . per i decimali, e anzi, se si scrive senza avere prima il decimale il parse lo cancella subito

Alfy, [05.08.2026 18:09]
Nell'import da CreditAgricole il btp più 33 ha importato gli interessi, ma non l'acquisto! 
il btp più 33 non è stato importato dall'estratto conto di credit agricole, la riga era:
25/02/2025 25/02/2025 COMPRAVENDITA TITOLI/FONDI/OPZIONI NOTA INF. ACQ. TIT:BTP PIU 25-2-33 CU DOSS:00496/05246854 -15.000,00 EUR


e credo mancano anche le varie tasse, mentre le cedole le vede:
26/05/2025 26/05/2025 COMMISS./SPESE SU OPERAZ. TITOLI SPESE STACCO CEDOLA DEL 25/05/2025 DOSSIER: 00496/05246854 TIT: IT0005634792 BTP PIU 25-2-33 CUM MOV:256412981 -1,50 EUR
26/05/2025 26/05/2025 CEDOLE, DIVIDENDI, PREMI ESTRATTI CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 DOS:00496/05246854 NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36 DATA : 25/05/2025 N.MOVIM: 1 93,52 EUR

Alfy, [05.08.2026 18:29]
e se provo a mettere sia btp che amundi pio, mancano dei dati per il validatore dei soldi, sospettiamo possa essere perchè non sono stati registrati o esportati dei dati.

ad ora ho verificato che se non presenti li prende come deposito e prelievo, ed ecco perchè andava in negativo!!!

Alfy, [05.08.2026 18:40]
per amundi pio dai movimenti conto non sembra si possa estrarre la quantità associata, solo l'ammontare economico, bisogna far flaggare e chiedere all'utente di inserire la quantità giusta

Alfy, [05.08.2026 19:06]
anche il btp 1/3/32 non è stato visto l'acquisto, e purtroppo accorpano commisione e acquisto, bisogna flaggare anche questo per farlo correggere all'utente, come fallback va bene mettere tutto nell'acquisto, ma da segnalare

Alfy, [05.08.2026 19:25]
su Credit agricol il patrimonio netto da noi calcolato è di 544k€ ma stando al sito dovrebbero essere 530k€, e ci sono 14,6k€ di dividendi e interessi nel p%l, potrebbe essere che il paatrimonio netto li calcola? credo che stiamo sommando 2 volte i dividendi e interessi, uno nel p&l che li comprende e un altro nella liquidità.

Alfy, [05.08.2026 19:26]
il tooltip custom non deve comparire subito, dopo qualche secondo che il mouse è fermo o con un click, ovunque

Alfy, [05.08.2026 23:14]
Il segnale del drowdown implementato non sembra ritornare il drowdown rispetto l'ultimo massimo, ma rispetto al massimo nel periodo mostrato.

Alfy, [06.08.2026 07:54]
Il pulsante duplica transazione non duplica anche la data, la mette ad oggi, so che avevamo pensato fosse corretto fare così, ma la realtà sta dimostrando che è meglio di no. in oltre il pulsante per eliminare 1 sola transazone che fa comparire la modale di delette unica, in realtà è al quanto scomoda, meglio fare che cliccando delete si apre la bulk modal transaction con la riga marcata come da eliminare.


Dati fondo amundi e btp più in parte corretti manualmente ma con le tasse comunque ancora non assegnate, nota che in un fodo amundi abbiamo assegnato la quantità guardando la transazione e abbiamo poi creato anche una transazione di commissione, purtroppo nel movimento conto i 2 numeri erano uniti, da qui la nota che si era fatta di segnalare all'utente che potrebbe essere necessario creare a mano una transazione di commissione, e che il plugin non può fare tutto da solo:
	

Data


Tipo


Qtà


Importo


Link

Asset


Broker


Tag


ID


Descrizione

Azioni

25 mag 2026	
Interesse
—	
+93,52
€
🇪🇺
EUR

Btp Piu' Sc Fb33 Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
cedole_dividendi_premi_estratti
#393	
CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 DOS:00496/05246854 NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36 DATA : 25/05/2026 N.MOVIM: 5
⋮

25 mag 2026	
Commissione
—	
-1,50
€
🇪🇺
EUR
—	
Crédit Agricole
Crédit Agricole
import
credit_agricole
commiss_spese_su_operaz_titoli
#392	
SPESE STACCO CEDOLA DEL 25/05/2026 DOSSIER: 00496/05246854 TIT: IT0005634792 BTP PIU 25-2-33 CUM MOV:266564859
⋮

25 feb 2026	
Interesse
—	
+93,52
€
🇪🇺
EUR

Btp Piu' Sc Fb33 Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
cedole_dividendi_premi_estratti
#462	
CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 DOS:00496/05246854 NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36 DATA : 25/02/2026 N.MOVIM: 4
⋮

25 feb 2026	
Commissione
—	
-1,50
€
🇪🇺
EUR
—	
Crédit Agricole
Crédit Agricole
import
credit_agricole
commiss_spese_su_operaz_titoli
#461	
SPESE STACCO CEDOLA DEL 25/02/2026 DOSSIER: 00496/05246854 TIT: IT0005634792 BTP PIU 25-2-33 CUM MOV:262945642
⋮

25 nov 2025	
Interesse
—	
+93,52
€
🇪🇺
EUR

Btp Piu' Sc Fb33 Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
cedole_dividendi_premi_estratti
#526	
CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 DOS:00496/05246854 NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36 DATA : 25/11/2025 N.MOVIM: 3
⋮

25 nov 2025	
Commissione
—	
-1,50
€
🇪🇺
EUR
—	
Crédit Agricole
Crédit Agricole
import
credit_agricole
commiss_spese_su_operaz_titoli
#525	
SPESE STACCO CEDOLA DEL 25/11/2025 DOSSIER: 00496/05246854 TIT: IT0005634792 BTP PIU 25-2-33 CUM MOV:263878791
⋮

11 nov 2025	
Vendita
-1867,178 📉	
+9984,47
€
🇪🇺
EUR

Amundi Primo Investimento Lc 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
giroconto_bonifico
#815	
ORD:AMUNDI PRIMO INVESTIMENTO DT.ORD:000000 DESCR.OPERAZIONESCT::RIMBORSI: : : :SU AMUNDI PRIMO INVES TIMENTO CL B<*> R IFERIMENTO SCT:HW-2025-11-10-33009343855 IDENTIFICATIVO SCT:
⋮

6 nov 2025	
Acquisto
+1843,575 📈	
-20.129,44
€
🇪🇺
EUR

Amundi F. Global Equity G Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
compravendita_titoli_fondi_opzioni
#814	
SOTTOSC SICAV ORD.:2025/003955841 AMUNDI PIO GLOB EQ G
⋮

25 ago 2025	
Interesse
—	
+93,52
€
🇪🇺
EUR

Btp Piu' Sc Fb33 Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
cedole_dividendi_premi_estratti
#597	
CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 DOS:00496/05246854 NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36 DATA : 25/08/2025 N.MOVIM: 2
⋮

25 ago 2025	
Commissione
—	
-1,50
€
🇪🇺
EUR
—	
Crédit Agricole
Crédit Agricole
import
credit_agricole
commiss_spese_su_operaz_titoli
#596	
SPESE STACCO CEDOLA DEL 25/08/2025 DOSSIER: 00496/05246854 TIT: IT0005634792 BTP PIU 25-2-33 CUM MOV:260198500
⋮

26 mag 2025	
Interesse
—	
+93,52
€
🇪🇺
EUR

Btp Piu' Sc Fb33 Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
cedole_dividendi_premi_estratti
#667	
CEDOLA:BTP PIU 25-2-33 CUM IT0005634792 DOS:00496/05246854 NOMINALE: 15.000,00 TASSO: 2,85 ALIQ: 12,50 RITENUTA: 13,36 DATA : 25/05/2025 N.MOVIM: 1
⋮

26 mag 2025	
Commissione
—	
-1,50
€
🇪🇺
EUR
—	
Crédit Agricole
Crédit Agricole
import
credit_agricole
commiss_spese_su_operaz_titoli
#663	
SPESE STACCO CEDOLA DEL 25/05/2025 DOSSIER: 00496/05246854 TIT: IT0005634792 BTP PIU 25-2-33 CUM MOV:256412981
⋮

25 feb 2025	
Acquisto
+15.000 📈	
-15.000,00
€
🇪🇺
EUR

Btp Piu' Sc Fb33 Eur 🇮🇹
↗
Crédit Agricole
Crédit Agricole
import
credit_agricole
compravendita_titoli_fondi_opzioni
#813	
NOTA INF. ACQ. TIT:BTP PIU 25-2-33 CU DOSS:00496/05246854
⋮

∞
