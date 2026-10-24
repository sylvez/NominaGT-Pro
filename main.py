from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error

app = FastAPI(
    title="NominaGT & RRHH Pro v3.0 Banking & Corporate Suite API",
    description="Propietario y Desarrollador Principal: Kevin Alejandro Vásquez Ramos",
    version="3.0.0"
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
    "password": "2025202241",  # <-- Coloca tu contraseña de MySQL si tienes una configurada
    "database": "nomina_gt_db"
}

def get_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error MySQL: {str(e)}")

class EmpleadoCreate(BaseModel):
    codigo_emp: str
    dpi: str
    nit: str = "CF"
    nombre_completo: str
    puesto: str
    departamento: str
    salario_base: float
    afiliacion_igss: str
    banco_ach: str = "Banco Industrial"
    cuenta_bancaria: str = "000-000000-0"
    tipo_cuenta: str = "MONETARIA"
    telefono_whatsapp: str = "50255550000"
    fecha_ingreso: str = "2026-01-15"

class PlanillaCreate(BaseModel):
    empleado_id: int
    periodo_mes: str = "OCTUBRE 2026"
    bonificacion_decreto: float = 250.00
    horas_extras: int = 0
    comisiones: float = 0.00
    descuento_isr_anticipos: float = 0.00

class GestionRRHHCreate(BaseModel):
    empleado_id: int
    tipo_gestion: str
    dias_aplicados: int = 0
    observaciones: str

@app.get("/api/dashboard")
def obtener_datos_rrhh():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM empleados ORDER BY id ASC")
        empleados = cursor.fetchall()

        cursor.execute("""
            SELECT p.*, e.codigo_emp, e.nombre_completo, e.dpi, e.nit, e.puesto,
                   e.departamento, e.afiliacion_igss, e.banco_ach, e.cuenta_bancaria,
                   e.tipo_cuenta, e.telefono_whatsapp
            FROM planilla_pagos p
            JOIN empleados e ON p.empleado_id = e.id
            ORDER BY p.id DESC
        """)
        planillas = cursor.fetchall()

        cursor.execute("SELECT * FROM bitacora_rrhh ORDER BY id DESC LIMIT 100")
        bitacora = cursor.fetchall()

        return {
            "status": "ok",
            "propietario": "Kevin Alejandro Vásquez Ramos",
            "empleados": empleados,
            "planillas": planillas,
            "bitacora": bitacora
        }
    finally:
        cursor.close()
        conn.close()

@app.post("/api/empleados")
def registrar_nuevo_empleado(emp: EmpleadoCreate):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO empleados (
                codigo_emp, dpi, nit, nombre_completo, puesto, departamento,
                salario_base, afiliacion_igss, banco_ach, cuenta_bancaria,
                tipo_cuenta, telefono_whatsapp, fecha_ingreso
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            emp.codigo_emp, emp.dpi, emp.nit, emp.nombre_completo, emp.puesto,
            emp.departamento, emp.salario_base, emp.afiliacion_igss, emp.banco_ach,
            emp.cuenta_bancaria, emp.tipo_cuenta, emp.telefono_whatsapp, emp.fecha_ingreso
        ))
        conn.commit()
        return {"mensaje": "Colaborador registrado exitosamente", "id": cursor.lastrowid}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.msg)
    finally:
        cursor.close()
        conn.close()

@app.post("/api/planillas")
def emitir_boleta_planilla(datos: PlanillaCreate):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO planilla_pagos (empleado_id, periodo_mes, bonificacion_decreto, horas_extras, comisiones, descuento_isr_anticipos)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (datos.empleado_id, datos.periodo_mes, datos.bonificacion_decreto, datos.horas_extras, datos.comisiones, datos.descuento_isr_anticipos))
        conn.commit()
        return {"mensaje": "Boleta calculada y auditada por Trigger MySQL exitosamente"}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.msg)
    finally:
        cursor.close()
        conn.close()

@app.post("/api/gestiones")
def registrar_vacaciones_o_igss(g: GestionRRHHCreate):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        if g.tipo_gestion == "VACACIONES_ART130":
            cursor.execute("UPDATE empleados SET dias_vacaciones_disponibles = GREATEST(0, dias_vacaciones_disponibles - %s), estado = 'VACACIONES' WHERE id = %s", (g.dias_aplicados, g.empleado_id))
        elif g.tipo_gestion == "SUSPENSION_IGSS":
            cursor.execute("UPDATE empleados SET estado = 'SUSPENDIDO_IGSS' WHERE id = %s", (g.empleado_id,))

        cursor.execute("""
            INSERT INTO gestiones_rrhh (empleado_id, tipo_gestion, dias_aplicados, observaciones)
            VALUES (%s, %s, %s, %s)
        """, (g.empleado_id, g.tipo_gestion, g.dias_aplicados, g.observaciones))
        conn.commit()
        return {"mensaje": "Gestión de RRHH aplicada correctamente"}
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=e.msg)
    finally:
        cursor.close()
        conn.close()