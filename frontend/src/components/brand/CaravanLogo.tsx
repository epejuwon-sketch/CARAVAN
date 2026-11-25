import React from "react";

interface CaravanSymbolProps {
  size?: number;
  className?: string;
  color?: string;
}

/**
 * Official CARAVAN Geometric Gold Symbol.
 * Faithfully reconstructed from the official brand identity:
 * A distinctive upward-pointing double chevron symbol in sharp metallic gold.
 */
export const CaravanSymbol: React.FC<CaravanSymbolProps> = ({
  size = 32,
  className = "",
  color = "#C69D49",
}) => {
  return (
    <svg
      width={size}
      height={(size * 4) / 5}
      viewBox="0 0 100 80"
      fill={color}
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}
      aria-label="CARAVAN symbol"
    >
      {/* Upper Chevron */}
      <path d="M 50 6 L 90 53 L 75 53 L 50 24 L 25 53 L 10 53 Z" />
      {/* Lower / Inner Nested Chevron */}
      <path d="M 50 31 L 75 60.5 L 60 60.5 L 50 48 L 40 60.5 L 25 60.5 Z" />
    </svg>
  );
};

interface CaravanLogoProps {
  size?: number; // Height of symbol
  layout?: "horizontal" | "vertical" | "symbol";
  wordmarkColor?: "gold" | "white" | "inherit";
  subtitle?: string;
  onClick?: () => void;
  className?: string;
}

/**
 * Official CARAVAN Brand Lockup.
 * Symbol + geometric CARAVAN wordmark in clean, premium minimalist typography.
 */
export const CaravanLogo: React.FC<CaravanLogoProps> = ({
  size = 32,
  layout = "horizontal",
  wordmarkColor = "white",
  subtitle,
  onClick,
  className = "",
}) => {
  if (layout === "symbol") {
    return (
      <div
        className={className}
        onClick={onClick}
        style={{ display: "inline-flex", alignItems: "center", cursor: onClick ? "pointer" : "default" }}
      >
        <CaravanSymbol size={size} />
      </div>
    );
  }

  const textColor =
    wordmarkColor === "gold"
      ? "var(--accent-gold, #C69D49)"
      : wordmarkColor === "white"
      ? "#FFFFFF"
      : "inherit";

  return (
    <div
      className={className}
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: size * 0.35,
        flexDirection: layout === "vertical" ? "column" : "row",
        cursor: onClick ? "pointer" : "default",
        userSelect: "none",
      }}
    >
      <CaravanSymbol size={size} />
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <span
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 800,
            fontSize: size * 0.58,
            lineHeight: 1,
            letterSpacing: "0.14em",
            color: textColor,
            textTransform: "uppercase",
          }}
        >
          CARAVAN
        </span>
        {subtitle && (
          <span
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 600,
              fontSize: Math.max(9, size * 0.24),
              letterSpacing: "0.12em",
              color: "var(--text-secondary, #9E9E9E)",
              textTransform: "uppercase",
              marginTop: 3,
            }}
          >
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
};

export default CaravanLogo;
