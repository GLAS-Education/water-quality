//
//  ContentView.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/19/24.
//

import SwiftUI

struct ConnectView: View {
    @EnvironmentObject var sharedState: SharedState
    @State var devices: [Device] = []
    @State var connected: Device? = nil
    @State var loading: UUID? = nil
    
    var body: some View {
        VStack(alignment: .leading) {
            List {
                ForEach(devices) { device in
                    Button {
                        if connected?.address == device.address {
                            loading = device.address
                            connected = nil
                            self.sharedState.bluetoothManager.unpairDevice()
                        } else if connected == nil && loading == nil {
                            loading = device.address
                            self.sharedState.bluetoothManager.pairDevice(address: device.address)
                            connected = device
                        }
                    } label: {
                        if connected?.address == device.address {
                            Label("\(device.name) (\(device.address))", systemImage: "checkmark.circle.fill")
                        } else if loading == device.address {
                            Label("\(device.name) (\(device.address))", systemImage: "ellipsis")
                        } else {
                            Label("\(device.name) (\(device.address))", systemImage: "cpu")
                        }
                    }
                    .foregroundStyle(connected?.address == device.address ? .green : .accentColor)
                    .disabled(loading != nil || ((connected != nil) && connected?.address != device.address))
                }
                
                Button {
                    sharedState.bluetoothManager.runScan()
                } label: {
                    Label("Refresh available connections", systemImage: "arrow.clockwise")
                }
                .foregroundStyle(.gray)
            }
            .listStyle(.inset)
            .padding(.bottom)
            .cornerRadius(15)
            .refreshable {
                sharedState.bluetoothManager.runScan()
            }
        }
        .navigationTitle("Connections")
        .onAppear {
            sharedState.bluetoothManager.runScan()
            Timer.scheduledTimer(withTimeInterval: 0.025, repeats: true) { _ in
                devices = Array(Set(connected != nil ? sharedState.bluetoothManager.devices + [connected!] : sharedState.bluetoothManager.devices)).sorted { $0.name < $1.name }
                connected = sharedState.bluetoothManager.connected
                loading = nil
            }
        }
    }
}
