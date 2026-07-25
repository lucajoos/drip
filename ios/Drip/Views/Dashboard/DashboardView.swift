import SwiftUI
import WidgetKit

struct DashboardView: View {
    @State private var client = DripClient.shared
    @State private var status: SystemStatus?
    @State private var weather: WeatherInfo?
    @State private var fetchedAt = Date()
    @State private var errorMessage: String?
    @State private var waterSheetZone: Zone?
    @State private var stopZone: Zone?

    var body: some View {
        NavigationStack {
            ScrollView {
                GlassEffectContainer(spacing: 20) {
                    VStack(spacing: 16) {
                        ForEach(Zone.allCases) { zone in
                            ZoneCard(
                                zone: zone,
                                status: status?.zone(zone),
                                fetchedAt: fetchedAt,
                                onWater: { waterSheetZone = zone },
                                onStop: { stopZone = zone }
                            )
                        }
                        WeatherCard(weather: weather)
                        if let errorMessage, status == nil {
                            ContentUnavailableView(
                                "Nicht erreichbar",
                                systemImage: "wifi.exclamationmark",
                                description: Text(errorMessage)
                            )
                        }
                    }
                    .padding(.horizontal)
                }
            }
            .navigationTitle("Drip")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    ConnectionBadge(route: client.activeRoute)
                }
            }
            .refreshable { await load() }
            .task {
                while !Task.isCancelled {
                    await load()
                    try? await Task.sleep(for: .seconds(10))
                }
            }
            .sheet(item: $waterSheetZone) { zone in
                WaterSheet(zone: zone) {
                    await load()
                    WidgetCenter.shared.reloadAllTimelines()
                }
            }
            .confirmationDialog(
                Text("\(stopZone?.displayName ?? "") – Gießen stoppen?"),
                isPresented: Binding(
                    get: { stopZone != nil },
                    set: { if !$0 { stopZone = nil } }
                ),
                titleVisibility: .visible,
                presenting: stopZone
            ) { zone in
                Button("\(zone.displayName) stoppen", role: .destructive) {
                    Task {
                        try? await client.stop(zone: zone)
                        await load()
                        WidgetCenter.shared.reloadAllTimelines()
                    }
                }
            }
            .sensoryFeedback(.impact, trigger: stopZone)
        }
    }

    private func load() async {
        do {
            status = try await client.status()
            fetchedAt = Date()
            errorMessage = nil
            if let status {
                LiveActivityManager.sync(with: status, fetchedAt: fetchedAt)
            }
        } catch {
            errorMessage = error.localizedDescription
        }
        weather = try? await client.weather()
    }
}

#Preview {
    DashboardView()
}
