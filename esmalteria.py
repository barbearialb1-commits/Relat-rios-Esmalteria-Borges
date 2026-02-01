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

# --- FUNÇÃO DE LIMPEZA INTELIGENTE (O SEGREDO DA CORREÇÃO) ---
def limpar_valor_moeda(valor):
    """
    Esta função aceita QUALQUER coisa (texto com vírgula, número inteiro, vazio)
    e devolve sempre um número decimal correto para o Python somar.
    """
    if pd.isna(valor) or valor == "":
        return 0.0
    
    # Se já for número (ex: 25 ou 25.0), devolve direto
    if isinstance(valor, (int, float)):
        return float(valor)
        
    # Se for texto (ex: "25,00" ou "R$ 25,00"), limpa
    try:
        valor_str = str(valor)
        valor_str = valor_str.replace("R$", "").replace(" ", "").replace(",", ".")
        return float(valor_str)
    except:
        return 0.0

def carregar_dados_tratados(aba):
    """Carrega e já arruma as colunas de Data e Valor para não dar erro depois"""
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df.empty:
             return pd.DataFrame()
        
        # 1. Garante que a Data é lida corretamente (Olhando para tua imagem: YYYY-MM-DD)
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce')
            df["Data_Dt"] = df["Data"].dt.date # Cria coluna só com o dia (sem hora)

        # 2. Garante que o Valor é numérico usando a função inteligente
        if "Valor" in df.columns:
            df["Valor_Calc"] = df["Valor"].apply(limpar_valor_moeda)

        return df
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame()

def salvar_registro(aba, novo_dado_df):
    # Lê o original sem tratamento para apenas adicionar a linha nova
    df_existente = conn.read(worksheet=aba, ttl=0)
    if df_existente.empty:
        df_atualizado = novo_dado_df
    else:
        df_atualizado = pd.concat([df_existente, novo_dado_df], ignore_index=True)
    conn.update(worksheet=aba, data=df_atualizado)

def excluir_registro(aba, indice_para_deletar):
    df = conn.read(worksheet=aba, ttl=0) # Lê cru para deletar pelo índice certo
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
    st.subheader("Registrar Atendimento")
    
    # 1. DATA (Filtro Visual)
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        data_selecionada = st.date_input("Ver agenda de:", data_hoje)

    st.markdown("---")

    # 2. TABELA (Mostra o que já tem)
    st.markdown(f"**Atendimentos em: {data_selecionada.strftime('%d/%m/%Y')}**")
    
    df_entradas = carregar_dados_tratados("Entradas")
    
    if not df_entradas.empty and "Data_Dt" in df_entradas.columns:
        # Filtra pelo dia selecionado
        filtro_dia = df_entradas[df_entradas["Data_Dt"] == data_selecionada]
        
        if filtro_dia.empty:
            st.info("Nenhum atendimento neste dia.")
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
            c1.markdown("**Data**"); c2.markdown("**Cliente**"); c3.markdown("**Serviço**"); c4.markdown("**Valor**")
            
            for index, row in filtro_dia.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 2, 1])
                # Data original formatada
                c1.write(row["Data"].strftime('%d/%m') if pd.notnull(row["Data"]) else "-")
                c2.write(row["Cliente"])
                c3.write(row["Serviço"])
                # Usa o valor calculado para exibir bonitinho
                c4.write(f"R$ {row['Valor_Calc']:.2f}")
                
                if c5.button("🗑️", key=f"del_e_{index}"):
                    excluir_registro("Entradas", index)
    else:
        st.info("A aguardar dados...")

    st.divider()

    # 3. FORMULÁRIO
    with st.form("form_entrada", clear_on_submit=True):
        st.write(f"**Novo agendamento para {data_selecionada.strftime('%d/%m/%Y')}**")
        
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Nome da Cliente")
        with col2:
            servico = st.text_input("Serviço")
            valor_entrada = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar = st.form_submit_button("💾 Salvar")
        
        if bt_salvar:
            if cliente and valor_entrada > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_selecionada),
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor_entrada
                }])
                salvar_registro("Entradas", novo_df)
                st.success(f"✅ {cliente} agendada!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Preencha nome e valor.")

# ================= ABA 2: SAÍDAS =================
with aba_saidas:
    st.subheader("Registrar Despesa")
    
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        data_sel_saida = st.date_input("Data da Despesa", data_hoje, key="data_saida_pick")

    st.markdown("---")
    
    st.markdown(f"**Gastos de: {data_sel_saida.strftime('%d/%m/%Y')}**")
    df_saidas = carregar_dados_tratados("Saidas")
    
    if not df_saidas.empty and "Data_Dt" in df_saidas.columns:
        filtro_dia_s = df_saidas[df_saidas["Data_Dt"] == data_sel_saida]
        
        if filtro_dia_s.empty:
            st.info("Nenhuma despesa neste dia.")
        else:
            c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
            c1.markdown("**Data**"); c2.markdown("**Descrição**"); c3.markdown("**Valor**")
            
            for index, row in filtro_dia_s.iterrows():
                c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
                c1.write(row["Data"].strftime('%d/%m') if pd.notnull(row["Data"]) else "-")
                c2.write(row["Descrição"])
                c3.write(f"R$ {row['Valor_Calc']:.2f}")
                if c4.button("🗑️", key=f"del_s_{index}"):
                    excluir_registro("Saidas", index)
    
    st.divider()

    with st.form("form_saida", clear_on_submit=True):
        st.write(f"**Nova saída para {data_sel_saida.strftime('%d/%m')}**")
        col1, col2 = st.columns(2)
        with col1:
            descricao = st.text_input("Descrição")
        with col2:
            valor_saida = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            
        bt_salvar_saida = st.form_submit_button("💾 Salvar Gasto")
        
        if bt_salvar_saida:
            if descricao and valor_saida > 0:
                novo_df = pd.DataFrame([{
                    "Data": str(data_sel_saida),
                    "Descrição": descricao,
                    "Valor": valor_saida
                }])
                salvar_registro("Saidas", novo_df)
                st.success("✅ Saída salva!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Preencha descrição e valor.")

# ================= ABA 3: RESULTADO DIÁRIO (FUNCIONA AGORA) =================
with aba_diario:
    st.subheader("📆 Fechamento do Dia")
    
    # Filtro
    col_f1, _ = st.columns([1, 2])
    with col_f1:
        dia_analise = st.date_input("Escolha o dia:", data_hoje, key="dia_analise")
        
    st.markdown("---")
    
    # Carrega dados TRATADOS (com coluna Valor_Calc segura)
    df_e = carregar_dados_tratados("Entradas")
    df_s = carregar_dados_tratados("Saidas")
    
    total_ent = 0.0
    total_sai = 0.0
    
    # Soma Entradas
    df_e_dia = pd.DataFrame()
    if not df_e.empty and "Data_Dt" in df_e.columns:
        df_e_dia = df_e[df_e["Data_Dt"] == dia_analise]
        total_ent = df_e_dia["Valor_Calc"].sum() # Soma a coluna tratada

    # Soma Saídas
    df_s_dia = pd.DataFrame()
    if not df_s.empty and "Data_Dt" in df_s.columns:
        df_s_dia = df_s[df_s["Data_Dt"] == dia_analise]
        total_sai = df_s_dia["Valor_Calc"].sum()

    lucro = total_ent - total_sai

    # Exibe Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Entrada Dia", f"R$ {total_ent:.2f}")
    col2.metric("Saída Dia", f"R$ {total_sai:.2f}")
    col3.metric("Lucro Líquido", f"R$ {lucro:.2f}", delta=lucro)

    st.markdown("---")
    
    # Tabelas de detalhe
    c_det1, c_det2 = st.columns(2)
    with c_det1:
        st.markdown("##### 📥 Lista de Entradas")
        if not df_e_dia.empty:
            st.dataframe(df_e_dia[["Cliente", "Serviço", "Valor"]], hide_index=True)
        else:
            st.caption("Sem registros.")

    with c_det2:
        st.markdown("##### 📤 Lista de Saídas")
        if not df_s_dia.empty:
            st.dataframe(df_s_dia[["Descrição", "Valor"]], hide_index=True)
        else:
            st.caption("Sem registros.")

# ================= ABA 4: RESUMO GERAL (MÊS) =================
with aba_resumo:
    st.subheader("📊 Balanço Mensal")
    
    df_e = carregar_dados_tratados("Entradas")
    df_s = carregar_dados_tratados("Saidas")
    
    mes_atual = data_hoje.month
    ano_atual = data_hoje.year
    nomes_meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    
    st.markdown(f"**Referência:** {nomes_meses[mes_atual]}/{ano_atual}")
    
    val_e_mes = 0.0
    val_s_mes = 0.0
    
    if not df_e.empty and "Data_Dt" in df_e.columns:
        mask_e = (df_e["Data"].dt.month == mes_atual) & (df_e["Data"].dt.year == ano_atual)
        val_e_mes = df_e[mask_e]["Valor_Calc"].sum()

    if not df_s.empty and "Data_Dt" in df_s.columns:
        mask_s = (df_s["Data"].dt.month == mes_atual) & (df_s["Data"].dt.year == ano_atual)
        val_s_mes = df_s[mask_s]["Valor_Calc"].sum()
        
    lucro_mes = val_e_mes - val_s_mes

    c4, c5, c6 = st.columns(3)
    c4.metric("Entrou no Mês", f"R$ {val_e_mes:.2f}")
    c5.metric("Saiu no Mês", f"R$ {val_s_mes:.2f}")
    c6.metric("Lucro Mês", f"R$ {lucro_mes:.2f}", delta=lucro_mes)
