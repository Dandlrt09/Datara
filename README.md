# Datara

**Una herramienta para analizar datos sin complicaciones.** Puedes subir un archivo —CSV, Excel, JSON, lo que sea— y hacer gráficos, calcular indicadores, o simplemente preguntarle a la IA qué significa todo eso. No necesitas saber programar ni instalar cosas raras.

---

## ¿Qué puede hacer?

### Cargar datos sin dolor

Puedes subir uno o varios archivos y la app los entiende solos. Si subes el mismo archivo dos veces te avisa y te deja elegir si reemplazarlo o quedarte con los dos. No importa si el CSV usa comas, punto y coma o tabulaciones — lo detecta solo.

### Hacer gráficos sin escribir código

Seleccionas el tipo de gráfico y eliges qué columnas van en cada eje. Barra, línea, dispersión, torta, histograma, box plot — los clásicos. Si no tienes ganas de elegir, puedes pedirle a la IA que lo haga por ti.

### Indicadores al instante

Tarjetas con promedios, sumas, mínimos, máximos o conteos. Eliges la columna y el tipo de cálculo, y si quieres puedes agruparlo por categoría. Aparecen de inmediato arriba del dashboard.

### Filtros que afectan todo a la vez

Seleccionas una columna para filtrar y tanto los gráficos como los indicadores se actualizan solos. No hay que tocar nada más.

### Un dashboard que acumula todo

Cada gráfico o KPI que creas se va agregando al dashboard. Puedes descargar cada gráfico como PNG o exportar los datos. Si quieres empezar de nuevo, un botón lo limpia todo.

### Chat con IA

Le preguntas en español lo que quieras saber y la IA te responde con texto, una tabla o un gráfico — elige lo que tenga más sentido según lo que preguntaste. Puedes hacer preguntas encadenadas: "muéstrame las ventas por mes", "ordena de mayor a menor", "muestra solo los 3 más altos". También puedes descargar la conversación completa.

### El código que genera la IA corre en una caja segura

Por seguridad, el código generado por la IA solo puede usar `pandas`, `numpy` y `plotly`. No puede acceder al sistema de archivos, ni a la red, ni ejecutar comandos. Si tarda más de 30 segundos se corta solo.

---

## Con qué está construido

| Capa | Qué usa |
|------|---------|
| Backend | FastAPI con Uvicorn |
| Frontend | HTML, CSS y JavaScript plano — sin frameworks, sin peso muerto |
| Gráficos | Plotly.js |
| Procesamiento | Pandas y OpenPyXL |
| IA | Gemini 2.5 Flash (de Google) |
| Tests | pytest |
| Python | 3.10 o superior |

---

## Cómo levantarlo en tu máquina

Esta guía la puede seguir cualquiera —hayas usado Python o no—. Solo tienes que copiar y pegar comandos.

### 1. Descarga el proyecto

Abre una terminal:
- **Windows**: presiona `Win + R`, escribe `powershell` y presiona Enter.
- **Mac**: abre "Terminal" desde el Launchpad.
- **Linux**: abre tu terminal (Ctrl+Alt+T en Ubuntu).

Pega esto y presiona Enter:

```bash
git clone https://github.com/Dandlrt09/Datara.git
cd Datara
```

Ya está, el proyecto está en tu computadora.

### 2. Instala Python (si no lo tienes)

Esta app funciona con Python 3.10 o superior. Para ver si lo tienes:

```bash
python --version
```

Si ves algo como `Python 3.10...` o superior, pasa al paso 3.

**Si no lo tienes:**

- **Windows**: ve a [python.org/downloads](https://python.org/downloads), descarga la última versión, ejecuta el instalador y **marca la casilla "Add Python to PATH"**. Esa casilla es importante.
- **Mac**: `brew install python@3.12` (necesitas [Homebrew](https://brew.sh/)) o descarga de [python.org/downloads](https://python.org/downloads).
- **Linux**: `sudo apt install python3 python3-venv python3-pip`

### 3. Crea el entorno virtual

Esto crea una carpeta `venv/` donde se instalan las dependencias, así no ensucia tu sistema:

```bash
python -m venv venv
```

Después **activa el entorno**:

| Sistema | Comando |
|---------|---------|
| **Windows** (PowerShell) | `venv\Scripts\activate` |
| **Windows** (CMD) | `venv\Scripts\activate.bat` |
| **Mac / Linux** | `source venv/bin/activate` |

Sabes que funcionó porque aparece `(venv)` al principio de la línea:

```
(venv) C:\Users\tu-usuario\Datara>
```

### 4. Instala las dependencias

Con el entorno activado (el `(venv)` está visible), ejecuta:

```bash
pip install -r requirements.txt
```

Esto descarga todo lo que la app necesita. Tarda entre 30 segundos y 2 minutos. Si ves barras de progreso y texto amarillo, va bien. Si ves un error rojo que habla de `Python 3.10` o `version`, es porque tu Python es muy viejo — vuelve al paso 2.

### 5. Configura la API key de Gemini

La app necesita una clave de Gemini para usar la IA. **Es gratis y la consigues en 2 minutos:**

1. Ve a [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Inicia sesión con tu cuenta de Google
3. Haz clic en **"Create API Key"**
4. Copia la clave que te dan (empieza con `AIza...`)

Ahora crea un archivo `.env` en la carpeta del proyecto:

```bash
# Windows (PowerShell):
New-Item -ItemType File -Name ".env"

# Mac / Linux:
touch .env
```

Abre ese archivo con el bloc de notas, TextEdit o VS Code y pon esto:

```
GEMINI_API_KEY=AIzaSy_PEGATUKEYACA
```

Cambia `AIzaSy_PEGATUKEYACA` por tu clave real. Guarda el archivo.

**Importante**: el archivo se llama `.env` con un punto al inicio, no `env` ni `.env.txt`. En Windows puede que no muestre el nombre completo; si ves ".env" solo, está bien.

### 6. Ejecuta la app

Con el entorno activado (recuerda: tiene que aparecer `(venv)`), ejecuta:

```bash
python run.py
```

Si todo funciona, ves algo así:

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Eso significa que la app ya está corriendo. **Abre tu navegador** (Chrome, Edge, Firefox, el que sea) y ve a:

👉 **http://localhost:8000**

¡Ya estás dentro!

---

### Si algo sale mal

| Problema | Qué hacer |
|----------|-----------|
| `Python no se reconoce...` | No instalaste Python o no marcaste "Add to PATH". Vuelve al paso 2. |
| `Error: No module named...` | Te faltó el paso 4. Ejecuta `pip install -r requirements.txt` de nuevo. |
| `API key inválida` | En la app, ve a Settings y verifica que la key esté bien pegada. |
| `Modelo no encontrado` | Presiona "Reset session" en la app o reinicia el servidor (Ctrl+C y `python run.py` de nuevo). |

### Cómo cerrar la app

En la terminal donde está corriendo la app, presiona **Ctrl + C** y se apaga.

---

## Cómo se usa

1. **Sube datos** — uno o más archivos (CSV, Excel, JSON, TSV)
2. **Chat con IA** — pregúntale sobre tus datos en español, pídele gráficos o análisis
3. **Constructor manual** — crea charts y KPIS tú mismo debajo del chat
4. **Dashboard** — todo se acumula, aplica filtros globales para explorar

Algunas preguntas que puedes hacerle a la IA:

| Tipo | Ejemplo |
|------|---------|
| Texto | "¿Cuántas filas tiene el dataset?" |
| Texto | "¿Cuál es la computadora más cara?" |
| Tabla | "Muéstrame el precio promedio por marca" |
| Tabla | "Lista los 10 productos más vendidos" |
| Gráfico | "Haz un gráfico de barras con ventas por categoría" |
| Gráfico | "Muéstrame la distribución de precios con un histograma" |

---

## Cómo está organizado el proyecto

```
Datara/
├── run.py              → El archivo que arranca todo (python run.py)
├── api/                → El backend (FastAPI)
├── frontend/           → La interfaz que ves en el navegador
├── services/           → La lógica pesada (Gemini, sandbox, archivos)
├── models/             → Cómo se representan los datos internamente
├── utils/              → Herramientas varias (prompts, validación, sandbox)
├── tests/              → Tests automatizados
│   └── fixtures/       → Datos de ejemplo para probar
├── uploads/            → Archivos que subes (no se sube a Git)
├── archives/           → Sesiones guardadas (no se sube a Git)
├── .env                → Tu API key (no se sube a GitHub)
├── requirements.txt    → Dependencias del proyecto
└── LICENSE             → Licencia MIT
```

---

## Tests

```bash
python -m pytest tests/ -v
```

Corren 400+ tests automáticos que cubren todo: APIs, servicios, modelos, frontend y ejecución de código.

---

## Licencia

**MIT** — puedes usar, copiar, modificar y distribuir este software libremente, siempre que mantengas el aviso de copyright original. El software se proporciona "tal cual", sin garantía de ningún tipo. Más detalles en [LICENSE](./LICENSE).
