// Tema claro/oscuro y menú móvil. El tema elegido se guarda en localStorage (si se puede).
(function () {
  "use strict";
  var raiz = document.documentElement;
  var oscuroSistema = window.matchMedia("(prefers-color-scheme: dark)");

  function temaActual() {
    var t = raiz.getAttribute("data-theme");
    if (t === "light" || t === "dark") return t;
    return oscuroSistema.matches ? "dark" : "light";
  }

  function actualizarBoton(boton) {
    var oscuro = temaActual() === "dark";
    boton.setAttribute("aria-label", oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
  }

  function avisar() {
    document.dispatchEvent(new CustomEvent("tema-cambiado", { detail: { tema: temaActual() } }));
  }

  document.addEventListener("DOMContentLoaded", function () {
    var botonTema = document.querySelector(".tema-boton");
    if (botonTema) {
      actualizarBoton(botonTema);
      botonTema.addEventListener("click", function () {
        var nuevo = temaActual() === "dark" ? "light" : "dark";
        raiz.setAttribute("data-theme", nuevo);
        try {
          localStorage.setItem("tema", nuevo);
        } catch (e) {
          /* sin almacenamiento: el tema dura hasta recargar */
        }
        actualizarBoton(botonTema);
        avisar();
      });
      oscuroSistema.addEventListener("change", function () {
        actualizarBoton(botonTema);
        avisar();
      });
    }

    var botonMenu = document.querySelector(".menu-boton");
    var nav = document.getElementById("navegacion");
    if (botonMenu && nav) {
      botonMenu.addEventListener("click", function () {
        var abierto = nav.classList.toggle("abierta");
        botonMenu.setAttribute("aria-expanded", abierto ? "true" : "false");
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && nav.classList.contains("abierta")) {
          nav.classList.remove("abierta");
          botonMenu.setAttribute("aria-expanded", "false");
          botonMenu.focus();
        }
      });
    }
  });
})();
