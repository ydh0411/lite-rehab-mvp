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
                .lineLimit(2)
                .minimumScaleFactor(0.75)
        }
        .frame(maxWidth: .infinity, minHeight: 64, alignment: .leading)
        .liteRehabCard()
        .accessibilityElement(children: .combine)
    }
}
