<template>
    <div class="barcode-container">
        <!-- Використовуємо SVG замість Canvas для векторної якості -->
        <svg ref="barcode" class="barcode-svg"></svg>
    </div>
</template>

<script>
import JsBarcode from "jsbarcode";

export default {
    name: "ProductBarcodePrinterBarcode",

    props: {
        product: {type: Object, required: true},
    },

    watch: {
        // Реактивне оновлення штрихкоду при зміні продукту
        product: {
            handler() {
                this.$nextTick(() => {
                    this.renderBarcode();
                });
            },
            deep: true
        }
    },

    methods: {
        /**
         * Генерує штрихкод на основі продукту
         * @returns {string} Значення штрихкоду
         */
        getBarcode() {
            // Якщо є готовий штрихкод, використовуємо його
            if (this.product.barcode) {
                return this.product.barcode;
            }

            // Генеруємо штрихкод на основі ID продукту
            const maxDigits = 10;
            const numberString = String(this.product.id);

            // Додаємо ведучі нулі для форматування
            const paddingLength = maxDigits - numberString.length;
            const paddedString = '0'.repeat(paddingLength) + numberString;

            // Формат: 11- для модифікацій, 10- для звичайних продуктів
            return (this.product.modification_name ? '11-' : '10-') + paddedString;
        },

        /**
         * Відображає штрихкод з оптимальними налаштуваннями якості
         */
        renderBarcode() {
            const barcodeValue = this.getBarcode();
            
            if (!barcodeValue || !this.$refs.barcode) {
                return;
            }

            // Очищаємо попередній вміст
            this.$refs.barcode.innerHTML = '';

            // Налаштування для максимальної якості
            JsBarcode(this.$refs.barcode, barcodeValue, {
                // Формат: CODE128 підтримує більшість символів і має хорошу якість
                format: "CODE128",
                
                // Ширина ліній - важливо для чіткості
                // 2-3 пікселі зазвичай оптимально для друку
                width: 2,
                
                // Висота штрихкоду
                height: 60,
                
                // Відступи для кращого сканування
                margin: 10,
                marginLeft: 15,
                marginRight: 15,
                
                // Налаштування тексту
                displayValue: true, // Показувати значення штрихкоду
                fontSize: 16,
                textMargin: 4,
                textPosition: "bottom", // Текст знизу
                textAlign: "center",
                
                // Кольори для контрасту (чорний на білому)
                background: "#ffffff",
                lineColor: "#000000",
                
                // Додаткові налаштування для якості
                valid: function(valid) {
                    if (!valid) {
                        console.warn('Невірний формат штрихкоду:', barcodeValue);
                    }
                }
            });
        }
    },

    mounted() {
        // Відображаємо штрихкод після монтування компонента
        this.$nextTick(() => {
            this.renderBarcode();
        });
    }
}
</script>

<style scoped>
.barcode-container {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    padding: 10px;
    background-color: #ffffff;
}

.barcode-svg {
    width: 100%;
    max-width: 100%;
    height: auto;
    /* Забезпечуємо чіткість на високопіксельних екранах */
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
}

/* Для друку - забезпечуємо максимальну якість */
@media print {
    .barcode-container {
        page-break-inside: avoid;
    }
    
    .barcode-svg {
        width: 100%;
        height: auto;
    }
}
</style>
