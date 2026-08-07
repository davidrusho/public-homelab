# public-homelab

A public reference repository of Docker Compose configurations from my personal homelab.
These are real, working stacks - sanitized of personal identifiers so you can use them as a starting point for your own setup.

Blog: [thehomelab.lol](https://thehomelab.lol)

---

## What This Repo Is

Every stack in this repo reflects how I actually run it - real service combinations, real network wiring, real resource limits. Nothing is a toy example. PII (IPs, domains, usernames, passwords, paths) has been replaced with clearly labeled placeholders so you know exactly what to substitute.

This repo is **reference material**, not a deployment tool. There are no CI/CD pipelines, no GitHub Actions, and no automation of any kind. Clone it, read it, adapt it.

---

## Repo Structure

```
public-homelab/
├── containers/       # Docker Compose stacks, one folder per logical service
├── print-files/      # STL files from 3D printing projects
└── scripts/          # Python and shell scripts
```

---

## How to Use the Container Configs

Each folder under `containers/` contains two files:

| File | Purpose |
|---|---|
| `compose.yaml` | Docker Compose configuration with comments explaining non-obvious decisions |
| `.env.example` | All required secrets listed as placeholders with explanations |

**To use a stack:**

1. Copy the folder to your machine
2. Copy `.env.example` to `.env`
3. Fill in every value in `.env` (never commit this file)
4. Run `docker compose up -d`

Some stacks combine multiple services into one folder (e.g. an application and its database). This is intentional - it shows exactly how they are wired together.

---

## Placeholder Conventions

| Placeholder | Replace with |
|---|---|
| `yourdomain.com` | Your domain name |
| `service.yourdomain.com` | Your subdomain for that service |
| `192.168.x.x` | Your host's local IP address |
| `/mnt/nas-media` | Your NAS or storage mount path for media |
| `/mnt/nas-config` | Your NAS or storage mount path for container config data |
| `/opt/stacks/service/config` | Your preferred host path for container config |
| `America/Your_Timezone` | Your timezone (see [TZ database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) |
| `your-username` | Your username (for PUID/PGID references) |

---

## My Setup

These configs run on a homelab with:

- **Container host:** Ubuntu Server VM on Proxmox (dedicated Docker host)
- **Storage:** QNAP NAS via NFS for media and persistent config volumes
- **Reverse proxy / tunnels:** Caddy + Dockflare (Cloudflare tunnels)
- **VPN:** Gluetun (PIA) for download containers

Your setup will differ - the comments in each compose file explain decisions that may need to change based on your environment.

---

## Blog Posts Using This Repo

Posts that reference specific stacks are linked here as they are published.

| Post | Stack |
|---|---|
| [My $130/Year Evernote Replacement: Paperless-ngx + GitOps](https://thehomelab.lol/articles/paperless-ngx-evernote-replacement/) | [`containers/paperless-ngx`](containers/paperless-ngx) |
| [Using a Local LLM to Auto-File Documents](https://thehomelab.lol/articles/paperless-ai-pipeline/) | [`containers/paperless-ngx`](containers/paperless-ngx) |
| [Give Claude Code CLI a Status HUD (claude-hud)](https://thehomelab.lol/articles/claude-code-statusline-hud/) | [`scripts/claude-hud-statusline-wrapper`](scripts/claude-hud-statusline-wrapper) |

---

## Notes

- Configs reflect my setup at the time of last commit. Image versions may have advanced.
- I update this repo when publishing a related blog post or after a significant config change.
- If something looks wrong or outdated, feel free to open an issue.
