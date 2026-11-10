// Vanilla JavaScript for Simple Store (progressive enhancement: the site works without it).
document.addEventListener("DOMContentLoaded", () => {
  // Mobile navigation toggle
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  // Dismiss flash messages (success messages auto-hide after 5 s)
  document.querySelectorAll(".message").forEach((msg) => {
    const close = msg.querySelector(".message-close");
    if (close) close.addEventListener("click", () => msg.remove());
    if (msg.classList.contains("success")) setTimeout(() => msg.remove(), 5000);
  });

  // Quantity stepper on the product page
  document.querySelectorAll(".qty").forEach((box) => {
    const input = box.querySelector("input");
    box.querySelectorAll(".qty-btn").forEach((btn) =>
      btn.addEventListener("click", () => {
        const min = parseInt(input.min || "1", 10);
        const max = parseInt(input.max || "999", 10);
        const next = (parseInt(input.value, 10) || min) + parseInt(btn.dataset.step, 10);
        input.value = Math.min(Math.max(next, min), max);
      })
    );
  });

  // Confirm before destructive actions (e.g. removing a cart item)
  document.querySelectorAll("form[data-confirm]").forEach((form) =>
    form.addEventListener("submit", (e) => {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    })
  );

  // Auto-submit filter dropdowns
  document.querySelectorAll("select[data-autosubmit]").forEach((sel) =>
    sel.addEventListener("change", () => sel.form.submit())
  );

  // Prevent double-clicking the "Place order" button
  document.querySelectorAll("button[data-once]").forEach((btn) =>
    btn.form.addEventListener("submit", () => {
      setTimeout(() => { btn.disabled = true; btn.textContent = "Placing order..."; }, 0);
    })
  );
});
