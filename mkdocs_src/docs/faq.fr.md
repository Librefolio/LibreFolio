# ❓ Foire Aux Questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous trouverez ici les réponses aux questions les plus courantes.

## 💬 Questions Générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un outil de suivi de portefeuille open-source qui vous offre une vue complète et privée de tous vos investissements. De puissants outils d'analyse donnent vie à vos données — pour que vous puissiez prendre des décisions éclairées en toute confiance et en tout contrôle.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open-source sous la [licence AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Vous pouvez l'installer sur votre propre serveur et tout gérer vous-même sans aucun coût.

!!! info "Bientôt disponible : plateforme en ligne ☁️"

    Nous travaillons sur une plateforme en ligne pour ceux qui n'ont pas le temps, l'intérêt ou les compétences techniques pour auto-héberger LibreFolio. La version hébergée offrira toutes les fonctionnalités sans aucune configuration, avec des mises à jour automatiques et un support dédié — disponible par abonnement.

### 🤖 Des fonctionnalités IA sont-elles prévues ?

Oui ! Notre feuille de route inclut des **assistants basés sur l'intelligence artificielle** pour vous aider à analyser votre portefeuille, repérer les tendances et prendre des décisions plus éclairées.

- **Auto-hébergé** : vous pouvez connecter vos propres modèles IA et tout gérer de manière autonome
- **Plateforme en ligne** : les assistants IA seront entièrement intégrés — prêts à l'emploi sans aucune configuration, avec un support premium

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions & ETF** — Prix récupérés automatiquement via des fournisseurs de données (ex: yfinance)
- **Cryptomonnaies** — Bientôt disponible
- **Obligations** — Saisie manuelle prise en charge
- **Prêts P2P** — Actifs à rendement programmé
- **Espèces & Dépôts** — Suivez votre liquidité

!!! tip "Il manque quelque chose ? 💡"

    Si vous souhaitez voir une classe d'actifs ou une fonctionnalité à laquelle nous n'avons pas encore pensé, nous serions ravis de recevoir vos suggestions ! Ouvrez une [demande de fonctionnalité sur GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) et faites-le nous savoir.

## 🚀 Prise en main

### 📦 Comment installer LibreFolio ?

Consultez notre [Guide d'Installation](developer/dev-installation.md) pour des instructions détaillées.

### 👤 Comment créer un compte ?

1. Accédez à la page de connexion
2. Cliquez sur "S'inscrire"
3. Remplissez vos informations
4. Votre compte est prêt à l'emploi !

### 🔑 J'ai oublié mon mot de passe, que faire ?

Actuellement, la réinitialisation du mot de passe s'effectue via CLI. Contactez l'administrateur de votre instance ou exécutez :

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Dépannage

### 📉 Les prix de mes actifs ne se mettent pas à jour

Vérifiez que :

1. La synchronisation automatique est activée dans les Paramètres globaux
2. Vos actifs possèdent des ISIN ou des symboles valides reconnus par le **fournisseur de données** configuré (ex: [yfinance](https://pypi.org/project/yfinance/) pour les actions et ETF)
3. Le service du fournisseur est disponible (vérifiez les journaux du serveur pour détecter d'éventuelles erreurs)

### 💱 Mes taux de change ne se mettent pas à jour

Vérifiez que :

1. La paire de devises possède au moins un [fournisseur de données configuré](user/fx/detail/provider.md)
2. L'API du fournisseur est joignable (ECB, FED, BOE, SNB)
3. Vous avez lancé une [synchronisation](user/fx/sync.md) pour la plage de dates souhaitée
4. Vérifiez la [chaîne d'approvisionnement du fournisseur](user/fx/detail/provider.md) pour les options de fallback

### 🔐 Je ne peux pas me connecter

- Vérifiez votre nom d'utilisateur et votre mot de passe
- Vérifiez si votre compte est activé
- Effacez les cookies du navigateur et réessayez

## 🆘 Besoin de plus d'aide ?

- [Documentation Complète](index.md)
- [Signaler un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Alfystar/LibreFolio/discussions)
