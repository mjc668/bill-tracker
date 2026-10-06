FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_APP_VERSION=dev
ENV NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION
ARG NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS=180
ENV NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS=$NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
# Run as the built-in unprivileged `node` user. Chown the app tree so Next can
# write its runtime cache (image optimization/ISR) while running unprivileged.
RUN chown -R node:node /app
EXPOSE 3000
# Seed the runtime-only API_URL/API_PREFIX from the container env so the same
# image works on any host without rebuilding. The layout injects both into the
# page at request time.
USER node
CMD ["/bin/sh", "-c", "export API_URL=\"${NEXT_PUBLIC_API_URL:-http://localhost:8010}\" && export API_PREFIX=\"${API_PREFIX:-${NEXT_PUBLIC_API_PREFIX:-}}\" && echo '' && echo '  Frontend/UI available on: http://localhost:3010' && echo '' && node server.js"]
