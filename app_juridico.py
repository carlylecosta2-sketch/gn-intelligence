import streamlit as st
import datetime
import json
import pypdf
import pandas as pd
import os
from openai import OpenAI

# --- ⚙️ CONFIGURAÇÕES E INICIALIZAÇÃO SEGURA ---

# 1. Definimos o client como None inicialmente para evitar o erro de 'not defined'
client = None

try:
    # Tentativa de carregar as chaves do "Cofre" (Secrets)
    # O .strip() é essencial para remover espaços invisíveis que cancelam a chave
    if "OPENAI_KEY" in st.secrets:
        OPENAI_KEY = st.secrets["OPENAI_KEY"].strip()
        client = OpenAI(api_key=OPENAI_KEY)
    else:
        st.error("❌ Erro Crítico: A chave 'OPENAI_KEY' não foi encontrada nos Secrets.")
except Exception as e:
    st.error(f"⚠️ Erro ao inicializar a chave: {e}")

# --- IDENTIDADE VISUAL G&N ---
st.set_page_config(page_title="GN - Inteligência Processual", page_icon="🏛️", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; background-color: #1a3a5a; color: white; border-radius: 10px; font-weight: bold; }
    .stMetric { background-color: white; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# MODO SEGURO: O código não sabe a chave, ele pede ao arquivo local
def carregar_config():
    if not os.path.exists("config_gn.txt"):
        # Se o arquivo não existir, cria um modelo vazio
        with open("config_gn.txt", "w") as f:
            f.write("OPENAI_KEY=COLE_SUA_CHAVE_AQUI")
        return None

# --- ⚖️ MOTOR DE MOSSORÓ/RN ---
def eh_feriado_ou_fds(data):
    # Feriados de Mossoró e Nacionais
    feriados = [(1,1),(13,6),(7,9),(30,9),(3,10),(12,10),(2,11),(15,11),(13,12),(25,12)]
    return data.weekday() >= 5 or (data.day, data.month) in feriados

def calcular_vencimento(dias_uteis):
    data = datetime.date.today()
    cont = 0
    while cont < dias_uteis:
        data += datetime.timedelta(days=1)
        if not eh_feriado_ou_fds(data): cont += 1
    return data

# --- 🤖 INTELIGÊNCIA ---
def analisar_documento(texto):
    # Verificação de segurança antes de prosseguir
    if client is None:
        return {"processo": "Erro", "peca": "Erro", "prazo": "0", "resumo": "Configuração de IA ausente.", "prioridade": "N/A"}
        
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Você é o consultor jurídico sênior da G&N Advogados em Mossoró. Extraia dados em JSON."},
                {"role": "user", "content": f"Analise o texto jurídico e extraia: 'processo', 'tipo_doc', 'peca', 'prazo' (apenas número), 'resumo', 'prioridade'. Documento: {texto[:12000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na análise da OpenAI: {e}")
        return None

# --- 🏛️ INTERFACE ---
st.title("🏛️ Genina OpenIA")
st.caption("Gestão Estratégica de Prazos | Mossoró-RN | G&N Advogados")

c_in, c_out = st.columns([1, 1], gap="large")

with c_in:
    st.subheader("📥 Entrada")
    pdf = st.file_uploader("Subir PDF:", type="pdf")
    txt_manual = st.text_area("Ou cole o texto:", height=150)
    
    if st.button("🚀 ANALISAR AGORA"):
        raw_text = ""
        if pdf:
            reader = pypdf.PdfReader(pdf)
            raw_text = "".join([p.extract_text() for p in reader.pages])
        else:
            raw_text = txt_manual
            
        if raw_text:
            with st.spinner("Analisando rito processual..."):
                res = analisar_documento(raw_text)
                if res:
                    st.session_state['res_gn'] = res
                    st.session_state['venc_gn'] = calcular_vencimento(int(res['prazo']))
        else:
            st.warning("Insira um documento.")

with c_out:
    st.subheader("📑 Diagnóstico")
    if 'res_gn' in st.session_state:
        res, venc = st.session_state['res_gn'], st.session_state['venc_gn']
        v_fmt = venc.strftime('%d/%m/%Y')
        
        st.write(f"**Processo:** `{res['processo']}`")
        m1, m2 = st.columns(2)
        m1.metric("Peça", res['peca'])
        m2.metric("Vencimento", v_fmt)
        st.info(f"**Resumo:** {res['resumo']}")
        
        if st.button("📥 SALVAR NA AGENDA"):
            df = pd.DataFrame([{"Processo": res['processo'], "Peça": res['peca'], "Vencimento": v_fmt, "Prioridade": res['prioridade']}])
            df.to_csv('prazos_gn.csv', mode='a', index=False, header=not os.path.exists('prazos_gn.csv'), sep=';', encoding='utf-8-sig')
            
            st.success("✅ Salvo com sucesso na agenda!")
            st.balloons()

st.divider()

# --- LISTA DE TAREFAS ---
st.subheader("📋 Lista de Prazos Pendentes - G&N")
if os.path.exists('prazos_gn.csv'):
    dados = pd.read_csv('prazos_gn.csv', sep=';')
    st.dataframe(dados, use_container_width=True)
    if st.button("🗑️ Limpar Agenda"):
        os.remove('prazos_gn.csv')
        st.rerun()
else:
    st.info("Nenhum prazo pendente.")

st.sidebar.markdown(f"**Responsável:** Dr. Carlyle Negreiros")