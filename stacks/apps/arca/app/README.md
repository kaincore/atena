# ARCA File System

Sistema de gerenciamento de arquivos com interface terminal.

## Características

- Upload de arquivos até 50MB
- Download de arquivos
- Listagem com informações detalhadas
- Interface terminal estilizada
- API REST
- Armazenamento persistente

## Tecnologias

- TypeScript
- Express
- Docker

## Instalação

```bash
# Instalar dependências
npm install

# Compilar TypeScript
npm run build

# Executar em desenvolvimento
npm run dev

# Executar em produção
npm start
```

## Docker

```bash
# Construir e iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

## API Endpoints

- `POST /api/upload` - Enviar arquivo
- `GET /api/files` - Listar arquivos
- `GET /api/files/:id` - Baixar arquivo
- `DELETE /api/files/:id` - Excluir arquivo

## Estrutura

```
arca/
├── src/
│   ├── controllers/    # Controladores
│   ├── routes/         # Rotas
│   ├── services/       # Serviços
│   ├── types/          # Tipos TypeScript
│   └── public/         # Frontend
├── uploads/            # Arquivos enviados
└── data/               # Metadados
```

## Acesso

Após iniciar: http://localhost:3002
