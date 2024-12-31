import streamlit as st
import psycopg2
import pandas as pd
import altair as alt
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Database connection
def get_connection():
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Database setup
def setup_database():
    conn = get_connection()
    if conn is not None:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitors (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id SERIAL PRIMARY KEY,
                competitor_id INTEGER REFERENCES competitors(id) ON DELETE CASCADE,
                votes INTEGER DEFAULT 0
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()

# Utility functions
def add_category(category_name):
    if category_name:
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categories (name) VALUES (%s)", (category_name,))
                conn.commit()
            except psycopg2.errors.UniqueViolation:
                st.warning(f"A categoria '{category_name}' já existe.")
            cursor.close()
            conn.close()

def add_competitor(category_name, competitor_name):
    if category_name and competitor_name:
        conn = get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = %s", (category_name,))
            category = cursor.fetchone()
            if category:
                cursor.execute("""
                    INSERT INTO competitors (name, category_id)
                    VALUES (%s, %s)
                    RETURNING id;
                """, (competitor_name, category[0]))
                competitor_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO votes (competitor_id) VALUES (%s)", (competitor_id,))
                conn.commit()
            cursor.close()
            conn.close()

def remove_category(category_name):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE name = %s", (category_name,))
        conn.commit()
        cursor.close()
        conn.close()

def remove_competitor(category_name, competitor_name):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM competitors
            WHERE name = %s AND category_id = (SELECT id FROM categories WHERE name = %s)
        """, (competitor_name, category_name))
        conn.commit()
        cursor.close()
        conn.close()

def vote(category_name, competitor_name):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE votes
            SET votes = votes + 1
            WHERE competitor_id = (
                SELECT c.id FROM competitors c
                JOIN categories cat ON c.category_id = cat.id
                WHERE cat.name = %s AND c.name = %s
            )
        """, (category_name, competitor_name))
        conn.commit()
        cursor.close()
        conn.close()

def get_results(query, params=None):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    return []

# Streamlit App
st.set_page_config(page_title="Melhores do Ano - Votação", layout="wide")

st.title("🏆 Melhores do Ano - Votação")
st.write("Vote nos seus favoritos! Adicione categorias e competidores para começar.")

# Initialize database
setup_database()

# Sidebar for Admin Actions
st.sidebar.header("Administração")
action = st.sidebar.radio("Ação:", ["Adicionar", "Remover", "Resultados"])

if action == "Adicionar":
    st.sidebar.subheader("Adicionar Categoria")
    new_category = st.sidebar.text_input("Nome da Categoria")
    if st.sidebar.button("Adicionar Categoria"):
        add_category(new_category)
        st.sidebar.success(f"Categoria '{new_category}' adicionada!")

    st.sidebar.subheader("Adicionar Competidor")
    categories = [row[0] for row in get_results("SELECT name FROM categories")]
    if categories:
        selected_category = st.sidebar.selectbox("Selecione uma Categoria", categories)
        new_competitor = st.sidebar.text_input("Nome do Competidor")
        if st.sidebar.button("Adicionar Competidor"):
            add_competitor(selected_category, new_competitor)
            st.sidebar.success(f"Competidor '{new_competitor}' adicionado à categoria '{selected_category}'!")
    else:
        st.sidebar.warning("Adicione categorias antes de adicionar competidores.")

elif action == "Remover":
    st.sidebar.subheader("Remover Categoria")
    categories = [row[0] for row in get_results("SELECT name FROM categories")]
    if categories:
        category_to_remove = st.sidebar.selectbox("Selecione uma Categoria", categories)
        if st.sidebar.button("Remover Categoria"):
            remove_category(category_to_remove)
            st.sidebar.success(f"Categoria '{category_to_remove}' removida!")

    st.sidebar.subheader("Remover Competidor")
    selected_category = st.sidebar.selectbox("Selecione uma Categoria", categories, key="remove_comp")
    if selected_category:
        competitors = [row[0] for row in get_results("SELECT name FROM competitors WHERE category_id = (SELECT id FROM categories WHERE name = %s)", (selected_category,))]
        competitor_to_remove = st.sidebar.selectbox("Selecione um Competidor", competitors)
        if st.sidebar.button("Remover Competidor"):
            remove_competitor(selected_category, competitor_to_remove)
            st.sidebar.success(f"Competidor '{competitor_to_remove}' removido da categoria '{selected_category}'!")

elif action == "Resultados":
    st.sidebar.subheader("Resultados")
    categories = [row[0] for row in get_results("SELECT name FROM categories")]
    selected_category = st.sidebar.selectbox("Selecione uma Categoria", categories)
    if selected_category:
        results = get_results("""
            SELECT c.name, v.votes
            FROM competitors c
            JOIN votes v ON c.id = v.competitor_id
            JOIN categories cat ON c.category_id = cat.id
            WHERE cat.name = %s
        """, (selected_category,))
        if results:
            st.subheader(f"Resultados - {selected_category}")
            results_df = pd.DataFrame(results, columns=["Competidor", "Votos"])
            chart = alt.Chart(results_df).mark_bar().encode(
                x="Competidor",
                y="Votos",
                color="Competidor"
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.sidebar.info("Sem resultados disponíveis para esta categoria.")

# Main Page - Voting
categories = [row[0] for row in get_results("SELECT name FROM categories")]
if categories:
    for category in categories:
        st.subheader(f"Categoria: {category}")
        competitors = [row[0] for row in get_results("""
            SELECT name FROM competitors WHERE category_id = (SELECT id FROM categories WHERE name = %s)
        """, (category,))]
        for competitor in competitors:
            if st.button(f"Votar em {competitor}", key=f"{category}_{competitor}"):
                vote(category, competitor)
                st.success(f"Voto computado para '{competitor}' na categoria '{category}'!")
else:
    st.info("Adicione categorias e competidores na barra lateral para começar a votação.")
