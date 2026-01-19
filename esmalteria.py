import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

# --- Configuração da Página ---
st.set_page_config(page_title="Esmalteria Borges", layout="centered")

# ================= SISTEMA DE LOGIN COM COOKIE (7 DIAS) =================
st.title("💅 Esmalteria Borges")

# Função para carregar o gerenciador de cookies
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# Tenta ler o cookie chamado 'acesso_esmalteria'
cookie_acesso = cookie_manager.get(cookie="acesso_esmalteria")

# Verifica: Se NÃO tem cookie válido, pede senha
if cookie_acesso != "liberado":
    st.markdown("### 🔒 Área Restrita")
    
    senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
    
    if st.button("Entrar"):
        if senha_digitada == "lb":
            # Se a senha estiver certa, cria o cookie que vence em 7 dias
            data_vencimento = datetime.datetime.now() + timedelta(days=7)
            cookie_manager.set("acesso_esmalteria", "liberado", expires_at=data_vencimento)
            
            # Recarrega a página para validar o acesso
            st.rerun()
        else:
            st.error("Senha incorreta!")
    
    # Para o código aqui se não estiver logado
    st.stop()

# ================= FIM DO BLOCO DE LOGIN =================

# --- CSS para visual de App ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Conexão com Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Funções de Dados ---
def carregar_dados(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df.empty:
             return pd.DataFrame()
        return df
    except:
        return pd.DataFrame()

def salvar_registro(aba, novo_dado_df):
    df_existente = carregar_dados(aba)
    df_atualizado = pd.concat([df_existente, novo_dado_df], ignore_index=True)
    conn.update(worksheet=aba, data=df_atualizado)

def excluir_registro(aba, indice_para_deletar):
    df = carregar_dados(aba)
    df_novo = df.drop(indice_para_deletar, axis=0)
    conn.update(worksheet=aba, data=df_novo)
    st.success("Item removido com sucesso!")
    st.rerun()

# --- Definição da Data Atual ---
data_hoje = date.today()

# --- Interface Principal ---
st.markdown("### 📊 Painel Financeiro")
aba_entradas, aba_saidas, aba_resumo = st.tabs(["💰 Entradas", "💸 Saídas", "📊 Resumo"])

# ================= ABA 1: ENTRADAS =================
with aba_entradas:
    st.subheader("Registrar Atendimento")
    
    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_reg = st.date_input("Data", data_hoje)
            cliente = st.text_input("Cliente")
        with col2:
            servico = st.text_input("Serviço")
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=None, placeholder="0.00")
            
        bt_salvar = st.form_submit_button("Salvar Entrada")
        
        if bt_salvar:
            if cliente and valor_entrada and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_reg),
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada
                }])
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} registrado!")
                st.rerun()
            else:
                st.warning("Preencha o nome e o valor.")

    st.divider()
    
    st.markdown(f"### 📋 Hoje: {data_hoje.strftime('%d/%m')}")
    df_entradas = carregar_dados("Entradas")
    
    if not df_entradas.empty:
        df_entradas["Data_Dt"] = pd.to_datetime(df_entradas["Data"]).dt.date
        filtro_dia = df_entradas[df_entradas["Data_Dt"] == data_hoje]
        
        if filtro_dia.empty:
            st.info("Nada registrado hoje.")
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
            c1.markdown("**Data**")
            c2.markdown("**Nome**")
            c3.markdown("**Serviço**")
            c4.markdown("**Valor**")
            st.markdown("---")

            for index, row in filtro_dia.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
                c1.write(pd.to_datetime(row["Data"]).strftime('%d/%m'))
                c2.write(row["Cliente"])
                c3.write(row["Serviço"])
                c4.write(f"R$ {float(row['Valor']):.2f}")
                if c5.button("🗑️", key=f"del_e_{index}"):
                    excluir_registro("Entradas", index)

# ================= ABA 2: SAÍDAS =================
with aba_saidas:
    st.subheader("Registrar Despesa")
    
    with st.form("form_saida", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_gasto = st.date_input("Data", data_hoje)
            descricao = st.text_input("Descrição")
        with col2:
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=None, placeholder="0.00")
            
        bt_salvar_saida = st.form_submit_button("Salvar Saída")
        
        if bt_salvar_saida:
            if descricao and valor_saida and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_gasto),
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                salvar_registro("Saidas", novo_df)
                st.success("✅ Saída registrada!")
                st.rerun()
            else:
                st.warning("Preencha descrição e valor.")
    
    st.divider()

    st.markdown(f"### 📉 Hoje: {data_hoje.strftime('%d/%m')}")
    df_saidas = carregar_dados("Saidas")
    
    if not df_saidas.empty:
        df_saidas["Data_Dt"] = pd.to_datetime(df_saidas["Data"]).dt.date
        filtro_dia_saida = df_saidas[df_saidas["Data_Dt"] == data_hoje]
        
        if filtro_dia_saida.empty:
            st.info("Nada registrado hoje.")
        else:
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            c1.markdown("**Data**")
            c2.markdown("**Descrição**")
            c3.markdown("**Valor**")
            st.markdown("---")

            for index, row in filtro_dia_saida.iterrows():
                c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
                c1.write(pd.to_datetime(row["Data"]).strftime('%d/%m'))
                c2.write(row["Descrição"])
                c3.write(f"R$ {float(row['Valor']):.2f}")
                if c4.button("🗑️", key=f"del_s_{index}"):
                    excluir_registro("Saidas", index)

# ================= ABA 3: RESUMO =================
with aba_resumo:
    st.subheader("Balanço")
    
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    if not df_e.empty:
        df_e["Data"] = pd.to_datetime(df_e["Data"]).dt.date
        df_e["Valor"] = pd.to_numeric(df_e["Valor"])
    if not df_s.empty:
        df_s["Data"] = pd.to_datetime(df_s["Data"]).dt.date
        df_s["Valor"] = pd.to_numeric(df_s["Valor"])

    # Cálculos Dia
    st.markdown(f"**Hoje:** {data_hoje.strftime('%d/%m')}")
    soma_e_dia = df_e[df_e["Data"] == data_hoje]["Valor"].sum() if not df_e.empty else 0.0
    soma_s_dia = df_s[df_s["Data"] == data_hoje]["Valor"].sum() if not df_s.empty else 0.0
    lucro_dia = soma_e_dia - soma_s_dia
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrou", f"R$ {soma_e_dia:.2f}")
    c2.metric("Saiu", f"R$ {soma_s_dia:.2f}")
    c3.metric("Lucro", f"R$ {lucro_dia:.2f}", delta=lucro_dia)
    
    st.divider()

    # Cálculos Mês
    mes_atual = data_hoje.month
    ano_atual = data_hoje.year
    nomes_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    
    st.markdown(f"**Mês:** {nomes_meses[mes_atual]}/{ano_atual}")
    
    soma_e_mes = 0.0
    soma_s_mes = 0.0
    
    if not df_e.empty:
        mask_e = (pd.to_datetime(df_e["Data"]).dt.month == mes_atual) & (pd.to_datetime(df_e["Data"]).dt.year == ano_atual)
        soma_e_mes = df_e[mask_e]["Valor"].sum()
        
    if not df_s.empty:
        mask_s = (pd.to_datetime(df_s["Data"]).dt.month == mes_atual) & (pd.to_datetime(df_s["Data"]).dt.year == ano_atual)
        soma_s_mes = df_s[mask_s]["Valor"].sum()
        
    lucro_mes = soma_e_mes - soma_s_mes

    c4, c5, c6 = st.columns(3)
    c4.metric("Entrou", f"R$ {soma_e_mes:.2f}")
    c5.metric("Saiu", f"R$ {soma_s_mes:.2f}")
    c6.metric("Lucro", f"R$ {lucro_mes:.2f}", delta=lucro_mes)
