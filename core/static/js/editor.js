/* Editor: markdown preview, autosave, image drag & drop, SEO counters */
(function () {
  "use strict";

  var doc = document;
  var contentEl = doc.getElementById("id_content");
  var titleEl = doc.getElementById("id_title");
  var previewEl = doc.getElementById("editor-preview");
  var statusEl = doc.querySelector(".editor-status");
  var autosaveUrl = doc.body.getAttribute("data-autosave-url");
  var saveTimer = null;
  var lastSaved = "";

  /* ---------- Live preview (simple client-side markdown) ------- */
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function inlineMd(s) {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }

  function renderPreview() {
    if (!previewEl) return;
    var text = contentEl ? contentEl.value : "";
    var lines = text.split("\n");
    var html = [];
    var inCode = false;
    var codeBuf = [];
    var listType = null;

    lines.forEach(function (line) {
      var fenced = line.match(/^```(\w*)\s*$/);
      if (fenced) {
        if (inCode) {
          html.push("<pre><code>" + codeBuf.join("\n") + "</code></pre>");
          codeBuf = [];
        } else {
          html.push("<pre><code>");
        }
        inCode = !inCode;
        return;
      }
      if (inCode) { codeBuf.push(escapeHtml(line)); return; }

      if (listType && !/^\s*[-*]\s/.test(line) && !/^\s*\d+\.\s/.test(line)) {
        html.push("</" + listType + ">"); listType = null;
      }
      var h = line.match(/^(#{1,4})\s+(.*)/);
      if (h) {
        var level = h[1].length;
        html.push("<h" + level + ">" + inlineMd(h[2]) + "</h" + level + ">");
      } else if (/^\s*[-*]\s/.test(line)) {
        if (listType !== "ul") { html.push("<ul>"); listType = "ul"; }
        html.push("<li>" + inlineMd(line.replace(/^\s*[-*]\s/, "")) + "</li>");
      } else if (/^\s*\d+\.\s/.test(line)) {
        if (listType !== "ol") { html.push("<ol>"); listType = "ol"; }
        html.push("<li>" + inlineMd(line.replace(/^\s*\d+\.\s/, "")) + "</li>");
      } else if (/^>\s/.test(line)) {
        html.push("<blockquote>" + inlineMd(line.replace(/^>\s?/, "")) + "</blockquote>");
      } else if (/^!\[([^\]]*)\]\(([^)\s]+)\)/.test(line)) {
        html.push('<img src="' + RegExp.$2 + '" alt="' + RegExp.$1 + '" />');
      } else if (!line.trim()) {
        html.push("");
      } else {
        html.push("<p>" + inlineMd(line) + "</p>");
      }
    });
    if (inCode && codeBuf.length) html.push("<pre><code>" + codeBuf.join("\n") + "</code></pre>");
    if (listType) html.push("</" + listType + ">");
    previewEl.innerHTML = html.join("");
  }

  /* ---------- Autosave draft ----------------------------------- */
  function setStatus(state) {
    if (!statusEl) return;
    statusEl.className = "editor-status " + state;
    var label = statusEl.querySelector("[data-label]");
    if (label) label.textContent = state === "saving" ? "Saving…" : state === "saved" ? "Saved just now" : "Draft auto-save active";
  }

  function autosave() {
    if (!autosaveUrl) return;
    var payload = {
      title: titleEl ? titleEl.value : "",
      content: contentEl ? contentEl.value : "",
      excerpt: doc.getElementById("id_excerpt") ? doc.getElementById("id_excerpt").value : ""
    };
    if (JSON.stringify(payload) === lastSaved) return;
    setStatus("saving");
    window.Inkwell.post(autosaveUrl, payload).then(function (data) {
      if (data.ok) { lastSaved = JSON.stringify(payload); setStatus("saved"); }
    });
  }

  function scheduleAutosave() {
    if (!autosaveUrl) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(autosave, 1400);
  }

  if (contentEl) {
    contentEl.addEventListener("input", function () { renderPreview(); scheduleAutosave(); });
    titleEl && titleEl.addEventListener("input", scheduleAutosave);
    var excerptEl = doc.getElementById("id_excerpt");
    excerptEl && excerptEl.addEventListener("input", scheduleAutosave);
    renderPreview();
  }

  /* ---------- Image upload (drag & drop) ----------------------- */
  var dropzone = doc.getElementById("dropzone");
  var fileInput = doc.getElementById("image-upload-input");

  function uploadFiles(files) {
    if (!files || !files.length) return;
    var form = new FormData();
    form.append("image", files[0]);
    if (dropzone) dropzone.classList.add("uploading");
    fetch("/upload/image/", {
      method: "POST",
      body: form,
      headers: { "X-CSRFToken": window.Inkwell.csrf() }
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.url) {
          var url = data.url;
          if (contentEl) {
            contentEl.value += "\n\n![Uploaded image](" + url + ")\n";
            renderPreview();
            scheduleAutosave();
          }
          if (dropzone) {
            dropzone.innerHTML = '<i class="fa-solid fa-check-circle"></i><p>Uploaded! You can drop another.</p>';
            setTimeout(function () {
              dropzone.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i><p>Drop an image here, or click to browse</p>';
              dropzone.classList.remove("uploading");
            }, 1600);
          }
        } else {
          if (dropzone) dropzone.classList.remove("uploading");
          alert(data.error || "Upload failed.");
        }
      })
      .catch(function () { if (dropzone) dropzone.classList.remove("uploading"); });
  }

  if (dropzone) {
    dropzone.addEventListener("click", function () { fileInput && fileInput.click(); });
    fileInput && fileInput.addEventListener("change", function () { uploadFiles(fileInput.files); });
    ["dragenter", "dragover"].forEach(function (ev) {
      dropzone.addEventListener(ev, function (e) { e.preventDefault(); dropzone.classList.add("dragover"); });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      dropzone.addEventListener(ev, function (e) { e.preventDefault(); dropzone.classList.remove("dragover"); });
    });
    dropzone.addEventListener("drop", function (e) {
      e.preventDefault();
      uploadFiles(e.dataTransfer.files);
    });
  }

  /* ---------- Toolbar buttons ---------------------------------- */
  doc.querySelectorAll("[data-md]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (!contentEl) return;
      var token = btn.getAttribute("data-md");
      var start = contentEl.selectionStart;
      var end = contentEl.selectionEnd;
      var selected = contentEl.value.slice(start, end) || "text";
      var insert = { "**": "**" + selected + "**", "*": "*" + selected + "*", "`": "`" + selected + "`", "#": "# " + selected }.hasOwnProperty(token)
        ? token === "#" ? "# " + selected : token + selected + token
        : token + " " + selected;
      contentEl.value = contentEl.value.slice(0, start) + insert + contentEl.value.slice(end);
      contentEl.focus();
      contentEl.setSelectionRange(start + insert.length, start + insert.length);
      renderPreview();
    });
  });

  /* ---------- SEO character counters --------------------------- */
  doc.querySelectorAll("[data-count-limit]").forEach(function (el) {
    var limit = parseInt(el.getAttribute("data-count-limit"), 10);
    var counter = doc.querySelector(el.getAttribute("data-counter"));
    function update() {
      if (counter) counter.textContent = el.value.length + " / " + limit;
    }
    el.addEventListener("input", update);
    update();
  });
})();
