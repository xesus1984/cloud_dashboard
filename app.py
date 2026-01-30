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
    page_title="Vertex Mobility v6.8", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: DESIGN SYSTEM v6.8 (ANIMATED EFFECTS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --bg: #fdfdfe;
        --text-dark: #0f172a;
        --text-light: #64748b;
        --radius: 20px;
    }

    * { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .stApp { background-color: var(--bg); }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 1.5rem !important; 
        padding-left: 5% !important;
        padding-right: 5% !important;
    }

    /* Branding Section */
    .brand-container {
        padding: 0.5rem 0;
        margin-bottom: 2.5rem;
    }
    .brand-title {
        font-weight: 800;
        font-size: 2.2rem;
        color: var(--text-dark);
        letter-spacing: -2px;
    }
    .brand-subtitle {
        font-weight: 600;
        font-size: 0.75rem;
        color: var(--text-light);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 12px;
    }

    /* --- ANIMACIÓN TORNASOL GRIS-BLANCO --- */
    @keyframes iridescent {
        0% { border-color: #e2e8f0; box-shadow: 0 0 5px rgba(226, 232, 240, 0.2); }
        33% { border-color: #ffffff; box-shadow: 0 0 10px rgba(255, 255, 255, 0.8); }
        66% { border-color: #94a3b8; box-shadow: 0 0 5px rgba(148, 163, 184, 0.3); }
        100% { border-color: #e2e8f0; box-shadow: 0 0 5px rgba(226, 232, 240, 0.2); }
    }

    /* BARRA DE BUSQUEDA ANIMADA TORNASOL */
    .stTextInput div[data-baseweb="input"] {
        background-color: transparent !important;
        border: none !important;
    }

    .stTextInput input {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important; /* Borde base */
        height: 50px !important;
        background-color: white !important;
        color: var(--text-dark) !important;
        font-size: 0.95rem !important;
        padding: 0 20px !important;
        
        /* Aplicación de la animación tornasol */
        animation: iridescent 4s infinite linear;
        transition: transform 0.2s ease;
    }

    .stTextInput input:focus {
        outline: none !important;
        transform: scale(1.01);
        border-color: #6366f1 !important; /* Resalta en azul al escribir */
        animation: none; /* Detiene animación al hacer focus para no distraer */
    }

    /* Productos Estilo Pop-It */
    div[data-testid="column"] button {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: var(--radius) !important;
        width: 100% !important;
        height: 140px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="column"] button:active {
        transform: scale(0.96);
        background-color: #f1f5f9 !important;
    }

    /* Paneles Redondeados */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius) !important;
        border: 1px solid #e2e8f0 !important;
        background: white !important;
    }

    /* Dialogs */
    div[role="dialog"] { border-radius: var(--radius) !important; }
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

# --- VISTA PRINCIPAL ---
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown(f"""
    <div class="brand-container">
        <div style="display: flex; align-items: baseline; flex-wrap: wrap;">
            <div class="brand-title">VERTEX</div>
            <div style="background: #eff6ff; color: #3b82f6; padding: 4px 14px; border-radius: 30px; font-size: 0.7rem; font-weight: 800; margin-left: 15px; border: 1px solid #dbeafe;">V 6.8</div>
        </div>
        <div class="brand-subtitle">MOVILIDAD E INTELIGENCIA DE NEGOCIO</div>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.write(" ")
    if st.button("DASHBOARD", use_container_width=True):
        st.info("ABRIENDO DASHBOARD EN POP-UP...")
        # Llamar dialog... (omitido por brevedad, se mantiene lógica v6.7)

col_main, col_side = st.columns([2.8, 1.2], gap="large")

with col_main:
    # BÚSQUEDA ANIMADA TORNASOL
    search = st.text_input("buscar...", placeholder="escribe o escanea", label_visibility="collapsed")
    
    df_p = get_data("products")
    
    if not df_p.empty:
        df_view = df_p[df_p['name'].str.contains(search, case=False)].head(28) if search else df_p.head(28)
        n_cols = 4
        for i in range(0, len(df_view), n_cols):
            cols = st.columns(n_cols)
            for j in range(n_cols):
                if i + j < len(df_view):
                    p = df_view.iloc[i + j]
                    with cols[j]:
                        label = f"{p['name'][:35].upper()}\n\n${p['price']:,.2f}"
                        if st.button(label, key=f"p_{p['id']}", use_container_width=True):
                            st.session_state.cart.append({"id": p['id'], "name": p['name'], "price": float(p['price']), "qty": 1})
                            st.rerun()

with col_side:
    with st.container(border=True):
        st.markdown("**CLIENTE ACTUAL**")
        st.markdown(f"<h2 style='margin:0;'>{st.session_state.selected_client.upper()}</h2>", unsafe_allow_html=True)
        if st.button("SELECCIONAR CLIENTE", use_container_width=True):
            st.info("ABRIENDO SELECCION...")

    st.write(" ")
    with st.container(border=True):
        st.markdown("**RESUMEN DE COMPRA**")
        if not st.session_state.cart:
            st.write("AGREGA ARTICULOS")
        else:
            total = sum(i['price'] * i['qty'] for i in st.session_state.cart)
            st.write(f"Items: {len(st.session_state.cart)}")
            st.divider()
            st.markdown(f"<h1 style='text-align: right; color: #6366f1;'>${total:,.2f}</h1>", unsafe_allow_html=True)
            if st.button("COMPLETAR VENTA", type="primary", use_container_width=True):
                st.success("ENVIANDO...")
            if st.button("VACIAR", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
