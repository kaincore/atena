---
name: Painel Atena
description: O servidor de casa como um templo grego visto de perto, em mármore e tinta, com o azul egípcio como único acento e o meandro como ornamento e como medida.
colors:
  # tema claro (o mármore, de dia): os valores de :root em app/public/estilo.css
  azul: "#24418f"
  azul-forte: "#1a3275"
  azul-claro: "#e9edf7"
  azul-tinta: "#f7f8fc"
  gravura: "#24418f"
  foco: "#24418f"
  malaquita: "#2b8059"
  malaquita-tinta: "#1c6946"
  ocre: "#b07c1e"
  ocre-claro: "#f7f1e4"
  ocre-tinta: "#6e4706"
  cinabrio: "#c23a26"
  cinabrio-claro: "#f9e8e4"
  cinabrio-tinta: "#a22d1b"
  pedra: "#c6ccc9"
  chao: "#f0f1ef"
  casca: "#f6f7f6"
  placa: "#fcfcfb"
  placa-2: "#f4f5f4"
  veio: "#e1e4e2"
  veio-forte: "#b8bfbb"
  tinta: "#151b27"
  tinta-2: "#556070"
  tinta-3: "#9aa3ad"
  noite: "#141a27"
  noite-tinta: "#e4e8ee"
  # tema escuro (a noite azul): o mesmo custom property sob @media (prefers-color-scheme: dark)
  azul-escuro: "#a3b5f3"
  azul-forte-escuro: "#bfcdf7"
  azul-claro-escuro: "#1b2441"
  azul-tinta-escuro: "#0b0f1a"
  gravura-escuro: "#cdd3df"
  centelha: "#2c4fae"
  centelha-escuro: "#f3eee2"
  foco-escuro: "#a3b5f3"
  malaquita-escuro: "#57b98a"
  malaquita-tinta-escuro: "#7fd0a8"
  ocre-escuro: "#d6a24a"
  ocre-claro-escuro: "#231d10"
  ocre-tinta-escuro: "#e8bf74"
  cinabrio-escuro: "#e8705c"
  cinabrio-claro-escuro: "#2d1714"
  cinabrio-tinta-escuro: "#f19a8a"
  pedra-escuro: "#343d52"
  chao-escuro: "#0b0f1a"
  casca-escuro: "#0e1320"
  placa-escuro: "#121827"
  placa-2-escuro: "#0e1320"
  veio-escuro: "#1f2738"
  veio-forte-escuro: "#374157"
  tinta-escuro: "#e7e9ee"
  tinta-2-escuro: "#a3acba"
  tinta-3-escuro: "#4f5a72"
  noite-escuro: "#06090f"
typography:
  inscricao:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.28em"
    fontVariation: "'FLAR' 100, 'VOLM' 100"
  titulo-tela:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "clamp(1.7rem, 1.2rem + 1.7vw, 2.5rem)"
    fontWeight: 400
    lineHeight: 1.05
    letterSpacing: "-0.015em"
    fontVariation: "'FLAR' 100, 'VOLM' 100"
  numero:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "2.4rem"
    fontWeight: 350
    lineHeight: 1
    letterSpacing: "-0.025em"
    fontFeature: "'tnum', 'lnum'"
    fontVariation: "'FLAR' 100, 'VOLM' 100"
  numero-medalhao:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "clamp(1.55rem, 1.15rem + 1.2vw, 2.05rem)"
    fontWeight: 350
    lineHeight: 1
    letterSpacing: "-0.025em"
    fontFeature: "'tnum', 'lnum'"
    fontVariation: "'FLAR' 100, 'VOLM' 100"
  titulo-modulo:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "1.02rem"
    fontWeight: 500
    lineHeight: 1.2
    fontVariation: "'FLAR' 100, 'VOLM' 100"
  corpo:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    fontVariation: "'FLAR' 0, 'VOLM' 0"
  corpo-fraco:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  detalhe:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "'tnum'"
  rotulo:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 550
    letterSpacing: "0.005em"
    fontVariation: "'FLAR' 100, 'VOLM' 50"
  tecla:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.86rem"
    fontWeight: 550
    lineHeight: 1.1
    letterSpacing: "0.01em"
  trilho:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.92rem"
    fontWeight: 500
  campo:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
  contagem:
    fontFamily: "Commissioner, system-ui, sans-serif"
    fontSize: "0.64rem"
    fontWeight: 700
    lineHeight: "1.15rem"
    fontFeature: "'tnum'"
  mono-registro:
    fontFamily: "ui-monospace, 'SF Mono', 'Cascadia Mono', 'Roboto Mono', Menlo, monospace"
    fontSize: "0.74rem"
    fontWeight: 400
    lineHeight: 1.55
  mono-texto:
    fontFamily: "ui-monospace, 'SF Mono', 'Cascadia Mono', 'Roboto Mono', Menlo, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.5
  mono-linha:
    fontFamily: "ui-monospace, 'SF Mono', 'Cascadia Mono', 'Roboto Mono', Menlo, monospace"
    fontSize: "0.78rem"
    fontWeight: 500
    lineHeight: 1.5
rounded:
  miudo: "3px"
  raio: "6px"
  janela: "10px"
  marcador: "12px"
  folha: "18px"
  pilula: "0.6rem"
  ponto: "50%"
spacing:
  entre-teclas: "0.45rem"
  entre-modulos: "0.9rem"
  entre-modulos-pc: "1rem"
  modulo: "1.15rem 1.25rem 1.25rem"
  item: "0.75rem 0"
  margem-celular: "0.75rem"
  margem-pc: "1.8rem 2.2rem 2.5rem"
  coluna-minima: "21rem"
  largura-maxima: "82rem"
  trilho-largura: "15.5rem"
  barra-altura: "4.4rem"
components:
  tecla:
    backgroundColor: "{colors.placa}"
    textColor: "{colors.tinta}"
    typography: "{typography.tecla}"
    rounded: "{rounded.raio}"
    padding: "0.5rem 1rem"
    height: "2.5rem"
  tecla-hover:
    backgroundColor: "{colors.placa-2}"
  tecla-escuro:
    backgroundColor: "{colors.placa-escuro}"
    textColor: "{colors.tinta-escuro}"
  tecla-principal:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.azul-tinta}"
    typography: "{typography.tecla}"
    rounded: "{rounded.raio}"
    padding: "0.5rem 1rem"
    height: "2.5rem"
  tecla-principal-hover:
    backgroundColor: "{colors.azul-forte}"
  tecla-principal-escuro:
    backgroundColor: "{colors.azul-escuro}"
    textColor: "{colors.azul-tinta-escuro}"
  tecla-discreta:
    backgroundColor: "transparent"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio}"
    padding: "0.4rem 0.78rem"
    height: "2.2rem"
  tecla-perigo:
    textColor: "{colors.cinabrio-tinta}"
    rounded: "{rounded.raio}"
  tecla-perigo-hover:
    backgroundColor: "{colors.cinabrio-claro}"
  tecla-grande:
    height: "3.1rem"
  campo:
    backgroundColor: "{colors.placa-2}"
    textColor: "{colors.tinta}"
    typography: "{typography.campo}"
    rounded: "{rounded.raio}"
    padding: "0.5rem 0.7rem"
    height: "2.5rem"
  campo-foco:
    backgroundColor: "{colors.placa}"
  trava:
    textColor: "{colors.tinta-2}"
    typography: "{typography.rotulo}"
    rounded: "{rounded.raio}"
    padding: "0.45rem 0.45rem 0.5rem"
  trava-ligada:
    backgroundColor: "{colors.azul-claro}"
    textColor: "{colors.azul}"
  modulo:
    backgroundColor: "{colors.placa}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio}"
    padding: "1.15rem 1.25rem 1.25rem"
  modulo-escuro:
    backgroundColor: "{colors.placa-escuro}"
    textColor: "{colors.tinta-escuro}"
  modulo-titulo:
    textColor: "{colors.tinta}"
    typography: "{typography.titulo-modulo}"
  modulo-codigo:
    textColor: "{colors.tinta-2}"
  cabecalho-tela:
    textColor: "{colors.tinta}"
    typography: "{typography.titulo-tela}"
  numero-grande:
    textColor: "{colors.tinta}"
    typography: "{typography.numero}"
  item:
    textColor: "{colors.tinta}"
    typography: "{typography.corpo}"
    padding: "0.75rem 0"
  item-detalhe:
    textColor: "{colors.tinta-2}"
    typography: "{typography.detalhe}"
  ponto:
    backgroundColor: "{colors.pedra}"
    rounded: "{rounded.ponto}"
    size: "0.5rem"
  ponto-ok:
    backgroundColor: "{colors.malaquita}"
  ponto-morno:
    backgroundColor: "{colors.ocre}"
  ponto-ruim:
    backgroundColor: "{colors.cinabrio}"
  ponto-info:
    backgroundColor: "{colors.azul}"
  selo:
    textColor: "{colors.tinta-2}"
    typography: "{typography.rotulo}"
  selo-ok:
    textColor: "{colors.malaquita-tinta}"
  selo-ruim:
    textColor: "{colors.cinabrio-tinta}"
  selo-neutro:
    textColor: "{colors.azul}"
  medalhao:
    textColor: "{colors.tinta}"
    typography: "{typography.numero-medalhao}"
    width: "9.6rem"
  crepidoma-zona:
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio}"
    padding: "0.3rem 0.5rem"
    height: "2.3rem"
  crepidoma-zona-acesa:
    backgroundColor: "{colors.azul-claro}"
  faixa:
    backgroundColor: "{colors.ocre-claro}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio}"
    padding: "0.85rem 1.1rem"
  faixa-escuro:
    backgroundColor: "{colors.ocre-claro-escuro}"
    textColor: "{colors.tinta-escuro}"
  contagem:
    backgroundColor: "{colors.ocre}"
    textColor: "#1b1307"
    typography: "{typography.contagem}"
    rounded: "{rounded.pilula}"
    padding: "0 0.3rem"
    height: "1.15rem"
  barra-item:
    textColor: "{colors.tinta-2}"
    typography: "{typography.rotulo}"
    padding: "0.3rem 0.1rem"
    height: "3.5rem"
  barra-item-ativa:
    textColor: "{colors.azul}"
  marcador:
    backgroundColor: "{colors.azul-claro}"
    rounded: "{rounded.marcador}"
  marcador-escuro:
    backgroundColor: "{colors.azul-claro-escuro}"
  trilho-item:
    textColor: "{colors.tinta-2}"
    typography: "{typography.trilho}"
    rounded: "{rounded.raio}"
    padding: "0.52rem 0.65rem"
  trilho-item-ativa:
    backgroundColor: "{colors.azul-claro}"
    textColor: "{colors.azul}"
  janela:
    backgroundColor: "{colors.placa}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.janela}"
    padding: "1.15rem 1.25rem"
  folha:
    backgroundColor: "{colors.placa}"
    rounded: "{rounded.folha}"
  teclado-item:
    backgroundColor: "{colors.placa-2}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.janela}"
    padding: "1rem 0.3rem 0.85rem"
  teclado-item-ativa:
    backgroundColor: "{colors.azul-claro}"
    textColor: "{colors.azul}"
  paleta-item-marcado:
    backgroundColor: "{colors.azul-claro}"
    textColor: "{colors.azul}"
    rounded: "{rounded.raio}"
    padding: "0.62rem 0.75rem"
  aviso:
    backgroundColor: "{colors.noite}"
    textColor: "{colors.noite-tinta}"
    rounded: "{rounded.janela}"
    padding: "0.75rem 0.95rem"
  registro:
    backgroundColor: "{colors.noite}"
    textColor: "{colors.noite-tinta}"
    typography: "{typography.mono-registro}"
    rounded: "{rounded.raio}"
    padding: "0.85rem 0.95rem"
  texto-pedido:
    backgroundColor: "{colors.placa-2}"
    textColor: "{colors.tinta}"
    rounded: "{rounded.raio}"
    padding: "0.7rem 0.8rem"
---

# Design System: Painel Atena

## Overview

**Creative North Star: "A Policromia Contida"**

O painel é um templo grego visto de perto, em mármore e tinta. Os templos eram pintados; aqui a pintura foi reduzida ao essencial: um mármore frio de dia e uma noite azul-escura quase preta, o azul egípcio como único acento e o meandro como ornamento e como medida. O tema segue o aparelho do dono (`prefers-color-scheme`); os dois temas trocam só os valores das mesmas custom properties.

A densidade é de ferramenta. A casca é do mesmo mármore, com um meandro fino na borda (embaixo do topo no celular, descendo pelo trilho no PC); cada tela abre com o nome na letra de pedra sobre uma faixa de meandro, e cada módulo é uma placa de mármore com a chave do meandro antes do título. O estado se lê em um olhar pelos medalhões, cujo meandro da borda se pinta de azul até o valor, e pela crepidoma das zonas, a escada do templo em 3D, um degrau por zona e um ponto por container. Os pigmentos antigos (malaquita, ocre e cinábrio) só aparecem para dizer o estado.

O sistema recusa, por decisão do dono, a cara de SaaS genérico (o dashboard de cartões cinza), a Grécia de souvenir (colunas de enfeite, dourado, creme) e o que pareça desenho animado, jogo ou fantasia. O movimento é fluido e quieto no dia a dia; a cena fica para os momentos que importam: entrar pela construção do templo, chegar uma aprovação, um agendamento rodar, o PC ligar, uma zona ter problema.

**Key Characteristics:**
- Mármore frio de dia, noite azul-escura à noite; a casca no mesmo mármore, com o meandro fino na borda.
- O azul egípcio é o único acento: a ação principal, a tela ativa, o foco e o que mede.
- Malaquita, ocre e cinábrio só como pontos de estado, sempre com o texto do lado; o ocre também na faixa de aprovações.
- O meandro é ornamento (a borda da casca, a faixa do nome da tela, a chave do módulo) e medida (o anel dos medalhões, o medidor).
- A crepidoma das zonas em 3D é a assinatura e a única profundidade de verdade.
- Commissioner, de um tipógrafo grego, com as serifas de pedra nos títulos e números; caixa-alta só na inscrição ΑΘΗΝΑ.
- Ícones de traço fino com a área "pintada" que acende na tela ativa.
- Ease-out no dia a dia, uma mola amortecida só no que assenta; com `prefers-reduced-motion`, nada se move.
- Sem dependências: fonte, desenhos e ícones servidos pelo próprio painel, sob CSP `default-src 'self'`.

## Colors

Uma paleta de templo pintado, mas contida: neutros de mármore (de dia) ou de noite azul (à noite) quase sem croma, um único acento azul e três pigmentos que só falam de estado. Todas as cores são custom properties em `:root`; o tema escuro troca só os valores, sob `@media (prefers-color-scheme: dark)`. As chaves `-escuro` do frontmatter são esses valores do tema escuro.

### Primary
- **Tinta da Gravura** (#24418f; #cdd3df à noite): a tinta da imagem da entrada (as mãos da Criação de Adão), azul egípcio de dia (como as gravuras azuis de Delft e de toile) e cor de osso à noite (como as gravuras de Doré em fundo preto).
- **Centelha** (#2c4fae; #f3eee2 à noite): a luz no vão entre os dedos das mãos da entrada. De dia é só um halo azul; à noite, um halo e um ponto de luz cor de marfim. Não aparece em mais lugar nenhum.
- **Azul Egípcio** (#24418f; #a3b5f3 à noite): a face da tecla principal, o texto e o ícone da tela ativa, links, seleção de texto, cursor, a chave do meandro antes de cada título, a tinta do anel dos medalhões e do medidor, a trava ligada, as próximas vezes no relógio de sol, o meandro que fecha na entrada e o ponto de informação (em andamento, este aparelho).
- **Azul Fundo** (#1a3275; #bfcdf7 à noite): só o hover da tecla principal.
- **Véu Azul** (#e9edf7; #1b2441 à noite): o fundo do que está escolhido ou sob o dedo: o marcador da tela ativa na barra e no trilho, a tecla do "Mais" ativa, o item marcado da paleta, a trava ligada, o degrau aceso da crepidoma e a linha dele na legenda.
- **Tinta sobre o Azul** (#f7f8fc; #0b0f1a à noite): o texto da tecla principal e da seleção. À noite o azul clareia e a tinta sobre ele escurece.
- **Foco** (#24418f; #a3b5f3 à noite): o contorno de foco do teclado; é o próprio azul.

### Tertiary
- **Malaquita** (#2b8059; #57b98a à noite): o ponto de "no ar", "ok", "concluído", e os pontos dos containers no piso de cada degrau.
- **Tinta de Malaquita** (#1c6946; #7fd0a8 à noite): o texto do selo ok, ao lado do ponto.
- **Ocre** (#b07c1e; #d6a24a à noite): o ponto de "perto do limite" e a tinta do anel e do medidor quando a medida chega perto do limite; fora do estado, a contagem de aprovações esperando, o ícone e a borda da faixa de aprovações.
- **Ocre Claro** (#f7f1e4; #231d10 à noite): o fundo da faixa de aprovações.
- **Tinta de Ocre** (#6e4706; #e8bf74 à noite): o "Ver" da faixa.
- **Cinábrio** (#c23a26; #e8705c à noite): o ponto de falha (com um halo de 3px a 18%), a tinta do anel e do medidor que passou do limite, os pontos ruins de um degrau (que pulsam) e a borda da tecla de perigo.
- **Cinábrio Claro** (#f9e8e4; #2d1714 à noite): a face do degrau com problema e o hover da tecla de perigo.
- **Tinta de Cinábrio** (#a22d1b; #f19a8a à noite): mensagens de erro, o selo ruim, o texto da tecla de perigo, o nome da zona com problema e a lista dos containers dela.
- **Pedra** (#c6ccc9; #343d52 à noite): o ponto sem estado (o PC desligado, a trava desligada).

### Neutral
- **Chão de Mármore** (#f0f1ef; Noite Azul #0b0f1a): o fundo da página e o `theme-color` do navegador.
- **Casca** (#f6f7f6; #0e1320 à noite): o topo do celular e o trilho do PC.
- **Placa** (#fcfcfb; #121827 à noite): módulos, janelas, teclas e as faces dos degraus.
- **Placa Funda** (#f4f5f4; #0e1320 à noite): campos em repouso, hover de teclas, as teclas do "Mais", as marcas do esqueleto e o texto de um pedido.
- **Veio** (#e1e4e2; #1f2738 à noite): a borda dos módulos e das janelas, as divisórias entre itens, a régua depois do título do módulo, o fio das sublistas e o meandro apagado dos medalhões.
- **Veio Forte** (#b8bfbb; #374157 à noite): o contorno das teclas, dos campos e das travas, o fundo apagado do medidor, a borda do relógio de sol e a barra de rolagem.
- **Tinta** (#151b27; #e7e9ee à noite): o texto principal e o gnômon do relógio.
- **Tinta Segunda** (#556070; #a3acba à noite): rótulos, detalhes, códigos, placeholders, os ícones em repouso e as folhas do ramo de oliveira.
- **Tinta de Ornamento** (#9aa3ad; #4f5a72 à noite): só o meandro fino da casca, da faixa do nome da tela, do relógio de sol e da moldura da entrada no PC.
- **Noite** (#141a27; #06090f no tema escuro) e **Tinta da Noite** (#e4e8ee): o fundo e o texto dos textos de máquina (registros e avisos), escuros nos dois temas.

### Named Rules
**A Regra do Azul Único.** O azul egípcio é o único acento. Ele marca a ação principal (uma por módulo ou janela), onde o dono está (a tela ativa, o item marcado, o foco) e o que mede (o anel, o medidor). Nenhum outro matiz entra como enfeite ou como ação.

**A Regra dos Pigmentos de Estado.** Malaquita, ocre e cinábrio só dizem estado: como pontos, sempre com o texto do lado escrito na tinta deles; na tecla de perigo e no erro; e no anel ou no medidor, que só trocam o azul por ocre perto do limite e por cinábrio passado dele. Fora do estado, só o ocre aparece, e só nas aprovações: a faixa e a contagem.

**A Regra do Ornamento Mudo.** A Tinta de Ornamento (2,5:1 sobre a placa) é só para o ornamento (o meandro fino, a geometria da entrada), nunca para texto. Todo texto usa Tinta ou Tinta Segunda (6,2:1 sobre a placa de dia, 7,7:1 à noite).

**A Regra da Noite dos Textos de Máquina.** Registros e avisos ficam na Noite nos dois temas. O ponto do aviso usa os pigmentos da noite fixos (#a3b5f3 informação, #57b98a ok, #e8705c erro), porque o fundo dele não muda com o tema.

## Typography

**Display Font:** Commissioner (com system-ui, sans-serif), variável em peso (100 a 900) e nos eixos FLAR (a serifa que se abre) e VOLM
**Body Font:** Commissioner (com system-ui, sans-serif), com FLAR e VOLM em 0
**Label/Mono Font:** a monoespaçada do sistema (ui-monospace, SF Mono, Cascadia Mono, Roboto Mono, Menlo), só para textos de máquina

**Character:** Commissioner é de Kostas Bartsokas, tipógrafo grego, e tem o grego de verdade, não um latim fantasiado. Com os eixos FLAR e VOLM ligados, os traços abrem em serifas de pedra, como letra gravada; desligados, ela é uma sem-serifa calma para ler. Os títulos e os números ficam na letra de pedra; o texto corrido, na letra lisa. Sai de dois arquivos `.woff2` servidos pelo próprio painel (latim e grego, separados por `unicode-range`), com `font-display: swap` e o latino pré-carregado.

### Hierarchy
- **Inscrição** (500, 1.1rem; 1.3rem no trilho e 1.7rem na entrada; espaço .28em; altura 1; pedra 100/100): o ΑΘΗΝΑ da marca, em letras gregas, escondido do leitor de tela, que lê "Atena".
- **Título da Tela** (400, clamp(1.7rem, 1.2rem + 1.7vw, 2.5rem), altura 1.05, espaço -.015em, pedra 100/100): o nome da tela, em cima da faixa de meandro. É a maior letra do painel.
- **Número** (350, 2.4rem, altura 1, espaço -.025em, algarismos tabulares e alinhados, pedra 100/100): o número de leitura num módulo (o gasto do mês, a próxima vez da agenda), com a unidade ao lado na letra lisa a .82rem. No medalhão, o mesmo número a clamp(1.55rem, 1.15rem + 1.2vw, 2.05rem), com a unidade a .42em, peso 500, na Tinta Segunda.
- **Título de Módulo** (500, 1.02rem, altura 1.2, pedra 100/100): o título de cada módulo, depois da chave do meandro, e o título das janelas.
- **Corpo** (400, 1rem, altura 1.5, pedra 0/0): o texto corrido e os valores das linhas. A pergunta de um pedido do Claude Code sobe para 1.05rem; o texto de um pedido fica em .92rem, altura 1.55.
- **Corpo Fraco** (400, .875rem, Tinta Segunda): explicações, metadados, estados vazios.
- **Detalhe** (400, .82rem, altura 1.4, algarismos tabulares, Tinta Segunda): a linha de baixo de cada item, com o estado escrito primeiro ("no ar há 6 h · saudável · CPU 0,3%").
- **Rótulo** (550, .8rem, espaço .005em, pedra 100/50, caixa comum): rótulos de linha e de campo. A mesma letra faz o `h3` (.9rem), o selo (.76rem), os nomes da barra e das zonas (.72rem), os grupos do trilho (.74rem, com inicial maiúscula), o nome do medalhão e da zona na crepidoma (.86rem) e o grupo na paleta (.76rem).
- **Tecla** (550, .86rem, altura 1.1, espaço .01em): o texto das teclas; .8rem nas discretas; .95rem nas grandes de decisão e na entrada.
- **Trilho** (500, .92rem; 600 na tela ativa): os nomes das telas no trilho do PC.
- **Máquina** (monoespaçada do sistema): registros a .74rem, altura 1.55; o editor de stacks a .8rem, altura 1.5; as linhas da Atividade em 500 a .78rem; o caminho dos arquivos em 500 a .78rem; o atalho (`kbd`) em 600 a .66rem.

### Named Rules
**A Regra da Inscrição.** A caixa-alta só existe na inscrição grega: o ΑΘΗΝΑ da marca. Títulos, rótulos, selos, nomes da barra e grupos do trilho ficam em caixa comum; nenhum estilo usa `text-transform: uppercase`.

**A Regra da Serifa de Pedra.** A serifa de pedra (FLAR 100, VOLM 100) é dos títulos, dos números e da inscrição; os rótulos usam a meia pedra (FLAR 100, VOLM 50); o corpo e as unidades ao lado dos números, a letra lisa (FLAR 0, VOLM 0).

**A Regra do Número de Verdade.** Todo número vem do executor e se escreve como aqui (15,0 GB, US$ 0,98, 1.304 RPM, 0,3%), pelo `num()`, `gb()`, `dinheiro()` e `plural()` do `comum.js`, em algarismos tabulares; o que vem em outro formato (o `54.68MiB` do docker stats) é traduzido antes de entrar na tela. A interface nunca inventa um número.

## Layout

O celular e o PC têm o mesmo peso; nenhum é a versão capada do outro.

**Celular (abaixo de 60rem).** No topo, na Casca, o ΑΘΗΝΑ à esquerda e os pontos das zonas à direita, cada um com o nome embaixo; a borda de baixo do topo é o meandro fino (.42rem de altura, em Tinta de Ornamento). A faixa de aprovações, quando há, vem antes do nome da tela. O conteúdo é uma grade de colunas automáticas de no mínimo 21rem (uma coluna no telefone), com .9rem entre módulos, margem lateral de .75rem e respiro de baixo do tamanho da barra (4.4rem) mais a área segura e 1.25rem. A barra fixa embaixo tem cinco itens (Início, PC, Agenda, Serviços e Mais) sobre a Placa a 94%, com desfoque de 14px e um fio de Veio em cima; o "Mais" abre a folha com as outras telas num teclado de três colunas. Abaixo de 40rem, as teclas discretas estreitam (.4rem por .64rem).

**PC (a partir de 60rem).** Duas colunas: o trilho fixo de 15.5rem à esquerda, na Casca, da altura da tela, com o meandro fino descendo pela borda direita; no alto o ΑΘΗΝΑ (1.3rem) e os pontos das zonas, depois os grupos hoje, servidor, máquina, registro e conta, e a tecla Buscar com Ctrl K no pé. A área de trabalho vai até 82rem, com 1.8rem em cima, 2.2rem nos lados e 2.5rem embaixo. A tela do PC fica numa coluna só de até 46rem.

**Módulo estreito.** Cada módulo é um container de CSS (`container: modulo`). Abaixo de 26rem, o que ele mede desce para baixo do título, inteiro, alinhado depois da chave; abaixo de 30rem, as linhas com mais de uma tecla põem as teclas embaixo do nome; abaixo de 19rem, a crepidoma empilha a escada sobre a legenda; a partir de 46rem, as linhas de registro põem o nome (15rem) e o detalhe lado a lado.

**A entrada.** No celular, as mãos atravessam a tela de ponta a ponta (128vw), com o vão entre os dedos no meio dela, e embaixo fica a frente, com até 22rem: o ΑΘΗΝΑ, o rótulo, o campo e a tecla principal, ambos com 3rem de altura. No PC, as mãos ficam em cima, largas (min(92vw, 64rem)), e a entrada embaixo, numa coluna de 21rem, 2.5rem abaixo delas. Sem moldura: a entrada fica solta na tela.

**Ritmo.** Teclas a .45rem umas das outras (.4rem nas linhas); o módulo tem 1.15rem em cima e 1.25rem nos lados e embaixo; o cabeçalho do módulo fica 1rem acima do conteúdo; os itens têm .75rem de respiro e 1px de Veio entre eles; os medalhões ficam numa grade auto-fit de no mínimo 8.2rem, com 1.2rem por 1.3rem de folga.

### Named Rules
**A Regra das Colunas de Jornal.** No PC, a tela é um fluxo de colunas CSS: duas colunas, e colunas automáticas de 21rem nas Aprovações; o Início é uma lâmina só, composta por inteiro (veja O Início). Cada módulo leva `break-inside: avoid`; o módulo largo, a faixa de aprovações e o cabeçalho da tela atravessam todas as colunas com `column-span: all`. Os módulos têm a altura do que mostram.

**A Regra do Polegar.** No celular, as telas de todo dia ficam na barra de baixo, em itens de 3.5rem de altura; com toque grosso (`pointer: coarse`), toda tecla tem no mínimo 2.75rem.

## Elevation & Depth

O mármore é plano. A profundidade vem das camadas de tom (o chão, a casca um pouco acima, a placa por cima) e de uma sombra ambiente quase sem peso embaixo dos módulos; só as janelas sobem de verdade. A única profundidade desenhada é a crepidoma: a escada das zonas em 3D real (perspectiva de 1100px, inclinada a 56° e girada a -30°, com `transform-style: preserve-3d`), cujas faces são a Placa misturada com a Tinta (o espelho a 14%, o lado a 26%) e contornadas pela Tinta a 20%.

### Shadow Vocabulary
- **Sombra do Mármore** (`box-shadow: 0 1px 1px rgb(21 27 39 / .03), 0 12px 32px -20px rgb(21 27 39 / .22)`; à noite `0 1px 1px rgb(0 0 0 / .3), 0 14px 36px -20px rgb(0 0 0 / .8)`): os módulos.
- **Sombra Alta** (`box-shadow: 0 30px 80px -24px rgb(10 14 26 / .45)`): janelas, a folha "Mais" e a paleta, sobre um fundo de `rgb(10 14 26 / .42)` com desfoque de 3px.
- **Brilho da Tecla Principal** (`box-shadow: 0 1px 0 rgb(255 255 255 / .12) inset, 0 6px 16px -8px color-mix(in srgb, var(--azul) 70%, transparent)`): só na tecla azul.
- **Sombra do Aviso** (`box-shadow: 0 18px 40px -16px rgb(0 0 0 / .55)`): os avisos na Noite.
- **Anel de Foco do Campo** (`box-shadow: 0 0 0 4px color-mix(in srgb, var(--azul) 14%, transparent)`): o campo em foco, junto com a borda azul.
- **Halo do Cinábrio** (`box-shadow: 0 0 0 3px color-mix(in srgb, var(--cinabrio) 18%, transparent)`): só o ponto de falha.

### Named Rules
**A Regra da Única Escada.** A crepidoma é o único 3D do painel. Módulos e teclas ficam planos: nenhuma sombra deslocada, nenhum lado de tecla, nenhum relevo. Nada flutua além das janelas, da folha, da paleta e dos avisos.

## Shapes

Cantos discretos e quase iguais: 6px em quase tudo (módulos, teclas, campos, travas, a faixa, os itens do trilho e da paleta, registros); 10px nas janelas, nos avisos e nas teclas do "Mais"; 18px nos cantos de cima da folha; 12px no marcador da barra; 3px no atalho e nas marcas do esqueleto. Pontos de estado, medalhões, o relógio de sol e o medalhão da entrada são círculos.

**O meandro.** Um traço só, que entra na espiral e sai pela base até a volta seguinte; cada volta ocupa 4 unidades de largura por 3 de altura (`desenhos.js`). Ele aparece de cinco jeitos: como máscara repetida (`--meandro` e `--meandro-em-pe`, traço de 1.2 numa célula de 16 por 14) na borda da casca, na moldura da entrada e no medidor; como faixa desenhada (traço de 1.3, quinas em ponta) sob o nome de cada tela e no esqueleto; como chave, uma volta só em azul, de .95rem por .72rem, antes de cada título de módulo; dando a volta num círculo, fechado sem emenda, na borda dos medalhões, do relógio de sol e da entrada; e como medida, pintado até o valor.

**Os medalhões** (Sistema e PC). Dois aros finos de Veio (.6), o meandro circular apagado em Veio (1) e, por cima, o mesmo meandro em tinta (1.7) pintado até a fração em voltas inteiras (um valor acima de zero pinta ao menos uma). No miolo, o número na letra de pedra ou um desenho (o ícone do PC, a roseta de oito pétalas que gira na velocidade da ventoinha).

**Os ícones.** Desenhados em `pictos.js`, numa grade de 24, com traço de 1.5 (1.05 nos finos), pontas e quinas redondas, em `currentColor`. As coisas gregas entram no lugar das de sempre quando dizem o mesmo: o Início é a frente do templo, as Aprovações uma coroa de louros com o visto, os Serviços uma ânfora, o Sistema a engrenagem de Anticítera, o Histórico uma ampulheta, os Arquivos um pergaminho. A área "tinta" (o tímpano, a faixa da ânfora, o líquido do frasco) fica vazia em repouso e se pinta a 16% na tela ativa.

**A imagem da entrada.** As mãos de Deus e de Adão na Criação de Adão, o afresco de Michelangelo na Capela Sistina, de uma foto em domínio público: recortadas do reboco, com os antebraços se apagando para as bordas, e tonalizadas como uma impressão numa cor só. O arquivo (`app/public/gravuras/criacao-de-adao.webp`, 1200 por 389) guarda a tinta no cinza e o recorte no alfa, e é desenhado num canvas (`gravura()` em `desenhos.js`) na Tinta da Gravura, na densidade do aparelho: de dia a tinta, adensada; à noite o claro da pintura, e as mãos ficam claras sobre o escuro. A estética é a das gravuras e impressões clássicas numa cor só, nunca a de desenho animado ou de personagem; a imagem precisa ser nítida na densidade do celular (dedos legíveis).

**O fundo da entrada.** Atrás da entrada, o reboco do céu do mesmo afresco, com as rachaduras de verdade (`app/public/gravuras/reboco.webp`, só máscara), na cor da Tinta a 5%, quase invisível, derivando devagar. No vão entre os dedos, a centelha: um halo que respira e, à noite, um ponto de luz. Dentro do painel o chão é liso; o fundo dele fica para depois.

### Named Rules
**A Regra do Meandro que Mede.** O meandro é ornamento e é medida. Uma fração se mostra pintando o meandro (o anel do medalhão, o medidor), nunca numa barra lisa ou num anel liso; e o ornamento é sempre o mesmo traço, nunca um friso de outra forma.

**A Regra do Traço que Nasce do Conteúdo.** Nenhum enfeite tem lugar fixo. O desenho aparece onde algo acontece (a lista que esvaziou, o serviço que caiu, o pedido que você aprovou, o fim da lista a que você chegou), se desenha naquela hora como pena ou buril e depois fica quieto. Ilustração é gravura antiga em domínio público; o que se desenha em código é geometria (o meandro, o louro, a rachadura, a esfera).

## Components

### Buttons
Teclas de mármore: um fio na cor do texto, sem relevo; o azul só na ação principal.
- **Shape:** cantos de 6px, contorno de 1px em Veio Forte.
- **Padrão:** face Placa, texto Tinta, 550 a .86rem, .5rem por 1rem, altura mínima de 2.5rem (2.75rem com toque grosso). Ícone de 1.15rem antes do texto, a .45rem.
- **Principal:** face e borda Azul Egípcio, texto Tinta sobre o Azul, com o brilho da tecla principal. Uma por módulo ou janela (Entrar, Ligar, Aprovar).
- **Discreta:** sem fundo, menor (.4rem por .78rem, altura 2.2rem, .8rem de texto). É a tecla das ações de cada linha (Logs, Reiniciar, Editar) e das secundárias (Atualizar, Fechar, Adicionar).
- **Perigo:** texto em Tinta de Cinábrio e borda de Cinábrio misturado ao Veio (45%); no hover, fundo Cinábrio Claro e borda Cinábrio. Toda ação que não tem volta pede confirmação antes.
- **Grandes:** na decisão (Aprovar e Recusar, Ligar), as teclas dividem a largura e sobem para 3.1rem, com .95rem de texto e ícone de 1.3rem.
- **Hover / Focus / Active:** no hover, fundo Placa Funda e borda Tinta Segunda (a principal vai ao Azul Fundo); no foco do teclado, contorno de 2px em Foco a 2px de distância; ao apertar, encolhe a 97%. As transições são de .2s em `--suave` (.16s no aperto). Desabilitada, fica a 45%.

### Chips
- **Ponto de estado:** um círculo de .5rem em Malaquita (ok), Ocre (perto do limite), Cinábrio (falha, com halo), Azul (informação, em andamento) ou Pedra (sem estado).
- **Selo:** ponto de .45rem e a legenda em Rótulo a .76rem, na tinta do pigmento (Malaquita, Cinábrio) ou em Azul (neutro, como "este" aparelho).
- **Contagem:** pílula de 1.15rem em Ocre, com o número de aprovações esperando em 700 a .64rem, presa ao item das Aprovações e do "Mais". O número sai num ocre quase preto (#1b1307), com 5,0:1 sobre o ocre de dia e 8,0:1 à noite; branco ali não chegava a 4,5:1.
- **Atalho (`kbd`):** monoespaçada 600 a .66rem, contorno de Veio Forte, cantos de 3px, Tinta Segunda.

### Cards / Containers
- **Corner Style:** 6px no módulo; 10px nas janelas.
- **Background:** Placa.
- **Shadow Strategy:** Sombra do Mármore (ver Elevation & Depth).
- **Border:** 1px de Veio.
- **Internal Padding:** 1.15rem em cima, 1.25rem nos lados e embaixo.
- **Cabeçalho (`modulo()`):** a chave do meandro em azul, o título de módulo, uma régua de 1px em Veio que ocupa o meio e, à direita, o que o módulo mede (.8rem, Tinta Segunda, algarismos tabulares, cortado com reticências se não couber). Sempre dado de verdade.
- **Linhas:** rótulo à esquerda e valor com algarismos tabulares à direita (`linha()`); o medidor logo abaixo quando há uma fração.
- **Largo:** o módulo largo ocupa a linha toda; no PC, os medalhões dele se espalham numa linha só.
- **Detalhes:** o `summary` leva uma seta de .72rem que gira 90° numa mola ao abrir; o que estava aberto continua aberto quando a tela se refaz.

### Inputs / Fields
- **Style:** fundo Placa Funda, contorno de 1px em Veio Forte, cantos de 6px, .5rem por .7rem, altura mínima de 2.5rem, Commissioner .95rem. Selects e campos com lista levam a seta própria em SVG, na Tinta Segunda.
- **Focus:** a borda vira Azul, o fundo sobe para a Placa e aparece o anel de foco de 4px do azul a 14%.
- **Campo (`campo()`):** o rótulo em cima do controle; num formulário, os campos ficam numa grade de colunas automáticas de no mínimo 9rem, e os largos ocupam a linha toda.
- **Travas:** para escolhas que ficam ligadas (os dias da semana), teclas pequenas de no mínimo 2.8rem com um ponto de Pedra no alto; ligadas, ficam no Véu Azul com texto e ponto azuis, e o ponto cresce a 115% numa mola.
- **Caixa de seleção:** a do sistema, com o azul como cor de destaque.
- **Error / Disabled:** a mensagem de erro sai em Tinta de Cinábrio logo abaixo, com a altura de uma linha reservada para não pular a tela.

### Navigation
- **Barra (celular):** cinco itens transparentes, ícone de 1.4rem e o nome em Rótulo a .72rem, na Tinta Segunda. A tela ativa fica azul, a tinta do ícone acende e, atrás dela, o marcador em Véu Azul (cantos de 12px) desliza até lá numa mola. A contagem vai no "Mais".
- **Trilho (PC):** grupos com o título em Rótulo a .74rem; cada tela é um item com ícone de 1.2rem e nome a .92rem. A ativa fica azul, em 600, com o mesmo marcador deslizante em Véu Azul (cantos de 6px). A contagem fica à direita das Aprovações.
- **Mais (folha):** sobe de baixo numa mola, com cantos de 18px no topo, e mostra as outras telas e a Buscar como teclas de Placa Funda num teclado de três colunas; no hover e na ativa, Véu Azul com texto azul.
- **Paleta (Ctrl+K):** janela a 12% do topo, até 36rem, com campo grande de 3rem; cada item mostra o ícone, o título e o grupo em Rótulo à direita. Setas movem a marcação, Enter executa; o item marcado fica no Véu Azul, com o ícone azul e a tinta acesa.

### Linhas de lista
Toda lista do painel é feita de linhas iguais (`item()` e `itens()` no `comum.js`), separadas por 1px de Veio.
- **Estrutura:** o ponto do estado numa coluna de .5rem, o nome (o de stack, app ou agendamento em 600) com o Detalhe embaixo, e as teclas discretas à direita. O nome tem sempre ao menos 13rem; as teclas ficam com o que sobra e quebram de linha.
- **Estado:** o ponto diz o estado e o detalhe começa por ele escrito ("no ar", "falhou", "pausado").
- **Teclas embaixo:** com quatro teclas ou mais, ou mais de uma num módulo estreito, elas descem para baixo do nome, alinhadas com ele.
- **Presas a outra:** os containers de uma stack e as execuções de um agendamento ficam embaixo dela, presos por um fio de 1px de Veio à esquerda.
- **Registros:** na Atividade, uma linha por evento, com o nome na monoespaçada.

### O Início
A primeira tela é uma lâmina só, composta como uma prancha impressa, e não um painel de cartões: nada nela tem placa, sombra ou borda de cartão. No alto, a data na Tinta Segunda e a frase do dia, escrita a partir dos dados na letra de pedra (1.28rem no celular, 1.55rem e centrada no PC): primeiro o que está errado (o container que caiu, a unidade que falhou, a leitura que passou do limite), depois o que espera você (aprovações e pendências), por fim o próximo agendamento; sem nada errado, "Tudo em ordem". Um filete duplo de Veio Forte fecha o alto. No meio, o monumento: o instrumento do servidor de pé numa haste sobre a crepidoma das zonas (o servidor apoiado nas zonas), com a legenda das letras dos dois lados do disco e as linhas de chamada apontando para ele, e o título embaixo ("Prancha I · o servidor…, sobre as zonas…"). Nas margens, as notas, que são o módulo sem a placa (o título com a chave e a régua, e o conteúdo direto no mármore): à esquerda, "O que pede você" (só quando há algo: os pedidos, com "Ver", o que caiu e o que falhou, com a rachadura) e as pendências; à direita, os próximos agendamentos, o gasto de IA e o systemd. Na folha larga (75rem ou mais), as margens têm 16rem e um filete duplo as separa do monumento; entre 60rem e 75rem, o monumento atravessa e as notas vão em duas colunas embaixo; no celular, tudo numa coluna, na ordem de leitura (o que pede você, o monumento, a agenda, o gasto, o systemd, as pendências). A faixa de aprovações não aparece no Início.

### Instrumento do Servidor
Um disco de prancha científica antiga (até 17.5rem; 18rem no PC, com a legenda ao lado): a graduação de 72 marcas (as de 30° mais longas) e o aro fino em volta, o eixo do zero no alto e, de fora para dentro, um anel por leitura (CPU, RAM, temperatura da CPU, GPU, cada disco; até seis), cada um com duas bordas finas de Veio Forte e a tinta em hachura (traços a 35°) pintada desde o zero até o valor, no tom do limite (azul, ocre perto dele, cinábrio passado dele). As letras gregas (Α, Β, Γ, Δ, Ε, Ζ) ficam no eixo do zero, ao lado do começo de cada anel, e a legenda embaixo diz o que cada letra é, com o valor e a nota. No meio, uma estrela de oito pontas. Na primeira vez, a graduação se grava em volta, as bordas e o eixo se traçam e a tinta se pinta; depois, quando um valor muda, a tinta anda do valor anterior ao novo (1s).

### Medalhões
A leitura do servidor (CPU, temperatura, RAM, GPU; o PC e o LM Studio; as ventoinhas): um disco de até 9.6rem com o número no meio e o meandro da borda pintado de azul até o valor, em voltas inteiras. Perto do limite (a 85% do alerta) a tinta passa a Ocre; passado dele, a Cinábrio. Embaixo, o nome em Rótulo a .86rem e uma nota a .78rem na Tinta Segunda. Ao chegar, o anel se pinta do zero até o valor em 1.3s; quando o valor muda, a tinta anda até o novo em 1s.

### Crepidoma das Zonas
A assinatura do painel: a escada do templo, um degrau de mármore de 7.2rem por zona (a zona de base embaixo, cada uma acima mais atrás e mais alta) e, no piso de cada degrau, um ponto de .36rem por container, em Malaquita ou em Cinábrio pulsando. Ao lado, a legenda que se lê e se toca: o ponto, o nome da zona, a conta "no ar/total" na letra de pedra e, se houver, os containers com problema em Tinta de Cinábrio. Passar por um degrau ou por uma linha acende os dois em Véu Azul (o degrau também se adianta .5rem); tocar abre os Serviços na zona. A zona com problema escorrega .9rem para o lado, como uma pedra deslocada, com a face em Cinábrio Claro.

### Relógio de Sol
O mostrador da agenda: 24 horas num disco com o meandro circular na borda, marcas a cada hora (mais fortes a cada seis), os numerais 0, 6, 12 e 18 na letra de pedra, a sombra (uma cunha de Tinta a 7% e o gnômon) na hora de agora e as próximas vezes das 24 h como pontos azuis, a primeira maior. Ao lado, a próxima vez e a conta do dia em Número.

### Faixa de Aprovações
No topo de qualquer tela quando há pedido esperando, menos nas Aprovações e no Início (lá o "O que pede você" mostra os pedidos): uma faixa de Ocre Claro com borda de Ocre a 38%, o ícone da coroa de louros em Ocre, "N aprovações esperando você" em 600 a .98rem e, à direita, "Ver" com a seta em Tinta de Ocre. No hover, a borda fica Ocre cheia. Atravessa todas as colunas no PC.

### A Entrada
As mãos da Criação de Adão direto sobre o chão, sem moldura, com o reboco do afresco quase invisível atrás e a centelha no vão entre os dedos. Embaixo das mãos, o ΑΘΗΝΑ a 1.7rem, o campo da senha e a tecla principal Entrar. Na senha errada, o ΑΘΗΝΑ fica em cinábrio por 1,6 s; na certa, ele fica azul e a imagem se desfaz no mesmo pontilhado em que se imprimiu.

### Avisos e Textos de Máquina
- **Aviso:** retângulo de Noite com cantos de 10px, texto a .85rem em Tinta da Noite e um ponto de .5rem à esquerda (azul informação, malaquita ok, cinábrio erro, nos tons da noite). Fica acima da barra no celular e no canto de baixo à direita no PC; some em 4s (8s se for erro). Com uma janela aberta, vai dentro dela.
- **Registro:** os logs em Noite, monoespaçada a .74rem, cantos de 6px, rolagem própria até 60% da altura.
- **Texto de pedido:** em Placa Funda com 1px de Veio, na letra lisa a .92rem.

### Esqueleto
A tela que ainda não chegou mostra duas placas já postas, uma faixa de meandro que se faz e se desfaz (2s, em `--traco`) e, no lugar de cada linha, uma hachura de Veio Forte (traços a -58°, de 1px a cada 5px) traçada da esquerda para a direita e apagada, uma linha depois da outra (2.4s). O que espera uma resposta curta (abrir um arquivo, procurar, rodar um comando) leva a mesma hachura embaixo do texto (`carregando()`). A tela já vista volta na hora com o que mostrava, na mesma altura da rolagem, até o dado novo entrar por cima.

### O Traço do Sistema
O ornamento do painel não tem lugar fixo: ele nasce do conteúdo, onde algo acontece, do tamanho do que acontece, e se desenha na hora, como pena ou buril, para depois ficar quieto (`ornamentos.js`). Cada desenho tem uma chave com o estado dele e corre uma vez por sessão; nas atualizações da tela ele já vem pronto. São quatro famílias:
- **Quem carrega hachura:** o esqueleto e o `carregando()`, acima.
- **O gesto deixa um traço** em volta do que você tocou, em Azul Egípcio, quando a ação dá certo, e some em seguida: o louro (dois ramos em parênteses, com folhas alternadas) ao aprovar um pedido ou publicar um app, e a tela espera ele terminar antes de tirar o pedido; o círculo de pena (uma volta e um pouco, fechando para dentro) em volta do nome do que você reiniciou; os raios (24, longos e curtos) em volta do medalhão do PC quando ele liga.
- **O vazio e o fim:** a lista vazia ganha uma vinheta de gravura antiga de 5.5rem, gravada a buril (em passadas na direção da hachura, cada uma começando numa hora), na Tinta da Gravura, com o texto embaixo (`vazio(texto, figura)`). São quatro aves em xilogravura do livro de Pierre Belon de 1555, todas com o nome grego na legenda: a coruja (a vigília) nas Aprovações, o galo (as horas) na Agenda, a andorinha (a que constrói o ninho) no Lab e a pega (a que guarda) na Atividade e no Histórico. A lista longa (8 linhas ou mais) da Atividade, do Histórico e dos Arquivos termina com um fecho de livro em Tinta de Ornamento, um losango com dois ramos em S, que se desenha do meio para fora quando você chega ao fim.
- **O dado vira desenho:** o que caiu (um container fora do ar, uma unidade do systemd com falha) ganha uma rachadura em Cinábrio a 50% saindo da borda de cima da linha dele, como o reboco do afresco, sempre com a mesma forma para o mesmo nome. Na Rede, a esfera armilar: um anel por alcance (só o servidor, containers, rede de casa, Tailscale, todas as redes), do servidor para fora, com um ponto Azul por porta aberta nele (Cinábrio nas abertas para todas as redes), o eixo e o servidor parados no meio, girando devagar (90s por volta); ao lado, os alcances com a conta de portas.

### Movimento
Três curvas, todas em custom properties: `--suave` (cubic-bezier(.22, 1, .36, 1), sai rápido e assenta devagar) para o dia a dia; `--mola` (uma mola amortecida escrita em `linear()`, que passa 1,5% do alvo e assenta) para o que se assenta no lugar; `--traco` (cubic-bezier(.65, 0, .25, 1)) para o traço que se desenha.
- **Trocar de tela:** uma View Transition: a tela velha se apaga em .16s (desfoque de 3px, sobe 4px) e a nova chega do desfoque de 8px em .46s, subindo 14px. A barra e os avisos têm camada própria e não se mexem. Onde o navegador não tem a API, o conteúdo só aparece.
- **O conteúdo que chega:** aparece todo junto, em .35s de opacidade; o que se mexe é o que mede (o anel se pinta, os degraus sobem um a um, de baixo para cima, a 75ms um do outro, e assentam na mola).
- **A tela ativa:** o marcador desliza na mola (.62s) e o ícone dela se redesenha (.6s em `--traco`); enquanto a tela lê do servidor, o ícone ativo respira de leve.
- **Janelas, folha e avisos:** chegam na mola (.5s, .55s, .55s); as janelas e os avisos vêm de um desfoque de 4px.
- **Contínuos:** só os que leem um dado ou dão vida à assinatura: a escada respira devagar (12s, ida e volta), o ponto ruim pulsa (1.8s), a roseta gira na velocidade da ventoinha.

**A Regra da Mola que Assenta.** A mola é só do que assenta no lugar: o marcador da tela ativa, as janelas, a folha, os avisos, os degraus da crepidoma, a seta dos detalhes, o ponto da trava, e os pontos das zonas ao chegar. Todo o resto é ease-out em `--suave`. Nada de quique, tremor ou cascata de módulos.

**A Regra do Que Não Fica.** Animação de opacidade ou desfoque num módulo, na tela ou num degrau usa `animation-fill-mode: backwards` (ou nenhum), nunca `forwards` nem `both`: uma opacidade ou um filtro que ficasse no elemento achataria o 3D da crepidoma.

**A Regra da Cena nos Momentos.** A cena só acontece quando importa: ao entrar, as mãos se imprimem por um pontilhado ordenado (a matriz de Bayer 8×8, em pontos de 2 px; 1,9s), que se adensa das bordas para o vão entre os dedos e da tinta mais escura para a mais clara, e o ΑΘΗΝΑ chega letra a letra; quando as mãos terminam, a centelha se acende no vão entre os dedos e respira (6s), e o reboco deriva quase parado (70s) enquanto a entrada está aberta; nada reage à digitação; na senha errada, a inscrição fica em cinábrio por um instante, e na certa ela fica azul e a imagem se desfaz no mesmo pontilhado antes de a entrada se desfazer e o painel chegar, com os pontos das zonas aparecendo um a um; quando chega uma aprovação, uma luz passa pela faixa e a coroa se redesenha, uma vez; quando um agendamento roda, a sombra do relógio de sol dá a volta (2.2s); quando o PC liga, o anel dele se pinta de novo; a zona com problema escorrega para o lado.

**A Regra do Parado.** Com `prefers-reduced-motion`, nada se move: animações, transições e View Transitions são desligadas, os traços aparecem já desenhados e o ícone que lia só fica a 60%.

### Proveniência
- **Fonte:** Commissioner, de Kostas Bartsokas, sob a SIL Open Font License 1.1, tirada do Fontsource 5.2.8. Os arquivos ficam em `app/public/fontes` (`commissioner-latin.woff2`, `commissioner-grego.woff2`) com a licença ao lado (`commissioner-LICENSE.txt`).
- **Ícone do app:** `app/public/icone.svg` é desenhado à mão: a chave do meandro (uma volta, num traço só de 30) em #f3f5f9 sobre um quadrado de cantos redondos em Azul Egípcio. `app/public/icone-192.png` e `app/public/icone-512.png` (o de 512 também como ícone mascarável) são renderizados desse SVG com o Chromium sem interface. Não há imagem gerada no painel.
- **A imagem da entrada:** `app/public/gravuras/criacao-de-adao.webp` vem de uma foto do afresco de Michelangelo feita por Jörg Bittner Unna (2011), reprodução fiel de uma obra em domínio público (PD-Art), pelo Wikimedia Commons. O preparo (o recorte com o GrabCut, a luz convertida em tinta e a redução) está em `app/public/gravuras/ORIGEM.txt`.
- **As vinhetas:** `app/public/gravuras/vinhetas/` (a coruja, o galo, a andorinha e a pega) vêm de *L'Histoire de la nature des oyseaux*, de Pierre Belon (1555), em domínio público, pelo Wikimedia Commons; as páginas, os recortes e o preparo estão em `app/public/gravuras/ORIGEM.txt`.
- **O reboco:** `app/public/gravuras/reboco.webp` é o céu da mesma foto do afresco, com a origem e o preparo em `app/public/gravuras/ORIGEM.txt`.
- **Desenhos e ícones:** o meandro, os medalhões, o instrumento do servidor, a crepidoma, o relógio de sol e os pictogramas são montados em código (`desenhos.js`, `pictos.js`, `estilo.css`) a partir dos dados de verdade; nada vem de biblioteca nem de outro endereço.

## Do's and Don'ts

### Do:
- **Do** montar todo módulo com `modulo()`: a chave do meandro, o título na letra de pedra, a régua de Veio e, à direita, o que ele mede, sempre dado de verdade.
- **Do** usar uma única tecla principal azul por módulo ou janela; as outras são de fio (Placa com contorno de Veio Forte), e as de cada linha e as secundárias são discretas.
- **Do** dizer todo estado com um ponto de pigmento e o texto do lado (`item()`, selo): Malaquita ok, Ocre perto do limite, Cinábrio falha, Azul informação ou em andamento, Pedra sem estado.
- **Do** medir com o meandro: `medalhao()` para uma leitura com limite, `medidor()` para uma fração numa linha; a tinta passa do azul ao ocre perto do limite e ao cinábrio passado dele.
- **Do** escrever números com `num()`, `gb()`, `dinheiro()` e `plural()`, em algarismos tabulares.
- **Do** desenhar ícones novos em `pictos.js`: grade de 24, traço de 1.5 em `currentColor`, pontas e quinas redondas, a área "tinta" onde os gregos pintariam e `pathLength` 1 nos traços, para o redesenho.
- **Do** pegar cor, raio, letra e curva das custom properties (`var(--azul)`, `var(--raio)`, `var(--letra)`, `var(--suave)`, `var(--mola)`) e mudar o tema só trocando valores sob `prefers-color-scheme: dark`.
- **Do** passar valores dinâmicos (`--fracao`, `--i`, `--volta`, a posição do marcador, a largura do medidor) pelo CSSOM, com `style.setProperty`: a CSP barra o atributo `style`.
- **Do** usar a mola só no que assenta, `--suave` no resto, e `animation-fill-mode: backwards` em toda animação de opacidade ou desfoque num módulo.
- **Do** deixar toda animação nova parada sob `prefers-reduced-motion`, com os traços já desenhados.
- **Do** manter os alvos de toque em 2.75rem no toque grosso e a barra embaixo no celular.
- **Do** pôr ornamento só onde algo acontece, pelo `ornamentos.js`: a hachura de quem carrega, o traço do gesto, a vinheta do vazio, o fecho da lista longa, a rachadura do que caiu, o dado desenhado. Cada um se desenha uma vez por estado e depois fica quieto.

### Don't:
- **Don't** usar caixa-alta fora das inscrições gregas (ΑΘΗΝΑ), nem `text-transform: uppercase`.
- **Don't** trazer um segundo acento, nem pintar com malaquita, ocre ou cinábrio o que não é estado (a única exceção é o ocre das aprovações).
- **Don't** escrever texto na Tinta de Ornamento.
- **Don't** medir com barra lisa ou anel liso: a medida é o meandro pintado.
- **Don't** pôr quique, tremor, cascata de módulos nem mola numa transição do dia a dia.
- **Don't** deixar opacidade ou filtro preso num módulo com `forwards` ou `both`: achata a crepidoma.
- **Don't** dar sombra deslocada, lado de tecla ou relevo a teclas e módulos: o 3D é só o dos desenhos de dado, a crepidoma e a esfera armilar.
- **Don't** pregar enfeite num lugar fixo (o canto do título, o rodapé de toda tela), nem repetir a mesma vinheta em todo lugar: o ornamento vem do conteúdo.
- **Don't** carregar fonte, script, estilo ou imagem de outro endereço, nem usar o atributo `style` inline: a CSP é `default-src 'self'` e o container não tem rede.
- **Don't** usar biblioteca de ícones nem caractere Unicode fazendo papel de ícone.
- **Don't** fazer a Grécia de souvenir (colunas de enfeite, dourado, creme), nem algo que pareça desenho animado, jogo ou fantasia, nem o dashboard de cartões cinza do SaaS genérico.
