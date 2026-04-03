import pdfplumber
import pandas as pd
import os
import re
import math
import json

ARCHIVO_REGLAS = "reglas_usuario.json"

def cargar_reglas():
    base = {"CHILE": {}, "FALA": {}}
    if os.path.exists(ARCHIVO_REGLAS):
        try:
            with open(ARCHIVO_REGLAS, 'r', encoding='utf-8') as f:
                contenido = f.read().strip()
                return json.loads(contenido) if contenido else base
        except Exception:
            return base
    return base

def guardar_reglas(reglas):
    with open(ARCHIVO_REGLAS, 'w', encoding='utf-8') as f:
        json.dump(reglas, f, ensure_ascii=False, indent=4)

def producto_existe(nombre_nuevo, reglas):
    nombre_nuevo = nombre_nuevo.strip().upper()
    for banco in reglas:
        for info in reglas[banco].values():
            if info[0].upper() == nombre_nuevo:
                return True
    return False

def solicitar_regla_nueva(item):
    print("\n" + "═"*60)
    print(" 🔎 DETALLE DEL GASTO ENCONTRADO")
    print("═"*60)
    print(f" 🏦 BANCO:       {item['BANCO']}")
    print(f" 📝 DESCRIPCIÓN: {item['D']}")
    print(f" 📅 FECHA:       {item['F']}")
    print(f" 💰 MONTO CUOTA: ${item['VM']:,}")
    print(f" 📊 CUOTAS:      {item['CP']} de {item['CT']}")
    print("─"*60)
    
    while True:
        producto = input(" ❓ ¿Qué producto es? (Nombre ÚNICO): ").strip().upper()
        if not producto: continue
        if producto_existe(producto, cargar_reglas()):
            print(f" ❌ El nombre '{producto}' ya existe. Usa uno más específico.")
        else:
            break
            
    opciones_pago = ["JAVIER", "MAMA", "PAPA", "PADRINO", "OTROS"]
    print("\n 👤 ¿Quién paga este producto?")
    for i, opcion in enumerate(opciones_pago, 1):
        print(f"    {i}. {opcion}")
    
    while True:
        seleccion = input("\n Selecciona un número (1-5): ").strip()
        if seleccion == "1": pagador = "JAVIER"; break
        elif seleccion == "2": pagador = "MAMA"; break
        elif seleccion == "3": pagador = "PAPA"; break
        elif seleccion == "4": pagador = "PADRINO"; break
        elif seleccion == "5": 
            pagador = input(" 📝 Escribe el nombre del pagador: ").strip().upper()
            break
        else:
            print(" ⚠️ Selección inválida.")
    return [producto, pagador]

def procesar_gastos_consolidado():
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    archivos_pdf = [f for f in os.listdir(ruta_actual) if f.lower().endswith('.pdf')]
    if not archivos_pdf: return print("❌ No hay archivos PDF.")

    reglas = cargar_reglas()
    movimientos = []

    for archivo in archivos_pdf:
        es_fala = "FALA" in archivo.upper()
        with pdfplumber.open(os.path.join(ruta_actual, archivo)) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if not texto: continue
                for linea in texto.split('\n'):
                    if any(x in linea.upper() for x in ["ADMINISTRACION", "IMPUESTO", "COMISION", "LEY 3475"]): continue
                    
                    item = None
                    if es_fala:
                        m = re.search(r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+[\d.]+\s+([\d.]+)\s+(\d+)/(\d+)(?:\s+.*?\s+([\d.]+))?", linea)
                        if m:
                            v_m = int(m.group(6).replace('.', '')) if m.group(6) else math.ceil(int(m.group(3).replace('.', '')) / int(m.group(5)))
                            item = {'BANCO': 'FALABELLA', 'F': m.group(1), 'D': m.group(2).strip().upper(), 'CP': int(m.group(4)), 'CT': int(m.group(5)), 'VM': v_m}
                    else:
                        m = re.search(r"([A-Z\s]+\s(\d{2}/\d{2}/(\d{2}))\s\d+)\s+(.*?)\$\s*[\d.]+\s*\$\s*[\d.]+\s*(\d+)/(\d+)\s*\$\s*([\d.]+)", linea)
                        if m:
                            item = {'BANCO': 'CHILE', 'F': m.group(2), 'D': m.group(4).strip().upper(), 'CP': int(m.group(5)), 'CT': int(m.group(6)), 'VM': int(m.group(7).replace('.', ''))}

                    if item:
                        b_key = "FALA" if es_fala else "CHILE"
                        llave = f"{item['F']} {item['D']} | ${item['VM']} | {item['CT']}C"

                        if llave in reglas[b_key]:
                            prod, pagador = reglas[b_key][llave]
                        else:
                            prod, pagador = solicitar_regla_nueva(item)
                            reglas[b_key][llave] = [prod, pagador]
                            guardar_reglas(reglas)

                        # --- LÓGICA DE PROYECCIÓN ---
                        pago_hoy = item['VM'] if item['CP'] > 0 else 0
                        pago_mes_1 = item['VM'] if item['CP'] < item['CT'] else 0
                        pago_mes_2 = item['VM'] if (item['CP'] + 1) < item['CT'] else 0

                        movimientos.append({
                            'BANCO': item['BANCO'], 'PRODUCTO': prod, 'QUIEN PAGA': pagador,
                            'VALOR CUOTA': item['VM'], 'CUOTA ACTUAL': item['CP'], 'TOTAL CUOTAS': item['CT'],
                            'PAGO HOY': pago_hoy, 'PAGO MES +1': pago_mes_1, 'PAGO MES +2': pago_mes_2
                        })

    if movimientos:
        df = pd.DataFrame(movimientos)
        
        # Resumen de pagos proyectados por persona
        resumen_proyectado = df.groupby('QUIEN PAGA')[['PAGO HOY', 'PAGO MES +1', 'PAGO MES +2']].sum().reset_index()
        
        with pd.ExcelWriter("Control_Gastos_Proyectado.xlsx") as writer:
            df.to_excel(writer, sheet_name='Detalle_Completo', index=False)
            resumen_proyectado.to_excel(writer, sheet_name='Resumen_Proyeccion', index=False)
        
        print("\n" + "═"*60)
        print(" ✅ PROCESO COMPLETADO")
        print(" 📄 Archivo generado: 'Control_Gastos_Proyectado.xlsx'")
        print(" 💡 Revisa la pestaña 'Resumen_Proyeccion' para ver el futuro.")
        print("═"*60)

if __name__ == "__main__":
    procesar_gastos_consolidado()