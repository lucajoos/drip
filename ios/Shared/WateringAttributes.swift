import ActivityKit
import Foundation

/// Live Activity fuer einen laufenden Giessvorgang.
struct WateringAttributes: ActivityAttributes {
    struct ContentState: Codable, Hashable {
        /// Zeitpunkt, an dem das Giessen endet
        var endDate: Date
    }

    var zone: Zone
    var startDate: Date
    var totalSeconds: Int
}
