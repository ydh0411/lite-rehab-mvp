@preconcurrency import AVFoundation
import SwiftUI

struct QRCodeScannerView: UIViewControllerRepresentable {
    let onCode: @MainActor (String) -> Void
    let onError: @MainActor (Error) -> Void

    func makeUIViewController(context: Context) -> ScannerViewController {
        let controller = ScannerViewController()
        controller.onCode = onCode
        controller.onError = onError
        return controller
    }

    func updateUIViewController(_ uiViewController: ScannerViewController, context: Context) {}
}

final class ScannerViewController: UIViewController, @preconcurrency AVCaptureMetadataOutputObjectsDelegate {
    var onCode: (@MainActor (String) -> Void)?
    var onError: (@MainActor (Error) -> Void)?
    private let session = AVCaptureSession()
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var deliveredCode = false

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        if ProcessInfo.processInfo.arguments.contains("-ui-testing") {
            return
        }
        configureCapture()
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        deliveredCode = false
        if !session.isRunning {
            DispatchQueue.global(qos: .userInitiated).async { [session] in
                session.startRunning()
            }
        }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if session.isRunning {
            DispatchQueue.global(qos: .userInitiated).async { [session] in
                session.stopRunning()
            }
        }
    }

    private func configureCapture() {
        guard let camera = AVCaptureDevice.default(for: .video) else {
            report(ScannerError.cameraUnavailable)
            return
        }
        do {
            let input = try AVCaptureDeviceInput(device: camera)
            guard session.canAddInput(input) else {
                throw ScannerError.cameraUnavailable
            }
            session.addInput(input)
            let output = AVCaptureMetadataOutput()
            guard session.canAddOutput(output) else {
                throw ScannerError.cameraUnavailable
            }
            session.addOutput(output)
            output.setMetadataObjectsDelegate(self, queue: .main)
            output.metadataObjectTypes = [.qr]

            let layer = AVCaptureVideoPreviewLayer(session: session)
            layer.videoGravity = .resizeAspectFill
            view.layer.addSublayer(layer)
            previewLayer = layer
        } catch {
            report(error)
        }
    }

    func metadataOutput(
        _ output: AVCaptureMetadataOutput,
        didOutput metadataObjects: [AVMetadataObject],
        from connection: AVCaptureConnection
    ) {
        guard !deliveredCode,
              let readable = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              let value = readable.stringValue else {
            return
        }
        deliveredCode = true
        session.stopRunning()
        Task { @MainActor [onCode] in
            onCode?(value)
        }
    }

    private func report(_ error: Error) {
        Task { @MainActor [onError] in
            onError?(error)
        }
    }
}

enum ScannerError: LocalizedError {
    case cameraUnavailable

    var errorDescription: String? {
        "The camera is unavailable. Check Camera access in Settings."
    }
}
