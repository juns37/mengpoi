import React from "react";
import devices from "@site/src/components/deviceInfo.js";
import "./style.css";

export default function DeviceInfo({ id }) {
  const device = devices[id];

  if (!device) {
    return <p>❌ Device tidak ditemukan.</p>;
  }

  return (
    <div className="device-container">
      {/* Judul */}
      <h1 className="device-title-main">{device.name}</h1>

      {/* Grid Atas */}
      <div className="device-grid">
        {/* Nama */}
        <div className="device-card">
          <div className="device-label">Nama Perangkat</div>
          <div className="device-value">{device.name}</div>
        </div>

        {/* Storage */}
        <div className="device-card">
          <div className="storage-bar">
            <div className="storage-used">
              <div
                className="storage-blue"
                style={{ width: device.storageBar.blue }}
              ></div>

              <div
                className="storage-orange"
                style={{ width: device.storageBar.orange }}
              ></div>

              <div
                className="storage-gray"
                style={{ width: device.storageBar.gray }}
              ></div>
            </div>
          </div>

          <div className="device-label">Storage</div>
          <div className="device-value">{device.storage}</div>
        </div>
      </div>

      {/* Spesifikasi */}
      <div className="spec-card">
        {device.specs.map((item, i) => (
          <div className="spec-row" key={i}>
            <span className="spec-name">{item.name}</span>
            <span className="spec-value">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}