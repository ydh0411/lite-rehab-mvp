import SwiftUI

struct MetricCard: View {
    let title: String
    let value: String
    var systemImage: String? = nil
    var tint: Color = .indigo

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Text(title)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.secondary)
                Spacer()
                if let systemImage {
                    Image(systemName: systemImage).foregroundStyle(tint)
                }
            }
            Text(value)
                .font(.title3.bold())
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .liteRehabCard()
        .accessibilityElement(children: .combine)
    }
}
