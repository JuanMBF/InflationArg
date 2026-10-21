-- =====================================================================
-- Pregunta: ¿En qué región del país subieron más los precios?
-- Lectura: acumulado desde dic-2016 e interanual del último mes por región, con su
-- puesto. diferencia_vs_pais_pp = puntos porcentuales por encima (+) o debajo (-) del total país.
-- =====================================================================
WITH ultimo AS (
    SELECT MAX(fecha) AS fecha FROM v_variacion WHERE grupo = 'ipc_region'
),
pais AS (
    SELECT var_interanual FROM v_variacion
    WHERE serie_id = 'ipc_nacional' AND fecha = (SELECT fecha FROM ultimo)
)
SELECT
    v.region,
    v.nombre,
    v.etiqueta AS hasta,
    ROUND(v.valor - 100, 1) AS acumulado_desde_dic2016_pct,
    RANK() OVER (ORDER BY v.valor DESC) AS puesto_acumulado,
    ROUND(100 * v.var_interanual, 2) AS interanual_pct,
    RANK() OVER (ORDER BY v.var_interanual DESC) AS puesto_interanual,
    ROUND(100 * (v.var_interanual - p.var_interanual), 2) AS diferencia_vs_pais_pp
FROM v_variacion AS v
CROSS JOIN pais AS p
WHERE v.grupo = 'ipc_region'
  AND v.fecha = (SELECT fecha FROM ultimo)
ORDER BY CASE WHEN v.region = 'nacional' THEN 0 ELSE 1 END, puesto_acumulado;
