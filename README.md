# Datara

**Una herramienta para analizar datos sin vueltas.** Subís un archivo —CSV, Excel, JSON, lo que sea— y podés hacer gráficos, calcular indicadores, o simplemente preguntarle a la IA qué quiere decir todo eso. No necesitás saber programar ni instalar cosas raras.

---

## ¿Qué puede hacer?

### Cargar datos y que no duela

Subís uno o varios archivos y la app los entiende solos. Si subís el mismo archivo dos veces te avisa y te deja elegir si reemplazarlo o quedarte con los dos. No importa si el CSV usa comas, punto y coma, o tabulaciones — lo detecta solo.

### Hacer gráficos sin escribir código

Seleccionás el tipo de gráfico y elegís qué columnas van en cada eje. Barra, línea, dispersión, torta, histograma, box plot — los clásicos. Si no tenés ganas de elegir, le pedís a la IA que lo haga por vos.

### Indicadores al instante

Tarjetas con promedios, sumas, mínimos, máximos o conteos. Elegís la columna y el tipo de cálculo, y si querés podés agruparlo por categoría. Aparecen al toque arriba del dashboard.

### Filtros que afectan todo a la vez

Seleccionás una columna para filtrar y tanto los gráficos como los indicadores se actualizan solos. No hay que tocar nada más.

### Un dashboard que acumula todo

Cada gráfico o KPI que creás se va agregando al dashboard. Podés descargar cada gráfico como PNG o exportar los datos. Si querés empezar de nuevo, un botón limpia todo.

### Chat con IA

Le preguntás en español lo que quieras saber y la IA te responde con texto, una tabla o un gráfico — elige lo que tenga más sentido según lo que preguntaste. Podés hacer preguntas encadenadas: "mostrame las ventas por mes", "ordená de mayor a menor", "mostrá solo los 3 más altos". También podés descargar la conversación completa.

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

Esta guía la puede seguir cualquiera —hayas usado Python o no—. Solo tenés que copiar y pegar comandos.

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

Ya está, el proyecto está en tu compu.

### 2. Instalá Python (si no lo tenés)

Esta app funciona con Python 3.10 o superior. Para ver si lo tenés:

```bash
python --version
```

Si ves algo como `Python 3.10.`... o superior, pasá al paso 3.

**Si no lo tenés:**

- **Windows**: andá a [python.org/downloads](https://python.org/downloads), descargá la última versión, ejecutá el instalador y **marcá la casilla "Add Python to PATH"**. Esa casilla es importante.
- **Mac**: `brew install python@3.12` (necesitás [Homebrew](https://brew.sh/)) o descargá de [python.org/downloads](https://python.org/downloads).
- **Linux**: `sudo apt install python3 python3-venv python3-pip`

### 3. Creá el entorno virtual

Esto crea una carpeta `venv/` donde se instalan las dependencias, así no ensuciás tu sistema:

```bash
python -m venv venv
```

Después **activá el entorno**:

| Sistema | Comando |
|---------|---------|
| **Windows** (PowerShell) | `venv\Scripts\activate` |
| **Windows** (CMD) | `venv\Scripts\activate.bat` |
| **Mac / Linux** | `source venv/bin/activate` |

Sabés que funcionó porque te aparece `(venv)` al principio de la línea:

```
(venv) C:\Users\tu-usuario\Datara>
```

### 4. Instalá las dependencias

Con el entorno activado (el `(venv)` está visible), corré:

```bash
pip install -r requirements.txt
```

Esto descarga todo lo que la app necesita. Tarda entre 30 segundos y 2 minutos. Si ves barras de progreso y texto amarillo, va bien. Si ves un error rojo que habla de `Python 3.10` o `version`, es porque tu Python es muy viejo — volvé al paso 2.

### 5. Configurá la API key de Gemini

La app necesita una clave de Gemini para usar la IA. **Es gratis y la sacás en 2 minutos:**

1. Andá a [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Iniciá sesión con tu cuenta de Google
3. Tocá **"Create API Key"**
4. Copiá la clave (empieza con `AIza...`)

Ahora creá un archivo `.env` en la carpeta del proyecto:

```bash
# Windows (PowerShell):
New-Item -ItemType File -Name ".env"

# Mac / Linux:
touch .env
```

Abrí ese archivo con el bloc de notas, TextEdit o VS Code y poné esto:

```
GEMINI_API_KEY=AIzaSy_PEGATUKEYACA
```

Cambiá `AIzaSy_PEGATUKEYACA` por tu clave real. Guardá el archivo.

**Ojo**: el archivo se llama `.env` con un punto adelante, no `env` ni `.env.txt`. En Windows capaz no te muestra el nombre completo; si ves ".env" solo, está bien.

### 6. Ejecutá la app

Con el entorno activado (acordate: tiene que aparecer `(venv)`), corré:

```bash
python run.py
```

Si todo funciona, ves algo así:

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Eso significa que la app ya está corriendo. **Abrí tu navegador** (Chrome, Edge, Firefox, el que sea) y andá a:

👉 **http://localhost:8000**

¡Ya estás adentro!

---

### Si algo sale mal

| Problema | Qué hacer |
|----------|-----------|
| `Python no se reconoce...` | No instalaste Python o no marcaste "Add to PATH". Volvé al paso 2. |
| `Error: No module named...` | Te faltó el paso 4. Corré `pip install -r requirements.txt` de nuevo. |
| `API key inválida` | En la app, andá a Settings y verificá que la key esté bien pegada. |
| `Modelo no encontrado` | Apretá "Reset session" en la app o reiniciá el servidor (Ctrl+C y `python run.py` de vuelta). |

### Cómo cerrar la app

En la terminal donde está corriendo la app, apretá **Ctrl + C** y se apaga.

---

## Cómo se usa

1. **Subí datos** — uno o más archivos (CSV, Excel, JSON, TSV)
2. **Chat con IA** — preguntale sobre tus datos en español, pedile gráficos o análisis
3. **Constructor manual** — creá charts y KPIs vos mismo debajo del chat
4. **Dashboard** — todo se acumula, aplicá filtros globales para explorar

Algunas preguntas que le podés hacer a la IA:

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
├── uploads/            → Archivos que subís (no se sube a Git)
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

Corren 400+ tests automáticos que cubren todo: APIs, servicios, modelos, frontend, y ejecución de código.

---

## Licencia

**MIT** — podés usar, copiar, modificar y distribuir este software libremente, siempre que mantengas el aviso de copyright original. El software se proporciona "tal cual", sin garantía de ningún tipo. Más detalles en [LICENSE](./LICENSE).
