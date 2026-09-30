// Hand-drawn SVG scenes. The motion is pure CSS (see styles/art.css) so it costs
// nothing at runtime and stops for people who asked for reduced motion.

export function Logo({ size = 40, wordmark = true, light = false }) {
  return (
    <span className={`logo ${light ? "logo-light" : ""}`}>
      <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
        <defs>
          <linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#34d399" />
            <stop offset="1" stopColor="#0f766e" />
          </linearGradient>
        </defs>
        <rect width="48" height="48" rx="14" fill="url(#logo-g)" />
        <path d="M13 35C12 23 20 14 35 12c1 14-6 23-22 23z" fill="#fff" fillOpacity=".95" />
        <path
          className="logo-pulse"
          d="M9 29h8l3.5-7 4.5 12 3.5-8H36"
          fill="none"
          stroke="#0f766e"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {wordmark && (
        <span className="logo-word">
          Agri<b>Pulse</b>
        </span>
      )}
    </span>
  );
}

// Rolling field with swaying wheat, a sun and drifting clouds
export function WheatField({ stalks = 26 }) {
  const items = Array.from({ length: stalks }, (_, i) => i);

  return (
    <svg className="art-field" viewBox="0 0 800 360" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <defs>
        <linearGradient id="sky-g" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0d3b2e" />
          <stop offset=".55" stopColor="#14705a" />
          <stop offset="1" stopColor="#f5b83d" stopOpacity=".55" />
        </linearGradient>
        <radialGradient id="sun-g" cx=".5" cy=".5" r=".5">
          <stop offset="0" stopColor="#fff3c4" />
          <stop offset=".45" stopColor="#f9c74f" />
          <stop offset="1" stopColor="#f9c74f" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect width="800" height="360" fill="url(#sky-g)" />

      <g className="art-sun">
        <circle cx="610" cy="120" r="120" fill="url(#sun-g)" />
        <circle cx="610" cy="120" r="46" fill="#fde68a" />
      </g>

      <g className="art-cloud art-cloud-1" fill="#fff" fillOpacity=".16">
        <ellipse cx="160" cy="90" rx="70" ry="20" />
        <ellipse cx="205" cy="76" rx="44" ry="20" />
      </g>
      <g className="art-cloud art-cloud-2" fill="#fff" fillOpacity=".12">
        <ellipse cx="430" cy="52" rx="60" ry="16" />
        <ellipse cx="465" cy="42" rx="34" ry="15" />
      </g>

      <path d="M0 250Q160 200 330 236T640 220T800 240V360H0Z" fill="#0b4f3c" fillOpacity=".75" />
      <path d="M0 285Q200 245 400 275T800 268V360H0Z" fill="#0a6b4c" />

      <g>
        {items.map((i) => {
          const x = 14 + (i * 772) / (stalks - 1);
          const h = 46 + ((i * 37) % 30);
          const base = 340 - ((i * 13) % 16);

          return (
            <g
              key={i}
              className="art-stalk"
              style={{ animationDelay: `${(i % 9) * -0.35}s`, transformOrigin: `${x}px ${base}px` }}
            >
              <path d={`M${x} ${base}q3 -${h / 2} 0 -${h}`} stroke="#c9a227" strokeWidth="2" fill="none" />
              <ellipse cx={x} cy={base - h - 6} rx="4" ry="11" fill="#f5c542" />
              <ellipse cx={x - 5} cy={base - h + 4} rx="3" ry="8" fill="#e6b325" transform={`rotate(-24 ${x - 5} ${base - h + 4})`} />
              <ellipse cx={x + 5} cy={base - h + 4} rx="3" ry="8" fill="#e6b325" transform={`rotate(24 ${x + 5} ${base - h + 4})`} />
            </g>
          );
        })}
      </g>
    </svg>
  );
}

// Sun / clouds / rain, picked from the weather text ("Clear", "Light rain"...)
export function WeatherArt({ condition = "", size = 150 }) {
  const text = String(condition).toLowerCase();

  const kind = /thunder|storm/.test(text)
    ? "storm"
    : /rain|drizzle|shower/.test(text)
    ? "rain"
    : /mist|fog|haze|smoke|dust/.test(text)
    ? "mist"
    : /cloud|overcast/.test(text)
    ? "cloud"
    : "sun";

  const cloud = (
    <g className="wx-cloud">
      <ellipse cx="82" cy="98" rx="46" ry="20" fill="#fff" />
      <ellipse cx="60" cy="86" rx="26" ry="20" fill="#fff" />
      <ellipse cx="96" cy="78" rx="30" ry="24" fill="#fff" />
    </g>
  );

  return (
    <svg width={size} height={size} viewBox="0 0 150 150" className={`wx-art wx-${kind}`} aria-hidden="true">
      {(kind === "sun" || kind === "cloud") && (
        <g className="wx-sun" transform={kind === "cloud" ? "translate(-18 -20) scale(.8)" : ""}>
          <circle cx="75" cy="75" r="26" fill="#fbbf24" />
          {Array.from({ length: 12 }, (_, i) => (
            <line
              key={i}
              x1="75"
              y1="28"
              x2="75"
              y2="40"
              stroke="#fbbf24"
              strokeWidth="5"
              strokeLinecap="round"
              transform={`rotate(${i * 30} 75 75)`}
            />
          ))}
        </g>
      )}

      {kind !== "sun" && (
        <g fillOpacity={kind === "mist" ? 0.7 : 1}>{cloud}</g>
      )}

      {(kind === "rain" || kind === "storm") &&
        [48, 68, 88, 108].map((x, i) => (
          <line
            key={x}
            className="wx-drop"
            style={{ animationDelay: `${i * -0.25}s` }}
            x1={x}
            y1="112"
            x2={x - 6}
            y2="128"
            stroke="#7dd3fc"
            strokeWidth="4"
            strokeLinecap="round"
          />
        ))}

      {kind === "storm" && (
        <path className="wx-bolt" d="M78 104l-14 22h12l-6 20 22-28H80l8-14z" fill="#fde047" />
      )}

      {kind === "mist" &&
        [112, 124, 136].map((y, i) => (
          <line
            key={y}
            className="wx-mist"
            style={{ animationDelay: `${i * -0.8}s` }}
            x1="40"
            y1={y}
            x2="112"
            y2={y}
            stroke="#fff"
            strokeOpacity=".7"
            strokeWidth="5"
            strokeLinecap="round"
          />
        ))}
    </svg>
  );
}

// The leaf being scanned while the model thinks
export function ScannerOverlay() {
  return (
    <div className="scanner" aria-hidden="true">
      <span className="scanner-corner tl" />
      <span className="scanner-corner tr" />
      <span className="scanner-corner bl" />
      <span className="scanner-corner br" />
      <span className="scanner-line" />
    </div>
  );
}

// Friendly empty-state drawing
export function EmptyArt({ children }) {
  return (
    <div className="empty-art">
      <span className="empty-ring empty-ring-1" />
      <span className="empty-ring empty-ring-2" />
      <span className="empty-core">{children}</span>
    </div>
  );
}
