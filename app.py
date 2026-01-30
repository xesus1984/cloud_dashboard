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
    page_title="Vertex Mobility v6.7", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: DESIGN SYSTEM "POP-IT" (v6.7) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --secondary: #4f46e5;
        --bg: #fdfdfe;
        --card-bg: #f8fafc;
        --text-dark: #0f172a;
        --text-light: #64748b;
        --radius: 24px;
    }

    /* Reset & Base */
    * { 
        font-family: 'Plus Jakarta Sans', sans-serif !important; 
    }

    .stApp {
        background-color: var(--bg);
    }

    /* Ocultar UI de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { 
        padding-top: 1.5rem !important; 
        padding-bottom: 2rem !important;
        padding-left: 5% !important;
        padding-right: 5% !important;
    }

    /* Branding Section */
    .brand-container {
        padding: 0.5rem 0;
        margin-bottom: 2rem;
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
        margin-top: -10px;
    }
    .version-badge {
        background: #eff6ff;
        color: #3b82f6;
        padding: 4px 14px;
        border-radius: 30px;
        font-size: 0.7rem;
        font-weight: 800;
        margin-left: 15px;
        border: 1px solid #dbeafe;
    }

    /* Botones de Producto Estilo Pop-It */
    div[data-testid="column"] button {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: var(--radius) !important;
        width: 100% !important;
        height: 140px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: var(--text-dark) !important;
        display: block !important;
        margin-bottom: 10px;
    }
    div[data-testid="column"] button:active {
        transform: scale(0.96);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
        background-color: #f1f5f9 !important;
    }

    /* Fix: Barra de Búsqueda sin doble borde */
    .search-box-container {
        padding: 0 !important;
        margin-bottom: 1.5rem;
    }
    .stTextInput input {
        border-radius: 18px !important;
        border: 1px solid #e2e8f0 !important;
        height: 60px !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        background: white !important;
        color: var(--text-dark) !important;
        padding-left: 25px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02) !important;
    }
    .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08) !important;
    }

    /* Contenedores con Esquinas Redondeadas Pop-It */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius) !important;
        border: 1px solid #e2e8f0 !important;
        background: white !important;
        padding: 20px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.04) !important;
    }

    /* Botones de Acción (Sidebar / General) */
    .stButton > button {
        border-radius: 16px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }

    /* Dialog/Modal Styling (Hack para Streamlit Dialogs) */
    div[role="dialog"] {
        border-radius: var(--radius) !important;
    }
    
    /* Quitar el borde extra del contenedor de búsqueda que el usuario reportó */
    div[data-testid="stVerticalBlock"] > div:has(.stTextInput) {
        border: none !important;
    }

    .custom-card {
        background: #f8fafc;
        border-radius: var(--radius);
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
    }
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

# Cachear datos
@st.cache_data(ttl=30)
def get_data(table):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- DIALOGS (VENTANAS POP-IT) ---

@st.dialog("INTELIGENCIA DE NEGOCIO")
def show_dashboard_dialog():
    st.markdown("### RESUMEN DE OPERACIONES")
    df_s = get_data("sales")
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['created_at'])
        today_sales = df_s[df_s['date'].dt.date == datetime.now().date()]
        total_today = today_sales['total'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("VENTAS HOY", f"${total_today:,.2f}")
        c2.metric("OPS", len(today_sales))
        
        daily = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
        fig = px.area(daily, x='date', y='total', height=250, color_discrete_sequence=['#6366f1'])
        fig.update_layout(margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("SIN REGISTROS PARA ANALIZAR")
    if st.button("CERRAR VENTANA", use_container_width=True):
        st.rerun()

@st.dialog("SELECCIONAR CLIENTE")
def show_client_dialog():
    st.markdown("### CATALOGO DE CLIENTES")
    df_c = get_data("customers")
    options = ["Mostrador"] + (df_c['name'].tolist() if not df_c.empty else [])
    sel = st.selectbox("BUSCAR O ELEGIR:", options)
    
    st.divider()
    if st.button("CONFIRMAR SELECCION", type="primary", use_container_width=True):
        st.session_state.selected_client = sel
        st.rerun()
    if st.button("CANCELAR", use_container_width=True):
        st.rerun()

# --- HEADER ---
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown(f"""
    <div class="brand-container">
        <div style="display: flex; align-items: baseline; flex-wrap: wrap;">
            <div class="brand-title">VERTEX</div>
            <div class="version-badge">V 6.7</div>
        </div>
        <div class="brand-subtitle">MOVILIDAD E INTELIGENCIA DE NEGOCIO</div>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.write(" ") # Espaciador
    if st.button("VER ANALISIS", use_container_width=True):
        show_dashboard_dialog()

# --- VISTA PRINCIPAL (POS) ---
col_main, col_side = st.columns([2.8, 1.2], gap="large")

with col_main:
    # BÚSQUEDA (Fix: placeholder y quitar doble borde)
    search = st.text_input("BUSCAR...", placeholder="ESCRIBE O ESCANEA", label_visibility="collapsed")
    
    df_p = get_data("products")
    
    if not df_p.empty:
        if search:
            mask = df_p['name'].str.contains(search, case=False) | df_p['barcode'].str.contains(search, case=False)
            df_view = df_p[mask].head(28)
        else:
            df_view = df_p.head(28)

        n_cols = 4
        for i in range(0, len(df_view), n_cols):
            cols = st.columns(n_cols)
            for j in range(n_cols):
                if i + j < len(df_view):
                    p = df_view.iloc[i + j]
                    with cols[j]:
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
    # CLIENTE (Pop-It Style)
    with st.container(border=True):
        st.markdown("**CLIENTE ACTUAL**")
        st.markdown(f"<h2 style='margin:0; color:#1e293b;'>{st.session_state.selected_client.upper()}</h2>", unsafe_allow_html=True)
        st.write(" ")
        if st.button("SELECCIONAR CLIENTE", use_container_width=True):
            show_client_dialog()

    # CARRITO (CARRITO FLUIDO)
    st.write(" ")
    with st.container(border=True):
        st.markdown("**RESUMEN DE COMPRA**")
        if not st.session_state.cart:
            st.write("AGREGA ARTICULOS")
        else:
            total = 0
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
                    aq2.markdown(f"<p style='text-align:center; padding-top:4px;'>{item['qty']}</p>", unsafe_allow_html=True)
                    if aq3.button(" + ", key=f"p_{idx}"):
                        item['qty'] += 1
                        st.rerun()
                    ap1.markdown(f"<p style='text-align:right; font-weight:800;'>${sub:,.2f}</p>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown(f"<h1 style='text-align: right; color: var(--primary);'>${total:,.2f}</h1>", unsafe_allow_html=True)
            
            if st.button("COMPLETAR VENTA", type="primary", use_container_width=True):
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
