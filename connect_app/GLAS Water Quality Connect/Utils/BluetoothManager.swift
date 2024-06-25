//
//  BluetoothManager.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/19/24.
//

import Foundation
import CoreBluetooth

struct Device: Identifiable, Hashable {
    var id: UUID { address }
    var name: String
    var address: UUID
}

enum DataType {
    case runtime
    case soundLevel
    case waterLevel
    case eulerX
    case eulerY
    case eulerZ
    case rotationalChange
}

struct DataEntry {
    var type: DataType
    var value: Any
}

class BluetoothManager: NSObject, CBCentralManagerDelegate, CBPeripheralDelegate, ObservableObject {
    var centralManager: CBCentralManager?
    var raw_peripherals: [CBPeripheral] = []
    var devices: [Device] = []
    var connected: Device?
    var storedData: [DataEntry] = []
    var rawSignals: [String] = []
    
    override init() {
        super.init()
        self.centralManager = CBCentralManager(delegate: self, queue: nil)
    }
    
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOff:
            print("BLE is powered off")
        case .poweredOn:
            print("BLE is powered on")
        case .resetting:
            print("BLE is resetting")
        case .unauthorized:
            print("BLE is unauthorized")
        case .unsupported:
            print("BLE is unsupported")
        default:
            print("BLE is unknown")
        }
    }
    
    func runScan() {
        self.raw_peripherals = []
        self.devices = []
        
        self.refreshCurrent()
        
        self.centralManager!.scanForPeripherals(withServices: [CBUUID(string: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")])
        Timer.scheduledTimer(withTimeInterval: 2.0, repeats: false) { [weak self] timer in
            self?.centralManager!.stopScan()
        }
    }
    
    func refreshCurrent() {
        let connected = centralManager?.retrieveConnectedPeripherals(withServices: [CBUUID(string: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")])
        if connected!.count != 0 {
            self.connected = Device(name: connected![0].name!, address: connected![0].identifier)
        } else {
            self.connected = nil
        }
    }
    
    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String : Any], rssi RSSI: NSNumber) {
        self.raw_peripherals.append(peripheral)
        self.devices.append(Device(name: peripheral.name ?? "Unnamed Device", address: peripheral.identifier))
    }
    
    func pairDevice(address: UUID) {
        let device = devices.first(where: { $0.address == address })
        let peripheral = raw_peripherals.first(where: { $0.identifier == address })
        peripheral!.delegate = self
        centralManager?.connect(peripheral!, options: nil)
        self.connected = device
        
        let transferCharacteristic = CBMutableCharacteristic(type: CBUUID(string: "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), properties: [.notify, .writeWithoutResponse], value: nil, permissions: [.readable, .writeable])
        let transferService = CBMutableService(type: CBUUID(string: "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), primary: true)
        transferService.characteristics = [transferCharacteristic]
    }
    
    func unpairDevice() {
        let connected = centralManager?.retrieveConnectedPeripherals(withServices: [CBUUID(string: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")])
        if connected!.count != 0 {
            centralManager?.cancelPeripheralConnection(connected![0])
        }
        self.connected = nil
    }
    
    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        peripheral.discoverServices(nil)
    }
    
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard let services = peripheral.services else { return }
        for service in services {
            peripheral.discoverCharacteristics(nil, for: service)
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        guard let characteristics = service.characteristics else { return }
        for characteristic in characteristics {
            if characteristic.properties.contains(.notify) {
                peripheral.setNotifyValue(true, for: characteristic)
            }
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        if let error = error {
            print("Failed to subscribe to characteristic: \(error.localizedDescription)")
            return
        }

        if characteristic.isNotifying {
            print("Successfully subscribed to characteristic: \(characteristic.uuid)")
        } else {
            print("Unsubscribed from characteristic: \(characteristic.uuid)")
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        if let error = error {
            print("Error receiving notification for characteristic \(characteristic.uuid): \(error.localizedDescription)")
            return
        }

        guard let data = characteristic.value else { return }
        let input = String(data: data, encoding: .utf8) ?? ""
        self.rawSignals.append(input)
        
        if self.rawSignals.count > 5000 {
            self.rawSignals.removeFirst(self.rawSignals.count - 5000)
        }
        
        for dataEntry in self.parseData(input: input) {
            self.storedData.append(dataEntry)
        }
        
        if self.storedData.count > (5000 * 5) {
            self.storedData.removeFirst(self.storedData.count - (5000 * 5))
        }
    }
    
    func parseData(input: String) -> [DataEntry] {
        let values = input.split(separator: ";")
        if values[0] == "WAKE" {
            return [
                DataEntry(type: .runtime, value: Int(values[1]) as Any),
                DataEntry(type: .soundLevel, value: Double(values[2]) as Any),
                DataEntry(type: .waterLevel, value: Int(values[3]) as Any),
                DataEntry(type: .eulerX, value: Double(values[4]) as Any),
                DataEntry(type: .eulerY, value: Double(values[5]) as Any),
                DataEntry(type: .eulerZ, value: Double(values[6]) as Any),
                DataEntry(type: .rotationalChange, value: Double(values[7]) as Any)
            ]
        } else {
            return []
        }
    }
}
