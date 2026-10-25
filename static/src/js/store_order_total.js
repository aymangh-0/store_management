import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class StoreOrderTotal extends Interaction {
    static selector = ".o_store_new_order";

    dynamicContent = {
    ".o_store_qty": { "t-on-input": this.updateTotal },
    };

    updateTotal() {
        let total = 0;
        for (const line of this.el.querySelectorAll(".o_store_line")) {
            const input = line.querySelector(".o_store_qty");
            const price = parseFloat(line.dataset.price);
            const qty = parseInt(input.value) || 0;
            const available = parseInt(input.max);

            input.classList.toggle("is-invalid", qty > available);
            total += price * qty;
        }
        this.el.querySelector(".o_store_total").textContent = total.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}


registry
    .category("public.interactions")
    .add("store_management.store_order_total", StoreOrderTotal);