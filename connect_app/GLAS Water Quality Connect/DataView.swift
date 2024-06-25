//
//  DataView.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/19/24.
//

import SwiftUI
import SceneKit
import Charts

struct DataView: View {
    @EnvironmentObject var sharedState: SharedState
    @State private var runtimeData: Int?
    @State private var soundLevelData: [DataEntry] = []
    @State private var waterLevelData: [DataEntry] = []
    @State private var eulerXData: Double?
    @State private var eulerYData: Double?
    @State private var eulerZData: Double?
    @State private var rotationalChangeData: [DataEntry] = []
    @State private var scene: SCNScene?
    
    var body: some View {
        ScrollView {
            VStack {
                HStack {
                    Text("Iterations")
                        .font(.title2)
                        .monospaced()
                    Spacer()
                }
                HStack {
                    Text(runtimeData != nil ? String(runtimeData!) : "...")
                        .foregroundStyle(.gray)
                        .monospaced()
                    Spacer()
                }
//                Chart {
//                    ForEach(Array(runtimeData.enumerated()), id: \.0.self) { (idx, entry) in
//                        LineMark(
//                            x: .value("ID", idx),
//                            y: .value("Value", entry.value as! Double)
//                        )
//                    }
//                }
//                .chartYAxis {
//                    AxisMarks(position: .leading)
//                }
//                .chartYScale(domain: .automatic(includesZero: false))
//                .frame(height: 300)
            }
            .padding(.top, 10)
            .padding(.horizontal, 29)
            .padding(.bottom)
                         
             VStack {
                 HStack {
                     Text("Sound Level")
                         .font(.title2)
                         .monospaced()
                     Spacer()
                 }
                 Chart {
                     ForEach(Array(soundLevelData.enumerated()), id: \.0.self) { (idx, entry) in
                         LineMark(
                             x: .value("ID", idx),
                             y: .value("Value", entry.value as! Double)
                         )
                     }
                 }
                 .chartYAxis {
                     AxisMarks(position: .leading)
                 }
                 .chartYScale(domain: 0...3)
                 .frame(height: 300)
             }
             .padding(.horizontal, 29)
             .padding(.bottom)
            
            VStack {
                HStack {
                    Text("Water Level")
                        .font(.title2)
                        .monospaced()
                    Spacer()
                }
                Chart {
                    ForEach(Array(waterLevelData.enumerated()), id: \.0.self) { (idx, entry) in
                        LineMark(
                            x: .value("ID", idx),
                            y: .value("Value", entry.value as! Int)
                        )
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading)
                }
                .chartYScale(domain: 0...30000)
                .frame(height: 300)
            }
            .padding(.horizontal, 29)
            .padding(.bottom)
            
            VStack {
                HStack {
                    Text("9D Orientation")
                        .font(.title2)
                        .monospaced()
                    Spacer()
                }
                
                if scene != nil {
                    HStack {
                        SceneView (
                            scene: scene,
                            pointOfView: scene!.rootNode.childNode(withName: "camera", recursively: true),
                            options: [.autoenablesDefaultLighting]
                        )
                        .frame(height: 500)
                        .cornerRadius(15)
                        .padding(.bottom)
                        
                        Spacer()
                    }
                }
            }
            .padding(.horizontal, 29)
            .padding(.bottom)
            
            VStack {
                HStack {
                    Text("Rotational Change")
                        .font(.title2)
                        .monospaced()
                    Spacer()
                }
                Chart {
                    ForEach(Array(rotationalChangeData.enumerated()), id: \.0.self) { (idx, entry) in
                        LineMark(
                            x: .value("ID", idx),
                            y: .value("Value", entry.value as! Double)
                        )
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading)
                }
                .chartYScale(domain: .automatic(includesZero: true))
                .frame(height: 300)
            }
            .padding(.horizontal, 29)
            .padding(.bottom)
        }
        .onAppear {
            do {
                try scene = SCNScene(url: Bundle.main.url(forResource: "orientation_dummy", withExtension: "scn")!)
            } catch {
                print(error)
            }
            
            Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
                // Runtime/iterations
                let allRuntimeData = sharedState.bluetoothManager.storedData.filter { $0.type == .runtime }
                if allRuntimeData.count != 0 {
                    runtimeData = allRuntimeData.reversed()[0].value as? Int
                }
                
                // Sound level
                soundLevelData = sharedState.bluetoothManager.storedData.filter { $0.type == .soundLevel }
                
                // Water level
                waterLevelData = sharedState.bluetoothManager.storedData.filter { $0.type == .waterLevel }
                
                // Rotational change
                rotationalChangeData = sharedState.bluetoothManager.storedData.filter { $0.type == .rotationalChange }
                
                // 9D rotation
                let allEulerXData = sharedState.bluetoothManager.storedData.filter { $0.type == .eulerX }
                let allEulerYData = sharedState.bluetoothManager.storedData.filter { $0.type == .eulerY }
                let allEulerZData = sharedState.bluetoothManager.storedData.filter { $0.type == .eulerZ }
                
                if allEulerXData.count != 0 {
                    eulerXData = allEulerXData.reversed()[0].value as? Double
                }
                if allEulerYData.count != 0 {
                    eulerYData = allEulerYData.reversed()[0].value as? Double
                }
                if allEulerZData.count != 0 {
                    eulerZData = allEulerZData.reversed()[0].value as? Double
                }
                
                let object = scene?.rootNode.childNode(withName: "object", recursively: true)
                object!.eulerAngles.x = Float(eulerXData ?? 0)
                object!.eulerAngles.y = Float(eulerYData ?? 0)
                object!.eulerAngles.z = Float(eulerZData ?? 0)

            }
        }
        .navigationTitle("Data Explorer")
        .toolbar {
            Button("Clear") {
                sharedState.bluetoothManager.storedData = []
                sharedState.bluetoothManager.rawSignals = []
            }
            .foregroundStyle(.red)
        }
    }
}
