-- =====================================================================
-- Pregunta: ¿Qué sector ganó y cuál perdió contra la inflación en cada año?
-- Lectura: var_real_pct compara diciembre contra diciembre del año anterior
-- (el último año, contra el último mes disponible). Positivo = le ganó a la inflación.
-- ganador / perdedor: el sector con mejor y peor resultado de ese año.
-- =====================================================================
WITH cierre AS (
    -- un punto por año: diciembre, o el último mes del último año
    SELECT serie_id, nombre, anio, fecha, etiqueta, indice_real
    FROM (
        SELECT
            r.*,
            ROW_NUMBER() OVER (PARTITION BY serie_id, anio ORDER BY fecha DESC) AS orden
        FROM v_salario_real AS r
    )
    WHERE orden = 1
),
anual AS (
    SELECT
        serie_id,
        nombre,
        anio,
        etiqueta AS hasta,
        100 * (indice_real / LAG(indice_real) OVER (PARTITION BY serie_id ORDER BY anio) - 1) AS var_real_pct
    FROM cierre
    WHERE serie_id <> 'sal_registrado'
),
ranking AS (
    SELECT
        a.*,
        RANK() OVER (PARTITION BY anio ORDER BY var_real_pct DESC) AS puesto,
        COUNT(*) OVER (PARTITION BY anio) AS sectores
    FROM anual AS a
    WHERE var_real_pct IS NOT NULL
)
SELECT
    anio,
    MAX(hasta) AS hasta,
    ROUND(MAX(CASE WHEN serie_id = 'sal_privado' THEN var_real_pct END), 2) AS privado_registrado,
    ROUND(MAX(CASE WHEN serie_id = 'sal_publico' THEN var_real_pct END), 2) AS publico,
    ROUND(MAX(CASE WHEN serie_id = 'sal_no_registrado' THEN var_real_pct END), 2) AS no_registrado,
    ROUND(MAX(CASE WHEN serie_id = 'sal_total' THEN var_real_pct END), 2) AS total,
    MAX(CASE WHEN puesto = 1 AND serie_id <> 'sal_total' THEN nombre END) AS ganador,
    MAX(CASE WHEN puesto = sectores AND serie_id <> 'sal_total' THEN nombre END) AS perdedor
FROM ranking
GROUP BY anio
ORDER BY anio;
