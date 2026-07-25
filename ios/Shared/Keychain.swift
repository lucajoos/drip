import Foundation
import Security

/// Minimaler Keychain-Wrapper fuer den API-Key. Ohne explizite Access Group --
/// Items landen in der ersten Gruppe aus den Entitlements
/// (de.lucajoos.drip.shared), auf die auch das Widget Zugriff hat.
enum Keychain {
    private static let service = "de.lucajoos.drip"
    private static let account = "apiKey"

    private static var baseQuery: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }

    static func save(_ value: String) {
        SecItemDelete(baseQuery as CFDictionary)
        guard !value.isEmpty, let data = value.data(using: .utf8) else { return }
        var query = baseQuery
        query[kSecValueData as String] = data
        // AfterFirstUnlock: auch fuer Widget/Background-Refresh bei gesperrtem Geraet lesbar
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        SecItemAdd(query as CFDictionary, nil)
    }

    static func load() -> String? {
        var query = baseQuery
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
}
