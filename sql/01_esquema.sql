-- =====================================================================
-- 01_esquema.sql: tablas de staging, modelo estrella y control de calidad
-- =====================================================================
-- Flujo: CSV oficiales -> stg_valor (formato largo, sin filtrar)
--        -> dim_fecha / dim_serie / fact_valor (modelo estrella)
--        -> vistas de análisis (03_vistas.sql) -> sql/consultas/*.sql

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS v_cobertura;
DROP VIEW IF EXISTS v_salario_usd;
DROP VIEW IF EXISTS v_poder_compra;
DROP VIEW IF EXISTS v_salario_real;
DROP VIEW IF EXISTS v_inflacion;
DROP VIEW IF EXISTS v_variacion;
DROP VIEW IF EXISTS v_valor;
DROP TABLE IF EXISTS excluido;
DROP TABLE IF EXISTS fact_valor;
DROP TABLE IF EXISTS dim_fecha;
DROP TABLE IF EXISTS dim_serie;
DROP TABLE IF EXISTS qa_marca;
DROP TABLE IF EXISTS stg_valor;
DROP TABLE IF EXISTS parametro;

-- Parámetros de la corrida (fecha de corte, inicio del análisis, etc.).
CREATE TABLE parametro (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Staging: una fila por (mes, serie) tal como viene del CSV, sin nulos.
CREATE TABLE stg_valor (
    fecha    TEXT NOT NULL,
    serie_id TEXT NOT NULL,
    valor    REAL NOT NULL,
    archivo  TEXT NOT NULL
);

-- Observaciones que la QA marcó como sospechosas (se cargan pero no se analizan).
CREATE TABLE qa_marca (
    fecha    TEXT NOT NULL,
    serie_id TEXT NOT NULL,
    motivo   TEXT NOT NULL,
    PRIMARY KEY (fecha, serie_id)
);

-- Dimensión serie: qué mide cada serie, de qué fuente sale y en qué unidad.
CREATE TABLE dim_serie (
    serie_id TEXT PRIMARY KEY,
    nombre   TEXT NOT NULL,
    grupo    TEXT NOT NULL,
    region   TEXT NOT NULL,
    unidad   TEXT NOT NULL,
    base     TEXT,
    fuente   TEXT NOT NULL,
    archivo  TEXT NOT NULL,
    columna  TEXT NOT NULL
);

-- Dimensión fecha: un registro por mes calendario (primer día del mes).
CREATE TABLE dim_fecha (
    fecha     TEXT PRIMARY KEY,
    anio      INTEGER NOT NULL,
    mes       INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    trimestre INTEGER NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    mes_idx   INTEGER NOT NULL UNIQUE,  -- anio * 12 + mes: aritmética de meses sin fechas
    etiqueta  TEXT NOT NULL             -- "sep-2026"
);

-- Hechos en formato largo: el valor de cada serie en cada mes.
CREATE TABLE fact_valor (
    fecha    TEXT NOT NULL REFERENCES dim_fecha (fecha),
    serie_id TEXT NOT NULL REFERENCES dim_serie (serie_id),
    valor    REAL NOT NULL CHECK (valor > 0),
    estado   TEXT NOT NULL CHECK (estado IN ('ok', 'sospechoso')),
    PRIMARY KEY (fecha, serie_id)
) WITHOUT ROWID;

CREATE INDEX ix_fact_serie ON fact_valor (serie_id, fecha);

-- Valores fuera de la ventana de análisis por estar fechados a futuro.
CREATE TABLE excluido (
    fecha    TEXT NOT NULL,
    serie_id TEXT NOT NULL,
    valor    REAL NOT NULL,
    motivo   TEXT NOT NULL
);
