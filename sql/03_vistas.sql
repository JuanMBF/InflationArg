-- =====================================================================
-- 03_vistas.sql: capa de análisis sobre el modelo estrella
-- =====================================================================
-- Todas las vistas leen solo observaciones con estado = 'ok'.
-- Las variaciones usan LAG() pero verifican con mes_idx que el mes anterior
-- sea realmente el anterior: si faltara un mes, la variación queda en NULL
-- en vez de comparar contra un mes equivocado.

-- Valor de cada serie con sus atributos de fecha y serie (la tabla "ancha" del modelo).
CREATE VIEW v_valor AS
SELECT
    f.fecha,
    d.etiqueta,
    d.anio,
    d.mes,
    d.mes_idx,
    f.serie_id,
    s.nombre,
    s.grupo,
    s.region,
    s.unidad,
    f.valor
FROM fact_valor AS f
JOIN dim_fecha AS d ON d.fecha = f.fecha
JOIN dim_serie AS s ON s.serie_id = f.serie_id
WHERE f.estado = 'ok';

-- Variación mensual, interanual y acumulada en el año para cualquier serie.
CREATE VIEW v_variacion AS
WITH lags AS (
    SELECT
        v.*,
        LAG(v.valor, 1) OVER w AS valor_1,
        LAG(v.mes_idx, 1) OVER w AS idx_1,
        LAG(v.valor, 12) OVER w AS valor_12,
        LAG(v.mes_idx, 12) OVER w AS idx_12
    FROM v_valor AS v
    WINDOW w AS (PARTITION BY v.serie_id ORDER BY v.mes_idx)
)
SELECT
    l.fecha,
    l.etiqueta,
    l.anio,
    l.mes,
    l.mes_idx,
    l.serie_id,
    l.nombre,
    l.grupo,
    l.region,
    l.valor,
    CASE WHEN l.idx_1 = l.mes_idx - 1 THEN l.valor / l.valor_1 - 1 END AS var_mensual,
    CASE WHEN l.idx_12 = l.mes_idx - 12 THEN l.valor / l.valor_12 - 1 END AS var_interanual,
    l.valor / dic.valor - 1 AS var_acumulada_anio
FROM lags AS l
LEFT JOIN v_valor AS dic
    ON dic.serie_id = l.serie_id
    AND dic.fecha = (l.anio - 1) || '-12-01';

-- Inflación (IPC por región y por categoría) con ranking de picos mensuales.
CREATE VIEW v_inflacion AS
SELECT
    v.*,
    RANK() OVER (PARTITION BY v.serie_id ORDER BY v.var_mensual DESC) AS ranking_mensual,
    RANK() OVER (PARTITION BY v.serie_id ORDER BY v.var_interanual DESC) AS ranking_interanual
FROM v_variacion AS v
WHERE v.grupo IN ('ipc_region', 'ipc_categoria', 'ipc_rubro')
  AND v.var_mensual IS NOT NULL;

-- Salario real por sector: índice nominal llevado a base dic-2016 = 100 y
-- deflactado por el IPC nacional. 100 = mismo poder de compra que en dic-2016.
CREATE VIEW v_salario_real AS
WITH base AS (
    SELECT serie_id, valor AS valor_base
    FROM v_valor
    WHERE fecha = (SELECT valor FROM parametro WHERE clave = 'base_analisis')
),
ipc AS (
    SELECT fecha, valor AS ipc
    FROM v_valor
    WHERE serie_id = 'ipc_nacional'
),
ipc_base AS (
    SELECT ipc AS ipc_base
    FROM ipc
    WHERE fecha = (SELECT valor FROM parametro WHERE clave = 'base_analisis')
),
real AS (
    SELECT
        v.fecha,
        v.etiqueta,
        v.anio,
        v.mes,
        v.mes_idx,
        v.serie_id,
        v.nombre,
        100.0 * v.valor / b.valor_base AS indice_nominal,
        100.0 * (v.valor / b.valor_base) / (i.ipc / ib.ipc_base) AS indice_real
    FROM v_valor AS v
    JOIN base AS b ON b.serie_id = v.serie_id
    JOIN ipc AS i ON i.fecha = v.fecha
    CROSS JOIN ipc_base AS ib
    WHERE v.grupo = 'salario_indice'
      AND v.fecha >= (SELECT valor FROM parametro WHERE clave = 'base_analisis')
)
SELECT
    r.*,
    CASE WHEN LAG(r.mes_idx, 12) OVER w = r.mes_idx - 12
         THEN r.indice_real / LAG(r.indice_real, 12) OVER w - 1 END AS var_real_interanual,
    MAX(r.indice_real) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS maximo_previo,
    r.indice_real / MAX(r.indice_real) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) - 1
        AS caida_desde_maximo
FROM real AS r
WINDOW w AS (PARTITION BY r.serie_id ORDER BY r.mes_idx);

-- Poder de compra: cuántas Canastas Básicas Totales (adulto equivalente)
-- compra cada ingreso de referencia en el mes.
CREATE VIEW v_poder_compra AS
WITH pivote AS (
    SELECT
        fecha,
        etiqueta,
        anio,
        mes,
        MAX(CASE WHEN serie_id = 'ripte' THEN valor END) AS ripte,
        MAX(CASE WHEN serie_id = 'smvm' THEN valor END) AS smvm,
        MAX(CASE WHEN serie_id = 'haber_minimo' THEN valor END) AS haber_minimo,
        MAX(CASE WHEN serie_id = 'cbt' THEN valor END) AS cbt,
        MAX(CASE WHEN serie_id = 'cba' THEN valor END) AS cba
    FROM v_valor
    WHERE serie_id IN ('ripte', 'smvm', 'haber_minimo', 'cbt', 'cba')
    GROUP BY fecha, etiqueta, anio, mes
)
SELECT
    p.*,
    p.ripte / p.cbt AS cbt_por_ripte,
    p.smvm / p.cbt AS cbt_por_smvm,
    p.haber_minimo / p.cbt AS cbt_por_haber_minimo
FROM pivote AS p
WHERE p.cbt IS NOT NULL;

-- Ingresos en dólares al tipo de cambio oficial de valuación del BCRA.
CREATE VIEW v_salario_usd AS
WITH pivote AS (
    SELECT
        fecha,
        etiqueta,
        anio,
        mes,
        MAX(CASE WHEN serie_id = 'ripte' THEN valor END) AS ripte,
        MAX(CASE WHEN serie_id = 'smvm' THEN valor END) AS smvm,
        MAX(CASE WHEN serie_id = 'haber_minimo' THEN valor END) AS haber_minimo,
        MAX(CASE WHEN serie_id = 'tc_oficial' THEN valor END) AS tc_oficial
    FROM v_valor
    WHERE serie_id IN ('ripte', 'smvm', 'haber_minimo', 'tc_oficial')
    GROUP BY fecha, etiqueta, anio, mes
)
SELECT
    p.*,
    p.ripte / p.tc_oficial AS ripte_usd,
    p.smvm / p.tc_oficial AS smvm_usd,
    p.haber_minimo / p.tc_oficial AS haber_minimo_usd
FROM pivote AS p
WHERE p.tc_oficial IS NOT NULL;

-- Cobertura: desde y hasta cuándo hay datos válidos de cada serie.
CREATE VIEW v_cobertura AS
SELECT
    s.serie_id,
    s.nombre,
    s.grupo,
    s.fuente,
    MIN(f.fecha) AS desde,
    MAX(f.fecha) AS hasta,
    COUNT(*) AS meses,
    (SELECT mes_idx FROM dim_fecha WHERE fecha = (SELECT valor FROM parametro WHERE clave = 'fecha_corte'))
        - MAX(d.mes_idx) AS meses_de_rezago
FROM dim_serie AS s
JOIN fact_valor AS f ON f.serie_id = s.serie_id AND f.estado = 'ok'
JOIN dim_fecha AS d ON d.fecha = f.fecha
GROUP BY s.serie_id, s.nombre, s.grupo, s.fuente;
