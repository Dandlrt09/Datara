# Datara

**Analizá tus datos con lenguaje natural.** Subí archivos CSV o Excel, hacé preguntas en español, y obtené respuestas, tablas y gráficos al instante — todo potenciado por inteligencia artificial.

---

## ✨ Funcionalidades

- **Carga de archivos**: CSV (auto-detecta delimitador) y Excel (.xlsx) con selección de hojas
- **Múltiples archivos**: Cargá varios archivos y la IA los relaciona automáticamente
- **Preguntas en lenguaje natural**: "¿Cuál es el promedio de precios?", "Mostrame un gráfico de ventas por mes"
- **Respuestas inteligentes**: La IA decide si responderte con texto, una tabla o un gráfico según lo que preguntes
- **Gráficos interactivos**: Plotly con zoom, descarga PNG y exportación de datos del gráfico
- **Historial de conversación**: Preguntá varias veces, la IA recuerda el contexto
- **Exportación**: Descargá la conversación como .txt, los resultados como CSV, y los gráficos como PNG
- **Preguntas encadenadas**: Hacé seguimiento — "ordená por precio", "mostrame solo los 3 más caros"

## 🧱 Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | [Streamlit](https://streamlit.io/) |
| Datos | [Pandas](https://pandas.pydata.org/) + [OpenPyXL](https://openpyxl.readthedocs.io/) |
| Gráficos | [Plotly](https://plotly.com/python/) |
| IA | [Gemini 2.5 Flash](https://ai.google.dev/) (vía API de OpenAI-compatible) |
| Tests | [pytest](https://docs.pytest.org/) |

## 📋 Requisitos

- Python 3.10+
- Una API key de Gemini (gratuita)

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

1. **Subí datos**: Cargá uno o más archivos CSV o Excel
2. **Preguntá**: Escribí preguntas en español sobre tus datos
3. **Explorá**: La IA te responde con texto, tablas o gráficos
4. **Iterá**: Hacé preguntas de seguimiento para profundizar

### Ejemplos de preguntas

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
│   ├── main.py                # Punto de entrada de la app
│   ├── views/                 # Vistas de la app (upload, chat, settings)
│   ├── components/            # Componentes reutilizables (chart, preview)
├── models/                    # Modelos de datos (FileData, ChatMessage, AnalysisResult)
├── services/                  # Lógica de negocio
│   ├── file_service.py        # Carga y gestión de archivos
│   ├── llm_service.py         # Comunicación con Gemini API
│   ├── code_executor.py       # Orquestación LLM + sandbox
│   ├── export_service.py      # Exportación de resultados
├── utils/
│   ├── sandbox.py             # Entorno seguro para ejecutar código Python
│   ├── prompts.py             # Templates de prompts para la IA
│   ├── validators.py          # Validación de archivos
├── tests/                     # Tests automatizados (145 tests)
│   ├── test_sandbox.py        # Tests del sandbox de ejecución
│   ├── test_file_service.py   # Tests del servicio de archivos
│   ├── test_export_service.py # Tests de exportación
│   ├── test_code_executor.py  # Tests del ejecutor de código
│   ├── test_models.py         # Tests de modelos de datos
│   └── test_validators.py     # Tests de validación
├── Dataset/                   # Archivos de ejemplo para probar
├── .env                       # Tu API key (NO se sube a GitHub)
├── .env.example               # Template de configuración
└── requirements.txt           # Dependencias
```

## 🔒 Seguridad

El código generado por la IA se ejecuta en un **sandbox** que:

- ✅ Solo permite usar `pandas`, `numpy` y `plotly`
- ✅ Bloquea `import os`, `open()`, `eval()`, `exec()`, `subprocess`
- ✅ Tiene timeout automático (30 segundos)
- ✅ No tiene acceso al sistema de archivos ni a la red

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

145 tests que cubren todos los servicios de la aplicación.

## 📄 Licencia

Este proyecto es de uso personal y educativo. Sentite libre de usarlo como inspiración o como parte de tu portfolio.
