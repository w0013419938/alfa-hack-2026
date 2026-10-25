/** Банковский термин с подсказкой: пунктирное подчёркивание, по наведению объяснение в одну фразу. */
import { Tooltip } from "@mantine/core";
import type { ReactNode } from "react";

import { GLOSSARY, type TermId } from "../texts/glossary";

export function Term({ id, children }: { id: TermId; children: ReactNode }) {
  return (
    <Tooltip label={GLOSSARY[id]}>
      <span
        tabIndex={0}
        style={{ borderBottom: "1px dashed currentColor", cursor: "help", textDecoration: "none" }}
        data-term={id}
      >
        {children}
      </span>
    </Tooltip>
  );
}
