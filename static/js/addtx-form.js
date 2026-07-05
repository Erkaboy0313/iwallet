/* Alpine component for the Add / Edit transaction form.
 *
 * The amount input is bound to `amountDisplay` (formatted "680 000"); the
 * raw digit string lives in `amount` and is what gets submitted. Server
 * strips the space in `clean_amount`.
 */
(function () {
    if (window.__addTxFormRegistered) return;
    window.__addTxFormRegistered = true;
    function register() {
        window.Alpine.data("addTxForm", function (initialType, initialAmount) {
            var money = window.iwMoney;
            return {
                type: initialType || "expense",
                amount: money.fromServer(initialAmount),
                picker: null,
                pickerLabel: "",
                pickerEmoji: "",
                get amountDisplay() {
                    return money.format(this.amount);
                },
                set amountDisplay(value) {
                    this.amount = money.strip(value);
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
