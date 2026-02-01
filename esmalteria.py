import streamlit as st
import pandas as pd
import datetime
import time 
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

# --- Configuração da Página ---
st.set_page_config(page_title="Esmalteria Borges", layout="centered")

# ================= SISTEMA DE LOGIN ROBUSTO =================
st.title("Esmalteria Borges")

# 1. Carrega o gerenciador de cookies
cookie_manager = stx.CookieManager(key="gerente_cookies")

# 2. Tenta ler o cookie
cookie_acesso = cookie_manager.get(cookie="acesso_esmalteria")

# 3. Verifica login na sessão
if "logado_agora" not in st.session_state:
    st.session_state["logado_agora"] = False

# LÓGICA DE BLOQUEIO
if cookie_acesso != "liberado" and not st.session_state["logado_agora"]:
    
    st.markdown("### 🔒 Área Restrita")
    senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
    
    if st.button("Entrar"):
        if senha_digitada == "lb":
            st.session_state["logado_agora"] = True
            
            data_vencimento = datetime.datetime.now() + timedelta(days=7)
            cookie_manager.set("acesso_esmalteria", "liberado", expires_at=data_vencimento)
            
            st.success("Senha correta! Acedendo ao sistema...")
            time.sleep(1.5)
            st.rerun()
        else:
            st.error("Senha incorreta!")
    
    st.stop() 

# ================= FIM DO LOGIN / INÍCIO DO APP =================

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

# --- Funções de Dados (INTOCADAS) ---
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

# --- Interface Principal ---
st.markdown("### 📊 Painel Financeiro")

# === ALTERAÇÃO: DATA GLOBAL FORA DAS ABAS ===
st.info("📅 Selecione a data abaixo para FILTRAR ou REGISTRAR:")
data_selecionada = st.date_input("Data de Referência", date.today())

st.divider()

aba_entradas, aba_saidas, aba_resumo = st.tabs(["💰 Entradas", "💸 Saídas", "📊 Resultado Diário"])

# ================= ABA 1: ENTRADAS =================
with aba_entradas:
    st.subheader("Registrar Atendimento")
    st.caption(f"Registrando para o dia: **{data_selecionada.strftime('%d/%m/%Y')}**")
    
    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            # Removemos a data daqui, usaremos a data_selecionada
            cliente = st.text_input("Cliente")
        with col2:
            servico = st.text_input("Serviço")
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=None, placeholder="0.00")
            
        bt_salvar = st.form_submit_button("Salvar Entrada")
        
        if bt_salvar:
            if cliente and valor_entrada and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_selecionada), # Usa a data global
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada
                }])
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} registrado em {data_selecionada.strftime('%d/%m')}!")
                st.rerun()
            else:
                st.warning("Preencha o nome e o valor.")

    st.divider()
    
    # Filtro visual para a data selecionada
    st.markdown(f"### 📋 Lista de: {data_selecionada.strftime('%d/%m/%Y')}")
    df_entradas = carregar_dados("Entradas")
    
    if not df_entradas.empty:
        df_entradas["Data_Dt"] = pd.to_datetime(df_entradas["Data"]).dt.date
        filtro_dia = df_entradas[df_entradas["Data_Dt"] == data_selecionada]
        
        if filtro_dia.empty:
            st.info(f"Nenhuma entrada registrada para {data_selecionada.strftime('%d/%m')}.")
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
    st.caption(f"Registrando para o dia: **{data_selecionada.strftime('%d/%m/%Y')}**")
    
    with st.form("form_saida", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            # Removemos a data daqui também
            descricao = st.text_input("Descrição")
        with col2:
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=None, placeholder="0.00")
            
        bt_salvar_saida = st.form_submit_button("Salvar Saída")
        
        if bt_salvar_saida:
            if descricao and valor_saida and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_selecionada), # Usa a data global
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                salvar_registro("Saidas", novo_df)
                st.success("✅ Saída registrada!")
                st.rerun()
            else:
                st.warning("Preencha descrição e valor.")
    
    st.divider()

    st.markdown(f"### 📉 Lista de: {data_selecionada.strftime('%d/%m/%Y')}")
    df_saidas = carregar_dados("Saidas")
    
    if not df_saidas.empty:
        df_saidas["Data_Dt"] = pd.to_datetime(df_saidas["Data"]).dt.date
        filtro_dia_saida = df_saidas[df_saidas["Data_Dt"] == data_selecionada]
        
        if filtro_dia_saida.empty:
            st.info(f"Nenhuma saída registrada para {data_selecionada.strftime('%d/%m')}.")
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

# ================= ABA 3: RESULTADO DIÁRIO =================
with aba_resumo:
    st.subheader("Balanço do Dia")
    
    # Carrega dados globais
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    # Converte colunas
    if not df_e.empty:
        df_e["Data"] = pd.to_datetime(df_e["Data"]).dt.date
        df_e["Valor"] = pd.to_numeric(df_e["Valor"])
    if not df_s.empty:
        df_s["Data"] = pd.to_datetime(df_s["Data"]).dt.date
        df_s["Valor"] = pd.to_numeric(df_s["Valor"])

    # --- CÁLCULOS BASEADOS NA DATA SELECIONADA ---
    st.markdown(f"Resumo referente a: **{data_selecionada.strftime('%d/%m/%Y')}**")
    
    # Filtra Entrada pelo dia selecionado
    soma_e_dia = 0.0
    if not df_e.empty:
        soma_e_dia = df_e[df_e["Data"] == data_selecionada]["Valor"].sum()
        
    # Filtra Saída pelo dia selecionado
    soma_s_dia = 0.0
    if not df_s.empty:
        soma_s_dia = df_s[df_s["Data"] == data_selecionada]["Valor"].sum()
        
    lucro_dia = soma_e_dia - soma_s_dia
    
    # Métricas do Dia
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Entradas", f"R$ {soma_e_dia:.2f}")
    col_b.metric("Total Saídas", f"R$ {soma_s_dia:.2f}")
    col_c.metric("Lucro Líquido", f"R$ {lucro_dia:.2f}", delta=lucro_dia)
    
    st.divider()

    # --- CÁLCULOS DO MÊS (Baseado no mês da data selecionada) ---
    mes_ref = data_selecionada.month
    ano_ref = data_selecionada.year
    nomes_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    
    st.markdown(f"### 🗓️ Acumulado do Mês: {nomes_meses[mes_ref]}/{ano_ref}")
    
    soma_e_mes = 0.0
    soma_s_mes = 0.0
    
    if not df_e.empty:
        mask_e = (pd.to_datetime(df_e["Data"]).dt.month == mes_ref) & (pd.to_datetime(df_e["Data"]).dt.year == ano_ref)
        soma_e_mes = df_e[mask_e]["Valor"].sum()
        
    if not df_s.empty:
        mask_s = (pd.to_datetime(df_s["Data"]).dt.month == mes_ref) & (pd.to_datetime(df_s["Data"]).dt.year == ano_ref)
        soma_s_mes = df_s[mask_s]["Valor"].sum()
        
    lucro_mes = soma_e_mes - soma_s_mes

    c4, c5, c6 = st.columns(3)
    c4.metric(f"Entradas ({nomes_meses[mes_ref]})", f"R$ {soma_e_mes:.2f}")
    c5.metric(f"Saídas ({nomes_meses[mes_ref]})", f"R$ {soma_s_mes:.2f}")
    c6.metric(f"Lucro ({nomes_meses[mes_ref]})", f"R$ {lucro_mes:.2f}", delta=lucro_mes)
