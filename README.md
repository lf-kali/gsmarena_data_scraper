<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>GSMArena Scraper — Documentação</title>
</head>
<body>

<h1>GSMArena Scraper — Documentação Completa</h1>

<blockquote>
  <p>Ferramenta de raspagem de dados do site <a href="https://www.gsmarena.com">GSMArena.com</a> escrita em Python. Coleta informações de todas as marcas e modelos de celulares e salva os dados em arquivos <code>.json</code> organizados por marca.</p>
</blockquote>

<hr>

<h2>Índice</h2>

<ol>
  <li><a href="#visao-geral">Visão Geral</a></li>
  <li><a href="#requisitos">Requisitos</a></li>
  <li><a href="#instalacao">Instalação</a></li>
  <li><a href="#uso-basico">Uso Básico</a></li>
  <li><a href="#argumentos">Argumentos da Linha de Comando</a></li>
  <li><a href="#exemplos">Exemplos de Uso</a></li>
  <li><a href="#estrutura-de-saida">Estrutura de Saída</a></li>
  <li><a href="#formato-json">Formato dos Arquivos JSON</a>
    <ul>
      <li><a href="#brands-json">brands.json</a></li>
      <li><a href="#marca-json">brands/{marca}.json</a></li>
    </ul>
  </li>
  <li><a href="#como-funciona">Como o Scraper Funciona</a></li>
  <li><a href="#boas-praticas">Boas Práticas e Limitações</a></li>
  <li><a href="#resolucao-de-problemas">Resolução de Problemas</a></li>
</ol>

<hr>

<h2 id="visao-geral">1. Visão Geral</h2>

<p>O <strong>GSMArena Scraper</strong> percorre automaticamente o site GSMArena em três etapas:</p>

<ol>
  <li>Coleta a lista completa de todas as marcas disponíveis em <code>gsmarena.com/makers.php3</code>.</li>
  <li>Para cada marca, navega por todas as páginas de listagem (com paginação automática) e coleta os dados básicos de cada modelo.</li>
  <li>Para cada modelo, acessa a página individual de especificações e extrai todas as informações técnicas disponíveis.</li>
</ol>

<p>Os dados são salvos em uma estrutura de pastas organizada: um arquivo <code>brands.json</code> global e um arquivo <code>.json</code> por marca dentro da pasta <code>brands/</code>.</p>

<p>Características principais:</p>

<ul>
  <li><strong>Paginação automática</strong> — navega por todas as páginas de listagem de cada marca sem configuração manual.</li>
  <li><strong>Retomada de execução</strong> — se o scraper for interrompido, ao rodar novamente ele pula os dispositivos já coletados.</li>
  <li><strong>Retry com backoff exponencial</strong> — em caso de erro de rede, tenta novamente com espera crescente antes de desistir.</li>
  <li><strong>Delay configurável</strong> — pausa entre requisições para não sobrecarregar os servidores.</li>
  <li><strong>Salvamento incremental</strong> — salva os dados a cada 10 dispositivos para evitar perda de progresso.</li>
</ul>

<hr>

<h2 id="requisitos">2. Requisitos</h2>

<h3>Python</h3>

<p>Versão mínima requerida: <strong>Python 3.10</strong> (o script usa anotações de tipo modernas como <code>list[dict]</code>).</p>

<p>Verifique sua versão com:</p>

<pre><code>python --version
</code></pre>

<h3>Dependências externas</h3>

<table>
  <thead>
    <tr>
      <th>Biblioteca</th>
      <th>Versão mínima</th>
      <th>Finalidade</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>requests</code></td>
      <td>2.28+</td>
      <td>Realiza as requisições HTTP ao GSMArena</td>
    </tr>
    <tr>
      <td><code>beautifulsoup4</code></td>
      <td>4.12+</td>
      <td>Faz o parsing do HTML das páginas</td>
    </tr>
    <tr>
      <td><code>lxml</code></td>
      <td>4.9+</td>
      <td>Parser HTML de alto desempenho usado pelo BeautifulSoup</td>
    </tr>
  </tbody>
</table>

<h3>Dependências da biblioteca padrão (já inclusas no Python)</h3>

<p><code>argparse</code>, <code>json</code>, <code>os</code>, <code>re</code>, <code>time</code>, <code>logging</code>, <code>pathlib</code>, <code>typing</code></p>

<hr>

<h2 id="instalacao">3. Instalação</h2>

<h3>Passo 1 — Clone ou baixe o script</h3>

<p>Salve o arquivo <code>gsmarena_scraper.py</code> em uma pasta de sua escolha, por exemplo:</p>

<pre><code>~/projetos/gsmarena/
└── gsmarena_scraper.py
</code></pre>

<h3>Passo 2 — Crie um ambiente virtual (recomendado)</h3>

<p>Usar um ambiente virtual evita conflitos com outras bibliotecas instaladas no sistema.</p>

<pre><code># Criar o ambiente virtual
python -m venv .venv

# Ativar no Linux / macOS
source .venv/bin/activate

# Ativar no Windows (PowerShell)
.venv\Scripts\Activate.ps1
</code></pre>

<h3>Passo 3 — Instale as dependências</h3>

<pre><code>pip install requests beautifulsoup4 lxml
</code></pre>

<p>Ou, se preferir criar um arquivo <code>requirements.txt</code>:</p>

<pre><code>requests>=2.28
beautifulsoup4>=4.12
lxml>=4.9
</code></pre>

<pre><code>pip install -r requirements.txt
</code></pre>

<h3>Passo 4 — Confirme a instalação</h3>

<pre><code>python -c "import requests, bs4, lxml; print('Tudo OK!')"
</code></pre>

<p>Se a saída for <code>Tudo OK!</code>, você está pronto para usar o scraper.</p>

<hr>

<h2 id="uso-basico">4. Uso Básico</h2>

<p>Execute o script a partir do terminal, dentro da pasta onde ele está salvo:</p>

<pre><code>python gsmarena_scraper.py
</code></pre>

<p>Sem nenhum argumento, o scraper irá:</p>

<ol>
  <li>Buscar <strong>todas</strong> as marcas disponíveis no GSMArena (100+ marcas).</li>
  <li>Para cada marca, coletar <strong>todos</strong> os modelos e suas especificações completas.</li>
  <li>Salvar os resultados na pasta <code>output/</code> (criada automaticamente no diretório atual).</li>
</ol>

<blockquote>
  <p><strong>Atenção:</strong> Raspar o catálogo completo pode levar <strong>várias horas</strong> (ou dias), pois há mais de 10.000 modelos. Recomenda-se começar com uma ou poucas marcas usando o argumento <code>--brands</code> para testar o funcionamento.</p>
</blockquote>

<hr>

<h2 id="argumentos">5. Argumentos da Linha de Comando</h2>

<table>
  <thead>
    <tr>
      <th>Argumento</th>
      <th>Tipo</th>
      <th>Padrão</th>
      <th>Descrição</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>--brands</code></td>
      <td><code>str</code> (um ou mais)</td>
      <td>Todas as marcas</td>
      <td>Filtra quais marcas serão raspadas. Aceita o <em>slug</em> da marca (nome em minúsculas, com hífens). Exemplo: <code>samsung</code>, <code>apple</code>, <code>nothing</code>.</td>
    </tr>
    <tr>
      <td><code>--max-devices</code></td>
      <td><code>int</code></td>
      <td>Sem limite</td>
      <td>Limita o número de dispositivos coletados por marca. Ideal para testes rápidos.</td>
    </tr>
    <tr>
      <td><code>--delay</code></td>
      <td><code>float</code></td>
      <td><code>2.0</code></td>
      <td>Tempo de espera em segundos entre cada requisição HTTP. Valores menores que <code>1.0</code> podem causar bloqueio temporário pelo site.</td>
    </tr>
    <tr>
      <td><code>--output</code></td>
      <td><code>str</code></td>
      <td><code>./output</code></td>
      <td>Caminho para a pasta onde os arquivos JSON serão salvos. Criada automaticamente se não existir.</td>
    </tr>
    <tr>
      <td><code>--skip-specs</code></td>
      <td>flag</td>
      <td><code>False</code></td>
      <td>Se presente, pula a raspagem das páginas individuais de cada dispositivo. Salva apenas a lista de modelos com dados básicos (nome, URL, miniatura).</td>
    </tr>
  </tbody>
</table>

<h3>Como descobrir o slug de uma marca</h3>

<p>O slug é a parte do nome da marca que aparece na URL do GSMArena. Por exemplo:</p>

<ul>
  <li><code>https://www.gsmarena.com/<strong>samsung</strong>-phones-9.php</code> → slug: <code>samsung</code></li>
  <li><code>https://www.gsmarena.com/<strong>sony_ericsson</strong>-phones-19.php</code> → slug: <code>sony_ericsson</code></li>
  <li><code>https://www.gsmarena.com/<strong>nothing</strong>-phones-128.php</code> → slug: <code>nothing</code></li>
</ul>

<p>Você também pode consultar o campo <code>"slug"</code> no arquivo <code>brands.json</code> gerado na primeira execução.</p>

<hr>

<h2 id="exemplos">6. Exemplos de Uso</h2>

<h3>Exemplo 1 — Teste rápido com uma marca e poucos dispositivos</h3>

<p>Ideal para verificar se o scraper está funcionando corretamente antes de uma coleta completa.</p>

<pre><code>python gsmarena_scraper.py --brands nothing --max-devices 5
</code></pre>

<p>Isso irá raspar apenas os 5 primeiros dispositivos da marca <em>Nothing</em> e salvar em <code>output/</code>.</p>

<h3>Exemplo 2 — Raspar múltiplas marcas específicas</h3>

<pre><code>python gsmarena_scraper.py --brands samsung apple google oneplus
</code></pre>

<h3>Exemplo 3 — Raspar tudo, com delay reduzido e pasta personalizada</h3>

<pre><code>python gsmarena_scraper.py --delay 1.5 --output ./dados_gsmarena
</code></pre>

<h3>Exemplo 4 — Coletar apenas a lista de modelos sem especificações detalhadas</h3>

<p>Muito mais rápido. Útil se você só precisa de nomes, URLs e miniaturas dos modelos.</p>

<pre><code>python gsmarena_scraper.py --brands xiaomi --skip-specs
</code></pre>

<h3>Exemplo 5 — Retomar uma coleta interrompida</h3>

<p>Simplesmente rode o mesmo comando novamente. O scraper detecta automaticamente quais dispositivos já foram salvos e os pula.</p>

<pre><code>python gsmarena_scraper.py --brands samsung
</code></pre>

<h3>Exemplo 6 — Coleta completa com log salvo em arquivo</h3>

<pre><code>python gsmarena_scraper.py 2>&amp;1 | tee gsmarena_log.txt
</code></pre>

<hr>

<h2 id="estrutura-de-saida">7. Estrutura de Saída</h2>

<p>Após a execução, a pasta de saída terá a seguinte estrutura:</p>

<pre><code>output/
├── brands.json           ← Lista global de todas as marcas
└── brands/
    ├── samsung.json      ← Todos os modelos Samsung com especificações
    ├── apple.json
    ├── nothing.json
    ├── xiaomi.json
    └── ...               ← Um arquivo por marca raspada
</code></pre>

<p>Os arquivos são escritos com indentação de 2 espaços e codificação <code>UTF-8</code>, garantindo compatibilidade com caracteres especiais de nomes de modelos internacionais.</p>

<hr>

<h2 id="formato-json">8. Formato dos Arquivos JSON</h2>

<h3 id="brands-json">8.1 — <code>brands.json</code></h3>

<p>Contém um <strong>array</strong> com todas as marcas encontradas no GSMArena. Cada objeto representa uma marca.</p>

<pre><code>[
  {
    "brand_id": "128",
    "name": "Nothing",
    "slug": "nothing",
    "url": "https://www.gsmarena.com/nothing-phones-128.php",
    "device_count": 15
  },
  {
    "brand_id": "9",
    "name": "Samsung",
    "slug": "samsung",
    "url": "https://www.gsmarena.com/samsung-phones-9.php",
    "device_count": 1454
  }
]
</code></pre>

<h4>Campos de cada marca</h4>

<table>
  <thead>
    <tr>
      <th>Campo</th>
      <th>Tipo</th>
      <th>Descrição</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>brand_id</code></td>
      <td><code>string</code></td>
      <td>Identificador numérico único da marca no GSMArena</td>
    </tr>
    <tr>
      <td><code>name</code></td>
      <td><code>string</code></td>
      <td>Nome oficial da marca conforme exibido no site</td>
    </tr>
    <tr>
      <td><code>slug</code></td>
      <td><code>string</code></td>
      <td>Versão do nome usada nas URLs do GSMArena (minúsculas, com hífens/underscores)</td>
    </tr>
    <tr>
      <td><code>url</code></td>
      <td><code>string</code></td>
      <td>URL completa da página de listagem da marca</td>
    </tr>
    <tr>
      <td><code>device_count</code></td>
      <td><code>int</code></td>
      <td>Número de dispositivos listados para a marca no momento da coleta</td>
    </tr>
  </tbody>
</table>

<hr>

<h3 id="marca-json">8.2 — <code>brands/{marca}.json</code></h3>

<p>Cada arquivo de marca contém um <strong>objeto</strong> com dois campos principais: <code>brand</code> (os dados da marca) e <code>devices</code> (array de todos os dispositivos).</p>

<pre><code>{
  "brand": {
    "brand_id": "128",
    "name": "Nothing",
    "slug": "nothing",
    "url": "https://www.gsmarena.com/nothing-phones-128.php",
    "device_count": 15
  },
  "devices": [
    {
      "name": "Phone (4a)",
      "device_id": "14503",
      "url": "https://www.gsmarena.com/nothing_phone_(4a)_5g-14503.php",
      "thumbnail": "https://fdn2.gsmarena.com/vv/bigpic/nothing-phone-3a-new.jpg",
      "quick_spec": "Nothing Phone (4a) 5G Android smartphone. Announced Mar 2026.",
      "highlights": {},
      "specs": {
        "Network": {
          "Technology": "GSM / HSPA / LTE / 5G",
          "2G bands": "GSM 850 / 900 / 1800 / 1900",
          "3G bands": "HSDPA 800 / 850 / 900 / 1700(AWS) / 1900 / 2100",
          "4G bands": "LTE",
          "5G bands": "SA/NSA",
          "Speed": "HSPA, LTE, 5G"
        },
        "Launch": {
          "Announced": "2026, March 04",
          "Status": "Available. Released 2026, March 21"
        },
        "Body": {
          "Dimensions": "161.2 x 76.3 x 8.0 mm",
          "Weight": "190 g",
          "Build": "Glass front (Panda Glass), plastic frame, glass back",
          "SIM": "Nano-SIM + Nano-SIM"
        },
        "Display": {
          "Type": "AMOLED, 1B colors, 120Hz, HDR10+",
          "Size": "6.78 inches, 111.0 cm2",
          "Resolution": "1260 x 2800 pixels, 20:9 ratio (~453 ppi density)",
          "Protection": "Panda Glass, Mohs level 5"
        },
        "Platform": {
          "OS": "Android 16, Nothing OS 4.0",
          "Chipset": "Qualcomm SM7635-AC Snapdragon 7s Gen 4 (4 nm)",
          "CPU": "Octa-core (1x2.7 GHz Cortex-A720 & 3x2.4 GHz Cortex-A720 & 4x1.8 GHz Cortex-A520)",
          "GPU": "Adreno 810"
        },
        "Memory": {
          "Card slot": "No",
          "Internal": "256GB 8GB RAM, 256GB 12GB RAM"
        },
        "Main Camera": {
          "Triple": "50 MP, f/1.9, 24mm (wide), dual pixel PDAF, OIS",
          "Features": "LED flash, panorama, HDR",
          "Video": "4K@30fps, 1080p@30/60/120fps, gyro-EIS, OIS"
        },
        "Selfie camera": {
          "Single": "32 MP, f/2.2, 22mm (wide)",
          "Video": "1080p@30fps"
        },
        "Sound": {
          "Loudspeaker": "Yes, with stereo speakers",
          "3.5mm jack": "No"
        },
        "Comms": {
          "WLAN": "Wi-Fi 802.11 a/b/g/n/ac/6, dual-band",
          "Bluetooth": "5.4, A2DP, LE",
          "Positioning": "GPS, GALILEO, GLONASS, BDS, QZSS",
          "NFC": "Yes",
          "USB": "USB Type-C 2.0, OTG"
        },
        "Features": {
          "Sensors": "Fingerprint (under display, optical), accelerometer, gyro, proximity, compass"
        },
        "Battery": {
          "Type": "5080 mAh",
          "Charging": "50W wired, 50% in 19 min, 100% in 56 min"
        },
        "Misc": {
          "Colors": "Black; other colors",
          "Models": "A069"
        }
      }
    }
  ]
}
</code></pre>

<h4>Campos de cada dispositivo</h4>

<table>
  <thead>
    <tr>
      <th>Campo</th>
      <th>Tipo</th>
      <th>Descrição</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>name</code></td>
      <td><code>string</code></td>
      <td>Nome do modelo conforme listado na página da marca</td>
    </tr>
    <tr>
      <td><code>device_id</code></td>
      <td><code>string</code></td>
      <td>Identificador numérico único do dispositivo no GSMArena</td>
    </tr>
    <tr>
      <td><code>url</code></td>
      <td><code>string</code></td>
      <td>URL completa da página de especificações do dispositivo</td>
    </tr>
    <tr>
      <td><code>thumbnail</code></td>
      <td><code>string</code></td>
      <td>URL da imagem de miniatura do dispositivo</td>
    </tr>
    <tr>
      <td><code>quick_spec</code></td>
      <td><code>string</code></td>
      <td>Resumo textual retirado do atributo <code>title</code> da miniatura (inclui anúncio, tela, bateria)</td>
    </tr>
    <tr>
      <td><code>highlights</code></td>
      <td><code>object</code></td>
      <td>Destaques visuais da página de specs (tamanho de tela, câmera, RAM, bateria). Pode estar vazio em alguns modelos.</td>
    </tr>
    <tr>
      <td><code>specs</code></td>
      <td><code>object</code></td>
      <td>Especificações completas organizadas por seção (Network, Launch, Body, Display, Platform, Memory, Camera, Battery, etc.)</td>
    </tr>
  </tbody>
</table>

<h4>Seções comuns em <code>specs</code></h4>

<table>
  <thead>
    <tr>
      <th>Seção</th>
      <th>Descrição</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>Network</code></td>
      <td>Tecnologia de rede, bandas 2G/3G/4G/5G, velocidade</td>
    </tr>
    <tr>
      <td><code>Launch</code></td>
      <td>Data de anúncio e status de disponibilidade</td>
    </tr>
    <tr>
      <td><code>Body</code></td>
      <td>Dimensões, peso, material, tipo de SIM, proteção IP</td>
    </tr>
    <tr>
      <td><code>Display</code></td>
      <td>Tipo de painel, tamanho, resolução, proteção de tela</td>
    </tr>
    <tr>
      <td><code>Platform</code></td>
      <td>Sistema operacional, chipset, CPU, GPU</td>
    </tr>
    <tr>
      <td><code>Memory</code></td>
      <td>Slot para cartão, armazenamento interno e RAM</td>
    </tr>
    <tr>
      <td><code>Main Camera</code></td>
      <td>Configuração das câmeras traseiras, recursos e vídeo</td>
    </tr>
    <tr>
      <td><code>Selfie camera</code></td>
      <td>Câmera frontal e capacidade de vídeo</td>
    </tr>
    <tr>
      <td><code>Sound</code></td>
      <td>Alto-falante, entrada de áudio P2</td>
    </tr>
    <tr>
      <td><code>Comms</code></td>
      <td>Wi-Fi, Bluetooth, GPS, NFC, Rádio FM, USB</td>
    </tr>
    <tr>
      <td><code>Features</code></td>
      <td>Sensores disponíveis</td>
    </tr>
    <tr>
      <td><code>Battery</code></td>
      <td>Capacidade, tipo de carregamento, velocidade</td>
    </tr>
    <tr>
      <td><code>Misc</code></td>
      <td>Cores disponíveis, números de modelo</td>
    </tr>
    <tr>
      <td><code>Tests</code></td>
      <td>Resultados de testes de desempenho (quando disponíveis)</td>
    </tr>
  </tbody>
</table>

<blockquote>
  <p><strong>Nota:</strong> As seções presentes variam conforme o modelo. Dispositivos mais antigos ou com dados incompletos no GSMArena podem ter menos seções ou campos com valor <code>N/A</code>.</p>
</blockquote>

<hr>

<h2 id="como-funciona">9. Como o Scraper Funciona</h2>

<h3>Etapa 1 — Coleta de marcas (<code>scrape_brands</code>)</h3>

<p>Acessa <code>gsmarena.com/makers.php3</code> e extrai todas as marcas da tabela HTML principal. Para cada marca, captura o nome, slug, ID interno e quantidade de dispositivos.</p>

<h3>Etapa 2 — Lista de dispositivos (<code>scrape_device_list</code>)</h3>

<p>Acessa a página da marca e extrai os dispositivos listados dentro do elemento <code>&lt;div class="makers"&gt;</code>. Detecta automaticamente o botão "Next page" e navega por todas as páginas de paginação até esgotar os resultados.</p>

<h3>Etapa 3 — Especificações do dispositivo (<code>scrape_device_specs</code>)</h3>

<p>Acessa a página individual de cada dispositivo e extrai as tabelas de especificações dentro do elemento <code>&lt;div id="specs-list"&gt;</code>. Cada tabela corresponde a uma seção (ex: <em>Network</em>, <em>Display</em>). As linhas da tabela seguem o padrão:</p>

<ul>
  <li>Coluna 1 (<code>td.ttl</code>): nome da especificação (ex: <em>Resolution</em>)</li>
  <li>Coluna 2 (<code>td.nfo</code>): valor da especificação (ex: <em>1260 x 2800 pixels</em>)</li>
</ul>

<h3>Mecanismo de retry</h3>

<p>Cada requisição HTTP tem até <strong>3 tentativas</strong>. Se uma tentativa falha, o scraper aguarda:</p>

<ul>
  <li>Tentativa 1 → falhou → aguarda <code>delay × 2</code> segundos</li>
  <li>Tentativa 2 → falhou → aguarda <code>delay × 4</code> segundos</li>
  <li>Tentativa 3 → falhou → registra o erro e continua para o próximo item</li>
</ul>

<h3>Mecanismo de resume</h3>

<p>Antes de iniciar a raspagem de uma marca, o scraper verifica se o arquivo <code>brands/{marca}.json</code> já existe. Se existir, carrega os IDs dos dispositivos já salvos e pula aqueles que já foram coletados, adicionando apenas os novos ao final.</p>

<hr>

<h2 id="boas-praticas">10. Boas Práticas e Limitações</h2>

<h3>Boas práticas</h3>

<ul>
  <li><strong>Use <code>--delay 2.0</code> ou maior</strong>. Valores abaixo de 1 segundo podem fazer seu IP ser temporariamente bloqueado pelo GSMArena.</li>
  <li><strong>Teste com <code>--max-devices 5</code> antes de uma coleta completa</strong> para garantir que o script está funcionando e os arquivos estão sendo gerados corretamente.</li>
  <li><strong>Execute preferencialmente com um único processo</strong>. Rodar múltiplas instâncias em paralelo aumenta o risco de bloqueio.</li>
  <li><strong>Deixe o terminal aberto ou use <code>nohup</code></strong> para coletas longas, evitando que a sessão seja encerrada:</li>
</ul>

<pre><code>nohup python gsmarena_scraper.py --output ./dados &gt; gsmarena.log 2&gt;&amp;1 &amp;
</code></pre>

<h3>Limitações conhecidas</h3>

<ul>
  <li>O GSMArena pode alterar sua estrutura HTML sem aviso prévio, o que pode quebrar os seletores do scraper.</li>
  <li>Dispositivos muito antigos podem ter páginas de especificações com estrutura diferente e gerar objetos <code>specs</code> incompletos.</li>
  <li>O campo <code>highlights</code> pode estar vazio em modelos cujas páginas não possuem a barra de destaques visual.</li>
  <li>O scraper não contorna proteções avançadas como CAPTCHAs. Se o site apresentar um CAPTCHA, a requisição falhará após as 3 tentativas.</li>
  <li>Os dados refletem o estado do site <strong>no momento da coleta</strong>. Especificações podem ser atualizadas pelo GSMArena posteriormente.</li>
</ul>

<hr>

<h2 id="resolucao-de-problemas">11. Resolução de Problemas</h2>

<h3>Erro: <code>ModuleNotFoundError: No module named 'bs4'</code></h3>

<p>As dependências não foram instaladas. Execute:</p>

<pre><code>pip install requests beautifulsoup4 lxml
</code></pre>

<h3>Erro: <code>RuntimeError: Could not fetch brands page</code></h3>

<p>O scraper não conseguiu acessar o GSMArena. Causas possíveis:</p>

<ul>
  <li>Sem conexão com a internet.</li>
  <li>O IP foi temporariamente bloqueado — aguarde alguns minutos e tente novamente com um delay maior.</li>
  <li>O GSMArena está fora do ar.</li>
</ul>

<h3>Erro: <code>SyntaxError</code> ou <code>TypeError</code></h3>

<p>Verifique se está usando Python 3.10 ou superior:</p>

<pre><code>python --version
</code></pre>

<h3>Arquivo <code>brands/{marca}.json</code> gerado com <code>devices: []</code></h3>

<p>O scraper não encontrou o elemento <code>&lt;div class="makers"&gt;</code> na página da marca. Isso pode indicar que o GSMArena alterou o HTML da listagem. Verifique manualmente a URL da marca e compare com o seletor no código.</p>

<h3>O scraper parou no meio e perdeu dados</h3>

<p>Os dados são salvos automaticamente a cada 10 dispositivos. Basta rodar o mesmo comando novamente — o scraper retomará de onde parou.</p>

<h3>Quero converter os dados para CSV ou banco de dados</h3>

<p>Os arquivos JSON gerados podem ser facilmente convertidos com <code>pandas</code>:</p>

<pre><code>import json, pandas as pd

with open("output/brands/samsung.json", encoding="utf-8") as f:
    data = json.load(f)

# Achata as specs em colunas individuais (opcional)
rows = []
for device in data["devices"]:
    row = {"name": device["name"], "device_id": device["device_id"], "url": device["url"]}
    for section, fields in device.get("specs", {}).items():
        for key, val in fields.items():
            row[f"{section} — {key}"] = val
    rows.append(row)

df = pd.DataFrame(rows)
df.to_csv("samsung.csv", index=False, encoding="utf-8-sig")
</code></pre>

<hr>

<p><em>Documentação gerada em Abril de 2026. Compatível com o layout atual do GSMArena.</em></p>

</body>
</html>
