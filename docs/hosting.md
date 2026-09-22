# Hosting DanceSync

How to run DanceSync on a server so you and your friends can use it from anywhere. It assumes the Docker setup from the README (`docker compose up`) and the passphrase from `DANCESYNC_PASSPHRASE`.

## The target, and why

**A small Linux VPS with Docker, with [Caddy](https://caddyserver.com) in front for HTTPS.**

- **Size:** 2 vCPU, 4 GB RAM, and 40 GB or more of disk. Hetzner's CX22 or a DigitalOcean/Linode 2 GB–4 GB droplet are both fine.
  - Renders are CPU-bound, and more cores make them faster.
  - The matcher needs about 1 GB of RAM while it works.
  - Disk goes to uploads and renders.
- **Why a VPS:** friends get a normal `https://` link that works on their phones, with nothing to install. A home machine needs port forwarding or a tunnel. The tunnels that are easy to set up don't work here:
  - Cloudflare Tunnel cuts requests off at 100 s.
  - ngrok's free tier has a bandwidth cap.
- **Why Caddy:** it gets and renews the TLS certificate by itself, with a three-line config. nginx works too, and there's a config for it [below](#nginx-instead-of-caddy).

**The alternative:** a home machine reached over [Tailscale](https://tailscale.com). It's free and nothing is exposed to the internet, but every friend has to install Tailscale and join your tailnet. Choose it if the group is small and technical. The Docker steps below are the same; skip the Caddy and DNS steps, and open `http://<machine-name>:8000` over the tailnet. Still set a passphrase.

## Step by step

### 1. Server and DNS

1. Create the VPS with Ubuntu 24.04 and your SSH key.
2. Point a DNS `A` record, for example `dance.example.com`, at its IP address.
3. Install Docker, which includes the compose plugin:

   ```bash
   curl -fsSL https://get.docker.com | sh
   ```

### 2. DanceSync

```bash
git clone https://github.com/Sonikyu/DanceSync.git && cd DanceSync
cp .env.example .env
```

Edit `.env`:

```bash
DANCESYNC_PASSPHRASE=pick-something-long   # four random words is plenty
DANCESYNC_PORT=127.0.0.1:8000              # only Caddy can reach it; see below
```

`DANCESYNC_PORT=127.0.0.1:8000` matters. Docker's published ports bypass `ufw`, so a plain `8000` would put the app on the internet over unencrypted HTTP, next to Caddy. Binding to `127.0.0.1` keeps it reachable only from the machine itself.

```bash
docker compose up -d --build
docker compose logs | grep -E "ffmpeg|Sign-in"   # expect "Using /usr/bin/ffmpeg …" and "Sign-in required"
```

### 3. Caddy (HTTPS and the reverse proxy)

```bash
sudo apt install -y caddy
```

Replace `/etc/caddy/Caddyfile` with:

```
dance.example.com {
	request_body {
		max_size 600MB
	}
	reverse_proxy 127.0.0.1:8000 {
		transport http {
			response_header_timeout 600s
			read_timeout 600s
			write_timeout 600s
		}
	}
}
```

Then run `sudo systemctl reload caddy`. Open `https://dance.example.com`, sign in with the passphrase, and you're done.

- **`max_size 600MB`** covers the 500 MB clip limit plus the multipart overhead. If you change `DANCESYNC_MAX_CLIP_MB`, change this too.
- **The timeouts are 600 s.** See the next section for why.

## Timeouts: why 600 s

Uploads, alignment, and renders all happen inside a single HTTP request (there's no job queue yet; that's DS-13). The proxy has to wait for the longest one, and for renders that takes longer than the usual 60 s default.

Measured on a 4-core x86 machine, with a 3-minute 1080×1920 phone take at 0.75× against a 1080p reference video:

| Request | Time |
|---|---|
| Upload and align the take, the first take on a new song | 18.5 s |
| Upload and align the take, when the song's features are cached | 1.6 s |
| Render the take alone (`layout=take`) | 34 s |
| Render side by side (`layout=side-by-side`) | 53 s |

On a 2 vCPU VPS, expect roughly twice these times, so a side-by-side render of a 3-minute take takes about 2 minutes. 600 s covers a take up to about 10 minutes, or a slower CPU, with room to spare. If a render ever gets cut off, the browser shows "Couldn't make that video". Raise the timeout, or use a bigger box. The render isn't lost: the server finishes writing it, and the next request serves it from the cache.

Uploads of large videos over a slow connection also count against `read_timeout`. A 500 MB clip at 10 Mbit/s takes about 7 minutes, so 600 s is enough for that case too.

## Where the data lives, and backups

Docker keeps two named volumes, both under `/var/lib/docker/volumes/`:

| Volume | Holds | Back up? |
|---|---|---|
| `dancesync_data` | `media/references` and `media/clips` (the uploads), `catalog/` (metadata), `media/synced` (renders) | Yes, except `media/synced`, which can be re-rendered |
| `dancesync_cache` | decoded audio and song features | No. Delete it any time to free space |

Nightly backup, excluding the renders:

```bash
docker run --rm -v dancesync_data:/data:ro -v "$PWD":/backup alpine \
  tar czf /backup/dancesync-$(date +%F).tar.gz -C /data --exclude=./media/synced .
```

To restore it into a fresh volume:

```bash
docker compose down
docker run --rm -v dancesync_data:/data -v "$PWD":/backup alpine \
  sh -c "cd /data && tar xzf /backup/dancesync-YYYY-MM-DD.tar.gz && chown -R 1000 /data"
docker compose up -d
```

**Renders are never deleted yet** (that's DS-10). Check the disk now and then with `docker system df -v | grep dancesync`. You can safely empty the renders at any time:

```bash
docker compose exec dancesync sh -c 'rm -f /data/media/synced/*'
```

## Updating

```bash
cd DanceSync
git pull
docker compose up -d --build
```

The volumes carry over. Any render that's in progress when the container restarts is lost, and the next request starts it again.

To change the passphrase, edit `.env` and run `docker compose up -d`. This signs everyone out.

## nginx instead of Caddy

Get a certificate with `certbot --nginx`, then add this `location` block:

```nginx
client_max_body_size 600m;

location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
    proxy_request_buffering off;   # stream uploads straight to the app
}
```

`X-Forwarded-Proto` is what makes the sign-in cookie `Secure`. Caddy sends it by default.

## YouTube import from this host

Not tested yet. YouTube import (DS-30–32) isn't built, and it's deferred for now. Once it lands, try one import from the server before relying on it, because YouTube often blocks datacenter IP ranges. If the VPS gets blocked, the home-machine-over-Tailscale setup has a residential IP and usually isn't. Record the result here.
