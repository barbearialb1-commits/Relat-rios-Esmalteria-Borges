import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- Configuração da Página ---
st.set_page_config(page_title="Esmalteria Borges", layout="centered")
st.title("💅 Esmalteria Borges - Financeiro")

# --- Conexão com Google Sheets ---
# O arquivo secrets.toml deve estar configurado corretamente
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Funções de Carregamento e Salvamento ---
def carregar_dados(aba):
    # ttl=0 garante que não pega dados velhos do cache
    try:
        df = conn.read(worksheet=aba, ttl=0)
        # Se vier vazio ou com problemas, forçamos as colunas certas
        if df.empty:
             return pd.DataFrame()
        return df
    except:
        return pd.DataFrame()

def salvar_registro(aba, novo_dado_df):
    # 1. Carrega o que já existe
    df_existente = carregar_dados(aba)
    # 2. Junta o antigo com o novo
    df_atualizado = pd.concat([df_existente, novo_dado_df], ignore_index=True)
    # 3. Reescreve na planilha
    conn.update(worksheet=aba, data=df_atualizado)

# --- Interface Principal ---
st.sidebar.header("Filtros")
data_selecionada = st.sidebar.date_input("Data de referência:", date.today())

aba_entradas, aba_saidas, aba_resumo = st.tabs(["💰 Entradas", "💸 Saídas", "📊 Resumo Financeiro"])

# ================= ABA 1: ENTRADAS =================
with aba_entradas:
    st.subheader("Registrar Atendimento")
    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_reg = st.date_input("Data", date.today())
            cliente = st.text_input("Cliente")
        with col2:
            servico = st.text_input("Serviço")
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar = st.form_submit_button("Salvar Entrada")
        
        if bt_salvar:
            if cliente and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_reg),
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada
                }])
                # AQUI: Mudado para "Entradas" (Maiúsculo)
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} registrado com sucesso!")
            else:
                st.warning("Preencha o nome e o valor.")

    st.divider()
    # Visualização rápida
    if st.checkbox("Ver últimos registros de Entrada"):
        # AQUI: Mudado para "Entradas" (Maiúsculo)
        df_entradas = carregar_dados("Entradas")
        st.dataframe(df_entradas.tail(5))

# ================= ABA 2: SAÍDAS =================
with aba_saidas:
    st.subheader("Registrar Despesa")
    with st.form("form_saida", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_gasto = st.date_input("Data", date.today())
            descricao = st.text_input("Descrição")
        with col2:
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar_saida = st.form_submit_button("Salvar Saída")
        
        if bt_salvar_saida:
            if descricao and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_gasto),
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                # AQUI: Mudado para "Saidas" (Maiúsculo e sem acento, conforme planilha)
                salvar_registro("Saidas", novo_df)
                st.success(f"✅ Gasto com '{descricao}' registrado!")
            else:
                st.warning("Preencha a descrição e o valor.")

# ================= ABA 3: RESUMO =================
with aba_resumo:
    st.subheader("Balanço Financeiro")
    
    # Carregar dados atualizados usando os nomes com Maiúscula
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    # Tratamento de erro caso a planilha esteja vazia
    if not df_e.empty:
        df_e["Data"] = pd.to_datetime(df_e["Data"]).dt.date
        df_e["Valor"] = pd.to_numeric(df_e["Valor"])
    
    if not df_s.empty:
        df_s["Data"] = pd.to_datetime(df_s["Data"]).dt.date
        df_s["Valor"] = pd.to_numeric(df_s["Valor"])

    # --- CÁLCULOS DO DIA ---
    st.markdown(f"### 📅 Resultado do Dia: {data_selecionada.strftime('%d/%m/%Y')}")
    
    # Filtros do dia
    soma_entrada_dia = 0.0
    soma_saida_dia = 0.0
    
    if not df_e.empty:
        soma_entrada_dia = df_e[df_e["Data"] == data_selecionada]["Valor"].sum()
    
    if not df_s.empty:
        soma_saida_dia = df_s[df_s["Data"] == data_selecionada]["Valor"].sum()
        
    lucro_dia = soma_entrada_dia - soma_saida_dia
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrou (Dia)", f"R$ {soma_entrada_dia:.2f}")
    c2.metric("Saiu (Dia)", f"R$ {soma_saida_dia:.2f}")
    c3.metric("Lucro Líquido (Dia)", f"R$ {lucro_dia:.2f}", delta=lucro_dia)
    
    st.divider()

    # --- CÁLCULOS DO MÊS ---
    mes_atual = data_selecionada.month
    ano_atual = data_selecionada.year
    
    st.markdown(f"### 🗓️ Resultado Mensal: {data_selecionada.strftime('%B/%Y')}")

    soma_entrada_mes = 0.0
    soma_saida_mes = 0.0

    if not df_e.empty:
        mask_mes_e = (pd.to_datetime(df_e["Data"]).dt.month == mes_atual) & (pd.to_datetime(df_e["Data"]).dt.year == ano_atual)
        soma_entrada_mes = df_e[mask_mes_e]["Valor"].sum()

    if not df_s.empty:
        mask_mes_s = (pd.to_datetime(df_s["Data"]).dt.month == mes_atual) & (pd.to_datetime(df_s["Data"]).dt.year == ano_atual)
        soma_saida_mes = df_s[mask_mes_s]["Valor"].sum()

    lucro_mes = soma_entrada_mes - soma_saida_mes

    c4, c5, c6 = st.columns(3)
    c4.metric("Entrou (Mês)", f"R$ {soma_entrada_mes:.2f}")
    c5.metric("Saiu (Mês)", f"R$ {soma_saida_mes:.2f}")
    c6.metric("Lucro Líquido (Mês)", f"R$ {lucro_mes:.2f}", delta=lucro_mes, delta_color="normal")
