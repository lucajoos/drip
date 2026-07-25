import SwiftUI

struct ScheduleRow: View {
    let schedule: Schedule
    let onToggle: (Bool) -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text(schedule.time)
                    .font(.title2.weight(.semibold).monospacedDigit())
                HStack(spacing: 6) {
                    Text(subtitle)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    if schedule.rainSkip.enabled {
                        Label("ab \(schedule.rainSkip.thresholdMm, format: .number.precision(.fractionLength(0...1))) mm",
                              systemImage: "cloud.rain.fill")
                            .font(.caption.weight(.medium))
                            .padding(.horizontal, 7)
                            .padding(.vertical, 2)
                            .background(.teal.opacity(0.15), in: .capsule)
                            .foregroundStyle(.teal)
                    }
                }
            }
            Spacer()
            Toggle("", isOn: Binding(
                get: { schedule.enabled },
                set: { onToggle($0) }
            ))
            .labelsHidden()
        }
        .opacity(schedule.enabled ? 1 : 0.5)
    }

    private var subtitle: String {
        var parts = [schedule.rhythmSummary, "\(schedule.durationMin) min"]
        if schedule.enabled, let next = schedule.nextRun {
            parts.append(next.formatted(.relative(presentation: .named)))
        }
        return parts.joined(separator: " · ")
    }
}
