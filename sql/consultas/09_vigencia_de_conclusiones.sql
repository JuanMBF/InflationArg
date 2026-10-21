-- =====================================================================
-- Pregunta: ¿Hasta qué mes vale cada conclusión?
-- Lectura: las series se publican con rezagos distintos; cada análisis llega hasta el
-- último mes en que TODAS sus series tienen dato válido (sin valores a futuro ni sospechosos).
-- =====================================================================
WITH grupos (analisis, grupo) AS (
    VALUES
        ('Salario real por sector', 'salario_indice'),
        ('Salario real por sector', 'ipc_region'),
        ('Inflación, rubros y regiones', 'ipc_region'),
        ('Inflación, rubros y regiones', 'ipc_categoria'),
        ('Inflación, rubros y regiones', 'ipc_rubro'),
        ('Poder de compra en canastas', 'ingreso_pesos'),
        ('Poder de compra en canastas', 'canasta'),
        ('Salario en dólares', 'ingreso_pesos'),
        ('Salario en dólares', 'tipo_cambio')
)
SELECT
    g.analisis,
    MIN(c.hasta) AS vale_hasta,
    GROUP_CONCAT(DISTINCT c.grupo) AS grupos,
    MAX(c.meses_de_rezago) AS rezago_maximo_meses
FROM grupos AS g
JOIN v_cobertura AS c ON c.grupo = g.grupo
GROUP BY g.analisis
ORDER BY vale_hasta;
