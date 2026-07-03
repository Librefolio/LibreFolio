# <img src="https://www.directa.it/favicon.ico" alt=""> Directa SIM

!!! info "Beta"

    Ce plugin est en **Beta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

LibreFolio prend en charge le format **CSV** exporté depuis Directa SIM. Les captures d'écran ci-dessous proviennent de la version bureau, mais les étapes sont similaires sur mobile.

### Étape 1 — Ouvrir la liste des mouvements

Connectez-vous à [Directa](https://www.directatrading.com) et cliquez sur l'onglet **CONTO** (❶). Cliquez ensuite sur l'icône filtre/mouvements à gauche (❷) et sélectionnez la période souhaitée — ex. **6M** (❸).

![Directa SIM — onglet CONTO, liste des mouvements, sélecteur de période](../../../static/broker-guides/Directa_1.png){ style="border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### Étape 2 — Exporter en CSV

Cliquez sur l'icône d'exportation (l'icône du tableur avec le **X** vert) en haut du tableau. Dans la boîte de dialogue, sélectionnez **File separato da virgole (csv)** et cliquez sur **ESTRAI**.

![Directa SIM — boîte de dialogue d'exportation, option CSV sélectionnée](../../../static/broker-guides/Directa_2.png){ style="border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

Enregistrez le fichier sans l'ouvrir ni le modifier dans Excel, puis importez-le dans LibreFolio.

## 📝 Notes

- Prise en charge des transactions d'actions, d'obligations et d'ETF, des dividendes, des taxes (*ritenute fiscali*) et des frais de transaction.
- Seul le format **CSV** est pris en charge — pas xlsx ni ods.
- Les opérations de compte sont libellées en EUR.
- L'exportation couvre jusqu'à 3 000 lignes par fichier. Pour des historiques plus longs, exportez plusieurs périodes et importez-les successivement.


