import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ERP Nexus PRO", layout="wide", page_icon="🚀")

# --- SISTEMA DE AUTENTICAÇÃO ---
def tela_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Acesso Restrito - ERP Nexus")
        usuario = st.text_input("Usuário Administrador")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Acessar Sistema"):
            # Credenciais para teste: admin / 12345
            if usuario == "admin" and senha == "12345":
                st.session_state.logado = True
                st.success("Login realizado!")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

# --- INICIALIZAÇÃO DE DADOS (ESTADO DA SESSÃO) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if 'produtos' not in st.session_state:
    st.session_state.produtos = pd.DataFrame(columns=['ID', 'Nome', 'Preço Custo', 'Preço Venda', 'Estoque'])

if 'movimentacoes' not in st.session_state:
    st.session_state.movimentacoes = pd.DataFrame(columns=['Data', 'ID', 'Tipo', 'Quantidade', 'Valor Total'])

# --- LÓGICA DO SISTEMA ---
if not st.session_state.logado:
    tela_login()
else:
    # Funções de Negócio Core
    def adicionar_produto(id_p, nome, custo, venda):
        if id_p in st.session_state.produtos['ID'].values:
            st.error("Erro: Este ID já está cadastrado!")
            return False
        novo_p = pd.DataFrame([[id_p, nome, custo, venda, 0]], columns=st.session_state.produtos.columns)
        st.session_state.produtos = pd.concat([st.session_state.produtos, novo_p], ignore_index=True)
        return True

    def processar_estoque(id_p, tipo, qtd):
        idx = st.session_state.produtos.index[st.session_state.produtos['ID'] == id_p].tolist()[0]
        df_prod = st.session_state.produtos.iloc[idx]
        
        if tipo == "Venda" and df_prod['Estoque'] < qtd:
            st.error(f"Estoque insuficiente! Saldo atual: {df_prod['Estoque']}")
            return False

        # Atualização aritmética do estoque
        if tipo == "Compra":
            st.session_state.produtos.at[idx, 'Estoque'] += qtd
            valor_un = df_prod['Preço Custo']
        else:
            st.session_state.produtos.at[idx, 'Estoque'] -= qtd
            valor_un = df_prod['Preço Venda']
        
        # Registro histórico financeiro
        nova_mov = pd.DataFrame([{
            'Data': datetime.now(),
            'ID': id_p,
            'Tipo': tipo,
            'Quantidade': qtd,
            'Valor Total': float(qtd * valor_un)
        }])
        st.session_state.movimentacoes = pd.concat([st.session_state.movimentacoes, nova_mov], ignore_index=True)
        return True

    # --- MENU LATERAL (SIDEBAR) ---
    st.sidebar.title("🚀 ERP Nexus PRO")
    st.sidebar.write(f"Usuário: **Administrador**")
    
    menu = st.sidebar.radio("Navegação", ["Dashboard", "📦 Estoque & Cadastro", "🛒 Compras", "💰 Vendas"])
    
    if st.sidebar.button("🚪 Encerrar Sessão"):
        st.session_state.logado = False
        st.rerun()

    # --- MÓDULOS ---

    if menu == "Dashboard":
        st.title("📊 Painel de Controle")
        
        # Cálculos de Métricas
        faturamento = st.session_state.movimentacoes[st.session_state.movimentacoes['Tipo'] == 'Venda']['Valor Total'].sum()
        investimento = st.session_state.movimentacoes[st.session_state.movimentacoes['Tipo'] == 'Compra']['Valor Total'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento (Vendas)", f"R$ {faturamento:,.2f}")
        m2.metric("Investimento (Compras)", f"R$ {investimento:,.2f}")
        m3.metric("Saldo (Caixa)", f"R$ {(faturamento - investimento):,.2f}")

        # Visualização Gráfica
        st.markdown("---")
        col_graf, col_tab = st.columns([2, 1])
        
        with col_graf:
            if not st.session_state.movimentacoes.empty:
                vendas_df = st.session_state.movimentacoes[st.session_state.movimentacoes['Tipo'] == 'Venda']
                if not vendas_df.empty:
                    fig = px.bar(vendas_df, x='Data', y='Valor Total', title="Fluxo de Vendas", color_discrete_sequence=['#00CC96'])
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aguardando registros de vendas para gerar gráficos.")
            
        with col_tab:
            st.subheader("Estoque Crítico")
            # Filtra itens com pouco estoque (exemplo: menos de 5)
            critico = st.session_state.produtos[st.session_state.produtos['Estoque'] < 5]
            st.dataframe(critico[['Nome', 'Estoque']], use_container_width=True)

    elif menu == "📦 Estoque & Cadastro":
        st.title("Gestão de Produtos")
        
        tab1, tab2 = st.tabs(["Listagem Geral", "Cadastrar Novo"])
        
        with tab1:
            st.dataframe(st.session_state.produtos, use_container_width=True)
            if st.button("Excluir Produto Selecionado") and not st.session_state.produtos.empty:
                st.warning("Selecione o ID abaixo para remover.")
                id_del = st.selectbox("ID para remover", st.session_state.produtos['ID'].tolist())
                if st.button("Confirmar Remoção"):
                    st.session_state.produtos = st.session_state.produtos[st.session_state.produtos['ID'] != id_del]
                    st.rerun()

        with tab2:
            with st.form("form_cadastro"):
                c1, c2 = st.columns(2)
                id_p = c1.text_input("ID / SKU")
                nome = c2.text_input("Nome do Produto")
                custo = c1.number_input("Custo de Aquisição", min_value=0.0)
                venda = c2.number_input("Preço de Venda", min_value=0.0)
                if st.form_submit_button("Salvar"):
                    if id_p and nome:
                        if adicionar_produto(id_p, nome, custo, venda):
                            st.success(f"{nome} cadastrado com sucesso!")
                            st.rerun()

    elif menu == "🛒 Compras":
        st.title("🛒 Registro de Compras")
        st.write("Aumente seu estoque registrando a entrada de mercadorias.")
        
        if not st.session_state.produtos.empty:
            df = st.session_state.produtos
            with st.form("form_compra"):
                p_id = st.selectbox("Selecione o Produto", options=df['ID'].tolist(), 
                                   format_func=lambda x: f"{x} - {df.loc[df['ID']==x, 'Nome'].values[0]}")
                qtd = st.number_input("Quantidade Comprada", min_value=1)
                if st.form_submit_button("Registrar Entrada"):
                    if processar_estoque(p_id, "Compra", qtd):
                        st.success("Estoque atualizado!")
                        st.rerun()
        else:
            st.warning("Cadastre um produto antes de realizar compras.")

    elif menu == "💰 Vendas":
        st.title("💰 Ponto de Venda (PDV)")
        st.write("Realize vendas e baixe o estoque automaticamente.")
        
        if not st.session_state.produtos.empty:
            df = st.session_state.produtos
            with st.form("form_venda"):
                p_id = st.selectbox("Selecione o Produto", options=df['ID'].tolist(), 
                                   format_func=lambda x: f"{x} - {df.loc[df['ID']==x, 'Nome'].values[0]}")
                qtd = st.number_input("Quantidade Vendida", min_value=1)
                if st.form_submit_button("Concluir Venda"):
                    if processar_estoque(p_id, "Venda", qtd):
                        st.balloons()
                        st.success("Venda processada com sucesso!")
                        st.rerun()
        else:
            st.warning("Catálogo vazio. Cadastre produtos primeiro.")