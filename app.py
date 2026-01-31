import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
import json
import numpy as np
from datetime import datetime, timedelta
import pytz

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
    page_title="Vertex Mobility v7.5", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SISTEMA DE SONIDO ---
def play_audio(sound_type="click"):
    # URLs de sonidos premium cortos
    sounds = {
        "click": "https://cdn.pixabay.com/audio/2022/03/15/audio_7302484f47.mp3", # Pop suave
        "success": "https://cdn.pixabay.com/audio/2021/08/04/audio_bb6304535b.mp3" # Chime de éxito
    }
    url = sounds.get(sound_type)
    if url:
        st.markdown(f"""
            <audio autoplay>
                <source src="{url}" type="audio/mpeg">
            </audio>
        """, unsafe_allow_html=True)

# --- CSS: V7.5 FULL SYNC EDITION ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@200;300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --primary-soft: rgba(99, 102, 241, 0.1);
        --pastel-red: rgba(255, 107, 107, 0.12);
        --text-red: #e63946;
        --bg: #f8fafc;
        --text-dark: #0f172a;
        --text-light: #64748b;
        --glass-bg: rgba(255, 255, 255, 0.7);
        --glass-border: rgba(255, 255, 255, 0.4);
        --radius: 20px;
    }

    * { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        text-transform: capitalize !important; 
    }

    .stApp { 
        background-image: radial-gradient(circle at top right, #e2e8f0, #f8fafc);
        background-attachment: fixed;
    }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 1rem !important; 
        padding-left: 5% !important;
        padding-right: 5% !important;
    }

    /* Branding Luxury */
    .brand-title {
        font-weight: 800;
        font-size: 2rem !important;
        color: var(--text-dark);
        letter-spacing: -2px;
        text-transform: uppercase !important;
    }
    .version-badge {
        background: white;
        color: var(--primary);
        padding: 3px 12px;
        border-radius: 30px;
        font-size: 0.65rem;
        font-weight: 800;
        border: 1px solid var(--glass-border);
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-left: 10px;
        display: inline-block;
        vertical-align: middle;
    }

    /* RELOJ MEXICO */
    .clock-container { text-align: center; padding-top: 10px; }
    .clock-time { font-size: 1.25rem; font-weight: 800; color: var(--text-dark); margin: 0; }
    .clock-date { font-size: 0.75rem; font-weight: 400; color: var(--text-light); margin-top: -2px; }

    /* CARRITO */
    .ticket-header {
        font-size: 0.65rem !important;
        font-weight: 400 !important;
        color: var(--text-light);
        border-bottom: 2px solid #f1f5f9;
        margin-top: -5px !important;
        margin-bottom: 8px !important;
        padding-bottom: 4px !important;
    }
    .ticket-item-text { font-size: 0.75rem !important; font-weight: 400 !important; color: var(--text-dark); }

    /* BOTONES PASTEL */
    div.stButton > button[kind="primary"] {
        background-color: var(--pastel-red) !important;
        color: var(--text-red) !important;
        border: 1px solid rgba(230, 57, 70, 0.15) !important;
        font-weight: 600 !important;
    }
    
    /* Dialog Styling */
    div[role="dialog"] {
        border-radius: var(--radius) !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* PRODUCTOS CON ELEVACIÓN */
    div[data-testid="column"] button {
        height: 140px !important;
        background: white !important;
        border: 1px solid #f1f5f9 !important;
        border-radius: 24px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div[data-testid="column"] button:hover {
        transform: translateY(-6px) !important;
        box-shadow: 0 12px 25px rgba(99, 102, 241, 0.1) !important;
        border: 1px solid var(--primary-soft) !important;
    }

    /* GLASSMORPHISM - PANELES LATERALES */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 28px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05) !important;
        padding: 15px !important;
    }

    /* Búsqueda Modern - Rectangular */
    .stTextInput input {
        height: 48px !important;
        border-radius: 0 !important; /* Esquinas rectas */
        background-color: white !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02) !important;
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
@st.dialog("Finalizar Venta")
def show_checkout_dialog(total):
    st.markdown(f"<div style='text-align:center;'><p style='margin:0; color:var(--text-light);'>Total A Pagar</p><h1 style='color:var(--primary); font-size:3.5rem; margin:0;'>${total:,.2f}</h1></div>", unsafe_allow_html=True)
    
    st.write(" ")
    recibido = st.number_input("Dinero Recibido", min_value=0.0, step=1.0, value=total, format="%.2f")
    
    cambio = recibido - total
    
    if cambio >= 0:
        st.markdown(f"<div style='background:#f8fafc; padding:15px; border-radius:15px; text-align:center; margin-top:10px;'><p style='margin:0; font-size:0.8rem; color:var(--text-light);'>Cambio A Entregar</p><h2 style='margin:0; color:#10b981;'>${cambio:,.2f}</h2></div>", unsafe_allow_html=True)
    else:
        st.error(f"Faltan ${abs(cambio):,.2f}")

    st.write(" ")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("PAGAR", use_container_width=True, type="primary"):
            if supabase:
                try:
                    payload = {
                        "customer_name": st.session_state.selected_client,
                        "total": total,
                        "items_data": purify_payload(st.session_state.cart),
                        "source": "web",
                        "created_at": datetime.now(pytz.timezone('America/Mexico_City')).isoformat()
                    }
                    res = supabase.table("sales").insert(payload).execute()
                    if res.data:
                        play_audio("success") # Sonido de éxito
                        st.session_state.cart = []
                        time.sleep(1.0)
                        st.rerun()
                    else:
                        st.error("Error Al Guardar La Venta.")
                except Exception as e:
                    st.error(f"Error De Conexión: {str(e)}")
            else:
                st.error("Supabase No Está Configurado.")
    with col2:
        if st.button("AGENDAR", use_container_width=True):
            st.info("Pedido Agendado")
            st.session_state.cart = []
            time.sleep(1)
            st.rerun()
    
    if st.button("CANCELAR", use_container_width=True, key="cancel_checkout"):
        st.rerun()

@st.dialog("Dashboard")
def show_dashboard_dialog():
    st.markdown("### Análisis De Ventas")
    df_s = get_data("sales")
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['created_at'])
        tz_mx = pytz.timezone('America/Mexico_City')
        today = datetime.now(tz_mx).date()
        today_sales = df_s[df_s['date'].dt.date == today]
        c1, c2 = st.columns(2)
        c1.metric("Ventas Hoy", f"${today_sales['total'].sum():,.2f}")
        c2.metric("Operaciones", len(today_sales))
        daily = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
        fig = px.area(daily, x='date', y='total', height=250, color_discrete_sequence=['#6366f1'])
        st.plotly_chart(fig, use_container_width=True)
    if st.button("Cerrar", use_container_width=True): st.rerun()

@st.dialog("Clientes")
def show_client_dialog():
    tab_search, tab_new = st.tabs(["🔍 Buscar Cliente", "➕ Nuevo Cliente"])
    
    with tab_search:
        df_c = get_data("customers")
        options = ["Mostrador"] + (df_c['name'].tolist() if not df_c.empty else [])
        sel = st.selectbox("Elegir Cliente:", options)
        if st.button("Confirmar Y Seleccionar", type="primary", use_container_width=True):
            st.session_state.selected_client = sel
            st.rerun()

    with tab_new:
        with st.form("new_customer_web"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nombre Completo *")
            company = c2.text_input("Empresa")
            
            c3, c4 = st.columns(2)
            phone = c3.text_input("Teléfono")
            email = c4.text_input("Email")
            
            c5, c6 = st.columns(2)
            address = c5.text_input("Dirección")
            localidad = c6.text_input("Localidad")
            
            show_bday = st.toggle("Agregar Cumpleaños")
            birthday = None
            if show_bday:
                 birthday = st.date_input("Fecha De Nacimiento", value=datetime(2000, 1, 1)).isoformat()
            
            st.write(" ")
            if st.form_submit_button("Guardar Y Seleccionar", use_container_width=True, type="primary"):
                if name:
                    if supabase:
                        try:
                            cust_payload = {
                                "name": name,
                                "company": company,
                                "phone": phone,
                                "email": email,
                                "address": address,
                                "localidad": localidad,
                                "birthday": birthday,
                                "notes": "Creado desde Cloud Dashboard"
                            }
                            res = supabase.table("customers").insert(cust_payload).execute()
                            if res.data:
                                play_audio("success")
                                st.session_state.selected_client = name
                                st.success(f"Cliente {name} Guardado Correctamente")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                    else:
                        st.error("Conexión No Disponible")
                else:
                    st.warning("El Nombre Es Obligatorio")

# --- HEADER v7.2 ---
col_brand, col_clock, col_action = st.columns([2, 2, 2])
with col_brand:
    st.markdown(f"""
        <div style="display: flex; align-items: baseline;">
            <div class="brand-title">Vertex</div>
            <div class="version-badge">Versión 7.5</div>
        </div>
        <div style="font-size:0.7rem; color:var(--text-light); text-transform:uppercase;">Movilidad E Inteligencia De Negocio</div>
    """, unsafe_allow_html=True)
with col_clock:
    tz_mexico = pytz.timezone('America/Mexico_City')
    now_mex = datetime.now(tz_mexico)
    time_str = now_mex.strftime("%I:%M %p")
    meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    dias = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes", 5:"Sábado", 6:"Domingo"}
    date_str = f"{dias[now_mex.weekday()]}, {now_mex.day} De {meses[now_mex.month]} {now_mex.year}"
    st.markdown(f'<div class="clock-container"><p class="clock-time">{time_str}</p><p class="clock-date">{date_str}</p></div>', unsafe_allow_html=True)
with col_action:
    st.write(" ")
    c1, c2 = st.columns([1, 1])
    with c2:
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
                                if item['id'] == p['id']: item['qty'] += 1; found = True; break
                            if not found:
                                st.session_state.cart.append({
                                    "id": p['id'], 
                                    "name": p['name'], 
                                    "price": float(p['price']), 
                                    "qty": 1,
                                    "barcode": p.get('barcode', '')
                                })
                            play_audio("click") # Sonido al agregar
                            st.rerun()

with col_s:
    with st.container(border=True):
        st.markdown("<p style='font-size:0.7rem; margin:0;'>Cliente Actual</p>", unsafe_allow_html=True)
        st.markdown(f"<h5 style='margin:0;'>{st.session_state.selected_client}</h5>", unsafe_allow_html=True)
        if st.button("Buscar Cliente", use_container_width=True): show_client_dialog()
    st.write(" ")
    with st.container(border=True):
        st.markdown("<p style='font-size:0.9rem; font-weight:800; margin:0 0 5px 0;'>Carrito</p>", unsafe_allow_html=True)
        th1, th2, th3, th4 = st.columns([0.6, 2.5, 1, 1])
        th1.markdown('<div class="ticket-header">Cant</div>', unsafe_allow_html=True)
        th2.markdown('<div class="ticket-header">Productos</div>', unsafe_allow_html=True)
        th3.markdown('<div class="ticket-header">Precio</div>', unsafe_allow_html=True)
        th4.markdown('<div class="ticket-header" style="text-align:right;">Total</div>', unsafe_allow_html=True)
        total = 0
        for it in st.session_state.cart:
            sub = it['price'] * it['qty']
            total += sub
            r1, r2, r3, r4 = st.columns([0.6, 2.5, 1, 1])
            r1.markdown(f'<div class="ticket-item-text">{it["qty"]}</div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="ticket-item-text">{it["name"][:20]}</div>', unsafe_allow_html=True)
            r3.markdown(f'<div class="ticket-item-text">${it["price"]:,.0f}</div>', unsafe_allow_html=True)
            r4.markdown(f'<div class="ticket-item-text" style="text-align:right;">${sub:,.0f}</div>', unsafe_allow_html=True)
        if not st.session_state.cart: st.markdown("<p style='font-size:0.75rem; color:#cbd5e1; text-align:center; padding:5px 0;'>Vacío</p>", unsafe_allow_html=True)
        st.divider()
        f1, f2 = st.columns([1,1])
        f1.markdown("**Total Neto**")
        f2.markdown(f"<h3 style='text-align:right; color:#6366f1; margin:0;'>${total:,.2f}</h3>", unsafe_allow_html=True)
        st.write(" ")
        if st.button("Confirmar Venta", type="primary", use_container_width=True):
            if total > 0:
                show_checkout_dialog(total)
        if st.button("Vaciar", use_container_width=True): st.session_state.cart = []; st.rerun()
