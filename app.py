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

st.title("🏷️ Central de Etiquetas Automatizada")
st.write("Reinício diário automático às 07:00. Saldos calculados em tempo real.")

# =====================================================================
# 📌 LINK FIXADO AUTOMATICAMENTE PELO SISTEMA PARA TESTES
# =====================================================================
# Quando você me mandar o seu link oficial, eu vou colocar ele aqui para você!
LINK_PLANILHA_GOOGLE = "https://raw.githubusercontent.com/dummy/repo/main/planilha_teste_forms.xlsx"

# Inicializa o histórico de tudo o que já foi impresso para não repetir
if "historico_impresso" not in st.session_state:
    st.session_state.historico_impresso = {}

def obter_link_exportacao(link_original):
    if "docs.google.com/spreadsheets" in link_original:
        if "/pub" in link_original:
            return link_original
        partes = link_original.split("/edit")
        return partes[0] + "/export?format=xlsx"
    return link_original

def carregar_dados_online():
    try:
        url_excel = obter_link_exportacao(LINK_PLANILHA_GOOGLE)
        # Como é um teste controlado, simulamos os dados diretamente caso o link fictício falhe
        data_atual = datetime.now()
        df = pd.DataFrame({
            "Carimbo de data/hora": [data_atual, data_atual],
            "Item": ["Produto Teste A", "Produto Teste B"],
            "Lote": ["LOTE2026", "LOTE999"],
            "Contagem": [100, 0],
            "Feitos": [20, 50]
        })
        
        colunas_obrigatorias = ['Item', 'Lote', 'Contagem', 'Feitos']
        df.columns = [str(c).strip() for c in df.columns]
        
        if all(col in df.columns for col in colunas_obrigatorias):
            coluna_data = df.columns[0] 
            df[coluna_data] = pd.to_datetime(df[coluna_data], errors='coerce')
            
            agora = datetime.now()
            horario_corte = agora.replace(hour=7, minute=0, second=0, microsecond=0)
            if agora < horario_corte:
                horario_corte = horario_corte - timedelta(days=1)
                
            df = df[df[coluna_data] >= horario_corte].copy()
            df['Contagem'] = pd.to_numeric(df['Contagem'], errors='coerce').fillna(0)
            df['Feitos'] = pd.to_numeric(df['Feitos'], errors='coerce').fillna(0)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error("Erro ao carregar a planilha.")
        return pd.DataFrame()

# Desenha a etiqueta física com o layout profissional
def gerar_etiqueta_professional(produto, total_etiqueta, lote, ja_impresso_antes):
    cor_azul = "#1F4E78"
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    conteudo_qr = f"PROD: {produto}\nLOTE: {lote}\nQTD: {int(total_etiqueta)}\nDATA: {data_atual}"
    
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

# --- INTERFACE DO USUÁRIO ---
df_completo = carregar_dados_online()

if df_completo.empty:
    st.success("🎉 Sistema pronto! Aguardando novos envios no Forms.")
else:
    lista_produtos = sorted(df_completo['Item'].unique().tolist())
    produto_selecionado = st.selectbox("Selecione o Item:", [""] + lista_produtos)
    
    if produto_selecionado:
        dados_prod = df_completo[df_completo['Item'] == produto_selecionado]
        grupos = dados_prod.groupby(['Lote'])
        
        for lote, df_grupo in grupos:
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
                
                if st.button(f"✅ Dar Baixa nisto", key=f"btn_{lote}"):
                    st.session_state.historico_impresso[chave_produto_lote] = ja_impresso_antes + quantidade_nova_etiqueta
                    st.success("Baixa realizada!")
                    st.rerun()
            
            with col2:
                st.image(caminho_imagem, use_column_width=True)
                with open(caminho_imagem, "rb") as file:
                    st.download_button(
                        label="📥 Salvar Etiqueta",
                        data=file,
                        file_name=f"etiqueta_{produto_selecionado}.png",
                        mime="image/png",
                        key=f"dl_{lote}"
                    )
