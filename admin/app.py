#!/usr/bin/env python3
"""Portfolio admin portal — Tailscale/LAN-only content editor for stephennimako.com.

Edits /var/www/portfolio/content.json. Every save keeps a timestamped backup.
Only keys declared in SECTION_SPECS are modified; everything else in the JSON
is preserved untouched (merge semantics). Binds the LAN IP only.
"""
import datetime
import html as _html
import json
import os
import secrets
from functools import wraps

from flask import Flask, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("PORTFOLIO_ADMIN_CONFIG", os.path.join(BASE_DIR, "config.json"))
CONTENT_PATH = os.environ.get("PORTFOLIO_CONTENT", "/var/www/portfolio/content.json")
BACKUP_DIR = os.environ.get("PORTFOLIO_BACKUPS", "/var/www/portfolio/backups")
BIND_IP = os.environ.get("ADMIN_BIND_IP", "192.168.0.60")
PORT = int(os.environ.get("ADMIN_PORT", "8081"))

app = Flask(__name__)
with open(CONFIG_PATH) as f:
    _cfg = json.load(f)
app.secret_key = _cfg["secret_key"]
PASSWORD_HASH = _cfg["password_hash"]
USERNAME = _cfg.get("username", "stephen")

# ---------------------------------------------------------------- specs
# kind: text | textarea | lines | csv | bool | int | select | list | object

SECTION_SPECS = [
    ("hero", "Hero", "object", {
        "name": ("Name", "text", None),
        "role": ("Role line", "text", None),
        "roles": ("Typewriter rotator phrases (one per line)", "lines", None),
        "tagline": ("Tagline (**bold** supported)", "textarea", None),
        "intro": ("Intro (**bold** supported)", "textarea", None),
        "ctas": ("Buttons", "list", {
            "label": ("Label", "text", None),
            "href": ("Link URL", "text", None),
            "style": ("Style", "select", ["primary", "ghost"]),
            "icon": ("Icon", "select", ["", "linkedin", "github", "mail"]),
            "external": ("Open in new tab", "bool", None)}),
        "stats": ("Stats", "list", {
            "value": ("Value", "text", None),
            "suffix": ("Suffix (e.g. +)", "text", None),
            "label": ("Label", "text", None)}),
    }),
    ("about", "About", "object", {
        "heading": ("Heading", "text", None),
        "note": ("Small note label", "text", None),
        "paragraphs": ("Paragraphs (one per line, **bold** supported)", "lines", None),
        "facts": ("Quick-facts card", "object", {
            "title": ("Card title", "text", None),
            "rows": ("Rows", "list", {
                "label": ("Label", "text", None),
                "value": ("Value", "text", None)}),
        }),
    }),
    ("experience", "Experience", "list", {
        "company": ("Company", "text", None),
        "role": ("Role", "text", None),
        "period": ("Period", "text", None),
        "location": ("Location", "text", None),
        "current": ("Show 'Current' badge", "bool", None),
        "bullets": ("Bullets (one per line, **bold** supported)", "lines", None),
        "tags": ("Tags", "list", {
            "label": ("Label", "text", None),
            "hot": ("Gold highlight", "bool", None)}),
    }),
    ("skills", "Skills", "list", {
        "category": ("Card title", "text", None),
        "blurb": ("One-line description", "text", None),
        "group": ("Filter group key (e.g. cloud, network, endpoint, systems, lab)", "text", None),
        "icon": ("Icon", "select", ["cloud", "network", "endpoint", "systems", "lab", "work"]),
        "items": ("Skill pills", "list", {
            "label": ("Label", "text", None),
            "core": ("Gold 'daily driver' pill", "bool", None)}),
    }),
    ("certifications", "Certifications", "list", {
        "name": ("Name", "text", None),
        "issuer": ("Issuer", "text", None),
        "badge": ("Badge text", "text", None),
        "badgeAccent": ("Amber badge highlight", "bool", None),
        "description": ("Card paragraph", "textarea", None),
        "meta": ("Meta line (dates/status/verification, verbatim)", "text", None),
        "credentialId": ("Credential ID", "text", None),
    }),
    ("education", "Education", "object", {
        "school": ("School", "text", None),
        "degree": ("Degree", "text", None),
        "period": ("Period", "text", None),
        "mark": ("Card monogram", "text", None),
        "description": ("Card paragraph", "textarea", None),
        "details": ("Details (one per line)", "lines", None),
        "tags": ("Pills", "list", {
            "label": ("Label", "text", None),
            "hot": ("Gold highlight", "bool", None)}),
    }),
    ("dojo", "Build Log", "list", {
        "title": ("Title", "text", None),
        "date": ("Date", "text", None),
        "summary": ("Summary (**bold** supported)", "textarea", None),
        "tags": ("Tags (comma separated)", "csv", None),
        "link": ("Build-log link (optional)", "text", None),
    }),
    ("dojo_loop", "Dojo: Mastery Loop banner", "object", {
        "title": ("Title", "text", None),
        "text": ("Text", "textarea", None),
        "steps": ("Steps (one per line)", "lines", None),
    }),
    ("dojo_tracks", "Dojo: Track cards", "list", {
        "title": ("Title", "text", None),
        "status": ("Status text", "text", None),
        "statusClass": ("Status style", "select", ["now", "next"]),
        "description": ("Description", "textarea", None),
        "progress": ("Progress % (0-100)", "int", None),
    }),
    ("path", "Roadmap", "object", {
        "heading": ("Heading", "text", None),
        "note": ("Note label", "text", None),
        "intro": ("Intro", "textarea", None),
        "milestones": ("Milestones", "list", {
            "when": ("When", "text", None),
            "title": ("Title", "text", None),
            "description": ("Description", "textarea", None),
            "tags": ("Tags", "list", {
                "label": ("Label", "text", None),
                "hot": ("Gold highlight", "bool", None)}),
        }),
    }),
    ("contact", "Contact", "object", {
        "heading": ("Heading", "text", None),
        "subheading": ("Subheading", "text", None),
        "text": ("Text", "textarea", None),
        "email": ("Email", "text", None),
        "linkedin": ("LinkedIn URL", "text", None),
        "github": ("GitHub URL", "text", None),
    }),
]

SECTION_LABELS = {k: lbl for k, lbl, _, _ in SECTION_SPECS}

# ---------------------------------------------------------------- storage

def load_content():
    with open(CONTENT_PATH) as f:
        return json.load(f)


def save_content(data):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(CONTENT_PATH):
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(CONTENT_PATH) as f:
            old = f.read()
        with open(os.path.join(BACKUP_DIR, f"content-{ts}.json"), "w") as f:
            f.write(old)
        backs = sorted(os.listdir(BACKUP_DIR))
        for b in backs[:-30]:
            os.remove(os.path.join(BACKUP_DIR, b))
    tmp = CONTENT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, CONTENT_PATH)


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("authed"):
            return redirect(url_for("login", next=request.path))
        return fn(*a, **kw)
    return wrapper

# ---------------------------------------------------------------- rendering

CSS = """
:root{--bg:#0f1420;--card:#182030;--line:#2a3550;--txt:#e8ecf4;--mut:#9aa6bf;--acc:#4f8cff;--danger:#e05c5c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.55 -apple-system,'Segoe UI',Roboto,sans-serif}
.wrap{max-width:880px;margin:0 auto;padding:28px 18px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:24px 0 8px;color:#fff}
.sub{color:var(--mut);margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
.card.dashed{border-style:dashed}
label{display:block;font-size:13px;color:var(--mut);margin:12px 0 4px}
input[type=text],input[type=password],input[type=url],input[type=number],textarea,select{width:100%;background:#0c1120;border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:10px 12px;font:inherit}
textarea{min-height:80px;resize:vertical}
input[type=checkbox]{width:auto;transform:scale(1.3);margin-right:8px}
.checkline{display:flex;align-items:center;margin:12px 0 4px;font-size:14px}
.btn{display:inline-block;background:var(--acc);color:#fff;border:0;border-radius:8px;padding:11px 22px;font:inherit;font-weight:600;cursor:pointer;margin-top:16px;text-decoration:none}
.btn.ghost{background:transparent;border:1px solid var(--line);color:var(--txt)}
.btn.danger{background:var(--danger)}
.btn.small{padding:7px 14px;font-size:13px;margin-top:8px}
.row{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.topbar a{color:var(--mut);text-decoration:none;font-size:13px;margin-left:14px}
.topbar a:hover{color:#fff}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}
.flash{background:#3a2b12;border:1px solid #8a6d2f;color:#ffd98a;padding:10px 14px;border-radius:8px;margin:12px 0}
.okmsg{background:#123626;border:1px solid #2c7a52;color:#8fe3b6;padding:10px 14px;border-radius:8px;margin:12px 0}
.count{color:var(--mut);font-size:13px}
a{color:var(--acc)}
.login-card{max-width:380px;margin:12vh auto}
.nest{margin-left:14px;border-left:2px solid var(--line);padding-left:14px}
"""

CHROME = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Admin — {title}</title><style>{css}</style></head>
<body><div class="wrap">
<div class="topbar"><div><strong>Portfolio Admin</strong> <span class="count">stephennimako.com</span></div>
<div><a href="{dash}">Dashboard</a><a href="{logout}">Log out</a></div></div>
{body}</div></body></html>"""


def page(title, body):
    return render_template_string(
        CHROME.format(title=_html.escape(title), css=CSS, body=body,
                      dash=url_for("dashboard"), logout=url_for("logout")))


def _esc(v):
    return _html.escape(v if isinstance(v, str) else "")


def render_field(fkey, fname, spec, value, prefix):
    """Render one field. spec = (label, kind, options)."""
    label, kind, opts = spec
    name = f"{prefix}__{fkey}"
    if kind == "text":
        return f'<label>{label}</label><input type="text" name="{name}" value="{_esc(value)}">'
    if kind == "textarea":
        return f'<label>{label}</label><textarea name="{name}">{_esc(value)}</textarea>'
    if kind == "lines":
        v = "\n".join(value) if isinstance(value, list) else (value or "")
        return f'<label>{label}</label><textarea name="{name}">{_esc(v)}</textarea>'
    if kind == "csv":
        v = ", ".join(value) if isinstance(value, list) else (value or "")
        return f'<label>{label}</label><input type="text" name="{name}" value="{_esc(v)}">'
    if kind == "bool":
        chk = " checked" if value else ""
        return (f'<div class="checkline"><input type="checkbox" name="{name}" value="1"{chk}>'
                f'<span>{label}</span></div>')
    if kind == "int":
        return f'<label>{label}</label><input type="number" name="{name}" value="{_esc(str(value or ""))}">'
    if kind == "select":
        o = "".join(f'<option value="{_esc(x)}"{(" selected" if x == value else "")}>{_esc(x or "(none)")}</option>'
                    for x in opts)
        return f'<label>{label}</label><select name="{name}">{o}</select>'
    return ""


def render_object(fields_spec, data, prefix, depth=0):
    parts = []
    for fkey, spec in fields_spec.items():
        label, kind, opts = spec
        val = data.get(fkey)
        if kind == "list":
            parts.append(render_list(fkey, label, opts, val or [], f"{prefix}__{fkey}", depth))
        elif kind == "object":
            parts.append(f'<div class="card"><strong>{label}</strong><div class="nest">'
                         + render_object(opts, val or {}, f"{prefix}__{fkey}", depth + 1)
                         + '</div></div>')
        else:
            parts.append(render_field(fkey, label, spec, val, prefix))
    return "\n".join(parts)


def render_list(fkey, label, item_spec, items, prefix, depth=0):
    parts = [f'<h2>{label}</h2>']
    for i, it in enumerate(items):
        inner = render_object(item_spec, it, f"{prefix}__{i}", depth + 1)
        parts.append(
            f'<div class="card"><div class="row" style="border:0;padding:0 0 6px">'
            f'<strong>#{i + 1}</strong>'
            f'<button class="btn small danger" type="submit" name="__delete" value="{prefix}__{i}" '
            f'formnovalidate onclick="return confirm(\'Delete this entry?\')">Delete</button></div>'
            f'<div class="nest">{inner}</div></div>')
    parts.append(f'<div class="card dashed"><strong>New entry</strong><div class="nest">'
                 + render_object(item_spec, {}, f"{prefix}__{len(items)}", depth + 1)
                 + '</div></div>')
    parts.append(f'<input type="hidden" name="__count_{prefix}" value="{len(items)}">')
    return "\n".join(parts)


def parse_field(spec, form, name):
    label, kind, opts = spec
    if kind == "bool":
        return name in form
    raw = form.get(name, "")
    if kind == "lines":
        return [l.strip() for l in raw.splitlines() if l.strip()]
    if kind == "csv":
        return [x.strip() for x in raw.split(",") if x.strip()]
    if kind == "int":
        try:
            return int(raw)
        except ValueError:
            return 0
    return raw.strip()


def parse_object(fields_spec, form, prefix, data):
    """Merge form values into data (preserves undeclared keys)."""
    for fkey, spec in fields_spec.items():
        label, kind, opts = spec
        name = f"{prefix}__{fkey}"
        if kind == "list":
            data[fkey] = parse_list(opts, form, name, data.get(fkey) or [])
        elif kind == "object":
            sub = data.get(fkey)
            if not isinstance(sub, dict):
                sub = {}
            parse_object(opts, form, name, sub)
            data[fkey] = sub
        else:
            data[fkey] = parse_field(spec, form, name)
    return data


def parse_list(item_spec, form, prefix, existing):
    count = int(form.get(f"__count_{prefix}", len(existing)))
    items = []
    for i in range(count + 1):  # +1 = the blank "new entry" row
        base = dict(existing[i]) if i < len(existing) and isinstance(existing[i], dict) else {}
        entry = parse_object(item_spec, form, f"{prefix}__{i}", base)
        # drop if effectively empty (no text/true values)
        if any(v not in (None, "", [], {}, False, 0) for v in entry.values()):
            items.append(entry)
    return items


def delete_by_path(data, top_spec, target):
    """Delete list item at path like 'experience__2' or 'experience__0__tags__1'."""
    parts = target.split("__")
    node, spec = data, top_spec
    i = 0
    while i < len(parts):
        fkey = parts[i]
        fspec = spec.get(fkey)
        if fspec is None:
            return False
        kind = fspec[1]
        if kind == "list":
            idx = int(parts[i + 1])
            if i + 2 == len(parts):
                lst = node.get(fkey, [])
                if 0 <= idx < len(lst):
                    del lst[idx]
                    return True
                return False
            node = node[fkey][idx]
            spec = fspec[2]
            i += 2
        elif kind == "object":
            node = node.setdefault(fkey, {})
            spec = fspec[2]
            i += 1
        else:
            return False
    return False

# ---------------------------------------------------------------- routes

@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if secrets.compare_digest(u, USERNAME) and check_password_hash(PASSWORD_HASH, p):
            session["authed"] = True
            return redirect(request.args.get("next") or url_for("dashboard"))
        err = '<div class="flash">Wrong username or password.</div>'
    body = (f'<div class="login-card"><div class="card"><h1>Sign in</h1>'
            f'<p class="sub">Portfolio content admin</p>{err}'
            '<form method="post"><label>Username</label>'
            '<input type="text" name="username" autocomplete="username">'
            '<label>Password</label>'
            '<input type="password" name="password" autocomplete="current-password">'
            '<button class="btn" type="submit">Sign in</button></form></div></div>')
    return render_template_string(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Sign in — Portfolio Admin</title><style>{CSS}</style></head>"
        f"<body><div class='wrap'>{body}</div></body></html>")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    try:
        c = load_content()
    except Exception as e:
        return page("Dashboard", f'<div class="flash">Could not read content.json: {_html.escape(str(e))}</div>')
    rows = []
    for key, label, kind, _ in SECTION_SPECS:
        v = c.get(key)
        n = len(v) if isinstance(v, list) else (1 if v else 0)
        unit = "entries" if kind == "list" else "block"
        rows.append(
            f'<div class="row"><div><strong>{label}</strong>'
            f'<div class="count">{n} {unit}</div></div>'
            f'<a class="btn small ghost" href="{url_for("edit_section", name=key)}">Edit</a></div>')
    # section headers chrome
    rows.append(
        f'<div class="row"><div><strong>Section headers</strong>'
        f'<div class="count">Per-section titles, notes, intro text</div></div>'
        f'<a class="btn small ghost" href="{url_for("edit_headers")}">Edit</a></div>')
    return page("Dashboard",
                "<h1>Content</h1><p class='sub'>Every save backs up the previous "
                "content.json automatically.</p><div class='card'>" + "".join(rows) + "</div>")


@app.route("/edit/<name>", methods=["GET", "POST"])
@login_required
def edit_section(name):
    spec = next(((k, lbl, kind, f) for k, lbl, kind, f in SECTION_SPECS if k == name), None)
    if not spec:
        return page("Not found", "<p>Unknown section.</p>"), 404
    key, label, kind, fields = spec
    c = load_content()
    saved = request.args.get("saved")
    if request.method == "POST":
        if request.form.get("__delete"):
            if delete_by_path(c, {key: (label, kind, fields)}, request.form["__delete"]):
                save_content(c)
            return redirect(url_for("edit_section", name=name, saved=1))
        if kind == "list":
            c[key] = parse_list(fields, request.form, key, c.get(key) or [])
        else:
            node = c.get(key)
            if not isinstance(node, dict):
                node = {}
            c[key] = parse_object(fields, request.form, key, node)
        save_content(c)
        return redirect(url_for("edit_section", name=name, saved=1))
    msg = '<div class="okmsg">Saved &amp; published.</div>' if saved else ""
    if kind == "list":
        form_html = render_list(key, "Entries", fields, c.get(key) or [], key)
    else:
        form_html = render_object(fields, c.get(key) or {}, key)
    return page(label, f"<h1>{label}</h1>{msg}<form method='post'>{form_html}"
                       "<button class='btn' type='submit'>Save &amp; Publish</button> "
                       f"<a class='btn ghost' href='{url_for('dashboard')}'>Back</a></form>")


@app.route("/edit-headers", methods=["GET", "POST"])
@login_required
def edit_headers():
    c = load_content()
    saved = request.args.get("saved")
    secs = c.get("sections", {})
    order = ["about", "experience", "skills", "certifications", "education",
             "dojo", "path", "contact"]
    if request.method == "POST":
        for sid in order:
            s = secs.get(sid, {})
            s["heading"] = request.form.get(f"h_{sid}_heading", "").strip()
            s["note"] = request.form.get(f"h_{sid}_note", "").strip()
            s["sub"] = request.form.get(f"h_{sid}_sub", "").strip()
            secs[sid] = s
        c["sections"] = secs
        save_content(c)
        return redirect(url_for("edit_headers", saved=1))
    msg = '<div class="okmsg">Saved &amp; published.</div>' if saved else ""
    parts = [f"<h1>Section headers</h1>{msg}<form method='post'>"]
    for sid in order:
        s = secs.get(sid, {})
        parts.append(f'<div class="card"><strong>{sid}</strong>'
                     f'<label>Heading (h2)</label><input type="text" name="h_{sid}_heading" value="{_esc(s.get("heading"))}">'
                     f'<label>Note (small label)</label><input type="text" name="h_{sid}_note" value="{_esc(s.get("note"))}">'
                     f'<label>Sub (intro paragraph)</label><textarea name="h_{sid}_sub">{_esc(s.get("sub"))}</textarea></div>')
    parts.append("<button class='btn' type='submit'>Save &amp; Publish</button></form>")
    return page("Section headers", "".join(parts))


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(host=BIND_IP, port=PORT, threaded=True)
