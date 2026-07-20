import SwiftUI

enum LiteRehabStyle {
    static let accent = Color.indigo
    static let success = Color.green
    static let warning = Color.orange
    static let danger = Color.red

    static let cardShape = RoundedRectangle(cornerRadius: 18, style: .continuous)
}

extension View {
    func liteRehabCard() -> some View {
        padding(16)
            .background(.background, in: LiteRehabStyle.cardShape)
            .overlay {
                LiteRehabStyle.cardShape.stroke(.quaternary)
            }
    }
}
