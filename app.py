python
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

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

st.title("🏷️ Central de Etiquetas de Produção")
st.write("Selecione o produto para consolidar o que foi produzido e gerar a etiqueta.")

# Definição dos Setores e seus respectivos arquivos Excel
ARQUIVOS_SETORES = {
    "estoque_seco.xlsx": "Estoque Seco",
    "packing.xlsx": "Packing",
    "camara_fria.xlsx": "Câmara Fria",
    "folhosas.xlsx": "Folhosas"
}

# 1. Garante que as planilhas existam e tenham todas as colunas necessárias
def inicializar_planilhas_se_necessario():
    for nome_arquivo, nome_setor in ARQUIVOS_SETORES.items():
        if not os.path.exists(nome_arquivo):
            df_modelo = pd.DataFrame(columns=["Produto", "Quantidade", "Lote", "Tipo", "Status"])
            df_modelo.loc[0] = ["Exemplo de Produto", 100, "LOTE-01", "Contagem", "Pendente"]
            df_modelo.to_excel(nome_arquivo, index=False)
        else:
            try:
                df = pd.read_excel(nome_arquivo)
                alterado = False
                if "Status" not in df.columns:
                    df["Status"] = "Pendente"
                    alterado = True
                if "Tipo" not in df.columns:
                    df["Tipo"] = "Produção"
                    alterado = True
                if alterado:
                    df.to_excel(nome_arquivo, index=False)
            except Exception as e:
                st.error(f"Erro ao ler/configurar o arquivo {nome_arquivo}: {e}")

inicializar_planilhas_se_necessario()

# 2. Carrega apenas as linhas marcadas como "Pendente"
def carregar_producao_pendente():
    todos_dados = []
    for nome_arquivo, nome_setor in ARQUIVOS_SETORES.items():
        if os.path.exists(nome_arquivo):
            try:
                df = pd.read_excel(nome_arquivo)
                if all(col in df.columns for col in ['Produto', 'Quantidade', 'Lote']):
                    df['Status'] = df['Status'].fillna("Pendente").astype(str)
                    df['Tipo'] = df['Tipo'].fillna("Produção").astype(str)
                    
                    df_pendente = df[df['Status'].str.strip() == "Pendente"].copy()
                    
                    if not df_pendente.empty:
                        df_pendente['Quantidade'] = pd.to_numeric(df_pendente['Quantidade'], errors='coerce').fillna(0)
                        df_pendente['Setor'] = nome_setor
                        df_pendente['Origem_Arquivo'] = nome_arquivo
                        todos_dados.append(df_pendente)
            except Exception as e:
                st.error(f"Erro ao ler {nome_arquivo}: {e}")
                
    if not todos_dados:
        return pd.DataFrame(columns=['Produto', 'Lote', 'Quantidade', 'Setor', 'Origem_Arquivo', 'Status', 'Tipo'])
        
    return pd.concat(todos_dados, ignore_index=True)

# 3. Função para dar baixa das linhas etiquetadas na planilha correspondente
def dar_baixa_na_planilha(produto, lote, arquivo_origem):
    try:
        df = pd.read_excel(arquivo_origem)
        df['Status'] = df['Status'].fillna("Pendente").astype(str)
        
        horario_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        condicao = (df['Produto'] == produto) & (df['Lote'] == lote) & (df['Status'].str.strip() == "Pendente")
        
        df.loc[condicao, 'Status'] = f"Impresso em {horario_atual}"
        df.to_excel(arquivo_origem, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status na planilha: {e}")
        return False

# 4. Cria o visual profissional da etiqueta com cores por Setor
def gerar_etiqueta_professional(produto, quantidade, lote, setor, contem_contagem):
    cores_setores = {
        "Estoque Seco": "#8B5A2B",    # Marrom
        "Packing": "#1F4E78",         # Azul
        "Câmara Fria": "#009688",      # Ciano/Verde Água
        "Folhosas": "#2E7D32"         # Verde Folha
    }
    cor_setor = cores_setores.get(setor, "#333333")
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    status_contagem = "SIM" if contem_contagem else "NAO"
    conteudo_qr = f"SETOR: {setor}\nPROD: {produto}\nQTD: {int(quantidade)}\nLOTE: {lote}\nDATA: {data_atual}\nCONTAGEM: {status_contagem}"
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=1)
    qr.add_data(conteudo_qr)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").resize((240, 240))
    
    etiqueta = Image.new("R
