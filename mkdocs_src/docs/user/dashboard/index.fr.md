# 📊 Tableau de bord

Le Tableau de bord est le **centre de commandement de votre portefeuille** — un seul écran qui vous indique ce que vaut votre portefeuille, comment il se comporte et où votre argent est réparti.

<div class="lf-screenshot-carousel" data-carousel="carousel-dashboard-main" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
  <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="main" data-title="📈 Vue principale (absolue)" alt="Tableau de bord — Mode absolu">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="main-pct" data-title="📈 Vue principale (pourcentage)" alt="Tableau de bord — Mode pourcentage">
  <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="allocation-type-now" data-title="📊 Allocation" alt="Tableau de bord — Allocation">
</div>

## 🗂️ Mise en page à onglets

L'interface du Tableau de bord est organisée en quatre onglets principaux, qui vous permettent de basculer entre différents niveaux de détail :

1. **Vue d'ensemble** (par défaut) : indicateurs clés, soldes de trésorerie et graphiques visuels de votre portefeuille.
2. **[Positions et analyse](positions.md)** : positions ouvertes, pondérations et analyse détaillée des lots fiscaux (FIFO).
3. **[Risque](#risk-tab)** : le panneau **Risque du portefeuille**, qui répond à quatre questions sur le risque de votre portefeuille.
4. **Transactions** : les opérations de la plage de dates et du périmètre de courtiers sélectionnés, sous forme de liste paginée en lecture seule — double-cliquez sur une ligne pour ouvrir son visualiseur de détail. Voir [Transactions](../transactions/index.md) pour le guide complet.

---

## 📈 Onglet Vue d'ensemble

L'onglet Vue d'ensemble est la page d'accueil par défaut. Il est structuré selon les sections suivantes :

| Section | Description |
|---------|-------------|
| **[Cartes KPI](kpi-cards.md)** | Synthèse de la valeur nette, du P&L période et des taux de rendement. |
| **Soldes de trésorerie** | Soldes liquides regroupés par devise sur le périmètre de courtiers actif. |
| **[Graphique de croissance](charts.md#portfolio-growth-chart)** | Valeur du portefeuille dans le temps selon trois vues : valeurs absolues (Abs), taux de rendement (%) et argent réellement gagné (P&L). |
| **[Panneau d'allocation](charts.md#allocation-panel)** | Graphiques en anneau et empilés historiques regroupés par Type, Secteur et Zone géographique. |

### 🪙 Soldes de trésorerie

Directement sous les cartes KPI, le panneau **Soldes de trésorerie** affiche le total de votre trésorerie disponible agrégé par devise. Par exemple, si vous détenez des USD chez le courtier A et des EUR chez le courtier B, les deux soldes seront affichés côte à côte.

Lorsque vous appliquez un filtre de courtiers, les soldes de trésorerie se mettent automatiquement à jour pour ne refléter que la trésorerie détenue chez les courtiers sélectionnés.

---

## 🛡️ Onglet Risque {: #risk-tab }

L'onglet Risque contient le panneau **Risque du portefeuille**, qui répond à quatre questions sur le risque de votre portefeuille : **Combien cela peut-il me coûter ?**, **Suis-je aussi diversifié que je le pense ?**, **Suis-je rémunéré pour ce risque ?** et **Et si… ?** Il couvre toujours l'ensemble de votre portefeuille — chaque courtier que vous détenez avec une part supérieure à 0 % — et suit la plage de dates et la devise cible du tableau de bord, mais pas le filtre de courtiers : lorsqu'un filtre est actif, un sous-titre le signale. Voir [Onglet Risque](risk.md) pour les blocs et les outils qu'il affiche.

---

## 🎛️ Plage de dates, filtres et export IA

En haut à droite du tableau de bord, plusieurs contrôles vous permettent de personnaliser votre vue :

- **Plage temporelle** — des préréglages de **1S** à **Tout**, ou une plage personnalisée via le sélecteur de dates.
- **Filtre de courtiers** — restreint les indicateurs à un ou plusieurs courtiers spécifiques ; l'onglet Risque couvre toujours chaque courtier que vous détenez, et un sous-titre le signale lorsqu'un filtre est actif.
- **Devise cible** — convertit dynamiquement tous les actifs et soldes de trésorerie dans une seule devise sélectionnée pour une vue agrégée. La liste propose votre devise par défaut et les devises de vos paires FX configurées — les deux extrémités de chaque paire. Une devise que seule une [route en chaîne](../fx/add-pair.md) traverse n'est pas proposée : la synchronisation d'une chaîne ne stocke que le taux de sa propre paire, c'est pourquoi LibreFolio n'a aucun taux pour convertir vers cette devise. Pour rendre une devise disponible, donnez-lui sa propre paire : choisissez **Créer un forex…** en bas de la liste, ou cochez **Créer aussi les paires intermédiaires** lorsque vous ajoutez une paire via une route en chaîne.
- **Export IA** (:material-brain:) — ouvre un export vers le presse-papiers. Choisissez **Instantané de données** pour les données factuelles uniquement, ou une **tâche d'analyse** qui inclut automatiquement ses instructions et son contrat de réponse, puis sélectionnez le **niveau de détail** (Compact, Standard ou Complet). L'instantané côté serveur suit le filtre de courtiers, la plage de dates et la devise cible actifs ; LibreFolio ne contacte aucun service d'IA. Voir [Export IA du portefeuille](../ai-export/portfolio.md) ou la [vue d'ensemble de l'export IA](../ai-export/index.md).

La plage temporelle, le filtre de courtiers et la devise cible restent tels que vous les avez définis pour le reste de votre session dans cet onglet de navigateur — un rechargement de page les conserve également — et sont réinitialisés lorsque vous vous déconnectez. La plage temporelle est partagée avec les autres pages qui en ont une (les pages Actifs et FX, leurs pages de détail, et la page de chaque courtier), si bien qu'une modification effectuée là-bas apparaît aussi ici. À côté de **Export IA**, le bouton **Actualiser** (:material-refresh:) recalcule tout à la demande : voir [Revenir et actualiser](#coming-back-and-refreshing).

!!! tip "Le périmètre compte"

    Lorsque vous filtrez sur un seul courtier, les virements *vers d'autres courtiers* deviennent des flux externes pour ce périmètre. Cela affecte les calculs du [Capital versé](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md) et du [P&L](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md).

!!! note "Le partage affecte ces chiffres"

    Le tableau de bord ne compte que les courtiers que vous **détenez** avec une part supérieure à 0 %, et chaque montant provenant d'eux est **mis à l'échelle selon votre part de détention** : un Propriétaire avec une part de 50 % voit la moitié de la valeur, des revenus et du P&L de ce courtier comptabilisés dans les totaux. Les courtiers pour lesquels vous êtes **Éditeur** ou **Lecteur** — qui portent toujours une part de 0 % par règle — sont exclus, comme ceux que vous détenez avec une part de 0 % : ils sont absents des totaux, du filtre de courtiers, de l'onglet Positions (vue Période et panneau des lots inclus), de l'onglet Risque et de l'onglet Transactions. Vous les voyez sur leur propre page de courtier, qui compte le courtier **dans son intégralité** pour chaque rôle. Voir [Partage de courtier](../brokers/sharing.md) pour plus de détails.

La page d'un courtier est ce même Tableau de bord appliqué à un seul courtier, avec son propre onglet **Info** : voir [La page du courtier est le Tableau de bord appliqué à un seul courtier](../brokers/index.md#broker-page-is-dashboard).

---

## 🔄 Revenir et actualiser {: #coming-back-and-refreshing }

Revenez au Tableau de bord — depuis la barre latérale, ou avec le bouton retour **←** d'une page d'actif — et il affiche immédiatement ce qu'il affichait lorsque vous l'avez quitté : les cartes KPI, les graphiques, l'onglet Positions avec sa vue Période et son panneau [Analyse des lots FIFO](positions.md#fifo-lots-analysis), et l'onglet Risque. Aucun espace réservé de chargement n'apparaît, et les chiffres des KPI s'affichent directement à leur valeur au lieu de compter à partir de zéro. Si vous avez modifié la plage temporelle sur une autre page entre-temps, le Tableau de bord s'ouvre sur cette plage à la place.

- **Si rien n'a changé entre-temps**, c'est tout : LibreFolio ne recalcule rien.
- **Si quelque chose a changé** — par exemple une transaction ; des prix, taux ou événements saisis à la main ou apportés par une synchronisation ; un actif modifié ou fusionné ; une modification de l'un de vos courtiers ou de votre accès à celui-ci ; ou le prix live qu'une page d'actif vérifie pendant qu'elle est ouverte — les anciens chiffres restent à l'écran pendant que LibreFolio recalcule en arrière-plan, puis les nombres passent aux nouvelles valeurs. Une synchronisation de prix ou de taux qui n'a rien apporté de nouveau n'est pas un changement.

Le bouton **Actualiser** recalcule tout, même lorsque rien n'a changé : les chiffres, la vue Période, le panneau des lots et l'onglet Risque. Ce que vous voyez reste à l'écran pendant ce temps.

Si un recalcul échoue, les chiffres déjà affichés restent affichés et un message vous en informe. Dans l'onglet Risque, cela ne vaut que pour les chiffres de la période et de la devise que vous consultez : si vous basculez vers une période ou une devise pour laquelle l'onglet n'a pas encore de chiffres et que le calcul échoue, il affiche *Les données de risque n'ont pas pu être chargées.* à la place de ses niveaux, plutôt que les chiffres de votre choix précédent.

---

## 🌡️ Bannière de qualité des données {: #data-quality-banner }

Si des prix ou des taux FX manquent à la date de fin, une bannière apparaît en haut pour expliquer quels actifs n'ont pas pu être valorisés.
<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="data-quality-banner" alt="Bannière de qualité des données du tableau de bord avec liens par actif">
</div>
 Les actifs sans fournisseur de prix (saisis manuellement, comme les projets de financement participatif immobilier) sont valorisés au prix de leur dernier achat ou de leur dernière vente, sauf si vous saisissez vous-même un prix plus récent — c'est intentionnel et cela ne génère aucun avertissement. Un actif qui a bien un fournisseur de prix mais n'a toujours pas de prix de marché à la date de fin, plus de deux semaines après votre premier achat, est lui aussi valorisé entre-temps au prix de son dernier achat ou de sa dernière vente, et la bannière le liste : une obligation achetée à l'émission, avant sa première cotation, par exemple.

Un ajustement enregistre ce que les unités ont coûté, jamais un prix. Un transfert aussi, avec une exception : pour un actif qui n'a encore rien d'autre — aucun prix de marché, aucun achat ou vente, aucun ajustement, aucune sortie antérieure — le coût que vous avez attribué à un transfert entrant fait office de prix, une estimation, jusqu'à ce qu'un prix réel ou une transaction le remplace. Un tel actif est valorisé à ce coût converti au taux de change de chaque jour, sa valeur évolue donc avec le taux, et la bannière le traite comme un actif valorisé à son dernier achat ou à sa dernière vente : pour un actif doté d'un fournisseur de prix, il est listé plus de deux semaines après l'arrivée du transfert, s'il n'a toujours pas de prix de marché. Un actif coté déplacé entre vos courtiers conserve son prix de marché. Un actif que vous détenez sans aucun prix — aucun prix de marché, aucun achat ou vente et aucun transfert de ce type, comme celui que vous avez reçu par le biais d'un ajustement — est valorisé à ce qu'il vous a coûté, lorsque ce coût est connu, sans plus-value ni moins-value latente. Pour un actif manuel, c'est intentionnel et cela ne génère aucun avertissement ; pour un actif doté d'un fournisseur de prix, plus de deux semaines après sa première acquisition, la bannière le liste comme *valorisé au coût* jusqu'à ce qu'il obtienne un prix.

La bannière vous avertit également lorsqu'un actif que vous détenez a un fournisseur de prix mais que son dernier prix date de **plus d'une semaine** à la date de fin : cliquez sur **Synchroniser les prix** pour récupérer les prix manquants, et l'avertissement disparaît une fois qu'ils sont à jour. Les actifs manuels ne sont jamais signalés de cette façon, puisqu'il n'y a rien à synchroniser.

Il en va de même pour les **taux de change obsolètes**. Lorsque le portefeuille est valorisé à la date de fin avec un taux de change dont le dernier taux stocké date de **plus d'une semaine**, une ligne d'avertissement liste les paires de devises concernées, avec un seul bouton **Synchroniser les taux** pour toutes. Si la synchronisation réussit mais que le fournisseur n'a pas encore de taux plus récent, une alerte le signale — *Le fournisseur n'a pas encore de taux plus récents pour USD → EUR : réessayez plus tard* — au lieu d'un simple message de succès ; réessayez plus tard, et la ligne disparaît une fois un taux plus récent stocké.

Il liste également les actifs dont le **coût d'achat est manquant** : un transfert ou un ajustement qui a apporté des unités sans coût de base. LibreFolio ne peut pas savoir ce que ces unités ont coûté, il les compte donc pour zéro dans votre coût d'achat et affiche le coût moyen et le P&L latent de cette position comme indisponibles (`—`). Pour corriger cela, retrouvez ce transfert ou cet ajustement parmi vos [transactions](../transactions/index.md) et attribuez-lui son coût de base.

Il vous avertit également des **codes de devise qui ne sont pas des codes ISO** : un nombre ou un nom, comme `978` ou `EURO`, qu'une version antérieure de LibreFolio a enregistré tel que vous l'avez saisi. LibreFolio n'enregistre désormais que des codes tels que `EUR`, les montants d'une telle valeur ne peuvent donc pas être convertis, et une ligne qui la contient ne peut plus être enregistrée après une modification tant que son code n'est pas corrigé. L'avertissement nomme la valeur et le code qu'elle représente (`978` est `EUR`), et ne liste aucun taux de change à ajouter pour elle, car aucun ne serait utile. Lorsque la valeur est votre propre devise par défaut, il vous indique de la choisir à nouveau dans **Paramètres › Préférences**. Votre administrateur peut lister toutes ces valeurs avec `./dev.py db currencies` ([Outils d'administration CLI](../../admin/cli_tools.md), « Codes de devise qui ne sont pas des codes ISO »).

Il signale aussi, sans vous demander de corriger quoi que ce soit, les **transferts entre courtiers que vous détenez à des parts différentes** : chaque côté compte à la part de son propre courtier, ce qui quitte un courtier et ce qui arrive à l'autre diffèrent donc, et LibreFolio compte cette différence comme une plus-value ou une moins-value.

Les taux de change sont vérifiés pour chaque transaction jusqu'à la date de fin — chaque achat, vente et mouvement de trésorerie est converti au taux de sa propre date — et, pour valoriser ce que vous détenez, à chaque jour de la période affichée : vos titres, ainsi que la trésorerie que vous gardez dans une autre devise, valorisée chaque jour au taux de ce jour. Lorsqu'une paire FX configurée avec un fournisseur n'a **aucun taux** pour certaines de ces dates, la bannière la liste avec l'intervalle des dates manquantes. LibreFolio convertit un montant avec le taux le plus récent à sa date ou antérieur, quelle que soit son ancienneté, ces dates se situent donc *avant* le premier taux stocké de la paire — souvent bien avant la période affichée, car chaque transaction passée compte dans les totaux tels que votre P&L total et votre coût d'achat. Cliquez sur **Synchroniser les taux** pour les remplir :

- LibreFolio télécharge cet intervalle de dates avec **une semaine supplémentaire de chaque côté** (jamais au-delà d'aujourd'hui), quelle que soit la période affichée par le tableau de bord. La semaine supplémentaire couvre les week-ends et jours fériés, lorsque les fournisseurs ne publient rien : un tel jour en bordure d'intervalle prend alors le taux du jour ouvré précédent.
- Une fois le téléchargement terminé, le tableau de bord s'actualise et un message rapporte le résultat pour chaque paire.
- Si le téléchargement aboutit mais que les mêmes paires sont toujours signalées, le fournisseur n'a pas de taux pour les dates encore manquantes — généralement parce qu'elles précèdent le début de son historique. Le message se transforme alors en un avertissement qui le dit : saisissez ces taux à la main dans l'[Éditeur de données](../fx/detail/data-editor.md) de la paire.

Les paires avec des taux manuels uniquement (sans fournisseur) reçoivent leur propre avertissement : le bouton **Voir FX** de cet avertissement ouvre la page de la première paire qu'il liste, où vous ajoutez les taux vous-même.

!!! tip "Remplir tout l'historique d'une paire en une fois"

    Ouvrez la [page FX](../fx/index.md), choisissez la plage **Tout** et cliquez sur [Tout synchroniser](../fx/sync.md) : LibreFolio télécharge tout ce que les fournisseurs publient pour vos paires, jusqu'à aujourd'hui. Une paire que vous ajoutez avec un fournisseur fait cela d'elle-même — voir [Ajouter une paire de devises](../fx/add-pair.md).

---

## 🔗 Dans cette section

- 💰 **[Cartes KPI](kpi-cards.md)** — Valeur nette, P&L période et rendements expliqués
- 📊 **[Graphiques](charts.md)** — Graphique de croissance et panneau d'allocation expliqués
- 🔍 **[Positions et analyse](positions.md)** — Positions ouvertes, vues tableau vs carte, et analyse détaillée des lots fiscaux FIFO.

## 🔗 Théorie associée

- **[NAV / valeur nette](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md)**
- **[Valeur comptable](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/book-value.md)**
- **[P&L période](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/period-pnl.md)**
- **[Capital versé et P&L total](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/deposited-capital.md)**
- **[Vue d'ensemble des indicateurs de performance](../../financial-theory/technical-analysis/performance-metrics/index.md)**
