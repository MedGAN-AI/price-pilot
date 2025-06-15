# Multi-stage build for production
FROM node:18-alpine AS builder

WORKDIR /app

# Install dependencies for native modules if needed
RUN apk add --no-cache python3 make g++

# Copy package files
COPY package*.json ./

# Clear npm cache and install dependencies
RUN npm cache clean --force
RUN npm ci

# Copy source code (be selective about what you copy)
COPY src/ ./src/
COPY public/ ./public/ 2>/dev/null || true
COPY index.html ./
COPY vite.config.* ./
COPY tsconfig.* ./
COPY *.config.js ./2>/dev/null || true
COPY *.config.ts ./2>/dev/null || true

# Build argument for API URL
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Set NODE_ENV for build
ENV NODE_ENV=production

# Build the application with error handling
RUN npm run build || (echo "Build failed. Checking for common issues..." && \
    echo "Contents of current directory:" && ls -la && \
    echo "Contents of node_modules/.bin:" && ls -la node_modules/.bin/ && \
    echo "Package.json scripts:" && cat package.json | grep -A 10 "scripts" && \
    exit 1)

# Verify build output
RUN ls -la dist/ || (echo "Build output not found in dist/ directory" && exit 1)

# Production stage with nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Create a simple nginx config for SPA
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Expose port 80 (nginx default)
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
