import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ERP Nexus PRO", layout="wide", page_icon="🚀")

# --- CONEXÃO COM POSTGRESQL ---
# Certifique-se de configurar a URL no arquivo .streamlit/secrets.toml
conn = st.connection("postgresql", type="sql")

# --- FUNÇÕES DE BANCO DE DADOS (DATABASE LAYER) ---
def init_db():
    """Inicializa as tabelas no PostgreSQL"""
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS produtos (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                preco_custo DECIMAL(10,2),
                preco_venda DECIMAL(10,2),
                estoque INTEGER DEFAULT 0
            );
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id SERIAL PRIMARY KEY,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                produto_id TEXT REFERENCES produtos(id),
                tipo TEXT,
                quantidade INTEGER,
                valor_total DECIMAL(10,2)
            );
        """))
        session.commit()

def get_produtos():
    return conn.query("SELECT * FROM produtos ORDER BY nome", ttl=0)

def get_movimentacoes():
    return conn.query("SELECT * FROM movimentacoes ORDER BY data DESC", ttl=0)

# --- LÓGICA DE NEGÓCIO ---
def adicionar_produto_db(id_p, nome, custo, venda):
    try:
        with conn.session as s:
            s.execute(text("INSERT INTO produtos (id, nome, preco_custo, preco_venda, estoque) VALUES (:id, :n, :c, :v, 0)"),
                      {"id": id_p, "n": nome, "c": custo, "v": venda})
            s.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao cadastrar: ID já existe ou erro na conexão.")
        return False

def registrar_movimentacao(id_p, tipo, qtd):
    df_prods = get_produtos()
    prod = df_prods[df_prods['id'] == id_p].iloc[0]
    
    estoque_atual = prod['estoque']
    valor_un = prod['preco_custo'] if tipo == "Compra" else prod['preco_venda']
    
    if tipo == "Venda" and estoque_atual < qtd:
        st.error(f"Estoque insuficiente! Saldo: {estoque_atual}")
        return False

    novo_estoque = (estoque_atual + qtd) if tipo == "Compra" else (estoque_atual - qtd)
    valor_total = float(qtd * valor_un)

    with conn.session as s:
        # Atualiza estoque do produto
        s.execute(text("UPDATE produtos SET estoque = :est WHERE id = :id"), {"est": novo_estoque, "id": id_p})
        # Insere movimentação
        s.execute(text("INSERT INTO movimentacoes (produto_id, tipo, quantidade, valor_total) VALUES (:id, :t, :q, :v)"),
                  {"id": id_p, "t": tipo, "q": qtd, "v": valor_total})
        s.commit()
    return True

# --- INTERFACE DE USUÁRIO (UI) ---
def main():
    init_db()
    
    if 'logado' not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        tela_login()
    else:
        sidebar_menu()

def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Acesso Restrito - ERP Nexus")
        usuario = st.text_input("Usuário Administrador")
        senha = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            if usuario == "admin" and senha == "12345":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

def sidebar_menu():
    st.sidebar.title("🚀 ERP Nexus PRO")
    menu = st.sidebar.radio("Navegação", ["Dashboard", "📦 Estoque", "🛒 Compras", "💰 Vendas"])
    
    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()

    if menu == "Dashboard":
        render_dashboard()
    elif menu == "📦 Estoque":
        render_estoque()
    elif menu == "🛒 Compras":
        render_transacao("Compra")
    elif menu == "💰 Vendas":
        render_transacao("Venda")

def render_dashboard():
    st.title("📊 Painel de Controle")
    movs = get_movimentacoes()
    prods = get_produtos()
    
    if not movs.empty:
        faturamento = movs[movs['tipo'] == 'Venda']['valor_total'].sum()
        investimento = movs[movs['tipo'] == 'Compra']['valor_total'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", f"R$ {faturamento:,.2f}")
        m2.metric("Investimento", f"R$ {investimento:,.2f}")
        m3.metric("Saldo", f"R$ {(faturamento - investimento):,.2f}")
        
        fig = px.line(movs[movs['tipo'] == 'Venda'], x='data', y='valor_total', title="Histórico de Vendas")
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("⚠️ Alerta de Estoque Baixo")
    critico = prods[prods['estoque'] < 5]
    st.dataframe(critico[['nome', 'estoque']], use_container_width=True)

def render_estoque():
    st.title("Gestão de Produtos")
    tab1, tab2 = st.tabs(["Listagem", "Novo Cadastro"])
    
    with tab1:
        st.dataframe(get_produtos(), use_container_width=True)
        
    with tab2:
        with st.form("cadastro"):
            id_p = st.text_input("ID/SKU")
            nome = st.text_input("Nome")
            custo = st.number_input("Custo", min_value=0.0)
            venda = st.number_input("Venda", min_value=0.0)
            if st.form_submit_button("Salvar"):
                if adicionar_produto_db(id_p, nome, custo, venda):
                    st.success("Cadastrado!")
                    st.rerun()

def render_transacao(tipo):
    st.title(f"{tipo} de Mercadorias")
    prods = get_produtos()
    if prods.empty:
        st.warning("Cadastre produtos primeiro.")
        return

    with st.form(f"form_{tipo}"):
        escolha = st.selectbox("Produto", prods['id'].tolist(), 
                              format_func=lambda x: prods[prods['id']==x]['nome'].values[0])
        qtd = st.number_input("Quantidade", min_value=1)
        if st.form_submit_button("Confirmar"):
            if registrar_movimentacao(escolha, tipo, qtd):
                st.success("Registrado com sucesso!")
                if tipo == "Venda": st.balloons()
                st.rerun()

if __name__ == "__main__":
    main()