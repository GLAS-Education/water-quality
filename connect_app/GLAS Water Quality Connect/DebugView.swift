//
//  DebugView.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/19/24.
//

import SwiftUI

struct DebugView: View {
    @EnvironmentObject var sharedState: SharedState
    @State private var signals: [String] = []
    
    var body: some View {
        VStack(alignment: .leading) {
            List(Array(signals.enumerated().reversed()), id: \.0.self) { (_, signal) in
                Text(signal)
                    .textSelection(.enabled)
                    .monospaced()
            }
            .listStyle(.inset)
            .padding(.horizontal, 10)
        }
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
                signals = sharedState.bluetoothManager.rawSignals
            }
        }
        .navigationTitle("Signal Debugger")
        .toolbar {
            Button("Clear") {
                sharedState.bluetoothManager.storedData = []
                sharedState.bluetoothManager.rawSignals = []
                signals = []
            }
            .foregroundStyle(.red)
        }
    }
}
