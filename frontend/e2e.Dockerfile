# Образ для E2E-тестов: Playwright с браузером Chromium (версия совпадает с @playwright/test в package-lock.json)
FROM mcr.microsoft.com/playwright:v1.64.1-noble
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY playwright.config.ts tsconfig.json ./
COPY e2e ./e2e
CMD ["npx", "playwright", "test"]
