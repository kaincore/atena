# Painel Atena: sem dependências do npm. O Node 22 roda o TypeScript direto e já traz o SQLite.
FROM node:22.23.4-alpine3.24
ENV NODE_ENV=production
WORKDIR /app
COPY package.json ./
COPY src ./src
COPY public ./public
# o usuário de verdade vem do compose (atena-painel do servidor); este é só o padrão sem privilégio
USER nobody
CMD ["node", "--disable-warning=ExperimentalWarning", "src/principal.ts"]
