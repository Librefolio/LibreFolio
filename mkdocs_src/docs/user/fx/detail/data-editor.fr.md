# ✏️ Éditeur de données et import CSV

L'éditeur de données vous permet d'ajouter, de modifier et de supprimer les taux enregistrés d'une paire un par un, ou d'en charger plusieurs d'un coup à partir d'un fichier CSV. Rien n'est enregistré tant que vous n'avez pas cliqué sur **Enregistrer**.

---

## 📝 Ouvrir l'éditeur

Cliquez sur ✏️ (**Modifier les taux**) sur le graphique. L'éditeur s'ouvre sous le graphique et les autres panneaux se replient pendant que vous modifiez.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Éditeur de données FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Il liste les taux de la période sélectionnée avec leur **Date**, leur **Taux** et leur **Statut** (**Original**, **Modifié**, **Supprimé** ou **Nouveau**).

- Une date marquée d'un ⚠️ et d'un nombre de jours n'a pas de taux propre (un week-end ou un jour férié) et répète le précédent. L'interrupteur ⚠️ en haut masque ces jours.
- Double-cliquez sur un point du graphique (appui long sur mobile) pour accéder à sa date dans l'éditeur.

---

## ✍️ Modifier les taux

### ➕ Ajouter un taux

Cliquez sur **Ajouter une ligne** : une ligne apparaît le jour suivant la dernière ligne, jamais plus tard qu'aujourd'hui. Modifiez sa date avec le sélecteur de date si nécessaire, puis saisissez le taux.

### ✏️ Modifier un taux

Cliquez sur un taux et saisissez la nouvelle valeur.

### 🗑️ Supprimer des taux

Cliquez sur 🗑️ sur une ligne, ou sélectionnez des lignes et cliquez sur la corbeille en haut. **Annuler** rétablit une ligne jusqu'à l'enregistrement.

### 💾 Enregistrer vos modifications

Vos modifications apparaissent sur le graphique sous forme de ligne **Aperçu** violette. **Enregistrer (N)** les écrit toutes ; **Abandonner** les abandonne. Un taux doit être supérieur à zéro : un taux nul, négatif ou vide est ignoré.

!!! warning "Les données synchronisées écrasent les modifications manuelles"

    Une synchronisation ultérieure des mêmes dates remplace vos valeurs par celles du fournisseur. Pour un contrôle entièrement manuel, utilisez une paire sans fournisseur — voir [Configuration du fournisseur](provider.md).

---

## 📥 Import CSV

### 🔓 Ouvrir la fenêtre d'import

1. Dans l'éditeur, cliquez sur **Importer un CSV**.
2. Dans **Importer des données CSV**, déposez un fichier `.csv` ou `.txt`, ou collez le texte dans la zone.
3. Vérifiez le sens en haut, puis cliquez sur **Importer (N)**.

Les lignes rejoignent l'éditeur : vérifiez-les, puis cliquez sur **Enregistrer**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Fenêtre d'import CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📄 Format du fichier

Deux colonnes, avec une ligne d'en-tête qui définit le sens :

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

| Règle | Détails |
|------|---------|
| **Séparateur** | Point-virgule (`;`) |
| **En-tête** | `date` et le sens, par ex. `EUR>USD` |
| **Dates** | `YYYY-MM-DD` |
| **Taux** | Nombres positifs ; `.` ou `,` comme séparateur décimal, `_` facultatif pour les milliers (`1_000.50`) |

### ↔️ Sens

- `EUR>USD` signifie **1 EUR = X USD** ; `EUR<USD` est l'inverse, **1 USD = X EUR**.
- L'en-tête doit nommer les deux devises de cette paire, dans n'importe quel ordre.
- La barre en haut indique comment les taux sont lus (*Taux interprétés comme : 1 EUR = X USD*) ; ⇄ inverse le sens et réécrit l'en-tête.
- Un fichier dans le sens opposé à la page est inversé pour vous : chaque taux $r$ devient $1/r$.

??? example "📋 Exemples — les mêmes taux écrits dans les deux sens"

    ```csv
    date;EUR>USD
    2024-01-02;1.1045
    2024-01-03;1.0982
    ```

    ```csv
    date;USD>EUR
    2024-01-02;0.9053
    2024-01-03;0.9106
    ```

    Sur la page EUR/USD, les deux fichiers donnent les mêmes taux : `0.9053` devient $1/0.9053 \approx 1.1046$.

### ⚠️ Erreurs courantes

La fenêtre d'import signale chaque ligne incorrecte ; seules les lignes valides sont importées.

| Message | Cause | Correction |
|---------|-------|-----|
| **Les devises de l'en-tête ne correspondent pas** | D'autres devises dans l'en-tête, par ex. `GBP>JPY` sur la page EUR/USD | Utilisez les devises de cette paire |
| **En-tête attendu** ou **Colonnes obligatoires manquantes** | Pas de ligne d'en-tête, ou une colonne manque | Commencez par une ligne telle que `date;EUR>USD` |
| **Format de date invalide** | La date n'est pas au format `YYYY-MM-DD` | Corrigez la date |
| **Nombre invalide** | Le taux n'est pas un nombre | Corrigez la valeur |
| **Date en double** | La même date apparaît deux fois | Conservez une seule ligne par date |

??? info "🔀 Comment les lignes importées fusionnent — lorsque l'éditeur contient déjà certaines dates"

    - Une date déjà présente dans l'éditeur prend le taux importé (**Modifié**) ; une nouvelle date est ajoutée (**Nouveau**). Les dates absentes du fichier restent telles quelles.
    - Les dates situées hors de la période sélectionnée sont également enregistrées, en remplaçant tout taux stocké ces jours-là ; après l'enregistrement, la période s'élargit pour les afficher.
