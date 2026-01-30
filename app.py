import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
import json
import numpy as np
from datetime import datetime, timedelta

# --- UTILIDADES DE DATOS ---
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)): return int(obj)
        if isinstance(obj, (np.floating, np.float64)): return float(obj)
        if isinstance(obj, (np.ndarray, list)): return [self.default(i) for i in obj]
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        if hasattr(obj, 'item'): return obj.item()
        return super(NpEncoder, self).default(obj)

def purify_payload(data):
    try:
        return json.loads(json.dumps(data, cls=NpEncoder))
    except Exception as e:
        return data

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Vertex Mobility v6.9.1", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: V6.9.1 NO-SCROLL & TITLE CASE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --bg: #fdfdfe;
        --text-dark: #0f172a;
        --text-light: #64748b;
        --radius: 18px;
    }

    /* TIPOGRAFÍA GLOBAL EN FORMATO TITULO */
    * { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        text-transform: capitalize !important; 
    }

    .stApp { 
        background-color: var(--bg); 
        overflow: hidden !important; /* Evitar scroll global */
    }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 1rem !important; 
        padding-left: 3% !important;
        padding-right: 3% !important;
        height: 100vh !important;
    }

    /* Branding - Ajuste de tamaño para ganar espacio vertical */
    .brand-title {
        font-weight: 800;
        font-size: 1.8rem !important;
        color: var(--text-dark);
        letter-spacing: -1.5px;
        text-transform: uppercase !important; /* Vertex se mantiene en Caps por marca */
    }
    .brand-subtitle {
        font-weight: 600;
        font-size: 0.7rem !important;
        color: var(--text-light);
        letter-spacing: 1px;
    }

    /* Barra de Búsqueda Compacta */
    .stTextInput input {
        height: 40px !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
    }

    /* Productos Compactos para que quepan */
    div[data-testid="column"] button {
        height: 110px !important;
        padding: 0.5rem !important;
        font-size: 0.85rem !important;
    }

    /* --- CARRITO SIN SCROLL --- */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 10px !important;
    }

    .ticket-header {
        font-size: 0.65rem;
        font-weight: 800;
        color: var(--text-light);
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 5px;
    }

    .ticket-row {
        font-size: 0.8rem;
        padding: 4px 0;
        border-bottom: 1px solid #f8fafc;
        display: flex;
        align-items: center;
    }

    .ticket-footer {
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid #f1f5f9;
    }

    .ticket-total-value { 
        font-weight: 800; 
        font-size: 1.2rem !important; 
        color: var(--primary); 
    }

    /* Forzar que el botón de confirmar sea corto */
    .stButton > button {
        height: 40px !important;
        font-size: 0.9rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = get_supabase()

# --- ESTADO DE SESIÓN ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'selected_client' not in st.session_state: st.session_state.selected_client = "Mostrador"

# Cachear datos
@st.cache_data(ttl=30)
def get_data(table):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- DIALOGS ---
@st.dialog("Dashboard")
def show_dashboard_dialog():
    st.markdown("### Análisis De Ventas")
    if st.button("Cerrar"): st.rerun()

@st.dialog("Clientes")
def show_client_dialog():
    st.markdown("### Seleccionar Cliente")
    df_c = get_data("customers")
    options = ["Mostrador"] + (df_c['name'].tolist() if not df_c.empty else [])
    sel = st.selectbox("Elegir Cliente:", options)
    if st.button("Confirmar"):
        st.session_state.selected_client = sel
        st.rerun()

# --- HEADER COMPACTO ---
c_log, c_ver, c_d = st.columns([1.5, 3.5, 1])
with c_log: st.markdown('<div class="brand-title">Vertex</div>', unsafe_allow_html=True)
with c_ver: 
    st.markdown('<div style="padding-top:10px;"><span style="background:#eff6ff; color:#3b82f6; padding:2px 8px; border-radius:20px; font-size:0.6rem; font-weight:800; border:1px solid #dbeafe;">Versión 6.9.1</span></div>', unsafe_allow_html=True)
with c_d:
    if st.button("Dashboard"): show_dashboard_dialog()
st.markdown('<div class="brand-subtitle">Movilidad E Inteligencia De Negocio</div>', unsafe_allow_html=True)

# --- VISTA PRINCIPAL (Ajustada para No-Scroll) ---
col_main, col_side = st.columns([2.8, 1.2], gap="small")

with col_main:
    search = st.text_input("Buscar...", placeholder="Escribe O Escanea", label_visibility="collapsed")
    df_p = get_data("products")
    if not df_p.empty:
        # Reducimos a head(12) para que quepa en una sola pantalla verticalmente
        df_view = df_p[df_p['name'].str.contains(search, case=False)].head(12) if search else df_p.head(12)
        n_cols = 4
        for i in range(0, len(df_view), n_cols):
            cols = st.columns(n_cols)
            for j in range(n_cols):
                if i + j < len(df_view):
                    p = df_view.iloc[i + j]
                    with cols[j]:
                        lbl = f"{p['name'][:25]}\n\n${p['price']:,.2f}"
                        if st.button(lbl, key=f"p_{p['id']}", use_container_width=True):
                            found = False
                            for item in st.session_state.cart:
                                if item['id'] == p['id']:
                                    item['qty'] += 1
                                    found = True
                                    break
                            if not found:
                                st.session_state.cart.append({"id": p['id'], "name": p['name'], "price": float(p['price']), "qty": 1})
                            st.rerun()

with col_side:
    # CLIENTE COMPACTO
    with st.container(border=True):
        st.markdown("**Cliente Actual**")
        st.markdown(f"**{st.session_state.selected_client}**")
        if st.button("Buscar Cliente", use_container_width=True): show_client_dialog()

    # CARRITO SIN SCROLL
    with st.container(border=True):
        st.markdown("### Carrito")
        
        # Header de la tabla (Súper compacto)
        th1, th2, th3, th4 = st.columns([0.6, 2.5, 1.2, 1.2])
        th1.markdown('<div class="ticket-header">Cant</div>', unsafe_allow_html=True)
        th2.markdown('<div class="ticket-header">Artículos</div>', unsafe_allow_html=True)
        th3.markdown('<div class="ticket-header">Precio</div>', unsafe_allow_html=True)
        th4.markdown('<div class="ticket-header" style="text-align:right;">Total</div>', unsafe_allow_html=True)
        
        running_total = 0
        total_items = len(st.session_state.cart)
        # Mostramos 4 filas fijas para asegurar que quepa en pantalla sin scroll
        for i in range(4):
            tr1, tr2, tr3, tr4 = st.columns([0.6, 2.5, 1.2, 1.2])
            if i < total_items:
                item = st.session_state.cart[i]
                sub = item['price'] * item['qty']
                running_total += sub
                tr1.markdown(f"<div style='font-size:0.75rem;'>{item['qty']}</div>", unsafe_allow_html=True)
                tr2.markdown(f"<div style='font-size:0.75rem;'>{item['name'][:15]}</div>", unsafe_allow_html=True)
                tr3.markdown(f"<div style='font-size:0.75rem;'>${item['price']:,.0f}</div>", unsafe_allow_html=True)
                tr4.markdown(f"<div style='font-size:0.75rem; text-align:right;'>${sub:,.0f}</div>", unsafe_allow_html=True)
            else:
                tr1.markdown('<div style="color:#f8fafc;">.</div>', unsafe_allow_html=True)

        # Totales compactos
        st.markdown('<div class="ticket-footer"></div>', unsafe_allow_html=True)
        f1, f2 = st.columns([1, 1])
        f1.markdown('<div style="font-size:0.8rem;">Total Neto</div>', unsafe_allow_html=True)
        f2.markdown(f'<div class="ticket-total-value" style="text-align:right;">${running_total:,.2f}</div>', unsafe_allow_html=True)
        
        if st.button("Confirmar Venta", type="primary", use_container_width=True):
            if running_total > 0:
                st.session_state.cart = []
                st.rerun()
        
        if st.button("Vaciar", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
