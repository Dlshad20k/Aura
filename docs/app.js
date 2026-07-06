/*
 * Aura Vision – Fokus-Scanner mit Objekt- & Barcode-Modus
 * Läuft komplett auf dem Gerät (TensorFlow.js + ZXing). Kein Server, kein API-Key.
 *
 *  Fokus-Modus   : erkennt EIN Objekt in der Bildmitte (Fadenkreuz), stabilisiert
 *                  es über mehrere Frames (kein Flackern) und schätzt einen Preis.
 *  Barcode-Modus : liest echte Produkt-Barcodes -> echter Markenname (Open Food Facts)
 *                  + Link zu echten Live-Preisen.
 */
(() => {
  const $ = id => document.getElementById(id);
  const video   = $('video');
  const overlay = $('overlay');
  const ctx     = overlay.getContext('2d');
  const startEl = $('start');
  const btnStart= $('btnStart');
  const statusEl= $('status');
  const dotEl   = $('dot');
  const resultsEl = $('results');
  const sheetTitle= $('sheetTitle');
  const reticle = $('reticle');
  const errEl   = $('err');
  const btnFlip = $('btnFlip');
  const btnPause= $('btnPause');
  const modeObjectBtn  = $('modeObject');
  const modeBarcodeBtn = $('modeBarcode');

  let model = null, netModel = null, codeReader = null;
  let stream = null, facing = 'environment';
  let running = false, paused = false, mode = 'object';
  let lastNet = 0, lastRender = 0, lastScan = 0;
  let focus = null, challenger = null, lastBarcode = null;

  // Offscreen-Canvas fürs Zuschneiden (MobileNet) und Barcode-Scan
  const crop = document.createElement('canvas');
  const cctx = crop.getContext('2d', { willReadFrequently: true });
  const bc = document.createElement('canvas');
  const bctx = bc.getContext('2d', { willReadFrequently: true });

  const setStatus = t => statusEl.textContent = t;
  const showError = html => { errEl.innerHTML = html; errEl.style.display = 'block'; };

  /* ---------- Kamera ---------- */
  async function startCamera(){
    if (stream) stream.getTracks().forEach(t => t.stop());
    try{
      stream = await navigator.mediaDevices.getUserMedia({
        video:{ facingMode:{ ideal:facing }, width:{ideal:1280}, height:{ideal:720} }, audio:false
      });
    }catch(e){
      showError('<b>Kamera nicht erlaubt.</b><br>Bitte in den Safari-Einstellungen den Kamerazugriff für diese Seite erlauben und neu laden.<br><small>'+(e.message||e)+'</small>');
      throw e;
    }
    video.srcObject = stream;
    await video.play();
    resize();
  }
  function resize(){ overlay.width = window.innerWidth; overlay.height = window.innerHeight; }
  window.addEventListener('resize', resize);
  window.addEventListener('orientationchange', () => setTimeout(resize, 300));

  /* ---------- Modelle ---------- */
  async function loadModels(){
    setStatus('KI-Modelle werden geladen…');
    const [m, n] = await Promise.all([
      cocoSsd.load({ base:'lite_mobilenet_v2' }),
      mobilenet.load({ version:2, alpha:1.0 })
    ]);
    model = m; netModel = n;
    setStatus('Live'); dotEl.classList.add('live');
  }
  const cleanLabel = s => (s||'').split(',')[0].trim();

  /* ---------- Koordinaten: Video (cover) -> Bildschirm ---------- */
  function cover(){
    const vw = video.videoWidth, vh = video.videoHeight;
    const cw = overlay.width, ch = overlay.height;
    const scale = Math.max(cw/vw, ch/vh);
    return { scale, dx:(cw-vw*scale)/2, dy:(ch-vh*scale)/2, vw, vh };
  }

  /* ---------- Fokus-Modus ---------- */
  // Wählt das Objekt in der Bildmitte (unter dem Fadenkreuz)
  function pickCentral(preds){
    const { vw, vh } = cover();
    const cx = vw/2, cy = vh/2;
    let best = null, bestScore = -1;
    for (const p of preds){
      if (p.score < 0.45) continue;
      const [x,y,w,h] = p.bbox;
      const contains = cx>=x && cx<=x+w && cy>=y && cy<=y+h;
      const boxCx = x+w/2, boxCy = y+h/2;
      const dist = Math.hypot(boxCx-cx, boxCy-cy) / Math.hypot(vw,vh); // 0..~0.7
      // Mittige, große, sichere Objekte bevorzugen
      const areaFrac = (w*h)/(vw*vh);
      const s = (contains ? 1.0 : 0.0) + p.score*0.6 + areaFrac*0.8 - dist*1.2;
      if (s > bestScore){ bestScore = s; best = p; }
    }
    // Nur akzeptieren, wenn es die Mitte enthält oder sehr nah dran ist
    if (best){
      const [x,y,w,h] = best.bbox;
      const boxCx = x+w/2, boxCy = y+h/2;
      const near = Math.hypot(boxCx-cx, boxCy-cy) < Math.min(vw,vh)*0.33;
      if ((cx>=x&&cx<=x+w&&cy>=y&&cy<=y+h) || near) return best;
    }
    return null;
  }

  const mkFocus = c => ({ cls:c.class, score:c.score, box:c.bbox.slice(), seen:1, lostAt:0, refined:null });
  function lerpBox(a, b, t){ return a.map((v,i) => v + (b[i]-v)*t); }

  async function refineFocus(){
    if (!focus) return;
    const [x,y,w,h] = focus.box.map(Math.round);
    if (w < 8 || h < 8) return;
    crop.width = 224; crop.height = 224;
    try {
      cctx.drawImage(video, Math.max(0,x), Math.max(0,y), w, h, 0, 0, 224, 224);
      const res = await netModel.classify(crop, 1);
      if (res && res[0] && res[0].probability > 0.18)
        focus.refined = { label: cleanLabel(res[0].className), prob: res[0].probability };
    } catch(e){ /* ignore */ }
  }

  function updateFocus(preds, now){
    const cand = pickCentral(preds);
    if (cand){
      if (focus && cand.class === focus.cls){
        focus.box = lerpBox(focus.box, cand.bbox, 0.35);   // sanft nachziehen -> kein Springen
        focus.score = focus.score*0.7 + cand.score*0.3;
        focus.seen++; focus.lostAt = 0; challenger = null;
      } else if (!focus){
        focus = mkFocus(cand);
      } else {
        // Anderes Objekt: erst nach mehrfacher Bestätigung wechseln (Anti-Flacker)
        if (challenger && challenger.cls === cand.class) challenger.count++;
        else challenger = { cls:cand.class, count:1 };
        if (challenger.count >= 2 || cand.score > focus.score + 0.2){
          focus = mkFocus(cand); challenger = null;
        }
      }
    } else if (focus){
      if (!focus.lostAt) focus.lostAt = now;
      if (now - focus.lostAt > 900){ focus = null; challenger = null; }
    }
    reticle.classList.toggle('lock', !!focus);
  }

  function drawFocus(){
    ctx.clearRect(0,0,overlay.width,overlay.height);
    if (!focus) return;
    const { scale, dx, dy } = cover();
    const [x,y,w,h] = focus.box;
    const sx = x*scale+dx, sy = y*scale+dy, sw = w*scale, sh = h*scale;
    ctx.lineWidth = 3; ctx.strokeStyle = '#00e6a8';
    ctx.strokeRect(sx, sy, sw, sh);
  }

  /* ---------- Barcode-Modus ---------- */
  function getCodeReader(){
    if (codeReader) return codeReader;
    const hints = new Map();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
      ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8,
      ZXing.BarcodeFormat.UPC_A,  ZXing.BarcodeFormat.UPC_E,
      ZXing.BarcodeFormat.CODE_128, ZXing.BarcodeFormat.CODE_39,
      ZXing.BarcodeFormat.QR_CODE
    ]);
    hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
    codeReader = new ZXing.BrowserMultiFormatReader(hints);
    return codeReader;
  }

  function scanBarcode(){
    const { scale, dx, dy, vw, vh } = cover();
    // Bildschirm-Fadenkreuz zurück in Video-Koordinaten rechnen
    const side = Math.min(window.innerWidth*0.56, 320);
    const sx = (window.innerWidth-side)/2, sy = (window.innerHeight-side)/2;
    let rx = (sx-dx)/scale, ry = (sy-dy)/scale, rw = side/scale, rh = side/scale;
    rx = Math.max(0,rx); ry = Math.max(0,ry);
    rw = Math.min(rw, vw-rx); rh = Math.min(rh, vh-ry);
    bc.width = Math.round(rw); bc.height = Math.round(rh);
    bctx.drawImage(video, rx, ry, rw, rh, 0, 0, bc.width, bc.height);
    try {
      const lum = new ZXing.HTMLCanvasElementLuminanceSource(bc);
      const bitmap = new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(lum));
      return getCodeReader().decodeBitmap(bitmap).getText();
    } catch(e){ return null; }   // NotFoundException = kein Barcode im Bild
  }

  async function onBarcode(code){
    if (code === lastBarcode) return;
    lastBarcode = code;
    reticle.classList.add('lock');
    if (navigator.vibrate) navigator.vibrate(60);
    renderBarcode({ code, loading:true });
    let name = null, brand = null, img = null;
    try {
      const r = await fetch(`https://world.openfoodfacts.org/api/v2/product/${encodeURIComponent(code)}.json?fields=product_name,brands,image_front_small_url`);
      const j = await r.json();
      if (j && j.status === 1 && j.product){
        name  = j.product.product_name || null;
        brand = j.product.brands || null;
        img   = j.product.image_front_small_url || null;
      }
    } catch(e){ /* offline / nicht gefunden */ }
    renderBarcode({ code, name, brand, img });
  }

  /* ---------- Rendering ---------- */
  const shopLink = (q, label='Live-Preise ›') =>
    q ? `<a class="shop" target="_blank" rel="noopener"
          href="https://www.google.com/search?tbm=shop&q=${encodeURIComponent(q)}">${label}</a>` : '';

  function renderFocusCard(){
    const now = performance.now();
    if (now - lastRender < 250) return;
    lastRender = now;
    if (!focus){
      resultsEl.innerHTML = '<div id="empty">Richte das Fadenkreuz auf eine Sache…</div>';
      return;
    }
    const db = window.AURA_DB[focus.cls] || { de:focus.cls, emoji:'🔎', price:null, q:focus.cls };
    const name = focus.refined ? focus.refined.label : db.de;
    const conf = Math.round((focus.refined ? focus.refined.prob : focus.score) * 100);
    const price = db.price
      ? `<span class="price">${db.price}</span> <span class="sub">ca.</span>`
      : `<span class="sub">Preis per „Live-Preise"</span>`;
    const q = focus.refined ? focus.refined.label : (db.q || db.de);
    resultsEl.innerHTML = `<div class="card net">
      <div class="emoji">${db.emoji}</div>
      <div class="info">
        <div class="name">${name}<span class="conf">${conf}%</span></div>
        <div class="sub">${price}${db.de && db.de!==name ? ' · '+db.de : ''}</div>
      </div>
      ${shopLink(q)}
    </div>`;
  }

  function renderBarcode(d){
    if (d.loading){
      resultsEl.innerHTML = `<div class="card net"><div class="emoji">🏷️</div>
        <div class="info"><div class="name">Barcode ${d.code}</div>
        <div class="sub">Suche Produkt…</div></div></div>`;
      return;
    }
    const title = [d.brand, d.name].filter(Boolean).join(' – ') || `Unbekanntes Produkt`;
    const q = (d.brand || d.name) ? [d.brand, d.name].filter(Boolean).join(' ') : d.code;
    const thumb = d.img ? `<img src="${d.img}" style="width:44px;height:44px;border-radius:10px;object-fit:cover">`
                        : `<div class="emoji">🏷️</div>`;
    resultsEl.innerHTML = `<div class="card net">
      ${thumb}
      <div class="info">
        <div class="name">${title}</div>
        <div class="sub">Barcode ${d.code}${(d.brand||d.name)?'':' · nicht in Datenbank'}</div>
      </div>
      ${shopLink(q, 'Echte Preise ›')}
    </div>`;
  }

  /* ---------- Hauptschleife ---------- */
  async function loop(){
    if (!running) return;
    if (!paused && video.readyState >= 2){
      const now = performance.now();
      if (mode === 'object' && model){
        let preds = [];
        try { preds = await model.detect(video, 15, 0.45); } catch(e){}
        updateFocus(preds, now);
        if (focus && netModel && now - lastNet > 500){ lastNet = now; refineFocus(); }
        drawFocus();
        renderFocusCard();
      } else if (mode === 'barcode'){
        ctx.clearRect(0,0,overlay.width,overlay.height);
        if (now - lastScan > 220){
          lastScan = now;
          const code = scanBarcode();
          if (code) onBarcode(code);
        }
      }
    }
    requestAnimationFrame(loop);
  }

  /* ---------- Modus-Umschaltung ---------- */
  function setMode(m){
    mode = m;
    focus = null; challenger = null; lastBarcode = null;
    reticle.classList.remove('lock');
    ctx.clearRect(0,0,overlay.width,overlay.height);
    modeObjectBtn.classList.toggle('on', m==='object');
    modeBarcodeBtn.classList.toggle('on', m==='barcode');
    if (m==='object'){
      sheetTitle.textContent = 'Fokus · zentriere ein Objekt';
      resultsEl.innerHTML = '<div id="empty">Richte das Fadenkreuz auf eine Sache…</div>';
    } else {
      sheetTitle.textContent = 'Barcode · echte Marke & Preise';
      resultsEl.innerHTML = '<div id="empty">Halte einen Produkt-Barcode ins Fadenkreuz…</div>';
    }
  }
  modeObjectBtn.addEventListener('click', () => setMode('object'));
  modeBarcodeBtn.addEventListener('click', () => setMode('barcode'));

  /* ---------- Steuerung ---------- */
  btnFlip.addEventListener('click', async () => {
    facing = facing==='environment' ? 'user' : 'environment';
    try { await startCamera(); } catch(e){}
  });
  btnPause.addEventListener('click', () => {
    paused = !paused;
    btnPause.textContent = paused ? '▶️' : '⏸';
    setStatus(paused ? 'Pausiert' : 'Live');
    dotEl.classList.toggle('live', !paused);
  });

  btnStart.addEventListener('click', async () => {
    btnStart.disabled = true; btnStart.textContent = 'Lädt…';
    try{
      await startCamera();
      if (!model) await loadModels();
      startEl.style.display = 'none';
      running = true; loop();
    }catch(e){
      btnStart.disabled = false; btnStart.textContent = '📷 Erneut versuchen';
    }
  });

  if ('serviceWorker' in navigator)
    navigator.serviceWorker.register('sw.js').catch(()=>{});
})();
