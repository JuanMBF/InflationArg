-- =====================================================================
-- Pregunta: ¿Le ganaron los salarios a la inflación entre dic-2016 y el último mes con datos?
-- Lectura: indice_real = 100 es el mismo poder de compra que en dic-2016; 90 es un 10 % menos.
-- var_real_pct es la ganancia (+) o pérdida (-) de poder de compra en todo el período.
-- maximo / minimo muestran el mejor y el peor momento de cada sector.
-- =====================================================================
WITH ultimo_comun AS (
    -- último mes en que hay dato de TODOS los sectores (las series terminan en meses distintos)
    SELECT MIN(hasta) AS fecha
    FROM (SELECT serie_id, MAX(fecha) AS hasta FROM v_salario_real GROUP BY serie_id)
),
extremos AS (
    SELECT
        serie_id,
        MAX(indice_real) AS maximo,
        MIN(indice_real) AS minimo
    FROM v_salario_real
    WHERE fecha <= (SELECT fecha FROM ultimo_comun)
    GROUP BY serie_id
)
SELECT
    r.serie_id,
    r.nombre,
    r.etiqueta AS hasta,
    ROUND(r.indice_real, 2) AS indice_real,
    ROUND(r.indice_real - 100, 2) AS var_real_pct,
    ROUND(e.maximo, 2) AS maximo,
    (SELECT etiqueta FROM v_salario_real x WHERE x.serie_id = r.serie_id AND x.indice_real = e.maximo) AS fecha_maximo,
    ROUND(e.minimo, 2) AS minimo,
    (SELECT etiqueta FROM v_salario_real x WHERE x.serie_id = r.serie_id AND x.indice_real = e.minimo) AS fecha_minimo,
    ROUND(100 * r.caida_desde_maximo, 2) AS distancia_al_maximo_pct,
    RANK() OVER (ORDER BY r.indice_real DESC) AS ranking
FROM v_salario_real AS r
JOIN extremos AS e ON e.serie_id = r.serie_id
WHERE r.fecha = (SELECT fecha FROM ultimo_comun)
ORDER BY ranking;
