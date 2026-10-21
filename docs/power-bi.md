# Guía: dashboard en Power BI con el modelo estrella

Power BI Desktop es una app de Windows, así que este dashboard se arma a mano. El pipeline ya deja los datos listos y modelados: la idea es mostrar que sabés importar un modelo estrella, relacionarlo y escribir medidas DAX. Lleva unos 30 a 45 minutos.

## 1. Conseguir los CSV

Cualquiera de estas dos opciones:

- Bajar `powerbi.zip` desde la página [Metodología y QA](https://juanmbf.github.io/InflationArg/metodologia/#descargas-titulo) del sitio y descomprimirlo.
- O correr el pipeline: `python -m inflationarg all`. Los archivos quedan en `build/powerbi/`.

| Archivo | Qué es | Clave |
|---|---|---|
| `dim_fecha.csv` | Un mes por fila: año, mes, trimestre, etiqueta (`sep-2026`) | `fecha` |
| `dim_serie.csv` | Qué mide cada serie, su grupo, región, unidad y fuente | `serie_id` |
| `fact_valor.csv` | El valor de cada serie en cada mes (formato largo) y su `estado` de QA | `fecha` + `serie_id` |
| `salario_real.csv` | Salario real por sector ya calculado (dic-2016 = 100) | `fecha` + `serie_id` |

Los CSV usan coma como separador, **punto como decimal** y UTF-8.

## 2. Importar

1. **Inicio → Obtener datos → Texto/CSV** y elegir `dim_fecha.csv`. Tocar **Transformar datos** (no "Cargar").
2. Repetir con los otros tres archivos. Quedan cuatro consultas en el Editor de Power Query.
3. Tipos de datos. Si tu Windows está en español, el punto decimal se lee mal: en cada consulta, clic derecho en la columna `valor` (o `indice_real`, etc.) → **Cambiar tipo → Usar configuración regional…** → *Número decimal* con *Inglés (Estados Unidos)*. Así:
   - `fecha` → **Fecha** (en las cuatro tablas).
   - `valor`, `indice_nominal`, `indice_real`, `var_real_interanual` → **Número decimal** (con configuración regional inglés).
   - `anio`, `mes`, `trimestre` → **Número entero**.
4. **Cerrar y aplicar**.

## 3. Relaciones (vista de modelo)

Power BI puede detectarlas solo; verificá que queden así, todas de **uno a varios** y con filtro en una sola dirección:

```
dim_fecha[fecha]     1 ──── * fact_valor[fecha]
dim_serie[serie_id]  1 ──── * fact_valor[serie_id]
dim_fecha[fecha]     1 ──── * salario_real[fecha]
dim_serie[serie_id]  1 ──── * salario_real[serie_id]
```

Después: clic derecho en `dim_fecha` → **Marcar como tabla de fechas** → columna `fecha`. Esto habilita las funciones de inteligencia de tiempo (`DATEADD`, `SAMEPERIODLASTYEAR`).

Ordená `dim_fecha[etiqueta]` por `dim_fecha[fecha]` (**Herramientas de columnas → Ordenar por columna**) para que los meses no queden en orden alfabético.

## 4. Medidas DAX

Crear una tabla vacía `Medidas` (**Inicio → Especificar datos → Cargar**) y agregar:

```dax
Valor =
CALCULATE ( SUM ( fact_valor[valor] ), fact_valor[estado] = "ok" )

Var. mensual % =
VAR actual = [Valor]
VAR anterior = CALCULATE ( [Valor], DATEADD ( dim_fecha[fecha], -1, MONTH ) )
RETURN IF ( ISBLANK ( anterior ), BLANK (), DIVIDE ( actual, anterior ) - 1 )

Var. interanual % =
VAR actual = [Valor]
VAR anterior = CALCULATE ( [Valor], SAMEPERIODLASTYEAR ( dim_fecha[fecha] ) )
RETURN IF ( ISBLANK ( anterior ), BLANK (), DIVIDE ( actual, anterior ) - 1 )

Salario real =
AVERAGE ( salario_real[indice_real] )

Pérdida real vs. dic-2016 % =
DIVIDE ( [Salario real], 100 ) - 1

Canastas por RIPTE =
DIVIDE (
    CALCULATE ( [Valor], dim_serie[serie_id] = "ripte" ),
    CALCULATE ( [Valor], dim_serie[serie_id] = "cbt" )
)

Canastas por salario mínimo =
DIVIDE (
    CALCULATE ( [Valor], dim_serie[serie_id] = "smvm" ),
    CALCULATE ( [Valor], dim_serie[serie_id] = "cbt" )
)

RIPTE en dólares =
DIVIDE (
    CALCULATE ( [Valor], dim_serie[serie_id] = "ripte" ),
    CALCULATE ( [Valor], dim_serie[serie_id] = "tc_oficial" )
)
```

Formato: las medidas `%` como **Porcentaje** con 1 decimal; las de canastas con 2 decimales.

> `fact_valor[estado] = "ok"` deja afuera lo que la QA puso en cuarentena (el RIPTE de ago-2026, que repite el valor de junio). Es la misma regla que usan las vistas SQL.

## 5. Páginas sugeridas

**Página 1 · Resumen**
- Tres **tarjetas**: `Pérdida real vs. dic-2016 %` filtrada a cada sector (privado registrado, público, no registrado) en el último mes con datos (filtro de página: `dim_fecha[fecha]` = jul-2026).
- **Gráfico de líneas**: eje X `dim_fecha[fecha]`, valores `Salario real`, leyenda `dim_serie[nombre]`, filtro `dim_serie[grupo] = salario_indice`. Agregar una **línea constante** en 100 (panel de análisis).

**Página 2 · Inflación**
- **Columnas**: `Var. mensual %` por mes con filtro `dim_serie[serie_id] = ipc_nacional`.
- **Líneas**: `Var. interanual %` con leyenda `dim_serie[nombre]` y filtro `grupo = ipc_categoria` (núcleo, regulados, estacionales).
- **Segmentador** por `dim_fecha[anio]`.

**Página 3 · Rubros y regiones**
- **Barras horizontales**: `Var. interanual %` del último mes por `dim_serie[nombre]`, filtro `grupo = ipc_rubro`, ordenado de mayor a menor.
- Lo mismo con `grupo = ipc_region`.

**Página 4 · Poder de compra**
- **Líneas**: `Canastas por RIPTE` y `Canastas por salario mínimo` por mes, con línea constante en 1.
- **Líneas**: `RIPTE en dólares`.

## 6. Verificar contra el sitio

Con la foto de datos del 21/10/2026, estos números tienen que coincidir con el [dashboard web](https://juanmbf.github.io/InflationArg/dashboard/) y con `python -m inflationarg consulta 01`:

| Medida | Filtro | Valor |
|---|---|---|
| `Salario real` | `sal_total`, jul-2026 | 78,21 |
| `Salario real` | `sal_publico`, jul-2026 | 65,71 |
| `Var. mensual %` | `ipc_nacional`, dic-2023 | 25,5 % |
| `Canastas por RIPTE` | jul-2026 | 3,84 |

Si no coinciden, lo más común es el separador decimal (paso 2.3) o que falte marcar `dim_fecha` como tabla de fechas.

## 7. Publicarlo

**Archivo → Exportar → PDF** genera un PDF de las páginas para adjuntar al CV. Para compartirlo en línea hace falta una cuenta de Power BI Service (**Publicar**); con la cuenta gratuita se puede publicar en "Mi área de trabajo" y sacar capturas para el README o LinkedIn.
