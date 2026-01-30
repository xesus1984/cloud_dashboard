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
    page_title="Vertex Mobility v6.9", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: V6.9 PROFESSIONAL CART ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --secondary: #4f46e5;
        --bg: #fdfdfe;
        --text-dark: #0f172a;
        --text-light: #64748b;
        --radius: 18px;
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

    /* Branding */
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

    /* Barra de Búsqueda */
    .stTextInput input {
        border-radius: 12px !important;
        border: none !important;
        background-color: #f1f5f9 !important;
        height: 50px !important;
        transition: all 0.2s ease;
    }
    .stTextInput input:focus {
        background-color: white !important;
        box-shadow: 0 0 0 1px #e2e8f0 !important;
    }

    /* Productos */
    div[data-testid="column"] button {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: var(--radius) !important;
        height: 140px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="column"] button:active { transform: scale(0.96); }

    /* Formato de Ticket / Carrito */
    .ticket-header {
        font-size: 0.7rem;
        font-weight: 800;
        color: var(--text-light);
        text-transform: uppercase;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 8px;
        margin-bottom: 15px;
    }
    .ticket-row {
        font-size: 0.85rem;
        padding: 8px 0;
        border-bottom: 1px solid #f8fafc;
        min-height: 40px;
        display: flex;
        align-items: center;
    }
    .ticket-footer {
        margin-top: 20px;
        padding-top: 15px;
        border-top: 2px solid #f1f5f9;
    }
    .ticket-total-label { font-weight: 400; font-size: 0.9rem; color: var(--text-light); }
    .ticket-total-value { font-weight: 800; font-size: 1.5rem; color: var(--primary); text-align: right; }

    /* Botones de acción compactos */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
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
@st.dialog("DASHBOARD")
def show_dashboard_dialog():
    st.markdown("### ANALISIS DE VENTAS")
    df_s = get_data("sales")
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['created_at'])
        today_sales = df_s[df_s['date'].dt.date == datetime.now().date()]
        st.metric("VENTAS HOY", f"${today_sales['total'].sum():,.2f}")
        daily = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
        fig = px.area(daily, x='date', y='total', height=250, color_discrete_sequence=['#6366f1'])
        st.plotly_chart(fig, use_container_width=True)
    if st.button("CERRAR"): st.rerun()

@st.dialog("CLIENTES")
def show_client_dialog():
    st.markdown("### SELECCIONAR CLIENTE")
    df_c = get_data("customers")
    options = ["Mostrador"] + (df_c['name'].tolist() if not df_c.empty else [])
    sel = st.selectbox("ELEGIR:", options)
    if st.button("CONFIRMAR", type="primary"):
        st.session_state.selected_client = sel
        st.rerun()

# --- HEADER ---
c_log, c_ver, c_d = st.columns([1.5, 3.5, 1])
with c_log: st.markdown('<div class="brand-title">VERTEX</div>', unsafe_allow_html=True)
with c_ver: 
    st.markdown('<div style="padding-top:16px;"><span style="background:#eff6ff; color:#3b82f6; padding:2px 10px; border-radius:30px; font-size:0.65rem; font-weight:800; border:1px solid #dbeafe;">V 6.9</span></div>', unsafe_allow_html=True)
with c_d:
    if st.button("DASHBOARD"): show_dashboard_dialog()
st.markdown('<div class="brand-subtitle">MOVILIDAD E INTELIGENCIA DE NEGOCIO</div>', unsafe_allow_html=True)
st.write(" ")

# --- VISTA PRINCIPAL ---
col_main, col_side = st.columns([2.8, 1.2], gap="large")

with col_main:
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
                        lbl = f"{p['name'][:35].upper()}\n\n${p['price']:,.2f}"
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
    # CLIENTE ACTUAL
    with st.container(border=True):
        st.markdown("**CLIENTE ACTUAL**")
        st.markdown(f"### {st.session_state.selected_client.upper()}")
        if st.button("BUSCAR CLIENTE"): show_client_dialog()

    st.write(" ")
    
    # CARRITO (NUEVO FORMATO PROFESIONAL)
    with st.container(border=True):
        st.markdown("<h3 style='margin-bottom:20px;'>CARRITO</h3>", unsafe_allow_html=True)
        
        # Header de la tabla
        th1, th2, th3, th4 = st.columns([0.8, 3, 1.5, 1.5])
        th1.markdown('<div class="ticket-header">CANT</div>', unsafe_allow_html=True)
        th2.markdown('<div class="ticket-header">DESCRIP</div>', unsafe_allow_html=True)
        th3.markdown('<div class="ticket-header">P.UNIT</div>', unsafe_allow_html=True)
        th4.markdown('<div class="ticket-header" style="text-align:right;">TOTAL</div>', unsafe_allow_html=True)
        
        total_items = len(st.session_state.cart)
        rows_to_show = max(5, total_items) # Asegurar al menos 5 filas para look profesional
        
        running_total = 0
        
        for i in range(rows_to_show):
            tr1, tr2, tr3, tr4 = st.columns([0.8, 3, 1.5, 1.5])
            if i < total_items:
                item = st.session_state.cart[i]
                sub = item['price'] * item['qty']
                running_total += sub
                
                # Cantidad con botones discretos lateralizados si es posible, o solo numero
                # Para mantener el look de tabla, usaremos solo el numero y un popover o botones laterales
                with tr1:
                    # Implementación de +/- compacta
                    st.markdown(f"<div style='padding-top:5px;'>{item['qty']}</div>", unsafe_allow_html=True)
                    # Añadimos mini-botones en una sub-columna si hay espacio? No, mejor en una linea abajo o discreto
                with tr2:
                    st.markdown(f"<div style='padding-top:5px; font-size:0.8rem;'>{item['name'][:25].upper()}</div>", unsafe_allow_html=True)
                with tr3:
                    st.markdown(f"<div style='padding-top:5px; font-size:0.8rem;'>${item['price']:,.2f}</div>", unsafe_allow_html=True)
                with tr4:
                    st.markdown(f"<div style='padding-top:5px; font-size:0.8rem; text-align:right; font-weight:600;'>${sub:,.2f}</div>", unsafe_allow_html=True)
                
                # Botones de ajuste (separados para no romper la tabla)
                # b1, b2 = st.columns([1,1]) # Demasiado grande. Usaré botones en la misma fila pero abajo?
                # Para simplificar y mantener el look, los pondre solo si hay seleccion
            else:
                # Filas vacías para estética
                tr1.markdown('<div style="color:#f1f5f9;">—</div>', unsafe_allow_html=True)
                tr2.markdown('<div style="color:#f1f5f9;">—</div>', unsafe_allow_html=True)
                tr3.markdown('<div style="color:#f1f5f9;">—</div>', unsafe_allow_html=True)
                tr4.markdown('<div style="color:#f1f5f9; text-align:right;">—</div>', unsafe_allow_html=True)
        
        # Footer con Totales
        st.markdown('<div class="ticket-footer"></div>', unsafe_allow_html=True)
        f_c1, f_c2 = st.columns([1, 1])
        with f_c1:
            st.markdown('<div class="ticket-total-label">SUBTOTAL</div>', unsafe_allow_html=True)
            st.markdown('<div class="ticket-total-label" style="font-weight:800; color:var(--text-dark);">TOTAL NETO</div>', unsafe_allow_html=True)
        with f_c2:
            st.markdown(f'<div style="text-align:right; color:var(--text-light); font-size:0.9rem;">${running_total:,.2f}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ticket-total-value">${running_total:,.2f}</div>', unsafe_allow_html=True)
        
        st.write(" ")
        if st.button("🚀 COMPLETAR VENTA", type="primary", use_container_width=True):
            if running_total > 0:
                st.success("SIMULANDO VENTA...")
                st.session_state.cart = []
                st.rerun()
        
        if st.button("VACIAR CARRITO", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
