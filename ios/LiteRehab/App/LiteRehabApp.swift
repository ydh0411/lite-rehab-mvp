import Spezi
import SwiftUI

@main
struct LiteRehabApp: App {
    @UIApplicationDelegateAdaptor(LiteRehabAppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            AppRootView()
                .spezi(appDelegate)
        }
    }
}
