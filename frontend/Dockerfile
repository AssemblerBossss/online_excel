# Stage 1: Установка зависимостей
FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
# ЗАМЕНИТЕ npm ci на npm install
RUN npm install --no-audit --prefer-offline

# Stage 2: Сборка
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --prefer-offline
COPY . .
RUN npm run build

# Stage 3: Production
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80