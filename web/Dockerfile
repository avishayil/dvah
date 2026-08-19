# DVAH web UI image (Next.js). Multi-stage: build with full deps, then run `next start`.
# NEXT_PUBLIC_API_BASE is inlined into the browser bundle at BUILD time, so it must be
# the host-published API URL (not the compose-internal hostname).
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN npm run build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "run", "start"]
