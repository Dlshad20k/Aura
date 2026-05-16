import os,json,socket,subprocess,threading,uuid,time
from flask import Flask,request,jsonify,send_from_directory,send_file,Response,redirect,make_response
from flask_cors import CORS

app=Flask(__name__)
CORS(app)
app.secret_key='auraplay2025'

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR=os.path.join(BASE_DIR,"music")
TMPL_DIR=os.path.join(BASE_DIR,"templates")
os.makedirs(MUSIC_DIR,exist_ok=True)

PIN="1040"

FIXED_USERS=[
    {"id":"dlo",  "name":"Dlo",  "emoji":"🎧","color":"#1DB954"},
    {"id":"nazo", "name":"Nazo", "emoji":"🎵","color":"#E91E63"},
    {"id":"wooqq","name":"Wooqq","emoji":"🔥","color":"#FF9800"},
    {"id":"shezo","name":"Shezo","emoji":"💫","color":"#9C27B0"},
    {"id":"alle", "name":"Alle", "emoji":"🌍","color":"#00BCD4"},
]

def lj(p,d):
    try:
        with open(p) as f: return json.load(f)
    except: return d

def sj(p,d):
    os.makedirs(os.path.dirname(p),exist_ok=True)
    with open(p,"w") as f: json.dump(d,f,indent=2,ensure_ascii=False)

def load_all():
    global songs_db,favorites_db,users_db
    users_db=lj(os.path.join(BASE_DIR,"users.json"),{})
    songs_db={}
    favorites_db={}
    for u in FIXED_USERS:
        uid=u["id"]
        users_db.setdefault(uid,u)
        os.makedirs(os.path.join(MUSIC_DIR,uid),exist_ok=True)
        songs_db[uid]=lj(os.path.join(MUSIC_DIR,uid,"songs.json"),{})
        favorites_db[uid]=lj(os.path.join(MUSIC_DIR,uid,"favorites.json"),{})
    sj(os.path.join(BASE_DIR,"users.json"),users_db)

def save_all():
    sj(os.path.join(BASE_DIR,"users.json"),users_db)
    for uid in users_db:
        sj(os.path.join(MUSIC_DIR,uid,"songs.json"),songs_db.get(uid,{}))
        sj(os.path.join(MUSIC_DIR,uid,"favorites.json"),favorites_db.get(uid,{}))

load_all()

download_jobs={}
dl_queue=[]
dl_lock=threading.Lock()

def download_worker():
    while True:
        job=None
        with dl_lock:
            if dl_queue: job=dl_queue.pop(0)
        if not job: time.sleep(0.5); continue
        jid=job["job_id"]; uid=job["user_id"]; sid=job["song_id"]
        title=job["title"]; upl=job.get("uploader","")
        download_jobs[jid]={"state":"downloading","progress":5,"song_id":sid,"error":None}
        try:
            udir=os.path.join(MUSIC_DIR,uid)
            os.makedirs(udir,exist_ok=True)
            safe="".join(c for c in title if c.isalnum() or c in " _-")[:60].strip()
            cmd=["/home/dlohoro/spotify_clone/venv/bin/yt-dlp",f"ytsearch1:{title} {upl}".strip(),"-x",
                 "--audio-format","mp3","--audio-quality","0",
                 "-o",os.path.join(udir,safe+".%(ext)s"),
                 "--no-playlist","--no-warnings","-q"]
            download_jobs[jid]["progress"]=20
            subprocess.run(cmd,capture_output=True,text=True,timeout=300)
            download_jobs[jid]["progress"]=80
            mp3=None
            for fn in sorted(os.listdir(udir),key=lambda x:os.path.getmtime(os.path.join(udir,x)),reverse=True):
                if fn.endswith(".mp3"): mp3=fn; break
            if not mp3: raise RuntimeError("MP3 nicht gefunden")
            songs_db.setdefault(uid,{})[sid]={"id":sid,"title":title,"uploader":upl,"file":mp3,"is_favorite":False}
            save_all()
            download_jobs[jid]={"state":"done","progress":100,"song_id":sid,"error":None}
        except Exception as e:
            download_jobs[jid]={"state":"error","progress":0,"song_id":sid,"error":str(e)}

threading.Thread(target=download_worker,daemon=True).start()

def get_uid():
    u=request.cookies.get("auraUserId","").strip()
    if u: return u
    u=request.headers.get("X-User-ID","").strip()
    return u or "alle"

def get_base():
    scheme=request.headers.get("X-Forwarded-Proto",request.scheme)
    host=request.headers.get("X-Forwarded-Host",request.host)
    return f"{scheme}://{host}"

@app.route("/")
def index():
    if not request.cookies.get("auraPinOk"):
        return send_from_directory(TMPL_DIR,"pin.html")
    uid=request.cookies.get("auraUserId","").strip()
    if uid and uid in users_db:
        return send_from_directory(TMPL_DIR,"index.html")
    return send_from_directory(TMPL_DIR,"select_user.html")

@app.route("/pin",methods=["POST"])
def check_pin():
    p=request.form.get("pin","")
    if p==PIN:
        resp=make_response(redirect("/"))
        resp.set_cookie("auraPinOk","1",max_age=60*60*24*30)
        return resp
    return send_from_directory(TMPL_DIR,"pin.html")


@app.route("/select/<uid>")
def select_user(uid):
    if uid not in users_db:
        return redirect("/")
    resp = make_response(redirect("/"))
    resp.set_cookie("auraUserId", uid, max_age=60*60*24*365)
    return resp

@app.route("/logout")
def logout():
    resp=make_response(redirect("/"))
    resp.delete_cookie("auraUserId")
    resp.delete_cookie("auraPinOk")
    return resp

@app.route("/manifest.json")
def manifest():
    return jsonify({"name":"Aura Play","short_name":"Aura","start_url":"/","display":"standalone","background_color":"#0a0a0f","theme_color":"#1DB954"})

@app.route("/sw.js")
def sw():
    try: return send_from_directory(BASE_DIR,"sw.js")
    except: return "// no sw",200,{"Content-Type":"application/javascript"}

@app.route("/api/users")
def api_users():
    return jsonify({"users":list(users_db.values())})

@app.route("/api/search")
def api_search():
    q=request.args.get("q","").strip()
    if not q: return jsonify({"results":[]})
    try:
        r=subprocess.run(["/home/dlohoro/spotify_clone/venv/bin/yt-dlp",f"ytsearch10:{q}","--dump-json","--flat-playlist","--no-warnings","-q"],
                         capture_output=True,text=True,timeout=30)
        out=[]
        for line in r.stdout.strip().split("\n"):
            if not line.strip(): continue
            try:
                d=json.loads(line)
                th=d.get("thumbnail","")
                if not th and d.get("thumbnails"): th=d["thumbnails"][0].get("url","")
                out.append({"id":d.get("id",str(uuid.uuid4())),"title":d.get("title","?"),
                            "uploader":d.get("uploader") or d.get("channel") or "",
                            "duration":d.get("duration",0),"thumbnail":th})
            except: continue
        return jsonify({"results":out})
    except Exception as e:
        return jsonify({"results":[],"error":str(e)})

@app.route("/api/download",methods=["POST"])
def api_download():
    uid=get_uid(); data=request.json or {}
    sid=data.get("id") or str(uuid.uuid4())
    if uid in songs_db and sid in songs_db[uid]:
        return jsonify({"success":True,"cached":True,"song_id":sid})
    jid=str(uuid.uuid4())
    with dl_lock:
        dl_queue.append({"job_id":jid,"user_id":uid,"song_id":sid,
                         "title":data.get("title",""),"uploader":data.get("uploader","")})
    download_jobs[jid]={"state":"queued","progress":0,"song_id":sid,"error":None}
    return jsonify({"success":True,"job_id":jid,"song_id":sid})

@app.route("/api/download/status/<jid>")
def dl_status(jid):
    j=download_jobs.get(jid)
    return jsonify(j) if j else (jsonify({"state":"unknown"}),404)

@app.route("/api/play",methods=["POST"])
def api_play():
    uid=get_uid(); sid=(request.json or {}).get("id","")
    song=songs_db.get(uid,{}).get(sid)
    if not song: return jsonify({"success":False,"error":"Nicht geladen"}),404
    base=get_base()
    return jsonify({"success":True,"url":f"{base}/stream/{uid}/{song['file']}","song":song})

@app.route("/stream/<uid>/<fname>")
def stream(uid,fname):
    fp=os.path.join(MUSIC_DIR,uid,fname)
    if not os.path.exists(fp): return "Nicht gefunden",404
    sz=os.path.getsize(fp); rh=request.headers.get("Range")
    if rh:
        s,e=0,sz-1; m=rh.replace("bytes=","").split("-")
        if m[0]: s=int(m[0])
        if len(m)>1 and m[1]: e=int(m[1])
        l=e-s+1
        def gen():
            with open(fp,"rb") as f:
                f.seek(s); rem=l
                while rem>0:
                    c=f.read(min(8192,rem))
                    if not c: break
                    rem-=len(c); yield c
        return Response(gen(),206,headers={"Content-Range":f"bytes {s}-{e}/{sz}",
                        "Accept-Ranges":"bytes","Content-Length":str(l),"Content-Type":"audio/mpeg"})
    return send_file(fp,mimetype="audio/mpeg",conditional=True)

@app.route("/api/library")
def api_library():
    return jsonify({"songs":list(songs_db.get(get_uid(),{}).values())})

@app.route("/api/library/remove",methods=["POST"])
def api_library_remove():
    uid=get_uid(); sid=(request.json or {}).get("id","")
    s=songs_db.get(uid,{}).pop(sid,None)
    if s:
        fp=os.path.join(MUSIC_DIR,uid,s.get("file",""))
        if os.path.exists(fp): os.remove(fp)
        favorites_db.get(uid,{}).pop(sid,None)
        save_all()
    return jsonify({"success":True})

@app.route("/api/favorites")
def api_favorites():
    return jsonify({"favorites":list(favorites_db.get(get_uid(),{}).values())})

@app.route("/api/favorites/add",methods=["POST"])
def api_fav_add():
    uid=get_uid(); sid=(request.json or {}).get("id","")
    s=songs_db.get(uid,{}).get(sid)
    if not s: return jsonify({"success":False}),400
    favorites_db.setdefault(uid,{})[sid]=s.copy()
    songs_db[uid][sid]["is_favorite"]=True
    favorites_db[uid][sid]["is_favorite"]=True
    save_all(); return jsonify({"success":True})

@app.route("/api/favorites/remove",methods=["POST"])
def api_fav_remove():
    uid=get_uid(); sid=(request.json or {}).get("id","")
    favorites_db.get(uid,{}).pop(sid,None)
    if sid in songs_db.get(uid,{}): songs_db[uid][sid]["is_favorite"]=False
    save_all(); return jsonify({"success":True})

if __name__=="__main__":
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close()
    except: ip="127.0.0.1"
    print(f"\n AURA PLAY LAEUFT\n Lokal: http://127.0.0.1:5001\n Netzwerk: http://{ip}:5001\n PIN: 1040\n")
    app.run(host="0.0.0.0",port=5001,debug=False,threaded=True)
