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
    page_title="Vertex Mobility v6.9.2", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: V6.9.2 REFINED CARDS & PASTEL ACTION ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --pastel-red: rgba(255, 107, 107, 0.2);
        --pastel-red-hover: rgba(255, 107, 107, 0.3);
        --text-red: #e63946;
        --bg: #fdfdfe;
        --text-dark: #0f172a;
        --text-light: #64748b;
        --radius: 20px;
    }

    /* TIPOGRAFÍA GLOBAL EN FORMATO TITULO */
    * { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        text-transform: capitalize !important; 
    }

    .stApp { background-color: var(--bg); }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 1.5rem !important; 
        padding-left: 5% !important;
        padding-right: 5% !important;
    }

    /* Branding - Tamaño corregido */
    .brand-title {
        font-weight: 800;
        font-size: 2.2rem !important;
        color: var(--text-dark);
        letter-spacing: -2px;
        text-transform: uppercase !important;
    }
    .brand-subtitle {
        font-weight: 600;
        font-size: 0.75rem !important;
        color: var(--text-light);
        text-transform: uppercase !important; /* El subtítulo se ve mejor en Caps de marca */
    }

    /* Barra de Búsqueda Normal */
    .stTextInput input {
        height: 50px !important;
        border-radius: 12px !important;
        background-color: #f1f5f9 !important;
        border: none !important;
    }

    /* Productos: REVERTIDOS A TAMAÑO COMPLETO */
    div[data-testid="column"] button {
        height: 140px !important;
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: var(--radius) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
        padding: 1rem !important;
    }
    div[data-testid="column"] button:active { transform: scale(0.96); }

    /* --- CARRITO SIN SCROLL AJUSTADO --- */
    .ticket-header {
        font-size: 0.7rem;
        font-weight: 800;
        color: var(--text-light);
        border-bottom: 2px solid #f1f5f9;
        margin-bottom: 10px;
    }

    /* BOTÓN CONFIRMAR VENTA: ROJO TRASLUCIDO / PASTEL */
    div.stButton > button[kind="primary"] {
        background-color: var(--pastel-red) !important;
        color: var(--text-red) !important;
        border: 1px solid rgba(230, 57, 70, 0.2) !important;
        font-weight: 800 !important;
        box-shadow: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: var(--pastel-red-hover) !important;
        border: 1px solid rgba(230, 57, 70, 0.4) !important;
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

# --- HEADER ---
c_log, c_ver, c_d = st.columns([1.5, 3.5, 1])
with c_log: st.markdown('<div class="brand-title">Vertex</div>', unsafe_allow_html=True)
with c_ver: 
    st.markdown('<div style="padding-top:16px;"><span style="background:#eff6ff; color:#3b82f6; padding:4px 12px; border-radius:30px; font-size:0.7rem; font-weight:800; border:1px solid #dbeafe;">Versión 6.9.2</span></div>', unsafe_allow_html=True)
with c_d:
    if st.button("Dashboard"): show_dashboard_dialog()
st.markdown('<div class="brand-subtitle">Movilidad E Inteligencia De Negocio</div>', unsafe_allow_html=True)

# --- VISTA PRINCIPAL ---
col_main, col_side = st.columns([2.8, 1.2], gap="large")

with col_main:
    search = st.text_input("Buscar...", placeholder="Escribe O Escanea", label_visibility="collapsed")
    df_p = get_data("products")
    if not df_p.empty:
        df_view = df_p[df_p['name'].str.contains(search, case=False)].head(20) if search else df_p.head(20)
        n_cols = 4
        for i in range(0, len(df_view), n_cols):
            cols = st.columns(n_cols)
            for j in range(n_cols):
                if i + j < len(df_view):
                    p = df_view.iloc[i + j]
                    with cols[j]:
                        lbl = f"{p['name']}\n\n${p['price']:,.2f}"
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
    # CLIENTE
    with st.container(border=True):
        st.markdown("**Cliente Actual**")
        st.markdown(f"### {st.session_state.selected_client}")
        if st.button("Buscar Cliente", use_container_width=True): show_client_dialog()

    st.write(" ")
    
    # CARRITO (Ajustado para quepar sin scroll pero respetando tamaños)
    with st.container(border=True):
        st.markdown("### Carrito")
        
        th1, th2, th3, th4 = st.columns([0.6, 2.5, 1.2, 1.2])
        th1.markdown('<div class="ticket-header">Cant</div>', unsafe_allow_html=True)
        th2.markdown('<div class="ticket-header">Artículos</div>', unsafe_allow_html=True)
        th3.markdown('<div class="ticket-header">Precio</div>', unsafe_allow_html=True)
        th4.markdown('<div class="ticket-header" style="text-align:right;">Total</div>', unsafe_allow_html=True)
        
        running_total = 0
        current_items = st.session_state.cart
        for i in range(4): # 4 filas compactas
            t1, t2, t3, t4 = st.columns([0.6, 2.5, 1.2, 1.2])
            if i < len(current_items):
                item = current_items[i]
                sub = item['price'] * item['qty']
                running_total += sub
                t1.write(item['qty'])
                t2.write(item['name'][:18])
                t3.write(f"${item['price']:,.0f}")
                t4.markdown(f"<p style='text-align:right;'>${sub:,.0f}</p>", unsafe_allow_html=True)
            else:
                t1.write(" ")

        st.divider()
        f1, f2 = st.columns([1, 1])
        f1.markdown("**Total Neto**")
        f2.markdown(f"<h3 style='text-align:right; color:#6366f1; margin:0;'>${running_total:,.2f}</h3>", unsafe_allow_html=True)
        
        if st.button("Confirmar Venta", type="primary", use_container_width=True):
            if running_total > 0:
                st.session_state.cart = []
                st.rerun()
        
        if st.button("Vaciar", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
