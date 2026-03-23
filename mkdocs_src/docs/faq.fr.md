# ❓ Foire aux questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous y trouverez des réponses aux questions courantes.

## 💬 Questions générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un tracker de portefeuille auto-hébergé et open source, conçu pour les investisseurs soucieux de leur vie privée. Il vous permet de suivre vos investissements, d'analyser leurs performances et de conserver le contrôle total de vos données financières.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open source sous licence [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html).

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions et ETF** - Prix automatiquement récupérés via yfinance
- **Cryptomonnaies** - Bientôt disponibles
- **Obligations** - Saisie manuelle prise en charge
- **Prêts P2P** - Actifs à rendement périodique
- **Espèces et Dépôts** — Suivi des liquidités

!!! tip "Il manque quelque chose ? 💡"

    Si vous souhaitez un type d'actif ou une fonctionnalité que nous n'avons pas encore envisagé, faites-le nous savoir ! Ouvrez une [demande d'amélioration sur GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement).

## 🚀 Démarrer

### 📦 Comment installer LibreFolio ?

Consultez notre [Guide d'installation](developer/dev-installation.md) pour des instructions détaillées.

### 👤 Comment créer un compte ?

1. Accédez à la page de connexion
2. Cliquez sur "S'inscrire"
3. Remplissez vos informations
4. Votre compte est prêt à l'emploi !

### 🔑 J'ai oublié mon mot de passe, que faire ?

Actuellement, la réinitialisation du mot de passe se fait via CLI. Contactez l'administrateur de votre instance ou exécutez :

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Dépannage

### 📉 Les prix de mes actifs ne se mettent pas à jour

Vérifiez que :

1. La synchronisation automatique est activée dans les Paramètres globaux
2. Vos actifs possèdent des ISIN ou symboles valides reconnus par le **fournisseur de données** configuré (ex. [yfinance](https://pypi.org/project/yfinance/) pour les actions et ETF)
3. Le service du fournisseur est disponible (consultez les journaux du serveur)

### 💱 Mes taux de change ne se mettent pas à jour

Vérifiez que :

1. La paire de devises a au moins un [fournisseur de données configuré](user/fx/detail/provider.md)
2. L'API du fournisseur est accessible (BCE, Fed, BOE, BNS)
3. Vous avez exécuté une [synchronisation](user/fx/sync.md) pour la plage de dates souhaitée

### 🔐 Je ne peux pas me connecter

- Vérifiez votre nom d'utilisateur et mot de passe
- Vérifiez si votre compte est activé
- Effacez les cookies du navigateur et réessayez

## 🆘 Besoin de plus d'aide ?

- [Documentation complète](index.md)
- [Signaler un bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Alfystar/LibreFolio/discussions)
