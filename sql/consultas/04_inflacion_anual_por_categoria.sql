-- =====================================================================
-- Pregunta: ¿Cuánta inflación hubo cada año y qué la empujó: núcleo, regulados o estacionales?
-- Lectura: variación diciembre contra diciembre (el último año: acumulada hasta el último mes).
-- regulados - nucleo > 0 indica que las tarifas y precios regulados subieron más que el resto.
-- =====================================================================
WITH cierre AS (
    SELECT
        serie_id,
        anio,
        etiqueta,
        var_acumulada_anio,
        ROW_NUMBER() OVER (PARTITION BY serie_id, anio ORDER BY fecha DESC) AS orden
    FROM v_variacion
    WHERE serie_id IN ('ipc_nacional', 'ipc_nucleo', 'ipc_regulados', 'ipc_estacionales')
      AND var_acumulada_anio IS NOT NULL
)
SELECT
    anio,
    MAX(etiqueta) AS hasta,
    ROUND(100 * MAX(CASE WHEN serie_id = 'ipc_nacional' THEN var_acumulada_anio END), 2) AS nivel_general,
    ROUND(100 * MAX(CASE WHEN serie_id = 'ipc_nucleo' THEN var_acumulada_anio END), 2) AS nucleo,
    ROUND(100 * MAX(CASE WHEN serie_id = 'ipc_regulados' THEN var_acumulada_anio END), 2) AS regulados,
    ROUND(100 * MAX(CASE WHEN serie_id = 'ipc_estacionales' THEN var_acumulada_anio END), 2) AS estacionales,
    ROUND(100 * (MAX(CASE WHEN serie_id = 'ipc_regulados' THEN var_acumulada_anio END)
               - MAX(CASE WHEN serie_id = 'ipc_nucleo' THEN var_acumulada_anio END)), 2) AS regulados_menos_nucleo
FROM cierre
WHERE orden = 1
GROUP BY anio
ORDER BY anio;
