import streamlit as st
import datetime
import json
import pypdf
import pandas as pd
import os
from openai import OpenAI
from fpdf import FPDF

# --- 👥 CONFIGURAÇÃO DA EQUIPE G&N ---
# Adicione ou remova nomes conforme a necessidade do escritório
PROFISSIONAIS = ["Dr. Carlyle", "Dra. Jaqueline"]

# --- ⚙️ CONFIGURAÇÕES E INICIALIZAÇÃO ---
client = None
try:
    if "OPENAI_KEY" in st.secrets:
        client = OpenAI(api_key=st.secrets["OPENAI_KEY"].strip())
    else:
        st.error("❌ Chave OpenAI não encontrada.")
except Exception as e:
    st.error(f"⚠️ Erro: {e}")

# --- ⚖️ LÓGICA DE DISTRIBUIÇÃO POR IGUAL (LOAD BALANCING) ---
def definir_responsavel_automatico():
    if not os.path.exists('prazos_gn.csv'):
        return PROFISSIONAIS[0]
    
    df_atual = pd.read_csv('prazos_gn.csv', sep=';')
    
    # Se a coluna de responsável ainda não existir na agenda antiga
    if 'Responsável' not in df_atual.columns:
        return PROFISSIONAIS[0]
    
    # Conta quantas tarefas cada um possui na lista
    contagem = df_atual['Responsável'].value_counts().to_dict()
    
    # Garante que todos da equipe entrem na conta, mesmo com zero tarefas
    for p in PROFISSIONAIS:
        if p not in contagem:
            contagem[p] = 0
            
    # Retorna o profissional que tem o menor número de prazos atribuídos
    # Em caso de empate, o Python retorna o primeiro que encontrar
    return min(contagem, key=contagem.get)

# --- 📄 FUNÇÃO PARA GERAR O PDF COM COLUNA DE RESPONSÁVEL ---
def gerar_relatorio_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(190, 10, "GUALBERTO & NEGREIROS SOCIEDADE DE ADVOGADOS", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Mapa de Distribuicao de Prazos - Gerado em {datetime.date.today().strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(26, 58, 90) # Azul G&N
    pdf.set_text_color(255, 255, 255)
    
    # Cabeçalho da Tabela
    pdf.cell(35, 10, "Processo", border=1, fill=True)
    pdf.cell(45, 10, "Partes", border=1, fill=True)
    pdf.cell(40, 10, "Peca", border=1, fill=True)
    pdf.cell(30, 10, "Responsavel", border=1, fill=True)
    pdf.cell(30, 10, "Vencimento", border=1, fill=True)
    pdf.ln()
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 8)
    
    for _, row in df.iterrows():
        pdf.cell(35, 10, str(row['Processo'])[:15], border=1)
        pdf.cell(45, 10, str(row['Partes'])[:20], border=1)
        pdf.cell(40, 10, str(row['Peça Sugerida'])[:18], border=1)
        pdf.cell(30, 10, str(row.get('Responsável', 'N/A')), border=1)
        pdf.cell(30, 10, str(row['Vencimento']), border=1)
        pdf.ln()
        
    return pdf.output(dest='S')

# --- MOTOR DE CÁLCULO E IA ---
def eh_feriado_ou_fds(data):
    feriados = [(1,1),(13,6),(7,9),(30,9),(3,10),(12,10),(2,11),(15,11),(13,12),(25,12)]
    return data.weekday() >= 5 or (data.day, data.month) in feriados

def calcular_vencimento(dias):
    data = datetime.date.today()
    cont = 0
    try: d = int(dias)
    except: d = 15
    while cont < d:
        data += datetime.timedelta(days=1)
        if not eh_feriado_ou_fds(data): cont += 1
    return data

def analisar_documento_co_piloto(texto):
    if client is None: return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Consultor G&N Mossoro/RN. Extraia dados em JSON."},
                {"role": "user", "content": f"Analise e retorne JSON: {{'processo':'','partes':'','tipo_doc':'','peca_principal_sugerida':'','prazo':15,'resumo':'','parecer_risco':'','rascunho_estrutura':'','sugestoes_alternativas':[],'prioridade':''}}. Texto: {texto[:12000]}"}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Erro na análise: {e}")
        return None

# --- 🏛️ INTERFACE ---
st.set_page_config(page_title="GN - Gestão de Equipe", page_icon="🏛️", layout="wide")
st.title("🏛️ G&N Intelligence: Co-piloto & Gestão de Prazos")

c_in, c_out = st.columns([1, 1.2], gap="large")

with c_in:
    st.subheader("📥 Entrada de Documentos")
    pdf_input = st.file_uploader("PDF:", type="pdf")
    txt_input = st.text_area("Texto:", height=150)
    
    if st.button("🚀 GERAR ESTRUTURA E DISTRIBUIR"):
        raw = ""
        if pdf_input: raw = "".join([p.extract_text() for p in pypdf.PdfReader(pdf_input).pages])
        elif txt_input: raw = txt_input
            
        if raw:
            with st.spinner("Analisando e calculando distribuição..."):
                res = analisar_documento_co_piloto(raw)
                if res:
                    st.session_state['res_gn'] = res
                    st.session_state['venc_gn'] = calcular_vencimento(res['prazo'])
                    # Define quem vai cumprir o prazo neste momento
                    st.session_state['resp_gn'] = definir_responsavel_automatico()

with c_out:
    if 'res_gn' in st.session_state:
        res = st.session_state['res_gn']
        venc = st.session_state['venc_gn'].strftime('%d/%m/%Y')
        resp = st.session_state['resp_gn']
        
        st.subheader("📑 Diagnóstico e Atribuição")
        st.warning(f"⚖️ **Responsável Sugerido:** {resp} (Menor carga de trabalho)")
        st.write(f"**Proc:** `{res['processo']}` | **Partes:** `{res['partes']}`")
        
        with st.expander("📝 PARECER DE RISCO", expanded=True):
            st.info(res['parecer_risco'])
        
        st.text_area("Esqueleto da Defesa:", value=res['rascunho_estrutura'], height=200)
        
        if st.button("📥 CONFIRMAR E SALVAR NA AGENDA"):
            nova_linha = {
                "Data": datetime.date.today().strftime('%d/%m/%Y'), 
                "Processo": res['processo'], 
                "Partes": res['partes'], 
                "Peça Sugerida": res['peca_principal_sugerida'], 
                "Responsável": resp, # Salva o nome sugerido
                "Vencimento": venc, 
                "Prioridade": res['prioridade']
            }
            pd.DataFrame([nova_linha]).to_csv('prazos_gn.csv', mode='a', index=False, header=not os.path.exists('prazos_gn.csv'), sep=';', encoding='utf-8-sig')
            st.success(f"✅ Salvo! Tarefa atribuída ao {resp}.")

st.divider()

# --- AGENDA E RELATÓRIO PDF ---
st.subheader("📋 Mapa de Prazos do Escritório")
if os.path.exists('prazos_gn.csv'):
    dados = pd.read_csv('prazos_gn.csv', sep=';')
    st.dataframe(dados, use_container_width=True)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ Limpar Agenda"):
            os.remove('prazos_gn.csv'); st.rerun()
            
    with col2:
        pdf_data = gerar_relatorio_pdf(dados)
        st.download_button(
            label="📥 BAIXAR RELATÓRIO DE DISTRIBUIÇÃO (PDF)",
            data=pdf_data,
            file_name=f"Mapa_Prazos_GN_{datetime.date.today()}.pdf",
            mime="application/pdf",
        )
else:
    st.info("Nenhum prazo pendente.")

st.sidebar.markdown(f"**Escritório:** G&N Advogados\n\n**Equipe:** {', '.join(PROFISSIONAIS)}")