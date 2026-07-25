import SwiftUI

struct SchedulesView: View {
    @State private var schedules: [Schedule] = []
    @State private var isLoaded = false
    @State private var errorMessage: String?
    @State private var editorItem: EditorItem?

    private enum EditorItem: Identifiable {
        case new
        case edit(Schedule)

        var id: String {
            switch self {
            case .new: "new"
            case .edit(let s): "edit-\(s.id)"
            }
        }
    }

    var body: some View {
        NavigationStack {
            Group {
                if schedules.isEmpty && isLoaded {
                    ContentUnavailableView {
                        Label("Noch keine Gießpläne", systemImage: "calendar.badge.plus")
                    } description: {
                        Text(errorMessage ?? "Lege den ersten Plan an, damit automatisch gegossen wird.")
                    } actions: {
                        Button("Plan erstellen") { editorItem = .new }
                            .buttonStyle(.glassProminent)
                    }
                } else {
                    List {
                        ForEach(Zone.allCases) { zone in
                            let zoneSchedules = schedules.filter { $0.zone == zone }
                            if !zoneSchedules.isEmpty {
                                Section {
                                    ForEach(zoneSchedules) { schedule in
                                        ScheduleRow(schedule: schedule) { enabled in
                                            setEnabled(schedule, enabled)
                                        }
                                        .contentShape(.rect)
                                        .onTapGesture { editorItem = .edit(schedule) }
                                    }
                                    .onDelete { offsets in
                                        delete(zoneSchedules, at: offsets)
                                    }
                                } header: {
                                    Label(zone.displayName, systemImage: zone.symbolName)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Pläne")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        editorItem = .new
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .refreshable { await load() }
            .task { await load() }
            .sheet(item: $editorItem) { item in
                switch item {
                case .new:
                    ScheduleEditor(schedule: nil) { await load() }
                case .edit(let schedule):
                    ScheduleEditor(schedule: schedule) { await load() }
                }
            }
        }
    }

    private func load() async {
        do {
            schedules = try await DripClient.shared.schedules()
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoaded = true
    }

    private func setEnabled(_ schedule: Schedule, _ enabled: Bool) {
        var payload = SchedulePayload(from: schedule)
        payload.enabled = enabled
        Task {
            _ = try? await DripClient.shared.updateSchedule(id: schedule.id, payload)
            await load()
        }
    }

    private func delete(_ zoneSchedules: [Schedule], at offsets: IndexSet) {
        let toDelete = offsets.map { zoneSchedules[$0] }
        Task {
            for schedule in toDelete {
                try? await DripClient.shared.deleteSchedule(id: schedule.id)
            }
            await load()
        }
    }
}

#Preview {
    SchedulesView()
}
