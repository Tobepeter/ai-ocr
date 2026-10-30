import Foundation
import Vision
import AppKit
let args=CommandLine.arguments
let manifest=URL(fileURLWithPath:args[1]), folder=URL(fileURLWithPath:args[2]), root=args[3], phase=args[4]
try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
let all=try JSONSerialization.jsonObject(with:Data(contentsOf:manifest)) as! [String:Any]
let rows=(all["cases"] as! [[String:Any]]).filter { ($0["phase"] as! String)==phase }
func write(_ name:String,_ value:[String:Any]) throws {
 let data=try JSONSerialization.data(withJSONObject:value,options:[.prettyPrinted,.sortedKeys])
 try data.write(to:folder.appendingPathComponent(name+".json"),options:.atomic)
}
func infer(_ path:String) throws -> [String:Any] {
 let request=VNRecognizeTextRequest()
 request.recognitionLevel = .accurate
 request.recognitionLanguages=["zh-Hans","zh-Hant","en-US"]
 request.usesLanguageCorrection=true
 request.minimumTextHeight=0
 let handler=VNImageRequestHandler(url:URL(fileURLWithPath:path),options:[:])
 try handler.perform([request])
 let observations=request.results ?? []
 let lines=observations.compactMap { $0.topCandidates(1).first?.string }
 let boxes=observations.map { o -> [String:Any] in
  let b=o.boundingBox
  return ["text":o.topCandidates(1).first?.string ?? "","confidence":o.topCandidates(1).first?.confidence ?? 0,"box":[b.minX,b.minY,b.width,b.height]]
 }
 return ["text":lines.joined(separator:"\n"),"raw":boxes,"status":"ok"]
}
let started=Date();let req=VNRecognizeTextRequest();req.recognitionLevel = .accurate
try write("setup",["engine":"vision","os":ProcessInfo.processInfo.operatingSystemVersionString,"revision":req.revision,"supported_languages":try req.supportedRecognitionLanguages(),"config":["recognitionLevel":"accurate","languages":["zh-Hans","zh-Hant","en-US"],"device":"automatic","languageCorrection":true,"minimumTextHeight":0]])
let warmupPath = args.count > 5 ? args[5] : "data/outputs/bench-20261030/inputs/omni-003.png"
let warm=Date();_ = try infer(root+"/"+warmupPath)
try write("warmup",["seconds":Date().timeIntervalSince(warm),"status":"ok"])
var summaries=[[String:Any]]()
for row in rows {
 let id=row["case_id"] as! String
 try write("current",["case_id":id])
 let t=Date();var result:[String:Any]
 do { result=try autoreleasepool { try infer(root+"/"+(row["prepared_path"] as! String)) } }
 catch { result=["text":"","status":"error","error":String(describing:error)] }
 result["seconds"]=Date().timeIntervalSince(t);result["case_id"]=id;result["prepared_sha256"]=row["prepared_sha256"]
 try write(id,result);summaries.append(["case_id":id,"seconds":result["seconds"]!,"status":result["status"]!])
 print(id,result["status"]!,result["seconds"]!);fflush(stdout)
}
try write("summary",["engine":"vision","complete":true,"count":rows.count,"total_seconds":Date().timeIntervalSince(started),"results":summaries])
