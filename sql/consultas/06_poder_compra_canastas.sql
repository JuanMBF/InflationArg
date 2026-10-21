-- =====================================================================
-- Pregunta: ¿Cuántas Canastas Básicas Totales compran el salario promedio (RIPTE),
-- el salario mínimo y la jubilación mínima?
-- Lectura: CBT de un adulto equivalente en GBA. Menos de 1 = ese ingreso no alcanza
-- para que una sola persona adulta supere la línea de pobreza.
-- Un punto por año (diciembre) más el último mes con todas las series.
-- =====================================================================
WITH completo AS (
    SELECT *
    FROM v_poder_compra
    WHERE ripte IS NOT NULL AND smvm IS NOT NULL AND haber_minimo IS NOT NULL
),
ultimo AS (
    SELECT MAX(fecha) AS fecha FROM completo
)
SELECT
    etiqueta AS mes,
    ROUND(cbt, 2) AS cbt_pesos,
    ROUND(cbt_por_ripte, 2) AS cbt_por_ripte,
    ROUND(cbt_por_smvm, 2) AS cbt_por_salario_minimo,
    ROUND(cbt_por_haber_minimo, 2) AS cbt_por_jubilacion_minima,
    CASE WHEN fecha = (SELECT fecha FROM ultimo) THEN 1 ELSE 0 END AS es_ultimo
FROM completo
WHERE mes = 12 OR fecha = (SELECT fecha FROM ultimo)
ORDER BY fecha;
