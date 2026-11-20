// Gráficos del sitio con Apache ECharts. Los datos vienen incrustados en la página
// (<script type="application/json">) y salen de las vistas y consultas SQL del pipeline.
(function () {
  "use strict";

  var MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  var NOMBRES = {
    sal_privado: "Privado registrado",
    sal_publico: "Público",
    sal_no_registrado: "Privado no registrado",
    sal_total: "Total",
    ipc_nacional: "Nivel general",
    ipc_nucleo: "Núcleo",
    ipc_regulados: "Regulados",
    ipc_estacionales: "Estacionales",
    ripte: "Salario promedio (RIPTE)",
    smvm: "Salario mínimo",
    haber_minimo: "Jubilación mínima (sin bono)",
  };
  var reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var graficos = [];
  var estado = { inflacion: "mensual", rubros: "acumulado", base: null };

  function leerJSON(id) {
    var nodo = document.getElementById(id);
    return nodo ? JSON.parse(nodo.textContent) : null;
  }

  function numero(v, dec) {
    if (v === null || v === undefined || isNaN(v)) return "–";
    return new Intl.NumberFormat("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: dec }).format(v);
  }

  function etiquetaMes(aaaamm) {
    return MESES[parseInt(aaaamm.slice(5, 7), 10) - 1] + "-" + aaaamm.slice(0, 4);
  }

  function colores() {
    var css = getComputedStyle(document.documentElement);
    var v = function (n) { return css.getPropertyValue(n).trim(); };
    return {
      series: [v("--serie-1"), v("--serie-2"), v("--serie-3"), v("--serie-4")],
      texto: v("--texto"),
      texto2: v("--texto-2"),
      texto3: v("--texto-3"),
      grilla: v("--grilla"),
      eje: v("--eje"),
      superficie: v("--superficie"),
      borde: v("--borde"),
    };
  }

  function angosto(el) {
    return el.clientWidth < 560;
  }

  function base(el, c, opciones) {
    var chico = angosto(el);
    return Object.assign(
      {
        animation: !reducido,
        textStyle: { fontFamily: getComputedStyle(document.body).fontFamily, color: c.texto2 },
        grid: { left: 8, right: chico ? 12 : 24, top: chico ? 64 : 48, bottom: 8, containLabel: true },
        legend: {
          top: 0, left: 0, icon: "roundRect", itemWidth: 14, itemHeight: 4, itemGap: chico ? 10 : 18,
          textStyle: { color: c.texto2, fontSize: chico ? 12 : 13 },
        },
        tooltip: {
          trigger: "axis",
          confine: true,
          backgroundColor: c.superficie,
          borderColor: c.borde,
          textStyle: { color: c.texto, fontSize: 13 },
          axisPointer: { type: "line", lineStyle: { color: c.eje } },
        },
      },
      opciones
    );
  }

  function ejeMeses(fechas, c, el) {
    return {
      type: "category",
      data: fechas,
      boundaryGap: false,
      axisLine: { lineStyle: { color: c.eje } },
      axisTick: { show: false },
      axisLabel: {
        color: c.texto3,
        // Una etiqueta por año (en enero); en pantallas angostas, años pares.
        interval: function (i, v) {
          return v.slice(5, 7) === "01" && (!angosto(el) || parseInt(v.slice(0, 4), 10) % 2 === 0);
        },
        formatter: function (v) { return v.slice(0, 4); },
      },
    };
  }

  function ejeValor(c, formato, extra) {
    return Object.assign(
      {
        type: "value",
        splitLine: { lineStyle: { color: c.grilla } },
        axisLabel: { color: c.texto3, formatter: formato },
      },
      extra || {}
    );
  }

  function tooltipLineas(dec, sufijo, prefijo) {
    return function (items) {
      var filas = items
        .filter(function (i) { return i.value !== null && i.value !== undefined; })
        .map(function (i) {
          return i.marker + " " + i.seriesName + ": <strong>" + (prefijo || "") + numero(i.value, dec) + sufijo + "</strong>";
        });
      return "<strong>" + etiquetaMes(items[0].axisValue) + "</strong><br>" + filas.join("<br>");
    };
  }

  function linea(nombre, datos, color, extra) {
    return Object.assign(
      {
        name: nombre, type: "line", data: datos, showSymbol: false, symbolSize: 8,
        lineStyle: { width: 2, color: color }, itemStyle: { color: color }, connectNulls: false,
        emphasis: { focus: "series" },
      },
      extra || {}
    );
  }

  function referencia(valor, texto, c) {
    return {
      silent: true, symbol: "none",
      lineStyle: { color: c.texto3, type: "dashed", width: 1 },
      label: { formatter: texto, color: c.texto3, position: "insideEndTop" },
      data: [{ yAxis: valor }],
    };
  }

  // Salario real con otro mes base: recorta la serie desde ese mes y lo lleva a 100.
  // Mirar desde un punto de partida distinto puede dar vuelta la conclusión.
  function rebasar(g, mesBase) {
    var i0 = mesBase ? g.fechas.indexOf(mesBase) : 0;
    if (i0 < 0) i0 = 0;
    var series = {};
    Object.keys(g.series).forEach(function (id) {
      var base = g.series[id][i0];
      series[id] = g.series[id].slice(i0).map(function (v) {
        return v === null || !base ? null : (v / base) * 100;
      });
    });
    return { fechas: g.fechas.slice(i0), series: series };
  }

  function lecturaBase(datos) {
    var nodo = document.getElementById("lectura-base");
    if (!nodo) return;
    var g = rebasar(datos.graficos.salario_real, estado.base);
    var ultimo = g.fechas.length - 1;
    // Cada sector se lee en su último mes con dato (el no registrado termina antes).
    var partes = ["sal_privado", "sal_publico", "sal_no_registrado"].map(function (id) {
      var i = ultimo;
      while (i > 0 && g.series[id][i] === null) i--;
      var v = g.series[id][i] - 100;
      var hasta = i === ultimo ? "" : " (a " + etiquetaMes(g.fechas[i]) + ")";
      return NOMBRES[id].toLowerCase() + " " + (v > 0 ? "+" : "") + numero(v, 1).replace("-", "−") + "\u00a0%" + hasta;
    });
    var texto = "Entre " + etiquetaMes(g.fechas[0]) + " y " + etiquetaMes(g.fechas[ultimo]) + ": " + partes.join(", ") + ".";
    // Guion no separable en los meses, como en el resto del sitio.
    nodo.textContent = texto.replace(/\b([a-z]{3})-(\d{4})\b/g, "$1\u2011$2");
    return texto;
  }

  // ------------------------------------------------------------------ gráficos

  var constructores = {
    salario_real: function (el, d, c) {
      var g = rebasar(d.graficos.salario_real, estado.base);
      var orden = ["sal_privado", "sal_publico", "sal_no_registrado", "sal_total"];
      var series = orden.map(function (id, i) {
        var esTotal = id === "sal_total";
        return linea(NOMBRES[id], g.series[id], esTotal ? c.texto : c.series[i], {
          lineStyle: { width: esTotal ? 2.5 : 2, color: esTotal ? c.texto : c.series[i], type: esTotal ? "dashed" : "solid" },
          markLine: i === 0 ? referencia(100, etiquetaMes(g.fechas[0]) + " = 100", c) : undefined,
        });
      });
      return base(el, c, {
        tooltip: Object.assign(base(el, c, {}).tooltip, { formatter: tooltipLineas(1, "") }),
        xAxis: ejeMeses(g.fechas, c, el),
        yAxis: ejeValor(c, function (v) { return numero(v, 0); }, { scale: true }),
        series: series,
      });
    },

    inflacion: function (el, d, c) {
      var g = d.graficos.inflacion;
      var mensual = estado.inflacion === "mensual";
      var serie = mensual
        ? { name: "Inflación mensual", type: "bar", data: g.series.mensual, barMaxWidth: 10,
            itemStyle: { color: c.series[0], borderRadius: [2, 2, 0, 0] } }
        : linea("Inflación interanual", g.series.interanual, c.series[0], { areaStyle: { opacity: 0.08 } });
      var eje = ejeMeses(g.fechas, c, el);
      eje.boundaryGap = mensual;
      return base(el, c, {
        legend: { show: false },
        grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
        tooltip: Object.assign(base(el, c, {}).tooltip, {
          formatter: tooltipLineas(mensual ? 1 : 1, "\u00a0%"),
          axisPointer: { type: mensual ? "shadow" : "line" },
        }),
        xAxis: eje,
        yAxis: ejeValor(c, function (v) { return numero(v, 0) + "\u00a0%"; }),
        series: [serie],
      });
    },

    categorias: function (el, d, c) {
      var g = d.graficos.categorias;
      var inicio = g.series.ipc_nacional.findIndex(function (v) { return v !== null; });
      var orden = ["ipc_nucleo", "ipc_regulados", "ipc_estacionales", "ipc_nacional"];
      return base(el, c, {
        tooltip: Object.assign(base(el, c, {}).tooltip, { formatter: tooltipLineas(1, "\u00a0%") }),
        xAxis: ejeMeses(g.fechas.slice(inicio), c, el),
        yAxis: ejeValor(c, function (v) { return numero(v, 0) + "\u00a0%"; }),
        series: orden.map(function (id, i) {
          var general = id === "ipc_nacional";
          return linea(NOMBRES[id], g.series[id].slice(inicio), general ? c.texto : c.series[i], {
            lineStyle: { width: general ? 2.5 : 2, color: general ? c.texto : c.series[i], type: general ? "dashed" : "solid" },
          });
        }),
      });
    },

    rubros: function (el, d, c) {
      var filas = d.consultas["05_rubros_ranking"].filas.slice();
      var acumulado = estado.rubros === "acumulado";
      var campo = acumulado ? "veces" : "ultimo_anio_pct";
      filas.sort(function (a, b) { return a[campo] - b[campo]; });
      var nacional = d.consultas["07_regiones"].filas.filter(function (f) { return f.region === "nacional"; })[0];
      var general = acumulado ? 1 + nacional.acumulado_desde_dic2016_pct / 100 : nacional.interanual_pct;
      var fmt = function (v) { return acumulado ? "×" + numero(v, 1) : numero(v, 1) + "\u00a0%"; };
      var chico = angosto(el);
      return base(el, c, {
        legend: { show: false },
        grid: { left: 8, right: chico ? 52 : 64, top: 32, bottom: 8, containLabel: true },
        tooltip: {
          trigger: "item", confine: true, backgroundColor: c.superficie, borderColor: c.borde,
          textStyle: { color: c.texto },
          formatter: function (p) { return p.name + "<br><strong>" + fmt(p.value) + "</strong>"; },
        },
        xAxis: ejeValor(c, function (v) { return acumulado ? "×" + numero(v, 0) : numero(v, 0) + "\u00a0%"; }, {
          axisLabel: { show: !chico, color: c.texto3, formatter: function (v) { return acumulado ? "×" + numero(v, 0) : numero(v, 0) + "\u00a0%"; } },
        }),
        yAxis: {
          type: "category",
          data: filas.map(function (f) { return f.rubro; }),
          axisTick: { show: false },
          axisLine: { lineStyle: { color: c.eje } },
          axisLabel: {
            color: c.texto2, width: chico ? 120 : 260, overflow: "break", lineHeight: 14, fontSize: chico ? 11 : 12,
          },
        },
        series: [{
          type: "bar", data: filas.map(function (f) { return f[campo]; }), barMaxWidth: 22,
          itemStyle: { color: c.series[0], borderRadius: [0, 4, 4, 0] },
          // Fondo en las etiquetas y la línea de referencia por debajo: así no se pisan.
          label: {
            show: true, position: "right", color: c.texto2, backgroundColor: c.superficie, padding: [1, 3],
            formatter: function (p) { return fmt(p.value); },
          },
          markLine: {
            z: 1, silent: true, symbol: "none", lineStyle: { color: c.texto, type: "dashed" },
            label: { formatter: "General " + fmt(general), color: c.texto2, position: "end" },
            data: [{ xAxis: general }],
          },
        }],
      });
    },

    poder_compra: function (el, d, c) {
      var g = d.graficos.poder_compra;
      var orden = ["ripte", "smvm", "haber_minimo"];
      return base(el, c, {
        tooltip: Object.assign(base(el, c, {}).tooltip, { formatter: tooltipLineas(2, "\u00a0CBT") }),
        xAxis: ejeMeses(g.fechas, c, el),
        yAxis: ejeValor(c, function (v) { return numero(v, 0); }, { min: 0 }),
        series: orden.map(function (id, i) {
          return linea(NOMBRES[id], g.series[id], c.series[i], {
            markLine: i === 0 ? referencia(1, "1 canasta", c) : undefined,
          });
        }),
      });
    },

    regiones: function (el, d, c) {
      var filas = d.consultas["07_regiones"].filas.slice();
      filas.sort(function (a, b) { return a.interanual_pct - b.interanual_pct; });
      return base(el, c, {
        legend: { show: false },
        grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
        tooltip: {
          trigger: "item", confine: true, backgroundColor: c.superficie, borderColor: c.borde, textStyle: { color: c.texto },
          formatter: function (p) { return p.name + "<br><strong>" + numero(p.value, 1) + " %</strong> interanual (" + filas[0].hasta + ")"; },
        },
        xAxis: ejeValor(c, function (v) { return numero(v, 0) + "\u00a0%"; }),
        yAxis: {
          type: "category", axisTick: { show: false }, axisLine: { lineStyle: { color: c.eje } },
          axisLabel: { color: c.texto2 },
          data: filas.map(function (f) { return f.nombre.replace("IPC nivel general – ", ""); }),
        },
        series: [{
          type: "bar", barMaxWidth: 26,
          data: filas.map(function (f) {
            return { value: f.interanual_pct, itemStyle: { color: f.region === "nacional" ? c.texto3 : c.series[0], borderRadius: [0, 4, 4, 0] } };
          }),
          label: { show: true, position: "right", color: c.texto2, formatter: function (p) { return numero(p.value, 1) + "\u00a0%"; } },
        }],
      });
    },

    usd: function (el, d, c) {
      var g = d.graficos.usd;
      var orden = ["ripte", "smvm", "haber_minimo"];
      return base(el, c, {
        tooltip: Object.assign(base(el, c, {}).tooltip, { formatter: tooltipLineas(0, "", "US$\u00a0") }),
        xAxis: ejeMeses(g.fechas, c, el),
        yAxis: ejeValor(c, function (v) { return "US$ " + numero(v, 0); }, { min: 0 }),
        series: orden.map(function (id, i) { return linea(NOMBRES[id], g.series[id], c.series[i]); }),
      });
    },
  };

  // ------------------------------------------------------------------ montaje

  function dibujar(datos) {
    var c = colores();
    graficos.forEach(function (g) { g.chart.dispose(); });
    graficos = [];
    document.querySelectorAll("[data-grafico]").forEach(function (el) {
      var tipo = el.getAttribute("data-grafico");
      if (!constructores[tipo]) return;
      var cargando = el.querySelector(".grafico__cargando");
      if (cargando) cargando.remove();
      var chart = window.echarts.init(el, null, { renderer: "svg" });
      chart.setOption(constructores[tipo](el, datos, c));
      graficos.push({ chart: chart, el: el, tipo: tipo });
    });
  }

  function iniciar() {
    var datos = { graficos: leerJSON("datos-graficos"), consultas: leerJSON("datos-consultas") || {} };
    if (!datos.graficos) return;
    if (!window.echarts) {
      document.querySelectorAll(".grafico__cargando").forEach(function (p) {
        p.textContent = "No se pudo cargar la librería de gráficos. Los datos están en la tabla.";
      });
      return;
    }
    dibujar(datos);

    var selectorBase = document.getElementById("base-salario");
    if (selectorBase) {
      estado.base = selectorBase.value;
      selectorBase.addEventListener("change", function () {
        estado.base = selectorBase.value;
        var lectura = lecturaBase(datos);
        var c = colores();
        graficos.forEach(function (g) {
          if (g.tipo !== "salario_real") return;
          g.chart.setOption(constructores.salario_real(g.el, datos, c), true);
          g.el.setAttribute("aria-label", "Salario real por sector, " + etiquetaMes(estado.base) + " = 100. " + lectura);
        });
      });
    }

    document.querySelectorAll("[data-control]").forEach(function (boton) {
      boton.addEventListener("click", function () {
        var control = boton.getAttribute("data-control");
        estado[control] = boton.getAttribute("data-valor");
        document.querySelectorAll('[data-control="' + control + '"]').forEach(function (b) {
          b.setAttribute("aria-pressed", b === boton ? "true" : "false");
        });
        var c = colores();
        graficos.forEach(function (g) {
          if (g.tipo !== control) return;
          g.chart.setOption(constructores[g.tipo](g.el, datos, c), true);
          // El texto alternativo describe lo que muestra el gráfico ahora.
          if (boton.hasAttribute("data-aria")) g.el.setAttribute("aria-label", boton.getAttribute("data-aria"));
        });
      });
    });

    var ancho = window.innerWidth;
    var espera;
    window.addEventListener("resize", function () {
      clearTimeout(espera);
      espera = setTimeout(function () {
        var cruzo = (ancho < 560) !== (window.innerWidth < 560);
        ancho = window.innerWidth;
        if (cruzo) dibujar(datos);
        else graficos.forEach(function (g) { g.chart.resize(); });
      }, 150);
    });
    document.addEventListener("tema-cambiado", function () { dibujar(datos); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
