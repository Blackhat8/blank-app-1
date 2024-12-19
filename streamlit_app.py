import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from collections import Counter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Configuración inicial
st.set_page_config(page_title="TI724 Incidentes Dashboard", layout="wide", page_icon="📊")

# Título de la aplicación
st.title("📊 TI724 Incidentes Dashboard")
st.sidebar.title("🔍 Navegación")

# Cargar el archivo Excel
@st.cache_data
def cargar_datos():
    try:
        ruta_archivo = 'Data/incidentes_Septiembre2024_ti724.xlsx'
        return pd.read_excel(ruta_archivo, engine='openpyxl')
    except FileNotFoundError:
        st.error("El archivo no se encuentra. Verifica la ruta.")
        return None

# Procesar datos
def procesar_datos(df):
    df['Creado'] = pd.to_datetime(df['Creado'], errors='coerce')
    df['Estado'] = df['Estado'].fillna('Sin Estado')
    df, _ = detectar_alertas_conocidas(df)
    return df

# Detectar alertas conocidas
def detectar_alertas_conocidas(df):
    alertas_tipos = {
        "Se valida la alerta y ya se encuentra superada": "Superada",
        "Se valida alerta y la misma obedece a un consumo elevado por procesos de Java": "Java",
        "consumo dentro de los recursos disponibles del servidor": "Recursos Servidor",
        "Se valida el alertamiento y estos son procesos propios del servidor": "Procesos del Servidor",
        "Se procede con el cierre del caso, ya que la unidad alertada no puede ser ampliada": "Unidad no ampliada",
        "e valida alerta y la misma obedece a un consumo elevado por procesos de ISS": "ISS",
        "se deja en monitoreo al finalizar el proceso se solventará la misma": "Monitoreo",
        "se valida la alerta en el servidor y no se ve afectación": "Sin afectación"
    }

    df['Tipo de Alerta'] = None
    for frase, tipo in alertas_tipos.items():
        df.loc[df['Notas de trabajo'].str.contains(frase, case=False, na=False), 'Tipo de Alerta'] = tipo
        df.loc[df['Notas de resolución'].str.contains(frase, case=False, na=False), 'Tipo de Alerta'] = tipo

    return df, alertas_tipos

# Generar mapa de calor
def generar_mapa_calor(df, columna_x, columna_y, titulo):
    heatmap_data = pd.crosstab(df[columna_x], df[columna_y])
    fig_heatmap = ff.create_annotated_heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns.tolist(),
        y=heatmap_data.index.tolist(),
        colorscale='Viridis',
        showscale=True
    )
    fig_heatmap.update_layout(title=titulo)
    return fig_heatmap

# Generar sugerencias con IA
def generar_sugerencias(df):
    grupos_alertas = df.groupby(['Tipo de Alerta', 'Resuelto por']).size().reset_index(name='Cantidad')
    grupos_alertas = grupos_alertas.sort_values(by='Cantidad', ascending=False)
    if not grupos_alertas.empty:
        sugerencia = grupos_alertas.iloc[0]
        return f"👨‍💻 Resolutor recomendado para el tipo de alerta '{sugerencia['Tipo de Alerta']}': {sugerencia['Resuelto por']} con {sugerencia['Cantidad']} casos."
    else:
        return "No hay suficientes datos para generar sugerencias."

# Configuración del menú
opcion = st.sidebar.radio(
    "Selecciona una sección:",
    ["Grupos Resolutores", "Alertas Conocidas - Detalles", "Resumen General", "Análisis de Frases", "Detalle de Incidente", "Análisis Avanzado"]
)

# Cargar y procesar datos
df = cargar_datos()

if df is not None:
    df = procesar_datos(df)

    if opcion == "Grupos Resolutores":
        st.header("👥 Grupos Resolutores (Resuelto por)")

        # Top 15 Resolutores
        casos_por_resolutor = df['Resuelto por'].value_counts().reset_index()
        casos_por_resolutor.columns = ['Resolutor', 'Cantidad']
        top_15_resolutores = casos_por_resolutor.head(15)

        fig_top = px.bar(
            top_15_resolutores,
            x="Resolutor",
            y="Cantidad",
            color="Cantidad",
            title="Top 15 Resolutores por Casos Resueltos",
            color_continuous_scale="Plasma"
        )
        st.plotly_chart(fig_top, use_container_width=True)

        # Mapa de calor: Resolutor vs Estado
        fig_heatmap = generar_mapa_calor(df, 'Resuelto por', 'Estado', "Resolutores vs Estado")
        st.plotly_chart(fig_heatmap, use_container_width=True)

        # Distribución porcentual de casos por resolutor
        distribucion = casos_por_resolutor.copy()
        distribucion['Porcentaje'] = (distribucion['Cantidad'] / distribucion['Cantidad'].sum()) * 100
        fig_distr = px.pie(
            distribucion,
            names='Resolutor',
            values='Cantidad',
            title="Distribución de Casos por Resolutor",
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig_distr, use_container_width=True)

    elif opcion == "Alertas Conocidas - Detalles":
        st.header("🔍 Detalles de Incidentes de Alertas Conocidas")

        # Filtro por tipo de alerta conocida
        df_alertas, alertas_tipos = detectar_alertas_conocidas(df)
        tipo_alerta_seleccionado = st.selectbox("Selecciona un Tipo de Alerta para Detallar", ["Todas"] + list(alertas_tipos.values()))
        if tipo_alerta_seleccionado == "Todas":
            alertas_filtradas = df_alertas[df_alertas['Tipo de Alerta'].notna()]
        else:
            alertas_filtradas = df_alertas[df_alertas['Tipo de Alerta'] == tipo_alerta_seleccionado]

        # Mostrar cada incidente de forma organizada
        for idx, row in alertas_filtradas.iterrows():
            st.markdown(f"### Incidente: {row['Número']}")
            st.write(f"**Resuelto por:** {row['Resuelto por']}")
            st.write(f"**Notas de Trabajo:** {row['Notas de trabajo']}")
            st.write(f"**Notas de Resolución:** {row['Notas de resolución']}")
            st.write(f"**Tipo de Alerta:** {row['Tipo de Alerta']}")
            st.write("---")

        # Gráfica interactiva con barras dinámicas
        conteo_alertas = alertas_filtradas['Resuelto por'].value_counts().reset_index()
        conteo_alertas.columns = ['Resolutor', 'Cantidad']
        fig = px.bar(
            conteo_alertas,
            x='Resolutor',
            y='Cantidad',
            color='Cantidad',
            title="Resolutores que Más Manejan Alertas Conocidas",
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Sugerencias con IA
        st.subheader("🤖 Sugerencias con IA")
        sugerencia = generar_sugerencias(alertas_filtradas)
        st.success(sugerencia)

    elif opcion == "Resumen General":
        st.header("📋 Resumen General")

        # Métricas generales
        total_casos = len(df)
        casos_resueltos = len(df[df['Estado'].isin(['Resuelta', 'Cerrada'])])
        alertas_conocidas = len(df[df['Tipo de Alerta'].notna()])

        col1, col2, col3 = st.columns(3)
        col1.metric("📋 Total de Incidentes", total_casos)
        col2.metric("✅ Casos Resueltos", casos_resueltos)
        col3.metric("⚠️ Alertas Conocidas", alertas_conocidas)

        # Gráfico de incidentes por estado
        incidentes_por_estado = df['Estado'].value_counts().reset_index()
        incidentes_por_estado.columns = ['Estado', 'Cantidad']
        fig_estado = px.pie(
            incidentes_por_estado,
            names='Estado',
            values='Cantidad',
            title="Distribución de Incidentes por Estado",
            color_discrete_sequence=px.colors.sequential.Viridis
        )
        st.plotly_chart(fig_estado, use_container_width=True)

    elif opcion == "Análisis de Frases":
        st.header("📝 Análisis de Frases Comunes")
        contador = Counter(df['Notas de trabajo'].dropna().astype(str).tolist() + df['Notas de resolución'].dropna().astype(str).tolist())
        frases_mas_repetidas = pd.DataFrame(contador.most_common(20), columns=["Frase", "Frecuencia"])
        st.dataframe(frases_mas_repetidas)

        fig = px.bar(frases_mas_repetidas, x='Frase', y='Frecuencia', color='Frecuencia',
                     color_continuous_scale='Cividis', title="Top Frases Más Repetidas")
        st.plotly_chart(fig, use_container_width=True)

    elif opcion == "Detalle de Incidente":
        st.header("🔍 Detalle de Incidente")
        numero_incidente = st.selectbox("Selecciona un Número de Incidente", df['Número'].unique())
        incidente = df[df['Número'] == numero_incidente]
        if not incidente.empty:
            st.write("### Información del Incidente")
            st.write(incidente.T)

    elif opcion == "Análisis Avanzado":
        st.header("📈 Análisis Avanzado de Datos")

        # Mapa de calor
        st.subheader("🔍 Mapa de Calor")
        columnas = df.columns.tolist()
        columna_x = st.selectbox("Selecciona la columna X:", columnas, index=1)
        columna_y = st.selectbox("Selecciona la columna Y:", columnas, index=2)

        if columna_x and columna_y:
            try:
                fig_mapa_calor = generar_mapa_calor(df, columna_x, columna_y, "Mapa de Calor Personalizado")
                st.plotly_chart(fig_mapa_calor, use_container_width=True)
            except Exception as e:
                st.error(f"Error al generar el mapa de calor: {e}")

        # Gráfica de correlaciones
        st.subheader("📊 Análisis de Correlación")
        columnas_numericas = df.select_dtypes(include=['number']).columns.tolist()

        if len(columnas_numericas) > 1:
            correlaciones = df[columnas_numericas].corr()
            fig_correlaciones = px.imshow(
                correlaciones,
                text_auto=True,
                color_continuous_scale='RdBu',
                title="Mapa de Correlación entre Variables Numéricas"
            )
            st.plotly_chart(fig_correlaciones, use_container_width=True)
        else:
            st.warning("No hay suficientes columnas numéricas para generar un análisis de correlación.")

else:
    st.error("No se pudieron cargar los datos. Verifica que el archivo esté en la ruta correcta.")
