#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true

if ! command -v cloudflared &>/dev/null; then
  wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O /tmp/cf
  chmod +x /tmp/cf && sudo mv /tmp/cf /usr/local/bin/cloudflared
fi

python3 server.py &
sleep 2

cloudflared tunnel --url http://localhost:5001 2>&1 | tee /tmp/tunnel.log | while read line; do
  if echo "$line" | grep -q "trycloudflare.com"; then
    URL=$(echo "$line" | grep -o 'https://[a-z0-9-]*.trycloudflare.com')
    echo "$URL" > ~/spotify_clone/tunnel_url.txt
    echo "LINK: $URL"
  fi
done
