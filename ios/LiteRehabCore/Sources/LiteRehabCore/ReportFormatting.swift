import Foundation


public enum ReportFormatting {
    public static func percent(_ value: Double?) -> String {
        guard let value else { return "Not available" }
        return formatted(value, decimals: 1) + "%"
    }

    public static func ecgCompleteness(_ value: Double?) -> String {
        guard let value else { return "Not recorded" }
        return formatted(value, decimals: 0) + "%"
    }

    public static func degrees(_ value: Double?) -> String {
        guard let value else { return "Not available" }
        return formatted(value, decimals: 1) + "°"
    }

    public static func bpm(_ value: Double?) -> String {
        guard let value else { return "Not available" }
        return formatted(value, decimals: 0)
    }

    public static func duration(_ value: Double?) -> String {
        guard let value else { return "Not available" }
        let seconds = max(0, Int(value.rounded()))
        if seconds < 60 {
            return "\(seconds)s"
        }
        return String(format: "%dm %02ds", seconds / 60, seconds % 60)
    }

    private static func formatted(_ value: Double, decimals: Int) -> String {
        String(
            format: "%.*f",
            locale: Locale(identifier: "en_US_POSIX"),
            decimals,
            value
        )
    }
}
