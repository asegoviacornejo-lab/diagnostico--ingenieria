import streamlit as st

st.title("Calculadora de Horas Autonomas por Asignatura")

st.write("Selecciona una asignatura para estimar sus horas autonomas necesarias.")

asignaturas = {
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

asignatura_seleccionada = st.selectbox(
    "Selecciona tu asignatura",
    list(asignaturas.keys())
)

sct = asignaturas[asignatura_seleccionada]

horas_totales_semestre = sct * valor_sct
horas_totales_semana = horas_totales_semestre / semanas_semestre
horas_autonomas_semana = horas_totales_semana - horas_directas_por_semana

st.subheader("Resultado")

st.write("Asignatura seleccionada:", asignatura_seleccionada)
st.write("SCT:", sct)
st.write("Horas totales estimadas por semestre:", horas_totales_semestre)
st.write("Horas totales estimadas por semana:", round(horas_totales_semana, 1))
st.write("Horas autonomas necesarias por semana:", round(horas_autonomas_semana, 1))
