import SwiftUI

struct WaterSheet: View {
    let zone: Zone
    let onStarted: () async -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var durationMin = 10
    @State private var isStarting = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Picker("Dauer", selection: $durationMin) {
                    ForEach(1...45, id: \.self) { minutes in
                        Text("\(minutes) min").tag(minutes)
                    }
                }
                .pickerStyle(.wheel)

                if let errorMessage {
                    Label(errorMessage, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(.red)
                }

                Button {
                    start()
                } label: {
                    if isStarting {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Label("Gießen starten", systemImage: "drop.fill")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.glassProminent)
                .controlSize(.large)
                .disabled(isStarting)
            }
            .padding()
            .navigationTitle(zone.displayName)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Abbrechen", role: .cancel) { dismiss() }
                }
            }
        }
        .presentationDetents([.medium])
        .sensoryFeedback(.success, trigger: isStarting)
    }

    private func start() {
        isStarting = true
        errorMessage = nil
        Task {
            do {
                try await DripClient.shared.water(zone: zone, durationMin: durationMin)
                await onStarted()
                dismiss()
            } catch {
                errorMessage = error.localizedDescription
            }
            isStarting = false
        }
    }
}
