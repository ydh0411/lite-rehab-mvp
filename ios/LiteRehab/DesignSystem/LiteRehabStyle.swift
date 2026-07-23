import SwiftUI

enum LiteRehabStyle {
    static let accent = Color.accentColor
    static let success = Color.green
    static let warning = Color.orange
    static let danger = Color.red

    static let cardShape = RoundedRectangle(cornerRadius: 18, style: .continuous)
}

extension View {
    func liteRehabCard() -> some View {
        padding(16)
            .background(Color(uiColor: .secondarySystemGroupedBackground), in: LiteRehabStyle.cardShape)
            .overlay {
                LiteRehabStyle.cardShape.stroke(
                    Color(uiColor: .separator).opacity(0.25),
                    lineWidth: 0.5
                )
            }
    }
}
