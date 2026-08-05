/* Inkwell — global UI interactions (dependency-free) */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;
  var storageKey = "inkwell-theme";

  /* ---------- Theme toggle ------------------------------------ */
  function applyTheme(theme, persist) {
    root.setAttribute("data-theme", theme);
    if (persist !== false) {
      try { localStorage.setItem(storageKey, theme); } catch (e) {}
    }
  }

  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem(storageKey); } catch (e) {}
    var theme = saved || (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    applyTheme(theme, false);
    doc.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.innerHTML = theme === "dark" ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
    });
  }

  doc.addEventListener("click", function (e) {
    var toggle = e.target.closest("[data-theme-toggle]");
    if (!toggle) return;
    var current = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(current);
    toggle.innerHTML = current === "dark" ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
  });

  /* ---------- Navbar scroll state ----------------------------- */
  var nav = doc.querySelector(".navbar");
  function onScroll() {
    if (nav) nav.classList.toggle("scrolled", window.scrollY > 12);
    var topBtn = doc.querySelector(".to-top");
    if (topBtn) topBtn.classList.toggle("show", window.scrollY > 500);
    updateProgress();
  }
  window.addEventListener("scroll", onScroll, { passive: true });

  /* ---------- Reading progress bar ---------------------------- */
  var progressBar = doc.querySelector(".read-progress");
  function updateProgress() {
    if (!progressBar) return;
    var total = doc.body.scrollHeight - window.innerHeight;
    var pct = total > 0 ? (window.scrollY / total) * 100 : 0;
    progressBar.style.width = pct + "%";
  }

  /* ---------- Mobile menu ------------------------------------- */
  var burger = doc.querySelector(".hamburger");
  var mobileMenu = doc.querySelector(".mobile-menu");
  if (burger && mobileMenu) {
    burger.addEventListener("click", function () {
      var open = mobileMenu.classList.toggle("open");
      burger.classList.toggle("open", open);
      doc.body.style.overflow = open ? "hidden" : "";
    });
    mobileMenu.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        mobileMenu.classList.remove("open");
        burger.classList.remove("open");
        doc.body.style.overflow = "";
      });
    });
  }

  /* ---------- User dropdown ----------------------------------- */
  doc.addEventListener("click", function (e) {
    var menu = e.target.closest(".user-menu");
    var dropdown = menu && menu.querySelector(".dropdown");
    if (menu && dropdown) {
      e.stopPropagation();
      var wasOpen = dropdown.classList.contains("open");
      doc.querySelectorAll(".dropdown.open").forEach(function (d) { d.classList.remove("open"); });
      if (!wasOpen) dropdown.classList.add("open");
    } else {
      doc.querySelectorAll(".dropdown.open").forEach(function (d) { d.classList.remove("open"); });
    }
  });

  /* ---------- Scroll to top ------------------------------------ */
  var topBtn = doc.querySelector(".to-top");
  if (topBtn) {
    topBtn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* ---------- Reveal on scroll -------------------------------- */
  function initReveal() {
    var items = doc.querySelectorAll(".reveal");
    if (!items.length) return;
    if (!("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("in-view"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    items.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Animated counters ------------------------------- */
  function initCounters() {
    doc.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseInt(el.getAttribute("data-count"), 10) || 0;
      if (!("IntersectionObserver" in window)) { el.textContent = target.toLocaleString(); return; }
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          io.unobserve(el);
          var duration = 1200;
          var start = null;
          function step(ts) {
            if (!start) start = ts;
            var p = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(target * eased).toLocaleString();
            if (p < 1) requestAnimationFrame(step);
          }
          requestAnimationFrame(step);
        });
      }, { threshold: 0.4 });
      io.observe(el);
    });
  }

  /* ---------- Button ripple ----------------------------------- */
  doc.addEventListener("click", function (e) {
    var btn = e.target.closest(".btn");
    if (!btn) return;
    var rect = btn.getBoundingClientRect();
    var ripple = doc.createElement("span");
    ripple.className = "ripple";
    var size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = size + "px";
    ripple.style.left = e.clientX - rect.left - size / 2 + "px";
    ripple.style.top = e.clientY - rect.top - size / 2 + "px";
    btn.appendChild(ripple);
    setTimeout(function () { ripple.remove(); }, 600);
  });

  /* ---------- Auto-dismiss messages --------------------------- */
  doc.querySelectorAll(".messages .alert").forEach(function (alert) {
    setTimeout(function () {
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-10px)";
      setTimeout(function () { alert.remove(); }, 400);
    }, 4200);
  });

  /* ---------- Lightbox ---------------------------------------- */
  function initLightbox() {
    var box = doc.querySelector(".lightbox");
    if (!box) return;
    var img = box.querySelector("img");
    var close = box.querySelector(".lightbox-close");
    function open(src) { img.src = src; box.classList.add("open"); doc.body.style.overflow = "hidden"; }
    function closeBox() { box.classList.remove("open"); doc.body.style.overflow = ""; }
    close.addEventListener("click", closeBox);
    box.addEventListener("click", function (e) { if (e.target === box) closeBox(); });
    doc.addEventListener("keydown", function (e) { if (e.key === "Escape") closeBox(); });

    doc.querySelectorAll("[data-lightbox]").forEach(function (el) {
      el.addEventListener("click", function (e) {
        e.preventDefault();
        open(el.getAttribute("data-lightbox"));
      });
    });
  }

  /* ---------- Copy code buttons ------------------------------- */
  function initCopyCode() {
    doc.querySelectorAll(".article-prose pre").forEach(function (pre) {
      var btn = doc.createElement("button");
      btn.className = "copy-code-btn";
      btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
      btn.type = "button";
      btn.addEventListener("click", function () {
        var code = pre.querySelector("code");
        var text = code ? code.innerText : pre.innerText;
        if (navigator.clipboard) {
          navigator.clipboard.writeText(text).then(function () {
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
            setTimeout(function () { btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy'; }, 1800);
          });
        }
      });
      pre.appendChild(btn);
    });
  }

  /* ---------- CSRF helper -------------------------------------- */
  function getCookie(name) {
    var match = doc.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : null;
  }
  window.Inkwell = {
    csrf: function () { return getCookie("csrftoken") || ""; },
    post: function (url, body) {
      return fetch(url, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken") || "",
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin",
        body: body ? JSON.stringify(body) : undefined
      }).then(function (r) { return r.json().catch(function () { return {}; }); });
    }
  };

  /* ---------- Init --------------------------------------------- */
  initTheme();
  initReveal();
  initCounters();
  initLightbox();
  initCopyCode();
  onScroll();
  doc.addEventListener("DOMContentLoaded", function () {
    var loader = doc.querySelector(".page-loader");
    if (loader) setTimeout(function () { loader.classList.add("hidden"); }, 250);
  });
  window.addEventListener("load", onScroll);
})();
