# Public website deployment

The tested deployment artifact is a static Next export, not the private Node Lab.
From the repository root in PowerShell:

```powershell
npm ci
npm run check:web
npm run build:web
npm run build:public
```

Deploy **only** `dist/public-web-source/out` after reviewing its contents. The build
copies an explicit allowlist of public pages and the text-only demo component. It
does not copy environment files, research assets, `api`, `lab`, `live`, `session`,
`metrics` or `review`. The script fails if excluded routes occur in the output.
Public pages need no backend URL, database, token, cloud GPU or runtime secret.

For a local preview:

```powershell
.\apps\perception-lab\.venv\Scripts\python.exe -m http.server 3011 --bind 127.0.0.1 --directory dist/public-web-source/out
```

Open `http://127.0.0.1:3011`. This Python server is a local preview, not production.
CI checks both full Next build and static export. A later manually approved static
hosting deployment should create a preview first; verify routes, asset MIME types,
HTTPS, 404 handling, cache headers and security headers before assigning a domain.
No hosting account, domain, credential or deployed public URL was created here.

The private Lab needs Node and authorized local filesystem assets. Run it locally:

```powershell
$env:VISION_LAB_SECRET = node -e "process.stdout.write(require('node:crypto').randomBytes(32).toString('hex'))"
$env:VISION_LAB_MEDIA_ENABLED = "0"
npm run dev:web
```

Open `/lab/login` on the displayed loopback address and enter the secret from your
own terminal environment. Never put it in `NEXT_PUBLIC_*`, a screenshot, source
control or a public hosting variable. Rotate it to invalidate existing cookies.
Enable raw media only after rights review; private replay metadata remains authenticated.
Public hosting cannot access the phone or Windows loopback inference gateway.
