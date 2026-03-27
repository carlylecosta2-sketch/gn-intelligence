import streamlit as st
import datetime
import json
import pypdf
import pandas as pd
import os
from openai import OpenAI

# --- ⚙️ CONFIGURAÇÕES E INICIALIZAÇÃO SEGURA ---
client = None
try:
    if "OPENAI_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_KEY"].strip())
    else:
        st.error("❌ Chave OpenAI não encontrada nos Secrets.")
except Exception as e:
    st.error(f"⚠️ Erro Crítico: {e}")

# --- IDENTIDADE VISUAL G&N ---
st.set_page_config(page_title="GN - Consultoria Estratégica", page_icon="🏛️", layout="wide")
st.markdown("<style>.stMetric { background-color: #ffffff; border-left: 5px solid #1a3a5a; border-radius: 10px; }</style>", unsafe_allow_html=True)

# --- MOTOR DE CÁLCULO MOSSORÓ/RN ---
def eh_feriado_ou_fds(data):
    # Feriados de Mossoró e Nacionais
    feriados = [(1,1),(13,6),(7,9),(30,9),(3,10),(12,10),(2,11),(15,11),(13,12),(25,12)]
    return data.weekday() >= 5 or (data.day, data.month) in feriados

def calcular_vencimento(dias):
    data = datetime.date.today()
    cont = 0
    try: d = int(dias)
    except: d = 15 # Padrão se IA falhar
    while cont < d:
        data += datetime.timedelta(days=1)
        if not eh_feriado_ou_fds(data): cont += 1
    return data

# --- 🧠 INTELIGÊNCIA JURÍDICA ESTRATÉGICA ---
def analisar_documento_co_piloto(texto):
    if client is None: return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Você é o Co-piloto Estratégico Sênior da Gualberto & Negreiros em Mossoró/RN, especialista em Direito Público e Administrativo.
                Sua tarefa é analisar o documento e fornecer um diagnóstico técnico rigoroso em JSON.
                O campo 'parecer_risco' deve conter uma análise de riscos e teses defensivas.
                O campo 'rascunho_estrutura' deve conter o rascunho da estrutura (esqueleto) da Peça Principal Sugerida, com tópicos e fundamentos legais baseados no CPC (ex: Preliminares, Mérito, Pedidos).
                O campo 'sugestoes_alternativas' deve listar as demais peças cabíveis."""},
                {"role": "user", "content": f"Analise profundamente e retorne JSON: {{'processo':'','tipo_doc':'','peca_principal_sugerida':'','prazo':15,'resumo':'','parecer_risco':'','rascunho_estrutura':'','sugestoes_alternativas':[],'prioridade':''}}. Texto: {texto[:12000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na análise estratégica: {e}")
        return None

# --- 🏛️ INTERFACE G&N Intelligence ---
st.title("🏛️ G&N Intelligence: Consultoria Estratégica & Co-piloto de Redação")
st.caption("Diagnóstico Tático de Casos e Rascunho de Peças | Foco em Administração Pública")

c_in, c_out = st.columns([1, 1.2], gap="large")

with c_in:
    st.subheader("📥 Entrada de Caso")
    pdf = st.file_uploader("Upload de Mandado/Petição (PDF):", type="pdf")
    txt = st.text_area("Ou cole o inteiro teor:", height=150)
    
    if st.button("🚀 GERAR ESTRUTURA E PARECER"):
        raw = ""
        if pdf:
            raw = "".join([p.extract_text() for p in pypdf.PdfReader(pdf).pages])
        elif txt: raw = txt
            
        if raw:
            with st.spinner("Genina analisando teses e estruturando defesa..."):
                res = analisar_documento_co_piloto(raw)
                if res:
                    st.session_state['res_gn'] = res
                    st.session_state['venc_gn'] = calcular_vencimento(res['prazo'])

with c_out:
    if 'res_gn' in st.session_state:
        res = st.session_state['res_gn']
        venc = st.session_state['venc_gn'].strftime('%d/%m/%Y')
        
        st.subheader("📑 Diagnóstico e Estrutura de Defesa da Genina")
        st.write(f"**Processo:** `{res['processo']}` | **Vencimento:** `{venc}`")
        
        # Seção de Parecer
        with st.expander("📝 PARECER PRÉVIO E ANÁLISE DE RISCO (Direito Administrativo)", expanded=True):
            st.info(res['parecer_risco'])
        
        # Rascunho Estruturado (O Co-piloto)
        st.write(f"**🛠️ ESTRUTURA SUGERIDA DA PEÇA PRINCIPAL (Rascunho)**")
        st.write(f"*(Peça Sugerida: {res['peca_principal_sugerida']} | Prazo: {res['prazo']} úteis)*")
        st.text_area("Copie o esqueleto da defesa:", value=res['rascunho_estrutura'], height=300)
        
        # Sugestões Alternativas
        st.write("**📖 OUTRAS SUGESTÕES PROCESSUAIS**")
        for peca in res['sugestoes_alternativas']:
            st.markdown(f"- {peca}")
            
        if st.button("📥 SALVAR NA AGENDA DO ESCRITÓRIO"):
            df = pd.DataFrame([{"Data": datetime.date.today(), "Proc": res['processo'], "Peça": res['peca_principal_sugerida'], "Venc": venc}])
            df.to_csv('prazos_gn.csv', mode='a', index=False, header=not os.path.exists('prazos_gn.csv'), sep=';', encoding='utf-8-sig')
            st.success("✅ Caso e prazo arquivados na agenda com sucesso!")

st.divider()

# --- AGENDA DE TAREFAS ---
st.subheader("📋 Lista de Prazos e Casos em Mossoró/RN")
if os.path.exists('prazos_gn.csv'):
    dados = pd.read_csv('prazos_gn.csv', sep=';')
    st.dataframe(dados, use_container_width=True)
    if st.button("🗑️ Limpar Agenda Completa"):
        os.remove('prazos_gn.csv')
        st.rerun()
else:
    st.info("Nenhum prazo pendente salvo.")

st.sidebar.markdown(f"**Responsável:** Dr. Carlyle Negreiros")