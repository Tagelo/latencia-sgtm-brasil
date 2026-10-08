#!/usr/bin/env bash
# Measures HTTPS latency from this machine to Cloud Run endpoints in several GCP regions (gcping) and, if SGTM_URL is set, to your sGTM.
# Cold = a new curl process per request (new TCP+TLS); warm = one curl process, connection reused, 1 request/s.
# Usage: [SGTM_URL=https://your-sgtm/healthy SGTM_LABEL=my-sgtm] scripts/measure.sh <round> [n] >> results.csv   (header when round=1)
set -euo pipefail
round=${1:?round number}; n=${2:-30}

endpoints=(
  "southamerica-east1|https://southamerica-east1-5tkroniexa-rj.a.run.app/api/ping"
  "southamerica-west1|https://southamerica-west1-5tkroniexa-tl.a.run.app/api/ping"
  "us-east1|https://us-east1-5tkroniexa-ue.a.run.app/api/ping"
  "us-central1|https://us-central1-5tkroniexa-uc.a.run.app/api/ping"
  "europe-west1|https://europe-west1-5tkroniexa-ew.a.run.app/api/ping"
)
[ -n "${SGTM_URL:-}" ] && endpoints+=("${SGTM_LABEL:-my-sgtm}|$SGTM_URL")
fmt='%{http_code},%{remote_ip},%{num_connects},%{http_version},%{time_namelookup},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}\n'
now() { date -u +%FT%T.%3NZ; }  # ts_utc = when the curl process started (warm: seq N runs ~N s later)

[ "$round" = 1 ] && echo "ts_utc,round,mode,label,seq,http_code,remote_ip,num_connects,http_version,t_dns,t_connect,t_tls,t_ttfb,t_total"

# Cold: regions interleaved so all of them see the same network conditions, then a 1 s pause.
for i in $(seq 1 "$n"); do
  for e in "${endpoints[@]}"; do
    curl -s -o /dev/null --max-time 10 -w "$(now),$round,cold,${e%%|*},$i,$fmt" "${e#*|}" || true
  done
  sleep 1
done

# Warm: n+1 transfers on one connection at 1 req/s; seq 0 opens the connection (num_connects=1) and is not warm.
for e in "${endpoints[@]}"; do
  args=(); for i in $(seq 0 "$n"); do args+=(-o /dev/null "${e#*|}"); done
  curl -s --max-time 10 --rate 1/s -w "$(now),$round,warm,${e%%|*},%{urlnum},$fmt" "${args[@]}" || true
done
