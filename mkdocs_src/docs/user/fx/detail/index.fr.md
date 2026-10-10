# 🔍 Page de détail d'une paire

Cliquez sur une paire dans la [liste FX](../index.md) pour ouvrir sa page : un grand graphique de ses taux, avec des outils
pour analyser, modifier et configurer la paire.

---

## 🗺️ La page en un coup d'œil

- **En-tête** — ⇄ inverse le sens de la paire et la carte de la liste suit (avec des modifications non enregistrées dans
  l'éditeur de taux, LibreFolio demande d'abord) ; ← revient à la liste.
- **Barre d'outils** — la période, le dernier taux avec sa variation, et les boutons **Export IA**, **Fournisseurs**,
  **Synchroniser** et **Recharger**. **Recharger** relit les taux stockés ; **Synchroniser** télécharge les nouveaux,
  voir [Synchronisation](../sync.md).
- **En dessous** — le panneau **Signaux** replié, le graphique, puis le panneau **Mesures** replié.

---

## 🧭 Fonctionnalités

### 📈 [Graphique interactif](chart.md)

L'historique des taux, avec zoom, déplacement, une vue **Abs** / **%** et des préréglages de période.

### 📊 [Signaux](signals.md)

Indicateurs, comparaisons et courbes des indices de référence tracés sur le graphique ; neuf indicateurs fonctionnent sur les taux FX.

### 📐 [Mesures](measures.md)

La variation, la variation en % et le taux annuel entre deux points du graphique.

### ✏️ [Éditeur de données](data-editor.md)

Ajoutez, modifiez ou supprimez des taux individuels, ou importez-en plusieurs d'un coup depuis un fichier CSV.

### ⚙️ [Configuration du fournisseur](provider.md)

**Fournisseurs** modifie l'origine des taux : le fournisseur, les routes de secours et les chaînes.

### 🧠 Export IA

**Export IA** prépare un instantané de la paire, ou une requête **Analyse de paire FX** ou **Impact de l'exposition FX**,
à coller dans un assistant IA. Impact de l'exposition FX ne compte que les liquidités et les positions
détenues directement dans les devises de la paire : il ne regarde pas à l'intérieur des fonds. Voir
[Export IA FX](../../ai-export/fx.md).

---

## 🔗 Voir aussi

- ⚙️ **[Paramètres du graphique](../chart-settings.md)** — Apparence du graphique et signaux superposés
- 📋 **[Vue d'ensemble FX](../index.md)** — Retour à la page de la liste FX
