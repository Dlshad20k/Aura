#!/usr/bin/env python3
“””
AURA PLAY – User Setup Script
Erstellt: Dlo, Nazo, Wooqq, Shezo, Alle (jeder mit eigenem Ordner)
Netflix-Style Auswahl Seite
Ausführen: python3 setup_users.py
“””

import os, json, shutil

BASE       = os.path.dirname(os.path.abspath(**file**))
MUSIC_DIR  = os.path.join(BASE, “music”)
TEMPLATES  = os.path.join(BASE, “templates”)
SERVER     = os.path.join(BASE, “server.py”)

# ─── 5 User definieren ────────────────────────────────

USERS = [
{“id”: “dlo”,   “name”: “Dlo”,   “emoji”: “🎧”, “color”: “#1DB954”},
{“id”: “nazo”,  “name”: “Nazo”,  “emoji”: “🎵”, “color”: “#E91E63”},
{“id”: “wooqq”, “name”: “Wooqq”, “emoji”: “🔥”, “color”: “#FF9800”},
{“id”: “shezo”, “name”: “Shezo”, “emoji”: “💫”, “color”: “#9C27B0”},
{“id”: “alle”,  “name”: “Alle”,  “emoji”: “🌍”, “color”: “#00BCD4”},
]

# ─── 1. Ordner für jeden User anlegen ─────────────────

print(“📁 Erstelle User-Ordner …”)
for u in USERS:
folder = os.path.join(MUSIC_DIR, u[“id”])
os.makedirs(folder, exist_ok=True)
print(f”  ✓ /music/{u[‘id’]}/ → {u[‘name’]}”)

# ─── 2. users.json initialisieren ─────────────────────

users_json = os.path.join(BASE, “users.json”)
if os.path.exists(users_json):
with open(users_json) as f:
try:
existing = json.load(f)
except:
existing = {}
else:
existing = {}

for u in USERS:
if u[“id”] not in existing:
existing[u[“id”]] = {
“id”:    u[“id”],
“name”:  u[“name”],
“emoji”: u[“emoji”],
“color”: u[“color”]
}

with open(users_json, “w”) as f:
json.dump(existing, f, indent=2)
print(f”\n✅ users.json gespeichert ({len(existing)} User)\n”)

# ─── 3. songs.json + favorites.json User-Slots anlegen ──

for fname in [“songs.json”, “favorites.json”]:
fpath = os.path.join(BASE, fname)
if os.path.exists(fpath):
with open(fpath) as f:
try:
data = json.load(f)
except:
data = {}
else:
data = {}

```
for u in USERS:
    if u["id"] not in data:
        data[u["id"]] = {}

with open(fpath, "w") as f:
    json.dump(data, f, indent=2)
print(f"✓ {fname} – User-Slots angelegt")
```

# ─── 4. Schöne Netflix-Style select_user.html ────────────

print(”\n🎨 Erstelle select_user.html …”)

users_js = json.dumps(USERS)

HTML = f”””<!DOCTYPE html>

<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AURA PLAY – Wer schaut?</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
–bg: #0a0a0f;
–glass: rgba(255,255,255,0.06);
–glass-border: rgba(255,255,255,0.12);
–text: #f0f0f0;
–muted: #888;
}}

html, body {{
height: 100%;
font-family: ‘Outfit’, sans-serif;
background: var(–bg);
color: var(–text);
overflow-x: hidden;
}}

/* Animated background */
body::before {{
content: ‘’;
position: fixed; inset: 0; z-index: 0;
background:
radial-gradient(ellipse 80% 60% at 20% 20%, rgba(29,185,84,0.12) 0%, transparent 60%),
radial-gradient(ellipse 60% 50% at 80% 80%, rgba(233,30,99,0.10) 0%, transparent 60%),
radial-gradient(ellipse 50% 40% at 50% 50%, rgba(156,39,176,0.07) 0%, transparent 60%);
animation: bgPulse 8s ease-in-out infinite alternate;
}}

@keyframes bgPulse {{
0%   {{ opacity: 0.8; transform: scale(1); }}
100% {{ opacity: 1;   transform: scale(1.05); }}
}}

.container {{
position: relative; z-index: 1;
display: flex; flex-direction: column;
align-items: center; justify-content: center;
min-height: 100vh;
padding: 40px 20px;
gap: 50px;
}}

/* Logo */
.logo {{
display: flex; align-items: center; gap: 12px;
animation: fadeDown 0.6s ease both;
}}
.logo-icon {{
width: 44px; height: 44px;
background: linear-gradient(135deg, #1DB954, #1ed760);
border-radius: 12px;
display: flex; align-items: center; justify-content: center;
font-size: 22px;
box-shadow: 0 4px 20px rgba(29,185,84,0.4);
}}
.logo-text {{
font-size: 26px; font-weight: 900;
letter-spacing: -0.5px;
}}
.logo-text span {{ color: #1DB954; }}

/* Heading */
h1 {{
font-size: clamp(22px, 5vw, 36px);
font-weight: 800;
letter-spacing: -0.5px;
color: var(–text);
animation: fadeDown 0.6s 0.1s ease both;
text-align: center;
}}

/* User Grid */
.user-grid {{
display: flex;
flex-wrap: wrap;
justify-content: center;
gap: 20px;
max-width: 680px;
animation: fadeUp 0.6s 0.2s ease both;
}}

.user-card {{
display: flex; flex-direction: column;
align-items: center; gap: 14px;
padding: 28px 22px;
width: 120px;
background: var(–glass);
border: 1px solid var(–glass-border);
border-radius: 20px;
cursor: pointer;
transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease;
backdrop-filter: blur(12px);
-webkit-backdrop-filter: blur(12px);
position: relative;
overflow: hidden;
}}

.user-card::before {{
content: ‘’;
position: absolute; inset: 0;
background: linear-gradient(135deg, var(–accent, #1DB954) 0%, transparent 70%);
opacity: 0;
transition: opacity 0.3s ease;
border-radius: inherit;
}}

.user-card:hover {{
transform: translateY(-10px) scale(1.03);
border-color: var(–accent, #1DB954);
box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px var(–accent, #1DB954);
}}
.user-card:hover::before {{ opacity: 0.08; }}

.user-card:active {{ transform: translateY(-5px) scale(1.01); }}

.avatar {{
width: 72px; height: 72px;
border-radius: 50%;
display: flex; align-items: center; justify-content: center;
font-size: 32px;
border: 3px solid var(–accent, #1DB954);
box-shadow: 0 0 20px rgba(0,0,0,0.4),
0 0 0 1px rgba(255,255,255,0.05);
background: rgba(0,0,0,0.4);
position: relative; z-index: 1;
transition: box-shadow 0.25s ease, transform 0.25s ease;
}}
.user-card:hover .avatar {{
box-shadow: 0 0 30px var(–accent, #1DB954),
0 0 0 1px rgba(255,255,255,0.1);
transform: scale(1.08);
}}

.user-name {{
font-size: 15px; font-weight: 700;
color: var(–text);
letter-spacing: 0.3px;
position: relative; z-index: 1;
}}

/* Active glow ring animation on hover */
.user-card:hover .avatar::after {{
content: ‘’;
position: absolute; inset: -6px;
border-radius: 50%;
border: 2px solid var(–accent, #1DB954);
opacity: 0.4;
animation: ping 1s ease infinite;
}}
@keyframes ping {{
0%   {{ transform: scale(1);    opacity: 0.4; }}
100% {{ transform: scale(1.4);  opacity: 0; }}
}}

/* Animations */
@keyframes fadeDown {{
from {{ opacity: 0; transform: translateY(-20px); }}
to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeUp {{
from {{ opacity: 0; transform: translateY(20px); }}
to   {{ opacity: 1; transform: translateY(0); }}
}}

/* Each card staggered */
.user-card:nth-child(1) {{ animation: fadeUp 0.5s 0.25s ease both; }}
.user-card:nth-child(2) {{ animation: fadeUp 0.5s 0.35s ease both; }}
.user-card:nth-child(3) {{ animation: fadeUp 0.5s 0.45s ease both; }}
.user-card:nth-child(4) {{ animation: fadeUp 0.5s 0.55s ease both; }}
.user-card:nth-child(5) {{ animation: fadeUp 0.5s 0.65s ease both; }}

/* Footer */
.footer {{
font-size: 12px; color: var(–muted);
animation: fadeUp 0.6s 0.7s ease both;
}}

@media (max-width: 480px) {{
.user-grid {{ gap: 14px; }}
.user-card {{ width: 100px; padding: 22px 14px; }}
.avatar {{ width: 60px; height: 60px; font-size: 26px; }}
}}
</style>

</head>
<body>
<div class="container">

  <div class="logo">
    <div class="logo-icon">🎵</div>
    <div class="logo-text">AURA <span>PLAY</span></div>
  </div>

  <h1>Wer hört Musik?</h1>

  <div class="user-grid" id="userGrid"></div>

  <p class="footer">Wähle dein Profil um zu starten</p>
</div>

<script>
const USERS = {users_js};

function render() {{
  const grid = document.getElementById('userGrid');
  grid.innerHTML = USERS.map(u => `
    <div class="user-card" style="--accent: ${{u.color}}" onclick="selectUser('${{u.id}}')">
      <div class="avatar">${{u.emoji}}</div>
      <div class="user-name">${{u.name}}</div>
    </div>
  `).join('');
}}

function selectUser(userId) {{
  document.cookie = `auraUserId=${{userId}}; path=/; max-age=31536000`;
  // Fade out animation
  document.querySelector('.container').style.transition = 'opacity 0.3s ease';
  document.querySelector('.container').style.opacity = '0';
  setTimeout(() => window.location.href = '/', 300);
}}

render();
</script>

</body>
</html>
"""

select_path = os.path.join(TEMPLATES, “select_user.html”)
with open(select_path, “w”) as f:
f.write(HTML)
print(f”  ✅ select_user.html erstellt\n”)

# ─── 5. server.py – /api/users Route sicherstellen ────

print(“🔧 Prüfe server.py …”)
with open(SERVER) as f:
srv = f.read()

USER_ROUTE = “””
@app.route(’/api/users’)
def api_get_users():
return jsonify({‘users’: list(users_db.values())})

@app.route(’/api/users/add’, methods=[‘POST’])
def api_add_user():
data    = request.json
user_id = data.get(‘id’, ‘’).strip().lower()
name    = data.get(‘name’, user_id)
if not user_id or user_id in users_db:
return jsonify({‘success’: False, ‘error’: ‘Existiert bereits’}), 400
users_db[user_id] = {‘id’: user_id, ‘name’: name, ‘emoji’: ‘🎵’, ‘color’: ‘#1DB954’}
songs_db[user_id]     = {}
favorites_db[user_id] = {}
import os as _os
_os.makedirs(_os.path.join(MUSIC_DIR, user_id), exist_ok=True)
save_db()
return jsonify({‘success’: True})
“””

if “api_get_users” not in srv:
# Vor erster @app.route einfügen
srv = srv.replace(”@app.route(’/’)”, USER_ROUTE + “\n@app.route(’/’)”, 1)
with open(SERVER, “w”) as f:
f.write(srv)
print(”  ✓ /api/users Route hinzugefügt”)
else:
print(”  · /api/users bereits vorhanden”)

# ─── 6. users_db mit Users vorbeladen ─────────────────

print(”\n🔄 Lade users_db mit den 5 Usern vor …”)
with open(SERVER) as f:
srv = f.read()

PRELOAD = “””

# Pre-load fixed users

_fixed_users = “”” + repr({u[“id”]: u for u in USERS}) + “””
for _uid, _udata in _fixed_users.items():
if _uid not in users_db:
users_db[_uid] = _udata
songs_db.setdefault(_uid, {})
favorites_db.setdefault(_uid, {})
import os as _os2
_os2.makedirs(os.path.join(MUSIC_DIR, _uid), exist_ok=True)
save_db()
del _fixed_users, _uid, _udata
“””

if “_fixed_users” not in srv:
# Nach save_db() laden – vor dem ersten @app.route
srv = srv.replace(”@app.route(’/’)”, PRELOAD + “\n@app.route(’/’)”, 1)
with open(SERVER, “w”) as f:
f.write(srv)
print(”  ✓ User-Preload in server.py eingefügt”)
else:
print(”  · User-Preload bereits vorhanden”)

# ─── Fertig ───────────────────────────────────────────

print(”\n” + “=”*50)
print(“✅ USER SETUP ABGESCHLOSSEN!”)
print(”=”*50)
print()
print(“👥 User & Ordner:”)
for u in USERS:
folder = os.path.join(MUSIC_DIR, u[“id”])
print(f”  {u[‘emoji’]} {u[‘name’]:8s} → music/{u[‘id’]}/”)
print()
print(“Jetzt starten:”)
print(”  source venv/bin/activate”)
print(”  python3 server.py”)
print()
print(“Dann öffnen:”)
print(”  http://192.168.2.142:5000”)
print()
print(“Du siehst zuerst: ‘Wer hört Musik?’ → User wählen → App!”)
