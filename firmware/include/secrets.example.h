#pragma once
// =============================================================================
// COPY THIS FILE to secrets.h and fill in your own values.
//
//     cp include/secrets.example.h include/secrets.h
//
// secrets.h is listed in .gitignore and must NEVER be committed.
// Each teammate keeps their own copy locally.
// =============================================================================

// The WiFi network the third box joins.
//
// NOTE for campus networks: eduroam and most university WLANs use WPA2-Enterprise
// (PEAP/MSCHAPv2), which needs a different, longer connect routine than the
// SSID+password call used here. For the lab bench, use a phone hotspot or a
// personal travel router -- it is far less trouble and it is also what you want
// for the demo, since you control it. See docs/01-system-design.md.
#define WIFI_SSID     "your-network-name"
#define WIFI_PASSWORD "your-network-password"
