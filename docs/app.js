/*
 * Aura Vision – Live Objekt- & Preis-Scanner
 * Läuft komplett auf dem Gerät (TensorFlow.js + COCO-SSD). Kein Server, kein API-Key.
 */
(() => {
  const video   = document.getElementById('video');
  const overlay = document.getElementById('overlay');
  const ctx     = overlay.getContext('2d');
  const startEl = document.getElementById('start');
  const btnStart= document.getElementById('btnStart');
  const statusEl= document.getElementById('status');
  const dotEl   = document.getElementById('dot');
  const resultsEl = document.getElementById('results');
  const errEl   = document.getElementById('err');
  const btnFlip = document.getElementById('btnFlip');
  const btnPause= document.getElementById('btnPause');

  let model = null;         // COCO-SSD (Objekt-Boxen)
  let netModel = null;      // MobileNet (Vollbild, 1000+ Kategorien)
  let stream = null;
  let facing = 'environment';   // Rückkamera
  let running = false;
  let paused = false;
  let lastRender = 0;
  let lastNet = 0;          // Throttle für MobileNet
  let netResult = null;     // Letzte Vollbild-Klassifikation
  const COLORS = ['#5b8cff','#00e6a8','#ff5b7a','#ffd166','#c77dff','#4cc9f0','#f77f00'];

  const setStatus = (t) => statusEl.textContent = t;

  function showError(html){
    errEl.innerHTML = html;
    errEl.style.display = 'block';
  }

  // --- Kamera starten (muss durch Nutzer-Tap ausgelöst werden, iOS-Anforderung) ---
  async function startCamera(){
    if (stream){ stream.getTracks().forEach(t => t.stop()); }
    try{
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: facing }, width:{ideal:1280}, height:{ideal:720} },
        audio: false
      });
    }catch(e){
      showError('<b>Kamera nicht erlaubt.</b><br>Bitte in den Safari-Einstellungen den Kamerazugriff für diese Seite erlauben und die Seite neu laden.<br><small>' + (e.message||e) + '</small>');
      throw e;
    }
    video.srcObject = stream;
    await video.play();
    resize();
  }

  function resize(){
    overlay.width  = video.videoWidth  || window.innerWidth;
    overlay.height = video.videoHeight || window.innerHeight;
  }
  window.addEventListener('resize', resize);

  // --- Modell laden ---
  async function loadModel(){
    setStatus('KI-Modelle werden geladen…');
    // Beide Modelle parallel laden. 'lite_mobilenet_v2' = schnell fürs Handy.
    const [m, n] = await Promise.all([
      cocoSsd.load({ base: 'lite_mobilenet_v2' }),
      mobilenet.load({ version: 2, alpha: 1.0 })
    ]);
    model = m; netModel = n;
    setStatus('Live');
    dotEl.classList.add('live');
  }

  // Nimmt ein MobileNet-Label ("coffee mug, mug") und liefert das erste, saubere Wort
  function cleanLabel(s){
    return (s || '').split(',')[0].trim();
  }

  // --- Erkennungs-Schleife ---
  async function loop(){
    if (!running) return;
    if (!paused && model && video.readyState >= 2){
      let predictions = [];
      try { predictions = await model.detect(video, 20, 0.5); }
      catch(e){ /* Frame überspringen */ }

      // MobileNet ist schwerer -> nur ~alle 700ms auf dem Vollbild laufen lassen
      const now = performance.now();
      if (netModel && now - lastNet > 700){
        lastNet = now;
        try {
          const cls = await netModel.classify(video, 2);
          if (cls && cls.length) netResult = cls[0];
        } catch(e){ /* Frame überspringen */ }
      }

      draw(predictions);
      renderResults(predictions);
    }
    requestAnimationFrame(loop);
  }

  // Da video object-fit:cover ist, müssen wir Koordinaten skalieren+beschneiden
  function coverTransform(){
    const vw = video.videoWidth, vh = video.videoHeight;
    const cw = overlay.width, ch = overlay.height;
    const scale = Math.max(cw/vw, ch/vh);
    return { scale, dx:(cw - vw*scale)/2, dy:(ch - vh*scale)/2 };
  }

  function draw(preds){
    ctx.clearRect(0,0,overlay.width,overlay.height);
    const {scale,dx,dy} = coverTransform();
    ctx.lineWidth = 3; ctx.font = '600 18px -apple-system,sans-serif';
    preds.forEach((p,i) => {
      const info = window.AURA_DB[p.class] || {de:p.class, emoji:'🔎', price:null};
      const col = COLORS[i % COLORS.length];
      let [x,y,w,h] = p.bbox;
      x = x*scale+dx; y = y*scale+dy; w*=scale; h*=scale;
      // Box
      ctx.strokeStyle = col; ctx.strokeRect(x,y,w,h);
      // Label-Hintergrund
      const label = `${info.emoji} ${info.de}` + (info.price ? `  ·  ${info.price}` : '');
      const tw = ctx.measureText(label).width + 16;
      ctx.fillStyle = col;
      const ly = y > 30 ? y-28 : y+4;
      ctx.fillRect(x, ly, tw, 26);
      ctx.fillStyle = '#0a0a12';
      ctx.fillText(label, x+8, ly+19);
    });
  }

  function shopLink(q){
    return q
      ? `<a class="shop" target="_blank" rel="noopener"
           href="https://www.google.com/search?tbm=shop&q=${encodeURIComponent(q)}">Live-Preise ›</a>`
      : '';
  }

  function objectCard(p){
    const info = window.AURA_DB[p.class] || {de:p.class, emoji:'🔎', price:null, q:p.class};
    const conf = Math.round(p.score*100);
    const priceHtml = info.price
      ? `<span class="price">${info.price}</span> <span class="sub">ca.</span>`
      : `<span class="sub">Preis per „Live-Preise"</span>`;
    return `<div class="card">
      <div class="emoji">${info.emoji}</div>
      <div class="info">
        <div class="name">${info.de}<span class="conf">${conf}%</span></div>
        <div class="sub">${priceHtml}</div>
      </div>
      ${shopLink(info.q || info.de)}
    </div>`;
  }

  // Highlight-Karte aus MobileNet (1000+ Kategorien, "alles auf der Welt")
  function netCard(){
    if (!netResult) return '';
    const label = cleanLabel(netResult.className);
    const conf = Math.round(netResult.probability*100);
    if (conf < 12) return '';
    return `<div class="card net">
      <div class="emoji">🌍</div>
      <div class="info">
        <div class="name">${label}<span class="conf">${conf}%</span></div>
        <div class="sub">Vollbild-Erkennung · <span class="sub">Preis per „Live-Preise"</span></div>
      </div>
      ${shopLink(label)}
    </div>`;
  }

  function renderResults(preds){
    const now = performance.now();
    if (now - lastRender < 350) return; // UI nicht zu oft neu bauen
    lastRender = now;

    // COCO-SSD Objekte nach Klasse zusammenfassen, höchste Konfidenz behalten
    const best = {};
    preds.forEach(p => {
      if (!best[p.class] || p.score > best[p.class].score) best[p.class] = p;
    });
    const items = Object.values(best).sort((a,b)=>b.score-a.score);

    const html = netCard() + items.map(objectCard).join('');
    resultsEl.innerHTML = html || '<div id="empty">Richte die Kamera auf ein Objekt…</div>';
  }

  // --- Steuerung ---
  btnFlip.addEventListener('click', async () => {
    facing = (facing === 'environment') ? 'user' : 'environment';
    try { await startCamera(); } catch(e){}
  });
  btnPause.addEventListener('click', () => {
    paused = !paused;
    btnPause.textContent = paused ? '▶️' : '⏸';
    setStatus(paused ? 'Pausiert' : 'Live');
    dotEl.classList.toggle('live', !paused);
  });

  // --- Start ---
  btnStart.addEventListener('click', async () => {
    btnStart.disabled = true;
    btnStart.textContent = 'Lädt…';
    try{
      await startCamera();
      if (!model) await loadModel();
      startEl.style.display = 'none';
      running = true;
      loop();
    }catch(e){
      btnStart.disabled = false;
      btnStart.textContent = '📷 Erneut versuchen';
    }
  });

  // Service Worker (offline / installierbar)
  if ('serviceWorker' in navigator){
    navigator.serviceWorker.register('sw.js').catch(()=>{});
  }
})();
