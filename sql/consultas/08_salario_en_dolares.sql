-- =====================================================================
-- Pregunta: ¿Cuánto vale el salario en dólares oficiales y cómo cambió?
-- Lectura: promedio anual del RIPTE, del salario mínimo y de la jubilación mínima
-- divididos por el tipo de cambio oficial de valuación del BCRA de cada mes.
-- El año en curso promedia solo los meses disponibles (columna meses).
-- =====================================================================
SELECT
    anio,
    COUNT(*) AS meses,
    ROUND(AVG(ripte_usd), 0) AS ripte_usd,
    ROUND(AVG(smvm_usd), 0) AS salario_minimo_usd,
    ROUND(AVG(haber_minimo_usd), 0) AS jubilacion_minima_usd,
    ROUND(AVG(tc_oficial), 2) AS tipo_cambio_promedio
FROM v_salario_usd
WHERE ripte_usd IS NOT NULL
  AND anio >= 2017
GROUP BY anio
ORDER BY anio;
