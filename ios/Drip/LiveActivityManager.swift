import ActivityKit
import Foundation

/// Startet/aktualisiert/beendet Live Activities anhand des Controller-Status.
/// Wird bei jedem Status-Abruf aufgerufen und deckt damit auch geplante
/// Giessvorgaenge ab, solange die App offen ist.
@MainActor
enum LiveActivityManager {
    static func sync(with status: SystemStatus, fetchedAt: Date) {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }

        for zoneStatus in status.zones {
            let existing = Activity<WateringAttributes>.activities
                .filter { $0.attributes.zone == zoneStatus.zone }

            if zoneStatus.active, let remaining = zoneStatus.remainingS {
                let endDate = fetchedAt.addingTimeInterval(TimeInterval(remaining))
                let state = WateringAttributes.ContentState(endDate: endDate)
                let content = ActivityContent(state: state, staleDate: endDate)

                if let activity = existing.first {
                    Task { await activity.update(content) }
                } else {
                    let attributes = WateringAttributes(
                        zone: zoneStatus.zone,
                        startDate: fetchedAt.addingTimeInterval(
                            TimeInterval(-((zoneStatus.durationS ?? remaining) - remaining))),
                        totalSeconds: zoneStatus.durationS ?? remaining
                    )
                    _ = try? Activity.request(attributes: attributes, content: content)
                }
            } else {
                for activity in existing {
                    Task {
                        await activity.end(activity.content, dismissalPolicy: .immediate)
                    }
                }
            }
        }
    }
}
