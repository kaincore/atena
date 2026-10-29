# etapa 1: compila o TypeScript
FROM node:22.23.4-alpine3.24 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# etapa 2: só o necessário para rodar, sem root
FROM node:22.23.4-alpine3.24
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev --no-audit --no-fund && npm cache clean --force
COPY --from=build /app/dist ./dist
COPY public ./public
RUN mkdir -p uploads data && chown node:node uploads data
USER node
EXPOSE 3002
CMD ["node", "dist/index.js"]
