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
    page_title="Vertex Mobility v6.6", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: DESIGN SYSTEM FLUIDO Y ADAPTATIVO (v6.6.1) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --secondary: #4f46e5;
        --bg: #f8fafc;
        --card-bg: rgba(255, 255, 255, 0.9);
        --text-dark: #1e293b;
        --text-light: #64748b;
    }

    /* Reset & Base */
    * { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
        box-sizing: border-box;
    }

    .stApp {
        background-color: var(--bg);
        background-image: radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.03) 0px, transparent 50%), 
                          radial-gradient(at 100% 100%, rgba(79, 70, 229, 0.03) 0px, transparent 50%);
    }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 2rem !important; 
        padding-bottom: 2rem !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
    }

    /* --- RESPONSIVIDAD DINÁMICA --- */
    
    /* Para pantallas grandes (Monitores 21"+) */
    @media (min-width: 1400px) {
        .block-container { max-width: 1600px !important; }
        .brand-title { font-size: 2.8rem !important; }
        div[data-testid="column"] button { height: 160px !important; font-size: 1.1rem !important; }
    }

    /* Para tablets (iPad) */
    @media (max-width: 1024px) {
        .block-container { padding-left: 2% !important; padding-right: 2% !important; }
        .brand-title { font-size: 1.8rem !important; }
        div[data-testid="column"] button { height: 120px !important; padding: 0.8rem !important; }
        h1 { font-size: 1.5rem !important; }
    }

    /* Branding Section */
    .brand-container {
        padding: 0.5rem 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 2rem;
    }
    .brand-title {
        font-weight: 800;
        font-size: 2.2rem;
        color: var(--text-dark);
        letter-spacing: -1.5px;
        margin-bottom: -5px;
    }
    .brand-subtitle {
        font-weight: 600;
        font-size: 0.75rem;
        color: var(--text-light);
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .version-badge {
        background: #f1f5f9;
        color: #475569;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 800;
        margin-left: 15px;
        border: 1px solid #e2e8f0;
    }

    /* Botones de Producto Adaptativos */
    div[data-testid="column"] button {
        background: var(--card-bg) !important;
        border: 1px solid rgba(226, 232, 240, 1) !important;
        border-radius: 14px !important;
        width: 100% !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s ease !important;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block !important;
    }
    div[data-testid="column"] button:hover {
        border-color: var(--primary) !important;
        box-shadow: 0 10px 15px -3px rgba(99, 102, 241, 0.1) !important;
        transform: translateY(-2px);
    }

    /* Inputs y Formularios */
    .stTextInput input {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        height: 50px !important;
        background: white !important;
    }
    .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }

    /* Contenedores de Información */
    [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        background: white !important;
        overflow: hidden;
    }

    /* Scrollbar Personalizada */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = get_supabase()

# --- ESTADO DE SESIÓN ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'selected_client' not in st.session_state: st.session_state.selected_client = "Mostrador"
if 'show_stats' not in st.session_state: st.session_state.show_stats = False

# Cachear datos
@st.cache_data(ttl=30)
def get_data(table):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- HEADER ADAPTATIVO ---
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown(f"""
    <div class="brand-container">
        <div style="display: flex; align-items: baseline; flex-wrap: wrap;">
            <div class="brand-title">VERTEX</div>
            <div class="version-badge">V 6.6.1</div>
        </div>
        <div class="brand-subtitle">MOVILIDAD E INTELIGENCIA DE NEGOCIO</div>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    label_stats = "OCULTAR ANALISIS" if st.session_state.show_stats else "VER ANALISIS"
    st.write(" ") # Espaciador
    if st.button(label_stats, use_container_width=True):
        st.session_state.show_stats = not st.session_state.show_stats

# --- DASHBOARD INTEGRADO ---
if st.session_state.show_stats:
    with st.expander("RESUMEN DE OPERACIONES", expanded=True):
        df_s = get_data("sales")
        if not df_s.empty:
            df_s['date'] = pd.to_datetime(df_s['created_at'])
            today_sales = df_s[df_s['date'].dt.date == datetime.now().date()]
            total_today = today_sales['total'].sum()
            
            # KPIs que se ajustan en columnas
            k_cols = st.columns(4)
            k_cols[0].metric("VENTAS HOY", f"${total_today:,.2f}")
            k_cols[1].metric("OPERACIONES", len(today_sales))
            
            # Gráfica fluida
            daily = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
            fig = px.area(daily, x='date', y='total', height=250, color_discrete_sequence=['#6366f1'])
            fig.update_layout(margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

# --- LAYOUT PRINCIPAL (REACCIONA AL TAMAÑO) ---
# En pantallas grandes el ratio es 3:1, en tablets se mantiene pero con márgenes ajustados
col_main, col_side = st.columns([2.8, 1.2], gap="medium")

with col_main:
    # BÚSQUEDA
    try:
        from streamlit_keyup import st_keyup
        search = st_keyup("BUSCAR PRODUCTOS...", placeholder="ESCRIBE NOMBRE O ESCANEA CODIGO", debounce=200, key="search_bar", label_visibility="collapsed")
    except ImportError:
        search = st.text_input("BUSCAR...", placeholder="ESCRIBE NOMBRE O ESCANEA CODIGO", label_visibility="collapsed")
    
    df_p = get_data("products")
    
    if not df_p.empty:
        if search:
            mask = df_p['name'].str.contains(search, case=False) | df_p['barcode'].str.contains(search, case=False)
            df_view = df_p[mask].head(28)
        else:
            df_view = df_p.head(28)

        # Grilla Adaptativa: 4 columnas en monitor, 3 en iPad modo vertical (Streamlit maneja el stack)
        n_cols = 4
        for i in range(0, len(df_view), n_cols):
            cols = st.columns(n_cols)
            for j in range(n_cols):
                if i + j < len(df_view):
                    p = df_view.iloc[i + j]
                    with cols[j]:
                        # Botón que escala con el contenedor
                        label = f"{p['name'][:35].upper()}\n\n${p['price']:,.2f}"
                        if st.button(label, key=f"btn_{p['id']}", use_container_width=True):
                            found = False
                            for item in st.session_state.cart:
                                if item['id'] == p['id']:
                                    item['qty'] += 1
                                    found = True
                                    break
                            if not found:
                                st.session_state.cart.append({
                                    "id": int(p['id']), "name": str(p['name']), 
                                    "price": float(p['price']), "qty": 1, "barcode": str(p.get('barcode', ''))
                                })
                            st.rerun()
    else:
        st.info("CATALOGO VACIO - SINCRONIZA DESDE ESCRITORIO")

with col_side:
    # CLIENTE
    with st.container(border=True):
        st.markdown("**CLIENTE ACTUAL**")
        sc1, sc2 = st.columns([2, 1])
        sc1.subheader(st.session_state.selected_client.upper())
        with sc2:
            with st.popover("DATOS", use_container_width=True):
                df_c = get_data("customers")
                options = ["Mostrador"] + (df_c['name'].tolist() if not df_c.empty else [])
                sel = st.selectbox("ELEGIR:", options)
                if st.button("OK"):
                    st.session_state.selected_client = sel
                    st.rerun()

    # CARRITO (CARRITO FLUIDO)
    st.write(" ")
    with st.container(border=True):
        st.markdown("**RESUMEN DE COMPRA**")
        if not st.session_state.cart:
            st.write("AGREGA ARTICULOS")
        else:
            total = 0
            # Contenedor con scroll si hay muchos items
            for idx, item in enumerate(st.session_state.cart):
                sub = item['price'] * item['qty']
                total += sub
                
                with st.container():
                    st.markdown(f"**{item['name'].upper()}**")
                    aq1, aq2, aq3, ap1 = st.columns([1,1,1,2])
                    if aq1.button(" - ", key=f"m_{idx}"):
                        if item['qty'] > 1: item['qty'] -= 1
                        else: st.session_state.cart.pop(idx)
                        st.rerun()
                    aq2.markdown(f"<p style='text-align:center;'>{item['qty']}</p>", unsafe_allow_html=True)
                    if aq3.button(" + ", key=f"p_{idx}"):
                        item['qty'] += 1
                        st.rerun()
                    ap1.markdown(f"<p style='text-align:right; font-weight:800;'>${sub:,.2f}</p>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown(f"<h2 style='text-align: right; color: var(--primary);'>TOTAL: ${total:,.2f}</h2>", unsafe_allow_html=True)
            
            if st.button("CONFIRMAR VENTA", type="primary", use_container_width=True):
                if supabase:
                    with st.spinner("PROCESANDO..."):
                        sale_data = purify_payload({
                            "folio": f"MOB-{int(time.time())}",
                            "total": float(total),
                            "source": "web",
                            "customer_name": str(st.session_state.selected_client),
                            "items_data": st.session_state.cart,
                            "payment_method": "Efectivo",
                            "created_at": datetime.now().isoformat()
                        })
                        try:
                            supabase.table("sales").insert(sale_data).execute()
                            st.session_state.cart = []
                            st.balloons()
                            st.success("COMPLETADO")
                            time.sleep(1.2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"ERROR: {e}")

            if st.button("VACIAR", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
