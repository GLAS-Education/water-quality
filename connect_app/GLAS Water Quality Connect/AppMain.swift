//
//  AppMain.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/19/24.
//

import SwiftUI

class SharedState: ObservableObject {
    @Published var bluetoothManager = BluetoothManager()
}

@main
struct AppMain: App {
    @StateObject var sharedState = SharedState()
    @State private var isConnected: Bool = false
    @State private var dontRefreshConnection: Bool = false
    
    var body: some Scene {
        WindowGroup {
            NavigationView {
                List {
                    NavigationLink(destination: ConnectView()) {
                        Label("Connections", systemImage: "dot.radiowaves.left.and.right")
                    }
                    NavigationLink(destination: DataView()) {
                        Label("Data Explorer", systemImage: "chart.xyaxis.line")
                    }
                    .disabled(!isConnected)
                    NavigationLink(destination: DebugView()) {
                        Label("Signal Debugger", systemImage: "stethoscope")
                    }
                    .disabled(!isConnected)
                }
                .navigationTitle("🌊 GLAS WQC")
            }
            .environmentObject(sharedState)
            .onAppear {
                Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
                    isConnected = sharedState.bluetoothManager.connected != nil
                }
                
                Timer.scheduledTimer(withTimeInterval: 2.5, repeats: true) { _ in
                    if !dontRefreshConnection && isConnected && sharedState.bluetoothManager.connected != nil {
                        sharedState.bluetoothManager.refreshCurrent()
                    }
                }
            }
        }
    }
}
