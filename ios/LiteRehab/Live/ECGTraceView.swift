import SwiftUI

struct ECGTraceView: View {
    let samples: [Double]

    var body: some View {
        Canvas { context, size in
            guard samples.count > 1,
                  let minimum = samples.min(),
                  let maximum = samples.max() else { return }
            let range = max(maximum - minimum, 1)
            var path = Path()
            for (index, sample) in samples.enumerated() {
                let x = CGFloat(index) / CGFloat(samples.count - 1) * size.width
                let normalized = (sample - minimum) / range
                let y = size.height - CGFloat(normalized) * size.height
                if index == 0 { path.move(to: CGPoint(x: x, y: y)) }
                else { path.addLine(to: CGPoint(x: x, y: y)) }
            }
            context.stroke(path, with: .color(.red), lineWidth: 1.6)
        }
        .frame(height: 88)
        .background(Color.red.opacity(0.04), in: RoundedRectangle(cornerRadius: 12))
        .accessibilityLabel("Live ECG waveform")
        .accessibilityValue(samples.isEmpty ? "No samples" : "\(samples.count) samples")
    }
}
