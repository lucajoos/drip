import SwiftUI

struct ScheduleEditor: View {
    /// nil = neuen Plan anlegen
    let schedule: Schedule?
    let onSaved: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var zone: Zone = .herbs
    @State private var time = Calendar.current.date(from: DateComponents(hour: 6, minute: 0)) ?? .now
    @State private var rhythm: Rhythm = .daily
    @State private var n = 2
    @State private var selectedWeekdays: Set<Weekday> = []
    @State private var durationMin = 10
    @State private var enabled = true
    @State private var rainSkipEnabled = false
    @State private var thresholdMm = 5.0
    @State private var isSaving = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Zone", selection: $zone) {
                        ForEach(Zone.allCases) { z in
                            Text(z.displayName).tag(z)
                        }
                    }
                    .pickerStyle(.segmented)

                    DatePicker("Uhrzeit", selection: $time, displayedComponents: .hourAndMinute)

                    Stepper(value: $durationMin, in: 1...45) {
                        LabeledContent("Dauer", value: "\(durationMin) min")
                    }
                }

                Section("Wiederholen") {
                    Picker("Rhythmus", selection: $rhythm) {
                        Text("Täglich").tag(Rhythm.daily)
                        Text("Alle n Tage").tag(Rhythm.everyNDays)
                        Text("Wochentage").tag(Rhythm.weekdays)
                    }
                    .pickerStyle(.segmented)

                    if rhythm == .everyNDays {
                        Stepper(value: $n, in: 1...30) {
                            LabeledContent("Intervall", value: "alle \(n) Tage")
                        }
                        Text("Beginnt heute und wiederholt sich alle \(n) Tage.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }

                    if rhythm == .weekdays {
                        ForEach(Weekday.allCases, id: \.self) { day in
                            Button {
                                if selectedWeekdays.contains(day) {
                                    selectedWeekdays.remove(day)
                                } else {
                                    selectedWeekdays.insert(day)
                                }
                            } label: {
                                HStack {
                                    Text(day.fullName)
                                        .foregroundStyle(.primary)
                                    Spacer()
                                    if selectedWeekdays.contains(day) {
                                        Image(systemName: "checkmark")
                                            .foregroundStyle(.tint)
                                    }
                                }
                            }
                        }
                    }
                }

                Section {
                    Toggle("Bei Regen überspringen", isOn: $rainSkipEnabled)
                    if rainSkipEnabled {
                        VStack(alignment: .leading) {
                            LabeledContent("Schwellwert",
                                           value: "\(thresholdMm.formatted(.number.precision(.fractionLength(0...1)))) mm")
                            Slider(value: $thresholdMm, in: 1...20, step: 0.5)
                        }
                    }
                } footer: {
                    Text("Übersprungen wird, wenn Regen der letzten 24 Stunden plus Vorhersage der nächsten 12 Stunden über dem Schwellwert liegt. Ist die Wetter-API nicht erreichbar, wird trotzdem gegossen.")
                }

                if schedule != nil {
                    Section {
                        Toggle("Aktiv", isOn: $enabled)
                    }
                }

                if let errorMessage {
                    Section {
                        Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle(schedule == nil ? "Neuer Plan" : "Plan bearbeiten")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Abbrechen", role: .cancel) { dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Sichern") { save() }
                        .disabled(isSaving || (rhythm == .weekdays && selectedWeekdays.isEmpty))
                }
            }
            .onAppear(perform: populate)
        }
    }

    private func populate() {
        guard let schedule else { return }
        zone = schedule.zone
        rhythm = schedule.rhythm
        n = schedule.n ?? 2
        selectedWeekdays = Set(schedule.weekdays ?? [])
        durationMin = schedule.durationMin
        enabled = schedule.enabled
        rainSkipEnabled = schedule.rainSkip.enabled
        thresholdMm = schedule.rainSkip.thresholdMm

        let parts = schedule.time.split(separator: ":").compactMap { Int($0) }
        if parts.count == 2,
           let date = Calendar.current.date(from: DateComponents(hour: parts[0], minute: parts[1])) {
            time = date
        }
    }

    private func save() {
        let components = Calendar.current.dateComponents([.hour, .minute], from: time)
        let timeString = String(format: "%02d:%02d", components.hour ?? 0, components.minute ?? 0)

        let payload = SchedulePayload(
            zone: zone,
            time: timeString,
            rhythm: rhythm,
            n: rhythm == .everyNDays ? n : nil,
            weekdays: rhythm == .weekdays
                ? Weekday.allCases.filter { selectedWeekdays.contains($0) }
                : nil,
            durationMin: durationMin,
            enabled: enabled,
            rainSkip: RainSkip(enabled: rainSkipEnabled, thresholdMm: thresholdMm)
        )

        isSaving = true
        errorMessage = nil
        Task {
            do {
                if let schedule {
                    try await DripClient.shared.updateSchedule(id: schedule.id, payload)
                } else {
                    try await DripClient.shared.createSchedule(payload)
                }
                await onSaved()
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
            }
            isSaving = false
        }
    }
}
