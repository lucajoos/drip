import Foundation
import Observation

/// Konfiguration in der App Group (fuer App + Widget), API-Key im Keychain.
@Observable
final class AppConfig: @unchecked Sendable {
    static let appGroup = "group.de.lucajoos.drip"
    static let shared = AppConfig()

    private let defaults: UserDefaults

    var localURL: String {
        didSet { defaults.set(localURL, forKey: "localURL") }
    }
    var remoteURL: String {
        didSet { defaults.set(remoteURL, forKey: "remoteURL") }
    }
    var notificationsEnabled: Bool {
        didSet { defaults.set(notificationsEnabled, forKey: "notificationsEnabled") }
    }
    var lastSeenLogTs: Int {
        didSet { defaults.set(lastSeenLogTs, forKey: "lastSeenLogTs") }
    }
    var apiKey: String {
        didSet { Keychain.save(apiKey) }
    }

    var isConfigured: Bool {
        !apiKey.isEmpty && (!localURL.isEmpty || !remoteURL.isEmpty)
    }

    private init() {
        let d = UserDefaults(suiteName: Self.appGroup) ?? .standard
        defaults = d
        localURL = d.string(forKey: "localURL") ?? "http://drip.local"
        remoteURL = d.string(forKey: "remoteURL") ?? ""
        notificationsEnabled = d.bool(forKey: "notificationsEnabled")
        lastSeenLogTs = d.integer(forKey: "lastSeenLogTs")
        apiKey = Keychain.load() ?? ""

#if DEBUG
        // Fuer Simulator-Tests: Konfiguration per Launch-Environment vorbelegen
        let env = ProcessInfo.processInfo.environment
        if apiKey.isEmpty, let key = env["DRIP_API_KEY"] { apiKey = key }
        if let url = env["DRIP_LOCAL_URL"] { localURL = url }
#endif
    }
}
