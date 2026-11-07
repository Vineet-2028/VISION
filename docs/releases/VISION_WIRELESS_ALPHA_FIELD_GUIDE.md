# Same-LAN wireless Alpha field guide

This is a supervised research harness. Keep a sighted supervisor and normal mobility
support; do not use it for navigation or hazard avoidance. The Windows inference PC
must remain running. Website deployment does not remove this requirement.

## Prepare once

Build/install the Android debug APK through the existing local SDK or trusted local
file transfer. USB is optional for installation and is not needed for each session.
The app still requires camera permission and a local English TTS voice. Pair a
Bluetooth headset through Android system settings if desired; routing is owned by
Android and must be tested by listening, not inferred from a callback.

```powershell
.\apps\perception-lab\.venv\Scripts\python.exe -m pip install -r apps/perception-lab/requirements-wireless.txt
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Wi-Fi*' }
```

## Start a supervised session

1. Put the phone and PC on the same trusted private Wi-Fi. Avoid guest networks with
   client isolation. Do not port-forward or expose this gateway to the internet.
2. Start with your PC's actual Wi-Fi address (replace the example):

   ```powershell
   .\apps\perception-lab\.venv\Scripts\python.exe tools/wireless_alpha.py --address 192.168.1.20
   ```

3. On the PC, open `http://127.0.0.1:8766`. In the phone app choose **Pair PC** and scan
   this trusted screen. QR codes expire after two minutes and work once. Manual QR
   payload entry is under Connection settings. Never scan a code from an unknown PC.
4. Choose **Test camera**. This preview sends no frames. Choose **Test audio** and
   confirm that you hear it on the intended speaker/headset.
5. Choose **Start supervised session**. The frozen Windows engine starts processing
   session frames; **Stop**, backgrounding the app, or disconnect ends active delivery.
6. Optional **History** collects compact event metadata only after explicit enablement.
   Export, individual deletion, Delete All and Clear Cache are separate actions.
7. End with Stop; use the PC page's revoke button to revoke all paired access. Ctrl+C
   stops the gateway. Restart creates a new certificate and requires re-pairing.

If Windows firewall blocks port 8767, allow the selected Python application only on
your trusted Private network and restrict the rule to the local subnet. Do not
disable the firewall. The QR operator page on 8766 and legacy Lab gateway on 8765
bind loopback. A changed Wi-Fi address requires restarting and a new QR.

## Acceptance record still required

Record phone/Android version, PC profile, Wi-Fi, actual audio output, camera timestamp
capability, reconnect/stale suppression, Stop/background behavior and retention/delete
results. Test revoked/expired QR, PC restart, Wi-Fi loss and Bluetooth removal.
No connected device was available in this pass. APK build, JVM policy tests and
desktop TLS tests do not satisfy these physical acceptance checks.
