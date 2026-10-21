-- =====================================================================
-- Pregunta: ¿Qué rubros del IPC subieron más y cuáles menos?
-- Lectura: acumulado_desde_dic2016_pct = cuánto subió cada rubro desde la base;
-- veces = cuántas veces se multiplicó el precio (índice / 100).
-- ultimo_anio_pct = variación interanual del último mes. Las columnas "vs_general" restan
-- la variación del nivel general: positivo = el rubro se encareció más que el promedio.
-- =====================================================================
WITH ultimo AS (
    SELECT MAX(fecha) AS fecha FROM v_variacion WHERE grupo = 'ipc_rubro'
),
general AS (
    SELECT valor, var_interanual
    FROM v_variacion
    WHERE serie_id = 'ipc_nacional' AND fecha = (SELECT fecha FROM ultimo)
)
SELECT
    RANK() OVER (ORDER BY v.valor DESC) AS puesto_acumulado,
    v.nombre AS rubro,
    v.etiqueta AS hasta,
    ROUND(v.valor / 100, 1) AS veces,
    ROUND(v.valor - 100, 1) AS acumulado_desde_dic2016_pct,
    ROUND(100 * (v.valor / g.valor - 1), 1) AS acumulado_vs_general_pct,
    RANK() OVER (ORDER BY v.var_interanual DESC) AS puesto_ultimo_anio,
    ROUND(100 * v.var_interanual, 2) AS ultimo_anio_pct,
    ROUND(100 * (v.var_interanual - g.var_interanual), 2) AS ultimo_anio_vs_general_pp
FROM v_variacion AS v
CROSS JOIN general AS g
WHERE v.grupo = 'ipc_rubro'
  AND v.fecha = (SELECT fecha FROM ultimo)
ORDER BY puesto_acumulado;
