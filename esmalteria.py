import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# --- Configuração da Página ---
st.set_page_config(page_title="Esmalteria Borges", layout="centered")
st.title("💅 Esmalteria Borges - Financeiro")

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
aba_entradas, aba_saidas, aba_resumo = st.tabs(["💰 Entradas", "💸 Saídas", "📊 Resumo Financeiro"])

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
            # AQUI: value=None deixa o campo vazio
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=None, placeholder="0.00")
            
        bt_salvar = st.form_submit_button("Salvar Entrada")
        
        if bt_salvar:
            # Verifica se valor_entrada não é None e se é maior que 0
            if cliente and valor_entrada and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_reg),
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada
                }])
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} registrado com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha o nome e o valor corretamente.")

    st.divider()
    
    # Lista de Hoje
    st.markdown(f"### 📋 Atendimentos do Dia: {data_hoje.strftime('%d/%m/%Y')}")
    
    df_entradas = carregar_dados("Entradas")
    
    if not df_entradas.empty:
        df_entradas["Data_Dt"] = pd.to_datetime(df_entradas["Data"]).dt.date
        filtro_dia = df_entradas[df_entradas["Data_Dt"] == data_hoje]
        
        if filtro_dia.empty:
            st.info("Nenhum atendimento registrado hoje.")
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
            c1.markdown("**Data**")
            c2.markdown("**Cliente**")
            c3.markdown("**Serviço**")
            c4.markdown("**Valor**")
            c5.markdown("**Ação**")
            st.markdown("---")

            for index, row in filtro_dia.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
                c1.write(pd.to_datetime(row["Data"]).strftime('%d/%m'))
                c2.write(row["Cliente"])
                c3.write(row["Serviço"])
                c4.write(f"R$ {float(row['Valor']):.2f}")
                
                if c5.button("🗑️", key=f"btn_del_ent_{index}"):
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
            # AQUI: value=None deixa o campo vazio
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f", value=None, placeholder="0.00")
            
        bt_salvar_saida = st.form_submit_button("Salvar Saída")
        
        if bt_salvar_saida:
            # Verifica se valor_saida não é None e se é maior que 0
            if descricao and valor_saida and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_gasto),
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                salvar_registro("Saidas", novo_df)
                st.success(f"✅ Gasto com '{descricao}' registrado!")
                st.rerun()
            else:
                st.warning("Preencha a descrição e o valor.")
    
    st.divider()

    # Lista de Hoje
    st.markdown(f"### 📉 Despesas do Dia: {data_hoje.strftime('%d/%m/%Y')}")
    
    df_saidas = carregar_dados("Saidas")
    
    if not df_saidas.empty:
        df_saidas["Data_Dt"] = pd.to_datetime(df_saidas["Data"]).dt.date
        filtro_dia_saida = df_saidas[df_saidas["Data_Dt"] == data_hoje]
        
        if filtro_dia_saida.empty:
            st.info("Nenhuma despesa registrada hoje.")
        else:
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            c1.markdown("**Data**")
            c2.markdown("**Descrição**")
            c3.markdown("**Valor**")
            c4.markdown("**Ação**")
            st.markdown("---")

            for index, row in filtro_dia_saida.iterrows():
                c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
                c1.write(pd.to_datetime(row["Data"]).strftime('%d/%m'))
                c2.write(row["Descrição"])
                c3.write(f"R$ {float(row['Valor']):.2f}")
                
                if c4.button("🗑️", key=f"btn_del_sai_{index}"):
                    excluir_registro("Saidas", index)

# ================= ABA 3: RESUMO =================
with aba_resumo:
    st.subheader("Balanço Financeiro")
    
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    if not df_e.empty:
        df_e["Data"] = pd.to_datetime(df_e["Data"]).dt.date
        df_e["Valor"] = pd.to_numeric(df_e["Valor"])
    
    if not df_s.empty:
        df_s["Data"] = pd.to_datetime(df_s["Data"]).dt.date
        df_s["Valor"] = pd.to_numeric(df_s["Valor"])

    # --- Cálculos do Dia ---
    st.markdown(f"### 📅 Resultado de Hoje: {data_hoje.strftime('%d/%m/%Y')}")
    
    soma_entrada_dia = 0.0
    soma_saida_dia = 0.0
    
    if not df_e.empty:
        soma_entrada_dia = df_e[df_e["Data"] == data_hoje]["Valor"].sum()
    
    if not df_s.empty:
        soma_saida_dia = df_s[df_s["Data"] == data_hoje]["Valor"].sum()
        
    lucro_dia = soma_entrada_dia - soma_saida_dia
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrou (Hoje)", f"R$ {soma_entrada_dia:.2f}")
    c2.metric("Saiu (Hoje)", f"R$ {soma_saida_dia:.2f}")
    c3.metric("Lucro (Hoje)", f"R$ {lucro_dia:.2f}", delta=lucro_dia)
    
    st.divider()

    # --- Cálculos do Mês ---
    mes_atual = data_hoje.month
    ano_atual = data_hoje.year
    
    st.markdown(f"### 🗓️ Resultado do Mês Atual: {data_hoje.strftime('%B/%Y')}")

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
