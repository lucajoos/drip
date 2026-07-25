import SwiftUI
import WidgetKit

struct SettingsView: View {
    @State private var config = AppConfig.shared
    @State private var client = DripClient.shared
    @State private var testState: TestState = .idle
    @State private var systemStatus: SystemStatus?

    private enum TestState: Equatable {
        case idle
        case running
        case success(Route)
        case failure(String)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    LabeledContent("Lokal") {
                        TextField("http://drip.local", text: $config.localURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("Unterwegs") {
                        TextField("optional", text: $config.remoteURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("API-Key") {
                        SecureField("Key", text: $config.apiKey)
                            .multilineTextAlignment(.trailing)
                    }

                    Button {
                        testConnection()
                    } label: {
                        HStack {
                            Text("Verbindung testen")
                            Spacer()
                            switch testState {
                            case .idle:
                                EmptyView()
                            case .running:
                                ProgressView()
                            case .success(let route):
                                Label(route.displayName, systemImage: "checkmark.circle.fill")
                                    .foregroundStyle(.green)
                            case .failure:
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.red)
                            }
                        }
                    }
                    .disabled(testState == .running)

                    if case .failure(let message) = testState {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                } header: {
                    Text("Verbindung")
                } footer: {
                    Text("Es wird zuerst die lokale URL versucht, danach die Unterwegs-URL (z.B. Port-Forwarding oder VPN-Adresse).")
                }

                Section {
                    Toggle("Mitteilungen", isOn: $config.notificationsEnabled)
                        .onChange(of: config.notificationsEnabled) { _, enabled in
                            if enabled { RefreshManager.requestAuthorization() }
                        }
                } footer: {
                    Text("Meldet gegossene Zonen und Regen-Skips. iOS entscheidet, wann im Hintergrund abgefragt wird – Mitteilungen können sich daher verzögern.")
                }

                if let status = systemStatus {
                    Section("System") {
                        LabeledContent("Zeitquelle", value: status.timeSource.uppercased())
                        LabeledContent("RTC", value: status.rtcPresent ? "verbunden" : "fehlt")
                        LabeledContent("WLAN-Signal", value: "\(status.rssi) dBm")
                        LabeledContent("Uptime", value: uptimeText(status.uptimeS))
                        LabeledContent("Freier Speicher", value: "\(status.freeHeap / 1024) KB")
                    }
                }
            }
            .navigationTitle("Einstellungen")
            .task { systemStatus = try? await client.status() }
            .refreshable { systemStatus = try? await client.status() }
            .onChange(of: config.apiKey) { reloadWidgets() }
            .onChange(of: config.localURL) { reloadWidgets() }
            .onChange(of: config.remoteURL) { reloadWidgets() }
        }
    }

    private func testConnection() {
        testState = .running
        Task {
            do {
                let route = try await client.testConnection()
                testState = .success(route)
                systemStatus = try? await client.status()
                WidgetCenter.shared.reloadAllTimelines()
            } catch {
                testState = .failure(error.localizedDescription)
            }
        }
    }

    private func reloadWidgets() {
        WidgetCenter.shared.reloadAllTimelines()
    }

    private func uptimeText(_ seconds: Int) -> String {
        let hours = seconds / 3600
        if hours >= 48 { return "\(hours / 24) Tage" }
        if hours >= 1 { return "\(hours) h" }
        return "\(seconds / 60) min"
    }
}

#Preview {
    SettingsView()
}
