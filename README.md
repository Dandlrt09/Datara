# Datara

**Analizá tus datos y construí dashboards sin esfuerzo.** Subí archivos CSV, Excel, JSON o TSV; creá gráficos y KPIs con el constructor visual, o deja que la IA lo haga por vos con lenguaje natural. Todo en un dashboard acumulativo con filtros globales.

---

## ✨ Funcionalidades

### 📁 Carga de datos
- **Formatos**: CSV (auto-detecta delimitador), Excel (.xlsx con selección de hojas), JSON y TSV
- **Múltiples archivos**: Cargá varios archivos, la IA los relaciona automáticamente
- **Manejo de duplicados**: Detecta archivos repetidos y te deja elegir si reemplazar o conservar ambos

### 📊 Constructor de gráficos manual
Creá gráficos sin escribir código — seleccioná el tipo y configurá columnas:

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
Seleccioná columnas para filtrar y **todos** los items del dashboard se actualizan en tiempo real — tanto gráficos como KPIs.

### 📐 Dashboard acumulativo
- Todos los gráficos y KPIs que creás se acumulan en un dashboard
- Gráficos en grilla de 2 columnas, KPIs en fila de tarjetas
- Botón para limpiar todo el dashboard
- Cada gráfico tiene botones individuales de descarga PNG y exportación de datos

### 💬 Chat con IA (Gemini)
- **Preguntas en lenguaje natural**: "¿Cuál es el promedio de precios?", "Mostrame un gráfico de ventas por mes"
- **Respuestas inteligentes**: La IA elige si responder con texto, tabla o gráfico según el contexto
- **Historial de conversación**: Preguntá varias veces, la IA recuerda el contexto
- **Preguntas encadenadas**: "ordená por precio", "mostrame solo los 3 más caros"
- **Exportación**: Descargá la conversación como .txt, resultados como CSV, gráficos como PNG

### 🔒 Ejecución segura de código
El código generado por la IA se ejecuta en un sandbox que:
- ✅ Solo permite `pandas`, `numpy` y `plotly`
- ✅ Bloquea `import os`, `open()`, `eval()`, `exec()`, `subprocess`
- ✅ Timeout automático (30 segundos)
- ✅ Sin acceso al sistema de archivos ni a la red

## 🧱 Stack

| Capa | Tecnología |
|------|-----------|
| Frontend & Backend | [Streamlit](https://streamlit.io/) |
| Procesamiento | [Pandas](https://pandas.pydata.org/) + [OpenPyXL](https://openpyxl.readthedocs.io/) |
| Gráficos | [Plotly](https://plotly.com/python/) |
| IA | [Gemini 2.5 Flash](https://ai.google.dev/) |
| Tests | [pytest](https://docs.pytest.org/) |
| Entorno | Python 3.10+ |

## 🚀 Instalación y uso

### 1. Cloná el repositorio

```bash
git clone https://github.com/Dandlrt09/Datara.git
cd Datara
```

### 2. Cread el entorno virtual

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate
```

### 3. Instalá las dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurá la API key de Gemini

**Obtené tu key gratis:**
1. Andá a [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Iniciá sesión con tu cuenta de Google
3. Click en "Create API Key"
4. Copiá la key

**Dos formas de configurarla:**

**Opción A — Archivo `.env` (recomendado):**
```bash
# Crea un archivo .env en la raíz del proyecto con:
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx
```

**Opción B — Desde la app:**
1. Abrí la app (paso 5)
2. Andá a la sección **Settings**
3. Pegá tu API key en el campo y hacé click en **Aplicar cambios**

> ⚠️ La key queda guardada solo en la sesión del navegador. Al cerrar la app la perdés. Usá el archivo `.env` para no tener que configurarla cada vez.

### 5. Ejecutá la app

```bash
streamlit run app/main.py
```

Se abre en tu navegador en [http://localhost:8501](http://localhost:8501)

## 🎯 Cómo usarla

### Flujo básico

1. **Subí datos** → Cargá uno o más archivos CSV, Excel, JSON o TSV
2. **Chat con IA** → Preguntá en español sobre tus datos, pedí gráficos o análisis
3. **Constructor de gráficos** → Creá charts y KPIs manualmente abajo del chat
4. **Dashboard** → Todo se acumula, aplicá filtros globales para explorar

### Ejemplos de preguntas para la IA

| Tipo | Ejemplo |
|------|---------|
| 🔵 Texto | "¿Cuántas filas tiene el dataset?" |
| 🔵 Texto | "¿Cuál es la computadora más cara?" |
| 🟡 Tabla | "Mostrame el precio promedio por marca" |
| 🟡 Tabla | "Listá los 10 productos más vendidos" |
| 🔴 Gráfico | "Hacé un gráfico de barras con ventas por categoría" |
| 🔴 Gráfico | "Mostrame la distribución de precios con un histograma" |

## 📁 Estructura del proyecto

```
Datara/
├── app/
│   ├── main.py                    # Punto de entrada + init de sesión
│   ├── views/
│   │   ├── upload.py              # Carga de archivos (CSV, XLSX, JSON, TSV)
│   │   ├── chat.py                # Chat con IA + constructor + dashboard
│   │   └── settings.py            # Configuración de API key
│   └── components/
│       ├── chart_builder.py       # Constructor manual de gráficos y KPIs
│       ├── chart_download.py      # Botón de descarga para cada chart
│       ├── chat_message.py        # Renderizado de mensajes del chat
│       ├── dashboard.py           # Dashboard con filtros globales
│       ├── data_preview.py        # Vista previa del DataFrame
│       └── file_list.py           # Lista de archivos cargados
├── models/
│   ├── file_data.py               # Representación de un archivo subido
│   ├── chat_message.py            # Mensaje del chat (rol, contenido)
│   └── analysis_result.py         # Resultado de ejecución de código IA
├── services/
│   ├── file_service.py            # Gestión y parseo de archivos
│   ├── llm_service.py             # Comunicación con Gemini API
│   ├── code_executor.py           # Orquestación LLM + sandbox
│   └── export_service.py          # Exportación de resultados
├── utils/
│   ├── sandbox.py                 # Entorno seguro para ejecutar código
│   ├── prompts.py                 # Templates de prompts para la IA
│   └── validators.py              # Validación de archivos
├── tests/                         # Tests automatizados (190 tests)
│   ├── test_sandbox.py            # Tests del sandbox
│   ├── test_file_service.py       # Tests de carga y parseo
│   ├── test_export_service.py     # Tests de exportación
│   ├── test_code_executor.py      # Tests del orquestador LLM
│   ├── test_models.py             # Tests de modelos de datos
│   ├── test_validators.py         # Tests de validación
│   └── test_dashboard.py          # Tests del dashboard
├── Dataset/                       # Archivos de ejemplo para probar
├── .env                           # Tu API key (NO se sube a GitHub)
├── .env.example                   # Template de configuración
└── requirements.txt               # Dependencias
```

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

190 tests que cubren servicios, modelos, validación, dashboard y ejecución de código.

## 📄 Licencia

Este proyecto es de uso personal y educativo. Sentite libre de usarlo como inspiración o como parte de tu portfolio.
