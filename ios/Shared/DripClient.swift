import Foundation
import Observation

enum Route: String, Sendable {
    case local
    case remote

    var displayName: String {
        switch self {
        case .local: "Lokal"
        case .remote: "Unterwegs"
        }
    }
}

enum DripError: LocalizedError {
    case notConfigured
    case unauthorized
    case http(Int, String?)
    case unreachable

    var errorDescription: String? {
        switch self {
        case .notConfigured: "Keine Verbindung konfiguriert – URL und API-Key in den Einstellungen setzen."
        case .unauthorized: "API-Key wird abgelehnt (401)."
        case .http(let code, let message): message ?? "HTTP-Fehler \(code)"
        case .unreachable: "Controller nicht erreichbar."
        }
    }
}

/// API-Client mit Dual-URL-Strategie: erst lokale URL (kurzer Timeout),
/// dann Remote-URL. Die zuletzt funktionierende Route wird bevorzugt.
@MainActor
@Observable
final class DripClient {
    static let shared = DripClient()

    /// Route des letzten erfolgreichen Requests, nil = offline/unbekannt
    private(set) var activeRoute: Route?

    private var preferredRoute: Route = .local
    private let config = AppConfig.shared
    private let session: URLSession

    private static let dateFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = .current // Firmware liefert Lokalzeit Europe/Berlin
        return f
    }()

    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    private init() {
        let sessionConfig = URLSessionConfiguration.ephemeral
        sessionConfig.waitsForConnectivity = false
        session = URLSession(configuration: sessionConfig)

        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .formatted(Self.dateFormatter)
        encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .formatted(Self.dateFormatter)
    }

    // MARK: - Endpoints

    func status() async throws -> SystemStatus {
        try await get("/api/status")
    }

    func weather() async throws -> WeatherInfo {
        try await get("/api/weather")
    }

    func schedules() async throws -> [Schedule] {
        try await get("/api/schedules")
    }

    @discardableResult
    func createSchedule(_ payload: SchedulePayload) async throws -> Schedule {
        try await send("/api/schedules", method: "POST", body: payload)
    }

    @discardableResult
    func updateSchedule(id: Int, _ payload: SchedulePayload) async throws -> Schedule {
        try await send("/api/schedules/\(id)", method: "PUT", body: payload)
    }

    func deleteSchedule(id: Int) async throws {
        _ = try await data(path: "/api/schedules/\(id)", method: "DELETE", body: nil)
    }

    func water(zone: Zone, durationMin: Int) async throws {
        struct Body: Encodable { let zone: Zone; let durationMin: Int }
        let body = try encoder.encode(Body(zone: zone, durationMin: durationMin))
        _ = try await data(path: "/api/water", method: "POST", body: body)
    }

    func stop(zone: Zone) async throws {
        struct Body: Encodable { let zone: Zone }
        let body = try encoder.encode(Body(zone: zone))
        _ = try await data(path: "/api/stop", method: "POST", body: body)
    }

    func logs(limit: Int = 100) async throws -> [LogEntry] {
        try await get("/api/logs?limit=\(limit)")
    }

    /// Verbindungstest fuer die Einstellungen; liefert die erreichte Route.
    func testConnection() async throws -> Route {
        _ = try await status()
        guard let route = activeRoute else { throw DripError.unreachable }
        return route
    }

    // MARK: - Core

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let data = try await data(path: path, method: "GET", body: nil)
        return try decoder.decode(T.self, from: data)
    }

    private func send<B: Encodable, T: Decodable>(_ path: String, method: String, body: B) async throws -> T {
        let bodyData = try encoder.encode(body)
        let data = try await data(path: path, method: method, body: bodyData)
        return try decoder.decode(T.self, from: data)
    }

    private func data(path: String, method: String, body: Data?) async throws -> Data {
        var routes: [Route] = preferredRoute == .local ? [.local, .remote] : [.remote, .local]
        routes = routes.filter { baseURL(for: $0) != nil }
        guard !routes.isEmpty, !config.apiKey.isEmpty else { throw DripError.notConfigured }

        var lastError: Error = DripError.unreachable
        for route in routes {
            guard let base = baseURL(for: route) else { continue }
            do {
                let result = try await perform(base: base, path: path, method: method,
                                               body: body,
                                               timeout: route == .local ? 3 : 15)
                activeRoute = route
                preferredRoute = route
                return result
            } catch let error as DripError {
                // API hat geantwortet (Auth/Validierung) -> kein Routen-Problem, nicht weiterprobieren
                switch error {
                case .unauthorized, .http:
                    activeRoute = route
                    throw error
                default:
                    lastError = error
                }
            } catch {
                lastError = error
            }
        }
        activeRoute = nil
        throw lastError
    }

    private func perform(base: URL, path: String, method: String, body: Data?, timeout: TimeInterval) async throws -> Data {
        guard let url = URL(string: base.absoluteString + path) else { throw DripError.unreachable }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: timeout)
        request.httpMethod = method
        request.setValue(AppConfig.shared.apiKey, forHTTPHeaderField: "X-API-Key")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw DripError.unreachable }
        switch http.statusCode {
        case 200...299:
            return data
        case 401:
            throw DripError.unauthorized
        default:
            struct ApiError: Decodable { let error: String? }
            let message = (try? decoder.decode(ApiError.self, from: data))?.error
            throw DripError.http(http.statusCode, message)
        }
    }

    private func baseURL(for route: Route) -> URL? {
        let raw = route == .local ? config.localURL : config.remoteURL
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        let withScheme = trimmed.contains("://") ? trimmed : "http://" + trimmed
        let normalized = withScheme.hasSuffix("/") ? String(withScheme.dropLast()) : withScheme
        return URL(string: normalized)
    }
}
