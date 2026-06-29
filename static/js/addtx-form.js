/* Alpine component for the Add / Edit transaction form.
 *
 * Tracks the active type pill + the (text) amount + the category-picker
 * state. The amount field is a plain native input now — the OS keyboard
 * handles digit entry, no custom keypad.
 */
(function () {
    if (window.__addTxFormRegistered) return;
    window.__addTxFormRegistered = true;
    function register() {
        window.Alpine.data("addTxForm", function (initialType, initialAmount) {
            return {
                type: initialType || "expense",
                // Edit form may pass "1500.00" — keep only the integer portion.
                amount: (initialAmount || "").toString().split(".")[0].replace(/[^\d]/g, ""),
                picker: null,
                pickerLabel: "",
                pickerEmoji: "",
            };
        });
    }
    if (window.Alpine) {
        register();
    } else {
        document.addEventListener("alpine:init", register);
    }
})();
