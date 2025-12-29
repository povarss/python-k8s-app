<template>
    <div>
        <!-- Використовуємо SVG для максимальної якості -->
        <svg ref="barcode" class="!w-full" style="width: 100% !important;"></svg>
    </div>
</template>

<script>
import JsBarcode from "jsbarcode";

export default {
    name: "ProductBarcodePrinterBarcode",

    props: {
        product: {type: Object, required: true},
    },

    methods: {
        /**
         * Генерує штрихкод на основі продукту
         * @returns {string} Значення штрихкоду
         */
        getBarcode() {
            // Якщо є готовий штрихкод - використовуємо його
            if (this.product.barcode) {
                return this.product.barcode;
            }

            // Генеруємо штрихкод на основі ID продукту
            const maxDigits = 10;
            const numberString = String(this.product.id);

            // Додаємо ведучі нулі для досягнення потрібної довжини
            const paddingLength = maxDigits - numberString.length;
            const paddedString = '0'.repeat(paddingLength) + numberString;

            // Формуємо фінальний штрихкод з префіксом залежно від модифікації
            return (this.product.modification_name ? '11-' : '10-') + paddedString;
        },

        /**
         * Генерує штрихкод на canvas з високою роздільною здатністю
         * Альтернативний метод якщо потрібен саме canvas
         */
        renderHighQualityCanvas() {
            const canvas = this.$refs.barcode;
            const ctx = canvas.getContext('2d');
            
            // Отримуємо роздільну здатність екрану
            const dpr = window.devicePixelRatio || 1;
            const rect = canvas.getBoundingClientRect();
            
            // Встановлюємо реальний розмір canvas з урахуванням DPR
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            
            // Масштабуємо контекст для правильного відображення
            ctx.scale(dpr, dpr);
            
            // Встановлюємо CSS розміри
            canvas.style.width = rect.width + 'px';
            canvas.style.height = rect.height + 'px';
            
            // Генеруємо штрихкод з підвищеною роздільною здатністю
            JsBarcode(canvas, this.getBarcode(), {
                format: "CODE128", // Вказуємо формат явно для кращої сумісності
                width: 2,
                height: 60, // Збільшуємо висоту для кращої читабельності
                margin: 0,
                marginLeft: 10,
                marginRight: 10,
                fontSize: 20,
                textMargin: 0,
                displayValue: true, // Показуємо текст під штрихкодом
            });
        }
    },

    mounted() {
        // Використовуємо SVG для максимальної якості (рекомендовано)
        JsBarcode(this.$refs.barcode, this.getBarcode(), {
            format: "CODE128", // Явно вказуємо формат для кращої сумісності
            width: 2, // Товщина ліній
            height: 60, // Висота штрихкоду (збільшено для кращої читабельності)
            margin: 0,
            marginLeft: 10,
            marginRight: 10,
            fontSize: 20, // Розмір шрифту для тексту
            textMargin: 0, // Відступ тексту від штрихкоду
            displayValue: true, // Показуємо текст значення під штрихкодом
            background: "#ffffff", // Білий фон для кращого контрасту
            lineColor: "#000000", // Чорний колір ліній
            // Додаткові параметри для покращення якості
            valid: function(valid) {
                // Перевірка валідності штрихкоду
                if (!valid) {
                    console.warn('Штрихкод може бути невалідним');
                }
            }
        });

        // Якщо потрібен саме canvas, розкоментуйте наступний рядок:
        // this.renderHighQualityCanvas();
    },

    watch: {
        // Оновлюємо штрихкод при зміні продукту
        'product': {
            handler() {
                this.$nextTick(() => {
                    JsBarcode(this.$refs.barcode, this.getBarcode(), {
                        format: "CODE128",
                        width: 2,
                        height: 60,
                        margin: 0,
                        marginLeft: 10,
                        marginRight: 10,
                        fontSize: 20,
                        textMargin: 0,
                        displayValue: true,
                        background: "#ffffff",
                        lineColor: "#000000",
                    });
                });
            },
            deep: true // Відстежуємо глибокі зміни в об'єкті продукту
        }
    }
}
</script>

<style scoped>
/* Додаткові стилі для забезпечення якості відображення */
svg {
    max-width: 100%;
    height: auto;
    display: block;
}
</style>
