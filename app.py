
import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import pytz
import time

# --- Configuración Inicial ---
st.set_page_config(page_title="Vertex Cloud", page_icon="☁️", layout="wide")

# Inicializar Supabase
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("⚠️ Configura las credenciales en .streamlit/secrets.toml")
    st.stop()

@st.cache_resource
def init_connection():
    return create_client(URL, KEY)

supabase = init_connection()

# --- Estados de Sesión (Carrito) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- Funciones de Utilidad ---
def get_mexico_time():
    return datetime.now(pytz.timezone('America/Mexico_City'))

def format_currency(value):
    return f"${value:,.2f}"

# --- Lógica de Base de Datos ---
def get_products():
    response = supabase.table('products').select("*").order('name').execute()
    return pd.DataFrame(response.data)

def get_customers():
    response = supabase.table('customers').select("*").order('name').execute()
    return pd.DataFrame(response.data)

def create_sale(items, total, customer_name="Mostrador", payment_method="Efectivo"):
    try:
        # 1. Preparar datos de venta (JSON)
        items_data = [
            {
                "id": item['id'],
                "name": item['name'],
                "price": item['price'],
                "quantity": item['qty'],
                "total": item['price'] * item['qty']
            } for item in items
        ]
        
        count = sum(item['qty'] for item in items)
        folio = f"WEB-{int(time.time())}"
        
        payload = {
            "folio": folio,
            "total": total,
            "items_count": count,
            "items_data": items_data, # JSONB
            "payment_method": payment_method,
            "status": "completed",
            "source": "web", # IMPORTANTE: Marca origen web
            "customer_name": customer_name,
            "local_id": None # Esperando sync de escritorio
        }
        
        # 2. Insertar Venta
        supabase.table("sales").insert(payload).execute()
        
        # 3. Actualizar Stock en Nube (Inmediato visualmente)
        for item in items:
            current_stock = item['max_stock'] # Stock al momento de cargar
            new_stock = current_stock - item['qty']
            supabase.table("products").update({"stock": new_stock}).eq("id", item['id']).execute()
            
        return True, folio
    except Exception as e:
        return False, str(e)

# --- UI ---

st.title("☁️ Vertex Cloud POS")
st.markdown(f"*Sincronizado con Escritorio en tiempo real*")

# Tabs Principales
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🛒 Punto de Venta", "📦 Inventario", "busts_in_silhouette: Clientes"])

# --- TAB 1: DASHBOARD ---
with tab1:
    if st.button('🔄 Actualizar Métricas'):
        st.cache_data.clear()
        st.rerun()

    try:
        # Obtener ventas de HOY (Web + Desktop)
        response = supabase.table('sales').select("*").order('created_at', desc=True).limit(100).execute()
        df_sales = pd.DataFrame(response.data)
        
        if not df_sales.empty:
            df_sales['created_at'] = pd.to_datetime(df_sales['created_at'])
            mx_tz = pytz.timezone('America/Mexico_City')
            df_sales['created_at'] = df_sales['created_at'].dt.tz_convert(mx_tz)
            
            today = get_mexico_time().date()
            df_today = df_sales[df_sales['created_at'].dt.date == today]
            
            # KPIS
            col1, col2, col3, col4 = st.columns(4)
            total_today = df_today['total'].sum()
            count_today = len(df_today)
            web_sales = len(df_today[df_today['source'] == 'web'])
            
            col1.metric("Venta Total Hoy", format_currency(total_today))
            col2.metric("Transacciones", count_today)
            col3.metric("Ticket Promedio", format_currency(total_today/count_today) if count_today > 0 else "$0")
            col4.metric("Ventas Web", web_sales)
            
            st.divider()
            st.subheader("Últimas Ventas")
            st.dataframe(
                df_today[['folio', 'customer_name', 'total', 'payment_method', 'source', 'created_at']].rename(columns={
                    'source': 'Origen', 'customer_name': 'Cliente'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Sin ventas recientes.")
            
    except Exception as e:
        st.error(f"Error cargando dashboard: {e}")

# --- TAB 2: PUNTO DE VENTA (POS) ---
with tab2:
    col_cart, col_products = st.columns([1, 2])
    
    # 1. Selector de Productos (lado derecho)
    with col_products:
        st.subheader("Catálogo")
        df_prods = get_products()
        
        if not df_prods.empty:
            search = st.text_input("🔍 Buscar producto...", key="search_pos")
            if search:
                mask = df_prods['name'].str.contains(search, case=False) | df_prods['barcode'].str.contains(search, na=False)
                df_prods = df_prods[mask]
            
            # Grid de productos
            for index, row in df_prods.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**{row['name']}**")
                    c1.caption(f"Stock Nube: {row['stock']}")
                    c2.markdown(f"**${row['price']}**")
                    if c3.button("➕", key=f"add_{row['id']}"):
                        product = {
                            "id": row['id'], 
                            "name": row['name'], 
                            "price": row['price'], 
                            "qty": 1,
                            "max_stock": row['stock']
                        }
                        # Add to cart logic
                        found = False
                        for item in st.session_state.cart:
                            if item['id'] == product['id']:
                                item['qty'] += 1
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append(product)
                        st.toast(f"Agregado: {row['name']}")
                        st.rerun() # Refresh to update cart
        else:
            st.warning("No hay productos en la nube.")

    # 2. Carrito (lado izquierdo)
    with col_cart:
        st.subheader(f"🛒 Carrito ({len(st.session_state.cart)})")
        
        if st.session_state.cart:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                subtotal = item['price'] * item['qty']
                total += subtotal
                
                with st.container(border=True):
                    st.text(f"{item['name']}")
                    c1, c2 = st.columns(2)
                    c1.text(f"{item['qty']} x ${item['price']}")
                    c2.text(f"= ${subtotal}")
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
            
            st.divider()
            st.metric("Total a Pagar", format_currency(total))
            
            # Checkout Form
            customers_df = get_customers()
            client_list = ["Mostrador"] + customers_df['name'].tolist() if not customers_df.empty else ["Mostrador"]
            
            selected_client = st.selectbox("Cliente", client_list)
            payment_avg = st.selectbox("Método Pago", ["Efectivo", "Tarjeta", "Transferencia"])
            
            if st.button("✅ Cobrar Venta", type="primary", use_container_width=True):
                success, msg = create_sale(st.session_state.cart, total, selected_client, payment_avg)
                if success:
                    st.success(f"Venta {msg} exitosa!")
                    st.session_state.cart = []
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Error: {msg}")
                    
            if st.button("❌ Cancelar"):
                st.session_state.cart = []
                st.rerun()
        else:
            st.info("El carrito está vacío.")

# --- TAB 3: INVENTARIO ---
with tab3:
    st.header("Gestión de Inventario")
    
    with st.expander("➕ Crear Nuevo Producto"):
        with st.form("new_product_cloud"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nombre")
            barcode = c1.text_input("Código Barras")
            price = c2.number_input("Precio", min_value=0.0)
            stock = c2.number_input("Stock Inicial", min_value=0, step=1)
            
            if st.form_submit_button("Guardar"):
                if name:
                    supabase.table("products").insert({
                            "name": name, "barcode": barcode, 
                            "price": price, "stock": stock,
                            "local_id": None # Pendiente sync
                    }).execute()
                    st.success("Producto creado. Se descargará al escritorio pronto.")
                else:
                    st.error("Falta nombre.")

    # Listado
    st.subheader("Productos existentes")
    df_inv = get_products()
    if not df_inv.empty:
        # Asegurar que existan las columnas para evitar errores si la DB es vieja
        cols = ['name', 'price', 'stock', 'barcode']
        for col in cols:
            if col not in df_inv.columns:
                df_inv[col] = None # Rellenar columnas faltantes
        st.dataframe(df_inv[cols], use_container_width=True)
    else:
        st.info("⚠️ El inventario en la nube está vacío. Crea productos aquí o sincroniza desde tu caja.")

# --- TAB 4: CLIENTES ---
with tab4:
    st.header("Directorio de Clientes")
    
    with st.expander("➕ Registrar Cliente"):
        with st.form("new_customer"):
            name = st.text_input("Nombre Completo")
            email = st.text_input("Email")
            phone = st.text_input("Teléfono")
            rfc = st.text_input("RFC")
            
            if st.form_submit_button("Guardar Cliente"):
                if name:
                    supabase.table("customers").insert({
                        "name": name, "email": email, "phone": phone, "rfc": rfc,
                        "local_id": None
                    }).execute()
                    st.success("Cliente guardado en nube.")
                else:
                    st.error("El nombre es obligatorio")
    
    st.dataframe(get_customers()[['name', 'email', 'phone']], use_container_width=True)
