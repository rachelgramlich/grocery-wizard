/*
 * Dropdown dismissal for touch devices (#440).
 *
 * Streamlit select / multiselect menus are non-modal popovers that close only when
 * the combobox input loses focus. On phones, tapping non-interactive content often
 * leaves the input focused (and the soft keyboard up), so the menu never closes.
 * This runs once in the parent document and blurs the open combobox when:
 *   - the user presses anywhere outside the combobox and its menu, or
 *   - the user picks an option from a single-select menu (dismisses the keyboard).
 */
(function () {
  if (window.__gwDropdownDismiss) {
    return;
  }
  window.__gwDropdownDismiss = true;

  var INSIDE_SELECTOR = [
    '[data-testid="stSelectbox"]',
    '[data-testid="stMultiSelect"]',
    '[data-testid="stSelectboxVirtualDropdown"]',
    '[data-testid="stMultiSelectDropdown"]',
  ].join(",");

  function openCombobox() {
    var active = document.activeElement;
    if (
      active &&
      active.getAttribute &&
      active.getAttribute("role") === "combobox" &&
      active.getAttribute("aria-expanded") === "true"
    ) {
      return active;
    }
    return null;
  }

  function isInside(target) {
    return Boolean(target && target.closest && target.closest(INSIDE_SELECTOR));
  }

  document.addEventListener(
    "pointerdown",
    function (event) {
      var combobox = openCombobox();
      if (combobox && !isInside(event.target)) {
        combobox.blur();
      }
    },
    true
  );

  document.addEventListener(
    "pointerup",
    function (event) {
      if (event.pointerType !== "touch" || !event.target.closest) {
        return;
      }
      var menu = event.target.closest('[data-testid="stSelectboxVirtualDropdown"]');
      if (!menu || !event.target.closest('[role="option"]')) {
        return;
      }
      setTimeout(function () {
        var active = document.activeElement;
        if (active && active.getAttribute && active.getAttribute("role") === "combobox") {
          active.blur();
        }
      }, 50);
    },
    true
  );
})();
