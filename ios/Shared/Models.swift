import Foundation

enum Zone: String, Codable, CaseIterable, Identifiable, Sendable {
    case herbs
    case beds

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .herbs: "Kräuter"
        case .beds: "Beete"
        }
    }

    var symbolName: String {
        switch self {
        case .herbs: "leaf.fill"
        case .beds: "tree.fill"
        }
    }
}

struct SystemStatus: Codable, Sendable {
    var time: Date?
    var timeSource: String
    var rtcPresent: Bool
    var uptimeS: Int
    var rssi: Int
    var freeHeap: Int
    var zones: [ZoneStatus]

    func zone(_ zone: Zone) -> ZoneStatus? {
        zones.first { $0.zone == zone }
    }
}

struct ZoneStatus: Codable, Identifiable, Sendable {
    var zone: Zone
    var active: Bool
    var cause: String?
    var remainingS: Int?
    var durationS: Int?
    var lastRunEnd: Date?
    var lastRunDurationS: Int?
    var lastScheduledRun: Date?
    var nextScheduledRun: Date?

    var id: String { zone.rawValue }
}

enum Rhythm: String, Codable, CaseIterable, Sendable {
    case daily
    case everyNDays = "every_n_days"
    case weekdays
}

enum Weekday: String, Codable, CaseIterable, Sendable {
    case mon, tue, wed, thu, fri, sat, sun

    var shortName: String {
        switch self {
        case .mon: "Mo"
        case .tue: "Di"
        case .wed: "Mi"
        case .thu: "Do"
        case .fri: "Fr"
        case .sat: "Sa"
        case .sun: "So"
        }
    }

    var fullName: String {
        switch self {
        case .mon: "Montag"
        case .tue: "Dienstag"
        case .wed: "Mittwoch"
        case .thu: "Donnerstag"
        case .fri: "Freitag"
        case .sat: "Samstag"
        case .sun: "Sonntag"
        }
    }
}

struct RainSkip: Codable, Sendable, Equatable {
    var enabled: Bool
    var thresholdMm: Double
}

struct Schedule: Codable, Identifiable, Sendable {
    var id: Int
    var zone: Zone
    var time: String
    var rhythm: Rhythm
    var n: Int?
    var weekdays: [Weekday]?
    var durationMin: Int
    var enabled: Bool
    var rainSkip: RainSkip
    var lastRun: Date?
    var nextRun: Date?

    var rhythmSummary: String {
        switch rhythm {
        case .daily:
            return "Täglich"
        case .everyNDays:
            let n = n ?? 1
            return n == 1 ? "Täglich" : "Alle \(n) Tage"
        case .weekdays:
            let days = Weekday.allCases.filter { weekdays?.contains($0) == true }
            return days.map(\.shortName).joined(separator: ", ")
        }
    }
}

/// Body für POST/PUT /api/schedules – enthält nur die Felder, die die Firmware erwartet.
struct SchedulePayload: Codable, Sendable {
    var zone: Zone
    var time: String
    var rhythm: Rhythm
    var n: Int?
    var weekdays: [Weekday]?
    var durationMin: Int
    var enabled: Bool
    var rainSkip: RainSkip

    init(zone: Zone, time: String, rhythm: Rhythm, n: Int? = nil,
         weekdays: [Weekday]? = nil, durationMin: Int, enabled: Bool,
         rainSkip: RainSkip) {
        self.zone = zone
        self.time = time
        self.rhythm = rhythm
        self.n = n
        self.weekdays = weekdays
        self.durationMin = durationMin
        self.enabled = enabled
        self.rainSkip = rainSkip
    }

    init(from schedule: Schedule) {
        self.init(zone: schedule.zone, time: schedule.time,
                  rhythm: schedule.rhythm, n: schedule.n,
                  weekdays: schedule.weekdays,
                  durationMin: schedule.durationMin,
                  enabled: schedule.enabled, rainSkip: schedule.rainSkip)
    }
}

struct LogEntry: Codable, Identifiable, Sendable {
    var ts: Int
    var time: Date
    var event: String
    var zone: Zone?
    var cause: String?
    var durationS: Int?
    var precipMm: Double?
    var note: String?

    var id: String { "\(ts)-\(event)-\(zone?.rawValue ?? "-")" }

    var title: String {
        let zoneName = zone?.displayName ?? "System"
        switch event {
        case "water_start":
            return "\(zoneName): Gießen gestartet"
        case "water_end":
            let minutes = ((durationS ?? 0) + 30) / 60
            let source = cause == "schedule" ? "geplant" : "manuell"
            if let d = durationS, d < 60 {
                return "\(zoneName): gegossen · \(d) s (\(source))"
            }
            return "\(zoneName): gegossen · \(minutes) min (\(source))"
        case "skip_rain":
            let mm = precipMm.map { String(format: "%.1f", $0) } ?? "?"
            return "\(zoneName): übersprungen, \(mm) mm Regen"
        case "skip_busy":
            return "\(zoneName): übersprungen, gießt bereits"
        case "weather_error":
            return "Wetterabruf fehlgeschlagen, trotzdem gegossen"
        case "boot":
            return "Controller neu gestartet"
        case "schedule_created":
            return "Gießplan erstellt (\(zoneName))"
        case "error":
            return note ?? "Fehler"
        default:
            return event
        }
    }

    var symbolName: String {
        switch event {
        case "water_start", "water_end": "drop.fill"
        case "skip_rain": "cloud.rain.fill"
        case "skip_busy": "clock.badge.exclamationmark"
        case "weather_error", "error": "exclamationmark.triangle.fill"
        case "boot": "power"
        case "schedule_created": "calendar.badge.plus"
        default: "info.circle"
        }
    }
}

struct WeatherInfo: Codable, Sendable {
    var ok: Bool
    var past24Mm: Double?
    var next12Mm: Double?
    var fetchedAt: Date?
    var error: String?
}
