# Coletor das receitas (lab): abre um site num Chromium sem tela e grava o que o Claude Code precisa
# para descrever o estilo dele (prints, CSS, scripts, estilos computados), sem IA nenhuma. O executor
# (receita.estudar) roda um container por pedido, na rede lab-coletor: internet sim; rede de casa,
# Tailscale e servidor não (atena-docker-firewall). Construído pelo instalador (88-lab.sh).
FROM node:24.22.1-bookworm-slim
ENV NODE_ENV=production PLAYWRIGHT_BROWSERS_PATH=/opt/navegadores HOME=/tmp
WORKDIR /app
COPY package.json package-lock.json ./
# o Chromium sem tela da mesma versão do playwright-core, e as bibliotecas do Debian que ele usa
RUN npm ci --ignore-scripts --no-audit --no-fund --loglevel=error \
 && node node_modules/playwright-core/cli.js install --with-deps --only-shell chromium \
 && rm -rf /var/lib/apt/lists/* /root/.npm /tmp/*
COPY coletar.js ./
# o usuário de verdade vem do executor (docker run --user); este é só o padrão sem privilégio
USER node
ENTRYPOINT ["node", "coletar.js"]
