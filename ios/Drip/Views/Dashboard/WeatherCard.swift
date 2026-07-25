import SwiftUI

struct WeatherCard: View {
    let weather: WeatherInfo?

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("Regen", systemImage: "cloud.rain.fill")
                .font(.headline)

            if let weather, weather.ok {
                HStack(spacing: 12) {
                    StatCell(title: "Letzte 24 h", value: weather.past24Mm ?? 0)
                    StatCell(title: "Nächste 12 h", value: weather.next12Mm ?? 0)
                }
                if let fetchedAt = weather.fetchedAt {
                    Text("Stand \(fetchedAt.formatted(date: .omitted, time: .shortened))")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            } else {
                Text(weather?.error ?? "Keine Wetterdaten")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassEffect(.regular, in: .rect(cornerRadius: 24))
    }
}

private struct StatCell: View {
    let title: String
    let value: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text("\(value, format: .number.precision(.fractionLength(1))) mm")
                .font(.title3.weight(.semibold).monospacedDigit())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.fill.tertiary, in: .rect(cornerRadius: 12))
    }
}
