interface RadarData {
  label: string
  value: number
  maxValue: number
}

interface RadarChartProps {
  data: RadarData[]
  playerName: string
  color: string
  size?: number
}

function hexPoint(cx: number, cy: number, r: number, index: number): [number, number] {
  const angle = -Math.PI / 2 + (Math.PI / 3) * index
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)]
}

const STAT_LABELS = ['Rating', 'KPR', 'ADR', 'K-A-S-T', 'Impact', 'Survival']

export default function RadarChart({ data, playerName, color, size = 220 }: RadarChartProps) {
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.38

  const levels = [0.2, 0.4, 0.6, 0.8, 1.0]

  const dataPoints = data.map((d, i) => {
    const ratio = Math.min(d.value / d.maxValue, 1)
    return hexPoint(cx, cy, r * ratio, i)
  })

  const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ') + ' Z'

  return (
    <div className="radar-animate flex flex-col items-center gap-2" style={{ animationDelay: '0.1s' }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
        {/* Grid polygons */}
        {levels.map((level) => {
          const pts = Array.from({ length: 6 }, (_, i) => {
            const [px, py] = hexPoint(cx, cy, r * level, i)
            return `${px.toFixed(2)},${py.toFixed(2)}`
          }).join(' ')
          return (
            <polygon
              key={level}
              points={pts}
              fill="none"
              stroke="#3f3f46"
              strokeWidth="0.5"
            />
          )
        })}

        {/* Axis lines */}
        {Array.from({ length: 6 }, (_, i) => {
          const [ex, ey] = hexPoint(cx, cy, r, i)
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={ex}
              y2={ey}
              stroke="#27272a"
              strokeWidth="0.5"
            />
          )
        })}

        {/* Data area */}
        <polygon
          points={dataPath}
          fill={`${color}25`}
          stroke={color}
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Data points */}
        {dataPoints.map(([px, py], i) => (
          <circle
            key={i}
            cx={px}
            cy={py}
            r="3.5"
            fill="#18181b"
            stroke={color}
            strokeWidth="2"
          />
        ))}

        {/* Labels */}
        {Array.from({ length: 6 }, (_, i) => {
          const [lx, ly] = hexPoint(cx, cy, r + 22, i)
          const value = data[i].value.toFixed(data[i].label === 'Rating' ? 2 : 1)
          return (
            <text
              key={i}
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#a1a1aa"
              className="font-mono"
              style={{ fontSize: '11px' }}
            >
              {value}
            </text>
          )
        })}

        {/* Stat labels outside */}
        {Array.from({ length: 6 }, (_, i) => {
          const [lx, ly] = hexPoint(cx, cy, r + 40, i)
          return (
            <text
              key={`label-${i}`}
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#71717a"
              style={{ fontSize: '10px', letterSpacing: '0.05em', textTransform: 'uppercase' }}
            >
              {STAT_LABELS[i]}
            </text>
          )
        })}
      </svg>
      <span className="text-sm font-medium text-zinc-300 tracking-tight truncate max-w-[180px]">
        {playerName}
      </span>
    </div>
  )
}
