import streamlit as st
import pandas as pd
import openpyxl
import zipfile
import os
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
            tablas[nombre] = {'columnas': [], 'pk': [], 'fk': []}
            
            bloque = frag[match_nombre.end():frag.rfind(')')]
            lineas = bloque.split(',')
            
            for linea in lineas:
                linea = linea.strip()
                if not linea: continue
                
                if re.match(r'PRIMARY KEY', linea, re.IGNORECASE):
                    pk_match = re.search(r'\(`?([^`)]+)`?\)', linea)
                    if pk_match: tablas[nombre]['pk'].append(pk_match.group(1))
                elif re.match(r'(CONSTRAINT.*)?FOREIGN KEY', linea, re.IGNORECASE):
                    fk_match = re.search(r'FOREIGN KEY\s*\(`?([^`)]+)`?\)\s*REFERENCES\s*`?([^`\s]+)`?\s*\(`?([^`)]+)`?\)', linea, re.IGNORECASE)
                    if fk_match:
                        tablas[nombre]['fk'].append({'columna': fk_match.group(1), 'tabla_ref': fk_match.group(2), 'col_ref': fk_match.group(3)})
                elif not re.match(r'(UNIQUE|KEY|CONSTRAINT)\b', linea, re.IGNORECASE):
                    col_match = re.match(r'`?([a-zA-Z0-9_]+)`?', linea)
                    if col_match: tablas[nombre]['columnas'].append(col_match.group(1))
                        
    return orden_tablas, tablas, db_nombre

def verificar_coincidencia_tablas(tablas_sql, datos_cargados):
    tablas_sql_set = set(tablas_sql)
    tablas_datos_set = set(datos_cargados.keys())
    return tablas_sql_set.issubset(tablas_datos_set) or tablas_datos_set.issubset(tablas_sql_set)

# =====================================================================
# PASO 1: PROTOCOLO HAYAKAWA 1 (Seguridad)
# =====================================================================
st.subheader("🔒 [PROTOCOLO HAYAKAWA 1]")
frase_input = st.text_input("Responde la pregunta de seguridad: *dame tu coleta la quiero tela exijo sera mi…*", type="password")

if frase_input:
    acceso_total = (limpiar_texto(frase_input) == limpiar_texto("Mi reliquia familiar"))
    
    if acceso_total:
        st.success("🔓 ¡Correcto! Acceso total concedido al núcleo de Kyomoto.")
        modos_disponibles = [
            '1. Crear Plantilla Estructural de Excel',
            '2. Esenciales: Inserts + CSV/Excel + Instructivos',
            '3. MEGA PRO: Todo + CRUD + Auditoría y Seguridad'
        ]
    else:
        st.warning("🚨 Respuesta incorrecta. Acceso restringido ÚNICAMENTE al Modo Básico.")
        modos_disponibles = [
            '1. Crear Plantilla Estructural de Excel (Única opción disponible)'
        ]

    st.markdown("---")
    st.subheader("⚙ CONFIGURACIÓN DE OPERACIÓN")
    
    modo_elegido = st.selectbox("Selecciona el Modo:", modos_disponibles)
    
    tipo_insercion_txt = st.selectbox(
        "Tipo de Inserción SQL:",
        ['INSERT INTO (Estándar)', 'INSERT IGNORE (Omite duplicados)', 'REPLACE INTO (Sobrescribe duplicados)']
    )
    
    st.markdown("---")
    st.subheader("📁 CARGA DE ARCHIVOS")
    st.info("💡 Sube tu archivo `.sql` (o `.txt`) y tus archivos de datos (`.xlsx`, `.csv`) aquí mismo sin restricciones desde tu celular o PC.")
    
    archivos_cargados = st.file_uploader("Seleccionar Archivos", accept_multiple_files=True, type=['sql', 'txt', 'xlsx', 'xls', 'csv'])
    
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
            archivos_csv_subidos = []
            excel_cargado = None
            
            cmd_sql = "INSERT INTO"
            if "IGNORE" in tipo_insercion_txt: cmd_sql = "INSERT IGNORE INTO"
            elif "REPLACE" in tipo_insercion_txt: cmd_sql = "REPLACE INTO"

            for nombre, contenido in uploaded_dict.items():
                if nombre.endswith('.sql') or nombre.endswith('.txt'):
                    try: decodificado = contenido.decode('utf-8')
                    except UnicodeDecodeError: decodificado = contenido.decode('latin-1')
                        
                    if nombre.endswith('.sql') or "CREATE TABLE" in decodificado.upper():
                        if not sql_texto:
                            sql_texto = decodificado
                            
                elif nombre.endswith(('.xlsx', '.xls')):
                    excel_cargado = nombre
                    with open(nombre, 'wb') as f: f.write(contenido)
                elif nombre.endswith('.csv'):
                    archivos_csv_subidos.append(nombre)
                    with open(nombre, 'wb') as f: f.write(contenido)

            modo_id = modo_elegido[0]

            if modo_id == "1":
                if not sql_texto:
                    st.error("❌ Error: Se requiere obligatoriamente el archivo .sql guía.")
                else:
                    orden_t, dic_t, _ = parsear_sql_estricto(sql_texto)
                    ruta_plantilla = "Kyomoto_Plantilla_Estructural.xlsx"
                    with pd.ExcelWriter(ruta_plantilla, engine='openpyxl') as writer:
                        for t in orden_t:
                            pd.DataFrame(columns=dic_t[t]['columnas']).to_excel(writer, sheet_name=t, index=False)
                    
                    st.success("✅ Plantilla estructural generada con éxito.")
                    with open(ruta_plantilla, "rb") as f:
                        st.download_button("📥 Descargar Plantilla Excel", f, file_name="Kyomoto_Plantilla_Estructural.xlsx")
            else:
                if not sql_texto:
                    st.error("❌ Error crítico: Se necesita el archivo .sql para validar estructuras.")
                else:
                    datos_en_memoria = {}
                    if excel_cargado:
                        datos_en_memoria = pd.read_excel(excel_cargado, sheet_name=None)
                    elif archivos_csv_subidos:
                        for arch in archivos_csv_subidos:
                            datos_en_memoria[Path(arch).stem] = pd.read_csv(arch)

                    orden_t, dic_t, nombre_db = parsear_sql_estricto(sql_texto)
                    estructuras_ok = verificar_coincidencia_tablas(orden_t, datos_en_memoria)

                    if not estructuras_ok:
                        st.warning("⚠ [ALERTA DE ESTRUCTURA]: Los nombres de tus tablas no coinciden con el SQL guía.")
                        clave_rescate = st.text_input("🔒 [Protocolo Hayakawa 2] - Inscribe la clave de rescate:", type="password")
                        
                        if clave_rescate:
                            if clave_rescate == "Easy revenge":
                                st.success("🔓 [Protocolo Hayakawa 2]: Clave correcta. Kyomoto ha corregido las estructuras.")
                                datos_mapeados = {}
                                for t_sql in orden_t:
                                    for t_csv, df in datos_en_memoria.items():
                                        if limpiar_texto(t_sql) in limpiar_texto(t_csv) or limpiar_texto(t_csv) in limpiar_texto(t_sql):
                                            datos_mapeados[t_sql] = df
                                if not datos_mapeados:
                                    datos_mapeados = datos_en_memoria
                                
                                zip_path = generar_kit_final(orden_t, dic_t, nombre_db, datos_mapeados, sql_texto, cmd_sql, modo_id, carpeta_salida)
                                with open(zip_path, "rb") as f:
                                    st.download_button("📦 Descargar Kit Kyomoto Ecosystem (.zip)", f, file_name="Kyomoto_Ecosystem.zip", mime="application/zip")
                            else:
                                st.error("🚨 Clave incorrecta. Sistema bloqueado.")
                    else:
                        zip_path = generar_kit_final(orden_t, dic_t, nombre_db, datos_en_memoria, sql_texto, cmd_sql, modo_id, carpeta_salida)
                        st.success("✅ ¡Kit Kyomoto (京本) generado con éxito!")
                        with open(zip_path, "rb") as f:
                            st.download_button("📦 Descargar Kit Kyomoto Ecosystem (.zip)", f, file_name="Kyomoto_Ecosystem.zip", mime="application/zip")

def generar_kit_final(orden_t, dic_t, nombre_db, datos_en_memoria, sql_texto, cmd_sql, modo_elegido, carpeta_salida):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    inserts_totales = []
    
    for t, df in datos_en_memoria.items():
        if t in dic_t:
            cols = ", ".join(df.columns)
            lineas_tabla = [f"\n-- INSERTS: {t}"]
            for _, fila in df.iterrows():
                vals = ["NULL" if pd.isna(v) else (str(v) if isinstance(v, (int, float)) else f"'{str(v).replace(chr(39), chr(39)+chr(39))}'") for v in fila]
                lineas_tabla.append(f"{cmd_sql} {t} ({cols}) VALUES ({', '.join(vals)});")
            inserts_totales.append("\n".join(lineas_tabla))

    inserts_texto = "\n".join(inserts_totales)

    with open(f"{carpeta_salida}/01_solo_inserts.sql", 'w', encoding='utf-8') as f: f.write(inserts_texto)
    with open(f"{carpeta_salida}/02_BACKUP_MAESTRO_{timestamp}.sql", 'w', encoding='utf-8') as f:
        f.write(sql_texto + "\n\n" + inserts_texto)

    with open(f"{carpeta_salida}/03_INSTRUCTIVO_IMPORTACION.txt", 'w', encoding='utf-8') as f:
        f.write(f"BASE DE DATOS: {nombre_db}\nORDEN ESTRICTO DE IMPORTACION:\n" + "\n".join([f"{i}. {t}" for i, t in enumerate(orden_t, 1)]))

    if modo_elegido == "3":
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

    shutil.make_archive("Kyomoto_Ecosystem", 'zip', carpeta_salida)
    return "Kyomoto_Ecosystem.zip"
