# -*- coding: utf-8 -*-
"""
Generador de Informe Agronomico PDF Profesional
Compatible con fpdf2 - Solo caracteres ASCII
11 secciones tipo informe tecnico
"""
from fpdf import FPDF
from datetime import datetime

# ==========================================
# FUNCIONES DE SEGURIDAD
# ==========================================
def safe_str(val, default="N/A"):
    if val is None or str(val).strip() == "":
        return str(default)
    return str(val).strip()

def safe_float(val, default=0.0):
    if val is None or str(val).strip() == "":
        return default
    try:
        return float(str(val).replace(',', '.').strip())
    except (ValueError, TypeError):
        return default

def ascii_safe(text):
    """Elimina caracteres no-ASCII para evitar errores de fpdf"""
    if text is None:
        return "N/A"
    text = str(text)
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', '²': '2', '³': '3',
        '⁺': '+', '⁻': '-', '°': 'o', 'µ': 'u',
        '–': '-', '—': '-', '“': '"', '”': '"', '‘': "'", '’': "'"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return ''.join(c for c in text if ord(c) < 128)

# ==========================================
# COLORES CORPORATIVOS
# ==========================================
VERDE_PRIMARIO = (46, 125, 50)
VERDE_CLARO = (230, 245, 230)
VERDE_MEDIO = (200, 230, 200)
GRIS_TEXTO = (80, 80, 80)
GRIS_SUAVE = (128, 128, 128)
ROJO_ALERTA = (200, 30, 30)
ROJO_SUAVE = (255, 235, 235)
AMARILLO_ALERTA = (255, 245, 200)
AZUL_INFO = (30, 100, 180)
AZUL_SUAVE = (230, 240, 250)
NEGRO = (0, 0, 0)

# ==========================================
# CLASE PDF CON HEADER Y FOOTER
# ==========================================
class InformeAgronomicoPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.nombre_cliente = "Cliente"
        self.telefono_cliente = ""
        self.fecha_informe = ""

    def header(self):
        self.set_fill_color(*VERDE_PRIMARIO)
        self.rect(0, 0, 210, 18, 'F')
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.set_y(4)
        self.cell(0, 10, ascii_safe('Asesoria Agronomica Profesional'), 0, 1, 'C')
        self.set_font('Arial', '', 9)
        self.set_text_color(230, 245, 230)
        self.cell(0, 4, ascii_safe(f'RIF: 503619694  |  Informe: {self.fecha_informe}'), 0, 1, 'C')
        self.set_y(24)
        self.set_text_color(*NEGRO)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*VERDE_PRIMARIO)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font('Arial', 'I', 7)
        self.set_text_color(*GRIS_SUAVE)
        self.cell(95, 4, ascii_safe(f'Documento generado automaticamente - {self.fecha_informe}'), 0, 0, 'L')
        self.cell(95, 4, ascii_safe(f'Pagina {self.page_no()}/{{nb}}'), 0, 0, 'R')

    def titulo_seccion(self, numero, titulo):
        self.ln(3)
        self.set_font('Arial', 'B', 13)
        self.set_text_color(*VERDE_PRIMARIO)
        self.cell(0, 8, ascii_safe(f'{numero}. {titulo}'), 0, 1)
        self.set_draw_color(*VERDE_PRIMARIO)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_text_color(*NEGRO)

    def subtitulo(self, texto):
        self.set_x(10)  # 🛡️ BLINDAJE: Forzar margen izquierdo
        self.set_font('Arial', 'B', 11)
        self.set_text_color(*AZUL_INFO)
        self.cell(0, 6, ascii_safe(texto), 0, 1)
        self.set_text_color(*NEGRO)
        self.ln(1)

    def texto_normal(self, texto, negrita=False):
        self.set_x(10)  # 🛡️ BLINDAJE
        self.set_font('Arial', 'B' if negrita else '', 10)
        self.set_text_color(*NEGRO)
        self.multi_cell(0, 5, ascii_safe(texto))
        self.ln(1)

    def texto_italica(self, texto):
        self.set_x(10)  # 🛡️ BLINDAJE
        self.set_font('Arial', 'I', 9)
        self.set_text_color(*GRIS_TEXTO)
        self.multi_cell(0, 4, ascii_safe(texto))
        self.set_text_color(*NEGRO)

    def fila_datos(self, etiqueta, valor, ancho_etiqueta=70):
        self.set_x(10)  # 🛡️ BLINDAJE
        self.set_font('Arial', 'B', 10)
        self.cell(ancho_etiqueta, 6, ascii_safe(etiqueta), 0, 0)
        self.set_font('Arial', '', 10)
        self.cell(0, 6, ascii_safe(str(valor)), 0, 1)

    def alerta(self, texto, tipo='rojo'):
        self.set_x(10)  # 🛡️ BLINDAJE
        if tipo == 'rojo':
            self.set_fill_color(*ROJO_SUAVE)
            self.set_text_color(*ROJO_ALERTA)
            icono = '[!] '
        else:
            self.set_fill_color(*AMARILLO_ALERTA)
            self.set_text_color(150, 100, 0)
            icono = '[*] '
        self.set_font('Arial', 'B', 10)
        self.multi_cell(0, 6, ascii_safe(icono + texto), 1, 'L', True)
        self.set_text_color(*NEGRO)
        self.ln(2)

    def tabla_encabezado(self, columnas, anchos):
        self.set_x(10)  # 🛡️ BLINDAJE
        self.set_fill_color(*VERDE_CLARO)
        self.set_font('Arial', 'B', 9)
        self.set_text_color(*NEGRO)
        for i, col in enumerate(columnas):
            self.cell(anchos[i], 7, ascii_safe(col), 1, 0, 'C', True)
        self.ln()

    def tabla_fila(self, valores, anchos, negrita=False, color_fondo=None):
        self.set_x(10)  # 🛡️ BLINDAJE
        self.set_font('Arial', 'B' if negrita else '', 9)
        if color_fondo:
            self.set_fill_color(*color_fondo)
        for i, val in enumerate(valores):
            self.cell(anchos[i], 6, ascii_safe(str(val)), 1, 0, 'C', bool(color_fondo))
        self.ln()

    def check_space(self, needed=50):
        if self.get_y() > (297 - 25 - needed):
            self.add_page()


# ==========================================
# FUNCION PRINCIPAL: GENERAR PDF
# ==========================================
def generar_pdf(datos: dict, informe: dict) -> bytes:
    pdf = InformeAgronomicoPDF()
    pdf.alias_nb_pages()
    
    nombre = safe_str(datos.get('nombre'), 'Cliente')
    telefono = safe_str(datos.get('telefono'), 'N/A')
    email = safe_str(datos.get('email'), 'N/A')
    ubicacion = safe_str(datos.get('ubicacion'), 'N/A')
    cultivo = safe_str(datos.get('cultivo'), 'No especificado')
    escala = safe_str(datos.get('escala'), 'N/A')
    zona = safe_str(datos.get('zona'), 'N/A')
    temporada = safe_str(datos.get('temporada'), 'N/A')
    area = safe_float(datos.get('area'), 1.0)
    textura = safe_str(datos.get('textura'), 'N/A')
    fecha = datetime.now().strftime('%d/%m/%Y')
    
    pdf.nombre_cliente = nombre
    pdf.telefono_cliente = telefono
    pdf.fecha_informe = fecha
    
    ph = safe_float(datos.get('ph'), 0.0)
    cic = safe_float(datos.get('cic'), 0.0)
    ce = safe_float(datos.get('ce'), 0.0)
    porosidad = safe_float(datos.get('porosidad'), 0.0)
    p_disponible = safe_float(datos.get('p_disponible'), 0.0)
    # 🛡️ Usar valores corregidos si existen en el informe, sino fallback a los crudos de datos
    ca = informe.get('ca_corregido', safe_float(datos.get('ca'), 0.0))
    mg = informe.get('mg_corregido', safe_float(datos.get('mg'), 0.0))
    k = informe.get('k_corregido', safe_float(datos.get('k'), 0.0))
    na = informe.get('na_corregido', safe_float(datos.get('na'), 0.0))
    al_h = informe.get('al_h_corregido', safe_float(datos.get('al_h'), 0.0))
    
    # Extraer la nota de conversión inteligente
    nota_conversion = informe.get('nota_conversion', '')
    
    tipo_cal = safe_str(datos.get('tipo_cal'), 'Cal agricola (CaCO3)')
    prnt = safe_float(datos.get('prnt'), 100.0)
    ph_deseado = safe_float(datos.get('ph_deseado'), 6.5)
    ultima_cal = safe_float(datos.get('ultima_cal_meses'), 12)
    ultima_mo = safe_float(datos.get('ultima_mo_meses'), 12)
    
    sat_ca = informe.get('sat_ca', 0.0)
    sat_mg = informe.get('sat_mg', 0.0)
    sat_k = informe.get('sat_k', 0.0)
    sat_na = informe.get('sat_na', 0.0)
    sat_al = informe.get('sat_al', 0.0)
    estado_ph = informe.get('estado_ph', 'N/A')
    estado_p = informe.get('estado_p', 'N/A')
    dosis_cal = informe.get('dosis_cal_kg_ha', 0.0)
    dosis_yeso = informe.get('dosis_yeso_kg_ha', 0.0)
    dosis_mo = informe.get('dosis_mo_ton_ha', 0.0)
    dosis_npk = informe.get('dosis_npk_kg_ha', 0.0)
    dosis_p = informe.get('dosis_p_kg_ha', 0.0)
    dosis_s = informe.get('dosis_s_kg_ha', 0.0)
    ica_e = informe.get('ica_e', 0.0)
    psi = informe.get('psi', 0.0)
    recomendacion_cal = informe.get('recomendacion_cal', 'No requerido')
    recomendacion_yeso = informe.get('recomendacion_yeso', 'No requerido')
    recomendacion_mo = informe.get('recomendacion_mo', 'No requerido')
    recomendacion_p = informe.get('recomendacion_p', 'No requerido')
    alerta_tox_al = informe.get('alerta_tox_al', False)
    alerta_sodico = informe.get('alerta_sodico', False)
    alerta_acido = informe.get('alerta_acido', False)
    calendario = informe.get('calendario', [])
    rotacion = informe.get('rotacion', [])
    roi = informe.get('roi', {})
    recomendaciones = informe.get('recomendaciones', {})
    diagnostico_expr = informe.get('diagnostico_expr', '')
    estado_general = informe.get('estado_general', 'N/A')
    
    # ==========================================
    # SECCION 1: PORTADA
    # ==========================================
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Arial', 'B', 28)
    pdf.set_text_color(*VERDE_PRIMARIO)
    pdf.cell(0, 15, ascii_safe('INFORME'), 0, 1, 'C')
    pdf.cell(0, 15, ascii_safe('AGRONOMICO'), 0, 1, 'C')
    pdf.ln(5)
    pdf.set_draw_color(*VERDE_PRIMARIO)
    pdf.set_line_width(1.5)
    pdf.line(50, pdf.get_y(), 160, pdf.get_y())
    pdf.ln(8)
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(*GRIS_TEXTO)
    pdf.cell(0, 8, ascii_safe('Plan Agronomico Integral'), 0, 1, 'C')
    pdf.cell(0, 8, ascii_safe('Analisis de Suelo y Recomendaciones Tecnicas'), 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(*VERDE_PRIMARIO)
    pdf.cell(0, 8, ascii_safe('DATOS DEL CLIENTE'), 0, 1, 'C')
    pdf.set_draw_color(*VERDE_PRIMARIO)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(*NEGRO)
    pdf.cell(0, 7, ascii_safe(f'Cliente: {nombre}'), 0, 1, 'C')
    pdf.cell(0, 7, ascii_safe(f'Telefono: {telefono}'), 0, 1, 'C')
    pdf.cell(0, 7, ascii_safe(f'Email: {email}'), 0, 1, 'C')
    pdf.cell(0, 7, ascii_safe(f'Ubicacion: {ubicacion}'), 0, 1, 'C')
    pdf.cell(0, 7, ascii_safe(f'Fecha del informe: {fecha}'), 0, 1, 'C')
    pdf.ln(15)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(*GRIS_SUAVE)
    pdf.cell(0, 5, ascii_safe('RIF: 503619694'), 0, 1, 'C')
    pdf.cell(0, 5, ascii_safe('Documento generado automaticamente - Asesoria Remota'), 0, 1, 'C')
    
    # ==========================================
    # SECCION 2: DATOS DEL ANALISIS
    # ==========================================
    pdf.add_page()
    pdf.titulo_seccion('1', 'DATOS DEL ANALISIS DE SUELO')
    pdf.subtitulo('Informacion del predio')
    pdf.fila_datos('Cliente:', nombre)
    pdf.fila_datos('Telefono:', telefono)
    pdf.fila_datos('Email:', email)
    pdf.fila_datos('Ubicacion:', ubicacion)
    pdf.fila_datos('Cultivo principal:', cultivo)
    pdf.fila_datos('Escala de produccion:', escala)
    pdf.fila_datos('Zona climatica:', zona)
    pdf.fila_datos('Temporada actual:', temporada)
    pdf.fila_datos('Area:', f'{area} ha')
    pdf.fila_datos('Textura dominante:', textura)
    pdf.ln(3)
    pdf.subtitulo('Parametros quimicos del suelo')
    anchos = [60, 60, 70]
    pdf.tabla_encabezado(['Parametro', 'Valor', 'Unidad'], anchos)
    pdf.tabla_fila(['pH', f'{ph}', '-'], anchos)
    pdf.tabla_fila(['CIC', f'{cic}', 'meq/100g'], anchos)
    pdf.tabla_fila(['Conductividad Electrica', f'{ce}', 'dS/m'], anchos)
    pdf.tabla_fila(['Porosidad', f'{porosidad}', '%'], anchos)
    pdf.tabla_fila(['P disponible', f'{p_disponible}', 'ppm (mg/kg)'], anchos)
    pdf.ln(3)

    pdf.subtitulo('Cationes base + acidez')
    anchos2 = [60, 60, 70]
    pdf.tabla_encabezado(['Cation', 'Valor', 'Unidad'], anchos2)
    pdf.tabla_fila(['Ca2+', f'{ca}', 'meq/100g'], anchos2)
    pdf.tabla_fila(['Mg2+', f'{mg}', 'meq/100g'], anchos2)
    pdf.tabla_fila(['K+', f'{k}', 'meq/100g'], anchos2)
    pdf.tabla_fila(['Na+', f'{na}', 'meq/100g'], anchos2)
    pdf.tabla_fila(['Al3+ + H+', f'{al_h}', 'meq/100g'], anchos2)
    
    # 🛡️ NOTA DE CONVERSIÓN INTELIGENTE (Si aplica)
    if nota_conversion:
        pdf.ln(2)
        pdf.alerta(nota_conversion, tipo='amarillo')  # Usa tu método existente que ya incluye ascii_safe()
        pdf.ln(2)

    pdf.ln(3)
    pdf.subtitulo('Informacion de enmiendas')
    pdf.fila_datos('Tipo de cal:', tipo_cal, 60)
    pdf.fila_datos('PRNT:', f'{prnt}%', 60)
    pdf.fila_datos('pH deseado:', f'{ph_deseado}', 60)
    pdf.fila_datos('Ultima aplicacion de cal:', f'{int(ultima_cal)} meses', 60)
    pdf.fila_datos('Ultima aplicacion de MO:', f'{int(ultima_mo)} meses', 60)
    
    # ==========================================
    # SECCION 3: DIAGNOSTICO EXPRES
    # ==========================================
    pdf.check_space(60)
    pdf.titulo_seccion('2', 'DIAGNOSTICO EXPRES')
    pdf.set_fill_color(*VERDE_CLARO)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, ascii_safe(f'ESTADO GENERAL DEL SUELO: {estado_general}'), 1, 1, 'C', True)
    pdf.ln(2)
    pdf.texto_normal(diagnostico_expr)
    
    alertas_activas = []
    if alerta_acido:
        alertas_activas.append(('rojo', f'SUELO ACIDO (pH {ph}) - Requiere encalado urgente'))
    if alerta_tox_al:
        alertas_activas.append(('rojo', f'TOXICIDAD POR ALUMINIO (Al3++H+ = {al_h} meq/100g)'))
    if alerta_sodico:
        alertas_activas.append(('rojo', f'SUELO SODICO (PSI = {psi}%) - Requiere yeso'))
    if safe_float(ce, 0) > 3.0:
        alertas_activas.append(('amarillo', f'SALINIDAD ALTA (CE = {ce} dS/m) - Lavar suelo'))
    if p_disponible < 10:
        alertas_activas.append(('amarillo', f'FOSFORO BAJO ({p_disponible} ppm) - Limitante de rendimiento'))
    if cic < 5:
        alertas_activas.append(('amarillo', f'CIC BAJA ({cic} meq/100g) - Mejorar materia organica'))
    
    if alertas_activas:
        pdf.subtitulo('Alertas de prioridad')
        for tipo, msg in alertas_activas:
            pdf.alerta(msg, tipo)
    else:
        pdf.set_fill_color(*VERDE_CLARO)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(*VERDE_PRIMARIO)
        pdf.cell(0, 8, ascii_safe('[OK] Sin alertas criticas - Suelo en condiciones aceptables'), 1, 1, 'C', True)
        pdf.set_text_color(*NEGRO)
        pdf.ln(2)
    
    # ==========================================
    # SECCION 4: SATURACION DEL COMPLEJO
    # ==========================================
    pdf.check_space(70)
    pdf.titulo_seccion('3', 'SATURACION DEL COMPLEJO DE INTERCAMBIO')
    anchos3 = [50, 40, 40, 60]
    pdf.tabla_encabezado(['Cation', '% Saturacion', 'Rango ideal', 'Estado'], anchos3)
    
    def estado_cat(val, bajo, alto, invertido=False):
        if invertido:
            if val > alto: return 'EXCESO'
            return 'Normal'
        if val < bajo: return 'BAJO'
        if val > alto: return 'ALTO'
        return 'OPTIMO'
    
    cationes_data = [
        ('Ca2+', sat_ca, 60, 80),
        ('Mg2+', sat_mg, 10, 20),
        ('K+', sat_k, 2, 5),
        ('Na+ (PSI)', sat_na, 15, 100),
        ('Al3+ + H+', sat_al, 10, 100),
    ]
    
    for cat, val, bajo, alto in cationes_data:
        invertido = cat in ['Na+ (PSI)', 'Al3+ + H+']
        estado = estado_cat(val, bajo, alto, invertido)
        color = None
        if estado in ['BAJO', 'EXCESO']:
            color = ROJO_SUAVE
        elif estado == 'OPTIMO':
            color = VERDE_CLARO
        pdf.tabla_fila([cat, f'{val}%', f'{bajo}-{alto}%', estado], anchos3, color_fondo=color)
    
    pdf.ln(2)
    pdf.texto_italica('Interpretacion: Ca2+ y Mg2+ son los cationes dominantes en suelos fertiles. '
                      'K+ es clave para fructificacion. Na+ > 15% indica sodicidad. '
                      'Al3+ + H+ > 10% indica acidez intercambiable toxica.')
    
    # ==========================================
    # SECCION 5: INDICES CLAVE
    # ==========================================
    pdf.check_space(60)
    pdf.titulo_seccion('4', 'INDICES CLAVE DEL SUELO')
    anchos4 = [60, 50, 80]
    pdf.tabla_encabezado(['Indice', 'Valor', 'Interpretacion'], anchos4)
    
    interp_psi = 'Normal' if psi <= 15 else 'SODICO - Requiere yeso'
    color_psi = VERDE_CLARO if psi <= 15 else ROJO_SUAVE
    pdf.tabla_fila(['PSI (Na/CIC)', f'{psi}%', interp_psi], anchos4, color_fondo=color_psi)
    
    interp_ica = 'Activo - Fraccionar P' if ica_e > 30 else 'Normal'
    color_ica = AMARILLO_ALERTA if ica_e > 30 else VERDE_CLARO
    pdf.tabla_fila(['ICA-e', f'{ica_e}%', interp_ica], anchos4, color_fondo=color_ica)
    
    interp_p = estado_p
    color_p = ROJO_SUAVE if estado_p == 'Bajo' else (VERDE_CLARO if estado_p == 'Alto' else AMARILLO_ALERTA)
    pdf.tabla_fila(['P disponible', f'{p_disponible} ppm', interp_p], anchos4, color_fondo=color_p)
    
    color_ph = ROJO_SUAVE if ph < 5.5 else (AMARILLO_ALERTA if ph > 7.5 else VERDE_CLARO)
    pdf.tabla_fila(['pH', f'{ph}', estado_ph], anchos4, color_fondo=color_ph)
    
    pdf.ln(2)
    pdf.texto_italica('PSI = Porcentaje de Sodio Intercambiable. ICA-e = Indice de Capacidad '
                      'Anionica efectivo (activo cuando pH < 5.5). Ambos indices determinan '
                      'la estrategia de enmiendas y fertilizacion.')
    
    # ==========================================
    # SECCION 6: PLAN DE ENMIENDAS
    # ==========================================
    pdf.add_page()
    pdf.titulo_seccion('5', 'PLAN DE ENMIENDAS RECOMENDADO')
    pdf.texto_normal(f'Area total a tratar: {area} ha | pH objetivo: {ph_deseado} | Tipo de cal: {tipo_cal}')
    anchos5 = [45, 35, 35, 75]
    pdf.tabla_encabezado(['Enmienda', 'Dosis/ha', 'Total', 'Recomendacion'], anchos5)
    
    total_cal = round(dosis_cal * area, 1)
    pdf.tabla_fila(['Cal', f'{dosis_cal} kg', f'{total_cal} kg', ascii_safe(recomendacion_cal)[:40]], anchos5)
    
    if dosis_yeso > 0:
        total_yeso = round(dosis_yeso * area, 1)
        pdf.tabla_fila(['Yeso', f'{dosis_yeso} kg', f'{total_yeso} kg', ascii_safe(recomendacion_yeso)[:40]], anchos5)
    
    if dosis_mo > 0:
        total_mo = round(dosis_mo * area, 1)
        pdf.tabla_fila(['Materia Org.', f'{dosis_mo} ton', f'{total_mo} ton', ascii_safe(recomendacion_mo)[:40]], anchos5)
    
    if dosis_npk > 0:
        total_npk = round(dosis_npk * area, 1)
        pdf.tabla_fila(['NPK formula', f'{dosis_npk} kg', f'{total_npk} kg', 'Fertilizacion base'], anchos5)
    
    if dosis_p > 0:
        total_p = round(dosis_p * area, 1)
        pdf.tabla_fila(['Fosforo (P)', f'{dosis_p} kg', f'{total_p} kg', ascii_safe(recomendacion_p)[:40]], anchos5)
    
    if dosis_s > 0:
        total_s = round(dosis_s * area, 1)
        pdf.tabla_fila(['Azufre (S)', f'{dosis_s} kg', f'{total_s} kg', 'Correccion deficiencia'], anchos5)
    
    pdf.ln(3)
    pdf.subtitulo('Instrucciones de aplicacion')
    pdf.texto_normal('Cal: Incorporar 15-20 cm antes de siembra. Efecto en 60-90 dias.')
    pdf.texto_normal('Yeso: Aplicar en superficie, no requiere incorporacion profunda.')
    pdf.texto_normal('Materia organica: Mezclar con suelo en preparacion de cama.')
    pdf.texto_normal('NPK: Fraccionar en 2-3 aplicaciones segun cultivo.')
    
    # ==========================================
    # SECCION 7: CALENDARIO AGRICOLA
    # ==========================================
    pdf.check_space(80)
    pdf.titulo_seccion('6', 'CALENDARIO AGRICOLA')
    if calendario:
        anchos6 = [40, 70, 80]
        pdf.tabla_encabezado(['Periodo', 'Actividad', 'Detalle'], anchos6)
        for item in calendario:
            periodo = safe_str(item.get('periodo', ''))
            actividad = safe_str(item.get('actividad', ''))
            detalle = safe_str(item.get('detalle', ''))[:45]
            pdf.tabla_fila([periodo, actividad, detalle], anchos6)
    else:
        pdf.texto_normal('No hay calendario disponible para esta combinacion de cultivo/zona/temporada.')
    
    # ==========================================
    # SECCION 8: ROTACION DE CULTIVOS
    # ==========================================
    pdf.check_space(60)
    pdf.titulo_seccion('7', 'ROTACION DE CULTIVOS SUGERIDA')
    if rotacion:
        pdf.texto_normal('Secuencia recomendada para mantener fertilidad y romper ciclos de plagas:')
        for i, item in enumerate(rotacion, 1):
            cultivo_rot = safe_str(item.get('cultivo', ''))
            duracion = safe_str(item.get('duracion', ''))
            beneficio = safe_str(item.get('beneficio', ''))
            pdf.set_x(10)  # 🛡️ BLINDAJE
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(5, 5, ascii_safe(f'{i}.'), 0, 0)
            pdf.cell(60, 5, ascii_safe(cultivo_rot), 0, 0)
            pdf.set_font('Arial', '', 10)
            pdf.cell(30, 5, ascii_safe(f'({duracion})'), 0, 0)
            pdf.cell(0, 5, ascii_safe(f'- {beneficio}'), 0, 1)
    else:
        pdf.texto_normal('No hay rotacion sugerida para este cultivo.')
    
    # ==========================================
    # SECCION 9: PROYECCION ROI
    # ==========================================
    pdf.check_space(70)
    pdf.titulo_seccion('8', 'PROYECCION DE RETORNO DE INVERSION (ROI)')
    if roi:
        costo_total = safe_float(roi.get('costo_total_usd', 0))
        rend_sin = safe_float(roi.get('rendimiento_sin_enmiendas', 0))
        rend_con = safe_float(roi.get('rendimiento_con_enmiendas', 0))
        incremento_pct = safe_float(roi.get('incremento_pct', 0))
        retorno_esperado = safe_float(roi.get('retorno_esperado_usd', 0))
        roi_pct = safe_float(roi.get('roi_pct', 0))
        payback = safe_str(roi.get('payback_meses', 'N/A'))
        
        anchos9 = [90, 100]
        pdf.tabla_encabezado(['Concepto', 'Valor'], anchos9)
        pdf.tabla_fila(['Costo total enmiendas', f'USD {costo_total:,.2f}'], anchos9)
        pdf.tabla_fila(['Rendimiento sin enmiendas', f'{rend_sin} ton/ha'], anchos9)
        pdf.tabla_fila(['Rendimiento con enmiendas', f'{rend_con} ton/ha (+{incremento_pct}%)'], anchos9, color_fondo=VERDE_CLARO)
        pdf.tabla_fila(['Retorno esperado', f'USD {retorno_esperado:,.2f}'], anchos9)
        pdf.tabla_fila(['ROI proyectado', f'{roi_pct}%'], anchos9, negrita=True, color_fondo=VERDE_CLARO)
        pdf.tabla_fila(['Recuperacion inversion', f'{payback} meses'], anchos9)
        
        pdf.ln(2)
        pdf.texto_italica('Proyeccion basada en coeficientes empiricos. Resultados reales varian segun '
                          'clima, manejo, plagas y precio de mercado. Validar con analisis foliar.')
    else:
        pdf.texto_normal('No hay proyeccion ROI disponible para este cultivo.')
    
    # ==========================================
    # SECCION 10: RECOMENDACIONES FINALES
    # ==========================================
    pdf.add_page()
    pdf.titulo_seccion('9', 'RECOMENDACIONES AGRONOMICAS FINALES')
    
    if recomendaciones:
        if recomendaciones.get('manejo_integrado'):
            pdf.subtitulo('Manejo integrado del suelo')
            for rec in recomendaciones['manejo_integrado']:
                pdf.set_x(10)  # 🛡️ BLINDAJE CRÍTICO
                pdf.set_font('Arial', '', 10)
                try:
                    pdf.multi_cell(0, 5, ascii_safe(f'  - {rec}'))
                except Exception as e:
                    print(f"ERROR PDF renderizando recomendacion: {e} | Valor: {rec}")
                    pdf.multi_cell(0, 5, "  - (Error de formato en esta linea)")
            pdf.ln(2)
        
        if recomendaciones.get('gestion_agua'):
            pdf.subtitulo('Gestion del agua y riego')
            for rec in recomendaciones['gestion_agua']:
                pdf.set_x(10)  # 🛡️ BLINDAJE CRÍTICO
                pdf.set_font('Arial', '', 10)
                try:
                    pdf.multi_cell(0, 5, ascii_safe(f'  - {rec}'))
                except Exception as e:
                    print(f"ERROR PDF renderizando recomendacion: {e} | Valor: {rec}")
                    pdf.multi_cell(0, 5, "  - (Error de formato en esta linea)")
            pdf.ln(2)
        
        if recomendaciones.get('monitoreo'):
            pdf.subtitulo('Monitoreo post-aplicacion')
            for rec in recomendaciones['monitoreo']:
                pdf.set_x(10)  # 🛡️ BLINDAJE CRÍTICO
                pdf.set_font('Arial', '', 10)
                try:
                    pdf.multi_cell(0, 5, ascii_safe(f'  - {rec}'))
                except Exception as e:
                    print(f"ERROR PDF renderizando recomendacion: {e} | Valor: {rec}")
                    pdf.multi_cell(0, 5, "  - (Error de formato en esta linea)")
            pdf.ln(2)
        
        if recomendaciones.get('prioridades'):
            pdf.subtitulo('Prioridades inmediatas')
            for i, rec in enumerate(recomendaciones['prioridades'], 1):
                pdf.set_x(10)  # 🛡️ BLINDAJE CRÍTICO
                pdf.set_font('Arial', 'B', 10)
                try:
                    pdf.multi_cell(0, 5, ascii_safe(f'  {i}. {rec}'))
                except Exception as e:
                    print(f"ERROR PDF renderizando prioridad: {e} | Valor: {rec}")
                    pdf.multi_cell(0, 5, f"  {i}. (Error de formato)")
            pdf.ln(2)
    else:
        pdf.texto_normal('No hay recomendaciones adicionales disponibles.')
    
    # ==========================================
    # SECCION 11: NOTA LEGAL
    # ==========================================
    pdf.check_space(40)
    pdf.ln(5)
    pdf.set_draw_color(*VERDE_PRIMARIO)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(*VERDE_PRIMARIO)
    pdf.cell(0, 5, ascii_safe('NOTA LEGAL Y RESPONSABILIDAD'), 0, 1, 'C')
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(*GRIS_SUAVE)
    nota_legal = (
        'Las dosis y recomendaciones generadas estan ajustadas en los datos proporcionados.' 
        'Los resultados pueden variar segun condiciones climaticas pasado el tiempo del reporte.'
        'RIF: 503619694. Documento generado el ' + fecha + '.'
    )
    pdf.multi_cell(0, 4, ascii_safe(nota_legal))
    
    return pdf.output()