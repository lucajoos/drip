import SwiftUI

struct LogsView: View {
    @State private var entries: [LogEntry] = []
    @State private var isLoaded = false
    @State private var errorMessage: String?
    @State private var zoneFilter: Zone?

    private var filtered: [LogEntry] {
        guard let zoneFilter else { return entries }
        return entries.filter { $0.zone == zoneFilter }
    }

    private var groupedByDay: [(day: Date, entries: [LogEntry])] {
        let groups = Dictionary(grouping: filtered) {
            Calendar.current.startOfDay(for: $0.time)
        }
        return groups.keys.sorted(by: >).map { ($0, groups[$0] ?? []) }
    }

    var body: some View {
        NavigationStack {
            Group {
                if filtered.isEmpty && isLoaded {
                    ContentUnavailableView(
                        "Kein Verlauf",
                        systemImage: "list.bullet.rectangle",
                        description: Text(errorMessage ?? "Sobald gegossen wird, erscheinen hier die Ereignisse.")
                    )
                } else {
                    List {
                        ForEach(groupedByDay, id: \.day) { group in
                            Section(dayTitle(group.day)) {
                                ForEach(group.entries) { entry in
                                    EventRow(entry: entry)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Verlauf")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Picker("Zone", selection: $zoneFilter) {
                            Text("Alle Zonen").tag(Zone?.none)
                            ForEach(Zone.allCases) { zone in
                                Text(zone.displayName).tag(Zone?.some(zone))
                            }
                        }
                    } label: {
                        Image(systemName: zoneFilter == nil
                              ? "line.3.horizontal.decrease.circle"
                              : "line.3.horizontal.decrease.circle.fill")
                    }
                }
            }
            .refreshable { await load() }
            .task { await load() }
        }
    }

    private func load() async {
        do {
            entries = try await DripClient.shared.logs(limit: 100)
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoaded = true
    }

    private func dayTitle(_ day: Date) -> String {
        if Calendar.current.isDateInToday(day) { return "Heute" }
        if Calendar.current.isDateInYesterday(day) { return "Gestern" }
        return day.formatted(date: .abbreviated, time: .omitted)
    }
}

#Preview {
    LogsView()
}
