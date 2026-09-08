# Recopilatorio de noticias financieras

Página estática que junta noticias recientes y las agrupa por acción/ticker, para no tener que leer cada sitio de noticias por separado.

## Cómo funciona

1. `data/sources.json` lista las fuentes de noticias (RSS). Hoy solo tiene la sección México de Bloomberg Línea.
2. `data/tickers.json` es un diccionario "nombre de empresa" -> ticker bursátil. `scripts/fetch_news.py` busca esos nombres dentro de cada noticia.
3. `scripts/fetch_news.py` descarga los RSS, hace el cruce y genera `data/news.json`.
4. `index.html` + `assets/app.js` leen `data/news.json` y pintan la página (últimas noticias y noticias agrupadas por acción).
5. `.github/workflows/update-news.yml` corre el script 3 veces al día, sube `data/news.json` si cambió y publica el sitio en GitHub Pages.

## Horarios de actualización

Tres corridas diarias (~cada 8 horas), elegidas por lo que pasa en el mercado y verificadas contra cuándo publica realmente la fuente:

| Hora CDMX | Hora UTC (la del cron) | Por qué |
|---|---|---|
| 07:30 | 13:30 | Una hora antes de la apertura de la BMV (8:30). Trae lo de la noche: Asia, Europa, pre-market de EE.UU. |
| 15:30 | 21:30 | Media hora después del cierre. BMV y NYSE cierran a las 15:00 CDMX. Trae la sesión completa. |
| 22:30 | 04:30 | Después del pico de publicación de la fuente (19:00-21:00 CDMX) y de los reportes after-hours. |

Estos horarios no se eligieron a ojo. Sobre 100 notas reales del feed se midió cuánto esperaría una nota promedio en aparecer en la página según el calendario:

| Calendario | Espera promedio |
|---|---|
| **07:30 / 15:30 / 22:30 (el que se usa)** | **3.41 h** |
| 06:30 / 14:30 / 21:30 | 3.70 h |
| Cada 8 h a reloj corrido (00 / 08 / 16) | 3.71 h |
| 06:30 / 15:30 / 23:30 | 3.88 h |

Notas:

- El cron de GitHub siempre se escribe en **UTC**. CDMX es UTC-6 todo el año (México quitó el horario de verano en 2022), así que la conversión es fija: hora CDMX + 6 = UTC.
- Los horarios usan el minuto `:30` a propósito. Los cron "en punto" son los más saturados en GitHub Actions y se retrasan más.
- GitHub Actions no garantiza puntualidad en `schedule`: retrasos de 5 a 30 minutos son normales.

## Sobre la "actualización automática"

Esto es un sitio estático (sin servidor propio corriendo), así que no hay forma de avisar al instante cuando sale una noticia. Con 3 corridas al día, una noticia espera en promedio 3.4 horas (hasta 9 en el peor caso, de madrugada) antes de aparecer en la página.

Vale la pena saber que este feed publica ~1.6 notas al día (100 notas en 63 días), así que 3 corridas diarias no se están perdiendo gran cosa. Cuando se agreguen más fuentes y el volumen suba, conviene volver a medir y probablemente subir la frecuencia — es cambiar un renglón del cron. Si algún día se necesita algo inmediato (minutos en vez de horas), habría que mover esto a un servicio con servidor propio, que es otro proyecto.

## Configuración ya hecha

- **GitHub Pages**: habilitado con Source = "GitHub Actions" (Settings → Pages).
- **Rama por defecto**: el workflow vive en `main`, que es de donde GitHub ejecuta los `schedule`.

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
