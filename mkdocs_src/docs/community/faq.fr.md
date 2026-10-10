# ❓ Foire aux questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous trouverez ici les réponses aux questions courantes.

## 💬 Questions générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un suivi de portefeuille open-source qui vous offre une vue complète et privée de tous vos investissements. Des outils d'analyse puissants transforment vos données en informations exploitables — pour vous permettre de prendre des décisions éclairées en toute confiance et avec un contrôle total.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open-source sous [licence AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Vous pouvez l'installer sur votre propre serveur et tout gérer vous-même, sans frais.

!!! info "Bientôt disponible : plateforme hébergée ☁️"

    Nous travaillons sur une plateforme en ligne pour ceux qui n'ont ni le temps, ni l'envie, ni les compétences techniques pour l'auto-héberger. La version hébergée offrira toutes les fonctionnalités sans configuration, avec des mises à jour automatiques et un support dédié — disponible sous forme d'abonnement payant.

### 🤖 Puis-je utiliser LibreFolio avec un assistant IA ?

Oui. **[Export IA](../user/ai-export/index.md)** copie vos données sous forme de texte prêt à coller, avec une question ciblée si vous le souhaitez, afin que vous puissiez interroger l'assistant IA de votre choix au sujet de votre portefeuille, d'un courtier, d'un actif ou d'une paire de devises. LibreFolio lui-même ne contacte jamais de service d'IA.

Sur la future plateforme hébergée, les assistants IA seront entièrement intégrés : prêts à l'emploi sans configuration, avec un support premium.

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions, ETF et fonds** — cours récupérés automatiquement auprès de fournisseurs de données (par ex., yfinance)
- **Obligations** — cours provenant d'un fournisseur, ou saisis manuellement
- **Crypto-actifs** — suivis comme actifs de portefeuille, et non comme devises
- **Crowdfunding et prêts P2P** — valorisés avec un rendement planifié
- **Matières premières, immobilier**, et actifs sans prix de marché (art, objets de collection, actions non cotées)
- **Liquidités** — le solde de chaque courtier, dans chaque devise

La liste complète se trouve dans [Types d'actifs](../financial-theory/instruments/asset-types/index.md).

!!! tip "Il manque quelque chose ? 💡"

    Si vous souhaitez voir une classe d'actifs ou une fonctionnalité à laquelle nous n'avons pas encore pensé, nous serions ravis d'avoir votre retour ! Ouvrez une [demande de fonctionnalité sur GitHub](https://github.com/Librefolio/LibreFolio/issues/new?labels=enhancement) et dites-le-nous.

## 🚀 Pour commencer

### 📦 Comment installer LibreFolio ?

Suivez le [Guide d'installation Docker](../user/installation.md), la méthode recommandée, ou le [Guide d'installation sur l'hôte](../admin/host_installation.md) pour l'exécuter avec Pipenv.

### 👤 Comment créer un compte ?

1. Ouvrez la page de connexion.
2. Cliquez sur **S'inscrire ici**, à côté de *Vous n'avez pas de compte ?*
3. Remplissez vos informations : votre compte est prêt à l'emploi.

Sur une nouvelle instance, le premier compte créé devient l'administrateur. Ensuite, l'inscription ne fonctionne que tant que l'administrateur garde **Activer l'inscription** activé dans les [Paramètres globaux](../admin/settings.md) ; sinon, demandez-lui un compte.

### 🔑 J'ai oublié mon mot de passe, que faire ?

La récupération par e-mail n'est pas encore disponible : demandez à l'administrateur de votre instance, qui peut définir un nouveau mot de passe depuis la ligne de commande ([Réinitialiser un mot de passe](../admin/cli_tools.md#reset-a-password-or-lock-an-account)).

## 🔧 Dépannage

### 📉 Les cours de mes actifs ne se mettent pas à jour

Vérifiez que :

1. L'option **Planificateur activé** est activée dans les [Paramètres globaux](../admin/settings.md#market-data-scheduler) : c'est elle qui exécute les mises à jour automatiques
2. Vos actifs ont des codes ISIN ou des symboles valides reconnus par le **fournisseur de données** configuré (par ex., [yfinance](https://pypi.org/project/yfinance/) pour les actions et les ETF)
3. Le service du fournisseur est disponible (consultez les journaux du serveur pour les erreurs)

### 💱 Mes taux de change ne se mettent pas à jour

Vérifiez que :

1. L'option **Planificateur activé** est activée dans les [Paramètres globaux](../admin/settings.md#market-data-scheduler)
2. La paire de devises a au moins un [fournisseur de données configuré](../user/fx/detail/provider.md)
3. L'API du fournisseur est accessible (BCE, Fed, BoE, BNS)
4. Vous avez exécuté une [synchronisation](../user/fx/sync.md) pour la plage de dates souhaitée
5. Consultez la [chaîne de fournisseurs](../user/fx/detail/provider.md) pour les options de fallback

### 🔐 Je n'arrive pas à me connecter

- Vérifiez votre nom d'utilisateur et votre mot de passe
- Avec un mot de passe incorrect, vous obtenez toujours le même message *Nom d'utilisateur ou mot de passe incorrect*, que le compte existe ou non ; avec le bon mot de passe, un compte désactivé est signalé comme tel : demandez à votre administrateur de le réactiver
- Effacez les cookies du navigateur et réessayez

### 📱 Puis-je utiliser LibreFolio comme application mobile ?

Oui ! LibreFolio prend en charge l'installation en **PWA (Progressive Web App)**. Vous pouvez l'ajouter à votre écran d'accueil sur Android, iOS ou ordinateur pour une expérience plein écran, semblable à une application — sans passer par un magasin d'applications.

Consultez le guide [Installer comme application (PWA)](../user/pwa.md) pour des instructions étape par étape.

## 🆘 Besoin d'aide supplémentaire ?

- [Documentation complète](../index.md)
- [Signaler un bug](https://github.com/Librefolio/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Librefolio/LibreFolio/discussions)
