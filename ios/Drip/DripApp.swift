import SwiftUI

@main
struct DripApp: App {
    @Environment(\.scenePhase) private var scenePhase

    init() {
        RefreshManager.register()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .background {
                RefreshManager.scheduleNextRefresh()
            }
        }
    }
}
