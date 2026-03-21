odoo.define("metro_pos_whatsapp_integration.ReceiptScreen", function (require) {
    "use strict";

    const ReceiptScreen = require("point_of_sale.ReceiptScreen");
    const { Printer } = require('point_of_sale.Printer');
    const Registries = require("point_of_sale.Registries");
    const { useListener } = require("web.custom_hooks");

    const WPReceiptScreen = (ReceiptScreen) =>
        class extends ReceiptScreen {
            constructor() {
                super(...arguments);
                useListener("click-send_wp_direct", this.on_click_send_wp_direct);
            }

            async getInvoiceLink(orderId) {
                try {
                    const url = await this.rpc({
                        model: "pos.order",
                        method: "action_get_pos_invoice_link",
                        args: [orderId],
                    });
                    console.log("Invoice link fetched:", url);
                    return url;
                } catch (error) {
                    console.error("Error fetching invoice link:", error);
                    return null;
                }
            }

            async getWhatsAppMethod() {
                try {
                    const method = await this.rpc({
                        model: "pos.config",
                        method: "search_read",
                        fields: ["whatsapp_method"],
                        domain: [["id", "=", this.env.pos.config.id]],
                    });
                    return method.length > 0 ? method[0].whatsapp_method : "web"; // Default to web
                } catch (error) {
                    console.error("Error fetching WhatsApp method:", error);
                    return "web";
                }
            }

            async getAssistroConfig() {
                try {
                    const access_token = await this.rpc({
                        model: "ir.config_parameter",
                        method: "get_param",
                        args: ["assistro.access_token"],
                    });

                    const api_url = await this.rpc({
                        model: "ir.config_parameter",
                        method: "get_param",
                        args: ["assistro.url"],
                    });

                    console.log("Assistro Config:", { access_token, api_url });

                    return {
                        access_token: access_token || null,
                        api_url: api_url || null,
                    };
                } catch (error) {
                    console.error("Error fetching Assistro config:", error);
                    return { access_token: null, api_url: null };
                }
            }

            _correctPhoneNumber(number) {
                if (!number) return null;

                // Remove non-numeric characters
                number = number.replace(/\D/g, "");

                // ✅ Handle Indian Numbers (Remove '+91', '91', '919' prefixes)
                if (number.startsWith("91") && number.length > 10) {
                    number = number.substring(2);
                } else if (number.startsWith("919") && number.length > 10) {
                    number = number.substring(3);
                }

                // ✅ If it's exactly 10 digits, assume it's an Indian number
                if (number.length === 10) {
                    number = "91" + number;
                }

                // ✅ Handle Singapore Numbers (8 digits → Prefix with '65')
                if (number.length === 8) {
                    number = "65" + number;
                } else if (number.startsWith("65") && number.length === 10) {
                    // Already a valid Singapore number
                    return number;
                }

                // ✅ Handle other international numbers
                if (number.length >= 10) {
                    return number;
                }

                console.warn("Invalid mobile number after correction:", number);
                return null; // Invalid number
            }


            async on_click_send_wp_direct(event) {
                console.log("Send WhatsApp button clicked...");
            
                const partner = this.currentOrder.get_client();
            
                if (!partner || !partner.mobile) {
                    this.showPopup("ErrorPopup", {
                        title: "Missing Mobile Number",
                        body: "Customer has no mobile number.",
                    });
                    console.warn("Customer mobile number missing.");
                    return;
                }
            
                let mobile = this._correctPhoneNumber(partner.mobile);
                if (!mobile) {
                    this.showPopup("ErrorPopup", {
                        title: "Invalid Mobile Number",
                        body: "Please enter a valid number.",
                    });
                    return;
                }
            
                console.log("Preparing WhatsApp message for:", mobile);
            
                // Show QUICK SUCCESS MESSAGE Immediately
                // this.showPopup("ConfirmPopup", {
                //     title: "Processing",
                //     body: `Your message is being sent to ${partner.name}.`,
                //     confirmText: "OK",
                // });
            
                const receipt = this.currentOrder.export_for_printing();
                const invoiceLink = await this.getInvoiceLink(this.currentOrder.id);
            
                let message = `Dear ${partner.name},\n\nHere is your order *${receipt.name}* amounting to *${receipt.total_with_tax.toFixed(2)}* ${receipt.currency.symbol} from ${receipt.company.name}.\n\nOrder details:\n`;
            
                receipt.orderlines.forEach(orderline => {
                    message += `\n*${orderline.product_name}*\n*Qty:* ${orderline.quantity}\n*Price:* ${orderline.price} ${receipt.currency.symbol}\n`;
                });
            
                message += `\n________________________\n*Total Amount:* ${receipt.total_with_tax.toFixed(2)} ${receipt.currency.symbol}`;
                
                if (invoiceLink) {
                    message += `\n\nYour invoice: ${invoiceLink}`;
                }
                
                message += `\n\n\n*Powered by Metro Accounting System*`;
            
                const printer = new Printer(null, this.env.pos);
                const receiptString = this.orderReceipt.comp.el.outerHTML;
                const ticketImage = await printer.htmlToImg(receiptString);
                
                const encodedMessage = encodeURIComponent(message);
                const whatsappMethod = await this.getWhatsAppMethod();
            
                if (whatsappMethod === "web") {
                    const whatsappURL = `https://web.whatsapp.com/send?phone=${mobile}&text=${encodedMessage}`;
                    window.open(whatsappURL, "_blank");
            
                } else if (whatsappMethod === "assistro") {
                    const { access_token, api_url } = await this.getAssistroConfig();
            
                    if (!access_token || !api_url) {
                        this.showPopup("ErrorPopup", {
                            title: "API Configuration Missing",
                            body: "Assistro API configuration is missing. Please check settings.",
                        });
                        console.warn("Missing Assistro API configuration.");
                        return;
                    }
            
                    const whatsapp_api_url = `${api_url}/api/v1/wapushplus/singlePass/message`;
            
                    const payload = {
                        "msgs": [
                            {
                                "number": mobile,
                                "message": message,
                                "media": [
                                    {
                                        "media_base64": ticketImage, 
                                        "file_name": "receipt.png"
                                    }
                                ]
                            }
                        ]
                    };
                    // ✅ **Show Success Message Immediately**
                    this.showPopup("ConfirmPopup", {
                        title: "Message Sent Successfully",
                        body: `Your message has been sent to ${partner.name}.`,
                        confirmText: "OK",
                    });
            
                    // Send API request asynchronously (User doesn't wait)
                    fetch(whatsapp_api_url, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${access_token}`,
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(payload)
                    })
                    .then(response => response.json())
                    .then(responseData => {
                        if (responseData.success) {
                            console.log("WhatsApp Message sent successfully:", responseData);
                        } else {
                            this.showPopup("ErrorPopup", {
                                title: "Message Failed",
                                body: `Failed to send WhatsApp message. Response: ${JSON.stringify(responseData)}`,
                            });
                            console.warn("Assistro API failed response:", responseData);
                        }
                    })
                    .catch(error => {
                        console.error("Error sending WhatsApp message:", error);
                        this.showPopup("ErrorPopup", {
                            title: "Error",
                            body: "An error occurred while sending the WhatsApp message.",
                        });
                    });
                }
            }
        };

    Registries.Component.extend(ReceiptScreen, WPReceiptScreen);

    return ReceiptScreen;
});



