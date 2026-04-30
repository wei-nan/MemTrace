# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit

COPY . .
RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Route all paths to index.html for SPA
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  index index.html;\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n  location /api/ {\n    proxy_pass http://api:8000/api/;\n    proxy_buffering off;\n    proxy_cache off;\n    proxy_set_header Connection "";\n    proxy_http_version 1.1;\n    proxy_read_timeout 300s;\n  }\n  location /auth/ {\n    proxy_pass http://api:8000/auth/;\n    proxy_buffering off;\n    proxy_cache off;\n    proxy_read_timeout 300s;\n  }\n}\n' \
    > /etc/nginx/conf.d/default.conf

EXPOSE 80
