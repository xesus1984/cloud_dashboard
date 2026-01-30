import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
import json
import numpy as np

# --- UTILIDADES DE DATOS ---
import numpy as np

# --- UTILIDADES DE DATOS ---
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)): return int(obj)
        if isinstance(obj, (np.floating, np.float64)): return float(obj)
        if isinstance(obj, (np.ndarray, list)): return [self.default(i) for i in obj]
        if isinstance(obj, (np.bool_, bool)): return bool(obj)
        if hasattr(obj, 'item'): return obj.item() # Generic numpy scalar
        return super(NpEncoder, self).default(obj)

def purify_payload(data):
    """Convierte cualquier objeto a tipos nativos serializables"""
    try:
        return json.loads(json.dumps(data, cls=NpEncoder))
    except Exception as e:
        print(f"Error purifying payload: {e}")
        return data

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="VERTEX Cloud POS v6.4 (iPad)", page_icon="⚡", layout="wide")

# --- CSS: ESTILO ESCRITORIO COMPACTO ---
st.markdown("""
<style>
    /* Ajuste GLOBAL para iPad/Touch */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 5rem !important; /* Espacio para scroll */
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    
    /* Tipografía Legible */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
        font-size: 16px !important; /* Texto base más grande */
        background-color: #f8fafc;
    }

    /* Branding VERTEX Moderno */
    .brand-section {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 0;
    }
    .brand-name {
        font-weight: 800;
        font-size: 24px;
        color: #0f172a;
        letter-spacing: -0.5px;
    }

    /* Botones de Navegación TÁCTILES */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        height: 50px !important; /* Altura táctil mínima */
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
    }

    /* Botones de Producto (Grilla) */
    div[data-testid="column"] button {
        height: 120px !important; /* Tarjetas altas */
        background-color: white !important;
        color: #334155 !important;
        border: 1px solid #e2e8f0 !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        white-space: normal !important; /* Permitir 2 líneas */
        line-height: 1.4 !important;
    }

    /* Highlight del Precio en Tarjeta */
    div[data-testid="column"] button p {
        font-size: 1.1em !important;
    }

    /* Input de Búsqueda ESTILO iOS */
    input[type="text"] {
        height: 55px !important;
        border-radius: 12px !important;
        font-size: 18px !important;
        padding-left: 20px !important;
        border: 2px solid #e2e8f0 !important;
        background-color: white !important;
    }
    input[type="text"]:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
    }

    /* Contenedores (Simulación de Glassmorphism/Cards) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 16px !important;
        padding: 15px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Títulos de Sección */
    h1, h2, h3 {
        color: #1e293b !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXIÓN ---
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

# --- ESTADO DE SESIÓN ---
if 'view' not in st.session_state: st.session_state.view = 'pos'
if 'cart' not in st.session_state: st.session_state.cart = []
if 'selected_client' not in st.session_state: st.session_state.selected_client = "Mostrador"

# Cachear datos para búsqueda fluida (60s)
@st.cache_data(ttl=60)
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- HEADER / NAVEGACIÓN ---
c_head_left, c_head_right = st.columns([1, 4])
with c_head_left:
    st.markdown('<div class="brand-section"><span class="brand-name">VERTEX</span></div>', unsafe_allow_html=True)

with c_head_right:
    n1, n2, n3, n4 = st.columns(4)
    if n1.button("Punto de Venta", use_container_width=True): st.session_state.view = 'pos'
    if n2.button("Articulos", use_container_width=True): st.session_state.view = 'articles'
    if n3.button("Dashboard", use_container_width=True): st.session_state.view = 'dashboard'
    if n4.button("Clientes", use_container_width=True): st.session_state.view = 'clients'

st.divider()

# --- VISTA: PUNTO DE VENTA ---
if st.session_state.view == 'pos':
    col_grid, col_ticket = st.columns([2.8, 1])
    
    with col_grid:
        # Búsqueda en tiempo real (debounce 300ms)
        from streamlit_keyup import st_keyup
        search = st_keyup("Buscar...", placeholder="Buscar producto o codigo...", debounce=300, key="search_input", label_visibility="collapsed")
        
        df_p = get_data("products")
        if search:
            # Soporte para lector de código de barras: 
            # Si hay un match exacto por barcode, añadir al carrito directamente
            exact_match = df_p[df_p['barcode'] == search.strip()]
            if not exact_match.empty:
                p = exact_match.iloc[0]
                found = False
                for item in st.session_state.cart:
                    if item['id'] == p['id']:
                        item['qty'] += 1
                        found = True
                        break
                if not found:
                    st.session_state.cart.append({
                        "id": int(p['id']), "name": str(p['name']), "price": float(p['price']), "qty": 1, "barcode": str(p.get('barcode', ''))
                    })
                st.toast(f"Añadido: {p['name']}")
                # Filtrar visualmente
                df_p = df_p[df_p['name'].str.contains(search, case=False)]
            else:
                df_p = df_p[df_p['name'].str.contains(search, case=False) | df_p['barcode'].str.contains(search, case=False)]
            
            n_cols = 5
            for i in range(0, len(df_p), n_cols):
                cols = st.columns(n_cols)
                for j in range(n_cols):
                    if i + j < len(df_p):
                        p = df_p.iloc[i + j]
                        with cols[j]:
                            label = f"{p['name'][:30]}\n\n**${p['price']:,.2f}**"
                            if st.button(label, key=f"p_{p['id']}", use_container_width=True):
                                found = False
                                for item in st.session_state.cart:
                                    if item['id'] == p['id']:
                                        item['qty'] += 1
                                        found = True
                                        break
                                if not found:
                                    st.session_state.cart.append({
                                        "id": int(p['id']), 
                                        "name": str(p['name']), 
                                        "price": float(p['price']), 
                                        "qty": 1,
                                        "barcode": str(p.get('barcode', ''))
                                    })
                                st.rerun()

    with col_ticket:
        # TARJETA 1: CLIENTE (ARRIBA)
        with st.container(border=True):
            st.markdown("**Cliente**")
            c_label, c_btn = st.columns([3, 2])
            c_label.write(st.session_state.selected_client)
            with c_btn:
                with st.popover("Cambiar", use_container_width=True):
                    cust_df = get_data("customers")
                    c_options = ["Mostrador"] + (cust_df['name'].tolist() if not cust_df.empty else [])
                    search_c = st.selectbox("Elegir:", c_options)
                    if st.button("Aplicar"):
                        st.session_state.selected_client = search_c
                        st.rerun()
                    st.divider()
                    new_c = st.text_input("Nuevo:")
                    if st.button("Registrar"):
                        supabase.table("customers").insert({"name": new_c}).execute()
                        st.session_state.selected_client = new_c
                        st.rerun()

        # TARJETA 2: CARRITO (ABAJO)
        with st.container(border=True):
            st.markdown("**Carrito**")
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                df_cart['Total'] = df_cart['price'] * df_cart['qty']
                
                st.dataframe(
                    df_cart[['name', 'qty', 'Total']], 
                    hide_index=True, 
                    use_container_width=True,
                    height=250 # Altura controlada para evitar scroll infinito
                )
                
                # Calcular total
                total = float(df_cart['Total'].sum())
                st.markdown(f"<h3 style='text-align: right;'>Total: ${total:,.2f}</h3>", unsafe_allow_html=True)

                if st.button("COBRAR", type="primary", use_container_width=True):
                    folio = f"W-{int(time.time())}"
                    
                    try:
                        # 1. Limpiar Carrito
                        clean_cart = []
                        for it in st.session_state.cart:
                            clean_cart.append({
                                "id": int(it['id']),
                                "name": str(it['name']),
                                "price": float(it['price']),
                                "qty": int(it['qty']),
                                "barcode": str(it.get('barcode', ''))
                            })

                        # 2. Preparar y Purificar Payload
                        sale_data = purify_payload({
                            "folio": folio,
                            "total": float(total),
                            "source": "web",
                            "customer_name": str(st.session_state.selected_client),
                            "items_data": clean_cart
                        })

                        # 3. Insertar
                        supabase.table("sales").insert(sale_data).execute()
                        
                        st.session_state.cart = []
                        st.success(f"Venta {folio} enviada. ¡Cocinando ticket!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al procesar: {str(e)}")
                
                if st.button("Limpiar", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Ticket vacio")

# --- OTRAS VISTAS (Dashboard, Articulos, Clientes) permanecen igual ---
elif st.session_state.view == 'dashboard':
    from datetime import datetime, timedelta
    
    st.subheader("📊 Inteligencia de Negocio")
    
    # --- FILTROS ---
    c_flt1, c_flt2 = st.columns([1, 3])
    with c_flt1:
        range_opt = st.selectbox("Periodo", ["Hoy", "Esta Semana", "Este Mes", "Todo el Año"])
    
    # Calcular fechas
    today = datetime.now()
    if range_opt == "Hoy":
        start_date = today.date()
    elif range_opt == "Esta Semana":
        start_date = (today - timedelta(days=today.weekday())).date()
    elif range_opt == "Este Mes":
        start_date = today.date().replace(day=1)
    else:
        start_date = today.date().replace(month=1, day=1)
        
    # --- CARGA DE DATOS ---
    with st.spinner("Analizando finanzas..."):
        df_sales = get_data("sales")
        df_expenses = get_data("expenses")
        
        # Procesar Ventas
        if not df_sales.empty:
            df_sales['date_dt'] = pd.to_datetime(df_sales['created_at'])
            df_sales['date_only'] = df_sales['date_dt'].dt.date
            # Filtrar
            mask_s = df_sales['date_only'] >= start_date
            df_s_filtered = df_sales.loc[mask_s].copy()
        else:
            df_s_filtered = pd.DataFrame(columns=['total', 'date_only'])

        # Procesar Gastos
        if not df_expenses.empty:
            # Expenses date suele venir como YYYY-MM-DD string o ts
            df_expenses['date_dt'] = pd.to_datetime(df_expenses['date'])
            df_expenses['date_only'] = df_expenses['date_dt'].dt.date
            # Filtrar
            mask_e = df_expenses['date_only'] >= start_date
            df_e_filtered = df_expenses.loc[mask_e].copy()
        else:
            df_e_filtered = pd.DataFrame(columns=['amount', 'category', 'date_only'])

    if df_s_filtered.empty and df_e_filtered.empty:
        st.info("No hay datos financieros para este periodo.")
    else:
        # --- KPIs FINANCIEROS ---
        total_income = df_s_filtered['total'].sum() if not df_s_filtered.empty else 0
        total_outcome = df_e_filtered['amount'].sum() if not df_e_filtered.empty else 0
        balance = total_income - total_outcome
        
        # Margen simple (asumiendo que outcome son costos op + costos venta si se registran ahi)
        # Ojo: Para utilidad real necesitamos Costo de Venta. Si no lo tenemos, esto es Cash Flow.
        margin_pct = (balance / total_income * 100) if total_income > 0 else 0
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ingresos", f"${total_income:,.2f}", f"{len(df_s_filtered)} Ops")
        k2.metric("Egresos", f"${total_outcome:,.2f}", f"{len(df_e_filtered)} Movs", delta_color="inverse")
        k3.metric("Flujo Neto", f"${balance:,.2f}", f"{margin_pct:.1f}% Margen", delta_color="normal" if balance >= 0 else "inverse")
        ticket_prom = total_income / len(df_s_filtered) if not df_s_filtered.empty else 0
        k4.metric("Ticket Promedio", f"${ticket_prom:,.2f}")
        
        st.divider()
        
        # --- GRÁFICOS ---
        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.markdown("**Evolución Diaria (Ingresos vs Egresos)**")
            # Agrupar por día
            daily_income = df_s_filtered.groupby('date_only')['total'].sum().reset_index()
            daily_income['Type'] = 'Ingreso'
            daily_income.rename(columns={'total': 'Monto', 'date_only': 'Fecha'}, inplace=True)
            
            daily_outcome = df_e_filtered.groupby('date_only')['amount'].sum().reset_index()
            daily_outcome['Type'] = 'Egreso'
            daily_outcome.rename(columns={'amount': 'Monto', 'date_only': 'Fecha'}, inplace=True)
            
            df_chart = pd.concat([daily_income, daily_outcome])
            
            if not df_chart.empty:
                fig = px.bar(df_chart, x='Fecha', y='Monto', color='Type', 
                             barmode='group', color_discrete_map={'Ingreso': '#10b981', 'Egreso': '#ef4444'})
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
                st.plotly_chart(fig, use_container_width=True)
                
        with g2:
            st.markdown("**Desglose de Gastos**")
            if not df_e_filtered.empty:
                fig2 = px.pie(df_e_filtered, values='amount', names='category', hole=0.4)
                fig2.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300, showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sin gastos registrados")

        # --- DETALLE RECIENTE ---
        st.markdown("**Últimos Movimientos**")
        # Mostrar ultimas 5 ventas y ultimos 5 gastos
        t1, t2 = st.tabs(["Ventas Recientes", "Gastos Recientes"])
        
        with t1:
            st.dataframe(
                df_s_filtered.sort_values('created_at', ascending=False).head(10)[['folio', 'total', 'payment_method', 'created_at']],
                use_container_width=True, hide_index=True
            )
            
        with t2:
             if not df_e_filtered.empty:
                st.dataframe(
                    df_e_filtered.sort_values('date', ascending=False).head(10)[['category', 'description', 'amount', 'date']],
                    use_container_width=True, hide_index=True
                )
             else:
                 st.write("Sin registros.")

elif st.session_state.view == 'articles':
    st.subheader("Articulos")
    df_art = get_data("products")
    st.dataframe(df_art[['name', 'price', 'stock']], use_container_width=True, hide_index=True)

elif st.session_state.view == 'clients':
    st.subheader("Clientes")
    df_cl = get_data("customers")
    st.dataframe(df_cl[['name', 'email', 'phone']], use_container_width=True, hide_index=True)
