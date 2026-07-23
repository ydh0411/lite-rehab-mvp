import SwiftUI
import UIKit

struct SessionCountdownView: View {
    let remaining: Int
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var scale = 0.86

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: "scope")
                .font(.system(size: 52, weight: .semibold))
                .foregroundStyle(LiteRehabStyle.accent)
                .accessibilityHidden(true)
            Text("\(remaining)")
                .font(.system(size: 112, weight: .bold, design: .rounded))
                .monospacedDigit()
                .contentTransition(.numericText())
                .scaleEffect(scale)
                .accessibilityLabel("Starting in \(remaining)")
            VStack(spacing: 8) {
                Text("Preparing your baseline")
                    .font(.title2.bold())
                Text("Stay still and keep the sensor in position.")
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            Spacer()
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onAppear { animateAndAnnounce() }
        .onChange(of: remaining) { _, _ in animateAndAnnounce() }
    }

    private func animateAndAnnounce() {
        UIAccessibility.post(notification: .announcement, argument: "Starting in \(remaining)")
        guard !reduceMotion else {
            scale = 1
            return
        }
        scale = 0.86
        withAnimation(.spring(response: 0.35, dampingFraction: 0.68)) {
            scale = 1
        }
    }
}
