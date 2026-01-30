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
    page_title="Vertex Mobility v7.0", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: V7.0 COMPACT ELITE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@200;300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --pastel-red: rgba(255, 107, 107, 0.12);
        --text-red: #e63946;
        --bg: #fdfdfe;
        --text-dark: #1e293b;
        --text-light: #64748b;
    }

    /* TIPOGRAFÍA GLOBAL */
    * { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        text-transform: capitalize !important; 
    }

    .stApp { background-color: var(--bg); }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 1rem !important; 
        padding-left: 5% !important;
        padding-right: 5% !important;
    }

    /* Branding */
    .brand-title {
        font-weight: 800;
        font-size: 2rem !important;
        color: var(--text-dark);
        letter-spacing: -2px;
        text-transform: uppercase !important;
    }
    .version-badge {
        background: #eff6ff;
        color: #3b82f6;
        padding: 3px 12px;
        border-radius: 30px;
        font-size: 0.65rem;
        font-weight: 800;
        border: 1px solid #dbeafe;
        margin-left: 10px;
        display: inline-block;
        vertical-align: middle;
    }

    /* FIX: CABECERAS DEL CARRITO MÁS DELGADAS */
    .ticket-header {
        font-size: 0.6rem !important;
        font-weight: 400 !important; /* Fuente más delgada */
        color: var(--text-light);
        border-bottom: 2px solid #f1f5f9;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }

    /* FIX: ARTÍCULOS EN EL CARRITO (TEXTO REDUCIDO) */
    .ticket-item-text {
        font-size: 0.75rem !important; /* Tamaño reducido */
        font-weight: 400 !important;
        line-height: 1.2 !important;
        color: var(--text-dark);
    }

    /* Reducir espacio entre elementos de Streamlit en el panel lateral */
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 12px !important;
    }
    
    /* Búsqueda */
    .stTextInput input {
        height: 45px !important;
        border-radius: 12px !important;
        background-color: #f1f5f9 !important;
    }

    /* Productos */
    div[data-testid="column"] button {
        height: 140px !important;
        background: white !important;
        border-radius: 20px !important;
    }

    /* Botón Confirmar Pastel */
    div.stButton > button[kind="primary"] {
        background-color: var(--pastel-red) !important;
        color: var(--text-red) !important;
        height: 40px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        border: none !important;
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

# --- HEADER v7.0 ---
col_ha, col_hb = st.columns([5, 1])
with col_ha:
    st.markdown(f"""
        <div style="display: flex; align-items: baseline;">
            <div class="brand-title">Vertex</div>
            <div class="version-badge">Versión 7.0</div>
        </div>
        <div style="font-size:0.7rem; color:var(--text-light); text-transform:uppercase;">Movilidad E Inteligencia De Negocio</div>
    """, unsafe_allow_html=True)
with col_hb:
    if st.button("Dashboard", use_container_width=True): show_dashboard_dialog()

st.write(" ")

# --- PANEL POS ---
col_m, col_s = st.columns([2.8, 1.2], gap="large")

with col_m:
    search = st.text_input("buscar...", placeholder="escribe o escanea", label_visibility="collapsed")
    df_p = get_data("products")
    if not df_p.empty:
        df_view = df_p[df_p['name'].str.contains(search, case=False)].head(16) if search else df_p.head(16)
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

with col_s:
    # CLIENTE ACTUAL (Compacto)
    with st.container(border=True):
        st.markdown("<p style='font-size:0.7rem; margin:0;'>Cliente Actual</p>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='margin:0;'>{st.session_state.selected_client}</h4>", unsafe_allow_html=True)
        if st.button("Buscar Cliente", use_container_width=True): show_client_dialog()

    st.write(" ")
    
    # CARRITO (NUEVA V7.0 ULTRA COMPRESS)
    with st.container(border=True):
        st.markdown("<h4 style='margin:0 0 10px 0;'>Carrito</h4>", unsafe_allow_html=True)
        
        # Header ultra delgado
        th1, th2, th3, th4 = st.columns([0.6, 2.5, 1, 1])
        th1.markdown('<div class="ticket-header">Cant</div>', unsafe_allow_html=True)
        th2.markdown('<div class="ticket-header">Productos</div>', unsafe_allow_html=True)
        th3.markdown('<div class="ticket-header">Precio</div>', unsafe_allow_html=True)
        th4.markdown('<div class="ticket-header" style="text-align:right;">Total</div>', unsafe_allow_html=True)
        
        total = 0
        current_cart = st.session_state.cart
        
        # Bucle de items compacto
        for it in current_cart:
            sub = it['price'] * it['qty']
            total += sub
            r1, r2, r3, r4 = st.columns([0.6, 2.5, 1, 1])
            r1.markdown(f'<div class="ticket-item-text">{it["qty"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="ticket-item-text">{it["name"][:20]}</div>', unsafe_allow_html=True)
            r3.markdown(f'<div class="ticket-item-text">${it["price"]:,.0f}</div>', unsafe_allow_html=True)
            r4.markdown(f'<div class="ticket-item-text" style="text-align:right;">${sub:,.0f}</div>', unsafe_allow_html=True)
        
        # Llenado dinámico solo si hay espacio, para evitar scroll
        if len(current_cart) == 0:
            st.markdown("<p style='font-size:0.7rem; color:#cbd5e1; text-align:center;'>Vacío</p>", unsafe_allow_html=True)
            
        st.markdown("<div style='margin:10px 0; border-top:1px dashed #f1f5f9;'></div>", unsafe_allow_html=True)
        
        # Totales
        f1, f2 = st.columns([1,1])
        f1.markdown("<p style='font-size:0.8rem; margin:0;'>Total Neto</p>", unsafe_allow_html=True)
        f2.markdown(f"<h3 style='text-align:right; color:#6366f1; margin:0;'>${total:,.2f}</h3>", unsafe_allow_html=True)
        
        st.write(" ")
        if st.button("Confirmar Venta", type="primary", use_container_width=True):
            if total > 0:
                st.session_state.cart = []
                st.rerun()
        if st.button("Vaciar", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
