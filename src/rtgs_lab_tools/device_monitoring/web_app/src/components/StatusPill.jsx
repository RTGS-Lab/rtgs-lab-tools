import { font, size } from "../theme";
import { STATUS } from "../utils";

export default function StatusPill({ value, trueLabel = "YES", falseLabel = "NO", trueLevel = "bad", falseLevel = "good" }) {
  const isTrue = value === true || value === "true" || value === 1 || value === "1";
  // Bright hue tints the chip, dark ink carries the label.
  const { fill, ink } = STATUS[isTrue ? trueLevel : falseLevel];
  return (
    <span style={{
      display: "inline-block",
      padding: "3px 12px",
      borderRadius: 99,
      fontSize: size.sm,
      fontFamily: font.mono,
      fontWeight: 600,
      letterSpacing: "0.09em",
      background: `${fill}26`,
      color: ink,
      border: `1px solid ${fill}66`,
    }}>
      {isTrue ? trueLabel : falseLabel}
    </span>
  );
}
