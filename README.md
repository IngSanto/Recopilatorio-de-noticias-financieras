# Recopilatorio de noticias financieras

Página estática que junta noticias recientes y las agrupa por acción/ticker, para no tener que leer cada sitio de noticias por separado.

## Cómo funciona

1. `data/sources.json` lista las fuentes de noticias (RSS). Hoy solo tiene la sección México de Bloomberg Línea.
2. `data/tickers.json` es un diccionario "nombre de empresa" -> ticker bursátil. `scripts/fetch_news.py` busca esos nombres dentro de cada noticia.
3. `scripts/fetch_news.py` descarga los RSS, hace el cruce y genera `data/news.json`.
4. `index.html` + `assets/app.js` leen `data/news.json` y pintan la página (últimas noticias y noticias agrupadas por acción).
5. `.github/workflows/update-news.yml` corre el script cada 2 horas, sube `data/news.json` si cambió y publica el sitio en GitHub Pages.

## Sobre la "actualización automática"

Esto es un sitio estático (sin servidor propio corriendo), así que no hay forma de avisar al instante cuando sale una noticia. Lo que sí hace: revisa las fuentes cada 2 horas (configurable en el cron del workflow) y republica el sitio solo si hubo cambios. Si en algún momento se necesita algo más inmediato (minutos en vez de horas), habría que mover esto a un servicio con servidor propio — es otro proyecto.

## Requisito único para que el cron funcione

GitHub solo ejecuta workflows con `schedule` desde la rama por defecto del repositorio (normalmente `main`). Mientras este trabajo viva en una rama distinta, el cron no se dispara solo — hay que fusionarlo a `main` primero.

## Habilitar GitHub Pages (una sola vez, manual)

En el repositorio: **Settings → Pages → Build and deployment → Source: "GitHub Actions"**. Esto no se puede hacer desde el propio workflow, requiere permisos de administrador del repositorio.

## Agregar una nueva fuente de noticias

Editar `data/sources.json` y agregar un objeto con `id`, `name`, `type: "rss"`, `url` (la URL del feed RSS) y `site_url`. El script no necesita más cambios si la fuente expone RSS estándar.

## Agregar una acción/empresa nueva al radar

Editar `data/tickers.json` y agregar un objeto con `ticker`, `name`, `exchange` y `aliases` (formas en que el nombre aparece en las noticias, por ejemplo variantes con/sin acentos).

## Correrlo en local

```bash
python3 scripts/fetch_news.py   # regenera data/news.json
python3 -m http.server 8000     # sirve la página en http://localhost:8000
```

No requiere dependencias externas, solo Python 3.
