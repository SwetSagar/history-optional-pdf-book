// OCR a scanned PDF into per-page text using Apple's Vision framework.
//
// Zero external dependencies: PDFKit renders each page, Vision recognises the
// text, and the result is written as JSON with page numbers preserved so a
// citation can point at an actual page.
//
//   swiftc -O pipeline/ocr/ocr.swift -o pipeline/ocr/ocr
//   ./pipeline/ocr/ocr <input.pdf> <output.json> [scale]

import Foundation
import PDFKit
import Vision
import CoreGraphics

struct PageText: Codable {
    let page: Int
    let text: String
    let confidence: Double
}

func render(_ page: PDFPage, scale: CGFloat) -> CGImage? {
    let bounds = page.bounds(for: .mediaBox)
    let w = Int(bounds.width * scale)
    let h = Int(bounds.height * scale)
    guard w > 0, h > 0, w < 20000, h < 20000 else { return nil }
    guard let ctx = CGContext(
        data: nil, width: w, height: h,
        bitsPerComponent: 8, bytesPerRow: 0,
        space: CGColorSpaceCreateDeviceGray(),
        bitmapInfo: CGImageAlphaInfo.none.rawValue
    ) else { return nil }

    ctx.setFillColor(gray: 1.0, alpha: 1.0)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: -bounds.origin.x, y: -bounds.origin.y)
    page.draw(with: .mediaBox, to: ctx)
    return ctx.makeImage()
}

func recognise(_ image: CGImage) -> (String, Double) {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["en-US"]

    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    do {
        try handler.perform([request])
    } catch {
        return ("", 0)
    }
    guard let obs = request.results, !obs.isEmpty else { return ("", 0) }

    var lines: [String] = []
    var total: Double = 0
    for o in obs {
        guard let best = o.topCandidates(1).first else { continue }
        lines.append(best.string)
        total += Double(best.confidence)
    }
    return (lines.joined(separator: "\n"), obs.isEmpty ? 0 : total / Double(obs.count))
}

// ---------------------------------------------------------------- main

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: ocr <input.pdf> <output.json> [scale]\n".data(using: .utf8)!)
    exit(2)
}
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])
let scale = CGFloat(args.count > 3 ? Double(args[3]) ?? 2.0 : 2.0)

guard let doc = PDFDocument(url: inURL) else {
    FileHandle.standardError.write("cannot open \(inURL.path)\n".data(using: .utf8)!)
    exit(1)
}

let count = doc.pageCount
var results = [PageText?](repeating: nil, count: count)
let lock = NSLock()
var done = 0
let name = inURL.lastPathComponent

// Vision handlers are independent, so pages parallelise cleanly.
DispatchQueue.concurrentPerform(iterations: count) { i in
    guard let page = doc.page(at: i) else {
        lock.lock(); results[i] = PageText(page: i + 1, text: "", confidence: 0); lock.unlock()
        return
    }

    // Prefer the PDF's own text layer: it is the publisher's text, so it is exact
    // where OCR only approximates. Fall back to Vision for scanned pages.
    var text = ""
    var conf = 0.0
    if let embedded = page.string?.trimmingCharacters(in: .whitespacesAndNewlines),
       embedded.count > 120 {
        text = embedded
        conf = 1.0
    } else if let img = render(page, scale: scale) {
        (text, conf) = recognise(img)
    }

    lock.lock()
    results[i] = PageText(page: i + 1, text: text, confidence: conf)
    done += 1
    if done % 25 == 0 {
        FileHandle.standardError.write("  \(name): \(done)/\(count)\n".data(using: .utf8)!)
    }
    lock.unlock()
}

let pages = results.compactMap { $0 }.sorted { $0.page < $1.page }
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
try encoder.encode(pages).write(to: outURL)

let chars = pages.reduce(0) { $0 + $1.text.count }
let empty = pages.filter { $0.text.count < 20 }.count
let avg = pages.isEmpty ? 0 : pages.reduce(0.0) { $0 + $1.confidence } / Double(pages.count)
print("\(name)|\(pages.count)|\(chars)|\(empty)|\(String(format: "%.3f", avg))")
