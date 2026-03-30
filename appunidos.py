import pdfplumber
import pandas as pd
import os
import re
import math

def procesar_gastos_consolidado():
    ruta_actual = os.path.dirname(os.path.abspath(__file__))
    archivos_pdf = [f for f in os.listdir(ruta_actual) if f.lower().endswith('.pdf')]
    
    if not archivos_pdf:
        print("❌ No se encontraron archivos PDF en la carpeta.")
        return

    # REGLAS BANCO DE CHILE (TAL CUAL TUS IMÁGENES)
    reglas_chile = {
        'TRAVEL AMIGOS CCU': ('LA BARRA', 'JAVIER'),
        '06/04/24 TELEFONICA 40 PZA O': ('TELEFONO PAPA', 'PAPA'),
        'TELEFONICA PROVIDEN': ('IPHONE', 'JAVIER'),
        'TRAVEL TIENDA TCOMP': ('NOTEBOOK', 'MAMA'),
        'ECOMMERCE - WOM': ('CELULAR AGU', 'JAVIER'),
        '21/01/25 TELEFONICA 40 PZA O': ('AIRPODS', 'JAVIER'),
        'OP SCHILLING LOCAL': ('LENTES PAPA', 'PAPA'),
        '10/05/25 TELEFONICA 40 PZA O': ('CELULAR TATA', 'JAVIER'),
        'RAO SPA': ('MUELAS AGU', 'MAMA'),
        'NOS PLAZA OESTE': ('POLERONES', 'JAVIER'),
        'MP *FENSA': ('COCINA', 'PADRINO'),
        'MP *MERCADO LIB': ('JBL', 'JAVIER'),
        'AVANCE EN CUOTAS': ('AVANCE CAMIONETA', 'PAPA'),
        '07/10/25 TRAVEL TIENDA TCOMP': ('REFRIGERADOR', 'JAVIER'),
        'ADIDAS PLAZA OESTE': ('ZAPATOS TETE', 'JAVIER'),
        'PAYU *ADIDAS': ('REGALO AMIGO', 'JAVIER'),
        'DOITE OESTE': ('REGALO PAPA', 'JAVIER'),
        'PUMA PLAZA OESTE': ('ZAPATILLAS AG', 'JAVIER'),
        'MP *YANEKEN': ('ZAPATILLAS JAV', 'JAVIER'),
        'FALABELLA PLAZA OES': ('POLERA STRANGER', 'MAMA'),
        'BOLD.CL': ('ZAPATILLAS TAT', 'OTRO'),
        'MERPAGO*MERCADOLIBR': ('INFLADOR', 'JAVIER'),
        'OUTLET VIVO MAIPU': ('ZAPATILLAS PUMA', 'JAVIER'),
        'RIPLEY PLAZA OESTE': ('SHORT CHILE', 'JAVIER'),
        'DLOCAL *NBC UNIVERS SANTIAGO': ('UNIVERSAL', 'JAVIER'),
        '05/02/26 MERCADOPAGO*CANTARI LAS CONDES': ('PARRILLADA', 'JAVIER'),
        'UBER LAS CONDES': ('UBER ONE', 'JAVIER'),
        'MERPAGO*TALLASGRAND': ('TALLAS GRANDES', 'JAVIER')

    }

    # REGLAS FALABELLA (TAL CUAL TUS IMÁGENES)
    reglas_fala = {
        '04/01/2026 Falabella.com': ('SILLA MIA', 'PADRINO'),
        '16/01/2026 Falabella.com': ('MESA NANA', 'PADRINO'),
        '31/08/2025 Compra En Cuotas Sodimac Hs Cerrillos T': ('PARRILLA', 'JAVIER'),
        '29/11/2025 Compras Tottus': ('CUMPLE', 'JAVIER'),
        '21/08/2025 Payu *adidas': ('ZAPA+GORRO', 'JAVIER'),
        '05/10/2025 Shein Cl': ('SHEIN', 'JAVIER'),
        '07/08/2025 Playstationn Cl 0,0': ('FIFA 26', 'JAVIER'),
        'Playstation CL USD 9,5 T': ('PLUS', 'JAVIER'),
        '04/02/2026 Playstation CL USD 17,8 T': ('JUEGO JOAQUIN', 'JAVIER'),
        '18/02/2026 Flow *inzpira Fragra T': ('PERFUMES', 'JAVIER'),
        '18/01/2026 Compra En Cuotas Sodimac Hs Cerrillos T': ('CAMARA+LUZ', 'PAPA'),

    }

    movimientos = []

    for archivo in archivos_pdf:
        es_fala = "FALA" in archivo.upper()
        with pdfplumber.open(os.path.join(ruta_actual, archivo)) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if not texto: continue
                
                for linea in texto.split('\n'):
                    if any(x in linea.upper() for x in ["ADMINISTRACION", "IMPUESTO", "COMISION", "LEY 3475"]):
                        continue

                    if es_fala:
                        patron_fala = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+[\d.]+\s+([\d.]+)\s+(\d+)/(\d+)(?:\s+.*?\s+([\d.]+))?")
                        m = patron_fala.search(linea)
                        if m:
                            f, comercio = m.group(1), m.group(2).strip()
                            desc = f"{f} {comercio}"
                            monto_t, c_paga, c_tot = int(m.group(3).replace('.', '')), int(m.group(4)), int(m.group(5))
                            
                            val_m = int(m.group(6).replace('.', '')) if m.group(6) else math.ceil(monto_t / c_tot)
                            cobro_mes = val_m if c_paga > 0 else 0
                            
                            prod, pagador = "POR ASIGNAR", "POR ASIGNAR"
                            for k, (p, q) in reglas_fala.items():
                                if k in desc: prod, pagador = p, q; break
                            
                            movimientos.append({
                                'BANCO': 'FALABELLA', 'PRODUCTO': prod, 'QUIEN PAGA': pagador,
                                'DESCRIPCION': desc, 'CUOTA PAGA': c_paga, 'CUOTAS TOTALES': c_tot,
                                'VALOR MENSUAL': val_m, 'COBRAR ESTE MES': cobro_mes
                            })
                    else:
                        patron_chile = re.compile(r"([A-Z\s]+\s(\d{2}/\d{2}/\d{2})\s\d+)\s+(.*?)\$\s*[\d.]+\s*\$\s*[\d.]+\s*(\d+)/(\d+)\s*\$\s*([\d.]+)")
                        m = patron_chile.search(linea)
                        if m:
                            f, comercio = m.group(2), m.group(3).strip()
                            desc = f"{f} {comercio}"
                            c_paga, c_tot = int(m.group(4)), int(m.group(5))
                            val_m = int(m.group(6).replace('.', ''))
                            cobro_mes = val_m if c_paga > 0 else 0
                            
                            prod, pagador = "OTRO", "OTRO"
                            # Para el Chile verificamos con la descripción completa que ya incluye la fecha
                            for k, (p, q) in reglas_chile.items():
                                if k in desc.upper() or k in comercio.upper():
                                    prod, pagador = p, q
                                    break
                            
                            movimientos.append({
                                'BANCO': 'CHILE', 'PRODUCTO': prod, 'QUIEN PAGA': pagador,
                                'DESCRIPCION': desc, 'CUOTA PAGA': c_paga, 'CUOTAS TOTALES': c_tot,
                                'VALOR MENSUAL': val_m, 'COBRAR ESTE MES': cobro_mes
                            })

    if movimientos:
        df = pd.DataFrame(movimientos)
        resumen = df.groupby('QUIEN PAGA')['COBRAR ESTE MES'].sum().reset_index()
        resumen.columns = ['QUIEN PAGA', 'TOTAL A TRANSFERIR ESTE MES']
        
        with pd.ExcelWriter("Control_Gastos_Unificado.xlsx") as writer:
            df.to_excel(writer, sheet_name='Detalle', index=False)
            resumen.to_excel(writer, sheet_name='Resumen_Pagos', index=False)
        print(f"✅ ¡Reporte unificado generado con éxito!")
    else:
        print("⚠️ No se detectaron movimientos.")

if __name__ == "__main__":
    procesar_gastos_consolidado()