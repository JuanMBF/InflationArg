-- =====================================================================
-- Pregunta: ¿Cuáles fueron los meses de mayor inflación desde 2017?
-- Lectura: top 10 de variación mensual del IPC nacional, con la interanual de ese mes
-- y el puesto que ocupa también en el ranking de inflación interanual.
-- =====================================================================
SELECT
    ranking_mensual AS puesto,
    etiqueta AS mes,
    ROUND(100 * var_mensual, 2) AS inflacion_mensual_pct,
    ROUND(100 * var_interanual, 2) AS inflacion_interanual_pct,
    ranking_interanual AS puesto_interanual
FROM v_inflacion
WHERE serie_id = 'ipc_nacional'
  AND ranking_mensual <= 10
ORDER BY ranking_mensual;
