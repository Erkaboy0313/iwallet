FROM node:22-alpine AS css
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build:css

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home iwallet
COPY --chown=iwallet:iwallet . .
COPY --from=css --chown=iwallet:iwallet /src/static/css/build.css static/css/build.css
# app.css is Tailwind's source entry, not a browser asset; its npm import is
# resolved into build.css before Django hashes the collected runtime assets.
RUN SECRET_KEY=build-only-placeholder DEBUG=False python manage.py collectstatic --noinput --ignore=css/app.css
USER iwallet
CMD ["uvicorn", "iwallet.asgi:application", "--host", "0.0.0.0", "--port", "8010", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]

FROM nginx:alpine AS gateway
COPY deploy/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=app /app/staticfiles /srv/static
