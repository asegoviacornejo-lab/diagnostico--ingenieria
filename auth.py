import streamlit as st
import hashlib
from database import execute, fetch_one


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(email: str, password: str):
    execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, hash_password(password))
    )


def authenticate(email: str, password: str):
    user = fetch_one(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    if user and user["password_hash"] == hash_password(password):
        return user["id"]
    return None


def auth_view():
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Entrar"):
        user_id = authenticate(email, password)
        if user_id:
            st.session_state.user_id = user_id
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
