import streamlit as st
import psycopg2
import pandas as pd
import altair as alt
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente

DATABASE_URL = os.getenv("DATABASE_URL")

# Função de conexão com o banco de dados
def get_connection():
    try:
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Função para criar tabelas no banco de dados se não existirem
def setup_database():
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS competitors (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category_id INTEGER REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            competitor_id INTEGER REFERENCES competitors(id),
            user_ip VARCHAR(255) NOT NULL
        );
        """)
        conn.commit()
        cur.close()
        conn.close()

# Função para obter resultados das categorias
def get_results(query, params=None):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    return []

# Função para adicionar categorias ou competidores
def add_category(name):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (name,))
        conn.commit()
        cur.close()
        conn.close()

def add_competitor(name, category_id):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO competitors (name, category_id) VALUES (%s, %s);", (name, category_id))
        conn.commit()
        cur.close()
        conn.close()

# Função para remover categorias ou competidores
def remove_category(category_name):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM categories WHERE name = %s;", (category_name,))
        conn.commit()
        cur.close()
        conn.close()

def remove_competitor(competitor_name):
    conn = get_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM competitors WHERE name = %s;", (competitor_name,))
        conn.commit()
        cur.close()
        conn.close()

# Iniciar o banco de dados
setup_database()

# Configuração da página
st.set_page_config(page_title="Melhores do Ano - Votação", layout="wide")

# Estilos personalizados (CSS)
st.markdown("""
    <style>
        body {
            background-color: #f9f9f9;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        .sidebar .sidebar-content {
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            border-radius: 10px;
        }
        .stButton > button {
            background-color: #FF9800;
            color: white;
            font-size: 16px;
            border-radius: 8px;
            padding: 12px 24px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            transition: background-color 0.3s ease-in-out;
        }
        .stButton > button:hover {
            background-color: #FF5722;
        }
        .stTextInput input, .stSelectbox select {
            font-size: 16px;
            padding: 10px;
            border-radius: 8px;
            background-color: #fff;
            border: 2px solid #ddd;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        }
        .stTextInput input:focus, .stSelectbox select:focus {
            border-color: #FF9800;
            outline: none;
        }
        .stRadio > div > label {
            font-weight: bold;
            color: #333;
        }
        .stTable th {
            background-color: #FF9800;
            color: white;
            font-weight: bold;
            border-radius: 10px;
        }
        .stTable td {
            background-color: #f9f9f9;
        }
        .winner-box {
            display: flex;
            justify-content: center;
            align-items: center;
            border-radius: 10px;
            background-color: #FF9800;
            padding: 15px;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        }
        .winner-box img {
            width: 50px;
            margin-right: 15px;
        }
        .category-header {
            font-size: 1.5rem;
            color: #333;
            margin-top: 20px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Cabeçalho
st.title("🏆 Melhores do Ano - Votação")
st.write("Vote nos seus favoritos! Adicione categorias e competidores para começar.")

# Sidebar para administração
st.sidebar.header("Administração")
action = st.sidebar.radio("Ação:", ["Adicionar", "Remover", "Resultados"])

if action == "Adicionar":
    st.sidebar.subheader("Adicionar Categoria")
    new_category = st.sidebar.text_input("Nome da Categoria")
    if st.sidebar.button("Adicionar Categoria"):
        if new_category:
            add_category(new_category)
            st.sidebar.success(f"Categoria '{new_category}' adicionada!")
        else:
            st.sidebar.error("O nome da categoria não pode ser vazio.")
    
    category_name = st.sidebar.selectbox("Selecione a Categoria para Adicionar Competidor", [row[0] for row in get_results("SELECT name FROM categories")])
    new_competitor = st.sidebar.text_input("Nome do Competidor")
    if st.sidebar.button("Adicionar Competidor"):
        if new_competitor and category_name:
            category_id = [row[0] for row in get_results("SELECT id FROM categories WHERE name = %s", (category_name,))][0]
            add_competitor(new_competitor, category_id)
            st.sidebar.success(f"Competidor '{new_competitor}' adicionado à categoria '{category_name}'!")
        else:
            st.sidebar.error("Todos os campos devem ser preenchidos.")

elif action == "Remover":
    st.sidebar.subheader("Remover Categoria")
    remove_category_name = st.sidebar.selectbox("Selecione a Categoria para Remover", [row[0] for row in get_results("SELECT name FROM categories")])
    if st.sidebar.button("Remover Categoria"):
        remove_category(remove_category_name)
        st.sidebar.success(f"Categoria '{remove_category_name}' removida!")
    
    remove_competitor_name = st.sidebar.selectbox("Selecione o Competidor para Remover", [row[0] for row in get_results("SELECT name FROM competitors")])
    if st.sidebar.button("Remover Competidor"):
        remove_competitor(remove_competitor_name)
        st.sidebar.success(f"Competidor '{remove_competitor_name}' removido!")

elif action == "Resultados":
    st.sidebar.subheader("Resultados")
    categories = [row[0] for row in get_results("SELECT name FROM categories")]
    selected_category = st.sidebar.selectbox("Selecione uma Categoria", categories)
    if selected_category:
        results = get_results("""
            SELECT c.name, COUNT(v.id) AS votes
            FROM competitors c
            LEFT JOIN votes v ON c.id = v.competitor_id
            JOIN categories cat ON c.category_id = cat.id
            WHERE cat.name = %s
            GROUP BY c.name
            ORDER BY votes DESC
        """, (selected_category,))
        if results:
            st.subheader(f"Resultados - {selected_category}")
            results_df = pd.DataFrame(results, columns=["Competidor", "Votos"])
            chart = alt.Chart(results_df).mark_bar().encode(
                x=alt.X('Competidor', sort='-y'),
                y='Votos',
                color='Competidor',
                tooltip=['Competidor', 'Votos']
            ).interactive()
            st.altair_chart(chart, use_container_width=True)

            # Vencedor
            winner = results[0]
            st.markdown(f"### 🏆 **Vencedor**: {winner[0]} com {winner[1]} votos!")
            st.markdown(f"<div class='winner-box'><img src='https://upload.wikimedia.org/wikipedia/commons/thumb/5/52/Trophy-icon.png/600px-Trophy-icon.png' alt='Trophy'/>{winner[0]}</div>", unsafe_allow_html=True)
        else:
            st.info("Sem resultados disponíveis para esta categoria.")
