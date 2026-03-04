FROM node:20-alpine AS build
WORKDIR /app

COPY front/sprite-ui/sprite-ui/package*.json ./sprite-ui/
WORKDIR /app/sprite-ui
RUN npm ci

COPY front/sprite-ui/sprite-ui/ .
RUN npm run build

FROM nginx:1.25-alpine
COPY infra/nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/sprite-ui/dist /usr/share/nginx/html