import json
from pathlib import Path

import streamlit as st


ARCHIVO_DATOS = Path("datos_usuario.json")


def cargar_datos():
    if ARCHIVO_DATOS.exists():
        try:
            with open(ARCHIVO_DATOS, "r", encoding="utf-8") as archivo:
                return json.load(archivo)
        except json.JSONDecodeError:
            pass

    return {
        "asignaturas_seleccionadas": [],
        "agregar_otra": False,
        "nombre_extra": "",
        "sct_extra": 4,
    }


def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def calcular_horas_autonomas(sct, valor_sct, semanas_semestre, horas_directas):
    horas_totales_semestre = sct * valor_sct
    horas_totales_semana = horas_totales_semestre / semanas_semestre
    horas_autonomas_semana = horas_totales_semana - horas_directas

    if horas_autonomas_semana < 0:
        horas_autonomas_semana = 0

    return horas_totales_semestre, horas_totales_semana, horas_autonomas_semana


st.set_page_config(
    page_title="Diagnóstico Académico Inteligente",
    page_icon="🎓",
    layout="centered",
)

st.markdown(
    """
    <style>
    .main .block-container {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #1f2937;
    }

    .resultado-principal {
        background-color: #eef6ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        padding: 1.2rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }

    .tarjeta-asignatura {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
    }

    .texto-suave {
        color: #4b5563;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("Diagnóstico Académico Inteligente")
st.write(
    "Selecciona tus asignaturas para estimar cuántas horas autónomas de estudio necesitas por semana."
)


asignaturas_base = {
    "Cálculo I": 6,
    "Álgebra I": 6,
    "Física I": 5,
    "Química General": 5,
    "Introducción a la Ingeniería": 3,
    "Programación": 4,
}

valor_sct = 27
semanas_semestre = 18
horas_directas_por_semana = 4

datos_guardados = cargar_datos()


st.subheader("Asignaturas")

asignaturas_seleccionadas = st.multiselect(
    "Selecciona las asignaturas que estás cursando",
    list(asignaturas_base.keys()),
    default=datos_guardados["asignaturas_seleccionadas"],
)

agregar_otra = st.checkbox(
    "Quiero agregar una asignatura que no está en la lista",
    value=datos_guardados["agregar_otra"],
)

nombre_extra = ""
sct_extra = 4

if agregar_otra:
    st.markdown("#### Nueva asignatura")

    nombre_extra = st.text_input(
        "Nombre de la asignatura",
        value=datos_guardados["nombre_extra"],
        placeholder="Ejemplo: Economía, Inglés, Dibujo de Ingeniería",
    )

    sct_extra = st.number_input(
        "Créditos transferibles de la asignatura",
        min_value=1,
        max_value=20,
        value=datos_guardados["sct_extra"],
        step=1,
    )


datos_actuales = {
    "asignaturas_seleccionadas": asignaturas_seleccionadas,
    "agregar_otra": agregar_otra,
    "nombre_extra": nombre_extra,
    "sct_extra": sct_extra,
}

guardar_datos(datos_actuales)


st.subheader("Resultados")

todas_las_asignaturas = {}

for asignatura in asignaturas_seleccionadas:
    todas_las_asignaturas[asignatura] = asignaturas_base[asignatura]

if agregar_otra and nombre_extra.strip():
    todas_las_asignaturas[nombre_extra.strip()] = sct_extra


if len(todas_las_asignaturas) == 0:
    st.info("Selecciona al menos una asignatura para ver el cálculo.")
else:
    total_horas_autonomas = 0

    for asignatura, sct in todas_las_asignaturas.items():
        horas_semestre, horas_semana, horas_autonomas = calcular_horas_autonomas(
            sct,
            valor_sct,
            semanas_semestre,
            horas_directas_por_semana,
        )

        total_horas_autonomas += horas_autonomas

        st.markdown(
            f"""
            <div class="tarjeta-asignatura">
                <h4>{asignatura}</h4>
                <p><strong>Créditos transferibles:</strong> {sct}</p>
                <p><strong>Horas totales por semestre:</strong> {horas_semestre:.1f}</p>
                <p><strong>Horas totales por semana:</strong> {horas_semana:.1f}</p>
                <p><strong>Horas autónomas necesarias por semana:</strong> {horas_autonomas:.1f}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="resultado-principal">
            <h3>Total semanal estimado</h3>
            <p class="texto-suave">
                Considerando las asignaturas seleccionadas, necesitas aproximadamente:
            </p>
            <h2>{total_horas_autonomas:.1f} horas autónomas por semana</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Cálculo usado: horas autónomas semanales = ((SCT × 27) ÷ 18) - horas directas semanales."
    )
