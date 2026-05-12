"""
Prompt templates for LLM-powered data analysis.

The system prompt instructs the LLM to generate Python code using pandas
and plotly, which is then executed in a sandboxed environment.
"""

from __future__ import annotations

from models import FileData

SYSTEM_PROMPT = """
Sos un experto en análisis de datos con Python. Respondés en español argentino (voseo).

Siempre respondés con un bloque de código Python encerrado entre ```python y ```.
Dentro del bloque, asignás el resultado a UNA de estas variables:

  - `result_text` → un string con tu respuesta textual
  - `result_df`   → un DataFrame de pandas con la tabla resultante
  - `fig`         → un gráfico de Plotly (figura go.Figure o px.Figure)

NO uses print(). NO uses `input()`. El código se ejecuta automáticamente.

Ejemplo de respuesta textual:
```python
result_text = "El dataset tiene 6259 filas y 11 columnas."
```

Ejemplo de respuesta con tabla:
```python
result_df = df.groupby("marca").agg({"precio": ["mean", "count"]})
```

Ejemplo de respuesta con gráfico:
```python
fig = px.bar(df, x="marca", y="precio", title="Precio promedio por marca")
```

IMPORTANTE — NO USES IMPORT:
pd (pandas), np (numpy), px (plotly.express) y go (plotly.graph_objects)
ya están importados y disponibles. NO escribas import en tu código.

CUÁNDO USAR CADA VARIABLE — SÉ MUY PRECISO:

Usá `result_text` (string) CUANDO:
  - La respuesta es un número, un promedio, un total, un conteo
  - Te preguntan "cuál es", "cuál es la más/menos algo", "describí", "decime"
  - Mostrás el ranking, el más caro, el más barato, el/los primeros
  - Cualquier respuesta que se exprese naturalmente en una o dos oraciones
  EJ: "¿Cuál es la compu más cara?" → result_text = "La más cara es la #X con $5399, 66MHz, 1200MB HD, 32MB RAM, pantalla 17\""
  EJ: "¿Promedio de precios?" → result_text = "El precio promedio es $2219.58"

Usá `result_df` (DataFrame) CUANDO:
  - La pregunta pide explícitamente "tabla", "listado", "mostrame todos"
  - Es un resumen con múltiples filas agrupadas (ej: precio promedio POR marca)
  - Son datos agregados que tienen sentido como tabla

Usá `fig` (Plotly figure) CUANDO:
  - Te piden un "gráfico", "chart", "visualización"
  - Mostrás tendencias, distribuciones, comparaciones visuales

REGLAS DEL CÓDIGO:
a) Solo usá pandas, numpy y plotly.
b) NO uses open(), os, sys, subprocess, shutil, eval(), exec(), compile().
c) NO importes NADA (pd, np, px, go ya están disponibles).
d) Los gráficos deben tener título y etiquetas en los ejes.
e) El código se ejecuta automáticamente. No esperes input del usuario.
"""


def build_context(
    files: list[FileData],
    question: str,
    df_names: list[str] | None = None,
    chat_history: list | None = None,
) -> str:
    """
    Build the full context string sent to the LLM.

    Includes system prompt, file schemas with sample data, conversation
    history (for follow-up questions), and the current question.

    Args:
        files: Currently loaded data files.
        question: User's natural language question.
        df_names: Variable names for the dataframes (e.g. ["df_computers"]).
                  Passed from CodeExecutor._build_dataframe_map().
        chat_history: Previous messages for follow-up context.
    """
    parts = [f"SISTEMA:\n{SYSTEM_PROMPT.strip()}\n"]

    # ─── Conversation history ────────────────────────────────
    if chat_history:
        parts.append("HISTORIAL DE LA CONVERSACIÓN:\n")
        parts.append("-" * 40 + "\n")
        for msg in chat_history:
            role = "Usuario" if msg.role == "user" else "Asistente"
            # Only include last 6 messages to avoid context overflow
            content_preview = msg.content[:500] if msg.content else ""
            if content_preview:
                parts.append(f"{role}: {content_preview}\n")
        parts.append("-" * 40 + "\n")

    # ─── Available data ──────────────────────────────────────
    if not files:
        parts.append("No hay archivos cargados. Respondé que primero cargue datos.\n")
    else:
        parts.append("DATOS DISPONIBLES:\n")
        parts.append("-" * 40 + "\n")

        # Tell the LLM which variable names hold the dataframes
        if df_names:
            if len(df_names) == 1:
                parts.append(f"Los datos están en la variable `{df_names[0]}` (o simplemente `df`).\n\n")
            else:
                names_str = ", ".join(f"`{n}`" for n in df_names)
                parts.append(f"Los datos están en las variables: {names_str}. También `df` es la primera.\n\n")

        for f in files:
            parts.append(f.summary())
            parts.append("-" * 40 + "\n")

    # ─── Current question ────────────────────────────────────
    parts.append(
        "CONSIGNA: Esta es la nueva pregunta del usuario.\n"
        "Usá el historial arriba para entender el contexto "
        "si la pregunta es una continuación.\n"
    )
    parts.append(f"PREGUNTA DEL USUARIO:\n{question}\n")

    # ─── Response hint ───────────────────────────────────────
    parts.append(
        "Ahora generá tu respuesta como un bloque de código ```python "
        "con la variable result_text, result_df o fig según corresponda.\n"
        "Recordá: NO uses import. pd, np, px, go ya están importados. "
        "Los dataframes ya están cargados en las variables indicadas arriba."
    )

    return "\n".join(parts)
