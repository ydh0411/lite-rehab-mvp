import SwiftUI

struct AcknowledgementsView: View {
    @State private var notices = "Loading acknowledgements…"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Label("Open source software", systemImage: "shippingbox")
                    .font(.title2.bold())
                Text("LiteRehab builds on carefully pinned open-source projects. License notices are reproduced below.")
                    .foregroundStyle(.secondary)
                Text(notices)
                    .font(.footnote.monospaced())
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .liteRehabCard()
            }
            .padding()
        }
        .background(Color(uiColor: .systemGroupedBackground))
        .navigationTitle("Open Source")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            guard let url = Bundle.main.url(forResource: "THIRD_PARTY_NOTICES", withExtension: "md"),
                  let text = try? String(contentsOf: url, encoding: .utf8) else {
                notices = "Third-party notices could not be loaded."
                return
            }
            notices = text
        }
    }
}
