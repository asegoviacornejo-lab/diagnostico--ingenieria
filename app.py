import streamlit as st
import json
from pathlib import Path

st.title("Calculadora de Horas Autonomas por Asignatura")

st.write("Selecciona tus asignaturas para estimar las horas autonomas necesarias.")

ARCHIVO_DATOS = Path("datos_usuario.json")


def cargar_datos():
    if ARCHIVO_DATOS.exists():
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    return {
        "asignaturas_seleccionadas": [],
        "agregar_otra": False,
        "nombre_extra": "",
        "sct_extra": 4
    }


def guardar_datos(datos):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


asignaturas_base = {
    "Calculo I": 6,
    "Algebra I": 6,
    "Fisica I": 5,
    "Quimica General": 5,
    "Introduccion a la Ingenieria": 3,
    "Programacion": 4
}

valor_sct = 27
semanas_semestre = 18
horas_directas_por_semana = 4

datos_guardados = cargar_datos()

asignaturas_seleccionadas = st.multiselect(
    "Selecciona tus asignaturas",
    list(asignaturas_base.keys()),
    default=datos_guardados["asignaturas_seleccionadas"]
)

st.subheader("Agregar otra asignatura")

agregar_otra = st.checkbox(
    "Quiero agregar una asignatura que no esta en la lista",
    value=datos_guardados["agregar_otra"]
)

nombre_extra = ""
sct_extra = 4

if agregar_otra:
    nombre_extra = st.text_input(
        "Nombre de la asignatura",
        value=datos_guardados["nombre_extra"]
    )

    sct_extra = st.number_input(
        "Creditos transferibles de la asignatura",
        min_value=1,
        max_value=20,
        value=datos_guardados["sct_extra"],
        step=1
    )

datos_actuales = {
    "asignaturas_seleccionadas": asignaturas_seleccionadas,
    "agregar_otra": agregar_otra,
    "nombre_extra": nombre_extra,
    "sct_extra": sct_extra
}

guardar_datos(datos_actuales)

st.subheader("Resultados")

todas_las_asignaturas = {}

for asignatura in asignaturas_seleccionadas:
    todas_las_asignaturas[asignatura] = asignaturas_base[asignatura]

if agregar_otra and nombre_extra:
    todas_las_asignaturas[nombre_extra] = sct_extra

if len(todas_las_asignaturas) == 0:
    st.info("Selecciona al menos una asignatura para ver el calculo.")
else:
    for asignatura, sct in todas_las_asignaturas.items():
        horas_totales_semestre = sct * valor_sct
        horas_totales_semana = horas_totales_semestre / semanas_semestre
        horas_autonomas_semana = horas_totales_semana - horas_directas_por_semana

        st.write("Asignatura:", asignatura)
        st.write("SCT:", sct)
        st.write("Horas autonomas necesarias por semana:", round(horas_autonomas_semana, 1))
        st.divider()
