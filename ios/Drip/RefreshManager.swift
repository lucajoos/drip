import BackgroundTasks
import UserNotifications
import WidgetKit

/// Hintergrund-Abgleich: iOS weckt die App opportunistisch, wir holen die Logs
/// und melden neue Ereignisse als lokale Mitteilung.
enum RefreshManager {
    static let taskIdentifier = "de.lucajoos.drip.refresh"

    static func register() {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: taskIdentifier, using: nil) { task in
            guard let refreshTask = task as? BGAppRefreshTask else {
                task.setTaskCompleted(success: false)
                return
            }
            handle(refreshTask)
        }
    }

    static func scheduleNextRefresh() {
        let request = BGAppRefreshTaskRequest(identifier: taskIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 30 * 60)
        try? BGTaskScheduler.shared.submit(request)
    }

    static func requestAuthorization() {
        UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
    }

    private static func handle(_ task: BGAppRefreshTask) {
        scheduleNextRefresh()

        let work = Task { @MainActor in
            await checkForNewEvents()
            WidgetCenter.shared.reloadAllTimelines()
            task.setTaskCompleted(success: true)
        }
        task.expirationHandler = {
            work.cancel()
            task.setTaskCompleted(success: false)
        }
    }

    @MainActor
    static func checkForNewEvents() async {
        let config = AppConfig.shared
        guard config.notificationsEnabled, config.isConfigured else { return }
        guard let entries = try? await DripClient.shared.logs(limit: 30) else { return }

        let lastSeen = config.lastSeenLogTs
        // Erster Lauf: nur Stand merken, nicht die komplette Historie melden
        guard lastSeen > 0 else {
            config.lastSeenLogTs = entries.map(\.ts).max() ?? 0
            return
        }

        let fresh = entries
            .filter { $0.ts > lastSeen }
            .filter { ["water_end", "skip_rain", "weather_error"].contains($0.event) }
            .sorted { $0.ts < $1.ts }

        for entry in fresh {
            let content = UNMutableNotificationContent()
            content.title = entry.zone?.displayName ?? "Drip"
            content.body = entry.title
            content.sound = .default
            let request = UNNotificationRequest(
                identifier: entry.id,
                content: content,
                trigger: nil
            )
            try? await UNUserNotificationCenter.current().add(request)
        }

        if let maxTs = entries.map(\.ts).max(), maxTs > lastSeen {
            config.lastSeenLogTs = maxTs
        }
    }
}
