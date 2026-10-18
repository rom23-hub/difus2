# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import io
import json
import traceback
from datetime import datetime, timezone

try:
    from pdf_generator import generar_pdf
    PDF_AVAILABLE = True
    print("✅ pdf_generator importado correctamente")
except ImportError as e:
    PDF_AVAILABLE = False
    print(f"❌ Error importando pdf_generator: {e}")

app = FastAPI(title="Bot Agronomico")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CONFIGURACION
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8898771619:AAEYAJiTleG-R_2EyNsff0DSI72hCbl1Md0")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "TU_CHAT_ID_PERSONAL")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_KEY)

db_suelos = {}

if SUPABASE_ENABLED:
    print(f"✅ Supabase conectado: {SUPABASE_URL[:30]}...")
else:
    print("⚠️ Supabase NO configurado. Usando memoria RAM como fallback.")

# ==========================================
# FUNCIONES DE SEGURIDAD
# ==========================================
def safe_float(value, default=0.0):
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(str(value).replace(',', '.').strip())
    except (ValueError, TypeError):
        return default

def safe_str(value, default="N/A"):
    if value is None or str(value).strip() == "":
        return str(default)
    return str(value).strip()

# ==========================================
# FUNCIONES SUPABASE
# ==========================================
async def supabase_request(method: str, table: str, data=None, filters=None, prefer="return=representation"):
    if not SUPABASE_ENABLED:
        return None

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }

    params = {}
    if filters:
        for k, v in filters.items():
            params[k] = f"eq.{v}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                r = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                r = await client.post(url, headers=headers, json=data, params=params)
            elif method == "PATCH":
                r = await client.patch(url, headers=headers, json=data, params=params)
            else:
                return None

            if r.status_code >= 400:
                print(f"❌ Supabase error {r.status_code}: {r.text[:200]}")
                return None
            return r.json() if r.text else []
    except Exception as e:
        print(f"❌ Supabase request failed: {e}")
        return None

async def supabase_upsert_suelo(data: dict):
    return await supabase_request(
        "POST", "suelos",
        data=data,
        prefer="resolution=merge-duplicates,return=representation"
    )

async def supabase_get_suelo(telefono: str):
    print(f"🔎 BUSCANDO en Supabase telefono: '{telefono}' (longitud: {len(telefono)})")
    result = await supabase_request("GET", "suelos", filters={"telefono": telefono})
    print(f"📦 RESPUESTA CRUDA de Supabase: {result}")
    
    if result and len(result) > 0:
        print(f"✅ ENCONTRADO en Supabase: {result[0].get('nombre')}")
        return result[0]
    
    print("⚠️ NO ENCONTRADO en Supabase (lista vacía)")
    return None

async def supabase_get_suelo_by_chat(chat_id: str):
    result = await supabase_request("GET", "suelos", filters={"chat_id_cliente": chat_id})
    if result and len(result) > 0:
        return result[0]
    return None

async def supabase_update_suelo(telefono: str, data: dict):
    return await supabase_request(
        "PATCH", "suelos",
        data=data,
        filters={"telefono": telefono}
    )

async def obtener_datos_cliente(telefono: str):
    print(f"🔍 INICIANDO BÚSQUEDA para el comando /start con: '{telefono}'")
    datos = None
    
    if SUPABASE_ENABLED:
        datos = await supabase_get_suelo(telefono)
    
    if not datos and telefono in db_suelos:
        print("✅ ENCONTRADO en memoria RAM (fallback)")
        datos = db_suelos[telefono]
        
    return datos

# ==========================================
# 🛡️ FUNCIÓN CORREGIDA Y BLINDADA
# ==========================================
async def guardar_datos_cliente(telefono: str, data: dict):
    """Guarda en Supabase (UPSERT) y en memoria como cache"""
    db_suelos[telefono] = data  # Cache local
    
    if SUPABASE_ENABLED:
        # 1. Lista blanca de columnas que SÍ existen en la tabla 'suelos'
        allowed = {
            "telefono", "chat_id", "nombre", "email", "ph", "cic", "ca", "mg", "k", "na", 
            "al_h", "p_disponible", "area", "cultivo", "plan", "created_at", "ce", "porosidad", 
            "textura", "cultivos_previos", "escala", "zona", "temporada", "ubicacion", 
            "tipo_cal", "prnt", "ph_deseado", "ultima_cal_meses", "ultima_mo_meses", 
            "chat_id_cliente", "plan_seleccionado", "monto_pago", "estado_pago", "aprobado_en", 
            "pdf_generado", "updated_at"
        }
        
        # 2. Campos que DEBEN ser numéricos o NULL (nunca "")
        numeric_fields = {
            "ph", "cic", "ca", "mg", "k", "na", "al_h", "p_disponible", "area", 
            "ce", "porosidad", "prnt", "ph_deseado", "ultima_cal_meses", "ultima_mo_meses", "monto_pago"
        }
        
        # 3. LIMPIEZA OBLIGATORIA
        clean_data = {}
        for key, value in data.items():
            if key not in allowed:
                continue  # Ignorar campos extra del frontend (ej: paymentMethod, txid)
            
            # Si es string vacío, convertir a None (NULL en PostgreSQL)
            if isinstance(value, str) and value.strip() == "":
                clean_data[key] = None
            # Si es campo numérico, forzar conversión a float
            elif key in numeric_fields:
                try:
                    clean_data[key] = float(str(value).replace(',', '.'))
                except (ValueError, TypeError):
                    clean_data[key] = None
            else:
                clean_data[key] = value
        
        print(f"🔍 DATOS LIMPIOS ENVIADOS A SUPABASE (telefono={telefono}):", {k: v for k, v in clean_data.items() if v is not None})
        
        # 4. Enviar clean_data, NO data
        result = await supabase_upsert_suelo(clean_data)
        if result:
            print(f"✅ Guardado en Supabase: {telefono}")
            return True
        else:
            print(f"⚠️ Falló Supabase: {telefono}")
            return False
    return True

# ==========================================
# ENDPOINTS
# ==========================================
@app.get("/")
async def root():
    return {
        "status": "Bot Agronomico Activo",
        "admin_chat_id": "Configurado" if ADMIN_CHAT_ID != "TU_CHAT_ID_PERSONAL" else "FALTA",
        "pdf_generator": "Disponible" if PDF_AVAILABLE else "No disponible",
        "supabase": "Conectado" if SUPABASE_ENABLED else "No configurado",
        "registros_en_memoria": len(db_suelos),
    }

@app.post("/webhook/netlify")
async def recibir_formulario(request: Request):
    try:
        data = await request.json()
        telefono = str(data.get("telefono", "")).strip()

        if not telefono:
            raise HTTPException(status_code=400, detail="Falta telefono")

        if telefono.startswith("0"):
            telefono = "58" + telefono[1:]
        elif not telefono.startswith("58"):
            telefono = "58" + telefono

        data["telefono"] = telefono
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        data["estado_pago"] = "pendiente"

        await guardar_datos_cliente(telefono, data)

        link_telegram = f"https://t.me/AsesoriaSuelosBot?start={telefono}"
        return {
            "status": "success",
            "message": f"Datos recibidos, {data.get('nombre')}! Para verificar tu Pago Movil, haz clic aqui y presiona 'Iniciar' en Telegram:\n\n{link_telegram}"
        }
    except Exception as e:
        print(f"❌ ERROR en webhook/netlify: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"/webhook/telegram/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        if "message" in data and "text" in data["message"]:
            chat_id = str(data["message"]["chat"]["id"])
            text = data["message"]["text"]

            if text.startswith("/start "):
                telefono = text.replace("/start ", "").strip()
                datos = await obtener_datos_cliente(telefono)

                if datos:
                    if SUPABASE_ENABLED:
                        await supabase_update_suelo(telefono, {"chat_id_cliente": chat_id})
                    else:
                        db_suelos[telefono]["chat_id_cliente"] = chat_id

                    nombre = datos.get("nombre", "Cliente")
                    await enviar_mensaje(
                        chat_id,
                        f"Hola {nombre}! Responde con:\n1. Cedula\n2. Monto exacto\n3. Ultimos 4 digitos de referencia"
                    )
                else:
                    await enviar_mensaje(chat_id, "No hay datos. Llena el formulario web primero.")
                return JSONResponse(status_code=200, content={"status": "ok"})

            else:
                telefono_encontrado = None
                if SUPABASE_ENABLED:
                    row = await supabase_get_suelo_by_chat(chat_id)
                    if row:
                        telefono_encontrado = row.get("telefono")

                if not telefono_encontrado:
                    for tel, d in db_suelos.items():
                        if d.get("chat_id_cliente") == chat_id:
                            telefono_encontrado = tel
                            break

                monto = 0
                if SUPABASE_ENABLED:
                    row = await supabase_get_suelo_by_chat(chat_id)
                    if row:
                        monto = row.get("monto_pago", 0) or 0
                elif telefono_encontrado in db_suelos:
                    monto = db_suelos[telefono_encontrado].get("monto_pago", 0)

                await enviar_alerta_admin(chat_id, text, telefono_encontrado or "desconocido", monto)
                return JSONResponse(status_code=200, content={"status": "ok"})

        elif "callback_query" in data:
            callback_data = data["callback_query"]["data"]
            message_id = data["callback_query"]["message"]["message_id"]
            chat_id_admin = data["callback_query"]["message"]["chat"]["id"]
    
            # ==========================================
            # ✅ APROBAR PAGO
            # ==========================================
            if callback_data.startswith("aprobar_"):
                telefono = callback_data.replace("aprobar_", "").strip()
                datos = await obtener_datos_cliente(telefono)
        
                if not datos:
                    await editar_mensaje(chat_id_admin, message_id, "❌ Datos no encontrados.")
                    return JSONResponse(status_code=200, content={"status": "error"})
        
                await editar_mensaje(chat_id_admin, message_id, "✅ APROBADO. Generando y enviando PDF...")
        
                chat_id_cliente = datos.get("chat_id_cliente")
                if not chat_id_cliente:
                    await editar_mensaje(chat_id_admin, message_id, "❌ Error: Cliente no inició el bot.")
                    return JSONResponse(status_code=200, content={"status": "error"})
        
                try:
                    informe = calcular_informe_agronomico(datos)
            
                    if SUPABASE_ENABLED:
                        await supabase_update_suelo(telefono, {
                            "estado_pago": "aprobado",
                            "aprobado_en": datetime.now(timezone.utc).isoformat(),
                            "plan": json.loads(json.dumps(informe)),
                            "pdf_generado": True,
                        })
                    else:
                        db_suelos[telefono]["estado_pago"] = "aprobado"
                        db_suelos[telefono]["plan"] = informe
            
                    if PDF_AVAILABLE:
                        pdf_bytes = generar_pdf(datos, informe)
                        await enviar_pdf(chat_id_cliente, pdf_bytes, f"Informe_{telefono}.pdf")
                        await enviar_mensaje(
                            chat_id_cliente,
                            f"✅ ¡Pago aprobado, {datos.get('nombre', 'Cliente')}!\n\n"
                            f"Adjunto tu Informe Agronómico PDF.\n\n"
                            f"RIF: 503619694"
                        )
                    else:
                        await enviar_mensaje(
                            chat_id_cliente,
                            f"✅ Pago aprobado.\n\n"
                            f"INFORME RESUMEN:\n"
                            f"pH: {datos.get('ph')}\n"
                            f"CIC: {datos.get('cic')} meq/100g\n"
                            f"Cal: {informe.get('recomendacion_cal')}"
                        )
            
                    # Confirmación al admin
                    await editar_mensaje(
                        chat_id_admin, 
                        message_id, 
                        f"✅ APROBADO\nTel: {telefono}\nPDF enviado al cliente."
                    )
            
                except Exception as e:
                    print(f"❌ ERROR al generar/enviar PDF: {e}")
                    traceback.print_exc()
                    await enviar_mensaje_sin_markdown(chat_id_admin, f"❌ Error al generar PDF: {str(e)}")
        
                return JSONResponse(status_code=200, content={"status": "ok"})
    
            # ==========================================
            # ❌ RECHAZAR PAGO
            # ==========================================
            elif callback_data.startswith("rechazar_"):
                telefono = callback_data.replace("rechazar_", "").strip()
                datos = await obtener_datos_cliente(telefono)
        
                if not datos:
                    await editar_mensaje(chat_id_admin, message_id, "❌ Datos no encontrados.")
                    return JSONResponse(status_code=200, content={"status": "error"})
        
                # Actualizar estado en Supabase
                if SUPABASE_ENABLED:
                    await supabase_update_suelo(telefono, {
                        "estado_pago": "rechazado",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    if telefono in db_suelos:
                        db_suelos[telefono]["estado_pago"] = "rechazado"
        
                # Notificar al cliente
                chat_id_cliente = datos.get("chat_id_cliente")
                if chat_id_cliente:
                    nombre = datos.get("nombre", "Cliente")
                    await enviar_mensaje(
                        chat_id_cliente,
                        f"❌ Hola {nombre},\n\n"
                        f"Lamentablemente tu pago no pudo ser verificado.\n\n"
                        f"Posibles razones:\n"
                        f"• Monto incorrecto\n"
                        f"• Referencia no encontrada en el banco\n"
                        f"• Datos de transferencia inconsistentes\n\n"
                        f"Por favor, verifica los datos y vuelve a enviar el pago.\n\n"
                        f"Si tienes dudas, responde a este mensaje con tus preguntas.\n\n"
                        f"RIF: 503619694"
                    )
        
                # Confirmación al admin
                await editar_mensaje(
                    chat_id_admin,
                    message_id,
                    f"❌ RECHAZADO\nTel: {telefono}\nCliente notificado."
                )
        
                return JSONResponse(status_code=200, content={"status": "ok"})
    
            # ==========================================
            # ⏳ MARCAR COMO PENDIENTE (reversión)
            # ==========================================
            elif callback_data.startswith("pendiente_"):
                telefono = callback_data.replace("pendiente_", "").strip()
        
                if SUPABASE_ENABLED:
                    await supabase_update_suelo(telefono, {
                        "estado_pago": "pendiente",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    if telefono in db_suelos:
                        db_suelos[telefono]["estado_pago"] = "pendiente"
        
                await editar_mensaje(
                    chat_id_admin,
                    message_id,
                    f"⏳ MARCADO PENDIENTE\nTel: {telefono}\nEsperando nueva verificación."
                )
        
                return JSONResponse(status_code=200, content={"status": "ok"})
    
            return JSONResponse(status_code=200, content={"status": "ok"})

    except Exception as e:
        print(f"❌ Error general en webhook/telegram: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

# ==========================================
# FUNCIONES AUXILIARES TELEGRAM
# ==========================================
async def enviar_mensaje(chat_id: str, texto: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"})

async def enviar_mensaje_sin_markdown(chat_id: str, texto: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": texto})

async def enviar_alerta_admin(chat_cliente: str, referencia: str, telefono: str, monto: float = 0):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # 🛡️ Mensaje más completo con datos del pago
    texto = (
        f"💰 *PAGO REPORTADO*\n\n"
        f"📱 Tel: `{telefono}`\n"
        f"💵 Monto: `${monto} USD`\n"
        f"📝 Ref: `{referencia}`\n\n"
        f"Revisa Banco Digital de Trabajadores (RIF: 503619694)\n\n"
        f"Acción:"
    )
    
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Aprobar y generar PDF", "callback_data": f"aprobar_{telefono}"},
                    {"text": "❌ Rechazar pago", "callback_data": f"rechazar_{telefono}"}
                ],
                [
                    {"text": "⏳ Marcar pendiente", "callback_data": f"pendiente_{telefono}"}
                ]
            ]
        }
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def editar_mensaje(chat_id: str, message_id: int, texto: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "message_id": message_id, "text": texto, "parse_mode": "Markdown"})

async def enviar_pdf(chat_id: str, pdf_bytes, filename: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    file_obj = io.BytesIO(bytes(pdf_bytes))
    files = {"document": (filename, file_obj, "application/pdf")}
    data = {
        "chat_id": chat_id,
        "caption": "Pago verificado!\n\nInforme Agronomico PDF\nRIF: 503619694",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data, files=files)
        print(f"Respuesta PDF: {response.status_code} - {response.text[:200]}")

# ==========================================
# CALCULAR INFORME AGRONOMICO
# ==========================================
def calcular_informe_agronomico(d: dict):
    # ==========================================
    # 1. EXTRACCIÓN DE DATOS BASE
    # ==========================================
    ph = safe_float(d.get('ph'), 0.0)
    cic = safe_float(d.get('cic'), 1.0)
    ce = safe_float(d.get('ce'), 0.0)
    p_disponible = safe_float(d.get('p_disponible'), 0.0)
    area = safe_float(d.get('area'), 1.0)
    prnt = safe_float(d.get('prnt'), 100.0)
    ph_deseado = safe_float(d.get('ph_deseado'), 6.5)
    textura = safe_str(d.get('textura'), 'Franca').lower()
    cultivo = safe_str(d.get('cultivo'), 'Maiz').lower()
    zona = safe_str(d.get('zona'), 'Llanos').lower()
    temporada = safe_str(d.get('temporada'), 'Lluvias').lower()
    escala = safe_str(d.get('escala'), 'Pequeno').lower()
    ultima_cal = safe_float(d.get('ultima_cal_meses'), 12)
    ultima_mo = safe_float(d.get('ultima_mo_meses'), 12)

    # ==========================================
    # 🛡️ 2. CÓDIGO INTELIGENTE: Detección automática ppm vs meq/100g
    # ==========================================
    ca_raw = safe_float(d.get('ca'), 0.0)
    mg_raw = safe_float(d.get('mg'), 0.0)
    k_raw = safe_float(d.get('k'), 0.0)
    na_raw = safe_float(d.get('na'), 0.0)
    al_h_raw = safe_float(d.get('al_h'), 0.0)

    suma_cationes = ca_raw + mg_raw + k_raw + na_raw + al_h_raw
    nota_conversion = ""

    # Si la suma excede la CIC (y la CIC es válida > 0), asumimos que vienen en ppm
    if suma_cationes > cic and cic > 0:
        ca = ca_raw / 200.0    # ppm a meq/100g
        mg = mg_raw / 121.5    # ppm a meq/100g
        k = k_raw / 391.0      # ppm a meq/100g
        na = na_raw / 230.0    # ppm a meq/100g
        al_h = al_h_raw        # Al+H usualmente ya viene en meq/100g

        nota_conversion = (
            "Nota: Los valores de cationes excedian la CIC reportada. "
            "Se asumieron en ppm (mg/kg) y se convirtieron a meq/100g para el calculo. "
            "Se recomienda verificar las unidades con el laboratorio."
        )
    else:
        ca = ca_raw
        mg = mg_raw
        k = k_raw
        na = na_raw
        al_h = al_h_raw

    # 🛡️ CORRECCIÓN CRÍTICA: Si Al+H es 0 o no vino del frontend, calcularlo automáticamente
    # Fórmula agronómica: Al+H = CIC - (Ca + Mg + K + Na)
    suma_bases = ca + mg + k + na
    if al_h <= 0 and cic > suma_bases:
        al_h = round(cic - suma_bases, 2)
        print(f"️ Al+H no enviado o es 0. Calculado automáticamente: CIC({cic}) - Bases({suma_bases}) = {al_h} meq/100g")
    elif al_h <= 0 and cic <= suma_bases:
        # Si las bases ya superan la CIC, Al+H debe ser 0 (suelo alcalino)
        al_h = 0.0
        print(f"ℹ️ Al+H calculado como 0 (suelo alcalino): CIC({cic}) <= Bases({suma_bases})")

    # ==========================================
    # 3. CÁLCULO DE SATURACIONES (sobre valores corregidos)
    # ==========================================
    sat_ca = round((ca / cic) * 100, 1) if cic > 0 else 0.0
    sat_mg = round((mg / cic) * 100, 1) if cic > 0 else 0.0
    sat_k = round((k / cic) * 100, 1) if cic > 0 else 0.0
    sat_na = round((na / cic) * 100, 1) if cic > 0 else 0.0
    sat_al = round((al_h / cic) * 100, 1) if cic > 0 else 0.0
    psi = sat_na

    # ==========================================
    # 4. DIAGNÓSTICO GENERAL
    # ==========================================
    estado_ph = 'Acido' if ph < 5.5 else ('Alcalino' if ph > 7.5 else 'Optimo')
    estado_p = 'Bajo' if p_disponible < 10 else ('Alto' if p_disponible > 25 else 'Medio')
    alerta_acido = ph < 5.5
    alerta_tox_al = al_h > 0.5
    alerta_sodico = psi > 15
    ica_e = round(sat_al, 1) if ph < 5.5 and cic > 0 else 0.0

    if alerta_acido or alerta_tox_al:
        estado_general = 'ACIDO / DEGRADADO'
    elif alerta_sodico:
        estado_general = 'SODICO'
    elif cic < 5:
        estado_general = 'BAJA FERTILIDAD'
    elif ce > 3:
        estado_general = 'SALINO'
    else:
        estado_general = 'ACEPTABLE'

    diag = f'Suelo con pH {ph} ({estado_ph}), CIC de {cic} meq/100g. '
    if cic < 5: diag += 'Baja capacidad de intercambio. '
    if alerta_acido: diag += f'Acidez marcada (Al+H: {sat_al}%). '
    if alerta_sodico: diag += f'Condicion sodica (PSI: {psi}%). '
    if estado_p == 'Bajo': diag += f'Fosforo bajo ({p_disponible} ppm). '

    # ==========================================
    # 🛡️ 5. PLAN DE ENMIENDAS (CORREGIDO AGRONÓMICAMENTE)
    # ==========================================

    # --- 5.1 CAL (Factor 1.5 estándar FAO/INIA para 0-20 cm) ---
    dosis_cal = 0.0
    rec_cal = 'No requerido'
    if ph < ph_deseado and al_h > 0:
        dosis_cal = round(((al_h * 1.5) * 1000) / (prnt / 100)) if prnt > 0 else 0
        if ultima_cal <= 6:
            dosis_cal = round(dosis_cal * 0.5)
        elif ultima_cal <= 12:
            dosis_cal = round(dosis_cal * 0.75)
        rec_cal = 'Incorporar 15-20 cm antes de siembra'

    # --- 5.2 YESO (Sin cambios) ---
    dosis_yeso = 0.0
    rec_yeso = 'No requerido'
    if psi > 15:
        dosis_yeso = round((psi - 15) * cic * 20)
        rec_yeso = 'Aplicar en superficie, no incorporar'

    # --- 5.3 MATERIA ORGÁNICA (Bases dinámicas según textura) ---
    dosis_mo = 0.0
    rec_mo = 'No requerido'
    if cic < 15 or 'arenosa' in textura or 'franca' in textura:
        if 'arcillosa' in textura:
            base_mo = 8.0   # Arcillas necesitan más MO para estructura
        elif 'arenosa' in textura:
            base_mo = 5.0   # Aumentado para mejorar retención en franco-arenosos
        else:
            base_mo = 6.0   # Francos

        # Bonus de recuperación si la CIC es muy baja (suelo degradado)
        if cic < 5:
            base_mo += 2.0

        dosis_mo = round(base_mo, 1)
        if ultima_mo <= 6:
            dosis_mo = round(dosis_mo * 0.5, 1)
        elif ultima_mo <= 12:
            dosis_mo = round(dosis_mo * 0.75, 1)
        rec_mo = 'Mezclar con suelo en preparacion de cama'

    # --- 5.4 NPK (Sin cambios) ---
    npk_base = {'maiz': 300, 'arroz': 250, 'cafe': 200, 'cacao': 180,
                'hortalizas': 400, 'platano': 350, 'pastos': 150}
    dosis_npk = npk_base.get(cultivo, 200)
    if 'grande' in escala: dosis_npk = round(dosis_npk * 1.1)
    elif 'familia' in escala: dosis_npk = round(dosis_npk * 0.8)

    # --- 5.5 FÓSFORO (Sin cambios) ---
    dosis_p = 0.0
    rec_p = 'No requerido'
    if p_disponible < 15:
        dosis_p = round((15 - p_disponible) * 5)
        rec_p = 'Fraccionar en 3 aplicaciones' if ica_e > 30 else 'Aplicar en siembra como fondo'

    # --- 5.6 AZUFRE (Sin cambios) ---
    dosis_s = 50 if ph > 7.5 or ce > 2 else 0.0

    # ==========================================
    # 6. CALENDARIO Y ROTACIÓN
    # ==========================================
    calendario = [
        {'periodo': 'Mes 1', 'actividad': 'Preparacion', 'detalle': 'Cal + MO + labranza'},
        {'periodo': 'Mes 2', 'actividad': 'Siembra', 'detalle': 'NPK fondo + P'},
        {'periodo': 'Mes 3-4', 'actividad': 'Desarrollo', 'detalle': '1er NPK fraccionado'},
        {'periodo': 'Mes 5-6', 'actividad': 'Floracion', 'detalle': '2do NPK + monitoreo'},
        {'periodo': 'Mes 7-8', 'actividad': 'Cosecha', 'detalle': 'Cosecha + rastrojo'},
    ]
    rotacion = [
        {'cultivo': cultivo.capitalize(), 'duracion': 'Ciclo completo', 'beneficio': 'Principal'},
        {'cultivo': 'Leguminosa', 'duracion': '3 meses', 'beneficio': 'Recupera N'},
    ]

    # ==========================================
    # 7. PROYECCIÓN ROI
    # ==========================================
    rend_base = {'maiz': 5.0, 'arroz': 4.5, 'cafe': 1.5, 'cacao': 1.2,
                 'hortalizas': 20.0, 'platano': 25.0, 'pastos': 8.0}
    rend_sin = rend_base.get(cultivo, 5.0)
    incremento_pct = min(60, sum([
        15 if dosis_cal > 0 else 0,
        10 if dosis_yeso > 0 else 0,
        12 if dosis_mo > 0 else 0,
        8 if dosis_p > 0 else 0,
        15 if dosis_npk > 0 else 0
    ]))
    rend_con = round(rend_sin * (1 + incremento_pct / 100), 1)

    costo_total = round(
        (dosis_cal * 0.15) + (dosis_yeso * 0.20) + (dosis_mo * 30) +
        (dosis_npk * 0.80) + (dosis_p * 1.50) + (dosis_s * 0.50), 2
    )
    precio = {'maiz': 250, 'arroz': 350, 'cafe': 3500, 'cacao': 3000,
              'hortalizas': 800, 'platano': 200, 'pastos': 150}.get(cultivo, 300)
    retorno_esperado = round((rend_con - rend_sin) * precio, 2)
    roi_pct = round((retorno_esperado / costo_total * 100), 0) if costo_total > 0 else 0
    payback_meses = '8-12' if roi_pct > 100 else ('12-18' if roi_pct > 50 else '18-24')

    roi = {
        'costo_total_usd': costo_total,
        'rendimiento_sin_enmiendas': rend_sin,
        'rendimiento_con_enmiendas': rend_con,
        'incremento_pct': incremento_pct,
        'retorno_esperado_usd': retorno_esperado,
        'roi_pct': roi_pct,
        'payback_meses': payback_meses,
    }

    # ==========================================
    # 8. RECOMENDACIONES FINALES
    # ==========================================
    recomendaciones = {
        'prioridades': [], 'manejo_integrado': [], 'gestion_agua': [], 'monitoreo': []
    }
    if alerta_acido: recomendaciones['prioridades'].append(f'Encalado urgente: {dosis_cal} kg/ha')
    if alerta_sodico: recomendaciones['prioridades'].append(f'Corregir sodicidad: {dosis_yeso} kg/ha yeso')
    if estado_p == 'Bajo': recomendaciones['prioridades'].append(f'Aportar fosforo: {dosis_p} kg/ha')
    if not recomendaciones['prioridades']: recomendaciones['prioridades'].append('Mantener manejo actual')

    recomendaciones['manejo_integrado'].append('Incorporar materia organica en cada ciclo')
    recomendaciones['manejo_integrado'].append('Rotar cultivos con leguminosas')
    recomendaciones['gestion_agua'].append('Programar riego suplementario si es temporada seca')
    recomendaciones['monitoreo'].append('Analisis de suelo cada 12 meses')

    # ==========================================
    # 9. RETURN CON TODOS LOS CAMPOS (incluye valores corregidos para el PDF)
    # ==========================================
    return {
        'sat_ca': sat_ca, 'sat_mg': sat_mg, 'sat_k': sat_k, 'sat_na': sat_na, 'sat_al': sat_al,
        'psi': psi, 'ica_e': ica_e, 'estado_ph': estado_ph, 'estado_p': estado_p,
        'estado_general': estado_general, 'diagnostico_expr': diag,
        'alerta_acido': alerta_acido, 'alerta_tox_al': alerta_tox_al, 'alerta_sodico': alerta_sodico,
        'dosis_cal_kg_ha': dosis_cal, 'dosis_yeso_kg_ha': dosis_yeso, 'dosis_mo_ton_ha': dosis_mo,
        'dosis_npk_kg_ha': dosis_npk, 'dosis_p_kg_ha': dosis_p, 'dosis_s_kg_ha': dosis_s,
        'recomendacion_cal': rec_cal, 'recomendacion_yeso': rec_yeso,
        'recomendacion_mo': rec_mo, 'recomendacion_p': rec_p,
        'calendario': calendario, 'rotacion': rotacion, 'roi': roi, 'recomendaciones': recomendaciones,
        # 🛡️ NUEVOS CAMPOS para pdf_generator.py
        'nota_conversion': nota_conversion,
        'ca_corregido': ca,
        'mg_corregido': mg,
        'k_corregido': k,
        'na_corregido': na,
        'al_h_corregido': al_h,
    }