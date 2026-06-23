# :heart: Soutenir LibreFolio

LibreFolio est un projet **open-source**, sous licence AGPL-3.0. Le code source est librement disponible, et toute personne disposant des compétences et de l'infrastructure nécessaires peut l'installer et l'exécuter de manière indépendante — c'est toute la beauté de l'open source.

Si vous utilisez LibreFolio et que vous le trouvez utile, nous apprécierions votre soutien — que ce soit par du **code**, des **idées** ou un **petit don**. Chaque contribution alimente la croissance du projet.

---

## :coffee: Offrez-moi un café

Si LibreFolio vous aide à mieux gérer vos investissements, envisagez de soutenir le développement en offrant un café :

<a href="https://www.buymeacoffee.com/librefolio" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Offrez-moi un café" style="height: 60px !important;width: 217px !important;" ></a>

Chaque don — aussi petit soit-il — aide à couvrir les outils de développement, l'infrastructure de test et motive l'amélioration continue.

---

## :rocket: Contributions à fort impact

Pour nous, **une excellente idée ou une contribution de code est tout aussi précieuse qu'un don**. Voici les domaines où votre aide peut faire la plus grande différence :

### :electric_plug: Nouveaux Plugins

LibreFolio utilise un [Système de Registre & Plugins](../developer/architecture/patterns/registry_pattern.md) avec auto-découverte. Ajouter un nouveau plugin est l'une des contributions les plus impactantes que vous puissiez faire :

| Type | Guide | Ce qu'il fait |
|------|-------|-------------|
| 📥 **BRIM** | [Guide Plugin BRIM](../developer/architecture/patterns/brim_plugin_guide.md) | Importer des transactions depuis un nouveau courtier (CSV/Excel) |
| 📈 **Actif** | [Guide Plugin Actif](../developer/architecture/patterns/asset_plugin_guide.md) | Récupérer les prix depuis une nouvelle source de données |
| 💱 **FX** | [Guide Plugin FX](../developer/architecture/patterns/fx_plugin_guide.md) | Ajouter un nouveau fournisseur de taux de change |
| 📊 **Chart Signals** | *Guide bientôt disponible* | Nouveaux indicateurs techniques et superpositions de graphiques (EMA, MACD, RSI, Bollinger…) |

* **Si vous n'êtes pas développeur** : vous pouvez demander un nouveau plugin en remplissant notre [Formulaire de Demande de Plugin](https://github.com/Librefolio/LibreFolio/issues/new?template=plugin_request.yml). En plus des détails de la demande, il est nécessaire de fournir des exemples réels et anonymisés (par exemple, des fichiers CSV ou Excel) du rapport de votre courtier.
* **Si vous êtes développeur** : vous pouvez procéder directement de votre côté à leur implémentation. Consultez le [Guide du Registry & Plugin System](../developer/architecture/patterns/registry_pattern.md) et les guides spécifiques liés dans le tableau ci-dessus pour découvrir comment créer des plugins.

### :art: Idées UI/UX

Améliorations esthétiques, suggestions de mise en page, optimisations de l'accessibilité — si vous voyez quelque chose qui pourrait être plus beau ou mieux fonctionner, dites-le nous en ouvrant un ticket à l'aide de notre [Formulaire d'idées & Suggestions UX](https://github.com/Librefolio/LibreFolio/issues/new?template=idea.yml) sur GitHub.

### :bug: Rapports de bugs

Trouver et signaler clairement des problèmes est extrêmement utile. Ouvrez un nouveau rapport à l'aide de notre [Formulaire de Rapport de Bug](https://github.com/Librefolio/LibreFolio/issues/new?template=bug_report.yml) sur GitHub.

Le formulaire vous guidera pour fournir les informations sur le navigateur, la méthode de déploiement et les journaux d'erreurs.

---

## :rocket: Demandes de Fonctionnalités

Proposez des fonctionnalités spécifiques avec des cas d'utilisation clairs en remplissant notre [Formulaire de Demande de Feature](https://github.com/Librefolio/LibreFolio/issues/new?template=feature_request.yml) sur GitHub.

Chaque demande sera évaluée et prise en compte dès qu'il y aura la capacité de la développer. Les demandes bien décrites avec des exemples concrets sont prioritaires.

---

## :computer: Contribuer au code

Si vous êtes développeur et souhaitez contribuer directement :

1. **Créez un fork** du [dépôt](https://github.com/Librefolio/LibreFolio)
2. **Créez une branche** pour votre fonctionnalité ou votre correction
3. **Développez et testez** dans votre propre dépôt
4. **Soumettez une Pull Request** avec une description claire et un préfixe de mot-clé dans le titre :

| Mot-clé | Quand l'utiliser |
|---------|------------|
| **`[FIX]`** | Corrections de bugs |
| **`[FEAT]`** | Nouvelles fonctionnalités ou améliorations |
| **`[PLUGIN]`** | Nouveau plugin (BRIM, Actif, FX, signal) |
| **`[DOCS]`** | Améliorations de la documentation |

!!! warning "Merge policy"

    Une PR sera fusionnée **uniquement si tous les tests existants continuent de passer**. Si vos modifications nécessitent des mises à jour des tests, incluez-les dans la PR — c'est tout à fait normal et attendu.

Consultez le [Manuel du Développeur](../developer/index.md) pour les détails d'architecture, les conventions de codage et les directives de test.

---

## :star: Mettre une étoile au projet

Un moyen simple mais puissant d'aider : **mettez une étoile au dépôt** sur GitHub ! Cela augmente la visibilité et aide d'autres utilisateurs à découvrir LibreFolio.

[:octicons-star-fill-24: Mettre une étoile sur GitHub](https://github.com/Librefolio/LibreFolio){ .md-button .md-button--primary }

---

## :globe_with_meridians: Et après — LibreFolio Cloud

Pour ceux qui souhaitent utiliser LibreFolio mais n'ont pas le temps, les compétences ou l'infrastructure pour l'auto-héberger, nous prévoyons une **plateforme hébergée** — **LibreFolio Cloud**. Elle offrira toutes les mêmes fonctionnalités puissantes sans aucune configuration technique, ainsi que des **analyses basées sur l'IA** à venir pour vous aider à prendre des décisions d'investissement plus intelligentes.

Pour soutenir l'infrastructure, la maintenance et le développement continu, la plateforme cloud sera proposée sous forme de **service d'abonnement** — le tarif sera déterminé ultérieurement.

---

!!! tip "Thank you!"

    Toute forme de soutien — code, idées, rapports de bugs ou dons — est profondément appréciée. Ensemble, nous pouvons construire le meilleur tracker de portefeuille auto-hébergé ! :rocket:
