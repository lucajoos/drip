import SwiftUI

/// Runterzählender Fortschrittsring: voll = definierte Gesamtdauer,
/// leer = fertig.
struct CountdownRing: View {
    let deadline: Date
    let totalSeconds: Int

    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { context in
            let remaining = max(0, deadline.timeIntervalSince(context.date))
            let progress = min(1, remaining / Double(max(totalSeconds, 1)))
            ZStack {
                Circle()
                    .stroke(.blue.opacity(0.15), lineWidth: 6)
                Circle()
                    .trim(from: 0, to: progress)
                    .stroke(.blue, style: StrokeStyle(lineWidth: 6, lineCap: .round))
                    .rotationEffect(.degrees(-90))
                Image(systemName: "drop.fill")
                    .font(.system(size: 16))
                    .foregroundStyle(.blue)
            }
            .frame(width: 54, height: 54)
            .animation(.linear(duration: 1), value: progress)
        }
    }
}
