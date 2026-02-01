import streamlit as st
import pandas as pd
import datetime
import time 
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

st.set_page_config(page_title="Esmalteria Borges", layout="centered")

# --- LOGIN ---
st.title("Esmalteria Borges")
cookie_manager = stx.CookieManager(key="gerente_cookies")
cookie_acesso = cookie_manager.get(cookie="acesso_esmalteria")

if "logado_agora" not in st.session_state:
    st.session_state["logado_agora"] = False

if cookie_acesso != "liberado" and not st.session_state["logado_agora"]:
    st.markdown("### 🔒 Área Restrita")
    senha_digitada = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if senha_digitada == "lb":
            st.session_state["logado_agora"] = True
            cookie_manager.set("acesso_esmalteria", "liberado", expires_at=datetime.datetime.now() + timedelta(days=7))
            st.rerun()
        else:
            st.error("Senha incorreta!")
    st.stop() 

# --- CONEXÃO ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO QUE FORÇA A LEITURA POR POSIÇÃO (A, B, C, D) ---
def carregar_dados_posicao(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        
        if df.empty:
            return pd.DataFrame()
        
        # --- AQUI ESTÁ A CORREÇÃO DEFINITIVA ---
        # Se for a aba de ENTRADAS, pegamos as colunas A, B, C, D
        if aba == "Entradas":
            # Seleciona apenas as primeiras 4 colunas (0, 1, 2, 3)
            df = df.iloc[:, :4] 
            # Renomeia na marra: A=Data, B=Cliente, C=Serviço, D=Valor
            df.columns = ["Data", "Cliente", "Serviço", "Valor"]
            
        # Se for a aba de SAÍDAS, pegamos A, B, C
        elif aba == "Saidas":
            df = df.iloc[:, :3]
            df.columns = ["Data", "Descrição", "Valor"]

        # --- TRATAMENTOS DE SEGURANÇA ---
        # 1. Limpa linhas vazias (onde a Data está vazia)
        df = df.dropna(subset=["Data"])
        
        # 2. Converte Data
        df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
        df["Data_Dt"] = df["Data"].dt.date
        
        # 3. Converte Valor (Trata texto com vírgula ou número)
        def limpar_valor(v):
            if isinstance(v, (int, float)): return float(v)
            if isinstance(v, str): 
                return float(v.replace("R$", "").replace(" ", "").replace(",", "."))
            return 0.0
            
        df["Valor_Calc"] = df["Valor"].apply(limpar_valor)
        
        return df
    except Exception as e:
        st.error(f"Erro ao ler {aba}: {e}")
        return pd.DataFrame()

def salvar_novo(aba, lista_dados):
    # Salva sempre como string/float simples para não quebrar a planilha
    df_novo = pd.DataFrame([lista_dados])
    df_antigo = conn.read(worksheet=aba, ttl=0)
    # Garante nomes das colunas para concatenar certo
    if aba == "Entradas":
        df_novo.columns = ["Data", "Cliente", "Serviço", "Valor"]
        # Se o antigo não tiver cabeçalho certo, ignoramos, pois o append é no fim
    elif aba == "Saidas":
        df_novo.columns = ["Data", "Descrição", "Valor"]
        
    df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
    conn.update(worksheet=aba, data=df_final)

def excluir_linha(aba, index):
    df = conn.read(worksheet=aba, ttl=0)
    df = df.drop(index)
    conn.update(worksheet=aba, data=df)
    st.rerun()

# --- INTERFACE ---
aba1, aba2, aba3, aba4 = st.tabs(["Entradas", "Saídas", "Diário", "Mensal"])
data_hoje = date.today()

# 1. ENTRADAS
with aba1:
    st.header("Entradas (A, B, C, D)")
    data_sel = st.date_input("Data:", data_hoje)
    
    df = carregar_dados_posicao("Entradas")
    
    # Exibe dados do dia
    if not df.empty:
        dia = df[df["Data_Dt"] == data_sel]
        if not dia.empty:
            for i, row in dia.iterrows():
                # Layout: A | B | C | D
                c1, c2, c3, c4, c5 = st.columns([2,3,3,2,1])
                c1.write(row["Data"].strftime("%d/%m") if pd.notnull(row["Data"]) else "-")
                c2.write(row["Cliente"])
                c3.write(row["Serviço"])
                c4.write(f"R$ {row['Valor_Calc']:.2f}")
                if c5.button("🗑️", key=f"e_{i}"): excluir_linha("Entradas", i)
    
    st.divider()
    with st.form("nova_entrada"):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente (B)")
        serv = c2.text_input("Serviço (C)")
        val = st.number_input("Valor (D)", step=0.01)
        if st.form_submit_button("Salvar"):
            # Salva na ordem exata: A, B, C, D
            salvar_novo("Entradas", [str(data_sel), cli, serv, val])
            st.success("Salvo!")
            time.sleep(1)
            st.rerun()

# 2. SAÍDAS
with aba2:
    st.header("Saídas")
    data_s = st.date_input("Data Saída:", data_hoje)
    df_s = carregar_dados_posicao("Saidas")
    
    if not df_s.empty:
        dia_s = df_s[df_s["Data_Dt"] == data_s]
        for i, row in dia_s.iterrows():
            c1, c2, c3, c4 = st.columns([2,4,2,1])
            c1.write(row["Data"].strftime("%d/%m") if pd.notnull(row["Data"]) else "-")
            c2.write(row["Descrição"])
            c3.write(f"R$ {row['Valor_Calc']:.2f}")
            if c4.button("🗑️", key=f"s_{i}"): excluir_linha("Saidas", i)
            
    st.divider()
    with st.form("nova_saida"):
        desc = st.text_input("Descrição")
        val_s = st.number_input("Valor", step=0.01)
        if st.form_submit_button("Salvar"):
            salvar_novo("Saidas", [str(data_s), desc, val_s])
            st.success("Salvo!")
            time.sleep(1)
            st.rerun()

# 3. DIÁRIO
with aba3:
    st.header("Fechamento Diário")
    dia_analise = st.date_input("Dia:", data_hoje, key="analise")
    
    df_e = carregar_dados_posicao("Entradas")
    df_s = carregar_dados_posicao("Saidas")
    
    tot_e = 0.0
    tot_s = 0.0
    
    if not df_e.empty: 
        tot_e = df_e[df_e["Data_Dt"] == dia_analise]["Valor_Calc"].sum()
    if not df_s.empty:
        tot_s = df_s[df_s["Data_Dt"] == dia_analise]["Valor_Calc"].sum()
        
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrada", f"R$ {tot_e:.2f}")
    c2.metric("Saída", f"R$ {tot_s:.2f}")
    c3.metric("Lucro", f"R$ {tot_e - tot_s:.2f}")

# 4. MENSAL
with aba4:
    st.header("Mensal")
    df_e = carregar_dados_posicao("Entradas")
    df_s = carregar_dados_posicao("Saidas")
    
    # Soma simples de tudo que for do mês atual
    mes = data_hoje.month
    
    t_mes_e = 0.0
    if not df_e.empty:
        t_mes_e = df_e[df_e["Data"].dt.month == mes]["Valor_Calc"].sum()
        
    t_mes_s = 0.0
    if not df_s.empty:
        t_mes_s = df_s[df_s["Data"].dt.month == mes]["Valor_Calc"].sum()
        
    st.metric("Lucro Mês", f"R$ {t_mes_e - t_mes_s:.2f}")
