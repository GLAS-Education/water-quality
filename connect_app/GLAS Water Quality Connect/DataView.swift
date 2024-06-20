//
//  DataView.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/19/24.
//

import SwiftUI
import Charts

struct DataView: View {
    @EnvironmentObject var sharedState: SharedState
    @State private var runtimeData: [DataEntry] = []
    @State private var waterLevelData: [DataEntry] = []
    
    var body: some View {
        ScrollView {
            Group {
                HStack {
                    Text("Runtime")
                        .font(.title2)
                        .monospaced()
                    Spacer()
                }
                Chart {
                    ForEach(Array(runtimeData.enumerated()), id: \.0.self) { (idx, entry) in
                        LineMark(
                            x: .value("ID", idx),
                            y: .value("Value", entry.value as! Double)
                        )
                    }
                }
                .chartYAxis {
                    AxisMarks(position: .leading)
                }
                .chartYScale(domain: .automatic(includesZero: false))
                .frame(height: 300)
            }
            .padding(.top, 10)
            .padding(.horizontal, 29)
            .padding(.bottom)
            
            Group {
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
                            y: .value("Value", entry.value as! Double)
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
        }
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
                runtimeData = sharedState.bluetoothManager.storedData.filter { $0.type == .runtime }
                waterLevelData = sharedState.bluetoothManager.storedData.filter { $0.type == .waterLevel }
            }
        }
        .navigationTitle("Data Explorer")
        .toolbar {
            Button("Clear") {
                sharedState.bluetoothManager.storedData = []
                sharedState.bluetoothManager.rawSignals = []
                runtimeData = []
                waterLevelData = []
            }
            .foregroundStyle(.red)
        }
    }
}
