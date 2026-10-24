-- =====================================================================================
-- NOMINAGT & RRHH PRO v1.0 - PLANILLAS IGSS/IRTRA/INTECAP, PRESTACIONES Y AUDITORÍA SQL
-- Motor: MySQL 8.0+ / MariaDB
-- =====================================================================================

DROP DATABASE IF EXISTS nomina_gt_db;
CREATE DATABASE nomina_gt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE nomina_gt_db;

-- 1. TABLA DE COLABORADORES ACTIVOS
CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_emp VARCHAR(20) NOT NULL UNIQUE,
    dpi VARCHAR(20) NOT NULL UNIQUE,
    nombre_completo VARCHAR(120) NOT NULL,
    puesto VARCHAR(80) NOT NULL,
    departamento VARCHAR(60) NOT NULL,
    salario_base DECIMAL(10,2) NOT NULL CHECK (salario_base >= 3000.00),
    afiliacion_igss VARCHAR(25) NOT NULL,
    estado ENUM('ACTIVO', 'SUSPENDIDO_IGSS', 'VACACIONES') DEFAULT 'ACTIVO',
    fecha_ingreso DATE NOT NULL
);

-- 2. TABLA DE PLANILLAS EMITIDAS (CALCULADA AUTOMÁTICAMENTE POR EL TRIGGER)
CREATE TABLE planilla_pagos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    periodo_mes VARCHAR(30) NOT NULL,
    salario_ordinario DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    bonificacion_decreto DECIMAL(10,2) NOT NULL DEFAULT 250.00,
    horas_extras INT NOT NULL DEFAULT 0,
    monto_horas_extras DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    comisiones DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    igss_laboral_483 DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    descuento_isr_anticipos DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    cuota_patronal_1267 DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    provision_prestaciones DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    liquido_a_recibir DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE RESTRICT
);

-- 3. BITÁCORA FORENSE DE AUDITORÍA DE RECURSOS HUMANOS
CREATE TABLE bitacora_rrhh (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_codigo VARCHAR(20) NOT NULL,
    evento VARCHAR(80) NOT NULL,
    detalle_financiero VARCHAR(255) NOT NULL,
    usuario_auditor VARCHAR(80) DEFAULT 'Derek Ramos - Admin RRHH',
    fecha_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================================
-- 4. TRIGGER TRANSACCIONAL: CÁLCULO AUTOMÁTICO DE LEYES LABORALES DE GUATEMALA
-- Calcula Hora Extra (1.5x), IGSS Laboral (4.83%), Patronal (12.67%) y Prestaciones
-- =====================================================================================
DELIMITER $$

CREATE TRIGGER trg_calcular_planilla_gt
BEFORE INSERT ON planilla_pagos
FOR EACH ROW
BEGIN
    DECLARE v_salario_base DECIMAL(10,2);
    DECLARE v_codigo_emp VARCHAR(20);
    DECLARE v_valor_hora_ordinaria DECIMAL(10,4);
    DECLARE v_base_afecta_igss DECIMAL(10,2);

    -- Obtener salario base del colaborador
    SELECT salario_base, codigo_emp INTO v_salario_base, v_codigo_emp
    FROM empleados WHERE id = NEW.empleado_id;

    SET NEW.salario_ordinario = v_salario_base;

    -- Cálculo legal de Hora Extra en Guatemala (Salario / 30 días / 8 horas * 1.5)
    SET v_valor_hora_ordinaria = (v_salario_base / 30.0) / 8.0;
    SET NEW.monto_horas_extras = ROUND(NEW.horas_extras * (v_valor_hora_ordinaria * 1.5), 2);

    -- Base afecta a IGSS (Salario Ordinario + Horas Extras + Comisiones; Decreto 78-89 NO paga IGSS)
    SET v_base_afecta_igss = NEW.salario_ordinario + NEW.monto_horas_extras + NEW.comisiones;

    -- Descuento IGSS Laboral (4.83%)
    SET NEW.igss_laboral_483 = ROUND(v_base_afecta_igss * 0.0483, 2);

    -- Cuota Patronal (10.67% IGSS + 1% IRTRA + 1% INTECAP = 12.67%)
    SET NEW.cuota_patronal_1267 = ROUND(v_base_afecta_igss * 0.1267, 2);

    -- Provisión Mensual de Prestaciones de Ley (Bono 14: 8.33% + Aguinaldo: 8.33% + Indemnización: 8.33% = 25%)
    SET NEW.provision_prestaciones = ROUND(v_base_afecta_igss * 0.2500, 2);

    -- Salario Líquido a Recibir
    SET NEW.liquido_a_recibir = ROUND(
        (v_base_afecta_igss + NEW.bonificacion_decreto) - (NEW.igss_laboral_483 + NEW.descuento_isr_anticipos), 2
    );

    -- Validación estricta SQL: un descuento no puede dejar al trabajador con sueldo negativo
    IF NEW.liquido_a_recibir <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'ERROR LEGAL SQL (Código de Trabajo GT): Los descuentos superan el salario líquido del colaborador.';
    END IF;

    -- Registrar en bitácora forense
    INSERT INTO bitacora_rrhh (empleado_codigo, evento, detalle_financiero)
    VALUES (
        v_codigo_emp,
        CONCAT('EMISIÓN BOLETA PLANILLA - ', NEW.periodo_mes),
        CONCAT('Devengado Base: Q', v_base_afecta_igss, ' | IGSS (4.83%): Q', NEW.igss_laboral_483, ' | Líquido Pagado: Q', NEW.liquido_a_recibir)
    );
END$$

DELIMITER ;

-- =====================================================================================
-- 5. DATOS SEMILLA EMPRESARIALES DE GUATEMALA
-- =====================================================================================
INSERT INTO empleados (codigo_emp, dpi, nombre_completo, puesto, departamento, salario_base, afiliacion_igss, fecha_ingreso) VALUES
('EMP-GT-001', '3019 48291 0101', 'Derek José Ramos Bar', 'Ingeniero de Sistemas / Líder TI', 'Tecnología e Innovación', 7500.00, '2026-09182-1', '2025-01-15'),
('EMP-GT-002', '2847 19283 0101', 'María Fernanda Salazar', 'Analista Financiera & Contable', 'Finanzas y Contabilidad', 6200.00, '2024-88210-4', '2025-03-01'),
('EMP-GT-003', '2591 83746 0101', 'Carlos Roberto Méndez', 'Administrador de Base de Datos', 'Tecnología e Innovación', 6800.00, '2023-44109-9', '2025-02-10'),
('EMP-GT-004', '3102 94857 0101', 'Ana Lucía Valenzuela', 'Coordinadora de Recursos Humanos', 'Capital Humano', 5500.00, '2025-11029-2', '2025-06-01');

-- Generar planillas iniciales disparando el Trigger automáticamente
INSERT INTO planilla_pagos (empleado_id, periodo_mes, bonificacion_decreto, horas_extras, comisiones, descuento_isr_anticipos) VALUES
(1, 'OCTUBRE 2026', 250.00, 8, 500.00, 0.00),
(2, 'OCTUBRE 2026', 250.00, 4, 0.00, 150.00),
(3, 'OCTUBRE 2026', 250.00, 6, 300.00, 0.00),
(4, 'OCTUBRE 2026', 250.00, 0, 0.00, 0.00);