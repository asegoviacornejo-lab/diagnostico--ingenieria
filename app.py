import streamlit as st

st.title("Diagnostico Academico Inteligente")

st.write("Esta app calcula una estimacion basica de carga academica SCT.")

valor_sct = st.number_input("Valor de 1 SCT en horas", value=27)
semanas = st.number_input("Cantidad de semanas del semestre", value=18)

nombre_asignatura = st.text_input("Nombre de la asignatura")
sct = st.number_input("SCT de la asignatura", value=6)

horas_disponibles = st.number_input("Horas semanales disponibles fuera de clases", value=20)

horas_semestrales = sct * valor_sct
horas_semanales = horas_semestrales / semanas
diferencia = horas_disponibles - horas_semanales

st.subheader("Resultados")

st.write("Asignatura:", nombre_asignatura)
st.write("Horas semestrales:", horas_semestrales)
st.write("Horas semanales esperadas:", horas_semanales)

if diferencia < 0:
    st.error(f"Deficit de {abs(diferencia):.1f} horas semanales")
elif diferencia > 0:
    st.success(f"Superavit de {diferencia:.1f} horas semanales")
else:
    st.info("Estas en equilibrio")
