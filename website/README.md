

```bash
sudo timedatectl set-timezone Europe/Paris
```


input.css
```
@import "tailwindcss";

```

```
npx @tailwindcss/cli -i ./input.css -o ./assets/css/tailwind.css --minify
```


### Add an user

```bash
docker exec oblo-website python3 scripts/user.py add <USERNAME>
```

### Remove an user

```bash
docker exec oblo-website python3 scripts/user.py delete <USERNAME>
```
