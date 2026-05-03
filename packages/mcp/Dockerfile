FROM node:22-slim AS builder
WORKDIR /app
COPY package.json tsconfig.json ./
RUN npm install
COPY src ./src
RUN npm run build

FROM node:22-slim
WORKDIR /app
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist

RUN groupadd -g 1000 memtrace && useradd -u 1000 -g memtrace -s /bin/bash -m memtrace && \
    chown -R memtrace:memtrace /app

USER 1000

EXPOSE 3001
ENV MCP_TRANSPORT=sse
ENV MCP_PORT=3001
ENV MEMTRACE_API=http://api:8000/api/v1

CMD ["node", "dist/index.js"]
