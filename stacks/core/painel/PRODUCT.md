# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Uma pessoa: o dono de um servidor caseiro Atena, que também é quem o administra. Usa o painel no celular e no PC por igual. No celular, muitas vezes à noite ou fora de casa, para ver e agir rápido: aprovar um pedido, ligar o PC, conferir um alerta. No PC, com tempo: ler registros, editar uma stack, mandar trabalho ao Claude Code, montar a agenda.

## Product Purpose

O painel é o servidor no navegador e no celular (PWA): o estado da máquina e dos serviços, as decisões que a Atena e o Claude Code esperam do dono, o lab, a agenda, os arquivos e o histórico. Dá certo quando o dono resolve o que veio resolver sem abrir um terminal e sabe, em um olhar, se está tudo bem.

## Positioning

É o painel de um servidor de uma pessoa só, não um produto SaaS de monitoramento. Ele não age sozinho: tudo passa por um executor com lista fechada de ações, e o próprio painel roda sem rede. Quem age no servidor no dia a dia é a assistente (a Atena) e o Claude Code; o painel é onde o dono vê o que eles fazem e decide.

## Operating Context

- Entrada só pelo Tailscale (HTTPS do `tailscale serve`), com senha e sessão de 30 dias; instalado como app no Chrome do Android e aberto no navegador do PC.
- Avisos chegam ao celular pelo ntfy; a Atena conversa pelo Telegram e pelo WhatsApp. O painel convive com esses canais: o que se aprova no celular também aparece nele.
- Telas atuais: Início, Aprovações, Serviços (com editor das stacks de apps), Sistema, PC, Rede (os aparelhos da rede de casa, só ver), Lab (apps e Claude Code), Agenda, Arquivos, Atividade, Histórico, Ajustes.

## Capabilities and Constraints

- Sem dependências do npm: servidor em Node 22 (TypeScript direto), interface em JavaScript puro, sem framework e sem build.
- CSP `default-src 'self'`: nada de script, estilo ou fonte de outro endereço, nem atributo `style` inline; fontes precisam ser arquivos servidos pelo próprio painel.
- O container não tem rede: nenhuma chamada externa, nem para fonte, ícone ou imagem.
- Interface em português do Brasil; o modelo público também é usado por outras pessoas, com outros servidores.
- Dados reais vêm do executor; a interface nunca inventa números.

## Brand Commitments

- O nome é Atena (o servidor e a assistente).
- O painel tem identidade própria, separada da do README (que é neon com tema grego): decisão do dono.
- O painel é "meio grego" desde 2026-10-22, por pedido do dono: elegante e sofisticado, com o grego como sistema (as cores dos templos pintados, o meandro, a letra de inscrição e as gravuras clássicas numa cor só), nunca como fantasia nem desenho animado.
- O que o dono marcou como errado: cara de SaaS genérico, ser ruim de usar no celular, e ser temático demais (parecer jogo ou fantasia em vez de ferramenta).
- Intensidade: "show" nos momentos certos (entrar, um alerta, uma aprovação, um agendamento que roda); o resto limpo e rápido.

## Evidence on Hand

- Os dados vêm do servidor em tempo real; não há depoimentos, clientes, números de uso ou imagens de produto, e nada disso deve ser inventado.
- Identidade gráfica do README (`docs/assets/banner.svg`, `docs/assets/zonas.svg`), que não é a do painel; a do painel está no DESIGN.md.

## Product Principles

1. Ferramenta primeiro: em qualquer tela, o estado e a ação vêm antes do mundo visual.
2. Celular e PC com o mesmo peso: nenhum dos dois é a versão capada do outro.
3. Cena só nos momentos que importam; o uso de todo dia é rápido.
4. Seguro de propósito: o que não tem volta pede confirmação clara; nada acontece sem o dono ver.
5. Sem nada de fora: tudo que a tela precisa vem do próprio painel.

## Accessibility & Inclusion

- Alvos de toque confortáveis no celular e leitura sem zoom.
- Respeitar `prefers-reduced-motion` e manter contraste de leitura nos dois temas.
