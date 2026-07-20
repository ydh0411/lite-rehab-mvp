import SwiftUI

struct StartSessionSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var participantID = ""
    @State private var errorMessage: String?
    let onStart: (String) async throws -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Participant") {
                    TextField("Participant ID", text: $participantID)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    Text("Use a study identifier, not a participant's full name.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let errorMessage {
                    Section {
                        Text(errorMessage).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Start Session")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Start") {
                        Task {
                            do {
                                try await onStart(participantID)
                                dismiss()
                            } catch {
                                errorMessage = error.localizedDescription
                            }
                        }
                    }
                    .disabled(participantID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}
