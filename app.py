# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import qrcode
import socket  # Importante para enviar os dados direto para a impressora de rede
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import requests
from io import BytesIO

# Configuração da página Web para Celular
st.set_page_config(page_title="Sistema de Etiquetas", page_icon="🏷️", layout="centered")

st.title("🏷️ Central de Etiquetas Automatizada")
st.write("Reinício diário automático às 07:00. Impressão direta por IP ativa.")

# =====================================================================
# CONFIGURAÇÃO DE REDE DA IMPRESSORA ZEBRA
# =====================================================================
# ⚠️ ADICIONE AQUI O IP QUE SAIU NO PAPEL DA SUA IMPRESSORA ZEBRA:
IP_IMPRESSORA_ZEBRA = 192.168.1.21
PORTA_ZEBRA = 9100 # Porta padrão de rede para impressoras Zebra

LINK_PLANILHA_GOOGLE = "https://raw.githubusercontent.com/dummy/repo/main/planilha_teste_forms.xlsx"

if "historico_impresso" not in st.session_state:
    st.session_state.historico_impresso = {}

def enviar_comando_zebra_rede(produto, lote, quantidade):
    """ Envia a etiqueta no idioma nativo da Zebra (EPL/ZPL) direto pela rede """
    try:
        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Código ZPL profissional (linguagem que a Zebra entende direto na memória de rede)
        codigo_zpl = f"""
        ^XA
        ^CI28
        ^FO50,50^GB500,230,2^FS
        ^FO70,70^A0N,28,28^FDSALDO DE PRODUCAO^FS
        ^FO70,105^A0N,35,35^FD{produto}^FS
        ^FO70,150^A0N,45,45^FDQTD: {int(quantidade)} Unid.^FS
        ^FO70,205^A0N,22,22^FDLOTE: {lote}^FS
        ^FO70,235^A0N,20,20^FDDATA: {data_atual}^FS
        ^FO360,70^BQN,2,4^FDQA,PROD: {produto}, LOTE: {lote}, QTD: {int(quantidade)}^FS
        ^XZ
        """
        
        # Conecta na impressora via IP e joga o código lá dentro
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0) # Espera no máximo 3 segundos para não travar o celular
        s.connect((IP_IMPRESSORA_ZEBRA, PORTA_ZEBRA))
        s.sendall(codigo_zpl.encode('utf-8'))
        s.close()
        return True
    except Exception as e:
        st.error(f"Não consegui conectar na Zebra pelo IP {IP_IMPRESSORA_ZEBRA}. Verifique se o Wi-Fi do celular está ligado na mesma rede da impressora.")
        return False

# (Restante do seu código padrão de processamento de dados...)
def obter_link_exportacao(link_original):
    if "docs.google.com/spreadsheets" in link_original:
        if "/pub" in link_original: return link_original
        return link_original.split("/edit")[0] + "/export?format=xlsx"
    return link_original

def carregar_dados_online():
    try:
        data_atual = datetime.now()
        df = pd.DataFrame({
            "Carimbo de data/hora": [data_atual, data_atual],
            "Item": ["Produto Teste A", "Produto Teste B"],
            "Lote": ["LOTE2026", "LOTE999"],
            "Contagem": [100, 0],
            "Feitos": [20, 50]
        })
        return df
    except:
        return pd.DataFrame()

df_completo = carregar_dados_online()

if not df_completo.empty:
    lista_produtos = sorted(df_completo['Item'].unique().tolist())
    produto_selecionado = st.selectbox("Selecione o Item:", [""] + lista_produtos)
    
    if produto_selecionado:
        dados_prod = df_completo[df_completo['Item'] == produto_selecionado]
        grupos = dados_prod.groupby(['Lote'])
        
        for lote, df_grupo in grupos:
            dia_atual_str = datetime.now().strftime("%Y-%m-%d")
            chave_produto_lote = f"{dia_atual_str}_{produto_selecionado}_{lote}"
            
            total_acumulado_geral = df_grupo['Contagem'].sum() + df_grupo['Feitos'].sum()
            ja_impresso_antes = st.session_state.historico_impresso.get(chave_produto_lote, 0)
            quantidade_nova_etiqueta = total_acumulado_geral - ja_impresso_antes
            
            if quantidade_nova_etiqueta <= 0: continue 
                
            st.markdown("---")
            st.subheader(f"{produto_selecionado} - Lote: {lote}")
            st.metric("Quantidade a imprimir", f"{int(quantidade_nova_etiqueta)} Unid.")
            
            # 🚀 NOVO BOTÃO DE IMPRESSÃO DIRETA
            if st.button(f"🖨️ Enviar direto para a Zebra", key=f"print_{lote}"):
                sucesso = enviar_comando_zebra_rede(produto_selecionado, lote, quantidade_nova_etiqueta)
                if sucesso:
                    st.session_state.historico_impresso[chave_produto_lote] = ja_impresso_antes + quantidade_nova_etiqueta
                    st.success("🔥 Comando enviado! A Zebra vai cuspir a etiqueta agora.")
                    st.rerun()
