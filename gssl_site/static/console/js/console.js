/* ==========================================================================
   Green Spark — website console
   Progressive enhancement only. Every screen works with JavaScript off: the
   filters have an Apply button, ordering falls back to the sort field on the
   form, and nothing here is required to save a change.
   No inline scripts and no inline styles: the console runs under the site's
   own Content-Security-Policy.
   ========================================================================== */
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }

  /* ---- Filters submit themselves ---------------------------------------- */

  function wireAutoSubmit() {
    document.querySelectorAll("select[data-autosubmit]").forEach(function (select) {
      select.addEventListener("change", function () {
        var form = select.closest("form");
        if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
      });
    });
  }

  /* ---- Warn before leaving an edited form ------------------------------- */

  function wireUnsavedGuard() {
    document.querySelectorAll("form[data-guard]").forEach(function (form) {
      var dirty = false;
      var saving = false;

      form.addEventListener("input", function () { dirty = true; });
      form.addEventListener("change", function () { dirty = true; });
      form.addEventListener("submit", function () { saving = true; });

      window.addEventListener("beforeunload", function (event) {
        if (!dirty || saving) return undefined;
        event.preventDefault();
        // Browsers show their own wording; the value only has to be set.
        event.returnValue = "";
        return "";
      });
    });
  }

  /* ---- Drag to reorder --------------------------------------------------- */

  function rowsOf(body) {
    return Array.prototype.slice.call(body.querySelectorAll("tr[data-pk]"));
  }

  function saveOrder(body) {
    var url = body.getAttribute("data-reorder-url");
    if (!url) return;
    var ids = rowsOf(body).map(function (row) { return row.getAttribute("data-pk"); });

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "XMLHttpRequest"
      },
      body: JSON.stringify({ ids: ids }),
      credentials: "same-origin"
    }).then(function (response) {
      body.classList.toggle("is-saved", response.ok);
      if (!response.ok) window.location.reload();
    }).catch(function () {
      window.location.reload();
    });
  }

  function wireReorder() {
    document.querySelectorAll("tbody[data-sortable]").forEach(function (body) {
      var dragging = null;

      rowsOf(body).forEach(function (row) {
        var handle = row.querySelector(".cns-drag");
        if (!handle) return;

        // Only the handle starts a drag, so selecting text in a cell still works.
        handle.setAttribute("draggable", "true");

        handle.addEventListener("dragstart", function (event) {
          dragging = row;
          row.classList.add("is-dragging");
          if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = "move";
            event.dataTransfer.setData("text/plain", row.getAttribute("data-pk"));
          }
        });

        handle.addEventListener("dragend", function () {
          row.classList.remove("is-dragging");
          if (dragging) saveOrder(body);
          dragging = null;
        });

        row.addEventListener("dragover", function (event) {
          if (!dragging || dragging === row) return;
          event.preventDefault();
          var box = row.getBoundingClientRect();
          var below = event.clientY > box.top + box.height / 2;
          body.insertBefore(dragging, below ? row.nextSibling : row);
        });
      });
    });
  }

  /* ---- Go ---------------------------------------------------------------- */

  function start() {
    wireAutoSubmit();
    wireUnsavedGuard();
    wireReorder();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
