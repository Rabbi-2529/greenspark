/* ==========================================================================
   Green Spark — console enhancements

   Select2 on dropdowns, DataTables on the lists, CKEditor on the limited-HTML
   fields. All three are progressive: every screen here works with JavaScript
   off, and this file only ever improves what is already on the page. If one
   of the libraries fails to load, the plain control is still there.

   Nothing is configured from an inline <script>: the console runs under the
   site's Content-Security-Policy, so the settings come from data attributes
   the server already wrote.
   ========================================================================== */
(function () {
  "use strict";

  var $ = window.jQuery;

  /* ---- Dropdowns --------------------------------------------------------
     Only where it earns its keep. Select2 on a three-option dropdown is
     slower to use than the browser's own, so it is applied to the long ones. */

  var SELECT2_FROM = 8;

  function enhanceSelects(root) {
    if (!$ || !$.fn || !$.fn.select2) return;
    $(root).find("select[data-enhance='select']").each(function () {
      var el = this;
      if (el.options.length < SELECT2_FROM || el.dataset.select2Done) return;
      el.dataset.select2Done = "1";
      $(el).select2({
        width: "100%",
        dropdownParent: $(el).closest(".cns-field, form"),
        placeholder: el.dataset.placeholder || "",
        allowClear: !el.required
      });
    });
  }

  /* ---- Lists ------------------------------------------------------------
     The table is already rendered by Django and already paged, sorted and
     filtered on the server. DataTables is pointed at the same endpoint the
     markup carries, so it never pulls the whole table into the browser. */

  function enhanceTables() {
    if (!$ || !$.fn || !$.fn.DataTable) return;
    $("table[data-source]").each(function () {
      var table = this;
      if (table.dataset.dtDone) return;
      table.dataset.dtDone = "1";

      var columns = [].map.call(table.tHead.rows[0].cells, function (th) {
        return { orderable: th.dataset.sort !== undefined, data: th.dataset.sort || null };
      });

      $(table).DataTable({
        serverSide: true,
        processing: true,
        searching: false,   /* the list has its own search box and filters */
        lengthChange: false,
        ajax: { url: table.dataset.source, type: "GET" },
        columns: columns,
        language: {
          emptyTable: "Nothing here yet.",
          zeroRecords: "Nothing matches that.",
          info: "_START_–_END_ of _TOTAL_",
          infoEmpty: "0 of 0",
          processing: "Loading…"
        }
      });
    });
  }

  /* ---- Limited-HTML fields ----------------------------------------------
     The toolbar is exactly what apps/content/richtext.py allows: bold,
     italic, a link, and the two kinds of list. A button that produced
     anything else would mean an editor losing work when they pressed save,
     because the validator refuses it by name. */

  function enhanceEditors() {
    var fields = document.querySelectorAll("textarea[data-richtext]");
    if (!fields.length || !window.CKEDITOR5) return;

    var CK = window.CKEDITOR5;
    [].forEach.call(fields, function (area) {
      if (area.dataset.ckDone) return;
      area.dataset.ckDone = "1";

      CK.ClassicEditor.create(area, {
        /* v44 asks every installation to name its licence. */
        licenseKey: "GPL",
        plugins: [
          CK.Essentials, CK.Paragraph, CK.Bold, CK.Italic,
          CK.Link, CK.List
        ],
        toolbar: ["bold", "italic", "|", "link", "|", "bulletedList", "numberedList"],
        link: { addTargetToExternalLinks: true }
      }).catch(function () {
        /* Leave the plain textarea: it saves perfectly well on its own. */
        area.dataset.ckDone = "";
      });
    });
  }

  function start() {
    enhanceSelects(document);
    enhanceTables();
    enhanceEditors();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  /* Inline formsets add rows after load; pick those up too. */
  document.addEventListener("cns:rowadded", function (event) {
    enhanceSelects(event.target || document);
  });
})();
