import streamlit as st
import pandas as pd
import zipfile
import os
import re
import datetime
from pathlib import Path
import io

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
# PROTOCOLO HAYAKAWA Y MODO SECRETO
# =====================================================================
st.subheader("🔒 [PROTOCOLO HAYAKAWA]")
frase_input = st.text_input("Introduce la clave o frase de acceso secreta:", type="password")

# Definimos las contraseñas válidas de forma limpia
pass_vip = limpiar_texto("trapitos sexys")
pass_normal = limpiar_texto("Mi reliquia familiar")

if frase_input:
    texto_limpio = limpiar_texto(frase_input)
    
    if texto_limpio == pass_vip:
        st.success("🌸 ¡PROTOCOLO VIP ACTIVATED! a pumps le gustan los frutilupis 🍓🥣")
        modos_disponibles = [
            '4. 💎 MODO VIP: Vault de Respaldos Privados y Carga Maestra',
            '1. Crear Plantilla Estructural de CSV',
            '2. Esenciales: Inserts + CSV + Instructivos',
            '3. MEGA PRO: Todo + CRUD + Auditoría'
        ]
    elif texto_limpio == pass_normal:
        st.success("🔓 ¡Correcto! Acceso total al núcleo de Kyomoto.")
        modos_disponibles = [
            '1. Crear Plantilla Estructural de CSV',
            '2. Esenciales: Inserts + CSV + Instructivos',
            '3. MEGA PRO: Todo + CRUD + Auditoría'
        ]
    else:
        st.warning("🚨 Contraseña incorrecta. Acceso restringido a Plantillas.")
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
    
    if "MODO VIP" in modo_elegido:
        st.info("💎 [VAULT PRIVADO]: Sube aquí tus respaldos comprimidos (.zip) o archivos confidenciales para procesarlos al instante.")
        archivos_cargados = st.file_uploader("Seleccionar Archivos VIP", accept_multiple_files=True, type=['sql', 'txt', 'csv', 'zip'])
    else:
        st.info("💡 Sube tu archivo `.sql` (o `.txt`) y tus archivos de datos (`.csv`) aquí mismo.")
        archivos_cargados = st.file_uploader("Seleccionar Archivos", accept_multiple_files=True, type=['sql', 'txt', 'csv'])
    
    if st.button("🚀 Confirmar y Ejecutar Proceso", type="primary"):
        if not archivos_cargados:
            st.error("❌ Error: Debes subir al menos un archivo.")
        else:
            uploaded_dict = {}
            for archivo in archivos_cargados:
                uploaded_dict[archivo.name] = archivo.read()
                
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
                    try:
                        datos_en_memoria[Path(nombre).stem] = pd.read_csv(io.BytesIO(contenido))
                    except Exception as e:
                        st.error(f"❌ Error leyendo el CSV {nombre}: {e}")

            zip_buffer = io.BytesIO()

            if "MODO VIP" in modo_elegido:
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    for nombre, contenido in uploaded_dict.items():
                        zip_out.writestr(nombre, contenido)
                st.success("💎 ¡Vault VIP empaquetado con éxito en memoria!")
                st.download_button("📦 Descargar Vault Privado (.zip)", zip_buffer.getvalue(), file_name="Kyomoto_Vault_VIP.zip", mime="application/zip")
            elif not sql_texto:
                st.error("❌ Error crítico: Se necesita obligatoriamente un archivo .sql guía.")
            else:
                orden_t, dic_t, nombre_db = parsear_sql_estricto(sql_texto)
                modo_id = modo_elegido[0]

                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    if modo_id == "1":
                        for t in orden_t:
                            cols = dic_t[t]['columnas'] if dic_t[t]['columnas'] else ['id', 'columna1']
                            df_temp = pd.DataFrame(columns=cols)
                            csv_nombre = f"{t}_plantilla.csv"
                            zip_out.writestr(csv_nombre, df_temp.to_csv(index=False))
                        
                        st.success("✅ Plantillas estructurales generadas con éxito.")
                        st.download_button("📥 Descargar Plantillas CSV (.zip)", zip_buffer.getvalue(), file_name="Kyomoto_Plantillas_CSV.zip", mime="application/zip")
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

                        zip_out.writestr("01_solo_inserts.sql", inserts_texto)
                        zip_out.writestr(f"02_BACKUP_MAESTRO_{timestamp}.sql", sql_texto + "\n\n" + inserts_texto)
                        
                        instructivo = f"BASE DE DATOS: {nombre_db}\nORDEN ESTRICTO DE IMPORTACION:\n" + "\n".join([f"{i}. {t}" for i, t in enumerate(orden_t, 1)])
                        zip_out.writestr("03_INSTRUCTIVO_IMPORTACION.txt", instructivo)

                        if modo_id == "3":
                            php_code = f'''<!DOCTYPE html>
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
</html>'''
                            zip_out.writestr("07_mini_php_crud/index.php", php_code)

                        st.success("✅ ¡Kit Kyomoto (京本) generado con éxito en memoria!")
                        st.download_button("📦 Descargar Kit Kyomoto Ecosystem (.zip)", zip_buffer.getvalue(), file_name="Kyomoto_Ecosystem.zip", mime="application/zip")
