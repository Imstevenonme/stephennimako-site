# Stephen Nimako Jr — Career Site

Source for [stephennimako.com](https://stephennimako.com), Stephen Nimako Jr's
personal career / portfolio site: IT infrastructure & support engineering,
experience, skills, certifications, education, and the Dojo build log.

## Layout

- `index.html` — the v1 page (self-contained markup, CSS, and render script).
  It fetches `content.json` on load and renders all editable copy from it.
- `content.json` — every editable word on the page. See `SCHEMA.md` for the
  full schema, text conventions, and escaping rules.
- `SCHEMA.md` — the `content.json` schema and what stays hard-coded in the page.
- `resume.pdf` — the master résumé, linked from the hero's "View Résumé"
  button (first CTA) and served alongside the page.
- `profile.jpg` — hero portrait (round; tap/click opens an enlarged round
  preview).
- `admin/app.py` — the private, LAN/Tailscale-only Flask admin portal that
  edits `content.json` on the origin host and keeps timestamped backups.

## Hosting

Self-hosted on a Debian 12 LXC (`portfolio`) on Stephen's own Proxmox host.
Caddy serves `/var/www/portfolio/` and a Cloudflare Tunnel publishes it as
https://stephennimako.com — no inbound ports are open on the router.

## Editing content

Edit `content.json` (directly, or via the admin portal on the origin) — never
hard-code copy into `index.html`. Keep `SCHEMA.md` in sync when the schema or
page behavior changes.
