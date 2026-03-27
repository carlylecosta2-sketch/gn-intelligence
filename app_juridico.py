import streamlit as st
import datetime
import json
import pypdf
import pandas as pd
import os
from openai import OpenAI
from fpdf import FPDF

# --- 👥 EQUIPE G&N ---
PROFISSIONAIS = ["Dr. Carlyle", "Dra. Lorena"]

# --- ⚙️ INICIALIZAÇÃO ---
client = None
try:
    if "OPENAI_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_KEY"].strip())
    else:
        st.error("❌ Chave OpenAI não encontrada nos Secrets.")
except Exception as e:
    st.error(f"⚠️ Erro: {e}")

# --- ⚖️ DISTRIBUIÇÃO AUTOMÁTICA ---
def definir_responsavel_automatico():
    if not os.path.exists('prazos_gn.csv'):
        return PROFISSIONAIS[0]
    df_atual = pd.read_csv('prazos_gn.csv', sep=';')
    if 'Responsável' not in df_atual.columns:
        return PROFISSIONAIS[0]
    contagem = df_atual['Responsável'].value_counts().to_dict()
    for p in PROFISSIONAIS:
        if p not in contagem: contagem[p] = 0
    return min(contagem, key=contagem.get)

# --- 📄 RELATÓRIO PDF (CORRIGIDO) ---
def gerar_relatorio_pdf(df):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 10, "GUALBERTO & NEGREIROS SOCIEDADE DE ADVOGADOS", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(190, 10, f"Mapa de Prazos - Gerado em {datetime.date.today().strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(26, 58, 90)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(40, 10, "Processo", border=1, fill=True)
        pdf.cell(55, 10, "Partes", border=1, fill=True)
        pdf.cell(40, 10, "Peca Sugerida", border=1, fill=True)
        pdf.cell(30, 10, "Responsavel", border=1, fill=True)
        pdf.cell(25, 10, "Vencimento", border=1, fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 7)
        for _, row in df.iterrows():
            def limpar(t): return str(t).encode('windows-1252', 'replace').decode('windows-1252')
            pdf.cell(40, 10, limpar(row['Processo']), border=1)
            pdf.cell(55, 10, limpar(row['Partes']), border=1)
            pdf.cell(40, 10, limpar(row['Peça Sugerida']), border=1)
            pdf.cell(30, 10, limpar(row.get('Responsável', 'N/A')), border=1)
            pdf.cell(25, 10, limpar(row['Vencimento']), border=1)
            pdf.ln()
        return bytes(pdf.output())
    except: return None

# --- 📅 MOTOR DE CÁLCULO (MOSSORÓ/RN) ---
def eh_feriado_ou_fds(data):
    feriados = [(1,1),(13,6),(7,9),(30,9),(3,10),(12,10),(2,11),(15,11),(13,12),(25,12)]
    return data.weekday() >= 5 or (data.day, data.month) in feriados

def calcular_vencimento(dias, data_base_str):
    try:
        data_inicio = datetime.datetime.strptime(data_base_str, "%Y-%m-%d").date()
    except:
        data_inicio = datetime.date.today()
    data_atual = data_inicio
    cont = 0
    try: d = int(dias)
    except: d = 15
    while cont < d:
        data_atual += datetime.timedelta(days=1)
        if not eh_feriado_ou_fds(data_atual): cont += 1
    return data_atual

# --- 🧠 INTELIGÊNCIA JURÍDICA (FOCO EM PETIÇÕES E PARECER) ---
def analisar_documento_co_piloto(texto):
    if client is None: return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Você é o Co-piloto Jurídico da G&N Advogados em Mossoró/RN.
                Sua prioridade absoluta é: 
                1. Identificar TODAS as petições cabíveis para o momento processual.
                2. Fornecer um Parecer de Risco detalhado sobre as consequências da decisão ou mandado.
                Retorne SEMPRE em JSON com as chaves exatas: 'processo', 'partes', 'data_documento', 'parecer_estrategico', 'peca_principal', 'rascunho_estrutura', 'outras_peticoes', 'prazo', 'prioridade'."""},
                {"role": "user", "content": f"Analise profundamente e sugira as peças ideais. Texto: {texto[:12000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na análise: {e}"); return None

# --- 🏛️ INTERFACE ---
st.set_page_config(page_title="GN - Consultoria Estratégica", page_icon="🏛️", layout="wide")
st.title("🏛️ G&N Intelligence: Co-piloto Estratégico & Gestão")

c_in, c_out = st.columns([1, 1.2], gap="large")

with c_in:
    st.subheader("📥 Entrada de Caso")
    pdf_input = st.file_uploader("PDF:", type="pdf")
    txt_input = st.text_area("Texto:", height=150)
    
    if st.button("🚀 GERAR PARECER E ESTRUTURA"):
        raw = ""
        if pdf_input: raw = "".join([p.extract_text() for p in pypdf.PdfReader(pdf_input).pages])
        elif txt_input: raw = txt_input
        if raw:
            with st.spinner("Genina traçando estratégia processual..."):
                res = analisar_documento_co_piloto(raw)
                if res:
                    st.session_state['res_gn'] = res
                    st.session_state['venc_gn'] = calcular_vencimento(res['prazo'], res['data_documento'])
                    st.session_state['resp_gn'] = definir_responsavel_automatico()

with c_out:
    if 'res_gn' in st.session_state:
        res = st.session_state['res_gn']
        venc = st.session_state['venc_gn'].strftime('%d/%m/%Y')
        resp = st.session_state['resp_gn']
        
        st.subheader("📑 Diagnóstico da Genina")
        st.warning(f"⚖️ **Responsável:** {resp} | **Vencimento:** {venc}")
        st.write(f"**Proc:** `{res.get('processo', 'Não localizado')}`")
        st.write(f"**Partes:** `{res.get('partes', 'Não localizadas')}`")
        
        # FOCO NO PARECER ESTRATÉGICO
        st.markdown("### 📝 Parecer Estratégico e Riscos")
        st.info(res.get('parecer_estrategico', 'Análise em processamento...'))
        
        # FOCO NAS PETIÇÕES
        st.markdown(f"### 🛠️ Peça Sugerida: **{res.get('peca_principal', 'Não definida')}**")
        st.text_area("Esqueleto da Petição:", value=res.get('rascunho_estrutura', ''), height=200)
        
        st.markdown("### 📖 Outras Petições Possíveis")
        st.write(res.get('outras_peticoes', 'Nenhuma petição secundária sugerida.'))
        
        if st.button("📥 CONFIRMAR E SALVAR NA AGENDA"):
            nova_linha = {
                "Data": datetime.date.today().strftime('%d/%m/%Y'),
                "Processo": res.get('processo','-'), 
                "Partes": res.get('partes','-'), 
                "Peça Sugerida": res.get('peca_principal','-'), 
                "Responsável": resp, 
                "Vencimento": venc, 
                "Prioridade": res.get('prioridade','Média')
            }
            pd.DataFrame([nova_linha]).to_csv('prazos_gn.csv', mode='a', index=False, header=not os.path.exists('prazos_gn.csv'), sep=';', encoding='utf-8-sig')
            st.success(f"✅ Salvo com sucesso!")

st.divider()

# --- AGENDA E RELATÓRIOS ---
st.subheader("📋 Mapa de Prazos do Escritório")
if os.path.exists('prazos_gn.csv'):
    dados = pd.read_csv('prazos_gn.csv', sep=';')
    st.dataframe(dados, use_container_width=True)
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ Limpar Agenda"):
            os.remove('prazos_gn.csv'); st.rerun()
    with col2:
        pdf_bytes = gerar_relatorio_pdf(dados)
        if pdf_bytes:
            st.download_button(label="📥 BAIXAR RELATÓRIO PDF", data=pdf_bytes, file_name=f"Relatorio_GN_{datetime.date.today()}.pdf", mime="application/pdf")
else:
    st.info("Nenhum prazo pendente.")

st.sidebar.markdown(f"**Equipe:** {', '.join(PROFISSIONAIS)}")