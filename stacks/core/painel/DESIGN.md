---
name: Painel Atena
description: O servidor de casa como um aparelho de mesa, com chassi de alumínio ou grafite, teclas físicas, LEDs de estado e um visor preto vivo.
colors:
  # tema claro (alumínio): os valores de :root em app/public/estilo.css
  amarelo: "#ffc400"
  amarelo-borda: "#c99a00"
  amarelo-lado: "#9a7600"
  amarelo-tinta: "#141414"
  tecla: "#2c2f2d"
  tecla-borda: "#1f2120"
  tecla-lado: "#0b0c0b"
  tecla-tinta: "#f1f2ef"
  tecla-perigo: "#ff8a7f"
  led-verde: "#2bd46a"
  led-ambar: "#ffa51f"
  led-vermelho: "#ff4433"
  led-azul: "#3e8bff"
  led-apagado: "#aeb1ac"
  verde: "#12773a"
  ambar: "#965400"
  vermelho: "#c42b1e"
  azul: "#2559c4"
  foco: "#2559c4"
  chassi: "#e3e4e1"
  chassi-2: "#d6d8d4"
  modulo: "#f1f2ef"
  modulo-claro: "#fafaf8"
  poco: "#d3d5d1"
  tinta: "#161716"
  tinta-2: "#585b57"
  risco: "#c3c6c1"
  risco-forte: "#9da09b"
  moldura: "#2a2c2b"
  borda-visor: "transparent"
  visor: "#070908"
  visor-traco: "#e6efe9"
  visor-fraco: "#7d8a83"
  visor-apagado: "#17211c"
  # tema escuro (grafite): o mesmo custom property sob @media (prefers-color-scheme: dark)
  tecla-escuro: "#353937"
  tecla-borda-escuro: "#444946"
  tecla-lado-escuro: "#080908"
  tecla-tinta-escuro: "#ecedea"
  led-apagado-escuro: "#3a3e3b"
  verde-escuro: "#3ddc7a"
  ambar-escuro: "#ffb347"
  vermelho-escuro: "#ff6a5c"
  azul-escuro: "#6aa4ff"
  foco-escuro: "#6aa4ff"
  chassi-escuro: "#151615"
  chassi-2-escuro: "#0f100f"
  modulo-escuro: "#1d1f1e"
  modulo-claro-escuro: "#242625"
  poco-escuro: "#0d0e0d"
  tinta-escuro: "#ecedea"
  tinta-2-escuro: "#a3a6a1"
  risco-escuro: "#2e312f"
  risco-forte-escuro: "#424643"
  moldura-escuro: "#090a09"
  borda-visor-escuro: "#343835"
typography:
  marca:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 800
    letterSpacing: "0.18em"
    fontVariation: "'wdth' 125"
  titulo:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.2
  corpo:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
    fontVariation: "'wdth' 100"
  corpo-fraco:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
  campo:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
  tecla:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.84rem"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "0.01em"
    fontVariation: "'wdth' 106"
  trilho:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 550
  rotulo:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.69rem"
    fontWeight: 650
    letterSpacing: "0.14em"
    fontVariation: "'wdth' 112"
  selo:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.62rem"
    fontWeight: 650
    letterSpacing: "0.14em"
    fontVariation: "'wdth' 112"
  rotulo-pequeno:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.6rem"
    fontWeight: 650
    letterSpacing: "0.12em"
    fontVariation: "'wdth' 112"
  codigo:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "0.64rem"
    fontWeight: 500
    fontFeature: "'tnum'"
  peca:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "0.62rem"
    fontWeight: 700
    letterSpacing: "0.04em"
  placa-modelo:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "0.6rem"
    fontWeight: 700
    letterSpacing: "0.06em"
  mono-texto:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.5
  mono-registro:
    fontFamily: "Martian Mono, ui-monospace, monospace"
    fontSize: "0.72rem"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  etiqueta: "2px"
  campo: "4px"
  raio-tecla: "5px"
  aviso: "6px"
  raio: "7px"
  visor: "9px"
  janela: "10px"
  folha: "14px"
  pilula: "0.6rem"
  led: "50%"
spacing:
  entre-teclas: "0.45rem"
  entre-modulos: "0.85rem"
  entre-modulos-pc: "1rem"
  modulo: "1rem 1.05rem 1.05rem"
  margem-celular: "0.75rem"
  margem-pc: "1.4rem 1.6rem"
  trilho-largura: "15.5rem"
  barra-altura: "4.4rem"
components:
  tecla:
    backgroundColor: "{colors.tecla}"
    textColor: "{colors.tecla-tinta}"
    typography: "{typography.tecla}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.5rem 0.95rem"
    height: "2.5rem"
  tecla-escuro:
    backgroundColor: "{colors.tecla-escuro}"
    textColor: "{colors.tecla-tinta-escuro}"
  tecla-principal:
    backgroundColor: "{colors.amarelo}"
    textColor: "{colors.amarelo-tinta}"
    typography: "{typography.tecla}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.5rem 0.95rem"
    height: "2.5rem"
  tecla-discreta:
    backgroundColor: "{colors.tecla}"
    textColor: "{colors.tecla-tinta}"
    typography: "{typography.tecla}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.4rem 0.72rem"
    height: "2.2rem"
  tecla-perigo:
    backgroundColor: "{colors.tecla}"
    textColor: "{colors.tecla-perigo}"
    typography: "{typography.tecla}"
    rounded: "{rounded.raio-tecla}"
  tecla-grande:
    height: "3.1rem"
  campo:
    backgroundColor: "{colors.poco}"
    textColor: "{colors.tinta}"
    typography: "{typography.campo}"
    rounded: "{rounded.campo}"
    padding: "0.5rem 0.65rem"
    height: "2.5rem"
  modulo:
    backgroundColor: "{colors.modulo}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio}"
    padding: "1rem 1.05rem 1.05rem"
  modulo-titulo:
    textColor: "{colors.tinta}"
    typography: "{typography.rotulo}"
  modulo-codigo:
    textColor: "{colors.tinta-2}"
    typography: "{typography.codigo}"
  peca:
    textColor: "{colors.tinta}"
    typography: "{typography.peca}"
    rounded: "{rounded.etiqueta}"
    padding: "0.05rem 0.3rem"
  placa-modelo:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.chassi}"
    typography: "{typography.placa-modelo}"
    rounded: "{rounded.etiqueta}"
    padding: "0.08rem 0.32rem"
  selo:
    textColor: "{colors.tinta-2}"
    typography: "{typography.selo}"
  selo-ok:
    textColor: "{colors.verde}"
  selo-ruim:
    textColor: "{colors.vermelho}"
  selo-neutro:
    textColor: "{colors.azul}"
  contagem:
    backgroundColor: "{colors.amarelo}"
    textColor: "{colors.amarelo-tinta}"
    rounded: "{rounded.pilula}"
    padding: "0 0.3rem"
    height: "1.1rem"
  faixa:
    backgroundColor: "{colors.amarelo}"
    textColor: "{colors.amarelo-tinta}"
    typography: "{typography.titulo}"
    rounded: "{rounded.raio}"
    padding: "0.8rem 1rem"
  visor-moldura:
    backgroundColor: "{colors.moldura}"
    rounded: "{rounded.visor}"
    padding: "5px"
  visor-vidro:
    backgroundColor: "{colors.visor}"
    textColor: "{colors.visor-traco}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.9rem 1rem 1rem"
  mostrador-numero:
    backgroundColor: "{colors.visor}"
    textColor: "{colors.visor-traco}"
    rounded: "{rounded.campo}"
    padding: "0.5rem 0.7rem 0.55rem"
  aviso:
    backgroundColor: "{colors.visor}"
    textColor: "{colors.visor-traco}"
    rounded: "{rounded.aviso}"
    padding: "0.65rem 0.85rem"
  registro:
    backgroundColor: "{colors.visor}"
    textColor: "{colors.visor-traco}"
    typography: "{typography.mono-registro}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.75rem 0.85rem"
  barra-item:
    textColor: "{colors.tinta-2}"
    typography: "{typography.rotulo-pequeno}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.3rem 0.2rem"
    height: "3.3rem"
  barra-item-ativa:
    backgroundColor: "{colors.poco}"
    textColor: "{colors.tinta}"
  trilho-item:
    textColor: "{colors.tinta-2}"
    typography: "{typography.trilho}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.5rem 0.6rem"
  trilho-item-ativa:
    backgroundColor: "{colors.poco}"
    textColor: "{colors.tinta}"
  janela:
    backgroundColor: "{colors.modulo}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.janela}"
    padding: "1rem 1.1rem"
  paleta-item-marcado:
    backgroundColor: "{colors.poco}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio-tecla}"
    padding: "0.6rem 0.7rem"
---

# Design System: Painel Atena

## Overview

**Creative North Star: "O Aparelho de Mesa"**

O painel é um aparelho de mesa da família Braun e Teenage Engineering, feito para um servidor caseiro: um chassi de alumínio (tema claro) ou grafite (tema escuro) onde se aparafusam módulos com etiqueta de engenharia, uma fileira de teclas físicas e um visor preto que desenha o estado da máquina em tempo real. O tema segue o aparelho do dono (`prefers-color-scheme`); só o chassi muda: o visor é o mesmo e as teclas continuam grafite nos dois.

A densidade é de instrumento, não de site. Os títulos são rótulos pequenos em versalete espaçado, e quem carrega a hierarquia é o visor, com números em 7 segmentos e desenhos vivos (carretéis de fita que giram na velocidade da CPU, termômetros, o tanque da RAM, a torre do PC, o mostrador de 24 h). O estado se lê pelos LEDs, sempre com o texto do lado. Uma tecla amarela por módulo diz qual é a ação principal; todas as outras são grafite.

O sistema recusa duas coisas, confirmadas pelo dono: a cara de SaaS genérico (cartões cinza iguais com ícones de biblioteca) e o temático demais (ficção científica, cara de jogo). A "cena" existe, mas só nos momentos que importam: entrar, chegar uma aprovação, um agendamento rodar, o PC ligar. O uso de todo dia é rápido e quieto.

**Key Characteristics:**
- Chassi de alumínio ou grafite que segue o tema do aparelho; visor sempre preto.
- Teclas grafite com lado de 3px que afundam ao toque; amarelo sinal só na ação principal.
- LEDs verde, âmbar, vermelho e azul como único vocabulário de estado, sempre com legenda.
- Módulos com parafusos nos cantos, régua na borda e etiqueta de engenharia (título em versalete, código em mono, peça posicional como IN-01).
- Placa de modelo "ATENA AT-1" na marca.
- Números medidos em 7 segmentos com os segmentos apagados visíveis.
- Pictogramas próprios numa grade de 24 com traço de 1,75.
- Archivo (largura variável) e Martian Mono, servidas pelo próprio painel.

## Colors

Uma paleta de instrumento: neutros de alumínio ou grafite quase sem croma, uma única cor de ação (o amarelo sinal) e quatro luzes de LED que só falam de estado. Todas as cores são custom properties em `:root`; o tema escuro troca só os valores, sob `@media (prefers-color-scheme: dark)`. As chaves `-escuro` do frontmatter são esses valores do tema escuro.

### Primary
- **Amarelo Sinal** (#ffc400): a face da tecla principal, a faixa de aprovações, a contagem de pedidos esperando, o ponto aceso da tela ativa na navegação, os marcadores do mostrador da agenda e a seleção de texto. É a cor de "isto é com você".
- **Borda e Lado do Amarelo** (#c99a00, #9a7600): o contorno e o lado de baixo da tecla amarela e da faixa; a Borda também é o sublinhado dos links (2px, 3px abaixo da linha).
- **Tinta sobre Amarelo** (#141414): todo texto e pictograma em cima do amarelo.

### Secondary
- **Tecla Grafite** (#2c2f2d; #353937 no escuro): a face de toda tecla que não é a principal, nos dois temas. No alumínio ela contrasta como uma tecla de calculadora escura; no grafite, fica um tom acima do chassi.
- **Borda e Lado da Tecla** (#1f2120 e #0b0c0b; #444946 e #080908 no escuro): o contorno de 1px e o lado de 3px que dão volume à tecla.
- **Tinta da Tecla** (#f1f2ef; #ecedea no escuro): o texto das teclas grafite.
- **Coral de Perigo** (#ff8a7f): o texto da tecla que apaga ou desfaz, acompanhado de um ponto de LED vermelho; o mesmo nos dois temas porque a tecla é sempre grafite.

### Tertiary
- **Luz Verde** (#2bd46a): no ar, ok, concluído; também o nível dos desenhos do visor e os segmentos acesos do medidor.
- **Luz Âmbar** (#ffa51f): perto do limite (a partir de 85% nos termômetros e no tanque).
- **Luz Vermelha** (#ff4433): falha, parado, passou do limite.
- **Luz Azul** (#3e8bff): informação ou em andamento (rodando, evento, este aparelho); também a fita dos carretéis.
- **LED Apagado** (#aeb1ac; #3a3e3b no escuro): o LED sem estado e os segmentos vazios do medidor.
- **Texto de Estado** (verde #12773a, âmbar #965400, vermelho #c42b1e, azul #2559c4; no escuro #3ddc7a, #ffb347, #ff6a5c, #6aa4ff): a legenda escrita ao lado do LED, escura o bastante para ler sobre o alumínio (todas acima de 5:1 sobre o módulo) e clara no grafite.

### Neutral
- **Alumínio Escovado** (#e3e4e1; Grafite Fundido #151615 no escuro): o chassi, o fundo da página.
- **Lateral do Chassi** (#d6d8d4; #0f100f no escuro): o trilho do PC e a barra do celular, um degrau abaixo do chassi.
- **Placa** (#f1f2ef; #1d1f1e no escuro): a face dos módulos, das janelas e da frente de entrada.
- **Tampo** (#fafaf8; #242625 no escuro): o tampo das placas da vista explodida e o fundo das teclas de atalho (`kbd`).
- **Poço** (#d3d5d1; #0d0e0d no escuro): tudo que afunda: campos, a tecla ativa da navegação, o item marcado da paleta, o texto de um pedido.
- **Tinta de Serigrafia** (#161716; #ecedea no escuro): o texto principal e os traços da vista explodida.
- **Tinta Secundária** (#585b57; #a3a6a1 no escuro): rótulos, textos fracos, códigos e placeholders.
- **Risco** (#c3c6c1; #2e312f no escuro): bordas dos módulos e divisórias entre itens.
- **Risco Forte** (#9da09b; #424643 no escuro): as marcas da régua, o contorno dos campos e da peça, as bordas do trilho e da barra, as guias tracejadas.
- **Moldura** (#2a2c2b; #090a09 no escuro): a moldura em volta do visor, do mostrador pequeno e dos avisos. No escuro ganha um contorno de 1px (#343835) para não sumir no chassi.
- **Vidro Preto** (#070908): o fundo do visor, dos avisos e dos registros, nos dois temas.
- **Traço do Visor** (#e6efe9): os segmentos acesos e as linhas dos desenhos.
- **Legenda do Visor** (#7d8a83): rótulos, unidades e linhas extras dentro do visor (5,5:1 sobre o vidro).
- **Segmento Fantasma** (#17211c): os segmentos apagados do 7 segmentos, visíveis por trás dos acesos, e o miolo dos desenhos.
- **Foco** (#2559c4; #6aa4ff no escuro): o contorno de foco do teclado.

### Named Rules
**A Regra da Tecla Amarela.** Entre as teclas, só a ação principal é amarela, uma por módulo ou janela; todas as outras são grafite, nos dois temas. Fora das teclas, o amarelo só aponta para o dono e para onde ele está: a faixa e a contagem de aprovações, o ponto da tela ativa, o sublinhado dos links, a seleção de texto, os marcadores do mostrador da agenda, o tampo da placa sob o ponteiro na vista explodida e a varredura dos LEDs ao entrar.

**A Regra do LED com Legenda.** Estado só se diz com os quatro LEDs (verde ok, âmbar perto do limite, vermelho falha, azul informação ou em andamento), e sempre com o texto do lado. Cor sozinha não é estado, e nenhum outro matiz entra nesse vocabulário.

**A Regra do Visor Sempre Preto.** O visor é vidro preto nos dois temas. O tema troca o chassi, nunca o visor.

## Typography

**Display Font:** Archivo (com system-ui, sans-serif), variável em peso (100 a 900) e largura (62% a 125%)
**Body Font:** Archivo (com system-ui, sans-serif)
**Label/Mono Font:** Martian Mono (com ui-monospace, monospace), variável em peso (100 a 800)

**Character:** Archivo faz o papel da serigrafia do aparelho: larga e espaçada nos rótulos e na marca, normal no texto corrido. Martian Mono é a máquina falando: códigos de peça, unidades, registros e avisos. As duas são arquivos `.woff2` servidos pelo próprio painel (licença OFL), porque a CSP não deixa carregar fonte de fora.

### Hierarchy
- **Marca** (800, 1.05rem, largura 125, espaço .18em): o "ATENA" do cabeçalho, do trilho e da frente de entrada, sempre seguido da placa de modelo AT-1.
- **Título** (700, 1rem, altura 1.2): o texto da faixa de aprovações e o título das janelas. Não há manchete maior que essa: a ênfase grande é dos números do visor.
- **Corpo** (400, 1rem, altura 1.45): o texto corrido e os valores das linhas; a pergunta de um pedido do Claude Code sobe para 1.05rem.
- **Corpo Fraco** (400, .875rem, Tinta Secundária): explicações, metadados de pedidos, estados vazios.
- **Tecla** (600, .84rem, largura 106): o texto das teclas; .95rem nas teclas grandes de decisão (Aprovar, Ligar) e na frente de entrada.
- **Trilho** (550, .9rem): os nomes das telas no trilho do PC.
- **Rótulo** (650, .69rem, largura 112, espaço .14em, caixa alta): títulos de módulo, rótulos de linha e `h3`. Na versão pequena (650, .6rem, espaço .12em) vira o nome das telas na barra do celular (e, com .14em, o título dos grupos do trilho); o selo de estado usa .62rem.
- **Código** (Martian Mono 500, .64rem, algarismos tabulares): o que o módulo mede, à direita do título ("12 núcleos · 15.5 GB").
- **Peça** (Martian Mono 700, .62rem, espaço .04em): o código posicional IN-01; a placa de modelo AT-1 usa 700, .6rem, espaço .06em.
- **Texto de Máquina** (Martian Mono 400, .8rem, altura 1.5; registros em .72rem, altura 1.55): o texto de um pedido, o editor de stacks e os logs. Avisos usam .78rem, altura 1.4.

### Named Rules
**A Regra da Etiqueta.** Título de módulo é rótulo, não manchete: Archivo 650 a .69rem, largura 112, caixa alta com .14em de espaço. A hierarquia vem do visor e dos números, nunca do tamanho dos títulos.

**A Regra do Número de Máquina.** Número medido no visor sai em 7 segmentos, com os segmentos apagados visíveis por trás. Códigos, unidades, registros e chaves saem em Martian Mono. Números em linhas de texto usam algarismos tabulares.

## Layout

O celular e o PC têm o mesmo peso; nenhum é a versão capada do outro.

**Celular (abaixo de 60rem).** No topo, a marca com a placa AT-1 e a fileira de LEDs das zonas, cada um com o nome da zona embaixo. O conteúdo é uma grade de colunas automáticas de no mínimo 21rem (uma coluna no telefone), com .85rem entre módulos, margem lateral de .75rem e respiro de baixo do tamanho da barra (4.4rem) mais a área segura. A barra fixa embaixo tem cinco teclas: Início, PC, Agenda, Serviços e Mais; o "Mais" abre uma folha de baixo para cima com as outras telas num teclado de três colunas. Abaixo de 40rem, o visor vira uma grade de duas colunas em que a primeira célula ocupa a linha toda.

**PC (a partir de 60rem).** O aparelho vira duas colunas: um trilho fixo de 15.5rem à esquerda, com os grupos hoje, servidor, máquina, registro e conta, e a tecla Buscar com o atalho Ctrl K no pé; e a área de trabalho, até 82rem de largura, com margem de 1.4rem por 1.6rem. A tela do PC fica numa coluna só de até 46rem.

**Ritmo.** Teclas ficam a .45rem umas das outras; módulos a 1rem no PC; o conteúdo do módulo tem 1rem de respiro em cima e 1.05rem nos lados e embaixo. O cabeçalho do módulo separa do conteúdo com uma linha de Risco e .8rem.

### Named Rules
**A Regra das Colunas de Jornal.** No PC, a tela é um fluxo de colunas CSS: duas colunas, e colunas automáticas de 21rem no Início e nas Aprovações. Cada módulo leva `break-inside: avoid`; os módulos largos e a faixa de aprovações atravessam todas as colunas com `column-span: all`. Os módulos têm a altura do que mostram.

**A Regra do Polegar.** No celular, as telas de todo dia ficam na barra de baixo, em teclas de 3.3rem de altura; com toque grosso (`pointer: coarse`), toda tecla tem no mínimo 2.75rem.

## Elevation & Depth

Profundidade física e discreta, como num aparelho de verdade: o que está montado sobe um pouco, o que é tecla tem lado, o que recebe dado ou está escolhido afunda num poço, e o visor é um vidro fundo dentro de uma moldura. Não há sombra decorativa nem brilho; a única luz é a dos LEDs e do ponto amarelo da tela ativa.

### Shadow Vocabulary
- **Placa** (`box-shadow: 0 1px 0 rgb(255 255 255 / .7) inset, 0 1px 2px rgb(0 0 0 / .07), 0 6px 16px -6px rgb(0 0 0 / .12)`; no escuro `0 1px 0 rgb(255 255 255 / .04) inset, 0 1px 2px rgb(0 0 0 / .5), 0 8px 20px -8px rgb(0 0 0 / .6)`): módulos e a frente de entrada. O realce de 1px no topo é a quina da chapa.
- **Tecla** (`box-shadow: 0 2px 5px -1px rgb(0 0 0 / .18)`; no escuro `.6`): teclas e a faixa, junto com o lado de 3px.
- **Tecla Apertada** (`box-shadow: 0 1px 2px rgb(0 0 0 / .2)`): durante o toque, com a tecla descendo 1px.
- **Poço** (`box-shadow: inset 0 1px 3px rgb(0 0 0 / .14)`): campos, tecla ativa da barra e do trilho, item marcado da paleta.
- **Vidro do Visor** (`box-shadow: inset 0 0 0 1px rgb(255 255 255 / .035), inset 0 10px 28px rgb(0 0 0 / .7)`): o fundo do visor; a moldura em volta leva `0 0 0 1px` da borda do visor, um realce de 1px embaixo e uma sombra interna de 1px.
- **Janela** (`box-shadow: 0 20px 50px -12px rgb(0 0 0 / .45)`, fundo `rgb(10 11 10 / .5)`): janelas, a folha "Mais" e a paleta.
- **Brilho de LED** (`box-shadow: 0 0 6px` na cor do LED a 55%): só em LEDs acesos.

### Named Rules
**A Regra da Tecla com Lado.** A profundidade de uma tecla é a borda de baixo de 3px, o lado dela, não uma sombra deslocada. Ao apertar, a tecla desce 1px e o lado vira 2px.

**A Regra da Placa e do Poço.** O que está montado sobe (módulo: realce no topo e sombra ambiente); o que está selecionado ou recebe dado afunda (sombra interna de 1px por 3px). Nada flutua além das janelas.

## Shapes

Cantos suavemente arredondados e em escada, do menor para o maior conforme o tamanho da peça: 2px nas etiquetas (peça, placa de modelo, medidor), 4px nos campos e no mostrador pequeno, 5px nas teclas e no vidro do visor, 6px nos avisos, 7px nos módulos e na faixa, 9px na moldura do visor, 10px nas janelas e na frente de entrada, 14px no topo da folha "Mais". LEDs e parafusos são círculos.

Os módulos levam quatro parafusos de 9px a 5px dos cantos (um círculo com fenda diagonal, desenhado em SVG) e uma régua na borda de cima, recuada 1.4rem dos lados, com marcas a cada 8px e marcas maiores a cada 40px. A frente de entrada leva os parafusos, sem régua. O medidor é uma barra de LEDs de VU: segmentos de 5px com folga de 2px. Os segmentos do 7 segmentos são hexágonos alongados com inclinação de 7 graus. A vista explodida desenha as zonas como placas em perspectiva isométrica, ligadas por guias tracejadas (3 por 3) e com linhas de chamada até o rótulo. Os pictogramas são de traço, com pequenos pontos ou tampas cheios só quando o desenho pede, numa grade de 24, com traço de 1,75 e pontas e quinas arredondadas.

### Named Rules
**A Regra do Parafuso.** Toda placa montada leva os quatro parafusos: o módulo também leva a régua na borda; a frente de entrada, só os parafusos. Janelas, visor, faixa e avisos não levam parafuso.

## Components

### Buttons
Teclas físicas de calculadora: firmes, com lado, que afundam ao toque.
- **Shape:** cantos de 5px; contorno de 1px e lado de 3px embaixo.
- **Grafite (padrão):** face Tecla Grafite com texto claro, 600 a .84rem, .5rem por .95rem, altura mínima de 2.5rem (2.75rem com toque grosso). Pictogramas de 1.15rem à esquerda do texto, com .45rem de folga.
- **Principal:** a mesma tecla com face Amarelo Sinal, borda e lado do amarelo e texto quase preto. Uma por módulo ou janela.
- **Discreta:** grafite menor (.4rem por .72rem, altura 2.2rem, .78rem de texto) para ações secundárias como Recusar ou Cancelar.
- **Perigo:** grafite com texto Coral de Perigo e um ponto de LED vermelho de .42rem antes do texto. Toda ação destrutiva pede confirmação antes de rodar.
- **Grandes:** na fila de decisão (Aprovar e Recusar, Ligar), as teclas dividem a largura e sobem para 3.1rem de altura e .95rem de texto.
- **Hover / Focus / Active:** no hover, brilho de 3%; no foco do teclado, contorno de 2px na cor de Foco a 2px de distância; ao apertar, desce 1px e o lado vai para 2px em 80ms (ease-out). Desabilitada, fica a 45% de opacidade.

### Chips
- **Peça:** o código posicional do módulo (IN-01, AP-02, SY-03...), em Martian Mono 700, com contorno de 1px em Risco Forte e cantos de 2px. É numerado sozinho pela posição do módulo na tela, com o prefixo da tela (IN, AP, AG, SV, SY, AR, PC, LB, AT, HI, AJ).
- **Placa de Modelo:** "AT-1" em Martian Mono 700, invertida (fundo Tinta, texto Chassi), cantos de 2px, logo depois da marca.
- **Selo de Estado:** LED de .46rem seguido da legenda em versalete (.62rem), na cor de estado: verde, vermelho ou azul; o texto nunca falta.
- **Contagem:** pílula amarela de 1.1rem com o número de aprovações esperando, em Martian Mono 700, presa à tecla das Aprovações e do "Mais".
- **Atalho (`kbd`):** Martian Mono .66rem em fundo Tampo, com borda de tecla e lado de 2px.

### Cards / Containers
- **Corner Style:** 7px no módulo; 10px nas janelas e na frente de entrada.
- **Background:** Placa, com os quatro parafusos por cima.
- **Shadow Strategy:** Placa (ver Elevation & Depth).
- **Border:** 1px de Risco; régua de marcas na borda de cima.
- **Internal Padding:** 1rem em cima, 1.05rem nos lados e embaixo.
- **Cabeçalho:** o título em Rótulo à esquerda e, à direita, a etiqueta: o código do que o módulo mede (Martian Mono, Tinta Secundária, cortado com reticências se não couber) e a peça. Uma linha de Risco separa o cabeçalho do conteúdo.
- **Linhas e listas:** rótulo em versalete à esquerda e valor com algarismos tabulares à direita; itens de lista separados por 1px de Risco.
- **Largo:** o módulo largo ocupa a linha toda; no PC, o visor dele cresce (desenhos de 4.6rem, números de 3rem) e as células se espalham numa linha só.

### Inputs / Fields
- **Style:** poço (fundo Poço com sombra interna), contorno de 1px em Risco Forte, cantos de 4px, .5rem por .65rem, altura mínima de 2.5rem, Archivo .95rem. Selects e campos com lista levam a seta própria desenhada em SVG, sem a do sistema. Caixas de seleção usam o amarelo como cor de destaque. A alça de redimensionar do textarea são três riscos diagonais em Risco Forte.
- **Focus:** contorno de 2px na cor de Foco a 2px de distância.
- **Error / Disabled:** a mensagem de erro sai em texto vermelho de estado logo abaixo, com altura reservada para não pular a tela.

### Navigation
- **Barra (celular):** cinco teclas transparentes na Lateral do Chassi, com pictograma de 1.4rem e o nome em rótulo pequeno. A ativa afunda (Poço, borda de Risco, sombra interna) e acende um ponto amarelo de .38rem no canto. A contagem de aprovações aparece no "Mais".
- **Trilho (PC):** grupos com título em rótulo pequeno; cada tela é um item com pictograma de 1.15rem e nome em Archivo 550 .9rem. Hover em meio poço; a ativa afunda e acende o ponto amarelo à direita. A marca, a placa AT-1 e os LEDs das zonas ficam no alto; a tecla Buscar com Ctrl K, no pé.
- **Mais (folha):** sobe de baixo, com cantos de 14px no topo, e mostra as outras telas como teclas grafite num teclado de três colunas.
- **Paleta (Ctrl+K):** janela a 12% do topo, até 36rem, com campo grande de 3rem; os itens mostram pictograma, título e o grupo em versalete à direita. Setas movem a marcação, Enter executa; o item marcado afunda.

### O Visor
A assinatura do aparelho: um vidro preto numa moldura, com células de desenho e leitura, sempre a partir dos dados de verdade.
- **Estrutura:** moldura de 5px, vidro com cantos de 5px e sombra interna funda; as células ficam lado a lado, cada uma com a largura do que mostra, separadas por 1rem por 2.2rem.
- **Célula:** rótulo em versalete na Legenda do Visor, o desenho, o número em 7 segmentos com a unidade em Martian Mono ao lado e, se houver, uma linha extra em mono.
- **7 segmentos:** os segmentos apagados ficam visíveis em Segmento Fantasma, como numa calculadora; ponto decimal e dois-pontos de relógio são parte do dígito; inclinação de 7 graus; altura de 2.15rem (1.95rem no telefone, 3rem no módulo largo do PC).
- **Desenhos:** traço de 1.6 em Traço do Visor (1 a 55% para os finos), níveis em verde que passam a âmbar perto do limite e a vermelho acima dele. Carretéis de fita giram de 9s por volta (CPU parada) a 0,7s (CPU cheia); a ventoinha da placa gira pelo rpm; a torre do PC acende o botão de energia em verde quando ligado.
- **Mostrador pequeno:** um número em 7 segmentos num vidro com moldura de 4px dentro de um módulo comum (por exemplo, o gasto do mês).

### Vista Explodida
O desenho técnico das zonas: uma placa isométrica por zona, com um LED por container (até 12, depois "+N"), linha de chamada até o nome da zona em versalete e a conta "no ar/total" em mono. Uma zona com problema sai do lugar (8px para a direita, 4px para cima), ganha um tampo levemente avermelhado e lista os containers com falha em vermelho. Cada placa é focável e leva à tela de Serviços filtrada na zona.

### Faixa de Aprovações
Uma tecla larga em Amarelo Sinal, com lado de 3px, no topo de qualquer tela quando há pedido esperando: o pictograma de aprovações, "N aprovações esperando você" em 700 e, à direita, "ver" com a seta. Atravessa todas as colunas no PC.

### Avisos
Retângulos de vidro preto com moldura de 3px, texto em Martian Mono e um LED à esquerda (azul informação, verde ok, vermelho erro). Ficam acima da barra no celular e no canto de baixo à direita no PC; somem em 4s (8s se for erro).

### Movimento
**A Regra da Cena nos Momentos.** Movimento de cena só em quatro momentos: a varredura dos LEDs das zonas ao entrar (cada LED acende em amarelo por .5s, 70ms depois do anterior), o pulso da faixa quando chega aprovação (anel amarelo de 16px, 1.2s, duas vezes), a ventoinha que acelera no primeiro minuto depois de o PC ligar e o ponteiro do mostrador que gira quando um agendamento roda (1.4s, duas voltas). Os carretéis e as ventoinhas do visor giram na velocidade medida, porque ali o movimento é a leitura. Com `prefers-reduced-motion`, nada se move: animações e transições são desligadas.

## Do's and Don'ts

### Do:
- **Do** montar todo módulo com o cabeçalho de etiqueta: título em Rótulo, o código do que ele mede em Martian Mono e a peça posicional (IN-01), que o painel numera sozinho.
- **Do** usar uma única tecla amarela (principal) por módulo ou janela; as outras são grafite, discretas ou de perigo.
- **Do** dizer todo estado com um LED e o texto do lado (selo), nas cores verde, âmbar, vermelho e azul.
- **Do** desenhar número medido em 7 segmentos no visor preto, com os segmentos apagados visíveis, e só com dado de verdade do executor.
- **Do** desenhar pictogramas novos no próprio painel, na grade de 24 com traço de 1,75, pontas redondas e `currentColor`.
- **Do** pegar cor, raio e fonte das custom properties (`var(--tecla)`, `var(--raio)`, `var(--mono)`) e mudar o tema só trocando valores sob `prefers-color-scheme: dark`.
- **Do** passar valores dinâmicos (largura do medidor, velocidade dos carretéis, atraso da varredura) pelo CSSOM, com `style.setProperty`.
- **Do** manter os alvos de toque em 2.75rem no toque grosso e a barra de baixo no celular.
- **Do** desligar toda animação nova sob `prefers-reduced-motion`.

### Don't:
- **Don't** pintar de amarelo uma tecla que não seja a ação principal, nem usar o amarelo como enfeite.
- **Don't** dizer estado só com cor, nem criar um quinto matiz de estado.
- **Don't** clarear o visor no tema claro.
- **Don't** usar biblioteca de ícones nem caractere Unicode fazendo papel de ícone.
- **Don't** carregar fonte, script, estilo ou imagem de outro endereço, nem usar o atributo `style` inline: a CSP é `default-src 'self'` e o container não tem rede.
- **Don't** pôr movimento contínuo que não seja leitura de dado; a cena fica nos quatro momentos.
- **Don't** fazer cara de SaaS genérico (cartões cinza iguais com ícones de biblioteca) nem de ficção científica ou jogo.
- **Don't** escrever texto abaixo de .6rem.
- **Don't** dar sombra deslocada às teclas: a profundidade é o lado de 3px.
