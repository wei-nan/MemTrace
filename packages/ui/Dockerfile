# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app
COPY package*.json ./
COPY packages/ui/package.json packages/ui/
COPY packages/core/package.json packages/core/
COPY packages/api/package.json packages/api/
COPY packages/cli/package.json packages/cli/
RUN npm install --no-audit

COPY . .
RUN npm run build --workspace=packages/ui

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/packages/ui/dist /usr/share/nginx/html

# SPA routing + API/auth/mcp proxying + WebSocket streaming for /speech/stt-stream
COPY packages/ui/nginx.conf /etc/nginx/conf.d/default.conf

# Adjust nginx to run as non-root
RUN sed -i 's/user  nginx;//g' /etc/nginx/nginx.conf && \
    sed -i 's/pid \/run\/nginx.pid;/pid \/tmp\/nginx.pid;/g' /etc/nginx/nginx.conf

EXPOSE 8080
