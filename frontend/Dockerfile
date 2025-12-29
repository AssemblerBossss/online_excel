FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
# Копируем конфигурацию Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Копируем собранное приложение
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80