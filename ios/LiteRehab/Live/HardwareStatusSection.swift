import SwiftUI

struct HardwareStatusSection: View {
    let readiness: HardwareReadiness

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Equipment check")
                .font(.headline)
                .padding(.bottom, 12)

            ForEach(Array(readiness.checks.enumerated()), id: \.element.id) { index, check in
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: symbol(for: check))
                        .font(.title3)
                        .foregroundStyle(color(for: check))
                        .frame(width: 28, height: 28)
                        .accessibilityHidden(true)
                    VStack(alignment: .leading, spacing: 3) {
                        HStack {
                            Text(check.title)
                                .font(.body.weight(.semibold))
                            Spacer()
                            Text(statusText(for: check))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(color(for: check))
                        }
                        Text(check.detail)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(.vertical, 11)
                .accessibilityElement(children: .combine)

                if index < readiness.checks.count - 1 {
                    Divider().padding(.leading, 40)
                }
            }
        }
        .liteRehabCard()
    }

    private func statusText(for check: HardwareReadiness.Check) -> String {
        if check.state == .ready { return "Ready" }
        return check.requirement == .required ? "Required" : "Optional"
    }

    private func symbol(for check: HardwareReadiness.Check) -> String {
        if check.state == .ready { return "checkmark.circle.fill" }
        return check.requirement == .required ? "xmark.octagon.fill" : "exclamationmark.triangle.fill"
    }

    private func color(for check: HardwareReadiness.Check) -> Color {
        if check.state == .ready { return LiteRehabStyle.success }
        return check.requirement == .required ? LiteRehabStyle.danger : LiteRehabStyle.warning
    }
}
