# containers/

Each subfolder is a self-contained Docker Compose stack.

## Folder Conventions

```
containers/
└── service-name/
    ├── compose.yaml      # Docker Compose configuration
    └── .env.example      # Required secrets as placeholders
```

Services that must run together (application + database, or application + sidecar) are combined into one folder. This reflects how they actually run and shows the network and dependency wiring between them.

## Using a Stack

1. Copy the folder to your machine
2. `cp .env.example .env`
3. Fill in every value in `.env`
4. `docker compose up -d`

Never commit your `.env` file. It contains real secrets.

## Networks

Some stacks join a shared external network (e.g. a reverse proxy network). When a compose file declares `external: true` on a network, create it first:

```bash
docker network create proxy-network
```

The comment on the network declaration will tell you which other stacks also use it.

## Stacks

| Folder | Services | Category |
|---|---|---|
| `arr-stack/` | Prowlarr, Sonarr (1080p), Sonarr (Anime), Radarr, Bazarr | Media |
| `audiobookshelf/` | Audiobookshelf | Media |
| `caddy/` | Caddy | Infrastructure |
| `discoflix/` | Discoflix | Media |
| `dockflare/` | Dockflare | Infrastructure |
| `dozzle/` | Dozzle | Infrastructure |
| `flaresolverr/` | FlareSolverr | Media |
| `frigate/` | Frigate, Frigate-Periphery | Home Automation |
| `gluetun-downloads/` | Gluetun, qBittorrent, SearXNG, Redis | Media |
| `home-automation/` | Home Assistant, Mosquitto, Zigbee2MQTT, Govee2MQTT | Home Automation |
| `homepage/` | Homepage | Infrastructure |
| `jellyfin/` | Jellyfin | Media |
| `jdownloader2/` | JDownloader2 | Media |
| `karakeep/` | Karakeep, Meilisearch | Productivity |
| `kavita/` | Kavita | Media |
| `mealie/` | Mealie, PostgreSQL | Productivity |
| `paperless-ngx/` | Paperless-ngx, PostgreSQL, Redis | Productivity |
| `plex/` | Plex | Media |
| `spoolman/` | Spoolman, Spoolmansync | 3D Printing |
| `tailscale/` | Tailscale | Infrastructure |
| `uptime-kuma/` | Uptime Kuma | Infrastructure |
| `vikunja/` | Vikunja, PostgreSQL | Productivity |
| `ytptube/` | YTPTube | Media |
| `zipline/` | Zipline, PostgreSQL | Productivity |
