import SwiftUI

struct ZoneCard: View {
    let zone: Zone
    let status: ZoneStatus?
    let fetchedAt: Date
    let onWater: () -> Void
    let onStop: () -> Void

    private var isActive: Bool { status?.active == true }

    /// Zeitpunkt, an dem das Gießen endet (aus remainingS beim Abruf)
    private var deadline: Date? {
        guard let remaining = status?.remainingS, isActive else { return nil }
        return fetchedAt.addingTimeInterval(TimeInterval(remaining))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label(zone.displayName, systemImage: zone.symbolName)
                    .font(.headline)
                Spacer()
                if isActive {
                    Image(systemName: "drop.fill")
                        .foregroundStyle(.blue)
                        .symbolEffect(.variableColor.iterative, options: .repeating)
                    Text(status?.cause == "schedule" ? "Geplant" : "Manuell")
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(.blue.opacity(0.15), in: .capsule)
                        .foregroundStyle(.blue)
                }
            }

            if isActive, let deadline {
                HStack(spacing: 16) {
                    CountdownRing(deadline: deadline,
                                  totalSeconds: status?.durationS ?? status?.remainingS ?? 1)
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Gießt gerade")
                            .font(.subheadline.weight(.medium))
                        Text(timerInterval: Date()...deadline, countsDown: true)
                            .font(.title2.weight(.semibold).monospacedDigit())
                            .contentTransition(.numericText())
                    }
                    Spacer()
                }
            } else {
                VStack(alignment: .leading, spacing: 6) {
                    InfoRow(symbol: "clock",
                            text: nextRunText)
                    if let lastEnd = status?.lastRunEnd {
                        InfoRow(symbol: "checkmark.circle",
                                text: "Zuletzt \(lastEnd.formatted(.relative(presentation: .named)))"
                                    + lastDurationSuffix)
                    }
                }
                .foregroundStyle(.secondary)
                .font(.subheadline)
            }

            HStack {
                if isActive {
                    Button(role: .destructive, action: onStop) {
                        Label("Stoppen", systemImage: "stop.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.glass)
                } else {
                    Button(action: onWater) {
                        Label("Gießen", systemImage: "drop.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.glassProminent)
                    .disabled(status == nil)
                }
            }
        }
        .padding(18)
        .glassEffect(.regular, in: .rect(cornerRadius: 24))
        .animation(.smooth, value: isActive)
    }

    private var nextRunText: String {
        guard let next = status?.nextScheduledRun else {
            return "Kein Gießplan aktiv"
        }
        return "Nächster Lauf \(next.formatted(.relative(presentation: .named)))"
    }

    private var lastDurationSuffix: String {
        guard let s = status?.lastRunDurationS else { return "" }
        if s < 60 { return " · \(s) s" }
        return " · \((s + 30) / 60) min"
    }
}

private struct InfoRow: View {
    let symbol: String
    let text: String

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: symbol)
            Text(text)
        }
    }
}
