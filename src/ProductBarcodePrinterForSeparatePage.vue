<template>
    <template v-for="product in printerData.products" :key="product.id">
        <!-- Одна колонка -->
        <template v-if="columns === 1">
            <div
                v-for="num in (product.count || 1)"
                :key="`${product.id}-${num}`"
                class="price-print-barcode"
                :style="barcodePaddingStyle"
            >
                <div v-if="showCertBlock" class="cert-block"><img :src="certImage" alt="cert"></div>
                <div
                    v-if="!product.hide_product_modification_names"
                    class="p-name-ellipsis"
                    :style="nameStyle"
                >
                    {{ product.product_name }}
                    <span v-if="product.modification_name">
                        ({{ product.modification_name }})
                    </span>

                    <template v-if="product.art">
                        ({{ $t("message.art") }}: {{ product.art }})
                    </template>
                </div>

                <div
                    v-if="product.characteristics.length || product.show_brand"
                    class="price-print-characteristics"
                    :style="characteristicsStyle"
                >
                    <span v-if="product.show_brand">
                        {{ $t("message.brand") }}:
                        {{ product.brand_name }}
                        <span v-if="product.characteristics.length">,</span>
                    </span>

                    <span
                        v-for="(c, i) in product.characteristics"
                        :key="i"
                    >
                        {{ c.characteristicName }}: {{ c.characteristicValue }}
                        <span v-if="i < product.characteristics.length - 1">, </span>
                    </span>
                </div>

                <div v-if="printerData.printPrices" class="price" :style="priceStyle">
                    {{ $t("message.price") }}:
                    <b>{{ product.price ? $formatCurrency(product.price) : "" }}</b>
                </div>

                <product-barcode-printer-barcode :product="product" :barcodeSettings="barcodeSettings" />
            </div>
        </template>

        <!-- Дві колонки -->
        <template v-else-if="columns === 2">
            <div
                class="price-print-barcode"
                v-for="num in (product.count || 1)"
                :key="`${product.id}-${num}`"
                :style="barcodePaddingStyle"
            >
                <div class="price-print-row">
                    <!-- ПЕРШИЙ СТОВПЧИК -->
                    <div class="price-print-left">
                        <div
                            v-if="!product.hide_product_modification_names"
                            class="p-name-ellipsis"
                            :style="nameStyle"
                        >
                            {{ product.product_name }}
                            <span v-if="product.modification_name">
                                ({{ product.modification_name }})
                            </span>

                            <template v-if="product.art">
                                ({{ $t("message.art") }}: {{ product.art }})
                            </template>
                        </div>

                        <div
                            v-if="product.characteristics.length || product.show_brand"
                            class="flex flex-wrap justify-start price-print-characteristics"
                            :style="characteristicsStyle"
                        >
                            <span v-if="product.show_brand" class="mr-1">
                                {{ $t("message.brand") }}:
                                {{
                                    product.brand_name +
                                    (product.characteristics.length ? "," : "")
                                }}
                            </span>

                            <template v-if="product.characteristics.length">
                                <span
                                    v-for="(characteristic, key) in product.characteristics"
                                    :key="key"
                                    class="mr-1"
                                >
                                    {{
                                        characteristic.characteristicName +
                                        ": " +
                                        characteristic.characteristicValue +
                                        (key < product.characteristics.length - 1
                                            ? ", "
                                            : "")
                                    }}
                                </span>
                            </template>
                        </div>

                        <div v-if="printerData.printPrices" :style="priceStyle">
                            {{ $t("message.price") }}:
                            <b>
                                {{ product.price ? $formatCurrency(product.price) : "" }}
                            </b>
                        </div>
                    </div>

                    <!-- ДРУГИЙ СТОВПЧИК -->
                    <div class="price-print-right">
                        <product-barcode-printer-barcode :product="product" :barcodeSettings="barcodeSettings" />

                        <div v-if="showCertBlock" class="cert-block"><img src="/images/UKR_sert.png" alt="cert"></div>
                    </div>
                </div>
            </div>
        </template>
    </template>
</template>

<script>
import ProductBarcodePrinterBarcode from "./ProductBarcodePrinterBarcode.vue";

export default {
    name: "ProductBarcodePrinterForSeparatePage",
    components: { ProductBarcodePrinterBarcode },

    props: {
        printerData: { type: Object, required: true },
        // Кількість колонок для друку (1 або 2)
        columns: {
            type: Number,
            default: 2,
            validator: (value) => [1, 2].includes(value),
        },
        // Розміри шрифтів (буде використано пізніше)
        fontSize: {
            type: Object,
            default: () => ({
                name: 10, // розмір шрифту для назви продукту
                characteristics: 9, // розмір шрифту для характеристик
                price: 12, // розмір шрифту для ціни
            }),
        },
        // Розміри сторінки
        pageSize: {
            type: Object,
            default: () => ({
                width: "100mm",
                height: "25mm",
                topMargin: "0mm", // Верхній margin для контенту
                rightMargin: "0mm", // Правий margin для контенту
                bottomMargin: "0mm", // Нижній margin для контенту
                leftMargin: "0mm", // Лівий margin для контенту
                topPadding: "0mm", // Верхній відступ для контенту
                rightPadding: "0mm", // Правий відступ для контенту
                bottomPadding: "0mm", // Нижній відступ для контенту
                leftPadding: "0mm", // Лівий відступ для контенту
            }),
        },
        // Показувати блок сертифікатів
        showCertBlock: {
            type: Boolean,
            default: true,
        },
        // Налаштування штрих-коду
        barcodeSettings: {
            type: Object,
            default: () => ({
                format: "CODE128",
                width: 1.5,
                height: 20,
                fontSize: 12,
                displayValue: true,
                margin: 0,
            }),
        },
        certImage: {
            type: String,
            default: '/images/UKR_sert.png',
            required: false,
        },
    },

    computed: {
        // Стилі для назви продукту
        nameStyle() {
            return {
                fontSize: `${this.fontSize.name}px`,
            };
        },
        // Стилі для характеристик
        characteristicsStyle() {
            return {
                fontSize: `${this.fontSize.characteristics}px`,
            };
        },
        // Стилі для ціни
        priceStyle() {
            return {
                fontSize: `${this.fontSize.price}px`,
            };
        },
        // Відступи безпосередньо для контенту (щоб обійти налаштування браузера)
        barcodePaddingStyle() {
            // Відступи застосовуються через CSS в applyPageStyles
            // Тут залишаємо порожній об'єкт, щоб не конфліктувати
            return {};
        },
    },

    created() {
        // Застосовуємо стилі сторінки одразу при створенні компонента
        this.applyPageStyles();
    },

    mounted() {
        // Застосовуємо стилі перед друком
        this.applyPageStyles();

        // Намагаємося вплинути на налаштування друку через beforeprint event
        const handleBeforePrint = () => {
            this.applyPageStyles();
            // Застосовуємо стилі безпосередньо до body та html
            document.body.style.margin = '0';
            document.body.style.padding = '0';
            document.documentElement.style.margin = '0';
            document.documentElement.style.padding = '0';
        };

        window.addEventListener('beforeprint', handleBeforePrint);

        setTimeout(() => {
            // Додатково застосовуємо стилі перед викликом print
            this.applyPageStyles();
            window.print();
            window.removeEventListener('beforeprint', handleBeforePrint);
            this.$root.unSetPrint();
        }, 500);
    },

    methods: {
        // Застосування стилів сторінки через CSS змінні
        applyPageStyles() {
            // Видаляємо попередній стиль, якщо він існує
            const existingStyle = document.getElementById('dynamic-page-styles');
            if (existingStyle) {
                existingStyle.remove();
            }

            const style = document.createElement('style');
            style.id = 'dynamic-page-styles';
            // Агресивні стилі з використанням CSS змінних та calc() для компенсації
            style.textContent = `
                :root {
                    --page-width: ${this.pageSize.width};
                    --page-height: ${this.pageSize.height};
                    --top-margin: ${this.pageSize.topMargin || '0mm'};
                    --right-margin: ${this.pageSize.rightMargin || '0mm'};
                    --bottom-margin: ${this.pageSize.bottomMargin || '0mm'};
                    --left-margin: ${this.pageSize.leftMargin || '0mm'};
                    --top-padding: ${this.pageSize.topPadding || '0mm'};
                    --right-padding: ${this.pageSize.rightPadding || '0mm'};
                    --bottom-padding: ${this.pageSize.bottomPadding || '0mm'};
                    --left-padding: ${this.pageSize.leftPadding || '0mm'};
                }
                @page {
                    size: var(--page-width) var(--page-height) !important;
                    margin: 0 !important;
                }
                @media print {
                    *:not(.price-print-barcode) {
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                    html, body {
                        margin: 0 !important;
                        padding: 0 !important;
                        width: auto !important;
                        height: auto !important;
                        min-height: 100% !important;
                        overflow: visible !important;
                    }
                    .show-on-print,
                    .print-product-barcodes {
                        width: 100% !important;
                        height: auto !important;
                        min-height: 100% !important;
                        overflow: visible !important;
                        display: block !important;
                        visibility: visible !important;
                    }
                    .price-print-barcode {
                        margin-top: var(--top-margin) !important;
                        margin-right: var(--right-margin) !important;
                        margin-bottom: var(--bottom-margin) !important;
                        margin-left: var(--left-margin) !important;
                        padding-top: var(--top-padding) !important;
                        padding-right: var(--right-padding) !important;
                        padding-bottom: var(--bottom-padding) !important;
                        padding-left: var(--left-padding) !important;
                        /* Використовуємо auto для ширини, щоб врахувати відступи */
                        width: auto !important; 
                        /* Розраховуємо висоту з урахуванням вертикальних відступів і віднімаємо 1px для запобігання переповнення */
                        height: calc(var(--page-height) - var(--top-margin) - var(--bottom-margin) - 1px) !important;
                        max-height: calc(var(--page-height) - var(--top-margin) - var(--bottom-margin) - 1px) !important;
                        min-height: calc(var(--page-height) - var(--top-margin) - var(--bottom-margin) - 1px) !important;
                        box-sizing: border-box !important;
                        position: relative !important;
                        display: flex !important;
                        flex-direction: column !important;
                        break-after: page !important;
                        page-break-after: always !important;
                        break-inside: avoid !important;
                        overflow: hidden !important;
                        visibility: visible !important;
                    }
                    .price-print-barcode:last-child {
                        break-after: auto !important;
                        page-break-after: auto !important;
                    }
                }
            `;
            document.head.appendChild(style);

            // Також застосовуємо стилі безпосередньо до body через JavaScript
            document.body.style.setProperty('margin', '0', 'important');
            document.body.style.setProperty('padding', '0', 'important');
            document.documentElement.style.setProperty('margin', '0', 'important');
            document.documentElement.style.setProperty('padding', '0', 'important');
        },
    },
};
</script>

<style>
/* ================== PRINT STYLES ================== */
@media print {
    /* Стилі @page застосовуються динамічно через JavaScript в методі applyPageStyles() */
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        color: #000;
    }

    .price-print-barcode {
        break-after: page !important;
        break-inside: avoid !important;
        width: 100%;
        box-sizing: border-box;
        display: flex !important;
        flex-direction: column !important;
        min-height: 0;
    }

    .price-print-barcode:last-child {
        break-after: auto !important;
    }

    .p-name-ellipsis {
        font-size: 10px;
        line-height: 1.1;
        margin-bottom: 2px;
        overflow: hidden;
        display: -webkit-box;
        max-height: 2.2em;
        -webkit-line-clamp: 2;
        line-clamp: 2;
        -webkit-box-orient: vertical;
    }

    .price-print-characteristics {
        font-size: 9px;
        line-height: 1.1;
        margin-bottom: 2px;
    }

    .price {
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 2px;
    }

    .barcode-wrap {
        margin-top: 2px;
        flex-shrink: 0;
    }

    /* Стилі для друку в дві колонки */
    .price-print-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        align-items: center;
        gap: 3mm;
    }

    .price-print-left {
        padding-right: 3mm;
        padding-top: var(--top-padding, 0mm);
        padding-bottom: var(--bottom-padding, 0mm);
        padding-left: var(--left-padding, 0mm);
        display: flex;
        flex-direction: column;
    }

    .price-print-right {
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
}
</style>
