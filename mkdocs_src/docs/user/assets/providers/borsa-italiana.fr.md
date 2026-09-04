# 🇮🇹 Borsa Italiana

**Borsa Italiana** est la bourse italienne, exploitée par Euronext. LibreFolio inclut un **fournisseur de données d'actifs** dédié qui récupère les prix, les séries historiques et les métadonnées directement depuis le site web de Borsa Italiana.

---

## 🔍 Ce qu'il fournit

| Données | Description |
|---------|-------------|
| **Prix actuel** | Dernier prix officiel du marché pour les instruments cotés ; NAV des fonds uniquement si datée d'aujourd'hui |
| **Prix historiques** | OHLCV quotidien pour les instruments cotés ; un point NAV à la date réelle de la NAV pour les fonds |
| **Métadonnées de l'instrument** | ISIN, segment de marché, devise et identifiants alternatifs lorsque disponibles |

Les actifs négociés sur Borsa Italiana incluent les actions italiennes (segment MTA/MIL), les ETF (ETFplus), les obligations (MOT) et les fonds communs/SICAV.

---

## ⚙️ Configuration

Aucune clé API ou inscription n'est requise — le fournisseur extrait les données publiques du site web de Borsa Italiana. La configuration est disponible par actif dans le panneau **Provider Config** de la page de détail de l'actif.

1. Naviguez vers l'actif que vous souhaitez suivre.
2. Ouvrez le panneau **⚙️ Provider Config**.
3. Sélectionnez **Borsa Italiana** dans la liste des fournisseurs.
4. Entrez l'**ISIN** pour les instruments cotés. Pour les fonds, utilisez la Recherche Intelligente afin d'obtenir automatiquement le code interne Borsa.
5. Enregistrez — LibreFolio récupérera la première série historique lors de la prochaine synchronisation.

!!! tip "Trouver l'ISIN"

    Vous pouvez rechercher l'ISIN sur [borsaitaliana.it](https://www.borsaitaliana.it) en cherchant le nom de l'instrument. L'ISIN est indiqué sur chaque page de détail de l'instrument.

!!! tip "La Recherche Intelligente peut utiliser les liens Borsa"

    Si la recherche normale ne trouve pas un fond, collez ou recherchez avec l'URL de la page du fond/détail de Borsa Italiana. La recherche intelligente de LibreFolio peut résoudre les pages Borsa prises en charge, associer les bons `provider_params` et rendre le fond cotable par son code interne.

---

## 🔄 Synchronisation

Le fournisseur Borsa Italiana participe au cycle standard de **synchronisation d'actifs**. Déclenchez-le manuellement depuis la page de détail de l'actif avec le bouton **🔄 Sync**, ou laissez la tâche d'arrière-plan planifiée s'exécuter la nuit.

!!! note "Limitation de débit"

    Le fournisseur applique un ralentissement automatique pour éviter d'être bloqué par Borsa Italiana. Si vous avez de nombreux actifs sur ce marché, la synchronisation complète peut prendre quelques minutes.

!!! note "Fonds communs (NAV)"

    Les fonds communs et les SICAV sont valorisés par leur **NAV** quotidienne, publiée une fois par jour avec un décalage. LibreFolio valorise chaque fond par son code interne Borsa, et non par ISIN. L'historique des prix affiche un point NAV à sa date réelle et la valeur actuelle est mise à jour uniquement lorsque la NAV publiée est datée d'aujourd'hui (sinon votre dernier prix d'achat est utilisé comme estimation).

!!! note "Identifiants alternatifs"

    Certains identifiants importés ou découverts par le fournisseur sont stockés sous forme de liste modifiable d'identifiants alternatifs. Pour les fonds Borsa Italiana, cette liste peut inclure le code interne du fond tandis que l'ISIN réel reste l'identifiant principal lorsqu'il est disponible.

---

## 🔗 Documentation Développeur

Pour les détails d'implémentation (format des requêtes, stratégie d'extraction HTML, mappage des champs), consultez :

→ [Manuel Développeur — Fournisseur Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Liens connexes

- 📋 **[Aperçu des actifs](../index.md)** — Gérer votre bibliothèque d'actifs
- 🏦 **[Fournisseurs d'actifs](./index.md)** — Autres sources de données
- 📡 **[justETF](./justetf.md)** — Source alternative pour les données d'ETF
