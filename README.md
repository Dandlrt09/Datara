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

Esta guía está escrita para que **cualquier persona** —haya usado Python o no— pueda levantar la app. No necesitás saber nada más que copiar y pegar comandos.

---

### 1. Descargá el proyecto

Abrí una terminal:
- **Windows**: apretá `Win + R`, escribí `powershell` y apretá Enter.
- **Mac**: abrí "Terminal" desde el Launchpad.
- **Linux**: abrí tu terminal (Ctrl+Alt+T en Ubuntu).

Pegá esto y apretá Enter:

```bash
git clone https://github.com/Dandlrt09/Datara.git
cd Datara
```

Ya tenés el proyecto en tu compu.

---

### 2. Instalá Python (si no lo tenés)

Esta app corre con **Python 3.10 o superior**. Para ver si ya lo tenés, escribí:

```bash
python --version
```

Si ves algo como `Python 3.10.x` o superior, pasá al paso 3.

**Si no lo tenés:**

- **Windows**: andá a [python.org/downloads](https://python.org/downloads), descargá la última versión, ejecutá el instalador y **marcá la casilla "Add Python to PATH"** antes de instalar. Es importante esa casilla.
- **Mac**: `brew install python@3.12` (necesitás [Homebrew](https://brew.sh/)) o descargá de [python.org/downloads](https://python.org/downloads).
- **Linux**: `sudo apt install python3 python3-venv python3-pip`.

---

### 3. Creá el entorno virtual

Esto crea una carpeta `venv/` donde se instalan las dependencias sin ensuciar tu sistema:

```bash
python -m venv venv
```

Después **activá el entorno**:

| Sistema | Comando |
|---------|---------|
| **Windows** (PowerShell) | `venv\Scripts\activate` |
| **Windows** (CMD) | `venv\Scripts\activate.bat` |
| **Mac / Linux** | `source venv/bin/activate` |

**Sabés que funcionó** porque te va a aparecer `(venv)` al principio de la línea, algo así:

```
(venv) C:\Users\tu-usuario\Datara>
```

---

### 4. Instalá las dependencias

Con el entorno activado (deberías ver `(venv)`), corré:

```bash
pip install -r requirements.txt
```

Esto descarga e instala todo lo que la app necesita. Puede tardar entre 30 segundos y 2 minutos. Si ves texto amarillo o barras de progreso, todo bien. Si ves un error en **rojo** y dice algo de `Python 3.10` o `version`, es porque tu Python es muy viejo — volvé al paso 2.

---

### 5. Configurá la API key de Gemini

La app necesita una clave de Gemini para usar la IA. **Es gratis, la sacás en 2 minutos:**

1. Andá a [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Iniciá sesión con tu cuenta de Google (la misma de Gmail)
3. Tocá el botón **"Create API Key"**
4. Copiá la clave que te dan (empieza con `AIza...`)

Ahora creá un archivo `.env` en la carpeta del proyecto:

```bash
# En Windows (PowerShell):
New-Item -ItemType File -Name ".env"

# En Mac / Linux:
touch .env
```

Abrí ese archivo con cualquier editor de texto (Bloc de Notas, TextEdit, VS Code) y **copiate esto adentro**:

```
GEMINI_API_KEY=AIzaSy_PEGATUKEYACA
```

Cambiá `AIzaSy_PEGATUKEYACA` por tu clave real. Guardá el archivo.

**Ojo**: el archivo se llama `.env` con un punto adelante, no `env` ni `.env.txt`. En Windows puede no mostrar el nombre completo; si ves ".env" solo, está bien.

---

### 6. Ejecutá la app

Con el entorno activado (recordá: tenés que ver `(venv)` en la terminal), corré:

```bash
python run.py
```

Si todo funciona, vas a ver algo como esto:

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Eso significa que la app ya está corriendo. **Abrí tu navegador** (Chrome, Edge, Firefox) y andá a esta dirección:

👉 **http://localhost:8000**

¡Ya estás dentro de Datara!

---

### ✋ Solución de problemas comunes

| Problema | Qué hacer |
|----------|-----------|
| `Python no se reconoce...` | No instalaste Python o no marcaste "Add to PATH". Volvé al paso 2 y reinstalá. |
| `Error: No module named...` | Te olvidaste del paso 4. Corré `pip install -r requirements.txt` de nuevo. |
| `API key inválida` | En Settings de la app, verificá que pegaste bien la clave de Gemini. |
| `Modelo no encontrado` | Apretá el botón "Reset session" en la app o reiniciá el servidor (Ctrl+C y volvé a correr `python run.py`). |

---

### 🛑 Cómo cerrar la app

En la terminal donde está corriendo la app, apretá **Ctrl + C** (las dos teclas juntas). La terminal vuelve a mostrar el prompt normal y la app se apaga.

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
│   ├── fixtures/                  # 📊 Datos de ejemplo para tests
│   │   ├── Computers.csv
│   │   ├── screen_categories.csv
│   │   └── datos_prueba.csv
│   ├── test_session_store.py      # Sesiones con TTL y aislamiento
│   ├── test_api_models.py         # Modelos Pydantic
│   ├── test_api_routers.py        # Endpoints REST
│   ├── test_archive_service.py    # Archivo/restauración
│   ├── test_file_service.py       # Carga y parseo
│   ├── test_llm_service.py        # Conexión con Gemini
│   └── ... (y más)
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

400+ tests que cubren sesiones, API endpoints, servicios, modelos, validación, dashboard, archive, frontend y ejecución de código.

## 📄 Licencia

Distribuido bajo licencia **MIT**. Consulta el archivo [LICENSE](./LICENSE) para más detalles.

Puedes usar, copiar, modificar y distribuir este software libremente, siempre que mantengas el aviso de copyright original. El software se proporciona "tal cual", sin garantía de ningún tipo.
