# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy frontend source and build
COPY . .
RUN npm run build

# Stage 2: Serve the build folder using lightweight Nginx
FROM nginx:stable-alpine

# Copy custom Nginx configuration to handle React client-side routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy build artifacts from Stage 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
