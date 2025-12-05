setup:
  #!/usr/bin/env bash

  if [[ -f ".env" ]]; then
    echo "❎ .env already exit"
    exit
  fi

  cat > ".env" <<EOF
  VAULTWARDEN_ADMIN_TOKEN=$(openssl rand -hex 32)
  VAULTWARDEN_DOMAIN=https://vault.oblo.ch
  VAULTWARDEN_INFOMANIAK_SSO_AUTHORITY=https://login.infomaniak.com
  VAULTWARDEN_INFOMANIAK_SSO_CLIENT_ID=
  VAULTWARDEN_INFOMANIAK_SSO_CLIENT_SECRET=
 
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=$(openssl rand -hex 32)
 
  OUTLINE_SECRET_KEY=$(openssl rand -hex 32)
  OUTLINE_UTILS_SECRET=$(openssl rand -hex 32)
  OUTLINE_URL=https://kb.oblo.ch
  OUTLINE_DB_NAME=outline
  OUTLINE_DB_USERNAME=outline
  OUTLINE_DB_PASSWORD=$(openssl rand -hex 32)
  OUTLINE_INFOMANIAK_OIDC_ISSUER_URL=https://login.infomaniak.com
  OUTLINE_INFOMANIAK_OIDC_CLIENT_ID=
  OUTLINE_INFOMANIAK_OIDC_CLIENT_SECRET=
 
  UMAMI_ADMIN_PASSWORD=$(openssl rand -hex 32)
  UMAMI_DB_NAME=umami
  UMAMI_DB_USERNAME=umami
  UMAMI_DB_PASSWORD=
 
  BOT_TELEGRAM_TOKEN=
  BOT_TELEGRAM_HOST=http://bot:8001
  BOT_TELEGRAM_GROUP_ID=
 
  WEBSITE_ADMIN_SECRET_KEY=$(openssl rand -hex 32)
  WEBSITE_INFOMANIAK_SSO_CLIENT_ID=
  WEBSITE_INFOMANIAK_SSO_CLIENT_SECRET=
  WEBSITE_INFOMANIAK_SSO_REDIRECT_URI=https://oblo.ch/login/infomaniak/callback
 
  DEBUG=False
  EOF

  echo "✅ .env généré"

clean:
  sudo rm -rf postgres/data/* redis/data/* 
