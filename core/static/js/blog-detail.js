/* Blog detail page interactions: like, bookmark, comments, shares, TOC */
(function () {
  "use strict";

  var doc = document;

  /* ---------- TOC scrollspy ------------------------------------ */
  function initToc() {
    var links = Array.prototype.slice.call(doc.querySelectorAll(".toc-list a[href^='#']"));
    if (!links.length) return;
    var headings = links
      .map(function (l) { return doc.getElementById(l.getAttribute("href").slice(1)); })
      .filter(Boolean);

    function onScroll() {
      var current = null;
      var scrollPos = window.scrollY + 110;
      headings.forEach(function (h) {
        if (h.offsetTop <= scrollPos) current = h.id;
      });
      links.forEach(function (l) {
        l.classList.toggle("active", l.getAttribute("href").slice(1) === current);
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  /* ---------- Engagement helpers ------------------------------- */
  function bindEngagement(selector, urlAttr, key, activeClass) {
    doc.querySelectorAll(selector).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var url = btn.getAttribute("data-url") || btn.getAttribute(urlAttr);
        var countEl = doc.querySelector(btn.getAttribute("data-count-target"));
        var wasActive = btn.classList.contains(activeClass);
        btn.disabled = true;
        window.Inkwell.post(url).then(function (data) {
          btn.disabled = false;
          if (data.error) return;
          var nowActive = data[key];
          btn.classList.toggle(activeClass, nowActive);
          btn.setAttribute("aria-pressed", nowActive ? "true" : "false");
          if (countEl && data.count !== undefined) {
            countEl.textContent = Number(data.count).toLocaleString();
          }
          btn.querySelector("[data-icon]") && (
            btn.querySelector("[data-icon]").className =
              "fa-" + (nowActive ? "solid" : "regular") + " fa-heart"
          );
        });
      });
    });
  }

  function initEngagement() {
    bindEngagement("[data-like-btn]", "data-url", "liked", "active");
    bindEngagement("[data-bookmark-btn]", "data-url", "saved", "active");
    bindEngagement("[data-comment-like]", "data-url", "liked", "liked");
  }

  /* ---------- Share buttons ------------------------------------ */
  function initShare() {
    var url = window.location.href;
    var title = doc.title;
    var handlers = {
      "data-share-x": "https://twitter.com/intent/tweet?url=" + encodeURIComponent(url) + "&text=" + encodeURIComponent(title),
      "data-share-facebook": "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url),
      "data-share-linkedin": "https://www.linkedin.com/sharing/share-offsite/?url=" + encodeURIComponent(url),
      "data-share-whatsapp": "https://wa.me/?text=" + encodeURIComponent(title + " " + url)
    };
    Object.keys(handlers).forEach(function (attr) {
      doc.querySelectorAll("[" + attr + "]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          window.open(handlers[attr], "_blank", "noopener,width=600,height=520");
        });
      });
    });
    doc.querySelectorAll("[data-copy-link]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (navigator.clipboard) navigator.clipboard.writeText(url);
        btn.classList.add("active");
        btn.innerHTML = '<i class="fa-solid fa-check"></i>';
        setTimeout(function () { btn.classList.remove("active"); btn.innerHTML = '<i class="fa-solid fa-link"></i>'; }, 1800);
      });
    });
  }

  /* ---------- Comment reply forms ------------------------------ */
  function initReplies() {
    doc.querySelectorAll("[data-reply-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var wrap = doc.getElementById(btn.getAttribute("data-reply-toggle"));
        if (wrap) wrap.classList.toggle("open");
        if (wrap && wrap.classList.contains("open")) {
          var input = wrap.querySelector("input[name='parent_id']");
          if (input) input.value = btn.getAttribute("data-comment-id");
        }
      });
    });
  }

  /* ---------- Reading progress -------------------------------- */
  function initReadingProgress() {
    var bar = doc.querySelector("[data-reading-progress]");
    if (!bar) return;
    var fill = bar.querySelector("span");
    function onScroll() {
      var total = doc.documentElement.scrollHeight - window.innerHeight;
      var pct = total > 0 ? (window.scrollY / total) * 100 : 0;
      fill.style.width = pct + "%";
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  initToc();
  initEngagement();
  initShare();
  initReplies();
  initReadingProgress();
})();
