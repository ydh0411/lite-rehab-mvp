import SwiftUI

struct AcknowledgementsView: View {
    @State private var notices = "Loading acknowledgements…"

    var body: some View {
        ScrollView {
            Text(notices)
                .font(.footnote.monospaced())
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
        }
        .navigationTitle("Acknowledgements")
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
