/* Live search suggestions with debounce */
(function () {
  "use strict";

  var doc = document;
  var input = doc.querySelector("[data-search-input]");
  if (!input) return;

  var box = doc.querySelector(input.getAttribute("data-target")) || doc.querySelector(".suggestions");
  var debounce = null;

  function render(results) {
    if (!box) return;
    if (!results.length) {
      box.innerHTML = '<div class="suggestion-empty">No matching results. Try a different term.</div>';
      box.classList.add("open");
      return;
    }
    var types = { post: "Articles", tag: "Tags", author: "Authors", category: "Categories" };
    var html = "";
    var seenType = null;
    results.forEach(function (r) {
      if (r.type !== seenType) {
        seenType = r.type;
        html += '<div class="suggestion-type">' + (types[r.type] || "Results") + "</div>";
      }
      var icon = r.type === "post" && r.image
        ? '<img src="' + r.image + '" alt="" loading="lazy"/>'
        : '<i class="fa-solid ' + (r.type === "post" ? "fa-newspaper" : r.type === "tag" ? "fa-hashtag" : r.type === "author" ? "fa-user" : "fa-folder") + '"></i>';
      html +=
        '<button type="button" class="suggestion-item" onclick="location.href=\'' + r.url + '\'">' +
        '<span class="s-ico">' + icon + "</span>" +
        '<span class="s-txt"><span class="s-title">' + r.title + "</span>" +
        (r.subtitle ? '<span class="s-sub">' + r.subtitle + "</span>" : "") + "</span></button>";
    });
    box.innerHTML = html;
    box.classList.add("open");
  }

  input.addEventListener("input", function () {
    var q = input.value.trim();
    clearTimeout(debounce);
    if (!q) { box.classList.remove("open"); return; }
    debounce = setTimeout(function () {
      fetch("/search/suggest/?q=" + encodeURIComponent(q), { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (r) { return r.json(); })
        .then(function (data) { render(data.results || []); })
        .catch(function () {});
    }, 240);
  });

  doc.addEventListener("click", function (e) {
    if (!e.target.closest(".search-box")) box.classList.remove("open");
  });
  doc.addEventListener("keydown", function (e) { if (e.key === "Escape") box.classList.remove("open"); });
})();
