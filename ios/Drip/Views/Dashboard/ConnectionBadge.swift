import SwiftUI

struct ConnectionBadge: View {
    let route: Route?

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(route == nil ? Color.red : .green)
                .frame(width: 7, height: 7)
            Text(route?.displayName ?? "Offline")
                .font(.caption.weight(.medium))
        }
        .padding(.horizontal, 4)
    }
}
