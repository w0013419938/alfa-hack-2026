/**
 * Тема интерфейса. Все цвета, шрифты и скругления — здесь, чтобы стиль меняли в одном месте.
 *
 * Значения сняты из Figma команды («кейс-школа-альфа», слайды презентации):
 *   акцент #EF3124, текст #222, салатовый #8FEE52, фон #F4F5F7, шрифт Golos Text,
 *   карточки со скруглением 32px, плашки 16–24px, заголовки с межбуквенным интервалом −2%.
 * Фиолетовый в макете есть только на 3D-картинках, поэтому взят из ТЗ (#9B5CFF).
 */
import { createTheme, type MantineColorsTuple } from "@mantine/core";

// Базовые цвета — их используют компоненты напрямую (например, фон страницы и вторичный текст)
export const COLORS = {
  accent: "#EF3124", // главный акцент: основная кнопка, крупные суммы, текущий шаг
  accentSoft: "rgba(239, 49, 36, 0.05)", // выделенная строка таблицы, мягкий фон
  positive: "#8FEE52", // «всё хорошо»: одобрено, этап пройден
  positiveText: "#2F6B0C", // текст на светлом салатовом фоне
  attention: "#9B5CFF", // внимание: ждём действия, предупреждение
  text: "#222222",
  textSecondary: "#6B6B6B",
  page: "#F4F5F7",
  card: "#FFFFFF",
  border: "#E6E7EB",
};

export const RADIUS = {
  card: 32, // большие карточки
  block: 24, // плашки и вложенные блоки
  control: 16, // кнопки, поля, бейджи
};

// Палитры для Mantine (10 оттенков от светлого к тёмному; индекс 6 — основной)
const red: MantineColorsTuple = [
  "#FFEDEB", "#FFD9D5", "#FFB0A8", "#FC8478", "#F75E4F", "#F44636", "#EF3124", "#D52418", "#BE1C12", "#A6100A",
];
const lime: MantineColorsTuple = [
  "#F3FDEA", "#E5F9D4", "#CBF3A8", "#B0EE79", "#99E952", "#8FEE52", "#7FD43F", "#6BB833", "#5A9E2A", "#4A8520",
];
const violet: MantineColorsTuple = [
  "#F4ECFF", "#E5D6FF", "#C8ABFF", "#AA7CFF", "#9B5CFF", "#8A45FA", "#7F38F8", "#6C2ADD", "#6023C6", "#521BAE",
];

export const theme = createTheme({
  primaryColor: "brand",
  primaryShade: 6,
  colors: { brand: red, lime, violet },
  black: COLORS.text,
  fontFamily: "'Golos Text', system-ui, -apple-system, 'Segoe UI', sans-serif",
  headings: {
    fontFamily: "'Golos Text', system-ui, sans-serif",
    fontWeight: "600",
    sizes: {
      h1: { fontSize: "40px", lineHeight: "1.05" },
      h2: { fontSize: "30px", lineHeight: "1.1" },
      h3: { fontSize: "22px", lineHeight: "1.2" },
      h4: { fontSize: "18px", lineHeight: "1.25" },
    },
  },
  defaultRadius: "md",
  radius: { xs: "8px", sm: "12px", md: `${RADIUS.control}px`, lg: `${RADIUS.block}px`, xl: `${RADIUS.card}px` },
  components: {
    Card: { defaultProps: { radius: "xl", padding: "xl", shadow: undefined } },
    Paper: { defaultProps: { radius: "xl" } },
    Button: { defaultProps: { radius: "md", size: "md" } },
    TextInput: { defaultProps: { radius: "md", size: "md" } },
    NumberInput: { defaultProps: { radius: "md", size: "md" } },
    Select: { defaultProps: { radius: "md", size: "md" } },
    Textarea: { defaultProps: { radius: "md", size: "md" } },
    PasswordInput: { defaultProps: { radius: "md", size: "md" } },
    Badge: { defaultProps: { radius: "md" } },
    Tooltip: { defaultProps: { multiline: true, w: 280, withArrow: true, events: { hover: true, focus: true, touch: true } } },
  },
});
