/* Alpine component for the Add / Edit transaction form.
 *
 * Loaded from both /app/transactions/add/ and /app/transactions/<id>/edit/
 * so the keypad + type radio cards work the same on either page. The
 * registration is guarded so loading the script twice in one page is a
 * no-op.
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
                keypadKeys: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "000", "0", "BACK"],
                pressKey: function (key) {
                    if (key === "BACK") {
                        this.amount = this.amount.slice(0, -1);
                        return;
                    }
                    var next = (this.amount + key).replace(/^0+(?=\d)/, "");
                    if (next.length <= 12) this.amount = next;
                },
                formattedAmount: function () {
                    var s = this.amount || "0";
                    return s.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
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
