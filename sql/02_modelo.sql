-- =====================================================================
-- 02_modelo.sql: de staging al modelo estrella
-- =====================================================================
-- Requiere: parametro(inicio_fact, fecha_corte), stg_valor, qa_marca, dim_serie.

-- dim_fecha: todos los meses entre el inicio y la fecha de corte (CTE recursiva).
INSERT INTO dim_fecha (fecha, anio, mes, trimestre, mes_idx, etiqueta)
WITH RECURSIVE meses (fecha) AS (
    SELECT valor FROM parametro WHERE clave = 'inicio_fact'
    UNION ALL
    SELECT date(fecha, '+1 month')
    FROM meses
    WHERE fecha < (SELECT valor FROM parametro WHERE clave = 'fecha_corte')
),
partes AS (
    SELECT
        fecha,
        CAST(strftime('%Y', fecha) AS INTEGER) AS anio,
        CAST(strftime('%m', fecha) AS INTEGER) AS mes
    FROM meses
)
SELECT
    fecha,
    anio,
    mes,
    (mes - 1) / 3 + 1,
    anio * 12 + mes,
    substr('enefebmarabrmayjunjulagosepoctnovdic', (mes - 1) * 3 + 1, 3) || '-' || anio
FROM partes;

-- Valores con fecha posterior al corte (p. ej. salario mínimo ya fijado por
-- resolución para meses que todavía no ocurrieron): se apartan y se informan.
INSERT INTO excluido (fecha, serie_id, valor, motivo)
SELECT fecha, serie_id, valor, 'valor a futuro: posterior a la fecha de corte'
FROM stg_valor
WHERE fecha > (SELECT valor FROM parametro WHERE clave = 'fecha_corte');

-- fact_valor: la ventana de análisis, con el estado que asignó la QA.
-- Las series que se publican con rezago se fechan en el mes que miden
-- (fecha de publicación - desfase_meses): así se deflactan con el IPC correcto.
-- staging y qa_marca quedan con la fecha de publicación, tal como la valida la QA.
INSERT INTO fact_valor (fecha, serie_id, valor, estado)
SELECT
    d.fecha,
    s.serie_id,
    s.valor,
    CASE WHEN m.serie_id IS NULL THEN 'ok' ELSE 'sospechoso' END
FROM stg_valor AS s
JOIN dim_serie AS ds ON ds.serie_id = s.serie_id
JOIN dim_fecha AS d ON d.fecha = date(s.fecha, '-' || ds.desfase_meses || ' months')
LEFT JOIN qa_marca AS m ON m.fecha = s.fecha AND m.serie_id = s.serie_id;
