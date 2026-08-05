/* Blog list page: sorting, filters and URL syncing */
(function () {
  "use strict";

  var doc = document;

  function sync() {
    var params = new URLSearchParams(window.location.search);
    doc.querySelectorAll("[data-filter]").forEach(function (el) {
      var name = el.getAttribute("data-filter");
      if (el.value) params.set(name, el.value);
      else params.delete(name);
    });
    // Keep an existing query string for category/tag routes intact.
    window.location.search = params.toString();
  }

  doc.querySelectorAll("[data-filter]").forEach(function (el) {
    el.addEventListener("change", sync);
  });

  // Animate cards in a staggered manner as they load.
  var cards = doc.querySelectorAll(".stagger > *");
  if (cards.length && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.05 });
    cards.forEach(function (c) { io.observe(c); });
  }
})();
