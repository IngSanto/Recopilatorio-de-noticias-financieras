# Recopilatorio de noticias financieras

Página estática que junta noticias recientes y las agrupa por acción/ticker, para no tener que leer cada sitio de noticias por separado.

## Cómo funciona

1. `data/sources.json` lista las fuentes de noticias (RSS).
2. `data/tickers.json` es un diccionario "nombre de empresa" -> ticker bursátil. `scripts/fetch_news.py` busca esos nombres dentro de cada noticia.
3. `scripts/fetch_news.py` descarga los RSS, hace el cruce y genera `data/news.json`.
4. `index.html` + `assets/app.js` leen `data/news.json` y pintan la página: pestaña "Por acción" y pestaña "Sin acción".
5. `.github/workflows/update-news.yml` corre el script 3 veces al día, sube `data/news.json` si cambió y publica el sitio en GitHub Pages.

## Fuentes

| Fuente | Alcance | Idioma | Volumen | Ventana del feed |
|---|---|---|---|---|
| Bloomberg Línea (México) | México | es | ~1.6/día | ~63 días |
| Investing.com España (acciones) | Internacional | es | ~17/día | ~14 h |
| CNBC Markets | Internacional | en | ~1.6/día | ~18 días |
| CNBC Finance | Internacional | en | ~2.9/día | ~10 días |
| Yahoo Finance | Internacional | en | ~20/día | ~3 días |
| MarketWatch | Internacional | en | ~15/día | ~16 h |

**Criterio para aceptar una fuente:** la *ventana* del feed (cuánto tiempo abarcan los artículos que trae) tiene que ser mayor que el hueco más largo entre corridas, que son 9 horas. Si la ventana es menor, entre una corrida y la siguiente pasan noticias que el feed ya descartó y nadie se entera. Por eso se usa el feed de acciones de Investing.com (ventana 14 h) y no su feed general, que publica ~103 notas/día pero solo conserva 10 artículos: su ventana es de 2.3 h y perderíamos ~70% de su contenido.

Reuters y Financial Times quedaron fuera porque sus RSS públicos ya no responden (Reuters da error de conexión, FT redirige).

## Las dos pestañas

- **Por acción**: una tarjeta por ticker con sus noticias. Se ordenan por qué tan pronto merecen atención: primero se agrupan por frescura de la nota más nueva (menos de 12 h, menos de 36 h, menos de 96 h, más viejo) y dentro de cada grupo mandan las acciones con más cobertura. Ordenar solo por fecha dejaba arriba acciones con una sola nota y enterraba a las que traían diez.
- **Sin acción**: noticias que no se pudieron ligar a ningún ticker del diccionario (macro, política económica, mercado en general). Cada fuente tiene un tope de cuántas notas sin acción aporta (`max_sin_accion` en `sources.json`), para que un feed de alto volumen no se coma la sección. Las noticias que **sí** tocan una acción no tienen tope: esas son la señal.

## Si una fuente falla

Los feeds se caen de vez en cuando. Si una corrida trae menos del 60% de artículos que la anterior, el script asume falla de fuente (no "hubo menos noticias"), **no sobrescribe** `data/news.json` y sale con error. La página se queda con los últimos datos buenos en vez de perder noticias que seguían vigentes.

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

Si algún día se necesita algo inmediato (minutos en vez de horas), habría que mover esto a un servicio con servidor propio, que es otro proyecto.

Al agregar fuentes hay que volver a revisar la tabla de ventanas de arriba: si una fuente nueva tiene ventana menor a 9 h, o se sube la frecuencia del cron o esa fuente pierde noticias en silencio.

## Configuración ya hecha

- **GitHub Pages**: habilitado con Source = "GitHub Actions" (Settings → Pages).
- **Rama por defecto**: el workflow vive en `main`, que es de donde GitHub ejecuta los `schedule`.

## Agregar una nueva fuente de noticias

Editar `data/sources.json` y agregar un objeto con `id`, `name`, `short_name`, `scope`, `lang`, `type: "rss"`, `url`, `site_url` y `max_sin_accion`. El script no necesita más cambios si la fuente expone RSS estándar. Al correrlo, revisa que la ventana que imprime sea mayor a 9 h; si no, avisa solo.

Los feeds no se ponen de acuerdo en el formato de fecha: Bloomberg Línea y CNBC usan RFC 2822, Yahoo usa ISO 8601 e Investing.com manda `2026-09-08 03:33:31` sin zona horaria. El script intenta los tres formatos.

## Agregar una acción/empresa nueva al radar

Editar `data/tickers.json` y agregar un objeto con `ticker`, `name`, `exchange`, `sector` y `aliases` (formas en que el nombre aparece en las noticias, por ejemplo variantes con/sin acentos).

**Cuidado con los alias que también son palabras comunes en español.** Es la forma más fácil de llenar la página de basura:

| Mal alias | Por qué | Alias correcto |
|---|---|---|
| `Visa` | "visa" de viaje sale en cualquier nota de migración | `Visa Inc` |
| `Meta` | "la meta de inflación" | `Meta Platforms` |
| `Total` | "el total de las exportaciones" | `TotalEnergies` |
| `Moderna` | "tecnología moderna" | (se dejó fuera) |
| `Vale` | "vale la pena" | `Vale S.A.` |

Un alias en MAYÚSCULAS de 5 letras o menos (`BYD`, `AMD`, `UPS`, `BP`) se busca respetando mayúsculas, justo para evitar este problema.

## Correrlo en local

```bash
python3 scripts/fetch_news.py   # regenera data/news.json
python3 -m http.server 8000     # sirve la página en http://localhost:8000
```

No requiere dependencias externas, solo Python 3.
