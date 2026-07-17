# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import requests
from io import BytesIO

# Configuração da página Web para Celular
st.set_page_config(
    page_title="Sistema de Etiquetas", 
    page_icon="🏷️", 
    layout="centered"
)

# Estilização básica para o celular
st.markdown("""
    <style>
    .reportview-container { background: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; height: 50px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🏷️ Central de Etiquetas Automatizada")
st.write("Reinício diário automático às 07:00. Saldos calculados em tempo real.")

# =====================================================================
# ⚠️ ADICIONE O LINK DA SUA PLANILHA DO GOOGLE SHEETS AQUI EMBAIXO ⚠️
# =====================================================================
LINK_PLANILHA_GOOGLE = "https://frexcocombr.sharepoint.com/:x:/s/Operao-CD/IQAjqT14s-1FS51K4C11dBSoAUD9Adnw6SzxXVbCUV62xEc?e=LhWEMc"

# Inicializa o histórico de tudo o que já foi impresso para não repetir
if "historico_impresso" not in st.session_state:
    st.session_state.historico_impresso = {}

# Transforma o link normal do Google Sheets em um link de download direto do formato Excel
def obter_link_exportacao(link_original):
    if "docs.google.com/spreadsheets" in link_original:
        partes = link_original.split("/edit")
        return partes[0] + "/export?format=xlsx"
    return link_original

# 1. Carrega os dados direto da nuvem filtrando pelo turno atual (A partir das 07:00 de hoje)
def carregar_dados_online():
    if "COLE_AQUI" in LINK_PLANILHA_GOOGLE:
        st.warning("⚠️ Você precisa colar o link da sua planilha do Google Sheets na linha 27 do código do app.py.")
        return pd.DataFrame()
        
    try:
        url_excel = obter_link_exportacao(LINK_PLANILHA_GOOGLE)
        response = requests.get(url_excel)
        df = pd.read_excel(BytesIO(response.content))
        
        colunas_obrigatorias = ['Item', 'Lote', 'Contagem', 'Feitos']
        
        if all(col in df.columns for col in colunas_obrigatorias):
            # Identifica a coluna de data que o Google Forms cria automaticamente (geralmente é a primeira coluna)
            coluna_data = df.columns[0] 
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
            
            # Define o momento de corte: 07:00 da manhã do dia de HOJE
            agora = datetime.now()
            horario_corte = agora.replace(hour=7, minute=0, second=0, microsecond=0)
            
            # Se agora for antes das 07:00 (madrugada), o corte passa a ser as 07:00 do dia anterior
            if agora < horario_corte:
                horario_corte = horario_corte - timedelta(days=1)
                
            # 🔥 FILTRO MÁGICO: Ignora tudo o que foi enviado antes das 07:00 do turno atual
            df = df[df[coluna_data] >= horario_corte].copy()
            
            # Trata as colunas numéricas
            df['Contagem'] = pd.to_numeric(df['Contagem'], errors='coerce').fillna(0)
            df['Feitos'] = pd.to_numeric(df['Feitos'], errors='coerce').fillna(0)
            return df
        else:
            st.error(f"Sua planilha precisa ter as colunas: {colunas_obrigatorias}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha online: {e}")
        return pd.DataFrame()

# 2. Desenha a etiqueta física com o layout profissional
def gerar_etiqueta_professional(produto, total_etiqueta, lote, ja_impresso_antes):
    cor_azul = "#1F4E78"
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    conteudo_qr = (
        f"PROD: {produto}\n"
        f"LOTE: {lote}\n"
        f"QTD_ETIQUETA: {int(total_etiqueta)}\n"
        f"DATA: {data_atual}\n"
        f"SALDO_ANTERIOR_DESC: {int(ja_impresso_antes)}"
    )
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data(conteudo_qr)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").resize((240, 240))
    
    etiqueta = Image.new("RGB", (600, 320), "white")
    etiqueta.paste(img_qr, (25, 40))
    desenho = ImageDraw.Draw(etiqueta)
    
    try:
        font_setor = ImageFont.truetype("arial.ttf", 14)
        font_titulo = ImageFont.truetype("arial.ttf", 22)
        font_subtitulo = ImageFont.truetype("arial.ttf", 16)
        font_destaque = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font_setor = ImageFont.load_default()
        font_titulo = ImageFont.load_default()
        font_subtitulo = ImageFont.load_default()
        font_destaque = ImageFont.load_default()
        
    x_texto = 290
    desenho.line([(280, 30), (280, 290)], fill="#D3D3D3", width=2)
    
    desenho.rectangle([(x_texto, 25), (575, 50)], fill=cor_azul)
    desenho.text((x_texto + 10, 28), "PRODUÇÃO DIÁRIA (SALDO)", fill="white", font=font_setor)
    
    nome_produto = produto if len(produto) <= 20 else produto[:18] + "..."
    desenho.text((x_texto, 65), nome_produto, fill="black", font=font_titulo)
    
    if ja_impresso_antes > 0:
        desenho.text((x_texto, 105), f"Descontado anterior: {int(ja_impresso_antes)} un", fill="#C62828", font=font_subtitulo)
    else:
        desenho.text((x_texto, 105), "Primeira tiragem de hoje", fill="#2E7D32", font=font_subtitulo)
        
    total_formatado = f"{int(total_etiqueta):,}".replace(",", ".")
    desenho.text((x_texto, 135), f"{total_formatado} Unid.", fill=cor_azul, font=font_destaque)
    
    desenho.text((x_texto, 215), f"LOTE: {lote}", fill="black", font=font_subtitulo)
    desenho.text((x_texto, 245), f"GERADO EM: {data_atual}", fill="black", font=font_subtitulo)
    
    nome_arquivo = "temp_etiqueta.png"
    etiqueta.save(nome_arquivo)
    return nome_arquivo

# --- INTERFACE DO USUÁRIO NO CELULAR ---

df_completo = carregar_dados_online()

if df_completo.empty:
    st.success("🎉 Nenhuma resposta enviada no Forms a partir das 07:00 de hoje.")
    if st.button("🔄 Verificar se há novos envios"):
        st.rerun()
else:
    lista_produtos = sorted(df_completo['Item'].unique().tolist())
    produto_selecionado = st.selectbox("Selecione o Item:", [""] + lista_produtos)
    
    if produto_selecionado:
        dados_prod = df_completo[df_completo['Item'] == produto_selecionado]
        grupos = dados_prod.groupby(['Lote'])
        
        for lote, df_grupo in grupos:
            # Chave baseada na Data + Produto + Lote para reiniciar de um dia para o outro
            dia_atual_str = datetime.now().strftime("%Y-%m-%d")
            chave_produto_lote = f"{dia_atual_str}_{produto_selecionado}_{lote}"
            
            total_contagem_planilha = df_grupo['Contagem'].sum()
            total_feitos_planilha = df_grupo['Feitos'].sum()
            total_acumulado_geral = total_contagem_planilha + total_feitos_planilha
            
            ja_impresso_antes = st.session_state.historico_impresso.get(chave_produto_lote, 0)
            quantidade_nova_etiqueta = total_acumulado_geral - ja_impresso_antes
            
            if quantidade_nova_etiqueta <= 0:
                continue 
                
            st.markdown("---")
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader(f"{produto_selecionado}")
                st.write(f"**Lote:** {lote}")
                st.write(f"📊 Acumulado desde às 07h: {int(total_acumulado_geral)} un")
                if ja_impresso_antes > 0:
                    st.write(f"✅ Já tirou hoje: -{int(ja_impresso_antes)} un")
                
                st.metric("Líquido desta etiqueta", f"{int(quantidade_nova_etiqueta):,}".replace(",", ".") + " Unid.")
                
                caminho_imagem = gerar_etiqueta_professional(
                    produto_selecionado, quantidade_nova_etiqueta, lote, ja_impresso_antes
                )
                
                if st.button(f"✅ Dar Baixa nesta tiragem", key=f"btn_{lote}"):
                    st.session_state.historico_impresso[chave_produto_lote] = ja_impresso_antes + quantity_nova_etiqueta
                    st.success("Baixa realizada! Calculando próximo saldo.")
                    st.balloons()
                    import time
                    time.sleep(1.2)
                    st.rerun()
            
            with col2:
                st.image(caminho_imagem, caption="Etiqueta com Saldo do Turno", use_column_width=True)
                
                with open(caminho_imagem, "rb") as file:
                    st.download_button(
                        label="📥 Salvar Etiqueta",
                        data=file,
                        file_name=f"etiqueta_{produto_selecionado.replace(' ', '_')}.png",
                        mime="image/png",
                        key=f"dl_{lote}"
                    )
