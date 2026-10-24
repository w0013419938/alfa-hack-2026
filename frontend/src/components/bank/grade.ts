/**
 * Цвет текста грейда: одна шкала «хорошо / нормально / плохо», а не отдельный цвет на каждую букву.
 * Буквы грейдов заданы в backend/config/scoring.yaml; если появится новая, она будет чернильной.
 */
import { COLORS } from "../../theme";

const GRADE_TEXT: Record<string, string> = {
  A: COLORS.positiveText,
  B: COLORS.positiveText,
  C: COLORS.text,
  D: COLORS.accentText,
  E: COLORS.accentText,
};

export function gradeColor(grade: string | null | undefined): string {
  return (grade && GRADE_TEXT[grade]) || COLORS.text;
}
