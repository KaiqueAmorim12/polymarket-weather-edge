# WeatherEdge v2 — Documentacao Completa

> Ultima atualizacao: 2026-04-06

---

## 1. Visao Geral

### O que e o sistema

O WeatherEdge v2 e um sistema de monitoramento de temperatura em tempo real que coleta dados meteorologicos de 34 cidades ao redor do mundo para apoiar decisoes de apostas em contratos de clima na plataforma Polymarket.

### Qual problema resolve

A Polymarket oferece contratos de aposta sobre "qual sera a temperatura maxima em [cidade] no dia [data]". O sistema resolve o problema de:

1. **Informacao assimetrica**: coleta dados de 6 modelos meteorologicos diferentes e compara com leituras reais para identificar qual modelo e mais preciso para cada cidade.
2. **Timing**: envia alertas Telegram 1 hora antes do pico de temperatura estimado, dando tempo para o usuario apostar antes da resolucao.
3. **Historico e acuracia**: mantem ranking dinamico de acuracia por modelo/cidade nos ultimos 30 dias, permitindo identificar "edge" (vantagem) sobre as odds do mercado.

### Como funciona em alto nivel (fluxo simplificado)

```
[Weather Underground API] --> Leituras hora a hora (34 cidades)
[Open-Meteo API]          --> Previsoes de 6 modelos meteorologicos
[Polymarket Gamma API]    --> Odds por faixa de temperatura
         |
         v
    [Supabase (PostgreSQL)]  <-- banco central
         |
         v
    [Dashboard HTML]  --> grid de cidades + detalhe + grafico + ranking
    [Telegram Bot]    --> alertas 1h antes do pico
```

O ciclo principal roda a cada 30 minutos via GitHub Actions e Railway:
1. Coleta leituras de temperatura de todas as 34 cidades via Weather Underground
2. Coleta previsoes dos 6 modelos meteorologicos via Open-Meteo
3. Busca odds atuais da Polymarket por faixa de temperatura
4. Salva tudo no Supabase
5. Dashboard (Firebase) consulta Supabase diretamente e exibe em tempo real
6. Alertas Telegram disparam 1h antes do pico estimado (13h local de cada cidade)

---

## 2. Arquitetura

### Diagrama da arquitetura

```
+------------------+       +-------------------+       +------------------+
|   GitHub Actions |       |     Railway       |       | Firebase Hosting |
|                  |       |                   |       |                  |
| - Coleta (6h)   |       | - Streamlit app   |       | - index.html     |
| - Modelos (1h)  |  -->  | - Coleta bg (30m) |       | - Dashboard SPA  |
| - Previsao 6h   |       |                   |       |                  |
| - Alertas (1h)  |       +--------+----------+       +--------+---------+
| - Limpeza (1/d) |                |                            |
+--------+---------+               |                            |
         |                         v                            v
         |              +----------+----------------------------+-------+
         +------------->|              Supabase (PostgreSQL)             |
                        |                                               |
                        |  we_leituras | we_modelos | we_odds           |
                        |  we_previsoes | we_apostas                    |
                        +-----------------------------------------------+
                                        ^
                                        |
                        +---------------+---------------+
                        |               |               |
                  Weather Underground  Open-Meteo   Polymarket
                    (leituras)        (6 modelos)   (odds)
```

### Papel de cada componente

| Componente | Papel |
|---|---|
| **GitHub Actions** | Orquestrador principal — roda scripts Python em cron para coleta, previsao, alertas e limpeza |
| **Railway** | Hospeda Streamlit (dashboard alternativo) + thread de coleta em background a cada 30 min |
| **Firebase Hosting** | Hospeda o dashboard HTML/JS estatico (frontend principal) |
| **Supabase** | Banco PostgreSQL central — armazena leituras, previsoes, modelos, odds e apostas |
| **Telegram Bot** | Envia alertas formatados 1h antes do pico de cada cidade |

### Fluxo de dados detalhado

1. **Coleta de leituras** (`main.py`): Weather Underground API -> parse -> Supabase `we_leituras`
2. **Coleta de modelos** (`coletar_modelos.py`): Open-Meteo API (6 modelos) -> Supabase `we_modelos`
3. **Captura de previsao** (`capturar_previsao.py`): WU Forecast API as 6h local -> Supabase `we_previsoes`
4. **Coleta de odds** (`main.py`): Polymarket Gamma API -> parse faixas -> Supabase `we_odds`
5. **Dashboard** (`frontend/index.html`): JavaScript busca Supabase REST API diretamente (anon key)
6. **Alertas** (`alerta_telegram.py`): consulta Supabase, calcula ranking, envia via Telegram Bot API

---

## 3. Stack Tecnologica

### Linguagens e frameworks

| Tecnologia | Uso |
|---|---|
| **Python 3.13** | Backend — coleta, processamento, alertas |
| **JavaScript (vanilla)** | Frontend — dashboard SPA sem framework |
| **HTML/CSS** | Interface do dashboard |
| **Chart.js 4.4.4** | Graficos de curva de temperatura |

### Bibliotecas Python

| Pacote | Versao | Uso |
|---|---|---|
| `httpx` | >= 0.28 | Cliente HTTP async para APIs |
| `schedule` | >= 1.2 | Agendamento de tarefas periodicas |
| `streamlit` | >= 1.44 | Dashboard alternativo (Railway) |
| `plotly` | >= 6.0 | Graficos no Streamlit |
| `numpy` | >= 2.2 | Calculos numericos |
| `scipy` | >= 1.15 | Calculos estatisticos |
| `supabase` | >= 2.0 | SDK Python do Supabase |
| `beautifulsoup4` | >= 4.13 | Parsing HTML |
| `python-dotenv` | >= 1.0 | Variaveis de ambiente (.env) |
| `pytest` / `pytest-asyncio` | >= 8.3 / 0.25 | Testes |

### Servicos cloud

| Servico | Funcao |
|---|---|
| **Firebase Hosting** | Hospedagem do frontend HTML estatico |
| **Railway** | Hospedagem do backend Streamlit + coleta background |
| **Supabase** | Banco PostgreSQL + REST API + autenticacao |
| **GitHub Actions** | CI/CD — workflows automatizados com cron |

### APIs externas

| API | Funcao | Autenticacao |
|---|---|---|
| **Weather Underground** (api.weather.com) | Leituras historicas de temperatura hora a hora | API Key |
| **Open-Meteo** | Previsoes de 6 modelos meteorologicos | Publica (sem key) |
| **Polymarket Gamma API** | Odds de contratos de temperatura | Publica (sem key) |
| **Telegram Bot API** | Envio de alertas | Bot Token |

---

## 4. Hospedagem e Infraestrutura

### 4.1 Firebase Hosting

**O que hospeda**: O frontend HTML estatico — um unico arquivo `index.html` de ~2267 linhas que contem todo o CSS, JavaScript e logica do dashboard SPA (Single Page Application).

**Configuracao** (`firebase.json`):
```json
{
  "hosting": {
    "public": "frontend",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{"source": "**", "destination": "/index.html"}]
  }
}
```

**Como fazer deploy**:
```bash
firebase deploy --only hosting
```

**Custos**: Gratuito no plano Spark (10 GB de transferencia/mes, 1 GB de armazenamento).

### 4.2 Railway

**O que roda**: O script `railway_start.py` que faz duas coisas simultaneamente:
1. **Thread de coleta em background**: roda `executar_ciclo()` a cada 30 minutos
2. **Streamlit**: serve o dashboard alternativo na porta definida pelo Railway

**Procfile**:
```
web: python railway_start.py
```

**Funcionamento**: O `railway_start.py` inicia uma thread daemon para coleta periodica e depois executa o Streamlit via `subprocess.run`. A porta e lida da variavel de ambiente `PORT` (default: 8501).

**Variaveis de ambiente necessarias**:
- `PORT` — porta do servidor (definida automaticamente pelo Railway)
- `SUPABASE_URL` — URL do projeto Supabase
- `SUPABASE_SERVICE_KEY` — chave de servico do Supabase

**Custos**: Plano trial gratuito com limites de uso; plano Hobby a partir de $5/mes.

### 4.3 Supabase

**Banco PostgreSQL** hospedado em `wzjdthcxlsopmqcwtvla.supabase.co`.

**Tabelas** (5 tabelas com prefixo `we_`):

| Tabela | Campos principais | Descricao |
|---|---|---|
| `we_leituras` | cidade, data_alvo, timestamp_wu, temperatura, hora_utc, hora_local, unidade | Leituras de temperatura hora a hora do WU |
| `we_modelos` | cidade, data_alvo, modelo, temp_max_prevista, unidade, hora_captura, criado_em | Previsoes dos 6 modelos meteorologicos |
| `we_previsoes` | cidade, data_alvo, temp_max_prevista, unidade, hora_captura, criado_em | Previsao de maxima capturada as 6h local |
| `we_odds` | cidade, data_alvo, faixa, preco_compra, volume, coletado_em | Odds da Polymarket por faixa de temperatura |
| `we_apostas` | cidade, data_alvo, faixa, tipo, odd, valor, horario_registro, resultado, pnl | Apostas registradas pelo usuario |

**Chaves de acesso** (censuradas parcialmente):
- **Anon key** (frontend, somente leitura): `eyJhbGci...ZnAUBX0K...6B6w`
- **Service role key** (backend, leitura + escrita): `eyJhbGci...ZRXuEULi...Ts0Q`

**RLS (Row Level Security)**: O frontend usa a anon key que permite apenas leitura. O backend usa a service role key que bypassa RLS para escrita.

**Custos**: Plano Free — 500 MB de banco, 2 GB de transferencia, 50.000 requisicoes/dia.

### 4.4 GitHub Actions

**5 workflows configurados**:

| Workflow | Arquivo | Cron | Frequencia | O que faz |
|---|---|---|---|---|
| **Coleta** | `coleta_diaria.yml` | `0 */6 * * *` | A cada 6 horas | Roda `agendar.py --agora` + `exportar_json.py`, commit e push dos resultados |
| **Modelos** | `modelos_diario.yml` | `0 * * * *` | A cada 1 hora | Roda `coletar_modelos.py` — coleta previsoes dos 6 modelos |
| **Previsao 6h** | `previsao_6h.yml` | 13 crons diferentes | 13x/dia (1 por fuso) | Roda `capturar_previsao.py` — captura previsao de maxima as 6h local |
| **Alertas** | `alerta_telegram.yml` | `0 * * * *` | A cada 1 hora | Roda `alerta_telegram.py` — verifica e envia alertas Telegram |
| **Limpeza** | `limpeza_diaria.yml` | `0 4 * * *` | 1x/dia (4h UTC) | Roda `limpar_antigos.py` — remove registros > 30 dias |

**Detalhes dos workflows**:

- **Coleta**: timeout de 15 min, instala requirements.txt completo, faz commit e push dos resultados
- **Modelos**: timeout de 10 min, instala apenas httpx
- **Previsao 6h**: timeout de 5 min, usa secrets do Supabase, 13 gatilhos cron (um para cada grupo de fuso horario)
- **Alertas**: timeout de 5 min, instala apenas httpx
- **Limpeza**: timeout de 5 min, instala apenas httpx

**Custos**: GitHub Actions oferece 2.000 minutos gratuitos/mes para repositorios privados.

**Estimativa de uso mensal**:
- Coleta: 4 runs/dia x 30 dias x ~5 min = ~600 min
- Modelos: 24 runs/dia x 30 dias x ~3 min = ~2.160 min
- Previsao: 13 runs/dia x 30 dias x ~2 min = ~780 min
- Alertas: 24 runs/dia x 30 dias x ~2 min = ~1.440 min
- Limpeza: 1 run/dia x 30 dias x ~1 min = ~30 min
- **Total estimado**: ~5.010 min/mes (acima do limite gratuito para repos privados; gratuito se publico)

---

## 5. Fontes de Dados

### 5.1 Weather Underground API

**O que coleta**: Leituras de temperatura historicas (observacoes) a cada ~30 minutos para cada estacao meteorologica.

**Endpoint**: `https://api.weather.com/v1/location/{estacao}/observations/historical.json`

**API Key**: `e1f10a...96f525`

**Parametros**:
- `apiKey` — chave de autenticacao
- `units` — `m` para Celsius, `e` para Fahrenheit
- `startDate` / `endDate` — range de datas em formato YYYYMMDD

**Frequencia de atualizacao**: A cada 30 minutos (via `main.py` no ciclo principal).

**Como funciona o fuso horario (dia local)**:

O WU API retorna dados em UTC. Para garantir cobertura completa do dia local de cada cidade, o sistema ajusta o range de datas:

- **Fusos positivos** (ex: Tokyo UTC+9): pede o dia anterior UTC tambem, pois a manha local (ex: 00:00-09:00 Tokyo) corresponde ao dia anterior em UTC
- **Fusos negativos** (ex: NYC UTC-4): pede o dia seguinte UTC tambem, pois a noite local corresponde ao dia seguinte em UTC

Apos receber os dados, filtra apenas as leituras que pertencem ao dia LOCAL correto usando o `fuso_offset`.

**Importancia**: Esta e a MESMA fonte que a Polymarket usa para resolver os contratos. A temperatura maxima registrada pelo WU naquele dia determina quem ganha a aposta.

**Endpoint de previsao** (forecast): `https://api.weather.com/v3/wx/forecast/daily/5day`
- Usado para capturar previsao de temperatura maxima as 6h local
- Parametros: `geocode` (lat,lon), `format`, `units`, `language`, `apiKey`
- Retorna temperatura maxima prevista para os proximos 5 dias

### 5.2 Open-Meteo (6 Modelos Meteorologicos)

**Quais modelos**:

| Modelo | Codigo Open-Meteo | Origem |
|---|---|---|
| **ECMWF** | `ecmwf_ifs025` | Centro Europeu (Europa) |
| **GFS** | `gfs_seamless` | NOAA (EUA) |
| **ICON** | `icon_seamless` | DWD (Alemanha) |
| **UKMO** | `ukmo_seamless` | Met Office (Reino Unido) |
| **JMA** | `jma_seamless` | JMA (Japao) |
| **GEM** | `gem_seamless` | Environment Canada |

**Endpoint**: `https://api.open-meteo.com/v1/forecast`

**Parametros**:
- `latitude`, `longitude` — coordenadas da cidade
- `daily` = `temperature_2m_max` — temperatura maxima prevista
- `models` — nome do modelo
- `forecast_days` = 2 — hoje e amanha

**Conversao de unidades**: Open-Meteo retorna sempre em Celsius. Para cidades com unidade Fahrenheit (EUA), o sistema converte: `F = C * 9/5 + 32`.

**Ranking de acuracia (teste de 30 dias)**:

O sistema calcula dinamicamente qual modelo e mais preciso para cada cidade nos ultimos 30 dias:

1. Busca previsoes de cada modelo no Supabase (`we_modelos`)
2. Busca leituras reais (`we_leituras`) e calcula a temperatura maxima real de cada dia
3. Compara: **acerto = previsao arredondada == maxima real arredondada**
4. Ordena modelos por numero de acertos (descendente)
5. Os 3 melhores recebem medalha: ouro, prata, bronze

**Por que cada cidade tem seu melhor modelo**: Modelos meteorologicos tem resolucoes espaciais e parametrizacoes diferentes. O ECMWF pode ser excelente para Paris mas mediocre para Jakarta. O ranking dinamico garante que o sistema sempre recomenda o modelo com melhor historico recente para cada cidade especifica.

### 5.3 Polymarket Gamma API

**O que busca**: Odds (probabilidades de mercado) por faixa de temperatura para cada cidade/data.

**Endpoint**: `https://gamma-api.polymarket.com/events/slug/{slug}`

**Como constroi o slug**: Padrao fixo baseado no nome da cidade e data:
```
highest-temperature-in-{cidade}-on-{mes}-{dia}-{ano}
```
Exemplo: `highest-temperature-in-london-on-april-8-2026`

**Formato das faixas**:
- **Celsius** (maioria das cidades): faixas de 1 grau C (ex: "20 C", "21 C", "22 C or higher", "18 C or below")
- **Fahrenheit** (cidades dos EUA): faixas de 2 graus F (ex: "between 68-69 F", "70 F or higher")

**Dados extraidos por faixa**:
- `faixa_grau` — temperatura da faixa (ex: 20)
- `tipo_faixa` — tipo (exato, higher, lower, range)
- `preco_compra` — probabilidade de mercado (0.0 a 1.0)
- `volume` — volume negociado em USD

### 5.4 Telegram API

**Bot Token**: `8694...Xv28`
**Chat ID**: `6406...6436`

**O que envia**: Mensagem formatada em HTML com:
- Nome da cidade e horario do pico
- Temperatura atual
- Melhor modelo dos ultimos 30 dias + percentual de acerto
- Ranking top 3 modelos
- Previsao do melhor modelo
- Consenso entre modelos (temperatura com mais votos)
- Lista de todos os modelos com suas previsoes (melhor destacado com `<<<`)
- Odd da Polymarket para a faixa prevista (se disponivel)

**Quando envia**: 1 hora antes do pico estimado, ou seja, as **13h local** de cada cidade. O script roda a cada hora (via GitHub Actions) e verifica se alguma cidade esta entre 13:00 e 13:30 local naquele momento. Se sim, envia o alerta.

---

## 6. Cidades Monitoradas

### Tabela completa das 34 cidades

| # | Nome | Estacao WU | Unidade | Fuso | Offset UTC | Regiao |
|---|---|---|---|---|---|---|
| 1 | Wellington | NZWN:9:NZ | C | Pacific/Auckland | +12 | Oceania |
| 2 | Seoul | RKSS:9:KR | C | Asia/Seoul | +9 | Asia |
| 3 | Tokyo | RJTT:9:JP | C | Asia/Tokyo | +9 | Asia |
| 4 | Busan | RKPK:9:KR | C | Asia/Seoul | +9 | Asia |
| 5 | Shanghai | ZSPD:9:CN | C | Asia/Shanghai | +8 | Asia |
| 6 | Hong Kong | VHHH:9:HK | C | Asia/Hong_Kong | +8 | Asia |
| 7 | Beijing | ZBAA:9:CN | C | Asia/Shanghai | +8 | Asia |
| 8 | Chongqing | ZUCK:9:CN | C | Asia/Shanghai | +8 | Asia |
| 9 | Taipei | RCTP:9:TW | C | Asia/Taipei | +8 | Asia |
| 10 | Singapore | WSSS:9:SG | C | Asia/Singapore | +8 | Asia |
| 11 | Kuala Lumpur | WMKK:9:MY | C | Asia/Kuala_Lumpur | +8 | Asia |
| 12 | Jakarta | WIII:9:ID | C | Asia/Jakarta | +7 | Asia |
| 13 | Lucknow | VILK:9:IN | C | Asia/Kolkata | +5.5 | Asia |
| 14 | Moscow | UUWW:9:RU | C | Europe/Moscow | +3 | Europa |
| 15 | Ankara | LTAC:9:TR | C | Europe/Istanbul | +3 | Europa |
| 16 | Istanbul | LTFM:9:TR | C | Europe/Istanbul | +3 | Europa |
| 17 | Tel Aviv | LLBG:9:IL | C | Asia/Jerusalem | +3 | Europa |
| 18 | Helsinki | EFHK:9:FI | C | Europe/Helsinki | +3 | Europa |
| 19 | Warsaw | EPWA:9:PL | C | Europe/Warsaw | +2 | Europa |
| 20 | Paris | LFPG:9:FR | C | Europe/Paris | +2 | Europa |
| 21 | Amsterdam | EHAM:9:NL | C | Europe/Amsterdam | +2 | Europa |
| 22 | Madrid | LEMD:9:ES | C | Europe/Madrid | +2 | Europa |
| 23 | Milan | LIMC:9:IT | C | Europe/Rome | +2 | Europa |
| 24 | London | EGLC:9:GB | C | Europe/London | +1 | Europa |
| 25 | Sao Paulo | SBGR:9:BR | C | America/Sao_Paulo | -3 | Americas |
| 26 | Buenos Aires | SAEZ:9:AR | C | America/Argentina/Buenos_Aires | -3 | Americas |
| 27 | Toronto | CYYZ:9:CA | C | America/Toronto | -4 | Americas |
| 28 | NYC | KLGA:9:US | **F** | America/New_York | -4 | Americas |
| 29 | Panama | MPTO:9:PA | C | America/Panama | -5 | Americas |
| 30 | Chicago | KORD:9:US | **F** | America/Chicago | -5 | Americas |
| 31 | Mexico City | MMMX:9:MX | C | America/Mexico_City | -6 | Americas |
| 32 | Denver | KDEN:9:US | **F** | America/Denver | -6 | Americas |
| 33 | Miami | KMIA:9:US | **F** | America/New_York | -4 | Americas |
| 34 | Seattle | KSEA:9:US | **F** | America/Los_Angeles | -7 | Americas |

### Cidades em Fahrenheit (EUA)

5 cidades usam Fahrenheit: **NYC**, **Chicago**, **Denver**, **Miami**, **Seattle**. Todas sao cidades dos Estados Unidos. As demais 29 cidades usam Celsius.

### Distribuicao por regiao

| Regiao | Qtd | Cidades |
|---|---|---|
| **Asia** | 13 | Wellington, Seoul, Tokyo, Busan, Shanghai, Hong Kong, Beijing, Chongqing, Taipei, Singapore, Kuala Lumpur, Jakarta, Lucknow |
| **Europa** | 11 | Moscow, Ankara, Istanbul, Tel Aviv, Helsinki, Warsaw, Paris, Amsterdam, Madrid, Milan, London |
| **Americas** | 10 | Sao Paulo, Buenos Aires, Toronto, NYC, Panama, Chicago, Mexico City, Denver, Miami, Seattle |

> Nota: Wellington esta classificada como "Oceania" no config mas agrupada com Asia por proximidade de fuso.

---

## 7. Dashboard (Frontend)

O dashboard e um SPA (Single Page Application) em um unico arquivo HTML (`frontend/index.html`, ~2267 linhas) com tema escuro (dark mode) e design dourado/preto.

### 7.1 Tela Principal (Grid de Cidades)

**O que mostra em cada card**:
- Nome da cidade e unidade (ex: "London (C)")
- Temperatura atual em destaque grande
- Seta de tendencia: verde para cima (subindo), vermelha para baixo (descendo), dourada lateral (estavel)
- Badge de status: "Subindo", "Perto do pico", "Pico atingido", "Descendo", "Sem dados"
- Temperatura de pico do dia + horario local
- Horario do pico em BRT (UTC-3)
- Numero de leituras coletadas
- Previsao de maxima (se disponivel) com horario de captura

**Filtros disponiveis**:
- **Por regiao**: Todas, Oceania, Asia, Europa, Americas
- **Ordenacao**: Alfabetica, temperatura (maior/menor), fuso horario

**Auto-refresh**: A cada 5 minutos (300.000 ms) recarrega todos os dados automaticamente.

### 7.2 Tela de Detalhe da Cidade

Ao clicar em um card, o grid e substituido pela tela de detalhe com:

**Grafico de curva de temperatura (Chart.js)**:
- Eixo X: horario local (leituras hora a hora)
- Eixo Y: temperatura
- Linha dourada com area preenchida em gradiente
- Ponto verde = pico do dia
- Ponto dourado claro = ultima leitura (atual)
- Linha horizontal tracejada cinza = previsao de maxima
- Linha vertical tracejada cinza = horario do pico medio (ultimos 7 dias)
- Tooltip com data, horario local e temperatura

**Info abaixo do grafico**:
- Temperatura atual
- Pico do dia + horario
- Temperatura minima
- Pico medio dos ultimos 7 dias
- Numero de leituras
- Previsao de maxima vs maxima real (diferenca em cores)

**Odds Polymarket**:
- Tabela de odds por faixa de temperatura
- Preco de compra (probabilidade)
- Volume negociado

**Previsoes dos 6 modelos com ranking dinamico**:
- Cada modelo com sua previsao para o dia
- Top 3 destacados com cores de medalha (ouro, prata, bronze)
- Melhor modelo destacado

**Historico de previsoes (30 dias)**:
- Tabela com data, previsao de cada modelo, maxima real e status (FINAL ou em andamento)
- Acertos marcados com check verde
- Ranking de acuracia com porcentagem de acerto por modelo
- Medalhas para os 3 melhores modelos

### 7.3 Secao de Apostas

**Como registrar aposta**:
1. Selecionar cidade no dropdown
2. Preencher: data alvo, faixa, tipo (compra/venda), odd e valor
3. Clicar em "Registrar Aposta"
4. A aposta e salva no Supabase com status "aguardando"

**Como resolver (ganhou/perdeu)**:
- Na lista de apostas, cada aposta pendente tem botoes "Ganhou" e "Perdeu"
- Ao clicar, atualiza o resultado e calcula o P&L automaticamente

**Metricas de P&L**:
- Total de apostas
- Ganhou / Perdeu / Aguardando
- P&L total
- Win rate (%)
- ROI (%)

---

## 8. Coleta de Dados (Backend)

### 8.1 Coleta de Leituras (`main.py`)

**Frequencia**: A cada 30 minutos (via `agendar.py` ou thread no Railway) + a cada 6 horas (via GitHub Actions).

**O que coleta por cidade**:
1. **Leituras WU**: todas as observacoes do dia local via `ColetorWU.coletar_dia()`
2. **Previsao de maxima**: via `ColetorWU.coletar_previsao()` (so se ainda nao tem previsao pro dia)
3. **Odds Polymarket**: via `PolymarketConector.buscar_odds()` para hoje e amanha

**Como trata fusos horarios**:
- Cada cidade tem um `fuso_offset` fixo (ex: Tokyo = +9, NYC = -4)
- O sistema calcula o dia local atual da cidade: `data_local = (UTC + offset).date()`
- Leituras do WU sao filtradas para incluir apenas o dia LOCAL correto
- Para fusos positivos, pede dia anterior UTC; para negativos, dia seguinte UTC

**Fluxo por cidade**:
1. Limpa leituras anteriores do dia (evita duplicatas)
2. Busca leituras via WU API
3. Salva cada leitura no Supabase
4. Calcula pico e status (subindo/descendo)
5. Captura previsao de maxima (se nao existir)
6. Busca odds da Polymarket (hoje e amanha)
7. Salva odds no Supabase

### 8.2 Coleta de Modelos (`coletar_modelos.py`)

**6 modelos via Open-Meteo**: ECMWF, GFS, ICON, UKMO, JMA, GEM.

**Frequencia**: A cada 1 hora (via GitHub Actions). Modelos meteorologicos atualizam a cada 6 horas, mas coletando a cada 1 hora garante a previsao mais recente possivel.

**Funcionamento**:
1. Carrega as 34 cidades do config
2. Para cada cidade, calcula a data local usando o fuso_offset
3. Para cada combinacao cidade x modelo (34 x 6 = 204 requests), busca a previsao via Open-Meteo
4. Usa semaforo de 10 requests paralelas para nao sobrecarregar a API
5. Converte Celsius para Fahrenheit quando necessario
6. Salva todos os registros no Supabase via batch insert

**Mantem historico**: NAO deleta previsoes anteriores. Isso permite analisar como a previsao evolui ao longo do dia (ex: previsao das 6h vs previsao das 12h).

### 8.3 Previsao 6h Local (`capturar_previsao.py`)

**O que faz**: Captura a previsao de temperatura maxima do Weather Underground Forecast as 6h da manha local de cada cidade. Essa previsao "de manha cedo" e importante porque e feita antes do dia esquentar.

**Gatilhos por fuso horario** (13 horarios UTC):

| Hora UTC | 6h local de... | Cidades |
|---|---|---|
| 18:00 | Wellington | 1 cidade |
| 21:00 | Seoul, Tokyo, Busan | 3 cidades |
| 22:00 | Shanghai, HK, Beijing, Chongqing, Taipei, Singapore, KL | 7 cidades |
| 23:00 | Jakarta | 1 cidade |
| 01:00 | Lucknow | 1 cidade |
| 03:00 | Moscow, Ankara, Istanbul, Tel Aviv, Helsinki | 5 cidades |
| 04:00 | Warsaw, Paris, Amsterdam, Madrid, Milan | 5 cidades |
| 05:00 | London | 1 cidade |
| 09:00 | Sao Paulo, Buenos Aires | 2 cidades |
| 10:00 | Toronto, NYC, Miami | 3 cidades |
| 11:00 | Panama, Chicago | 2 cidades |
| 12:00 | Mexico City, Denver | 2 cidades |
| 13:00 | Seattle | 1 cidade |

**Logica**: 
- Detecta a hora UTC atual
- Verifica se alguma cidade esta com 6h local nesse momento
- So captura previsao se ainda nao existir para aquela cidade/data no Supabase
- So salva a previsao do dia atual local (nao D+1)

### 8.4 Alertas Telegram (`alerta_telegram.py`)

**Quando dispara**: As **13h local** de cada cidade (1 hora antes do pico estimado de 14h). O script roda a cada hora e verifica se alguma cidade esta entre 13:00 e 13:30 local. A janela de 30 minutos evita alertas duplicados.

**Ranking dinamico (calcula em tempo real)**:
1. Busca previsoes dos ultimos 30 dias no Supabase (`we_modelos`)
2. Busca leituras reais (`we_leituras`)
3. Calcula maxima real por dia
4. Para cada dia finalizado (antes de hoje): compara previsao arredondada com maxima real arredondada
5. Conta acertos por modelo
6. Retorna: melhor modelo, percentual de acerto, top 3
7. Fallback: se nao ha dados, usa ICON como padrao

**Formato da mensagem** (exemplo):
```
ALERTA: London — pico em ~1h

Pico previsto: ~14:00 local / 12:00 BRT
Temp atual: 18 C

Melhor modelo (30d): ECMWF (acerto 45%)
Ranking: #1 ECMWF | #2 ICON | #3 GFS
Previsao: 21 C
Consenso: 21 C (4/6 modelos)

  ECMWF: 21 C <<<
  GFS: 20 C
  ICON: 21 C
  UKMO: 22 C
  JMA: 20 C
  GEM: 21 C

Odd Polymarket 21 C: 35.2%
```

### 8.5 Limpeza (`limpar_antigos.py`)

**O que faz**: Remove registros com mais de 30 dias de todas as 4 tabelas de dados:
- `we_modelos`
- `we_leituras`
- `we_previsoes`
- `we_odds`

**Frequencia**: 1x por dia as 4h UTC (1h BRT).

**Logica**: Calcula `data_corte = hoje - 30 dias` e deleta todos os registros onde `data_alvo < data_corte`.

**Nota**: A tabela `we_apostas` NAO e limpa — o historico de apostas e mantido indefinidamente.

---

## 9. Banco de Dados (Supabase)

### Schema completo de cada tabela

**`we_leituras`** — Leituras de temperatura hora a hora

| Campo | Tipo | Descricao |
|---|---|---|
| id | serial (PK) | Identificador unico |
| cidade | text | Nome da cidade |
| data_alvo | date | Data local da leitura |
| timestamp_wu | bigint | Timestamp Unix do WU |
| temperatura | float | Temperatura na leitura |
| hora_utc | text | Horario UTC (HH:MM) |
| hora_local | text | Horario local (HH:MM) |
| unidade | text | "C" ou "F" |

**`we_modelos`** — Previsoes de modelos meteorologicos

| Campo | Tipo | Descricao |
|---|---|---|
| id | serial (PK) | Identificador unico |
| cidade | text | Nome da cidade |
| data_alvo | date | Data alvo da previsao |
| modelo | text | Nome do modelo (ECMWF, GFS, etc.) |
| temp_max_prevista | float | Temperatura maxima prevista |
| unidade | text | "C" ou "F" |
| hora_captura | text | Quando foi capturada (ISO) |
| criado_em | timestamptz | Timestamp de insercao |

**`we_previsoes`** — Previsao de maxima (captura 6h local)

| Campo | Tipo | Descricao |
|---|---|---|
| id | serial (PK) | Identificador unico |
| cidade | text | Nome da cidade |
| data_alvo | date | Data alvo da previsao |
| temp_max_prevista | float | Temperatura maxima prevista |
| unidade | text | "C" ou "F" |
| hora_captura | text | Quando foi capturada (ISO) |
| criado_em | timestamptz | Timestamp de insercao |

**`we_odds`** — Odds Polymarket

| Campo | Tipo | Descricao |
|---|---|---|
| id | serial (PK) | Identificador unico |
| cidade | text | Nome da cidade |
| data_alvo | date | Data do contrato |
| faixa | text | Faixa de temperatura (ex: "20") |
| preco_compra | float | Probabilidade de mercado (0-1) |
| volume | float | Volume negociado (USD) |
| coletado_em | timestamptz | Quando foi coletada |

**`we_apostas`** — Apostas do usuario

| Campo | Tipo | Descricao |
|---|---|---|
| id | serial (PK) | Identificador unico |
| cidade | text | Nome da cidade |
| data_alvo | date | Data da aposta |
| faixa | text | Faixa apostada |
| tipo | text | "compra" ou "venda" |
| odd | float | Odd no momento da aposta |
| valor | float | Valor apostado (USD) |
| horario_registro | text | Quando foi registrada |
| resultado | text | "aguardando", "ganhou", "perdeu" |
| pnl | float | Lucro/prejuizo (positivo ou negativo) |

### Volume estimado de dados

- **we_leituras**: ~34 cidades x ~48 leituras/dia x 30 dias = ~48.960 registros
- **we_modelos**: ~34 cidades x 6 modelos x 24 coletas/dia x 30 dias = ~146.880 registros
- **we_odds**: ~34 cidades x ~10 faixas x 4 coletas/dia x 30 dias = ~40.800 registros
- **we_previsoes**: ~34 cidades x 30 dias = ~1.020 registros
- **Total estimado**: ~237.660 registros ativos (limpos a cada 30 dias)

---

## 10. Polymarket — Como Funciona

### Tipos de contrato de temperatura

A Polymarket cria diariamente contratos de aposta sobre a temperatura maxima de cada uma das 34 cidades. O titulo do contrato segue o padrao:

> "What will be the highest temperature in [City] on [Date]?"

Cada contrato tem multiplas faixas de temperatura. O usuario aposta em qual faixa a temperatura maxima real cairia.

### Faixas Celsius (1 C) vs Fahrenheit (2 F)

- **Celsius**: faixas de **1 grau** — ex: "20 C", "21 C", "22 C", "23 C or higher", "18 C or below"
- **Fahrenheit**: faixas de **2 graus** (range) — ex: "between 68-69 F", "between 70-71 F", "72 F or higher"

### Como a Polymarket resolve

1. O dia termina (meia-noite local da cidade)
2. A Polymarket consulta o **Weather Underground History** para aquela estacao naquele dia
3. A maior temperatura registrada no dia determina a faixa vencedora
4. Quem apostou na faixa correta recebe $1 por share; quem errou perde o investimento

### Conceito de edge e value betting

**Edge** = diferenca entre a probabilidade real (estimada pelo sistema) e a probabilidade do mercado (odds da Polymarket).

Exemplo:
- O melhor modelo (ECMWF) preve 21 C para London
- Consenso: 4 de 6 modelos concordam em 21 C
- Odd no mercado: 35% (preco = $0.35)
- Se a confianca historica do ECMWF pra London e 45%, ha um edge de +10%
- Nesse caso, comprar a $0.35 tem valor esperado positivo

O sistema ajuda a identificar esses edges automaticamente, combinando ranking de acuracia, consenso entre modelos e odds do mercado.

---

## 11. Modelo de Acuracia

### Como o ranking e calculado

O ranking de acuracia e calculado **dinamicamente** com base nos ultimos 30 dias, tanto no backend (alertas Telegram) quanto no frontend (dashboard). A logica e identica em ambos:

1. **Buscar dados**: previsoes dos 6 modelos (`we_modelos`) + leituras reais (`we_leituras`) dos ultimos 30 dias
2. **Calcular maxima real**: para cada dia, encontrar a maior temperatura registrada nas leituras
3. **Filtrar dias finalizados**: so considerar dias anteriores a hoje (dia em andamento nao conta)
4. **Comparar previsoes**: para cada modelo em cada dia, verificar se `round(previsao) == round(maxima_real)`
5. **Contar acertos**: somar acertos e total de previsoes por modelo
6. **Ordenar**: ranking decrescente por numero de acertos

### Acerto exato (arredondado)

O criterio de acerto e **arredondamento para o inteiro mais proximo**:
- Previsao: 21.3 C -> arredonda para 21
- Maxima real: 21.7 C -> arredonda para 22
- Resultado: **ERROU** (21 != 22)

Esse criterio e rigoroso e alinhado com como a Polymarket resolve (faixas de 1 grau).

### Top 3 por cidade (ouro, prata, bronze)

O dashboard exibe os 3 melhores modelos com medalhas:
- **Ouro** (1o lugar): cor dourada (#d4a017)
- **Prata** (2o lugar): cor cinza (#c0c0c0)
- **Bronze** (3o lugar): cor cobre (#cd7f32)

Cada modelo recebe porcentagem de acerto e contagem (ex: "ECMWF: 45% (9/20)").

### Por que cada cidade tem seu melhor modelo

Modelos meteorologicos tem diferentes resolucoes espaciais, parametrizacoes fisicas e dados de entrada. Por exemplo:
- **ECMWF** (europeu): tende a ser mais preciso para Europa e latitudes medias
- **JMA** (japones): pode ter melhor performance para Asia-Pacifico
- **GFS** (americano): forte em Americas do Norte
- **ICON** (alemao): boa resolucao para Europa central

O ranking dinamico automaticamente descobre qual modelo funciona melhor para cada cidade sem precisar de regras manuais.

---

## 12. Como Usar o Sistema

### 12.1 Rotina Diaria

**Passo a passo do que fazer cada dia**:

1. **De manha (8-9h BRT)**: Abrir o dashboard e verificar cidades da Asia/Oceania (ja com dia finalizado ou perto do fim)
2. **Ao longo do dia**: Verificar alertas no Telegram — eles chegam 1h antes do pico de cada grupo de cidades
3. **Quando receber alerta**: Avaliar se ha edge (previsao do melhor modelo vs odds do mercado)
4. **Se houver edge**: Registrar aposta no dashboard e executar na Polymarket
5. **Final do dia**: Verificar resultados das apostas e resolver (ganhou/perdeu)

**Tabela de horarios de pico em BRT (UTC-3)**:

| Pico local ~14h | Hora BRT | Cidades |
|---|---|---|
| 14:00 NZT | 23:00 BRT (dia anterior) | Wellington |
| 14:00 KST/JST | 02:00 BRT | Seoul, Tokyo, Busan |
| 14:00 CST/SGT | 03:00 BRT | Shanghai, HK, Beijing, Chongqing, Taipei, Singapore, KL |
| 14:00 WIB | 04:00 BRT | Jakarta |
| 14:00 IST | 05:30 BRT | Lucknow |
| 14:00 MSK/TRT | 08:00 BRT | Moscow, Ankara, Istanbul, Tel Aviv, Helsinki |
| 14:00 CET | 09:00 BRT | Warsaw, Paris, Amsterdam, Madrid, Milan |
| 14:00 BST | 10:00 BRT | London |
| 14:00 BRT | 14:00 BRT | Sao Paulo, Buenos Aires |
| 14:00 EDT | 15:00 BRT | Toronto, NYC, Miami |
| 14:00 CDT/EST | 16:00 BRT | Panama, Chicago |
| 14:00 CST/MDT | 17:00 BRT | Mexico City, Denver |
| 14:00 PDT | 18:00 BRT | Seattle |

### 12.2 Como Apostar

**Identificar edge**:
1. Olhar a previsao do melhor modelo (1o no ranking)
2. Verificar consenso (quantos modelos concordam)
3. Comparar com a odd do mercado na Polymarket
4. Se a previsao tem confianca alta e a odd esta "barata", ha edge

**Registrar no dashboard**:
1. Ir na secao "Apostas" no final da pagina
2. Preencher cidade, data, faixa, tipo (compra), odd e valor
3. Clicar "Registrar"

**Acompanhar resultado**:
1. Aguardar o dia finalizar (meia-noite local da cidade)
2. Verificar a temperatura maxima real no dashboard
3. Resolver a aposta como "Ganhou" ou "Perdeu"
4. O P&L e calculado automaticamente

---

## 13. Manutencao

### Como adicionar nova cidade

1. Editar `config/cidades.json` — adicionar novo objeto com:
   - `nome`, `slug_poly`, `estacao_wu`, `url_history`, `unidade`, `fuso`, `fuso_offset`, `regiao`, `latitude`, `longitude`
2. Editar `frontend/index.html` — adicionar na lista `CIDADES` do JavaScript
3. Editar `capturar_previsao.py` — adicionar no dicionario `GATILHOS_UTC` na hora UTC correta
4. Editar `.github/workflows/previsao_6h.yml` — adicionar cron se necessario (novo fuso)
5. Fazer deploy do frontend: `firebase deploy --only hosting`
6. Commit e push para atualizar GitHub Actions

### Como atualizar o deploy

**Firebase (frontend)**:
```bash
firebase deploy --only hosting
```

**Railway (backend)**:
- Push para o branch principal — Railway faz deploy automatico via Git
- Ou via dashboard da Railway

### Como forcar coleta manual

**Coleta completa (leituras + odds)**:
```bash
py agendar.py --agora
```

**Coleta de modelos**:
```bash
py coletar_modelos.py
```

**Captura de previsao (todas as cidades)**:
```bash
py capturar_previsao.py --todas
```

**Alertas Telegram (forcar verificacao)**:
```bash
py alerta_telegram.py
```

**Limpeza manual**:
```bash
py limpar_antigos.py
```

**Via GitHub Actions**: cada workflow tem `workflow_dispatch` habilitado, permitindo execucao manual pelo painel do GitHub.

### Onde ver logs

- **Local**: arquivo `logs/weather_edge.log`
- **GitHub Actions**: aba "Actions" no repositorio -> selecionar workflow -> selecionar run -> ver output
- **Railway**: dashboard da Railway -> aba "Logs"
- **Supabase**: dashboard do Supabase -> aba "Logs" (queries SQL)

---

## 14. Custos

| Servico | Plano | Custo | Notas |
|---|---|---|---|
| **Firebase Hosting** | Spark (gratuito) | $0/mes | 10 GB transferencia, 1 GB armazenamento |
| **Railway** | Trial / Hobby | $0-5/mes | Trial gratuito com limites; Hobby $5/mes |
| **Supabase** | Free | $0/mes | 500 MB banco, 50k req/dia, 2 GB transferencia |
| **GitHub Actions** | Free (repo publico) | $0/mes | Ilimitado para repos publicos; 2.000 min/mes para privados |
| **Weather Underground API** | Gratuita | $0/mes | API interna, sem cobranca aparente |
| **Open-Meteo API** | Gratuita | $0/mes | API publica sem autenticacao |
| **Polymarket Gamma API** | Gratuita | $0/mes | API publica sem autenticacao |
| **Telegram Bot API** | Gratuita | $0/mes | Sem limites praticos para uso pessoal |

**Custo total estimado**: **$0 a $5/mes** dependendo do plano Railway.

**Risco de custos**: Se o repositorio for privado, os ~5.000 minutos estimados de GitHub Actions por mes excedem os 2.000 minutos gratuitos. Solucao: manter o repositorio publico (minutos ilimitados) ou reduzir frequencia de coleta de modelos e alertas.
