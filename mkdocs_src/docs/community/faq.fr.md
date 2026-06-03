# ❓ Foire Aux Questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous trouverez ici les réponses aux questions les plus courantes.

## 💬 Questions Générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un outil de suivi de portefeuille open-source qui vous offre une vue complète et privée de tous vos investissements. De puissants outils d'analyse transforment vos données en informations exploitables — pour vous permettre de prendre des décisions éclairées avec une confiance totale et un contrôle complet.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open-source sous la [licence AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Vous pouvez l'installer sur votre propre serveur et tout gérer vous-même sans frais.

!!! info "Coming soon: hosted platform ☁️"

    Nous travaillons sur une plateforme en ligne pour ceux qui n'ont pas le temps, l'intérêt ou les compétences techniques pour l'auto-hébergement. La version hébergée offrira toutes les fonctionnalités sans configuration, avec des mises à jour automatiques et un support dédié — disponible via un abonnement payant.

### 🤖 Des fonctionnalités d'IA sont-elles prévues ?

Oui ! Notre feuille de route inclut des **assistants propulsés par l'IA** pour vous aider à analyser votre portefeuille, repérer les tendances et prendre des décisions mieux informées.

- **Auto-hébergé** : vous pouvez connecter vos propres modèles d'IA et tout gérer indépendamment
- **Plateforme hébergée** : les assistants IA seront pleinement intégrés — prêts à l'emploi sans configuration requise, avec un support premium

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions & ETF** — Prix récupérés automatiquement via des fournisseurs de données (ex: yfinance)
- **Cryptomonnaies** — Prochainement
- **Obligations** — Saisie manuelle prise en charge
- **Prêts P2P** — Actifs à investissement programmé
- **Espèces & Dépôts** — Suivez votre liquidité

!!! tip "Missing something? 💡"

    S'il y a une classe d'actifs ou une fonctionnalité que vous aimeriez voir et que nous n'avons pas encore envisagée, nous serions ravis de vous entendre ! Ouvrez une [demande de fonctionnalité sur GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) et faites-le nous savoir.

## 🚀 Prise en Main

### 📦 Comment installer LibreFolio ?

Consultez notre [Guide d'Installation](../developer/dev-installation.md) pour des instructions détaillées.

### 👤 Comment créer un compte ?

1. Accédez à la page de connexion
2. Cliquez sur "S'inscrire"
3. Saisissez vos informations
4. Votre compte est prêt à l'emploi !

### 🔑 J'ai oublié mon mot de passe, que faire ?

Actuellement, la réinitialisation du mot de passe se fait via la ligne de commande (CLI). Contactez l'administrateur de votre instance ou exécutez :

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Dépannage

### 📉 Les prix de mes actifs ne se mettent pas à jour

Vérifiez que :

1. La synchronisation automatique est activée dans les Paramètres Globaux
2. Vos actifs possèdent des ISIN ou des symboles valides reconnus par le **fournisseur de données** configuré (ex: [yfinance](https://pypi.org/project/yfinance/) pour les actions et ETF)
3. Le service du fournisseur est disponible (consultez les logs du serveur pour détecter des erreurs)

### 💱 Mes taux de change ne se mettent pas à jour

Vérifiez que :

1. La paire de devises possède au moins un [fournisseur de données configuré](../user/fx/detail/provider.md)
2. L'API du fournisseur est accessible (ECB, FED, BOE, SNB)
3. Vous avez lancé une [synchronisation](../user/fx/sync.md) pour la plage de dates souhaitée
4. Consultez la [chaîne d'approvisionnement du fournisseur](../user/fx/detail/provider.md) pour les options de fallback

### 🔐 Je ne peux pas me connecter

- Vérifiez votre nom d'utilisateur et votre mot de passe
- Vérifiez si votre compte est activé
- Effacez les cookies du navigateur et réessayez

### 📱 Puis-je utiliser LibreFolio comme une application mobile ?

Oui ! LibreFolio prend en charge l'installation en tant que **PWA (Progressive Web App)**. Vous pouvez l'ajouter à votre écran d'accueil sur Android, iOS ou bureau pour une expérience plein écran semblable à une application — sans avoir besoin de store d'applications.

Consultez le guide [Installer en tant qu'application (PWA)](../user/pwa.md) pour des instructions étape par étape.

## 🆘 Besoin d'aide supplémentaire ?

- [Documentation complète](../index.md)
- [Signaler un bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Alfystar/LibreFolio/discussions)
