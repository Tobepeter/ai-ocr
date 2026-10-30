import Foundation
import Vision
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
request.usesLanguageCorrection = true
request.minimumTextHeight = 0
let start = Date()
do {
    try VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1])).perform([request])
    let text = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    let result: [String: Any] = ["text": text, "seconds": Date().timeIntervalSince(start), "load_seconds": 0]
    try JSONSerialization.data(withJSONObject: result).write(to: URL(fileURLWithPath: CommandLine.arguments[2]))
} catch {
    fputs("\(error)\n", stderr)
    exit(1)
}
