# Stage 1: Сборка
FROM node:22-alpine3.22 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --prefer-offline
COPY . .
RUN npm run build

# Stage 2: Production
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80