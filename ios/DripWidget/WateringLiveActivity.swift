import ActivityKit
import SwiftUI
import WidgetKit

struct WateringLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: WateringAttributes.self) { context in
            // Sperrbildschirm / Banner
            HStack(spacing: 14) {
                ringView(context)
                    .frame(width: 44, height: 44)
                VStack(alignment: .leading, spacing: 2) {
                    Label(context.attributes.zone.displayName,
                          systemImage: context.attributes.zone.symbolName)
                        .font(.headline)
                    Text("Gießt gerade")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(timerInterval: Date.now...context.state.endDate, countsDown: true)
                    .font(.title2.weight(.semibold).monospacedDigit())
                    .frame(maxWidth: 70)
                    .multilineTextAlignment(.trailing)
            }
            .padding()
            .activityBackgroundTint(nil)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Label(context.attributes.zone.displayName,
                          systemImage: context.attributes.zone.symbolName)
                        .font(.headline)
                        .padding(.leading, 4)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Text(timerInterval: Date.now...context.state.endDate, countsDown: true)
                        .font(.title3.weight(.semibold).monospacedDigit())
                        .frame(maxWidth: 64)
                        .multilineTextAlignment(.trailing)
                        .padding(.trailing, 4)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    ProgressView(timerInterval: context.attributes.startDate...context.state.endDate,
                                 countsDown: true) {
                        EmptyView()
                    } currentValueLabel: {
                        EmptyView()
                    }
                    .tint(.blue)
                    .padding(.horizontal, 4)
                }
            } compactLeading: {
                Image(systemName: "drop.fill")
                    .foregroundStyle(.blue)
            } compactTrailing: {
                Text(timerInterval: Date.now...context.state.endDate, countsDown: true)
                    .monospacedDigit()
                    .frame(maxWidth: 44)
                    .multilineTextAlignment(.trailing)
                    .foregroundStyle(.blue)
            } minimal: {
                Image(systemName: "drop.fill")
                    .foregroundStyle(.blue)
            }
        }
    }

    @ViewBuilder
    private func ringView(_ context: ActivityViewContext<WateringAttributes>) -> some View {
        ProgressView(timerInterval: context.attributes.startDate...context.state.endDate,
                     countsDown: true) {
            EmptyView()
        } currentValueLabel: {
            Image(systemName: "drop.fill")
                .font(.system(size: 13))
                .foregroundStyle(.blue)
        }
        .progressViewStyle(.circular)
        .tint(.blue)
    }
}
