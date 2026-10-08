#!/usr/bin/env python3
# Summarizes the CSV written by measure.sh into a Markdown table (ms): median, p90, min, n per endpoint.
# Percentiles are nearest-rank on the raw samples; failed requests (http_code != 200) are counted, never dropped silently.
# Usage: python3 scripts/summarize.py dados/resultados-depois.csv
import csv, math, sys
from collections import defaultdict


def pct(xs, p):
    xs = sorted(xs)
    return xs[max(0, math.ceil(p / 100 * len(xs)) - 1)]


assert pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5 and pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9 and pct([7], 90) == 7

ORDER = ['southamerica-east1', 'tagelo-sp-via-cloudflare', 'southamerica-west1', 'us-east1', 'us-central1', 'europe-west1']
samples, failed = defaultdict(list), defaultdict(int)
for r in csv.DictReader(open(sys.argv[1])):
    if r['http_code'] != '200':
        failed[r['mode'], r['label']] += 1
        continue
    ms = {k: float(r[k]) * 1000 for k in ('t_tls', 't_ttfb', 't_total')}
    if r['mode'] == 'cold':
        samples['cold_total', r['label']].append(ms['t_total'])
        samples['cold_tls', r['label']].append(ms['t_tls'])
        samples['cold_after_tls', r['label']].append(ms['t_ttfb'] - ms['t_tls'])
    elif r['num_connects'] == '0':  # warm: only transfers that really reused the connection
        samples['warm_total', r['label']].append(ms['t_total'])

TITLES = {
    'cold_total': 'Conexão nova: tempo total (DNS + TCP + TLS + resposta)',
    'cold_tls': 'Conexão nova: até o fim do TLS (distância até a borda)',
    'cold_after_tls': 'Conexão nova: do fim do TLS ao primeiro byte (ida até a região)',
    'warm_total': 'Conexão reaproveitada: tempo total da requisição',
}
for metric, title in TITLES.items():
    print(f'\n**{title}** (ms)\n\n| Endpoint | Mediana | p90 | Mínimo | n | Falhas |\n|---|---:|---:|---:|---:|---:|')
    for label in ORDER + sorted({l for _, l in samples} - set(ORDER)):  # your SGTM_LABEL goes last
        xs = samples[metric, label]
        if xs:
            mode = metric.split('_')[0]
            print(f'| {label} | {pct(xs, 50):.0f} | {pct(xs, 90):.0f} | {min(xs):.0f} | {len(xs)} | {failed[mode, label]} |')
