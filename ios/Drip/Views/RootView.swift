import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            Tab("Übersicht", systemImage: "drop.fill") {
                DashboardView()
            }
            Tab("Pläne", systemImage: "calendar") {
                SchedulesView()
            }
            Tab("Verlauf", systemImage: "list.bullet.rectangle") {
                LogsView()
            }
            Tab("Einstellungen", systemImage: "gearshape") {
                SettingsView()
            }
        }
        .tabBarMinimizeBehavior(.onScrollDown)
    }
}

#Preview {
    RootView()
}
