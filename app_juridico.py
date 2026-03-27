import streamlit as st
import datetime
import json
import pypdf
import pandas as pd
import os
from openai import OpenAI
from fpdf import FPDF

# --- 👥 EQUIPE G&N ---
PROFISSIONAIS = ["Dr. Carlyle", "Dra. Jaqueline"]

# --- ⚙️ INICIALIZAÇÃO SEGURA ---
client = None
try:
    if "OPENAI_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_KEY"].strip())
        client = OpenAI(api_key=st.secrets["OPENAI_KEY"].strip())
    else:
        st.error("❌ Chave OpenAI não encontrada nos Secrets.")
except Exception as e:
    st.error(f"⚠️ Erro de Inicialização: {e}")

# --- ⚖️ DISTRIBUIÇÃO AUTOMÁTICA ---
def definir_responsavel_automatico():
    if not os.path.exists('prazos_gn.csv'):
        return PROFISSIONAIS[0]
    try:
        df_atual = pd.read_csv('prazos_gn.csv', sep=';')
        if 'Responsável' not in df_atual.columns:
            return PROFISSIONAIS[0]
        contagem = df_atual['Responsável'].value_counts().to_dict()
        for p in PROFISSIONAIS:
            if p not in contagem: contagem[p] = 0
        return min(contagem, key=contagem.get)
    except:
        return PROFISSIONAIS[0]

# --- 📄 RELATÓRIO PDF (SISTEMA DE LIMPEZA DE CARACTERES) ---
def gerar_relatorio_pdf(df):
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Função interna para limpar caracteres que o PDF não suporta
        def limpar_texto(txt):
            if pd.isna(txt): return ""
            txt = str(txt)
            # Troca caracteres especiais por equivalentes simples
            substituicoes = {
                "–": "-", "—": "-", "“": "\"", "”": "\"", 
                "‘": "'", "’": "'", "…": "...", "•": "*"
            }
            for original, novo in substituicoes.items():
                txt = txt.replace(original, novo)
            # Força a codificação para o padrão do PDF (latin-1)
            return txt.encode('latin-1', 'replace').decode('latin-1')

        pdf.set_font("Arial", "B", 14)
        pdf.cell(190, 10, "GUALBERTO & NEGREIROS SOCIEDADE DE ADVOGADOS", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(190, 10, f"Mapa de Prazos - Gerado em {datetime.date.today().strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.ln(10)
        
        widths = [35, 55, 45, 30, 25]
        headers = ["Processo", "Partes", "Peca Sugerida", "Responsavel", "Vencimento"]
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(26, 58, 90)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(widths[i], 10, h, border=1, fill=True, align="C")
        pdf.ln()
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 7)
        for _, row in df.iterrows():
            line_height = 6
            x, y = pdf.get_x(), pdf.get_y()
            
            # Aplica a limpeza em cada campo antes de escrever no PDF
            p_proc = limpar_texto(row['Processo'])
            p_part = limpar_texto(row['Partes'])
            p_peca = limpar_texto(row['Peça Sugerida'])
            p_resp = limpar_texto(row.get('Responsável', 'N/A'))
            p_venc = limpar_texto(row['Vencimento'])

            pdf.multi_cell(widths[0], line_height, p_proc, border=1)
            y2 = pdf.get_y()
            pdf.set_xy(x + widths[0], y)
            pdf.multi_cell(widths[1], line_height, p_part, border=1)
            y3 = pdf.get_y()
            pdf.set_xy(x + widths[0] + widths[1], y)
            pdf.multi_cell(widths[2], line_height, p_peca, border=1)
            y4 = pdf.get_y()
            pdf.set_xy(x + widths[0] + widths[1] + widths[2], y)
            pdf.multi_cell(widths[3], line_height, p_resp, border=1)
            y5 = pdf.get_y()
            pdf.set_xy(x + widths[0] + widths[1] + widths[2] + widths[3], y)
            pdf.multi_cell(widths[4], line_height, p_venc, border=1)
            y6 = pdf.get_y()
            
            pdf.set_y(max(y2, y3, y4, y5, y6))
            
        return bytes(pdf.output())
    except Exception as e:
        st.error(f"Erro na geração do relatório: {e}")
        return None

# --- 📅 MOTOR DE CÁLCULO MOSSORÓ/RN ---
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

# --- 🧠 CÉREBRO ESTRATÉGICO ---
def analisar_documento_co_piloto(texto):
    if client is None: return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Você é o Diretor Jurídico da G&N.
                Sua análise deve ser TÁTICA.
                1. Identifique o documento atual.
                2. Sugira a PRÓXIMA PEÇA processual (ex: Agravo, Embargos, Contestação).
                3. PROIBIDO: Sugerir a mesma peça que o juiz já decidiu no texto."""},
                {"role": "user", "content": f"Analise o texto e retorne JSON: {{'processo':'','partes':'','data_documento':'YYYY-MM-DD','tipo_doc':'','parecer':'','peca_sugerida':'','estrutura':'','secundarias':'','prazo':15,'prioridade':''}}. Texto: {texto[:12000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na análise estratégica: {e}"); return None

# --- 🏛️ INTERFACE ---
st.set_page_config(page_title="GN - Estratégia Jurídica", page_icon="🏛️", layout="wide")
st.title("🏛️ Genina IA")
st.caption("Gestão Estratégica de Prazos | GN Advogados")
c_in, c_out = st.columns([1, 1.2], gap="large")

with c_in:
    st.subheader("📥 Entrada")
    pdf_input = st.file_uploader("Upload PDF:", type="pdf")
    txt_input = st.text_area("Cole o Texto:", height=150)
    
    if st.button("🚀 ANALISAR CASO"):
        raw = ""
        if pdf_input: raw = "".join([p.extract_text() for p in pypdf.PdfReader(pdf_input).pages])
        elif txt_input: raw = txt_input
        if raw:
            with st.spinner("Genina analisando rito processual..."):
                res = analisar_documento_co_piloto(raw)
                if res:
                    st.session_state['res_gn'] = res
                    st.session_state['venc_gn'] = calcular_vencimento(res.get('prazo', 15), res.get('data_documento', ''))
                    st.session_state['resp_gn'] = definir_responsavel_automatico()

with c_out:
    if 'res_gn' in st.session_state:
        res = st.session_state['res_gn']
        venc = st.session_state['venc_gn'].strftime('%d/%m/%Y')
        resp = st.session_state['resp_gn']
        
        st.subheader("📑 Diagnóstico da Genina")
        st.warning(f"⚖️ **Próximo Passo:** {res.get('peca_sugerida', '-')}")
        
        col1, col2 = st.columns(2)
        col1.write(f"**Documento:** `{res.get('tipo_doc', '-')}`")
        col1.write(f"**Vencimento:** `{venc}`")
        col2.write(f"**Responsável:** `{resp}`")
        col2.write(f"**Processo:** `{res.get('processo', '-')}`")
        
        st.write(f"**Partes:** {res.get('partes', '-')}")
        
        st.markdown("### 📝 Parecer de Risco")
        st.info(res.get('parecer', '-'))
        
        st.markdown("### 🛠️ Estrutura Sugerida")
        st.text_area("Esqueleto:", value=res.get('estrutura', ''), height=200)
        
        if st.button("📥 SALVAR NA AGENDA"):
            nova_linha = {
                "Data": datetime.date.today().strftime('%d/%m/%Y'),
                "Processo": res.get('processo','-'), 
                "Partes": res.get('partes','-'), 
                "Peça Sugerida": res.get('peca_sugerida','-'), 
                "Responsável": resp, 
                "Vencimento": venc, 
                "Prioridade": res.get('prioridade','Média')
            }
            pd.DataFrame([nova_linha]).to_csv('prazos_gn.csv', mode='a', index=False, header=not os.path.exists('prazos_gn.csv'), sep=';', encoding='utf-8-sig')
            st.success("✅ Tática arquivada!")

st.divider()

# --- AGENDA E PDF ---
st.subheader("📋 Mapa de Prazos")
if os.path.exists('prazos_gn.csv'):
    dados = pd.read_csv('prazos_gn.csv', sep=';')
    st.dataframe(dados, use_container_width=True)
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🗑️ Limpar Agenda"):
            os.remove('prazos_gn.csv'); st.rerun()
    with col_b:
        pdf_bytes = gerar_relatorio_pdf(dados)
        if pdf_bytes:
            st.download_button(label="📥 BAIXAR RELATÓRIO PDF", data=pdf_bytes, file_name=f"Relatorio_GN_{datetime.date.today()}.pdf", mime="application/pdf")
else:
    st.info("Nenhum prazo pendente.")

st.sidebar.markdown(f"**Equipe:** {', '.join(PROFISSIONAIS)}")