# ---- Builder: install deps and produce the static build ----
FROM node:22-slim AS builder

WORKDIR /app

# Install dependencies first (cached unless lockfile/manifest change).
COPY package.json package-lock.json ./
RUN npm ci

# Build the app (tsc -b && vite build) -> /app/dist
COPY . .
RUN npm run build

# ---- Runtime: serve static files with nginx ----
FROM nginx:1.27-alpine AS runtime

# SPA + /api reverse proxy configuration.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static build output.
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
