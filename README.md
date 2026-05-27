# Datara

**Analiza tus datos y construye dashboards sin esfuerzo.** Sube archivos CSV, Excel, JSON o TSV; crea gráficos y KPIs con el constructor visual, o deja que la IA lo haga por ti con lenguaje natural. Todo en un dashboard acumulativo con filtros globales.

---

## ✨ Funcionalidades

### 📁 Carga de datos
- **Formatos**: CSV (auto-detecta delimitador), Excel (.xlsx con selección de hojas), JSON y TSV
- **Múltiples archivos**: Carga varios archivos, la IA los relaciona automáticamente
- **Manejo de duplicados**: Detecta archivos repetidos y te deja elegir si reemplazar o conservar ambos

### 📊 Constructor de gráficos manual
Crea gráficos sin escribir código — selecciona el tipo y configura columnas:

| Tipo | Parámetros |
|------|-----------|
| 📊 Barra | Eje X, Eje Y, agrupar por |
| 📈 Línea | Eje X, Eje Y, agrupar por |
| 🔵 Dispersión | Eje X, Eje Y, agrupar por, tamaño |
| 🥧 Torta | Categorías, valores |
| 📋 Histograma | Eje X, agrupar por |
| 📦 Box Plot | Eje X, Eje Y, agrupar por |

### 🏷️ Indicadores (KPIs)
Tarjetas con métricas calculadas al instante sobre los datos:
- **Promedio**, **Suma**, **Conteo**, **Mínimo**, **Máximo**
- Agrupación opcional por columna categórica
- Se renderizan como tarjetas tipo "metric card"

### 🔍 Filtros globales
Selecciona columnas para filtrar y **todos** los items del dashboard se actualizan en tiempo real — tanto gráficos como KPIs.

### 📐 Dashboard acumulativo
- Todos los gráficos y KPIs que creas se acumulan en un dashboard
- Gráficos en grilla de 2 columnas, KPIs en fila de tarjetas
- Botón para limpiar todo el dashboard
- Cada gráfico tiene botones individuales de descarga PNG y exportación de datos

### 💬 Chat con IA (Gemini)
- **Preguntas en lenguaje natural**: "¿Cuál es el promedio de precios?", "Muéstrame un gráfico de ventas por mes"
- **Respuestas inteligentes**: La IA elige si responder con texto, tabla o gráfico según el contexto
- **Historial de conversación**: Pregunta varias veces, la IA recuerda el contexto
- **Preguntas encadenadas**: "ordena por precio", "muestra solo los 3 más caros"
- **Exportación**: Descarga la conversación como .txt, resultados como CSV, gráficos como PNG

### 🔒 Ejecución segura de código
El código generado por la IA se ejecuta en un sandbox que:
- ✅ Solo permite `pandas`, `numpy` y `plotly`
- ✅ Bloquea `import os`, `open()`, `eval()`, `exec()`, `subprocess`
- ✅ Timeout automático (30 segundos)
- ✅ Sin acceso al sistema de archivos ni a la red

## 🧱 Stack

| Capa | Tecnología |
|------|-----------|
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| Frontend | HTML + CSS + JavaScript (vanilla) |
| Gráficos | [Plotly.js](https://plotly.com/javascript/) |
| Procesamiento | [Pandas](https://pandas.pydata.org/) + [OpenPyXL](https://openpyxl.readthedocs.io/) |
| IA | [Gemini 2.5 Flash](https://ai.google.dev/) |
| Tests | [pytest](https://docs.pytest.org/) |
| Entorno | Python 3.10+ |

## 🚀 Instalación y uso

### 1. Clona el repositorio

Abre una terminal (PowerShell en Windows, Terminal en Mac/Linux) y escribe:

```bash
git clone https://github.com/Dandlrt09/Datara.git
cd Datara
```

### 2. Crea el entorno virtual

Esto crea una "burbuja" con Python limpio para la app:

```bash
python -m venv venv
```

**Actívalo:**

| Sistema | Comando |
|---------|---------|
| **Windows** | `venv\Scripts\activate` |
| **Mac / Linux** | `source venv/bin/activate` |

Vas a saber que funcionó porque aparecerá `(venv)` al inicio de la línea en tu terminal.

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

Esperá unos segundos mientras se instala todo. Si ves errores rojos, asegurate de tener Python 3.10 o superior.

### 4. Configura la API key de Gemini

La app necesita una clave de Gemini para funcionar. **Es gratis y la sacás en 2 minutos:**

1. Andá a [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Iniciá sesión con tu cuenta de Google
3. Hacé clic en **"Create API Key"**
4. Copiá la clave (algo como `AIza...`)

**Dos formas de usarla:**

**Opción A — Archivo `.env` (recomendado):**
Creá un archivo llamado `.env` en la carpeta del proyecto y poné adentro:

```
GEMINI_API_KEY=AIzaPEGATUKEYACA
```

**Opción B — Desde la app (más fácil para probar):**
1. Abrí la app (paso 5)
2. Andá a **Settings** (engranaje)
3. Pegá tu API key y hacé clic en **Aplicar cambios**

### 5. Ejecuta la app

```bash
python run.py
```

Si todo funciona, vas a ver algo como:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Abrí tu navegador** en [http://localhost:8000](http://localhost:8000) y listo. Ya podés usar Datara.

> Para cerrar la app apretá **Ctrl+C** en la terminal.

## 🎯 Cómo usarla

### Flujo básico

1. **Sube datos** → Carga uno o más archivos CSV, Excel, JSON o TSV
2. **Chat con IA** → Pregunta en español sobre tus datos, pide gráficos o análisis
3. **Constructor de gráficos** → Crea charts y KPIs manualmente debajo del chat
4. **Dashboard** → Todo se acumula, aplica filtros globales para explorar

### Ejemplos de preguntas para la IA

| Tipo | Ejemplo |
|------|---------|
| 🔵 Texto | "¿Cuántas filas tiene el dataset?" |
| 🔵 Texto | "¿Cuál es la computadora más cara?" |
| 🟡 Tabla | "Muéstrame el precio promedio por marca" |
| 🟡 Tabla | "Lista los 10 productos más vendidos" |
| 🔴 Gráfico | "Haz un gráfico de barras con ventas por categoría" |
| 🔴 Gráfico | "Muéstrame la distribución de precios con un histograma" |

## 📁 Estructura del proyecto

```
Datara/
├── run.py                         # 🚀 Arranca la app (python run.py)
├── api/                           # Backend (FastAPI)
│   ├── main.py                    # App factory, CORS, lifespan, static files
│   ├── dependencies.py            # Inyección de sesión y servicios
│   ├── session_store.py           # Memoria de sesiones con TTL (1h)
│   ├── session_data.py            # Datos de una sesión (archivos, chat, etc.)
│   ├── models/                    # Modelos Pydantic (request/response)
│   └── routers/                   # Endpoints REST
│       ├── files.py               # Subir, listar, previsualizar, eliminar
│       ├── chat.py                # Chat con IA, historial, limpiar
│       ├── dashboard.py           # Dashboard items (gráficos + KPIs)
│       ├── settings.py            # Configuración de API key y modelo
│       ├── session.py             # Estado de sesión, reset
│       ├── archive.py             # Archivar y restaurar sesiones
│       └── export.py              # Exportar datos, gráficos, conversación
├── frontend/                      # 🎨 Frontend (vanilla JS)
│   ├── index.html                 # Página principal
│   ├── api.js                     # Cliente HTTP con X-Session-Id
│   ├── common.js                  # Utilidades compartidas
│   ├── styles.css                 # Estilos globales
│   └── screens/                   # Pantallas
│       ├── sidebar.html           # Barra lateral con navegación
│       ├── upload.html            # Subida de archivos
│       ├── chat.html              # Chat con IA y constructor de gráficos
│       ├── dashboard.html         # Dashboard con filtros globales
│       └── settings.html          # Configuración
├── services/                      # 🧠 Lógica de negocio
│   ├── llm_service.py             # Comunicación con Gemini API
│   ├── code_executor.py           # Orquestación LLM + sandbox
│   ├── file_service.py            # Gestión y parseo de archivos
│   ├── export_service.py          # Exportación de resultados
│   └── archive_service.py         # Archivar/restaurar sesiones en JSON
├── models/                        # 📦 Modelos de datos (sin Pydantic)
│   ├── file_data.py               # Archivo subido
│   ├── chat_message.py            # Mensaje del chat
│   ├── analysis_result.py         # Resultado de ejecución de código
│   └── session_archive.py         # Archivo de sesión (para persistencia)
├── utils/                         # 🔧 Utilidades
│   ├── sandbox.py                 # Entorno seguro para ejecutar código IA
│   ├── prompts.py                 # Templates de prompts
│   └── validators.py              # Validación de archivos
├── tests/                         # ✅ Tests automatizados
│   ├── conftest.py                # Fixtures compartidos
│   ├── test_session_store.py      # Sesiones con TTL y aislamiento
│   ├── test_api_models.py         # Modelos Pydantic
│   ├── test_api_routers.py        # Endpoints REST
│   ├── test_archive_service.py    # Archivo/restauración
│   ├── test_file_service.py       # Carga y parseo
│   ├── test_llm_service.py        # Conexión con Gemini
│   └── ... (y más)
├── Dataset/                       # 📊 Archivos de ejemplo para probar
├── uploads/                       # Archivos subidos (no se sube a Git)
├── archives/                      # Sesiones archivadas (no se sube a Git)
├── .env                           # 🔑 Tu API key (NO se sube a GitHub)
├── .env.example                   # Template de configuración
├── requirements.txt               # Dependencias
└── LICENSE                        # Licencia MIT
```

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

396 tests que cubren sesiones, API endpoints, servicios, modelos, validación, dashboard, archive y ejecución de código.

## 📄 Licencia

Distribuido bajo licencia **MIT**. Consulta el archivo [LICENSE](./LICENSE) para más detalles.

Puedes usar, copiar, modificar y distribuir este software libremente, siempre que mantengas el aviso de copyright original. El software se proporciona "tal cual", sin garantía de ningún tipo.
