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

# --- Funções Auxiliares (CORRIGIDA PARA LER DADOS REAIS) ---
def carregar_dados(aba):
    try:
        # Lê os dados da planilha
        df = conn.read(worksheet=aba, ttl=0)
        
        # Se vier vazio, retorna DataFrame vazio
        if df.empty:
            return pd.DataFrame()

        # 1. Limpeza de Nomes das Colunas (Remove espaços extras: "Cliente " vira "Cliente")
        df.columns = df.columns.str.strip()

        # 2. Tratamento da DATA
        if "Data" in df.columns:
            # Converte para datetime forçando erros a virarem NaT (Not a Time)
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
            # Cria a coluna auxiliar de data pura (sem horas)
            df["Data_Dt"] = df["Data"].dt.date
            # Remove linhas que tenham data inválida (opcional, mas evita erros)
            df = df.dropna(subset=["Data_Dt"])

        # 3. Tratamento do VALOR (Corrige o problema da vírgula)
        if "Valor" in df.columns:
            # Converte tudo para texto primeiro -> Troca vírgula por ponto -> Converte para número
            df["Valor"] = df["Valor"].astype(str).str.replace(',', '.', regex=False)
            # Remove símbolos de moeda se existirem (R$)
            df["Valor"] = df["Valor"].str.replace('R$', '', regex=False)
            df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0)

        return df
    except Exception as e:
        # Mostra o erro no ecrã para facilitar a depuração (podes remover depois)
        st.error(f"Erro ao ler dados: {e}")
        return pd.DataFrame()

def salvar_registro(aba, novo_dado_df):
    try:
        df_existente = conn.read(worksheet=aba, ttl=0)
        if df_existente.empty:
            df_atualizado = novo_dado_df
        else:
            # Garante que as colunas estejam limpas antes de concatenar
            df_existente.columns = df_existente.columns.str.strip()
            df_atualizado = pd.concat([df_existente, novo_dado_df], ignore_index=True)
        
        conn.update(worksheet=aba, data=df_atualizado)
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def excluir_registro(aba, indice_para_deletar):
    df = conn.read(worksheet=aba, ttl=0)
    df_novo = df.drop(indice_para_deletar, axis=0)
    conn.update(worksheet=aba, data=df_novo)
    st.toast("Item removido!", icon="🗑️")
    time.sleep(1)
    st.rerun()

# --- Definição da Data Atual ---
data_hoje = date.today()

# --- Interface Principal ---
st.markdown("### 💅 Painel de Gestão")
aba_entradas, aba_saidas, aba_diario, aba_resumo = st.tabs(["💰 Entradas", "💸 Saídas", "📅 Resultado Diário", "📊 Balanço Mensal"])

# ================= ABA 1: ENTRADAS =================
with aba_entradas:
    st.header("Agendamentos e Receitas")
    
    # SELETOR DE DATA
    col_data_e, col_vazia = st.columns([1, 2])
    with col_data_e:
        data_selecionada_ent = st.date_input("Data de Trabalho:", data_hoje, key="dt_entradas")

    st.divider()

    # VISUALIZAÇÃO
    st.markdown(f"**Agenda de: {data_selecionada_ent.strftime('%d/%m/%Y')}**")
    
    df_entradas = carregar_dados("Entradas")
    
    if not df_entradas.empty and "Data_Dt" in df_entradas.columns:
        filtro_dia = df_entradas[df_entradas["Data_Dt"] == data_selecionada_ent]
        
        if filtro_dia.empty:
            st.info("Nenhum atendimento registrado nesta data.")
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
            c2.markdown("**Cliente**"); c3.markdown("**Serviço**"); c4.markdown("**Valor**")
            
            for index, row in filtro_dia.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
                # Exibe a hora se existir, senão mostra traço
                hora_formatada = row["Data"].strftime('%H:%M') if pd.notnull(row["Data"]) else "---"
                c1.write(hora_formatada)
                c2.write(row["Cliente"])
                c3.write(row["Serviço"])
                c4.write(f"R$ {float(row['Valor']):.2f}")
                if c5.button("🗑️", key=f"del_e_{index}"):
                    excluir_registro("Entradas", index)
    else:
        st.info("A aguardar dados...")

    st.markdown("---")
    st.subheader("Novo Registro")

    # FORMULÁRIO
    with st.form("form_entrada", clear_on_submit=True):
        st.write(f"Cadastrando para: **{data_selecionada_ent.strftime('%d/%m/%Y')}**")
        
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Nome da Cliente")
        with col2:
            servico = st.text_input("Serviço")
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar = st.form_submit_button("💾 Salvar Atendimento")
        
        if bt_salvar:
            if cliente and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_selecionada_ent),
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada # Salva como float/número direto
                }])
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} registrado com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Preencha o nome e o valor.")

# ================= ABA 2: SAÍDAS =================
with aba_saidas:
    st.header("Despesas")
    
    col_data_s, col_vazia_s = st.columns([1, 2])
    with col_data_s:
        data_selecionada_saida = st.date_input("Data da Despesa:", data_hoje, key="dt_saidas")

    st.divider()
    
    st.markdown(f"**Saídas de: {data_selecionada_saida.strftime('%d/%m/%Y')}**")
    df_saidas = carregar_dados("Saidas")
    
    if not df_saidas.empty and "Data_Dt" in df_saidas.columns:
        filtro_dia_s = df_saidas[df_saidas["Data_Dt"] == data_selecionada_saida]
        
        if filtro_dia_s.empty:
            st.info("Nenhuma saída nesta data.")
        else:
            for index, row in filtro_dia_s.iterrows():
                c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
                c2.write(row["Descrição"])
                c3.write(f"R$ {float(row['Valor']):.2f}")
                if c4.button("🗑️", key=f"del_s_{index}"):
                    excluir_registro("Saidas", index)
    
    st.markdown("---")
    
    with st.form("form_saida", clear_on_submit=True):
        st.write(f"Registrando saída em: **{data_selecionada_saida.strftime('%d/%m/%Y')}**")
        col1, col2 = st.columns(2)
        with col1:
            descricao = st.text_input("Descrição do Gasto")
        with col2:
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar_saida = st.form_submit_button("💾 Salvar Saída")
        
        if bt_salvar_saida:
            if descricao and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_selecionada_saida),
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                salvar_registro("Saidas", novo_df)
                st.success("✅ Saída registrada!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Preencha a descrição e o valor.")

# ================= ABA 3: RESULTADO DIÁRIO =================
with aba_diario:
    st.subheader("🔍 Filtro de Resultado Diário")
    
    col_d, _ = st.columns([1, 2])
    with col_d:
        data_analise = st.date_input("Qual dia deseja analisar?", data_hoje, key="dt_analise")
    
    st.markdown("---")
    st.markdown(f"### 📅 Resultado de: {data_analise.strftime('%d/%m/%Y')}")

    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")

    total_entradas_dia = 0.0
    entradas_dia = pd.DataFrame()
    if not df_e.empty and "Data_Dt" in df_e.columns:
        entradas_dia = df_e[df_e["Data_Dt"] == data_analise]
        total_entradas_dia = entradas_dia["Valor"].sum()

    total_saidas_dia = 0.0
    saidas_dia = pd.DataFrame()
    if not df_s.empty and "Data_Dt" in df_s.columns:
        saidas_dia = df_s[df_s["Data_Dt"] == data_analise]
        total_saidas_dia = saidas_dia["Valor"].sum()

    lucro_dia = total_entradas_dia - total_saidas_dia

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Entrada", f"R$ {total_entradas_dia:.2f}")
    col2.metric("Total Saída", f"R$ {total_saidas_dia:.2f}")
    col3.metric("Lucro do Dia", f"R$ {lucro_dia:.2f}", delta=lucro_dia)

    st.markdown("---")
    
    c_det1, c_det2 = st.columns(2)
    
    with c_det1:
        st.markdown("#### 📥 Entradas Detalhadas")
        if not entradas_dia.empty:
            st.dataframe(entradas_dia[["Cliente", "Serviço", "Valor"]], hide_index=True)
        else:
            st.info("Sem entradas.")

    with c_det2:
        st.markdown("#### 📤 Saídas Detalhadas")
        if not saidas_dia.empty:
            st.dataframe(saidas_dia[["Descrição", "Valor"]], hide_index=True)
        else:
            st.info("Sem saídas.")

# ================= ABA 4: RESUMO GERAL (MÊS) =================
with aba_resumo:
    st.subheader("📊 Balanço Mensal")
    
    df_e = carregar_dados("Entradas")
    df_s = carregar_dados("Saidas")
    
    mes_atual = data_hoje.month
    ano_atual = data_hoje.year
    nomes_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    
    st.markdown(f"**Referência:** {nomes_meses[mes_atual]}/{ano_atual}")
    
    soma_e_mes = 0.0
    soma_s_mes = 0.0
    
    if not df_e.empty and "Data_Dt" in df_e.columns:
        mask_e = (pd.to_datetime(df_e["Data"]).dt.month == mes_atual) & (pd.to_datetime(df_e["Data"]).dt.year == ano_atual)
        soma_e_mes = df_e[mask_e]["Valor"].sum()
        
    if not df_s.empty and "Data_Dt" in df_s.columns:
        mask_s = (pd.to_datetime(df_s["Data"]).dt.month == mes_atual) & (pd.to_datetime(df_s["Data"]).dt.year == ano_atual)
        soma_s_mes = df_s[mask_s]["Valor"].sum()
        
    lucro_mes = soma_e_mes - soma_s_mes

    c4, c5, c6 = st.columns(3)
    c4.metric("Entrada Mês", f"R$ {soma_e_mes:.2f}")
    c5.metric("Saída Mês", f"R$ {soma_s_mes:.2f}")
    c6.metric("Lucro Mês", f"R$ {lucro_mes:.2f}", delta=lucro_mes)
