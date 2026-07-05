/* Alpine component for the Add / Edit transaction form.
 *
 * Tracks the active type pill + the amount (with thousand-separator display)
 * + the category-picker state. The amount input shows "680 000" but stores
 * the raw digit string; the server strips spaces on clean_amount so the
 * submitted value round-trips fine.
 */
(function () {
    if (window.__addTxFormRegistered) return;
    window.__addTxFormRegistered = true;
    function formatDigits(raw) {
        if (!raw) return "";
        // Numeric locale that groups by 3 with a space separator.
        var n = Number(raw);
        if (!isFinite(n)) return raw;
        return n.toLocaleString("en-US").replace(/,/g, " ");
    }
    function register() {
        window.Alpine.data("addTxForm", function (initialType, initialAmount) {
            var initialRaw = (initialAmount || "").toString().split(".")[0].replace(/[^\d]/g, "");
            return {
                type: initialType || "expense",
                // Raw digit string — this is what actually gets submitted.
                amount: initialRaw,
                picker: null,
                pickerLabel: "",
                pickerEmoji: "",
                // Getter/setter so the visible input shows "680 000" while
                // the source of truth stays as the raw digit string.
                get amountDisplay() {
                    return formatDigits(this.amount);
                },
                set amountDisplay(value) {
                    this.amount = (value || "").replace(/[^\d]/g, "");
                },
            };
        });
    }
    if (window.Alpine) {
        register();
    } else {
        document.addEventListener("alpine:init", register);
    }
})();
