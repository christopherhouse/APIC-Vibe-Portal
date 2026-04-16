# ============================================================================
# Frontend Dockerfile - Multi-stage build for Next.js application
# ============================================================================

# Build stage
FROM node:25-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./
COPY src/frontend/package.json ./src/frontend/
COPY src/shared/package.json ./src/shared/

# Install dependencies
RUN npm ci

# Copy source code
COPY src/frontend ./src/frontend
COPY src/shared ./src/shared
COPY tsconfig.base.json ./
COPY eslint.config.mjs ./
COPY .prettierrc.json ./

# Build the shared package first (frontend depends on it)
RUN npm run build --workspace=@apic-vibe-portal/shared

# Build the application
RUN npm run build --workspace=@apic-vibe-portal/frontend

# Production stage
FROM node:25-alpine AS production

WORKDIR /app

# Remove npm, yarn, and other package managers — not needed at runtime.
# This also removes bundled npm dependencies (e.g. picomatch) that may
# carry unpatched vulnerabilities.
RUN rm -rf /usr/local/lib/node_modules /usr/local/bin/npm /usr/local/bin/npx \
           /opt/yarn* /usr/local/bin/yarn /usr/local/bin/yarnpkg \
           /usr/local/bin/corepack

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Copy built assets from builder
COPY --from=builder --chown=nextjs:nodejs /app/src/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/src/frontend/.next/static ./src/frontend/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/src/frontend/public ./src/frontend/public

# Set user
USER nextjs

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Start the application
CMD ["node", "src/frontend/server.js"]
