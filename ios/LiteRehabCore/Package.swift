// swift-tools-version: 6.0

import PackageDescription


let package = Package(
    name: "LiteRehabCore",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(name: "LiteRehabCore", targets: ["LiteRehabCore"]),
    ],
    targets: [
        .target(name: "LiteRehabCore"),
        .testTarget(
            name: "LiteRehabCoreTests",
            dependencies: ["LiteRehabCore"]
        ),
    ]
)
