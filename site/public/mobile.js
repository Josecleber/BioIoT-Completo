"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "mobile-menu-button";
    button.textContent = "\u2630";
    button.setAttribute("aria-label", "Abrir menu");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", "bioiot-mobile-nav");

    sidebar.id = "bioiot-mobile-nav";

    const overlay = document.createElement("div");
    overlay.className = "mobile-menu-overlay";

    document.body.append(button, overlay);

    function fecharMenu() {
        document.body.classList.remove("mobile-menu-open");
        button.setAttribute("aria-expanded", "false");
        button.setAttribute("aria-label", "Abrir menu");
    }

    button.addEventListener("click", () => {
        const aberto = document.body.classList.toggle("mobile-menu-open");
        button.setAttribute("aria-expanded", String(aberto));
        button.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
    });

    overlay.addEventListener("click", fecharMenu);

    sidebar.addEventListener("click", (event) => {
        if (event.target.closest(".nav-item")) {
            fecharMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") fecharMenu();
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 768) fecharMenu();
    });
});
