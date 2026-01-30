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

# --- CSS: ESTILO PROFESIONAL "UNIFIED UI" ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');

    :root {
        --primary: #6366f1;
        --secondary: #4f46e5;
        --bg: #f8fafc;
        --card-bg: rgba(255, 255, 255, 0.85);
        --text-dark: #1e293b;
        --text-light: #64748b;
    }

    * { font-family: 'Plus Jakarta Sans', sans-serif !important; }

    .stApp {
        background-color: var(--bg);
        background-image: radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.05) 0px, transparent 50%), 
                          radial-gradient(at 100% 100%, rgba(79, 70, 229, 0.05) 0px, transparent 50%);
    }

    /* Ocultar elementos de Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; }

    /* Branding Section */
    .brand-container {
        padding: 0.5rem 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 1.5rem;
    }
    .brand-title {
        font-weight: 800;
        font-size: 2.2rem;
        color: var(--text-dark);
        letter-spacing: -1.5px;
        margin-bottom: -5px;
    }
    .brand-subtitle {
        font-weight: 500;
        font-size: 0.85rem;
        color: var(--text-light);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .version-badge {
        background: #f1f5f9;
        color: #475569;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 10px;
        border: 1px solid #e2e8f0;
    }

    /* Tarjetas de Producto Modernas */
    div[data-testid="column"] button {
        background: var(--card-bg) !important;
        border: 1px solid rgba(226, 232, 240, 0.8) !important;
        border-radius: 16px !important;
        padding: 1.2rem !important;
        height: 140px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: var(--text-dark) !important;
    }
    div[data-testid="column"] button:active {
        transform: scale(0.95) !important;
        background: #f1f5f9 !important;
    }
    div[data-testid="column"] button p {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }

    /* Input estilo iOS */
    .stTextInput input {
        border-radius: 14px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 1rem !important;
        height: 55px !important;
        font-size: 1rem !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }

    /* Panel Derecho (Carrito) */
    .sticky-panel {
        background: white;
        border-left: 1px solid #e2e8f0;
        height: 100vh;
        position: fixed;
        right: 0;
        top: 0;
        padding: 2rem;
    }

    .card-glass {
        background: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 18px !important;
        padding: 1.2rem !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05) !important;
    }

    /* Estilo de los items del carrito */
    .cart-item {
        padding: 10px 0;
        border-bottom: 1px solid #f1f5f9;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Error de conexión: Configura SECRETS en Streamlit Cloud. {e}")
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

# --- ENCABEZADO (BRANDING) ---
col_brand, col_nav = st.columns([3, 1])
with col_brand:
    st.markdown(f"""
    <div class="brand-container">
        <div style="display: flex; align-items: baseline;">
            <div class="brand-title">VERTEX</div>
            <div class="version-badge">v6.6</div>
        </div>
        <div class="brand-subtitle">Soluciones de Movilidad e Inteligencia</div>
    </div>
    """, unsafe_allow_html=True)

with col_nav:
    if st.button("📊 " + ("Ocultar Dashboard" if st.session_state.show_stats else "Ver Dashboard"), use_container_width=True):
        st.session_state.show_stats = not st.session_state.show_stats

# --- PANEL DE DASHBOARD (INTEGRADO) ---
if st.session_state.show_stats:
    with st.expander("📊 RESUMEN EJECUTIVO (BI)", expanded=True):
        df_s = get_data("sales")
        df_e = get_data("expenses")
        
        if not df_s.empty:
            df_s['date'] = pd.to_datetime(df_s['created_at'])
            today_sales = df_s[df_s['date'].dt.date == datetime.now().date()]
            total_today = today_sales['total'].sum()
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Ventas Hoy", f"${total_today:,.2f}", f"{len(today_sales)} ops")
            
            # Gráfico rápido
            daily = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
            fig = px.area(daily, x='date', y='total', title="Tendencia de Ingresos", height=200, color_discrete_sequence=['#6366f1'])
            fig.update_layout(margin=dict(l=0,r=0,t=30,b=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos suficientes para el Dashboard.")

# --- VISTA PRINCIPAL (POS) ---
col_grid, col_ticket = st.columns([2.5, 1], gap="large")

with col_grid:
    # 🔎 SECCIÓN DE BÚSQUEDA
    try:
        from streamlit_keyup import st_keyup
        search = st_keyup("Busca por nombre o código de barras...", placeholder="Ej: Jabon, Taza, 750...", debounce=200, key="search_bar", label_visibility="collapsed")
    except ImportError:
        search = st.text_input("Buscador...", placeholder="Busca por nombre o código de barras...", label_visibility="collapsed")
    
    df_p = get_data("products")
    
    if not df_p.empty:
        # Filtrado
        if search:
            mask = df_p['name'].str.contains(search, case=False) | df_p['barcode'].str.contains(search, case=False)
            df_view = df_p[mask].head(24)
        else:
            df_view = df_p.head(24)

        # Grilla de Productos
        n_cols = 4
        for i in range(0, len(df_view), n_cols):
            cols = st.columns(n_cols)
            for j in range(n_cols):
                if i + j < len(df_view):
                    p = df_view.iloc[i + j]
                    with cols[j]:
                        # Botón Táctil
                        label = f"{p['name'][:30]}\n\n${p['price']:,.2f}"
                        if st.button(label, key=f"btn_{p['id']}", use_container_width=True):
                            # Lógica Carrito
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
        st.warning("No hay productos en el catálogo. Sincroniza desde la PC.")

with col_ticket:
    # 👤 MODULO CLIENTE
    with st.container(border=True):
        st.markdown("🎯 **CLIENTE SELECCIONADO**")
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"### {st.session_state.selected_client}")
        with c2:
            with st.popover("⚙️", help="Cambiar cliente"):
                df_c = get_data("customers")
                options = ["Mostrador"] + (df_c['name'].tolist() if not df_c.empty else [])
                sel = st.selectbox("Elegir:", options)
                if st.button("Aplicar"):
                    st.session_state.selected_client = sel
                    st.rerun()

    # 🛒 MODULO CARRITO
    st.markdown(" ")
    with st.container(border=True):
        st.markdown("📦 **ORDEN ACTUAL**")
        if not st.session_state.cart:
            st.info("El carrito está vacío.")
        else:
            total = 0
            for idx, item in enumerate(st.session_state.cart):
                sub = item['price'] * item['qty']
                total += sub
                
                with st.container():
                    st.markdown(f"**{item['name']}**")
                    q_col, p_col = st.columns([2, 1])
                    with q_col:
                        m1, m2, m3 = st.columns([1,1,1])
                        if m1.button("➖", key=f"m_{idx}"):
                            if item['qty'] > 1: item['qty'] -= 1
                            else: st.session_state.cart.pop(idx)
                            st.rerun()
                        m2.markdown(f"<p style='text-align:center; padding-top:8px;'>{item['qty']}</p>", unsafe_allow_html=True)
                        if m3.button("➕", key=f"p_{idx}"):
                            item['qty'] += 1
                            st.rerun()
                    with p_col:
                        st.markdown(f"<p style='text-align:right; font-weight:800;'>${sub:,.2f}</p>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown(f"<h1 style='text-align: right; color: var(--primary);'>${total:,.2f}</h1>", unsafe_allow_html=True)
            
            if st.button("🚀 COMPLETAR VENTA", type="primary", use_container_width=True):
                if supabase:
                    with st.spinner("Sincronizando con Tienda Física..."):
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
                            st.success("¡Venta completada! Impresión en camino...")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al sincronizar: {e}")
                else:
                    st.error("Error de conexión a la nube.")

            if st.button("Limpiar Carrito", use_container_width=True, type="secondary"):
                st.session_state.cart = []
                st.rerun()
