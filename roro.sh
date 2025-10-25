#!/usr/bin/env bash
# tls_probe.sh
# Usage: ./tls_probe.sh subs.txt [port]
# Default port: 443
set -euo pipefail

INPUT="${1:-subs.txt}"
PORT="${2:-443}"
OUT="tls_results.csv"

if [[ ! -f "$INPUT" ]]; then
  echo "Input file not found: $INPUT" >&2
  exit 1
fi

# CSV header
echo "domain,port,reachable,negotiated_protocol,negotiated_cipher,tls1_3_supported,tls1_2_supported,cert_cn,alpn" > "$OUT"

probe_domain () {
  local d="$1" p="$2"
  local reach="no" proto="" cipher="" t13="no" t12="no" cn="" alpn=""

  # 1) Negotiated (sunucunun tercih ettiği) TLS sürümü & cipher
  #   -servername zorunlu (SNI)
  #   -brief birçok OpenSSL sürümünde desteklenir; yoksa normal çıkıştan parse ederiz
  local raw
  raw="$(timeout 6 bash -c "openssl s_client -connect ${d}:${p} -servername ${d} -brief </dev/null 2>/dev/null" || true)"

  if [[ -n "$raw" ]]; then
    reach="yes"
    # Protocol
    proto="$(echo "$raw" | awk -F': ' '/Protocol/ {print $2; exit}')"
    # Cipher
    cipher="$(echo "$raw" | awk -F': ' '/Cipher/ {print $2; exit}')"
    # Certificate CN (subject CN)
    cn="$(echo "$raw" | awk -F'CN=' '/subject=/ {sub(/ .*/,"",$2); print $2; exit}')"
    # ALPN (HTTP/2 vs h2, http/1.1)
    alpn="$(echo "$raw" | awk -F': ' '/ALPN protocol/ {print $2; exit}')"
  else
    # Bazı OpenSSL’lerde -brief yok; normal çıktıyı deneyelim
    raw="$(timeout 6 bash -c "openssl s_client -connect ${d}:${p} -servername ${d} </dev/null 2>/dev/null" || true)"
    if [[ -n "$raw" ]]; then
      reach="yes"
      proto="$(echo "$raw" | awk -F': ' '/Protocol  / {print $2; exit}')"
      cipher="$(echo "$raw" | awk -F': ' '/Cipher    / {print $2; exit}')"
      cn="$(echo "$raw" | sed -n 's/.*subject=.*CN=\([^,\/]*\).*/\1/p' | head -1)"
      alpn="$(echo "$raw" | awk -F': ' '/ALPN protocol/ {print $2; exit}')"
    fi
  fi

  # 2) TLS 1.3 destek testi (force)
  timeout 5 bash -c "openssl s_client -connect ${d}:${p} -servername ${d} -tls1_3 </dev/null >/dev/null 2>&1" && t13="yes" || true
  # 3) TLS 1.2 destek testi (force)
  timeout 5 bash -c "openssl s_client -connect ${d}:${p} -servername ${d} -tls1_2 </dev/null >/dev/null 2>&1" && t12="yes" || true

  # CSV-safe (virgül/çift tırnak kaçışları)
  # Çift tırnakları iki kez yazarak kaçır
  proto="${proto//\"/\"\"}"
  cipher="${cipher//\"/\"\"}"
  cn="${cn//\"/\"\"}"
  alpn="${alpn//\"/\"\"}"

  printf "\"%s\",%s,%s,\"%s\",\"%s\",%s,%s,\"%s\",\"%s\"\n" \
    "$d" "$p" "$reach" "$proto" "$cipher" "$t13" "$t12" "$cn" "$alpn" >> "$OUT"
}

# Sıra sıra çalıştır (gerekirse aşağıdaki parallel bölümüne bak)
while IFS=$'\r' read -r domain || [[ -n "$domain" ]]; do
  domain="$(echo "$domain" | xargs)"   # trim
  [[ -z "$domain" || "$domain" =~ ^# ]] && continue
  probe_domain "$domain" "$PORT"
done < "$INPUT"

echo "Bitti. Çıktı: $OUT"
