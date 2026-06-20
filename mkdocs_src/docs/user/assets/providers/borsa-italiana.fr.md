# <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" alt=""> Borsa Italiana

**Borsa Italiana** est la bourse italienne, opérée par Euronext. LibreFolio inclut un **fournisseur d'actif** dédié qui récupère les prix, les séries historiques et les métadonnées des instruments directement depuis le site web de Borsa Italiana.

---

## 🔍 Ce qu'il fournit

| Données | Description |
|------|-------------|
| **Prix actuel** | Dernier prix officiel du marché |
| **Historique OHLCV** | Séries quotidiennes d'ouverture/haut/bas/clôture/volume |
| **Métadonnées de l'instrument** | ISIN, segment de marché, devise |

Les actifs négociés sur Borsa Italiana comprennent les actions italiennes (segment MTA/MIL), les ETF (ETFplus), les obligations (MOT) et les fonds.

---

## ⚙️ Configuration

Aucune clé API ni inscription n'est requise — le fournisseur scrape les données publiques du site web de Borsa Italiana. La configuration est disponible par actif dans le panneau **Configuration du fournisseur** de la page de détails de l'actif.

1. Naviguez vers l'actif que vous souhaitez suivre.
2. Ouvrez le panneau **⚙️ Configuration du fournisseur**.
3. Sélectionnez **Borsa Italiana** dans la liste des fournisseurs.
4. Entrez l'**ISIN** ou le code ticker de Borsa Italiana.
5. Enregistrez — LibreFolio récupérera la première série historique lors de la prochaine synchronisation.

!!! tip "Trouver l'ISIN"

    Vous pouvez rechercher l'ISIN sur [borsaitaliana.it](https://www.borsaitaliana.it) en recherchant le nom de l'instrument. L'ISIN est affiché sur chaque page de détails de l'instrument.

---

## 🔄 Synchronisation

Le fournisseur Borsa Italiana participe au cycle standard de **synchronisation des actifs**. Déclenchez-la manuellement depuis la page de détails de l'actif avec le bouton **🔄 Sync**, ou laissez la tâche planifiée d'arrière-plan s'exécuter pendant la nuit.

!!! note "Limitation du débit"

    Le fournisseur limite automatiquement le débit pour éviter d'être bloqué par Borsa Italiana. Si vous possédez de nombreux actifs de cette bourse, la synchronisation complète peut prendre quelques minutes.

---

## 🔗 Documentation Développeur

Pour les détails d'implémentation (format de requête, stratégie d'analyse HTML, mappage des champs), voir :

→ [Manuel du Développeur — Fournisseur Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Liens connexes

- 📋 **[Aperçu des Actifs](../index.md)** — Gérez votre bibliothèque d'actifs
- 🏦 **[Fournisseurs d'actif](./index.md)** — Autres sources de données
- 📡 **[justETF](./justetf.md)** — Source alternative pour les données ETF
