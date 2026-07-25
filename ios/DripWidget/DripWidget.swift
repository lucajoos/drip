import SwiftUI
import WidgetKit

@main
struct DripWidgetBundle: WidgetBundle {
    var body: some Widget {
        DripStatusWidget()
        WateringLiveActivity()
    }
}

struct DripStatusWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "DripStatusWidget", provider: StatusProvider()) { entry in
            DripWidgetView(entry: entry)
                .containerBackground(.fill.tertiary, for: .widget)
        }
        .configurationDisplayName("Gießstatus")
        .description("Zeigt den Status beider Bewässerungszonen.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

struct StatusEntry: TimelineEntry {
    let date: Date
    let status: SystemStatus?
}

struct StatusProvider: TimelineProvider {
    func placeholder(in context: Context) -> StatusEntry {
        StatusEntry(date: .now, status: nil)
    }

    func getSnapshot(in context: Context, completion: @escaping (StatusEntry) -> Void) {
        Task { @MainActor in
            let status = try? await DripClient.shared.status()
            completion(StatusEntry(date: .now, status: status))
        }
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<StatusEntry>) -> Void) {
        Task { @MainActor in
            let status = try? await DripClient.shared.status()
            let now = Date()
            var entries = [StatusEntry(date: now, status: status)]

            // Endet gerade ein Giessvorgang, direkt danach auf inaktiv umschalten
            let maxRemaining = status?.zones.compactMap { $0.active ? $0.remainingS : nil }.max()
            if let maxRemaining {
                var finished = status
                finished?.zones = status?.zones.map { zone in
                    var z = zone
                    z.active = false
                    z.remainingS = nil
                    return z
                } ?? []
                entries.append(StatusEntry(date: now.addingTimeInterval(TimeInterval(maxRemaining + 3)),
                                           status: finished))
            }

            let interval: TimeInterval = maxRemaining != nil ? 5 * 60 : 30 * 60
            completion(Timeline(entries: entries, policy: .after(now + interval)))
        }
    }
}

struct DripWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: StatusEntry

    var body: some View {
        if let status = entry.status {
            VStack(alignment: .leading, spacing: family == .systemSmall ? 8 : 12) {
                ForEach(status.zones) { zone in
                    ZoneLine(zoneStatus: zone, entryDate: entry.date,
                             compact: family == .systemSmall)
                }
                Spacer(minLength: 0)
                Text("Stand \(entry.date.formatted(date: .omitted, time: .shortened))")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        } else if !AppConfig.shared.isConfigured {
            VStack(spacing: 6) {
                Image(systemName: "gearshape")
                    .foregroundStyle(.secondary)
                Text("In der App URL und API-Key eintragen")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
        } else {
            VStack(spacing: 6) {
                Image(systemName: "wifi.exclamationmark")
                    .foregroundStyle(.secondary)
                Text("Nicht erreichbar")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

private struct ZoneLine: View {
    let zoneStatus: ZoneStatus
    let entryDate: Date
    let compact: Bool

    private var deadline: Date? {
        guard zoneStatus.active, let remaining = zoneStatus.remainingS else { return nil }
        return entryDate.addingTimeInterval(TimeInterval(remaining))
    }

    private var startDate: Date {
        guard let total = zoneStatus.durationS, let remaining = zoneStatus.remainingS else {
            return entryDate
        }
        return entryDate.addingTimeInterval(TimeInterval(-(total - remaining)))
    }

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: zoneStatus.zone.symbolName)
                .font(.system(size: compact ? 12 : 15, weight: .semibold))
                .foregroundStyle(zoneStatus.active ? .blue : .green)
            VStack(alignment: .leading, spacing: 1) {
                Text(zoneStatus.zone.displayName)
                    .font(compact ? .caption.weight(.semibold) : .subheadline.weight(.semibold))
                    .lineLimit(1)
                if let deadline {
                    // Tickt live weiter, ohne dass die Timeline neu laden muss
                    Text(timerInterval: entryDate...deadline, countsDown: true)
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.blue)
                } else {
                    Text(detail)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 0)
            if let deadline {
                ProgressView(timerInterval: startDate...deadline, countsDown: true) {
                    EmptyView()
                } currentValueLabel: {
                    EmptyView()
                }
                .progressViewStyle(.circular)
                .tint(.blue)
                .frame(width: compact ? 22 : 28, height: compact ? 22 : 28)
            } else {
                Circle()
                    .fill(Color.green.opacity(0.5))
                    .frame(width: 7, height: 7)
            }
        }
    }

    private var detail: String {
        if zoneStatus.active { return "Gießt gerade" }
        if let next = zoneStatus.nextScheduledRun {
            return "Nächster Lauf \(next.formatted(date: .omitted, time: .shortened))"
        }
        return "Kein Plan aktiv"
    }
}
