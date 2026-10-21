-- =====================================================================
-- Pregunta: ¿Qué sector salió mejor y cuál peor parado frente a la inflación cada año?
-- Lectura: var_real_pct compara diciembre contra diciembre del año anterior
-- (el último año, contra el último mes en que hay dato de todos los sectores).
-- Positivo = le ganó a la inflación. mejor / peor: el sector con mejor y peor resultado
-- del año, aunque los dos hayan perdido (o ganado) contra la inflación.
-- =====================================================================
WITH ultimo_comun AS (
    -- último mes con dato de todos los sectores: así el último año compara el mismo período
    SELECT MIN(hasta) AS fecha
    FROM (
        SELECT serie_id, MAX(fecha) AS hasta
        FROM v_salario_real
        WHERE serie_id <> 'sal_registrado'
        GROUP BY serie_id
    )
),
cierre AS (
    -- un punto por año: diciembre, o el último mes común del último año
    SELECT serie_id, nombre, anio, fecha, indice_real
    FROM (
        SELECT
            r.*,
            ROW_NUMBER() OVER (PARTITION BY serie_id, anio ORDER BY fecha DESC) AS orden
        FROM v_salario_real AS r
        WHERE r.serie_id <> 'sal_registrado'
          AND r.fecha <= (SELECT fecha FROM ultimo_comun)
    )
    WHERE orden = 1
),
anual AS (
    SELECT
        serie_id,
        nombre,
        anio,
        fecha,
        100 * (indice_real / LAG(indice_real) OVER (PARTITION BY serie_id ORDER BY anio) - 1) AS var_real_pct
    FROM cierre
),
ranking AS (
    SELECT
        a.*,
        RANK() OVER (PARTITION BY anio ORDER BY var_real_pct DESC) AS puesto,
        COUNT(*) OVER (PARTITION BY anio) AS sectores
    FROM anual AS a
    WHERE var_real_pct IS NOT NULL
      AND serie_id <> 'sal_total'
),
total AS (
    SELECT anio, var_real_pct FROM anual WHERE serie_id = 'sal_total'
)
SELECT
    r.anio,
    (SELECT d.etiqueta FROM dim_fecha AS d
     WHERE d.fecha = (SELECT MAX(x.fecha) FROM ranking AS x WHERE x.anio = r.anio)) AS hasta,
    ROUND(MAX(CASE WHEN r.serie_id = 'sal_privado' THEN r.var_real_pct END), 2) AS privado_registrado,
    ROUND(MAX(CASE WHEN r.serie_id = 'sal_publico' THEN r.var_real_pct END), 2) AS publico,
    ROUND(MAX(CASE WHEN r.serie_id = 'sal_no_registrado' THEN r.var_real_pct END), 2) AS no_registrado,
    ROUND(MAX(t.var_real_pct), 2) AS total,
    MAX(CASE WHEN r.puesto = 1 THEN r.nombre END) AS ganador,
    MAX(CASE WHEN r.puesto = r.sectores THEN r.nombre END) AS perdedor
FROM ranking AS r
LEFT JOIN total AS t ON t.anio = r.anio
GROUP BY r.anio
ORDER BY r.anio;
