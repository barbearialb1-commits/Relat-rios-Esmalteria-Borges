import streamlit as st
import pandas as pd
import datetime
import time 
from datetime import date, timedelta
from streamlit_gsheets import GSheetsConnection
import extra_streamlit_components as stx

st.set_page_config(page_title="Esmalteria Borges", layout="centered")

# --- LOGIN (Mantido igual) ---
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

# --- FUNÇÃO QUE ARRUMA A BAGUNÇA DOS NÚMEROS ---
def limpar_dinheiro(valor):
    """
    Pega qualquer coisa que vier da planilha (texto com vírgula, número, vazio)
    e transforma num número que o Python consegue somar.
    """
    if pd.isna(valor) or str(valor).strip() == "":
        return 0.0
    
    # Se já for número, retorna logo
    if isinstance(valor, (int, float)):
        return float(valor)
    
    # Se for texto (ex: "11,5" ou "R$ 25,00")
    texto = str(valor).strip()
    texto = texto.replace("R$", "").replace(" ", "")
    texto = texto.replace(",", ".") # O segredo: troca vírgula por ponto
    try:
        return float(texto)
    except:
        return 0.0

def carregar_dados(aba):
    try:
        # Lê a planilha normal
        df = conn.read(worksheet=aba, ttl=0)
        
        if df.empty:
            return pd.DataFrame()

        # Remove espaços invisíveis dos cabeçalhos (ex: "Cliente " vira "Cliente")
        df.columns = df.columns.str.strip()

        # Se tiver coluna Data, converte para data
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
            df["Data_Dt"] = df["Data"].dt.date # Cria coluna auxiliar só de dia

        # Se tiver coluna Valor, limpa os números para poder somar
        if "Valor" in df.columns:
            df["Valor"] = df["Valor"].apply(limpar_dinheiro)

        return df
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame()

def salvar_dados(aba, df_novo):
    # Lê o que já tem
    df_antigo = conn.read(worksheet=aba, ttl=0)
    # Junta com o novo
    if df_antigo.empty:
        df_final = df_novo
    else:
        # Garante que os nomes batem para não criar colunas extras
        df_antigo.columns = df_antigo.columns.str.strip()
        df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
    
    conn.update(worksheet=aba, data=df_final)

def excluir(aba, index):
    df = conn.read(worksheet=aba, ttl=0)
    df = df.drop(index)
    conn.update(worksheet=aba, data=df)
    st.toast("Apagado!", icon="🗑️")
    time.sleep(1)
    st.rerun()

# --- TABS ---
aba1, aba2, aba3, aba4 = st.tabs(["Entradas", "Saídas", "Diário", "Mensal"])
hoje = date.today()

# 1. ENTRADAS
with aba1:
    st.subheader("Entradas")
    
    # Carrega usando os nomes da tua planilha: Data, Cliente, Serviço, Valor
    df_e = carregar_dados("Entradas")
    
    # Mostra tabela do dia
    st.write(f"**Hoje: {hoje.strftime('%d/%m')}**")
    if not df_e.empty and "Data_Dt" in df_e.columns:
        dia_atual = df_e[df_e["Data_Dt"] == hoje]
        if not dia_atual.empty:
            # Mostra colunas certinhas
            st.dataframe(dia_atual[["Cliente", "Serviço", "Valor"]], hide_index=True)
            
            # Botão de excluir o último (opcional, para simplificar)
            if st.button("Excluir última entrada de hoje"):
                excluir("Entradas", dia_atual.index[-1])

    st.divider()
    
    # Formulário
    with st.form("add_entrada", clear_on_submit=True):
        c1, c2 = st.columns(2)
        # Usa os teus nomes
        cli = c1.text_input("Cliente") 
        serv = c2.text_input("Serviço")
        val = st.number_input("Valor", min_value=0.0, step=0.50, format="%.2f")
        
        if st.form_submit_button("Salvar Entrada"):
            novo = pd.DataFrame([{
                "Data": str(hoje),
                "Cliente": cli,
                "Serviço": serv,
                "Valor": val
            }])
            salvar_dados("Entradas", novo)
            st.success("Salvo!")
            time.sleep(1)
            st.rerun()

# 2. SAÍDAS
with aba2:
    st.subheader("Saídas")
    df_s = carregar_dados("Saidas")
    
    if not df_s.empty and "Data_Dt" in df_s.columns:
        dia_s = df_s[df_s["Data_Dt"] == hoje]
        if not dia_s.empty:
            st.dataframe(dia_s[["Descrição", "Valor"]], hide_index=True)

    st.divider()
    with st.form("add_saida", clear_on_submit=True):
        desc = st.text_input("Descrição")
        val_s = st.number_input("Valor", min_value=0.0, step=0.50, format="%.2f")
        
        if st.form_submit_button("Salvar Saída"):
            novo = pd.DataFrame([{
                "Data": str(hoje),
                "Descrição": desc,
                "Valor": val_s
            }])
            salvar_dados("Saidas", novo)
            st.success("Gasto salvo!")
            time.sleep(1)
            st.rerun()

# 3. DIÁRIO (O QUE TU QUERIAS VER FUNCIONAR)
with aba3:
    st.header("Fechamento de Caixa")
    
    # Selecionar Data
    data_filtro = st.date_input("Data:", hoje)
    st.markdown("---")
    
    # Recarrega dados garantindo tratamento
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    # Somas
    total_entrada = 0.0
    if not df_e.empty and "Data_Dt" in df_e.columns:
        # Filtra dia e soma a coluna Valor (que já foi limpa na função carregar)
        total_entrada = df_e[df_e["Data_Dt"] == data_filtro]["Valor"].sum()
        
    total_saida = 0.0
    if not df_s.empty and "Data_Dt" in df_s.columns:
        total_saida = df_s[df_s["Data_Dt"] == data_filtro]["Valor"].sum()
        
    lucro = total_entrada - total_saida
    
    # Placar
    c1, c2, c3 = st.columns(3)
    c1.metric("Entrou", f"R$ {total_entrada:.2f}")
    c2.metric("Saiu", f"R$ {total_saida:.2f}")
    c3.metric("Lucro", f"R$ {lucro:.2f}", delta=lucro)

# 4. MENSAL
with aba4:
    st.header("Resumo do Mês")
    mes = hoje.month
    
    soma_e_mes = 0.0
    if not df_e.empty:
        soma_e_mes = df_e[df_e["Data"].dt.month == mes]["Valor"].sum()
        
    soma_s_mes = 0.0
    if not df_s.empty:
        soma_s_mes = df_s[df_s["Data"].dt.month == mes]["Valor"].sum()
        
    st.metric(f"Lucro Mês {mes}", f"R$ {soma_e_mes - soma_s_mes:.2f}")
