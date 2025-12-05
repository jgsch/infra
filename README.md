
## Installation

### Prérequis

- Docker + Docker Compose
- `just`

### Setup


`just setup`

Vous devriez maintenant avoir un fichier `.env` à la racine du repo qui ressemble à ceci :
```
VAULTWARDEN_ADMIN_TOKEN=<PASSWORD>
VAULTWARDEN_DOMAIN=https://vault.oblo.ch
VAULTWARDEN_INFOMANIAK_SSO_AUTHORITY=https://login.infomaniak.com
VAULTWARDEN_INFOMANIAK_SSO_CLIENT_ID=
VAULTWARDEN_INFOMANIAK_SSO_CLIENT_SECRET=

POSTGRES_USER=postgres
POSTGRES_PASSWORD=<PASSWORD>

OUTLINE_SECRET_KEY=<PASSWORD>
OUTLINE_UTILS_SECRET=<PASSWORD>
OUTLINE_URL=https://kb.oblo.ch
OUTLINE_DB_NAME=outline
OUTLINE_DB_USERNAME=outline
OUTLINE_DB_PASSWORD=<PASSWORD>
OUTLINE_INFOMANIAK_OIDC_ISSUER_URL=https://login.infomaniak.com
OUTLINE_INFOMANIAK_OIDC_CLIENT_ID=
OUTLINE_INFOMANIAK_OIDC_CLIENT_SECRET=

UMAMI_ADMIN_PASSWORD=<PASSWORD>
UMAMI_DB_NAME=umami
UMAMI_DB_USERNAME=umami
UMAMI_DB_PASSWORD=

BOT_TELEGRAM_TOKEN=
BOT_TELEGRAM_HOST=http://bot:8001
BOT_TELEGRAM_GROUP_ID=

WEBSITE_ADMIN_SECRET_KEY=<PASSWORD>
WEBSITE_INFOMANIAK_SSO_CLIENT_ID=
WEBSITE_INFOMANIAK_SSO_CLIENT_SECRET=
WEBSITE_INFOMANIAK_SSO_REDIRECT_URI=https://oblo.ch/login/infomaniak/callback

DEBUG=False
```

### Variables à renseigner

Il faut remplacer :
- `VAULTWARDEN_INFOMANIAK_SSO_CLIENT_ID`
- `VAULTWARDEN_INFOMANIAK_SSO_CLIENT_SECRET`
- `WEBSITE_INFOMANIAK_SSO_CLIENT_ID`
- `WEBSITE_INFOMANIAK_SSO_CLIENT_SECRET`
- `OUTLINE_INFOMANIAK_OIDC_CLIENT_ID`
- `OUTLINE_INFOMANIAK_OIDC_CLIENT_SECRET`

Ces valeurs sont disponibles après avoir créé une application Auth dans le Manager Infomaniak.

Il faut également renseigner :
- `BOT_TELEGRAM_TOKEN`
- `BOT_TELEGRAM_GROUP_ID` (ID du groupe Telegram requis pour le bot).

> Remarque : les URLs ci-dessus sont données pour le domaine `oblo.ch`. Si vous voulez utiliser un autre domaine, adapte `VAULTWARDEN_DOMAIN`, `OUTLINE_URL` et les reverse proxies.


### Démarrage des services

Une fois les valeurs ajoutées au `.env`, lance tous les services :
```
docker compose up -d
```

Vérifier les logs :
```
docker compose logs -f
```

### Post-install des services

#### Vaultwarden (manageur de mot de passe)

Dans `Admin Console`, puis `Master password requirements` :
- Cliquer sur `Turn on`
- Selectioner `Good(3)` dans `Minimum complexity`
- Cliquer sur `A-Z`, `a-z`, `0-9`, `!@#$%^&*` 

#### Outline (base de connaissance)

Preferences:
- Language: `Français`

Sécurité:
- Autoriser les utilisateurs à envoyer des invitations: Déactiver
- Rôle par défaut: `Lecteur`
- Domaines autorisées: `oblo.ch`

#### Umami (analytics du site)

La première connection se fait avec :
- username: `admin`
- password: `umami`

Changer le mot de passe dans `Profile` (en haut à droite) puis `Change password`

Une fois connecter pour ajouter le site web cliquer sur `Add website` puis dans rentrer les valeurs suivantes:
- Name: `oblo.ch`
- Domain: `oblo.ch`

### Ajouter un utilisateur

Les utilisateurs dont l’adresse mail se termine par : `@oblo.ch` peuvent s’inscrire eux-mêmes sur Vaultwarden et sur Outline via SSO Infomaniak.
