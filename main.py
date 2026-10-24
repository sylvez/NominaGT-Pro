from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error

app = FastAPI(
    title="NominaGT & RRHH Pro v1.0 API",
    description="API Empresarial de Planillas de Guatemala (IGSS 4.83%, IRTRA, INTECAP, Bono 14 y Aguinaldo)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "202502241",  # <-- Coloca tu contraseña de MySQL si tienes una
    "database": "nomina_gt_db"
}

def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error MySQL: {str(e)}")

class PlanillaCreate(BaseModel):
    empleado_id: int
    periodo_mes: str = "OCTUBRE 2026"
    bonificacion_decreto: float = 250.00
    horas_extras: int = 0
    comisiones: float = 0.00
    descuento_isr_anticipos: float = 0.00

@app.get("/api/dashboard")
def obtener_datos_rrhh():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM empleados ORDER BY id ASC")
        empleados = cursor.fetchall()

        cursor.execute("""
            SELECT p.*, e.codigo_emp, e.nombre_completo, e.dpi, e.puesto, e.afiliacion_igss
            FROM planilla_pagos p
            JOIN empleados e ON p.empleado_id = e.id
            ORDER BY p.id DESC
        """)
        planillas = cursor.fetchall()

        cursor.execute("SELECT * FROM bitacora_rrhh ORDER BY id DESC LIMIT 100")
        bitacora = cursor.fetchall()

        return {
            "status": "ok",
            "empleados": empleados,
            "planillas": planillas,
            "bitacora": bitacora
        }
    finally:
        cursor.close()
        conn.close()

@app.post("/api/planillas")
def emitir_boleta_planilla(datos: PlanillaCreate):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # El Trigger trg_calcular_planilla_gt calcula automáticamente IGSS, Horas Extras y Prestaciones
        cursor.execute("""
            INSERT INTO planilla_pagos (empleado_id, periodo_mes, bonificacion_decreto, horas_extras, comisiones, descuento_isr_anticipos)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (datos.empleado_id, datos.periodo_mes, datos.bonificacion_decreto, datos.horas_extras, datos.comisiones, datos.descuento_isr_anticipos))
        conn.commit()
        return {"mensaje": "Boleta de planilla calculada y auditada por Trigger MySQL exitosamente"}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.msg)
    finally:
        cursor.close()
        conn.close()