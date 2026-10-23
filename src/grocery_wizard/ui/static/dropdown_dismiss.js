/*
 * Dropdown dismissal for iOS / touch devices (#440).
 *
 * Why Streamlit menus stay open on an iPhone:
 *   - st.popover closes from a `click` listener on `document`. iOS Safari does not
 *     dispatch `click` for taps on non-interactive content, so tapping blank space
 *     or text never reaches that listener.
 *   - st.selectbox / st.multiselect (React Aria comboboxes) close only when the
 *     input blurs. iOS does not blur the focused input when you tap non-focusable
 *     content, so the menu (and the keyboard) stay up.
 *
 * Touch `pointerup` / `touchend` events do fire everywhere. This script runs once in
 * the parent document and, on a short tap outside an open menu:
 *   - blurs (and Escapes) every open combobox the tap did not land in, and
 *   - replays an outside `click` on <body> so every open popover closes itself.
 * It also blurs a single-select after an option is tapped, to dismiss the keyboard.
 *
 * Confirm the build has it: `window.__gwDropdownDismiss` is "v2" and
 * <html data-gw-dropdown-dismiss="v2"> is set.
 */
(function () {
  var VERSION = "v2";
  if (window.__gwDropdownDismiss === VERSION) {
    return;
  }
  window.__gwDropdownDismiss = VERSION;
  document.documentElement.setAttribute("data-gw-dropdown-dismiss", VERSION);

  var TAP_SLOP_PX = 10;
  var COMBOBOX_WIDGETS =
    '[data-testid="stSelectbox"], [data-testid="stMultiSelect"], ' +
    '[data-testid="stSelectboxVirtualDropdown"], [data-testid="stMultiSelectDropdown"]';
  var POPOVER_PARTS =
    '[data-testid="stPopover"], [data-testid="stPopoverBody"], [data-st-overlay-root="true"], ' +
    COMBOBOX_WIDGETS;

  var start = null;

  function openComboboxes() {
    return Array.prototype.slice.call(
      document.querySelectorAll('[role="combobox"][aria-expanded="true"]')
    );
  }

  function hasOpenPopover() {
    return Boolean(
      document.querySelector('[data-testid="stPopoverButton"][aria-expanded="true"]')
    );
  }

  function closest(target, selector) {
    return target && target.closest ? target.closest(selector) : null;
  }

  function closeCombobox(combobox) {
    combobox.blur();
    setTimeout(function () {
      if (combobox.getAttribute("aria-expanded") === "true") {
        combobox.dispatchEvent(
          new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true })
        );
      }
    }, 100);
  }

  function dismissOutside(target) {
    if (!closest(target, COMBOBOX_WIDGETS)) {
      openComboboxes().forEach(closeCombobox);
    }
    if (hasOpenPopover() && !closest(target, POPOVER_PARTS)) {
      document.body.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    }
  }

  function point(event) {
    var source = event.changedTouches ? event.changedTouches[0] : event;
    return source ? { x: source.clientX, y: source.clientY } : null;
  }

  function onStart(event) {
    if (event.pointerType === "mouse") {
      return;
    }
    start = point(event);
  }

  function onEnd(event) {
    if (event.pointerType === "mouse" || !start) {
      return;
    }
    var end = point(event);
    var moved = end && Math.hypot(end.x - start.x, end.y - start.y) > TAP_SLOP_PX;
    start = null;
    if (!moved) {
      dismissOutside(event.target);
    }
  }

  ["pointerdown", "touchstart"].forEach(function (name) {
    document.addEventListener(name, onStart, { capture: true, passive: true });
  });
  ["pointerup", "touchend"].forEach(function (name) {
    document.addEventListener(name, onEnd, { capture: true, passive: true });
  });
  ["pointercancel", "touchcancel"].forEach(function (name) {
    document.addEventListener(
      name,
      function () {
        start = null;
      },
      { capture: true, passive: true }
    );
  });

  document.addEventListener(
    "pointerup",
    function (event) {
      if (event.pointerType !== "touch" || !closest(event.target, '[role="option"]')) {
        return;
      }
      if (!closest(event.target, '[data-testid="stSelectboxVirtualDropdown"]')) {
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
