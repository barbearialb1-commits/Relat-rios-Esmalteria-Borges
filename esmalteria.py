import streamlit as st
import pandas as pd
import datetime
import time 
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

# --- Configuração da Página ---
st.set_page_config(page_title="Esmalteria Borges", layout="centered")

# ================= SISTEMA DE LOGIN =================
st.title("Esmalteria Borges")

cookie_manager = stx.CookieManager(key="gerente_cookies")
cookie_acesso = cookie_manager.get(cookie="acesso_esmalteria")

if "logado_agora" not in st.session_state:
    st.session_state["logado_agora"] = False

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

# ================= FIM DO LOGIN =================

# --- CSS ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Conexão ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Funções de Dados (VOLTAMOS À ORIGINAL QUE FUNCIONAVA) ---
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
    if df_existente.empty:
        df_atualizado = novo_dado_df
    else:
        df_atualizado = pd.concat([df_existente, novo_dado_df], ignore_index=True)
    conn.update(worksheet=aba, data=df_atualizado)

def excluir_registro(aba, indice_para_deletar):
    df = carregar_dados(aba)
    df_novo = df.drop(indice_para_deletar, axis=0)
    conn.update(worksheet=aba, data=df_novo)
    st.success("Item removido com sucesso!")
    time.sleep(1)
    st.rerun()

# --- Função Auxiliar Segura para Valores (Lida com vírgula e ponto) ---
def converter_valor_br(valor):
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        # Se for texto, troca vírgula por ponto
        if isinstance(valor, str):
            valor_limpo = valor.replace("R$", "").replace(" ", "").replace(",", ".")
            return float(valor_limpo)
        return 0.0
    except:
        return 0.0

# --- Definição da Data Atual ---
data_hoje = date.today()

# --- Interface Principal ---
st.markdown("### 📊 Painel Financeiro")
aba_entradas, aba_saidas, aba_diario, aba_resumo = st.tabs(["💰 Entradas", "💸 Saídas", "📅 Resultado Diário", "📊 Balanço Mensal"])

# ================= ABA 1: ENTRADAS =================
with aba_entradas:
    st.subheader("Registrar Atendimento")
    
    # 1. DATA FORA DO FORMULÁRIO (Para ver agenda antes)
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        data_selecionada = st.date_input("Selecionar Data", data_hoje)

    st.markdown("---")

    # 2. MOSTRA O QUE JÁ TEM NO DIA
    st.markdown(f"**Agenda de: {data_selecionada.strftime('%d/%m/%Y')}**")
    df_entradas = carregar_dados("Entradas")
    
    if not df_entradas.empty:
        # Cria coluna temporária para filtro (sem mexer no original)
        df_entradas["Data_Temp"] = pd.to_datetime(df_entradas["Data"], errors='coerce').dt.date
        filtro_dia = df_entradas[df_entradas["Data_Temp"] == data_selecionada]
        
        if filtro_dia.empty:
            st.info("Nada registrado nesta data.")
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
            c1.markdown("**Data**"); c2.markdown("**Nome**"); c3.markdown("**Serviço**"); c4.markdown("**Valor**")
            
            for index, row in filtro_dia.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
                c1.write(pd.to_datetime(row["Data"]).strftime('%d/%m'))
                c2.write(row["Cliente"])
                c3.write(row["Serviço"])
                val = converter_valor_br(row['Valor']) # Conversão segura
                c4.write(f"R$ {val:.2f}")
                if c5.button("🗑️", key=f"del_e_{index}"):
                    excluir_registro("Entradas", index)

    st.divider()

    # 3. FORMULÁRIO (Data fixa na selecionada acima)
    with st.form("form_entrada", clear_on_submit=True):
        st.write(f"Novo cadastro para: **{data_selecionada.strftime('%d/%m')}**")
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Cliente")
        with col2:
            servico = st.text_input("Serviço")
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar = st.form_submit_button("Salvar Entrada")
        
        if bt_salvar:
            if cliente and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_selecionada),
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada
                }])
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} registrado!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Preencha nome e valor.")

# ================= ABA 2: SAÍDAS =================
with aba_saidas:
    st.subheader("Registrar Despesa")
    
    # 1. DATA FORA DO FORMULÁRIO
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        data_sel_saida = st.date_input("Data da Despesa", data_hoje, key="data_saida_pick")

    st.markdown("---")
    
    # 2. MOSTRA O QUE JÁ TEM NO DIA
    st.markdown(f"**Despesas de: {data_sel_saida.strftime('%d/%m/%Y')}**")
    df_saidas = carregar_dados("Saidas")
    
    if not df_saidas.empty:
        df_saidas["Data_Temp"] = pd.to_datetime(df_saidas["Data"], errors='coerce').dt.date
        filtro_dia_s = df_saidas[df_saidas["Data_Temp"] == data_sel_saida]
        
        if filtro_dia_s.empty:
            st.info("Nada registrado nesta data.")
        else:
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            c1.markdown("**Data**"); c2.markdown("**Descrição**"); c3.markdown("**Valor**")
            
            for index, row in filtro_dia_s.iterrows():
                c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
                c1.write(pd.to_datetime(row["Data"]).strftime('%d/%m'))
                c2.write(row["Descrição"])
                val_s = converter_valor_br(row['Valor'])
                c3.write(f"R$ {val_s:.2f}")
                if c4.button("🗑️", key=f"del_s_{index}"):
                    excluir_registro("Saidas", index)

    st.divider()

    # 3. FORMULÁRIO
    with st.form("form_saida", clear_on_submit=True):
        st.write(f"Nova despesa para: **{data_sel_saida.strftime('%d/%m')}**")
        col1, col2 = st.columns(2)
        with col1:
            descricao = st.text_input("Descrição")
        with col2:
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar_saida = st.form_submit_button("Salvar Saída")
        
        if bt_salvar_saida:
            if descricao and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_sel_saida),
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                salvar_registro("Saidas", novo_df)
                st.success("✅ Saída registrada!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Preencha descrição e valor.")

# ================= ABA 3: RESULTADO DIÁRIO (NOVA) =================
with aba_diario:
    st.subheader("📆 Fechamento de Caixa Diário")
    
    # Filtro de Data
    col_f1, _ = st.columns([1, 2])
    with col_f1:
        dia_analise = st.date_input("Escolha o dia para analisar:", data_hoje, key="dia_analise")
        
    st.markdown("---")
    
    # Carrega dados
    df_e_raw = carregar_dados("Entradas")
    df_s_raw = carregar_dados("Saidas")
    
    total_ent = 0.0
    total_sai = 0.0
    
    # Processa Entradas
    if not df_e_raw.empty:
        # Cria cópia para não bugar cache
        df_e = df_e_raw.copy()
        df_e["Data_Dt"] = pd.to_datetime(df_e["Data"], errors='coerce').dt.date
        # Filtra dia
        filtro_e = df_e[df_e["Data_Dt"] == dia_analise].copy()
        # Converte valores com a função segura
        filtro_e["Valor_Num"] = filtro_e["Valor"].apply(converter_valor_br)
        total_ent = filtro_e["Valor_Num"].sum()
        
        # Mostra tabela se tiver dados
        if not filtro_e.empty:
            st.markdown("##### 📥 Entradas")
            st.dataframe(filtro_e[["Cliente", "Serviço", "Valor"]], hide_index=True)

    # Processa Saídas
    if not df_s_raw.empty:
        df_s = df_s_raw.copy()
        df_s["Data_Dt"] = pd.to_datetime(df_s["Data"], errors='coerce').dt.date
        filtro_s = df_s[df_s["Data_Dt"] == dia_analise].copy()
        filtro_s["Valor_Num"] = filtro_s["Valor"].apply(converter_valor_br)
        total_sai = filtro_s["Valor_Num"].sum()
        
        if not filtro_s.empty:
            st.markdown("##### 📤 Saídas")
            st.dataframe(filtro_s[["Descrição", "Valor"]], hide_index=True)

    st.divider()
    
    # Placar Final
    lucro = total_ent - total_sai
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Dia (Entrada)", f"R$ {total_ent:.2f}")
    c2.metric("Total Dia (Saída)", f"R$ {total_sai:.2f}")
    c3.metric("Lucro Líquido", f"R$ {lucro:.2f}", delta=lucro)


# ================= ABA 4: RESUMO (ORIGINAL MELHORADO) =================
with aba_resumo:
    st.subheader("Balanço Mensal")
    
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    mes_atual = data_hoje.month
    ano_atual = data_hoje.year
    nomes_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    
    st.markdown(f"**Referência:** {nomes_meses[mes_atual]}/{ano_atual}")
    
    val_e_mes = 0.0
    val_s_mes = 0.0
    
    if not df_e.empty:
        df_e["Data_Dt"] = pd.to_datetime(df_e["Data"], errors='coerce')
        mask_e = (df_e["Data_Dt"].dt.month == mes_atual) & (df_e["Data_Dt"].dt.year == ano_atual)
        # Aplica conversão segura antes de somar
        val_e_mes = df_e[mask_e]["Valor"].apply(converter_valor_br).sum()

    if not df_s.empty:
        df_s["Data_Dt"] = pd.to_datetime(df_s["Data"], errors='coerce')
        mask_s = (df_s["Data_Dt"].dt.month == mes_atual) & (df_s["Data_Dt"].dt.year == ano_atual)
        val_s_mes = df_s[mask_s]["Valor"].apply(converter_valor_br).sum()
        
    lucro_mes = val_e_mes - val_s_mes

    c4, c5, c6 = st.columns(3)
    c4.metric("Entrou", f"R$ {val_e_mes:.2f}")
    c5.metric("Saiu", f"R$ {val_s_mes:.2f}")
    c6.metric("Lucro", f"R$ {lucro_mes:.2f}", delta=lucro_mes)
