# 📊 Tableau de bord

Le Tableau de bord est le **centre de commandement de votre portefeuille** — un écran unique qui vous indique la valeur de votre portefeuille, sa performance et la répartition de votre argent.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vue principale (absolue)" alt="Tableau de bord — Mode absolu">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vue principale (pourcentage)" alt="Tableau de bord — Mode pourcentage">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Répartition" alt="Tableau de bord — Répartition">
</div>

## 🗂️ Disposition à onglets

L'interface du Tableau de bord est organisée en quatre onglets principaux, vous permettant de basculer entre différents niveaux de détail :

1. **Vue d'ensemble** (par défaut) : indicateurs clés, soldes de trésorerie et graphiques visuels de votre portefeuille.
2. **[Positions et analyse](positions.md)** : positions ouvertes, pondérations et analyse détaillée des lots fiscaux (FIFO).
3. **[Risque](#risk-tab)** : le panneau **Risque du portefeuille**, qui répond à quatre questions sur le risque de votre portefeuille.
4. **Transactions** : les opérations dans la plage de dates et le périmètre de courtiers sélectionnés, sous forme de liste paginée en lecture seule — double-cliquez sur une ligne pour ouvrir sa visionneuse de détail. Voir [Transactions](../transactions/index.md) pour le guide complet.

---

## 📈 Onglet Vue d'ensemble

L'onglet Vue d'ensemble est la page d'accueil par défaut. Il est structuré en sections suivantes :

| Section | Description |
|---------|-------------|
| **[Cartes KPI](kpi-cards.md)** | Résumé de la valeur nette, du P&L période et des métriques de taux de rendement. |
| **Soldes de trésorerie** | Soldes de trésorerie regroupés par devise sur l'ensemble du périmètre de courtiers actif. |
| **[Graphique de croissance](charts.md#portfolio-growth-chart)** | Valeur du portefeuille dans le temps selon trois vues : valeurs absolues (Abs), taux de rendement (%) et l'argent réellement gagné (P&L). |
| **[Panneau de répartition](charts.md#allocation-panel)** | Graphiques en anneau et historiques empilés regroupés par type, secteur et zone géographique. |

### 🪙 Soldes de trésorerie

Directement sous les cartes KPI, le panneau **Soldes de trésorerie** affiche le total de vos liquidités agrégé par devise. Par exemple, si vous détenez des USD chez le courtier A et des EUR chez le courtier B, les deux soldes seront affichés côte à côte.

Lorsque vous appliquez un filtre de courtiers, les soldes de trésorerie se mettent automatiquement à jour pour ne refléter que la trésorerie détenue au sein des courtiers sélectionnés.

---

## 🛡️ Onglet Risque {: #risk-tab }

L'onglet Risque contient le panneau **Risque du portefeuille**, qui répond à quatre questions sur le risque de votre portefeuille : **Combien cela peut-il faire mal ?**, **Suis-je aussi diversifié que je le pense ?**, **Suis-je rémunéré pour ce risque ?** et **Et si… ?** Il couvre toujours l'intégralité de votre portefeuille — chaque courtier que vous détenez avec une part supérieure à 0 % — et suit la plage de dates et la devise cible du tableau de bord, mais pas le filtre de courtiers : lorsqu'un filtre est actif, un sous-titre l'indique. Voir [Onglet Risque](risk.md) pour les blocs et les outils qu'ils affichent.

---

## 🎛️ Plage de dates, filtres et export IA

En haut à droite du tableau de bord, vous disposez de plusieurs contrôles pour personnaliser votre vue :

- **Plage temporelle** — des préréglages d'une semaine à Tout l'historique (MAX), ou une plage personnalisée via le sélecteur de dates.
- **Filtre de courtiers** — filtre les métriques sur un ou plusieurs courtiers spécifiques ; l'onglet Risque couvre toujours chaque courtier que vous détenez, et un sous-titre l'indique lorsqu'un filtre est actif.
- **Devise cible** — convertit dynamiquement tous les actifs et soldes de trésorerie dans une seule devise sélectionnée pour une vue agrégée. La liste propose votre devise par défaut et les devises de vos paires FX configurées — les deux extrémités de chaque paire. Une devise qu'une [route en chaîne](../fx/add-pair.md) traverse uniquement n'est pas proposée : la synchronisation d'une chaîne ne stocke que le taux de sa propre paire, LibreFolio n'a donc aucun taux pour convertir vers cette devise. Pour rendre une devise disponible, attribuez-lui sa propre paire : choisissez **Créer un forex…** en bas de la liste, ou cochez **Créer également les paires intermédiaires** lorsque vous ajoutez une paire via une route en chaîne.
- **Export IA** (:material-brain:) — ouvre un export vers le presse-papiers. Choisissez **Capture de données**
  pour les données factuelles uniquement, ou une **tâche d'analyse** qui inclut automatiquement
  ses instructions et son contrat de réponse, puis sélectionnez le **niveau de détail**
  (Compact, Standard ou Complet). La capture côté backend suit le filtre de courtiers,
  la plage de dates et la devise cible actifs ; LibreFolio ne contacte aucun
  service d'IA. Voir [Export IA du portefeuille](../ai-export/portfolio.md) ou la
  [présentation de l'Export IA](../ai-export/index.md).

La plage temporelle, le filtre de courtiers et la devise cible restent tels que vous les avez définis pour le reste de votre session dans cet onglet de navigateur — un rechargement de page les conserve également — et sont réinitialisés lorsque vous vous déconnectez. La plage temporelle est partagée avec les autres pages qui en disposent (les pages Actifs et FX, leurs pages de détail, et la page de chaque courtier), ainsi une modification effectuée là-bas apparaît ici aussi. À côté de **Export IA**, le bouton **Actualiser** (:material-refresh:) recalcule tout à la demande : voir [Revenir et actualiser](#coming-back-and-refreshing).

!!! tip "Le périmètre compte"

    Lorsque vous filtrez sur un seul courtier, les virements *vers d'autres courtiers* deviennent des flux externes pour ce périmètre. Cela affecte les calculs du [Capital versé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) et du [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "Le partage affecte ces chiffres"

    Le tableau de bord ne compte que les courtiers que vous **détenez** avec une part supérieure à 0 %, et chaque montant qui en provient est **mis à l'échelle selon votre part de détention** : un Propriétaire avec une part de 50 % voit la moitié de la valeur, des revenus et du P&L de ce courtier comptabilisés dans les totaux. Les courtiers où vous êtes **Éditeur** ou **Lecteur** — qui portent toujours une part de 0 % par règle — sont exclus, tout comme ceux que vous détenez avec une part de 0 % : ils sont absents des totaux, du filtre de courtiers, de l'onglet Positions (vue Performance et panneau des lots inclus), de l'onglet Risque et de l'onglet Transactions. Vous les voyez sur leur propre page de courtier, où les Éditeurs et Lecteurs obtiennent les montants **complets** du courtier. Voir [Partage de courtier](../brokers/sharing.md) pour plus de détails.

---

## 🔄 Revenir et actualiser {: #coming-back-and-refreshing }

Revenez au Tableau de bord — depuis la barre latérale, ou avec le bouton **←** de retour d'une page d'actif — et il affiche immédiatement ce qu'il montrait lorsque vous l'avez quitté : les cartes KPI, les graphiques, l'onglet Positions avec sa vue Performance et son panneau [Analyse des lots FIFO](positions.md#fifo-lots-analysis), et l'onglet Risque. Il n'y a aucun espace réservé de chargement, et les chiffres des KPI apparaissent à leur valeur finale au lieu de s'incrémenter depuis zéro. Si vous avez modifié la plage temporelle sur une autre page entre-temps, le Tableau de bord s'ouvre sur cette plage.

- **Si rien n'a changé entre-temps**, c'est tout : LibreFolio ne recalcule rien.
- **Si quelque chose a changé** — par exemple une transaction ; des prix, taux ou événements saisis manuellement ou apportés par une synchronisation ; un actif modifié ou fusionné ; une modification de l'un de vos courtiers ou de votre accès à celui-ci ; ou le prix live qu'une page d'actif vérifie tant qu'elle est ouverte — les anciens chiffres restent à l'écran pendant que LibreFolio recalcule en arrière-plan, puis les chiffres passent aux nouvelles valeurs. Une synchronisation de prix ou de taux qui n'a rien apporté de nouveau n'est pas un changement.

Le bouton **Actualiser** recalcule tout, même lorsque rien n'a changé : les chiffres, la vue Performance, le panneau des lots et l'onglet Risque. Ce que vous voyez reste à l'écran pendant ce temps.

Si un recalcul échoue, les chiffres déjà à l'écran restent et un message vous en informe. Dans l'onglet Risque, cela ne vaut que pour les chiffres de la période et de la devise que vous consultez : si vous basculez vers une période ou une devise pour laquelle l'onglet n'a pas encore de chiffres et que le calcul échoue, il affiche *Les données de risque n'ont pas pu être chargées.* à la place de ses niveaux, plutôt que les chiffres de votre choix précédent.

---

## 🌡️ Bannière de qualité des données {: #data-quality-banner }

Si des prix ou des taux FX sont manquants à la date de fin, une bannière apparaît en haut pour expliquer quels actifs n'ont pas pu être valorisés.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Bannière de qualité des données du tableau de bord avec liens par actif">
</div>
 Les actifs sans fournisseur de prix (saisis manuellement, comme les projets de financement participatif immobilier) sont valorisés au prix de leur dernière transaction, sauf si vous saisissez vous-même un prix plus récent — c'est intentionnel et ne génère pas d'avertissement. Un actif qui dispose bien d'un fournisseur de prix mais qui n'a toujours pas de prix de marché à la date de fin, plus de deux semaines après votre premier achat, est valorisé entre-temps au prix de sa dernière transaction également, et la bannière le liste : une obligation achetée à l'émission, avant sa première cotation, par exemple.

La bannière vous avertit également lorsqu'un actif que vous détenez dispose d'un fournisseur de prix mais que son dernier prix a **plus d'une semaine** à la date de fin : cliquez sur **Synchroniser les prix** pour récupérer les prix manquants, et l'avertissement disparaît une fois qu'ils sont à jour. Les actifs manuels ne sont jamais signalés de cette manière, puisqu'il n'y a rien à synchroniser.

Elle liste aussi les actifs avec un **coût d'achat manquant** : un transfert ou un ajustement qui a apporté des unités sans coût de base. LibreFolio ne peut pas savoir combien ces unités ont coûté, il les compte donc à zéro dans votre coût d'achat et affiche le coût moyen et le P&L latent de cette position comme indisponibles (`—`). Pour corriger cela, trouvez ce transfert ou cet ajustement parmi vos [transactions](../transactions/index.md) et attribuez-lui son coût de base.

Les taux de change sont vérifiés pour chaque transaction jusqu'à la date de fin — chaque achat, vente et mouvement de trésorerie est converti au taux de sa propre date — et, pour valoriser ce que vous détenez, à chaque jour de la période affichée. Lorsqu'une paire FX configurée avec un fournisseur n'a **aucun taux** pour certaines de ces dates, la bannière la liste avec l'intervalle des dates manquantes. LibreFolio convertit un montant avec le taux le plus récent à sa date ou antérieur, aussi ancien soit-il, donc ces dates se situent *avant* le premier taux stocké de la paire — souvent bien avant la période affichée, car chaque transaction passée compte dans les totaux tels que votre P&L total et votre coût d'achat. Cliquez sur **Synchroniser les taux** pour les compléter :

- LibreFolio télécharge cet intervalle de dates avec **une semaine supplémentaire de chaque côté** (jamais au-delà d'aujourd'hui), quelle que soit la période affichée par le tableau de bord. La semaine supplémentaire couvre les week-ends et jours fériés, lorsque les fournisseurs ne publient rien : un tel jour en bordure de l'intervalle prend alors le taux du jour ouvré précédent.
- Une fois le téléchargement terminé, le tableau de bord s'actualise et un message rapporte le résultat pour chaque paire.
- Si le téléchargement aboutit mais que les mêmes paires sont toujours signalées, le fournisseur n'a pas de taux pour les dates encore manquantes — généralement parce qu'elles précèdent le début de son historique. Le message devient alors un avertissement qui l'indique : saisissez ces taux manuellement dans l'[Éditeur de données](../fx/detail/data-editor.md) de la paire.

Les paires avec des taux manuels uniquement (sans fournisseur) reçoivent leur propre avertissement : son bouton **Voir FX** ouvre la page de la première paire qu'il liste, où vous ajoutez les taux vous-même.

!!! tip "Remplir tout l'historique d'une paire en une fois"

    Ouvrez la [page FX](../fx/index.md), choisissez la plage **Tout** (MAX) et cliquez sur [Tout synchroniser](../fx/sync.md) : LibreFolio télécharge tout ce que les fournisseurs publient pour vos paires, jusqu'à aujourd'hui. Une paire que vous ajoutez avec un fournisseur effectue cela d'elle-même — voir [Ajouter une paire de devises](../fx/add-pair.md).

---

## 🔗 Dans cette section

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L période et rendements expliqués
- 📊 **[Graphiques](charts.md)** — Graphique de croissance et panneau de répartition expliqués
- 🔍 **[Positions et analyse](positions.md)** — Positions ouvertes, vues tableau vs. carte, et analyse détaillée des lots fiscaux FIFO.

## 🔗 Théorie associée

- **[NAV / Valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Présentation des métriques de performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
