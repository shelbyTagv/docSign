FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Include default nginx.conf just in case, though the system uses external reverse proxy
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
