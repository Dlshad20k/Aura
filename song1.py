#!/usr/bin/env python3
"""
AURA PLAY – Auto Installer
Einfach ausführen: python3 install_aura.py
Erstellt ALLE Dateien automatisch!
"""

import os, json, sys

BASE = "/home/dlohoro/spotify_clone"
TMPL = os.path.join(BASE, "templates")

os.makedirs(BASE, exist_ok=True)
os.makedirs(TMPL, exist_ok=True)
os.makedirs(os.path.join(BASE, "music"), exist_ok=True)
for uid in ["dlo","nazo","wooqq","shezo","alle"]:
    os.makedirs(os.path.join(BASE, "music", uid), exist_ok=True)

print("📁 Ordner erstellt")

# ══════════════════════════════════════════════
# server.py
# ══════════════════════════════════════════════
SERVER_PY = '''import os
import json
import socket
import subprocess
import threading
import uuid
import time
from flask import Flask, request, jsonify, send_from_directory, send_file, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "music")
TMPL_DIR  = os.path.join(BASE_DIR, "templates")
os.makedirs(MUSIC_DIR, exist_ok=True)

SONGS_FILE     = os.path.join(BASE_DIR, "songs.json")
FAVORITES_FILE = os.path.join(BASE_DIR, "favorites.json")
USERS_FILE     = os.path.join(BASE_DIR, "users.json")

FIXED_USERS = [
    {"id":"dlo",   "name":"Dlo",   "emoji":"🎧","color":"#1DB954"},
    {"id":"nazo",  "name":"Nazo",  "emoji":"🎵","color":"#E91E63"},
    {"id":"wooqq", "name":"Wooqq", "emoji":"🔥","color":"#FF9800"},
    {"id":"shezo", "name":"Shezo", "emoji":"💫","color":"#9C27B0"},
    {"id":"alle",  "name":"Alle",  "emoji":"🌍","color":"#00BCD4"},
]

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_all():
    global songs_db, favorites_db, users_db
    songs_db     = load_json(SONGS_FILE,     {})
    favorites_db = load_json(FAVORITES_FILE, {})
    users_db     = load_json(USERS_FILE,     {})
    changed = False
    for u in FIXED_USERS:
        uid = u["id"]
        if uid not in users_db:
            users_db[uid] = u
            changed = True
        songs_db.setdefault(uid, {})
        favorites_db.setdefault(uid, {})
        os.makedirs(os.path.join(MUSIC_DIR, uid), exist_ok=True)
    if changed:
        save_all()

def save_all():
    save_json(SONGS_FILE,     songs_db)
    save_json(FAVORITES_FILE, favorites_db)
    save_json(USERS_FILE,     users_db)

load_all()

# ── Async Download ─────────────────────────────
download_jobs = {}
dl_queue      = []
dl_lock       = threading.Lock()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def download_worker():
    while True:
        job = None
        with dl_lock:
            if dl_queue:
                job = dl_queue.pop(0)
        if job is None:
            time.sleep(0.5)
            continue
        job_id   = job["job_id"]
        uid      = job["user_id"]
        song_id  = job["song_id"]
        title    = job["title"]
        uploader = job.get("uploader", "")
        query    = f"{title} {uploader}".strip()
        download_jobs[job_id] = {"state":"downloading","progress":5,"song_id":song_id,"error":None}
        try:
            user_dir  = os.path.join(MUSIC_DIR, uid)
            os.makedirs(user_dir, exist_ok=True)
            safe_name = "".join(c for c in title if c.isalnum() or c in " _-")[:60].strip()
            out_tmpl  = os.path.join(user_dir, safe_name + ".%(ext)s")
            cmd = ["yt-dlp", f"ytsearch1:{query}", "-x", "--audio-format","mp3",
                   "--audio-quality","0", "-o", out_tmpl, "--no-playlist","--no-warnings","-q"]
            download_jobs[job_id]["progress"] = 20
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            download_jobs[job_id]["progress"] = 80
            mp3_path = None
            for fname in sorted(os.listdir(user_dir), key=lambda x: os.path.getmtime(os.path.join(user_dir,x)), reverse=True):
                if fname.endswith(".mp3"):
                    mp3_path = fname
                    break
            if not mp3_path:
                raise RuntimeError("Datei nicht gefunden")
            songs_db.setdefault(uid, {})
            songs_db[uid][song_id] = {"id":song_id,"title":title,"uploader":uploader,"file":mp3_path,"is_favorite":False}
            save_all()
            download_jobs[job_id] = {"state":"done","progress":100,"song_id":song_id,"error":None}
        except Exception as e:
            download_jobs[job_id] = {"state":"error","progress":0,"song_id":song_id,"error":str(e)}

threading.Thread(target=download_worker, daemon=True).start()

def get_user_id():
    uid = request.cookies.get("auraUserId","").strip()
    if uid: return uid
    uid = request.headers.get("X-User-ID","").strip()
    if uid: return uid
    return "alle"

# ── Routes ─────────────────────────────────────
@app.route("/")
def index():
    uid = request.cookies.get("auraUserId","").strip()
    if uid and uid in users_db:
        return send_from_directory(TMPL_DIR, "index.html")
    return send_from_directory(TMPL_DIR, "select_user.html")

@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"Aura Play","short_name":"Aura","start_url":"/",
                    "display":"standalone","background_color":"#0a0a0f","theme_color":"#1DB954"})

@app.route("/sw.js")
def sw():
    try: return send_from_directory(BASE_DIR, "sw.js")
    except: return "// no sw", 200, {"Content-Type":"application/javascript"}

@app.route("/api/users")
def api_users():
    return jsonify({"users": list(users_db.values())})

@app.route("/api/search")
def api_search():
    q = request.args.get("q","").strip()
    if not q: return jsonify({"results":[]})
    try:
        cmd = ["yt-dlp", f"ytsearch10:{q}", "--dump-json","--flat-playlist","--no-warnings","-q"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        results = []
        for line in result.stdout.strip().split("\\n"):
            if not line.strip(): continue
            try:
                d = json.loads(line)
                thumb = d.get("thumbnail") or ""
                if not thumb and d.get("thumbnails"):
                    thumb = d["thumbnails"][0].get("url","")
                results.append({"id":d.get("id",str(uuid.uuid4())),"title":d.get("title","Unbekannt"),
                                 "uploader":d.get("uploader") or d.get("channel") or "",
                                 "duration":d.get("duration",0),"thumbnail":thumb})
            except: continue
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"results":[],"error":str(e)})

@app.route("/api/download", methods=["POST"])
def api_download():
    uid     = get_user_id()
    data    = request.json or {}
    song_id = data.get("id") or str(uuid.uuid4())
    title   = data.get("title","")
    uploader= data.get("uploader","")
    if uid in songs_db and song_id in songs_db[uid]:
        return jsonify({"success":True,"cached":True,"song_id":song_id})
    job_id = str(uuid.uuid4())
    with dl_lock:
        dl_queue.append({"job_id":job_id,"user_id":uid,"song_id":song_id,"title":title,"uploader":uploader})
    download_jobs[job_id] = {"state":"queued","progress":0,"song_id":song_id,"error":None}
    return jsonify({"success":True,"job_id":job_id,"song_id":song_id})

@app.route("/api/download/status/<job_id>")
def api_download_status(job_id):
    job = download_jobs.get(job_id)
    if not job: return jsonify({"state":"unknown"}), 404
    return jsonify(job)

@app.route("/api/play", methods=["POST"])
def api_play():
    uid     = get_user_id()
    data    = request.json or {}
    song_id = data.get("id","")
    user_songs = songs_db.get(uid, {})
    if song_id not in user_songs:
        return jsonify({"success":False,"error":"Nicht heruntergeladen"}), 404
    song     = user_songs[song_id]
    local_ip = get_local_ip()
    return jsonify({"success":True,"url":f"http://{local_ip}:5000/stream/{uid}/{song[\'file\']}","song":song})

@app.route("/stream/<user_id>/<filename>")
def stream(user_id, filename):
    filepath = os.path.join(MUSIC_DIR, user_id, filename)
    if not os.path.exists(filepath): return "Nicht gefunden", 404
    file_size    = os.path.getsize(filepath)
    range_header = request.headers.get("Range")
    if range_header:
        byte_start, byte_end = 0, file_size - 1
        match = range_header.replace("bytes=","").split("-")
        if match[0]: byte_start = int(match[0])
        if len(match) > 1 and match[1]: byte_end = int(match[1])
        length = byte_end - byte_start + 1
        def gen():
            with open(filepath,"rb") as f:
                f.seek(byte_start)
                rem = length
                while rem > 0:
                    chunk = f.read(min(8192, rem))
                    if not chunk: break
                    rem -= len(chunk)
                    yield chunk
        return Response(gen(), 206, headers={
            "Content-Range": f"bytes {byte_start}-{byte_end}/{file_size}",
            "Accept-Ranges":"bytes","Content-Length":str(length),"Content-Type":"audio/mpeg"})
    return send_file(filepath, mimetype="audio/mpeg", conditional=True)

@app.route("/api/library")
def api_library():
    uid = get_user_id()
    return jsonify({"songs": list(songs_db.get(uid,{}).values())})

@app.route("/api/library/remove", methods=["POST"])
def api_library_remove():
    uid     = get_user_id()
    data    = request.json or {}
    song_id = data.get("id","")
    user_songs = songs_db.get(uid, {})
    if song_id in user_songs:
        fpath = os.path.join(MUSIC_DIR, uid, user_songs[song_id].get("file",""))
        if os.path.exists(fpath): os.remove(fpath)
        del songs_db[uid][song_id]
        if uid in favorites_db and song_id in favorites_db[uid]:
            del favorites_db[uid][song_id]
        save_all()
    return jsonify({"success":True})

@app.route("/api/favorites")
def api_favorites():
    uid = get_user_id()
    return jsonify({"favorites": list(favorites_db.get(uid,{}).values())})

@app.route("/api/favorites/add", methods=["POST"])
def api_favorites_add():
    uid     = get_user_id()
    data    = request.json or {}
    song_id = data.get("id","")
    user_songs = songs_db.get(uid, {})
    if song_id not in user_songs:
        return jsonify({"success":False,"error":"Song nicht in Library"}), 400
    favorites_db.setdefault(uid, {})
    favorites_db[uid][song_id] = user_songs[song_id].copy()
    songs_db[uid][song_id]["is_favorite"] = True
    favorites_db[uid][song_id]["is_favorite"] = True
    save_all()
    return jsonify({"success":True})

@app.route("/api/favorites/remove", methods=["POST"])
def api_favorites_remove():
    uid     = get_user_id()
    data    = request.json or {}
    song_id = data.get("id","")
    if uid in favorites_db and song_id in favorites_db[uid]:
        del favorites_db[uid][song_id]
    if uid in songs_db and song_id in songs_db[uid]:
        songs_db[uid][song_id]["is_favorite"] = False
    save_all()
    return jsonify({"success":True})

if __name__ == "__main__":
    ip = get_local_ip()
    print(f"""
╔══════════════════════════════╗
║    🎵  AURA PLAY LÄUFT       ║
╠══════════════════════════════╣
║  Lokal:    http://127.0.0.1:5000
║  Netzwerk: http://{ip}:5000
╚══════════════════════════════╝
""")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
'''

# ══════════════════════════════════════════════
# select_user.html
# ══════════════════════════════════════════════
SELECT_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AURA PLAY</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--green:#1DB954;--bg:#0a0a0f;--card:rgba(255,255,255,0.06);--border:rgba(255,255,255,0.1);--text:#f0f0f0;--muted:#888}
html,body{height:100%;font-family:\'Outfit\',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden}
body::before{content:\'\';position:fixed;inset:0;z-index:0;
  background:radial-gradient(ellipse 80% 60% at 20% 20%,rgba(29,185,84,0.12) 0%,transparent 60%),
             radial-gradient(ellipse 60% 50% at 80% 80%,rgba(233,30,99,0.10) 0%,transparent 60%);
  animation:bgp 8s ease-in-out infinite alternate}
@keyframes bgp{0%{opacity:.8;transform:scale(1)}100%{opacity:1;transform:scale(1.05)}}
.wrap{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:40px 20px;gap:40px}
.logo{display:flex;align-items:center;gap:10px;font-size:28px;font-weight:900;letter-spacing:-1px;animation:fd .6s ease both}
.logo-icon{width:48px;height:48px;background:linear-gradient(135deg,#1DB954,#1ed760);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:24px;box-shadow:0 4px 20px rgba(29,185,84,.4)}
.logo span{color:var(--green)}
h1{font-size:clamp(20px,5vw,32px);font-weight:800;letter-spacing:-.5px;text-align:center;animation:fd .6s .1s ease both}
.grid{display:flex;flex-wrap:wrap;justify-content:center;gap:16px;max-width:640px;animation:fu .6s .2s ease both}
.card{display:flex;flex-direction:column;align-items:center;gap:12px;padding:26px 18px;width:116px;
  background:var(--card);border:1px solid var(--border);border-radius:18px;cursor:pointer;
  transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.card:hover{transform:translateY(-10px);border-color:var(--accent,var(--green));box-shadow:0 20px 50px rgba(0,0,0,.5),0 0 0 1px var(--accent,var(--green))}
.card:active{transform:translateY(-4px)}
.av{width:70px;height:70px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:30px;
  border:3px solid var(--accent,var(--green));background:rgba(0,0,0,.4);transition:box-shadow .25s ease,transform .25s}
.card:hover .av{box-shadow:0 0 28px var(--accent,var(--green));transform:scale(1.1)}
.name{font-size:15px;font-weight:700;color:var(--text)}
.card:nth-child(1){animation:fu .5s .25s ease both}
.card:nth-child(2){animation:fu .5s .35s ease both}
.card:nth-child(3){animation:fu .5s .45s ease both}
.card:nth-child(4){animation:fu .5s .55s ease both}
.card:nth-child(5){animation:fu .5s .65s ease both}
@keyframes fd{from{opacity:0;transform:translateY(-20px)}to{opacity:1;transform:translateY(0)}}
@keyframes fu{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.footer{font-size:12px;color:var(--muted);animation:fu .6s .7s ease both}
@media(max-width:480px){.card{width:96px;padding:20px 12px}.av{width:58px;height:58px;font-size:26px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo"><div class="logo-icon">🎵</div>AURA<span>PLAY</span></div>
  <h1>Wer hört Musik?</h1>
  <div class="grid" id="grid"></div>
  <p class="footer">Profil wählen um zu starten</p>
</div>
<script>
const USERS=[
  {id:"dlo",  name:"Dlo",  emoji:"🎧",color:"#1DB954"},
  {id:"nazo", name:"Nazo", emoji:"🎵",color:"#E91E63"},
  {id:"wooqq",name:"Wooqq",emoji:"🔥",color:"#FF9800"},
  {id:"shezo",name:"Shezo",emoji:"💫",color:"#9C27B0"},
  {id:"alle", name:"Alle", emoji:"🌍",color:"#00BCD4"},
];
document.getElementById("grid").innerHTML=USERS.map(u=>`
  <div class="card" style="--accent:${u.color}" onclick="pick('${u.id}')">
    <div class="av">${u.emoji}</div>
    <div class="name">${u.name}</div>
  </div>`).join("");
function pick(id){
  document.cookie=`auraUserId=${id};path=/;max-age=31536000`;
  document.querySelector(".wrap").style.cssText="transition:opacity .3s;opacity:0";
  setTimeout(()=>location.href="/",300);
}
</script>
</body>
</html>
'''

# ══════════════════════════════════════════════
# index.html  (vollständig)
# ══════════════════════════════════════════════
INDEX_HTML = open("/dev/stdin").read() if False else r'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Aura Play</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--green:#1DB954;--green2:#1ed760;--bg:#0a0a0f;--bg2:#111116;--card:rgba(255,255,255,.05);--card-h:rgba(255,255,255,.09);--border:rgba(255,255,255,.08);--text:#f0f0f0;--muted:#888;--r:14px}
html,body{height:100%;font-family:'Outfit',sans-serif;background:var(--bg);color:var(--text);overflow:hidden}
.app{display:flex;flex-direction:column;height:100vh;height:100dvh}
.header{padding:16px 16px 0;background:linear-gradient(180deg,rgba(29,185,84,.15) 0%,transparent 100%);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-bottom:1px solid var(--border);flex-shrink:0}
.header-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.logo{display:flex;align-items:center;gap:8px;font-size:20px;font-weight:900;letter-spacing:-.5px}
.logo-dot{color:var(--green)}
.user-btn{display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:20px;padding:6px 12px;cursor:pointer;font-family:inherit;font-size:13px;font-weight:600;color:var(--text);transition:background .2s}
.user-btn:hover{background:var(--card-h)}
.tabs{display:flex;gap:6px;padding-bottom:0}
.tab{padding:8px 16px;border-radius:20px;font-family:inherit;font-size:13px;font-weight:700;color:var(--muted);background:transparent;border:1px solid transparent;cursor:pointer;transition:all .2s}
.tab.active{background:var(--green);color:#000;border-color:var(--green);box-shadow:0 4px 15px rgba(29,185,84,.3)}
.content{flex:1;overflow-y:auto;padding:16px;padding-bottom:190px;-webkit-overflow-scrolling:touch}
.content::-webkit-scrollbar{display:none}
.search-wrap{margin-bottom:14px}
.search-box{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.08);border:1px solid var(--border);border-radius:12px;padding:12px 16px;backdrop-filter:blur(10px)}
.search-box input{flex:1;background:none;border:none;color:var(--text);font-family:inherit;font-size:15px;outline:none}
.search-box input::placeholder{color:var(--muted)}
.section-title{font-size:18px;font-weight:800;margin-bottom:12px;letter-spacing:-.3px}
.song-list{display:flex;flex-direction:column;gap:8px}
.song-item{display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);cursor:pointer;transition:background .2s,transform .15s;position:relative;overflow:hidden}
.song-item:hover{background:var(--card-h);transform:translateX(2px)}
.song-item.playing{border-color:var(--green);background:rgba(29,185,84,.08)}
.song-thumb{width:48px;height:48px;border-radius:10px;object-fit:cover;background:#222;flex-shrink:0}
.song-thumb-ph{width:48px;height:48px;border-radius:10px;background:linear-gradient(135deg,#1a1a2e,#16213e);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.song-info{flex:1;min-width:0}
.song-title{font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.song-artist{font-size:12px;color:var(--muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.song-actions{display:flex;gap:6px;align-items:center}
.btn-icon{width:34px;height:34px;border-radius:50%;border:none;background:rgba(255,255,255,.06);color:var(--text);font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .2s,transform .15s;flex-shrink:0}
.btn-icon:hover{background:rgba(255,255,255,.12);transform:scale(1.1)}
.btn-icon.fav-on{color:var(--green)}
.dl-bar{position:absolute;bottom:0;left:0;height:2px;background:linear-gradient(90deg,var(--green),var(--green2));width:0%;transition:width .5s ease;border-radius:0 2px 2px 0}
.player{position:fixed;bottom:0;left:0;right:0;background:rgba(10,10,15,.95);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);border-top:1px solid var(--border);padding:12px 16px;padding-bottom:max(12px,env(safe-area-inset-bottom));z-index:200}
.player-song{display:flex;align-items:center;gap:12px;margin-bottom:10px}
.player-thumb{width:42px;height:42px;border-radius:8px;background:#222;flex-shrink:0;font-size:18px;display:flex;align-items:center;justify-content:center}
.player-info{flex:1;min-width:0}
.player-title{font-size:14px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.player-artist{font-size:12px;color:var(--muted)}
.player-controls{display:flex;align-items:center;justify-content:center;gap:20px;margin-bottom:10px}
.ctrl-btn{background:none;border:none;color:var(--text);font-size:22px;cursor:pointer;padding:4px;transition:opacity .2s,transform .15s;display:flex;align-items:center}
.ctrl-btn:hover{opacity:.7;transform:scale(1.1)}
.play-btn{width:52px;height:52px;border-radius:50%;background:var(--green);color:#000;font-size:22px;display:flex;align-items:center;justify-content:center;cursor:pointer;border:none;transition:transform .15s,box-shadow .2s;box-shadow:0 4px 20px rgba(29,185,84,.4)}
.play-btn:hover{transform:scale(1.07)}
.progress-wrap{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted)}
.progress-bar{flex:1;height:4px;background:rgba(255,255,255,.12);border-radius:2px;cursor:pointer;position:relative}
.progress-fill{height:100%;border-radius:2px;background:var(--green);width:0%;pointer-events:none;transition:width .3s linear}
.empty{text-align:center;padding:60px 20px;color:var(--muted)}
.empty-icon{font-size:48px;margin-bottom:12px}
.empty h3{font-size:18px;font-weight:700;color:var(--text);margin-bottom:6px}
.toast{position:fixed;top:20px;left:50%;transform:translateX(-50%) translateY(-80px);background:rgba(20,20,30,.95);border:1px solid var(--border);border-radius:12px;padding:10px 20px;font-size:13px;font-weight:600;backdrop-filter:blur(20px);transition:transform .3s ease;z-index:999;white-space:nowrap}
.toast.show{transform:translateX(-50%) translateY(0)}
.toast.ok{border-color:var(--green);color:var(--green)}
.toast.err{border-color:#f44;color:#f44}
.spin{width:20px;height:20px;border:2px solid rgba(255,255,255,.1);border-top-color:var(--green);border-radius:50%;animation:sp .8s linear infinite;display:inline-block}
@keyframes sp{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="app">
  <div class="header">
    <div class="header-top">
      <div class="logo">🎵 Aura<span class="logo-dot">.</span></div>
      <button class="user-btn" onclick="switchUser()">
        <span id="uEmoji">🎵</span><span id="uName">...</span><span>⌄</span>
      </button>
    </div>
    <div class="tabs">
      <button class="tab active" onclick="showTab('search')">Suche</button>
      <button class="tab" onclick="showTab('library')">Bibliothek</button>
      <button class="tab" onclick="showTab('favorites')">Favoriten</button>
    </div>
  </div>
  <div class="content" id="content">
    <div id="tab-search">
      <div class="search-wrap">
        <div class="search-box">
          <span>🔍</span>
          <input id="searchInput" type="text" placeholder="Song oder Artist suchen..." autocomplete="off">
        </div>
      </div>
      <div id="searchResults"></div>
    </div>
    <div id="tab-library" style="display:none">
      <div class="section-title">Meine Songs</div>
      <div id="libraryList" class="song-list"></div>
    </div>
    <div id="tab-favorites" style="display:none">
      <div class="section-title">Favoriten</div>
      <div id="favoritesList" class="song-list"></div>
    </div>
  </div>
  <div class="player">
    <div class="player-song">
      <div class="player-thumb" id="pThumb">🎵</div>
      <div class="player-info">
        <div class="player-title" id="pTitle">Kein Song</div>
        <div class="player-artist" id="pArtist">Wähle einen Song aus</div>
      </div>
      <button class="btn-icon" id="pFavBtn" onclick="toggleCurFav()" style="font-size:20px">🤍</button>
    </div>
    <div class="player-controls">
      <button class="ctrl-btn" onclick="playPrev()">⏮</button>
      <button class="ctrl-btn" onclick="seekBack()">⏪</button>
      <button class="play-btn" id="playBtn" onclick="togglePlay()">▶</button>
      <button class="ctrl-btn" onclick="seekFwd()">⏩</button>
      <button class="ctrl-btn" onclick="playNext()">⏭</button>
    </div>
    <div class="progress-wrap">
      <span id="tNow">0:00</span>
      <div class="progress-bar" id="progBar" onclick="seekTo(event)">
        <div class="progress-fill" id="progFill"></div>
      </div>
      <span id="tTotal">0:00</span>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<audio id="audio"></audio>
<script>
const API=window.location.origin;
let userId=getCookie('auraUserId')||'alle';
let library={},favorites={},queue=[],qIdx=0,curSong=null,playing=false;
const audio=document.getElementById('audio');

function getCookie(n){const m=document.cookie.split('; ').find(r=>r.startsWith(n+'='));return m?decodeURIComponent(m.split('=')[1]):null}
async function api(ep,o={}){if(!o.headers)o.headers={};o.headers['X-User-ID']=userId;const r=await fetch(API+ep,o);return r.json()}
function toast(msg,t='ok'){const e=document.getElementById('toast');e.textContent=msg;e.className='toast '+t+' show';setTimeout(()=>e.className='toast',2500)}
function fmt(s){if(!s||isNaN(s))return'0:00';return`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`}

async function loadUserInfo(){
  try{const d=await api('/api/users');const u=d.users.find(x=>x.id===userId);
  if(u){document.getElementById('uEmoji').textContent=u.emoji||'🎵';document.getElementById('uName').textContent=u.name}}catch(e){}
}
function switchUser(){document.cookie='auraUserId=;path=/;max-age=0';location.href='/'}

function showTab(n){
  ['search','library','favorites'].forEach((t,i)=>{
    document.getElementById('tab-'+t).style.display=t===n?'':'none';
    document.querySelectorAll('.tab')[i].classList.toggle('active',t===n);
  });
  if(n==='library')loadLibrary();
  if(n==='favorites')loadFavorites();
}

function renderSong(s,inLib=false){
  const isFav=!!favorites[s.id];
  const isPlay=curSong&&curSong.id===s.id;
  const th=s.thumbnail?`<img class="song-thumb" src="${s.thumbnail}" loading="lazy" onerror="this.style.display='none'">`:`<div class="song-thumb-ph">🎵</div>`;
  const sd=JSON.stringify(s).replace(/"/g,'&quot;');
  const acts=inLib
    ?`<button class="btn-icon ${isFav?'fav-on':''}" onclick="toggleFav('${s.id}')">${isFav?'❤️':'🤍'}</button><button class="btn-icon" onclick="delSong('${s.id}')">🗑</button>`
    :`<button class="btn-icon" id="dlbtn-${s.id}" onclick="dlSong(${sd})">⬇</button>`;
  return`<div class="song-item ${isPlay?'playing':''}" id="song-${s.id}">${th}<div class="song-info" onclick="songClick(${sd})""><div class="song-title">${s.title}</div><div class="song-artist">${s.uploader||''}</div></div><div class="song-actions">${acts}</div><div class="dl-bar" id="dlbar-${s.id}"></div></div>`;
}

// Search
let sTimeout=null;
document.getElementById('searchInput').addEventListener('input',function(){
  clearTimeout(sTimeout);const q=this.value.trim();
  if(q.length<2){document.getElementById('searchResults').innerHTML='';return}
  sTimeout=setTimeout(()=>doSearch(q),600);
});

async function doSearch(q){
  const el=document.getElementById('searchResults');
  el.innerHTML='<div style="text-align:center;padding:30px"><div class="spin"></div></div>';
  try{
    const d=await api(`/api/search?q=${encodeURIComponent(q)}`);
    const r=d.results||[];
    if(!r.length){el.innerHTML='<div class="empty"><div class="empty-icon">🔍</div><h3>Nichts gefunden</h3></div>';return}
    el.innerHTML=`<div class="song-list">${r.map(s=>renderSong(s)).join('')}</div>`;
  }catch(e){el.innerHTML='<div class="empty"><div class="empty-icon">⚠️</div><h3>Suchfehler</h3></div>'}
}

// Download
async function dlSong(song){
  if(library[song.id]){toast('Schon geladen');playSong(song);return}
  const btn=document.getElementById('dlbtn-'+song.id);
  const bar=document.getElementById('dlbar-'+song.id);
  if(btn){btn.innerHTML='<div class="spin" style="width:16px;height:16px;border-width:2px"></div>';btn.disabled=true}
  try{
    const d=await api('/api/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:song.id,title:song.title,uploader:song.uploader})});
    if(!d.success){toast('Download Fehler','err');if(btn){btn.innerHTML='⬇';btn.disabled=false}return}
    if(d.cached){toast('Song geladen!');await loadLibrary();playSong(song);return}
    const poll=setInterval(async()=>{
      try{
        const st=await api('/api/download/status/'+d.job_id);
        if(bar)bar.style.width=(st.progress||10)+'%';
        if(st.state==='done'){
          clearInterval(poll);
          if(bar){bar.style.width='100%';setTimeout(()=>bar.style.width='0%',800)}
          if(btn)btn.innerHTML='✓';
          await loadLibrary();toast('✅ '+song.title);
          playSong({...song,id:st.song_id});
        }else if(st.state==='error'){
          clearInterval(poll);if(btn){btn.innerHTML='⬇';btn.disabled=false}
          if(bar)bar.style.width='0%';toast('Fehler: '+(st.error||'Unbekannt'),'err');
        }
      }catch(e){clearInterval(poll)}
    },1500);
  }catch(e){toast('Netzwerk Fehler','err');if(btn){btn.innerHTML='⬇';btn.disabled=false}}
}

function songClick(s){library[s.id]?playSong(s):dlSong(s)}

// Play
async function playSong(song){
  try{
    const d=await api('/api/play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:song.id})});
    if(!d.success){toast('Fehler: '+(d.error||''),'err');return}
    curSong={...song,...d.song};
    audio.src=d.url;audio.load();
    audio.play().then(()=>{playing=true;updatePlayer()}).catch(e=>toast('Audio: '+e.message,'err'));
    document.querySelectorAll('.song-item').forEach(e=>e.classList.remove('playing'));
    const el=document.getElementById('song-'+song.id);if(el)el.classList.add('playing');
  }catch(e){toast('Wiedergabe Fehler','err')}
}

function updatePlayer(){
  if(!curSong)return;
  document.getElementById('pTitle').textContent=curSong.title||'Kein Song';
  document.getElementById('pArtist').textContent=curSong.uploader||'';
  document.getElementById('pFavBtn').textContent=favorites[curSong.id]?'❤️':'🤍';
  document.getElementById('playBtn').textContent=playing?'⏸':'▶';
}

function togglePlay(){if(!curSong)return;if(playing){audio.pause();playing=false}else{audio.play();playing=true}document.getElementById('playBtn').textContent=playing?'⏸':'▶'}
function seekBack(){audio.currentTime=Math.max(0,audio.currentTime-10)}
function seekFwd(){audio.currentTime=Math.min(audio.duration||0,audio.currentTime+10)}
function seekTo(e){const b=document.getElementById('progBar');const r=b.getBoundingClientRect();if(audio.duration)audio.currentTime=((e.clientX-r.left)/r.width)*audio.duration}
audio.addEventListener('timeupdate',()=>{const p=audio.duration?(audio.currentTime/audio.duration)*100:0;document.getElementById('progFill').style.width=p+'%';document.getElementById('tNow').textContent=fmt(audio.currentTime);document.getElementById('tTotal').textContent=fmt(audio.duration)});
audio.addEventListener('ended',()=>playNext());
audio.addEventListener('pause',()=>{playing=false;document.getElementById('playBtn').textContent='▶'});
audio.addEventListener('play',()=>{playing=true;document.getElementById('playBtn').textContent='⏸'});
function playNext(){if(!queue.length)return;qIdx=(qIdx+1)%queue.length;playSong(queue[qIdx])}
function playPrev(){if(audio.currentTime>3){audio.currentTime=0;return}if(!queue.length)return;qIdx=(qIdx-1+queue.length)%queue.length;playSong(queue[qIdx])}

// Library
async function loadLibrary(){
  const d=await api('/api/library');
  library={};(d.songs||[]).forEach(s=>library[s.id]=s);
  queue=Object.values(library);
  const el=document.getElementById('libraryList');if(!el)return;
  if(!queue.length){el.innerHTML='<div class="empty"><div class="empty-icon">🎵</div><h3>Noch keine Songs</h3><p>Suche und lade Songs herunter</p></div>';return}
  el.innerHTML=queue.map(s=>renderSong(s,true)).join('');
}

async function delSong(id){
  if(!confirm('Song löschen?'))return;
  await api('/api/library/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  delete library[id];delete favorites[id];toast('Song gelöscht');
  loadLibrary();loadFavorites();
  if(curSong&&curSong.id===id){audio.pause();playing=false;curSong=null;document.getElementById('pTitle').textContent='Kein Song';document.getElementById('pArtist').textContent=''}
}

// Favorites
async function loadFavorites(){
  const d=await api('/api/favorites');
  favorites={};(d.favorites||[]).forEach(f=>favorites[f.id]=f);
  const el=document.getElementById('favoritesList');if(!el)return;
  const favs=Object.values(favorites);
  if(!favs.length){el.innerHTML='<div class="empty"><div class="empty-icon">❤️</div><h3>Keine Favoriten</h3></div>';return}
  el.innerHTML=favs.map(s=>renderSong(s,true)).join('');
}

async function toggleFav(id){
  const isFav=!!favorites[id];
  await api(`/api/favorites/${isFav?'remove':'add'}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  await loadFavorites();
  if(curSong&&curSong.id===id)document.getElementById('pFavBtn').textContent=isFav?'🤍':'❤️';
  if(document.getElementById('tab-library').style.display!=='none')loadLibrary();
  toast(isFav?'Aus Favoriten entfernt':'❤️ Zu Favoriten hinzugefügt');
}
async function toggleCurFav(){if(curSong)await toggleFav(curSong.id)}

async function init(){await loadUserInfo();await loadFavorites();await loadLibrary()}
init();
</script>
</body>
</html>
'''

# ══════════════════════════════════════════════
# Schreibe alle Dateien
# ══════════════════════════════════════════════
files = [
    (os.path.join(BASE, "server.py"),        SERVER_PY),
    (os.path.join(TMPL, "select_user.html"), SELECT_HTML),
    (os.path.join(TMPL, "index.html"),       INDEX_HTML),
]

# Backup
import shutil
bak = BASE + "_backup"
if os.path.exists(BASE) and not os.path.exists(bak):
    shutil.copytree(BASE, bak, ignore=shutil.ignore_patterns("venv","music","__pycache__"))
    print(f"📦 Backup → {bak}")

for path, content in files:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {path}")

# JSON Daten initialisieren
USERS_DATA = [
    {"id":"dlo",  "name":"Dlo",  "emoji":"🎧","color":"#1DB954"},
    {"id":"nazo", "name":"Nazo", "emoji":"🎵","color":"#E91E63"},
    {"id":"wooqq","name":"Wooqq","emoji":"🔥","color":"#FF9800"},
    {"id":"shezo","name":"Shezo","emoji":"💫","color":"#9C27B0"},
    {"id":"alle", "name":"Alle", "emoji":"🌍","color":"#00BCD4"},
]

for fname, default in [("users.json", {}), ("songs.json", {}), ("favorites.json", {})]:
    fpath = os.path.join(BASE, fname)
    try:
        with open(fpath) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except:
        data = {}

    if fname == "users.json":
        for u in USERS_DATA:
            data.setdefault(u["id"], u)
    else:
        for u in USERS_DATA:
            data.setdefault(u["id"], {})

    with open(fpath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ {fname}")

print("""
╔══════════════════════════════════╗
║  ✅  AURA PLAY INSTALLIERT!      ║
╠══════════════════════════════════╣
║  Jetzt starten:                  ║
║  cd ~/spotify_clone              ║
║  source venv/bin/activate        ║
║  python3 server.py               ║
╚══════════════════════════════════╝
""")
