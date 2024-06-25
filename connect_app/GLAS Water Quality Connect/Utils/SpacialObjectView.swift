//
//  3DOrientationView.swift
//  GLAS Water Quality Connect
//
//  Created by Teddy Lampert on 6/20/24.
//

import SwiftUI
import SceneKit

struct SpacialObjectView: UIViewRepresentable {
    @Binding var eulerX: Double?
    @Binding var eulerY: Double?
    @Binding var eulerZ: Double?

    func makeUIView(context: Context) -> SCNView {
        let scnView = SCNView()
        scnView.scene = SCNScene(named: "3DModels/cup_saucer_set.scn")
        scnView.allowsCameraControl = true
        scnView.autoenablesDefaultLighting = true
        scnView.backgroundColor = .red
        return scnView
    }

    func updateUIView(_ scnView: SCNView, context: Context) {
        guard let node = scnView.scene?.rootNode.childNode(withName: "CupAndSaucerCup", recursively: true) else {
            return
        }
        node.eulerAngles.x = Float(eulerX ?? 0)
        node.eulerAngles.y = Float(eulerY ?? 0)
        node.eulerAngles.z = Float(eulerZ ?? 0)
    }
}
