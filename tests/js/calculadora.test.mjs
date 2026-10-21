// Los mismos casos que tests/test_calculadora.py, contra la calculadora del sitio.
// Necesita build/datos/indices.json: correr antes `python -m inflationarg all`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { calcular, ErrorCalculadora, leerMonto, redondear } from "../../site/static/js/calculadora.js";

const raiz = new URL("../../", import.meta.url);
const casos = JSON.parse(await readFile(new URL("tests/casos_calculadora.json", raiz), "utf8"));
const indices = JSON.parse(await readFile(new URL("build/datos/indices.json", raiz), "utf8"));

// Python usa snake_case en la entrada; JS, camelCase.
const entradaJs = ({ sueldo_actual, ...resto }) =>
  sueldo_actual === undefined ? resto : { ...resto, sueldoActual: sueldo_actual };

function comparar(obtenido, esperado, tolerancia, ruta = "$") {
  if (esperado !== null && typeof esperado === "object") {
    assert.deepEqual(Object.keys(obtenido).sort(), Object.keys(esperado).sort(), ruta);
    for (const k of Object.keys(esperado)) comparar(obtenido[k], esperado[k], tolerancia, `${ruta}.${k}`);
  } else if (typeof esperado === "number") {
    assert.ok(Math.abs(obtenido - esperado) <= tolerancia, `${ruta}: ${obtenido} != ${esperado}`);
  } else {
    assert.equal(obtenido, esperado, ruta);
  }
}

for (const caso of casos.casos) {
  test(`caso: ${caso.descripcion}`, () => {
    comparar(calcular(indices, entradaJs(caso.entrada)), caso.esperado, casos.tolerancia);
  });
}

for (const caso of casos.errores) {
  test(`error: ${caso.descripcion}`, () => {
    assert.throws(
      () => calcular(indices, entradaJs(caso.entrada)),
      (e) => e instanceof ErrorCalculadora && e.codigo === caso.error
    );
  });
}

test("redondeo half-up igual que Python", () => {
  assert.equal(redondear(2.5, 0), 3);
  assert.equal(redondear(-2.5, 0), -2);
  assert.equal(redondear(1.005 * 1000, 0), 1005);
});

test("leerMonto entiende formato es-AR", () => {
  assert.equal(leerMonto("1.234.567,89"), 1234567.89);
  assert.equal(leerMonto("$ 850.000"), 850000);
  assert.equal(leerMonto("850000"), 850000);
  assert.equal(leerMonto("1234.5"), 1234.5);
  assert.equal(leerMonto(""), null);
  assert.ok(Number.isNaN(leerMonto("abc")));
});
