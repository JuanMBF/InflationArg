-- =====================================================================
-- Pregunta: ¿Hasta qué mes vale cada conclusión?
-- Lectura: las series se publican con rezagos distintos; cada análisis llega hasta el
-- último mes en que TODAS sus series tienen dato válido (sin valores a futuro ni sospechosos).
-- El privado no registrado va aparte: el INDEC lo publica con 5 meses de rezago y acá se
-- fecha en el mes que mide, así que termina antes que el resto de los salarios.
-- =====================================================================
WITH alcance (analisis, grupo, solo_serie, sin_serie) AS (
    VALUES
        ('Salario real: total, registrados, privado y público', 'salario_indice', NULL, 'sal_no_registrado'),
        ('Salario real: total, registrados, privado y público', 'ipc_region', NULL, NULL),
        ('Salario real: privado no registrado', 'salario_indice', 'sal_no_registrado', NULL),
        ('Salario real: privado no registrado', 'ipc_region', NULL, NULL),
        ('Inflación, rubros y regiones', 'ipc_region', NULL, NULL),
        ('Inflación, rubros y regiones', 'ipc_categoria', NULL, NULL),
        ('Inflación, rubros y regiones', 'ipc_rubro', NULL, NULL),
        ('Poder de compra en canastas', 'ingreso_pesos', NULL, NULL),
        ('Poder de compra en canastas', 'canasta', NULL, NULL),
        ('Salario en dólares', 'ingreso_pesos', NULL, NULL),
        ('Salario en dólares', 'tipo_cambio', NULL, NULL)
)
SELECT
    a.analisis,
    MIN(c.hasta) AS vale_hasta,
    GROUP_CONCAT(DISTINCT c.grupo) AS grupos,
    MAX(c.meses_de_rezago) AS rezago_maximo_meses
FROM alcance AS a
JOIN v_cobertura AS c
    ON c.grupo = a.grupo
    AND (a.solo_serie IS NULL OR c.serie_id = a.solo_serie)
    AND (a.sin_serie IS NULL OR c.serie_id <> a.sin_serie)
GROUP BY a.analisis
ORDER BY vale_hasta, a.analisis;
