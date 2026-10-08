# Latência até o Cloud Run, vista do Brasil (outubro de 2026)

Quanto tempo uma requisição HTTPS leva, a partir de uma conexão residencial no Brasil, até um serviço Cloud Run em cada região do Google Cloud. É a mesma viagem que o navegador do visitante faz quando manda um evento para um GTM server-side (sGTM) hospedado no Cloud Run.

Medição feita pela [Tagelo](https://tagelo.io), que hospeda sGTM em São Paulo. Por isso o script e todas as amostras brutas estão aqui: confira, repita e, se puder, rode de outra cidade. O texto com a análise está no [blog da Tagelo](https://tagelo.io/blog/latencia-gtm-server-side-sao-paulo-eua-europa).

## Resultado (mediana, ms)

| Região | Conexão reaproveitada | Conexão nova |
|---|---:|---:|
| São Paulo (`southamerica-east1`) | 25 | 142 |
| Santiago (`southamerica-west1`) | 101 | 273 |
| Iowa (`us-central1`) | 149 | 298 |
| Carolina do Sul (`us-east1`) | 175 | 298 |
| Bélgica (`europe-west1`) | 218 | 312 |
| Container sGTM da Tagelo (Cloud Run em São Paulo, atrás de um Worker da Cloudflare) | 79 | 197 |

De [`dados/resultados-depois.csv`](dados/resultados-depois.csv): 90 amostras por região e modo, nenhuma falha. A tabela completa, com p90, mínimo e o tempo de cada etapa, sai de `python3 scripts/summarize.py dados/resultados-depois.csv`.

**O detalhe que engana quem mede só o ping:** nos endereços `*.a.run.app`, TCP e TLS terminam na borda do Google mais perto do cliente. O tempo até o fim do handshake empata entre as regiões (95 a 116 ms); a diferença aparece do fim do TLS ao primeiro byte: 27 ms para São Paulo, 144 a 211 ms para as outras.

## Duas medições, e um erro nosso

A primeira medição ([`dados/resultados-antes.csv`](dados/resultados-antes.csv), 19h55 a 20h19 UTC) mostrou o container da Tagelo como o mais lento de todos: 369 ms com conexão reaproveitada e 499 ms com conexão nova. O Worker da Cloudflare na frente do Cloud Run estava com Smart Placement e rodava em Ashburn, nos EUA (`cf-placement: remote-IAD`). Fixamos o Worker perto de São Paulo (`[placement] region = "gcp:southamerica-east1"`, agora `cf-placement: local-GRU`) e medimos de novo das 21h55 às 22h18 UTC, com o mesmo script e da mesma máquina. As regiões do Google deram números parecidos nas duas medições.

O container da Tagelo ainda fica uns 55 ms atrás do Cloud Run puro em São Paulo, e o p90 com conexão nova (598 ms) é o pior da tabela. A diferença está depois do handshake, no caminho Worker → Cloud Run. [`dados/sonda-worker.csv`](dados/sonda-worker.csv) alterna um host sem container (o Worker responde 404 sem ir ao Cloud Run; mediana 57 ms) com o caminho completo (136 ms), na mesma conexão.

## Ponto de medição

- Uma máquina, em Maricá (RJ), numa operadora regional de fibra residencial, sem VPN. O link tem jitter: um `ping` para 8.8.8.8 variou de 8 a 44 ms no mesmo minuto.
- Outra cidade ou uma rede móvel vai ver outros milissegundos. O que deve se repetir é a ordem entre as regiões.

## Método

- **Endpoints:** os serviços Cloud Run públicos do [gcping](https://gcping.com) (lista em `https://global.gcping.com/api/endpoints`). Cada `/api/ping` responde com o nome da própria região, o que foi conferido antes de medir. O container da Tagelo foi medido em `/healthy`.
- **Conexão nova:** um processo `curl` por requisição (DNS + TCP + TLS a cada vez), regiões intercaladas e 1 s de pausa a cada volta, 30 por endpoint por rodada.
- **Conexão reaproveitada:** um `curl` por endpoint, 31 requisições na mesma conexão HTTP/2, uma por segundo. A primeira abre a conexão e fica fora da conta.
- **Rodadas:** 3 por medição, com 5 minutos de pausa. curl 8.18.0.
- **Estatística:** mediana e p90 por nearest-rank, sobre as amostras brutas. Status diferente de 200 conta como falha e fica fora das estatísticas.

## Como repetir

```
scripts/measure.sh 1 30 > resultados.csv
sleep 300; scripts/measure.sh 2 30 >> resultados.csv
sleep 300; scripts/measure.sh 3 30 >> resultados.csv
python3 scripts/summarize.py resultados.csv
```

Para incluir o seu sGTM na comparação, passe a URL de um endpoint leve dele:

```
SGTM_URL=https://seu-sgtm.exemplo.com/healthy SGTM_LABEL=meu-sgtm scripts/measure.sh 1 30 > resultados.csv
```

Cada linha do CSV é uma requisição: `ts_utc, round, mode (cold|warm), label, seq, http_code, remote_ip, num_connects, http_version, t_dns, t_connect, t_tls, t_ttfb, t_total` (tempos em segundos, do `curl -w`). `remote_ip` é o IP do servidor.

## Limitações

- Um ponto de medição, uma rede, uma tarde. Não é uma amostra do Brasil.
- `/api/ping` e `/healthy` não executam tags. Um evento real soma o processamento do container, que é o mesmo em qualquer região.
- HTTP/3 não foi testado; o `curl` usou HTTP/2.
- Cold start do Cloud Run não foi isolado. O container da Tagelo roda com mínimo de 0 instâncias, então um cold start pesaria contra ele.

## Licença

Dados em [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR); scripts em MIT. Cite "Tagelo, medição de latência sGTM, outubro de 2026".
