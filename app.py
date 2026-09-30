import streamlit as st
import pandas as pd
import zipfile
import os
import shutil
import re
import datetime
from pathlib import Path

# Configuración de la página web
st.set_page_config(page_title="Kyomoto Engine v6.0", page_icon="⚡", layout="centered")

st.markdown("<h1 style='text-align: center;'>⚡ KYOMOTO (京本) - ENGINE v6.0 ⚡</h1>", unsafe_allow_html=True)
st.markdown("---")

def limpiar_texto(texto):
    return re.sub(r'[^a-z0-9]', '', str(texto).lower())

def parsear_sql_estricto(sql_texto):
    tablas = {}
    orden_tablas = []
    db_nombre = "jdm_motores_db"
    
    match_db = re.search(r'(?:CREATE DATABASE|USE)\s+`?([a-zA-Z0-9_]+)`?', sql_texto, flags=re.IGNORECASE)
    if match_db: db_nombre = match_db.group(1)

    fragmentos = re.split(r'CREATE TABLE', sql_texto, flags=re.IGNORECASE)[1:]
    for frag in fragmentos:
        match_nombre = re.search(r'(?:IF NOT EXISTS\s+)?`?([a-zA-Z0-9_]+)`?\s*\(', frag, flags=re.IGNORECASE)
        if match_nombre:
            nombre = match_nombre.group(1)
            orden_tablas.append(nombre)
            tablas[nombre] = {'columnas': []}
            
            bloque = frag[match_nombre.end():frag.rfind(')')]
            lineas = bloque.split(',')
            
            for linea in lineas:
                linea = linea.strip()
                if not linea: continue
                if not re.match(r'(PRIMARY KEY|UNIQUE|KEY|CONSTRAINT|FOREIGN KEY)\b', linea, re.IGNORECASE):
                    col_match = re.match(r'`?([a-zA-Z0-9_]+)`?', linea)
                    if col_match: tablas[nombre]['columnas'].append(col_match.group(1))
                        
    return orden_tablas, tablas, db_nombre

# =====================================================================
# PROTOCOLO HAYAKAWA 1 (Seguridad)
# =====================================================================
st.subheader("🔒 [PROTOCOLO HAYAKAWA 1]")
frase_input = st.text_input("Responde la pregunta de seguridad: *dame tu coleta la quiero tela exijo sera mi…*", type="password")

if frase_input:
    acceso_total = (limpiar_texto(frase_input) == limpiar_texto("Mi reliquia familiar"))
    
    if acceso_total:
        st.success("🔓 ¡Correcto! Acceso total concedido al núcleo de Kyomoto.")
        modos_disponibles = [
            '1. Crear Plantilla Estructural de CSV',
            '2. Esenciales: Inserts + CSV + Instructivos',
            '3. MEGA PRO: Todo + CRUD + Auditoría y Seguridad'
        ]
    else:
        st.warning("🚨 Respuesta incorrecta. Acceso restringido ÚNICAMENTE a Plantillas.")
        modos_disponibles = ['1. Crear Plantilla Estructural de CSV']

    st.markdown("---")
    st.subheader("⚙ CONFIGURACIÓN DE OPERACIÓN")
    
    modo_elegido = st.selectbox("Selecciona el Modo:", modos_disponibles)
    
    tipo_insercion_txt = st.selectbox(
        "Tipo de Inserción SQL:",
        ['INSERT INTO (Estándar)', 'INSERT IGNORE (Omite duplicados)', 'REPLACE INTO (Sobrescribe duplicados)']
    )
    
    st.markdown("---")
    st.subheader("📁 CARGA DE ARCHIVOS")
    st.info("💡 Sube tu archivo `.sql` (o `.txt`) y tus archivos de datos (`.csv`) aquí mismo.")
    
    archivos_cargados = st.file_uploader("Seleccionar Archivos", accept_multiple_files=True, type=['sql', 'txt', 'csv'])
    
    if st.button("🚀 Confirmar y Ejecutar Proceso", type="primary"):
        if not archivos_cargados:
            st.error("❌ Error: Debes subir al menos el archivo .sql guía.")
        else:
            uploaded_dict = {}
            for archivo in archivos_cargados:
                uploaded_dict[archivo.name] = archivo.read()
                
            carpeta_salida = "kyomoto_output"
            if os.path.exists(carpeta_salida): shutil.rmtree(carpeta_salida)
            os.makedirs(carpeta_salida, exist_ok=True)

            sql_texto = ""
            datos_en_memoria = {}
            
            cmd_sql = "INSERT INTO"
            if "IGNORE" in tipo_insercion_txt: cmd_sql = "INSERT IGNORE INTO"
            elif "REPLACE" in tipo_insercion_txt: cmd_sql = "REPLACE INTO"

            for nombre, contenido in uploaded_dict.items():
                if nombre.endswith('.sql') or nombre.endswith('.txt'):
                    try: decodificado = contenido.decode('utf-8')
                    except UnicodeDecodeError: decodificado = contenido.decode('latin-1')
                    if not sql_texto: sql_texto = decodificado
                elif nombre.endswith('.csv'):
                    ruta_csv_temp = Path(nombre)
                    with open(ruta_csv_temp, 'wb') as f: f.write(contenido)
                    try:
                        datos_en_memoria[ruta_csv_temp.stem] = pd.read_csv(ruta_csv_temp)
                    except Exception as e:
                        st.error(f"❌ Error leyendo el CSV {nombre}: {e}")

            if not sql_texto:
                st.error("❌ Error crítico: Se necesita obligatoriamente el archivo .sql guía.")
            else:
                orden_t, dic_t, nombre_db = parsear_sql_estricto(sql_texto)
                modo_id = modo_elegido[0]

                if modo_id == "1":
                    ruta_zip_plantillas = "Kyomoto_Plantillas_CSV.zip"
                    with zipfile.ZipFile(ruta_zip_plantillas, 'w') as zipf:
                        for t in orden_t:
                            cols = dic_t[t]['columnas'] if dic_t[t]['columnas'] else ['id', 'columna1']
                            df_temp = pd.DataFrame(columns=cols)
                            csv_nombre = f"{t}_plantilla.csv"
                            df_temp.to_csv(csv_nombre, index=False)
                            zipf.write(csv_nombre)
                    
                    st.success("✅ Plantillas estructurales generadas con éxito.")
                    with open(ruta_zip_plantillas, "rb") as f:
                        st.download_button("📥 Descargar Plantillas CSV (.zip)", f, file_name="Kyomoto_Plantillas_CSV.zip", mime="application/zip")
                else:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    inserts_totales = []
                    
                    for t_sql in orden_t:
                        df_a_usar = None
                        for t_csv, df in datos_en_memoria.items():
                            if limpiar_texto(t_sql) in limpiar_texto(t_csv) or limpiar_texto(t_csv) in limpiar_texto(t_sql):
                                df_a_usar = df
                                break
                        
                        if df_a_usar is None and datos_en_memoria:
                            df_a_usar = list(datos_en_memoria.values())[0]

                        if df_a_usar is not None and not df_a_usar.empty:
                            cols = ", ".join(df_a_usar.columns)
                            lineas_tabla = [f"\n-- INSERTS: {t_sql}"]
                            for _, fila in df_a_usar.iterrows():
                                vals = ["NULL" if pd.isna(v) else (str(v) if isinstance(v, (int, float)) else f"'{str(v).replace(chr(39), chr(39)+chr(39))}'") for v in fila]
                                lineas_tabla.append(f"{cmd_sql} {t_sql} ({cols}) VALUES ({', '.join(vals)});")
                            inserts_totales.append("\n".join(lineas_tabla))

                    inserts_texto = "\n".join(inserts_totales)

                    with open(f"{carpeta_salida}/01_solo_inserts.sql", 'w', encoding='utf-8') as f: f.write(inserts_texto)
                    with open(f"{carpeta_salida}/02_BACKUP_MAESTRO_{timestamp}.sql", 'w', encoding='utf-8') as f:
                        f.write(sql_texto + "\n\n" + inserts_texto)

                    with open(f"{carpeta_salida}/03_INSTRUCTIVO_IMPORTACION.txt", 'w', encoding='utf-8') as f:
                        f.write(f"BASE DE DATOS: {nombre_db}\nORDEN ESTRICTO DE IMPORTACION:\n" + "\n".join([f"{i}. {t}" for i, t in enumerate(orden_t, 1)]))

                    if modo_id == "3":
                        os.makedirs(f"{carpeta_salida}/07_mini_php_crud", exist_ok=True)
                        with open(f"{carpeta_salida}/07_mini_php_crud/index.php", 'w', encoding='utf-8') as f:
                            f.write(f'''<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Kyomoto CRUD - {nombre_db}</title></head>
<body>
    <h1>京本 CRUD - {nombre_db}</h1>
    <form method="GET">
        <input type="text" name="buscar" placeholder="Consulta...">
        <button type="submit">Buscar</button>
    </form>
    <?php
    if (isset($_GET['buscar'])) {{
        $b = trim($_GET['buscar']);
        if ($b === 'lock_back') {{
            echo '<p style="color:red; font-weight:bold;">a pumps le gustan los frutilupis</p>';
        }} else {{
            echo "<p>Resultados para: " . htmlspecialchars($b) . "</p>";
        }}
    }}
    ?>
</body>
</html>''')

                    zip_path = shutil.make_archive("Kyomoto_Ecosystem", 'zip', carpeta_salida)
                    st.success("✅ ¡Kit MEGA PRO Kyomoto (京本) generado con éxito!")
                    with open(zip_path, "rb") as f:
                        st.download_button("📦 Descargar Kit Kyomoto Ecosystem (.zip)", f, file_name="Kyomoto_Ecosystem.zip", mime="application/zip")
