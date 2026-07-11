# Use an official Node.js image as the base
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install --frozen-lockfile --legacy-peer-deps

# Copy the rest of the frontend code
COPY . .

# Build the frontend
RUN npm run build

# Use a lightweight web server to serve the built files
FROM nginx:alpine AS server

# Copy the build output from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
