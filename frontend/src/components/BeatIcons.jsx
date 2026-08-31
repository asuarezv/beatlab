import { severityColor, severityLabel, typeIconName } from "../severity.js";

const SIZE = 18;

function Svg({ label, color, children }) {
  return (
    <svg
      className="beat-icon"
      width={SIZE}
      height={SIZE}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label={label}
    >
      <title>{label}</title>
      {children}
    </svg>
  );
}

const TYPE_PATHS = {
  pulse: (
    <polyline points="3 12 7 12 9 5 13 19 15 12 21 12" />
  ),
  alert: (
    <>
      <path d="M12 3 3 20h18L12 3z" />
      <path d="M12 9v5" />
      <circle cx="12" cy="17" r="0.6" fill="currentColor" />
    </>
  ),
  check: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="m8.5 12.5 2.4 2.4 4.6-5" />
    </>
  ),
  error: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="m9 9 6 6M15 9l-6 6" />
    </>
  ),
  sync: (
    <>
      <path d="M20 12a8 8 0 0 0-13.7-5.6L4 8" />
      <path d="M4 4v4h4" />
      <path d="M4 12a8 8 0 0 0 13.7 5.6L20 16" />
      <path d="M20 20v-4h-4" />
    </>
  ),
  cloud: (
    <path d="M7 18h10a4 4 0 0 0 .4-8 6 6 0 0 0-11.5-1.6A3.6 3.6 0 0 0 7 18z" />
  ),
  server: (
    <>
      <rect x="4" y="4" width="16" height="6" rx="1.4" />
      <rect x="4" y="14" width="16" height="6" rx="1.4" />
      <path d="M8 7h.01M8 17h.01" />
    </>
  ),
  shield: <path d="M12 3 5 6v6c0 4.2 2.8 7.2 7 8.5 4.2-1.3 7-4.3 7-8.5V6l-7-3z" />,
  bell: (
    <>
      <path d="M6 16V11a6 6 0 1 1 12 0v5l1.2 2H4.8L6 16z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </>
  ),
  activity: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="M8 14V8M12 16V10M16 13V7" />
    </>
  ),
};

export function TypeIcon({ name, label, color = "#6ee7ff" }) {
  const key = TYPE_PATHS[name] ? name : "pulse";
  return (
    <Svg label={label || "Tipo de Beat"} color={color}>
      {TYPE_PATHS[key]}
    </Svg>
  );
}

export function SeverityIcon({ severity, label }) {
  const color = severityColor(severity);
  const text = label || `Severidad ${severityLabel(severity)}`;
  if (severity === "info") {
    return (
      <Svg label={text} color={color}>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 11v5" />
        <circle cx="12" cy="8" r="0.7" fill={color} />
      </Svg>
    );
  }
  if (severity === "alerta") {
    return (
      <Svg label={text} color={color}>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 8v5" />
        <circle cx="12" cy="16" r="0.7" fill={color} />
      </Svg>
    );
  }
  if (severity === "critica") {
    return (
      <Svg label={text} color={color}>
        <path d="M13 3 5 14h6l-1 7 8-12h-6l1-6z" />
      </Svg>
    );
  }
  return (
    <Svg label={text} color={color}>
      <path d="M12 4 3 20h18L12 4z" />
      <path d="M12 10v5" />
      <circle cx="12" cy="17.2" r="0.6" fill={color} />
    </Svg>
  );
}

export function BeatMarks({ item }) {
  const typeName = item.beat_type_name || "Tipo";
  const sev = item.severity || "aviso";
  const sevText = item.severity_label || severityLabel(sev);
  return (
    <span className="beat-marks" aria-label={`${typeName}, severidad ${sevText}`}>
      <TypeIcon name={typeIconName(item)} label={`Tipo ${typeName}`} />
      <SeverityIcon severity={sev} label={`Severidad ${sevText}`} />
    </span>
  );
}

export function SeverityBadge({ severity, label }) {
  const sev = severity || "aviso";
  const text = label || severityLabel(sev);
  return (
    <span className={`sev-badge sev-${sev}`}>
      <SeverityIcon severity={sev} label={`Severidad ${text}`} />
      {text}
    </span>
  );
}
