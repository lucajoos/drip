import SwiftUI

struct EventRow: View {
    let entry: LogEntry

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: entry.symbolName)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(.white)
                .frame(width: 30, height: 30)
                .background(color.gradient, in: .circle)

            VStack(alignment: .leading, spacing: 2) {
                Text(entry.title)
                    .font(.subheadline)
                Text(entry.time.formatted(date: .omitted, time: .shortened))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }

    private var color: Color {
        switch entry.event {
        case "water_start", "water_end": .blue
        case "skip_rain": .teal
        case "skip_busy": .orange
        case "weather_error", "error": .orange
        case "boot": .gray
        default: .gray
        }
    }
}
