package dev.sentinel.field

import android.Manifest
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.SensorManager
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Bundle
import android.os.SystemClock
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.camera2.interop.Camera2CameraInfo
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import java.util.concurrent.Executors
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : ComponentActivity() {
    private val cameraExecutor = Executors.newSingleThreadExecutor()
    private val transportExecutor = Executors.newSingleThreadExecutor()
    private val historyExecutor = object : java.util.concurrent.ThreadPoolExecutor(1,1,0L,TimeUnit.MILLISECONDS,ArrayBlockingQueue<Runnable>(64)) {
        override fun terminated() { try { history.close() } finally { super.terminated() } }
    }
    private val history by lazy { HistoryStore(applicationContext) }
    private var showHistory by mutableStateOf(false)
    private var historyRows by mutableStateOf<List<org.json.JSONObject>>(emptyList())
    private var historyEnabled by mutableStateOf(false)
    private var historyDays by mutableIntStateOf(30)
    private val exportHistory = registerForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) historyTask { contentResolver.openOutputStream(uri)?.use { it.write(history.export().toByteArray(Charsets.UTF_8)) } }
    }
    private val exportDiagnostic = registerForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { uri ->
        if (uri != null) historyTask {
            DiagnosticFrames.expire(applicationContext)
            val clip = diagnosticVault.load()
            if (clip != null) {
                val stream = contentResolver.openOutputStream(uri) ?: error("Export destination unavailable")
                stream.use { it.write(clip) }
                runOnUiThread { status = "Readable diagnostic clip exported. Keep it private; delete the exported copy when finished." }
            }
            else runOnUiThread { status = "No retained diagnostic clip to export." }
        }
    }
    private val pending = LatestFrame<CameraFrame>()
    private val diagnosticCapture = java.util.concurrent.atomic.AtomicReference<DiagnosticCapture?>(null)
    private val running = AtomicBoolean(false)
    private val occupied = AtomicBoolean(false)
    private val sessionLock = Any()
    private var activeSpeech: FieldSpeech? = null
    private val sensors by lazy { FieldSensors(getSystemService(SensorManager::class.java)) }
    private var provider: ProcessCameraProvider? = null
    private var status by mutableStateOf("Disconnected — Guardian disabled")
    private var address by mutableStateOf("http://127.0.0.1:8765")
    private var token by mutableStateOf("")
    private var paired by mutableStateOf<PairedGateway?>(null)
    private var pairingPayload by mutableStateOf("")
    private val pairingVault by lazy { PrivateVault(applicationContext, "pairing") }
    private var cameraOnly = false
    private val qrScanner = registerForActivityResult(com.journeyapps.barcodescanner.ScanContract()) { result ->
        result.contents?.let { pair(it) }
    }
    private var preview: PreviewView? = null
    private var generation = 0
    private var settings by mutableStateOf(false)
    private val diagnosticFrames = DiagnosticFrames()
    private val diagnosticVault by lazy { PrivateVault(applicationContext, "diagnostic-clip") }
    private var clipConsent by mutableStateOf(false)
    private var savedClip by mutableStateOf(false)
    private val recentCaptures = java.util.ArrayDeque<DiagnosticCapture>()
    private var selectableCaptures by mutableStateOf<List<DiagnosticCapture>>(emptyList())
    private var selectedCapture by mutableStateOf<DiagnosticCapture?>(null)
    private var showDiagnostics by mutableStateOf(false)
    private var showSummary by mutableStateOf(false)
    private var lastSummary by mutableStateOf("No finished session.")
    private val permission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) { if (cameraOnly) testCamera() else startCamera() } else status = "Camera permission denied"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        HistoryCleanup.schedule(this)
        historyTask { history.cleanup(); DiagnosticFrames.expire(applicationContext) }
        try {
            pairingVault.load()?.let { val data = org.json.JSONObject(String(it, Charsets.UTF_8)); paired = PairedGateway(data.getString("endpoint"), data.getString("fingerprint"), data.getString("device_key"),data.getString("certificate")); address = paired!!.endpoint }
        } catch (_: Exception) { status = "Saved pairing unavailable. Pair again." }
        setContent {
            MaterialTheme {
                Surface(Modifier.fillMaxSize()) {
                    Column(Modifier.fillMaxSize().padding(20.dp).windowInsetsPadding(WindowInsets.safeDrawing), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text("VISION", style = MaterialTheme.typography.headlineMedium)
                        Text("Same Wi-Fi · keep your Windows PC running")
                        Text(status)
                        Row {
                            TextButton(enabled = !occupied.get(), onClick = { stopSession(); qrScanner.launch(com.journeyapps.barcodescanner.ScanOptions().setDesiredBarcodeFormats(com.journeyapps.barcodescanner.ScanOptions.QR_CODE).setPrompt("Scan only your trusted VISION PC's pairing screen").setBeepEnabled(false)) }) { Text(if (paired == null) "1. Pair PC" else "Pair another PC") }
                            TextButton(onClick = { cameraOnly = true; if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) testCamera() else permission.launch(Manifest.permission.CAMERA) }) { Text("2. Test camera") }
                        }
                        TextButton(onClick = { settings = !settings }) { Text("Connection settings") }
                        if (settings) AlertDialog(onDismissRequest = { settings = false },
                            title = { Text("Connection settings") },
                            confirmButton = { TextButton(onClick = { settings = false }) { Text("Done") } },
                            text = { Column(Modifier.verticalScroll(rememberScrollState())) {
                            OutlinedTextField(pairingPayload, { pairingPayload = it.take(2048) }, label = { Text("Manual QR payload (from trusted PC)") }, maxLines = 3)
                            TextButton(onClick = { pair(pairingPayload) }) { Text("Pair from payload") }
                            TextButton(onClick = { stopSession(); pairingVault.clear(); paired = null; token = ""; status = "Pairing removed on this phone. Revoke on PC too." }) { Text("Forget PC") }
                            OutlinedTextField(address, { address = it }, label = { Text("Gateway origin") }, singleLine = true)
                            OutlinedTextField(token, { token = it }, label = { Text("Ephemeral token") }, visualTransformation = PasswordVisualTransformation(), singleLine = true)
                        } })
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            Button(modifier = Modifier.weight(1f), onClick = { cameraOnly = false; if (paired == null && token.length < 32) { settings = true; status = "Pair with your PC first, or enter the USB operator token." }
                                else if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) startCamera() else permission.launch(Manifest.permission.CAMERA) }) { Text("Start supervised session") }
                            OutlinedButton(onClick = { stopSession() }) { Text("Stop") }
                        }
                        Row {
                            TextButton(onClick = { testAudio() }) { Text("Test audio") }
                            TextButton(onClick = { showSummary = true }) { Text("Session summary") }
                            TextButton(onClick = { showHistory = true; historyTask {} }) { Text("History") }
                        }
                        TextButton(onClick = {
                            selectableCaptures = synchronized(sessionLock) { recentCaptures.toList().reversed() }
                            selectedCapture = null
                            historyTask { DiagnosticFrames.expire(applicationContext); val retained = diagnosticVault.load() != null; runOnUiThread { savedClip = retained } }
                            showDiagnostics = true
                        }) { Text("Report a problem") }
                        if (showDiagnostics) AlertDialog(
                            onDismissRequest = { showDiagnostics = false },
                            title = { Text("Mark this moment") },
                            text = { Column(Modifier.verticalScroll(rememberScrollState())) {
                                Text("Buffer: " + if (clipConsent) "ENABLED" else "DISABLED")
                                Text("Saved encrypted clip: " + if (savedClip) "YES � export or delete before replacement" else "NONE")
                                Text("Session: " + ((selectedCapture ?: selectableCaptures.firstOrNull())?.sessionId ?: "No submitted capture"))
                                Text("Gateway recording is controlled on the PC operator page. Check RECORDING / FULL there and export before stopping.")
                                Text("Choose a submitted capture, or keep the latest capture reference.")
                                TextButton(onClick = { selectedCapture = null }) { Text("Use latest submitted capture") }
                                for (capture in selectableCaptures) {
                                    TextButton(onClick = { selectedCapture = capture }) {
                                        Text("Capture " + capture.sequence + if (capture == selectedCapture) " selected" else "")
                                    }
                                }
                                Row {
                                    Checkbox(checked = clipConsent, onCheckedChange = {
                                        clipConsent = it
                                        diagnosticFrames.enable(it)
                                    })
                                    Text("Buffer up to 2 seconds of camera images in RAM. Marking saves one encrypted local clip, Export or delete the retained clip before saving another.")
                                }
                                Text("One clip, at most 4 MiB of images, expires after 24 hours. Export creates a readable file at your selected location.")
                                TextButton(onClick = { exportDiagnostic.launch("vision-diagnostic-frames.bin") }) { Text("Export readable diagnostic clip") }
                                TextButton(onClick = { historyTask { diagnosticVault.clear(); runOnUiThread { savedClip = false; status = "Saved diagnostic clip deleted." } }; diagnosticFrames.enable(false); clipConsent = false }) { Text("Delete saved diagnostic clip") }
                                Text("Requires Save new events in History. Saves a timestamp and your feedback locally. Images are saved only when buffering is enabled. Audio is never recorded.")
                                for ((code, label) in listOf("MISSED" to "VISION missed this", "WRONG_NAME" to "Wrong name", "UNNECESSARY" to "Unnecessary warning", "CORRECT_SILENCE" to "Correct silence")) {
                                    TextButton(onClick = { markDiagnostic(code); showDiagnostics = false }) { Text(label) }
                                }
                            } },
                            confirmButton = { TextButton(onClick = { showDiagnostics = false }) { Text("Cancel") } }
                        )
                        if (showHistory) HistoryPanel(historyRows,historyEnabled,historyDays,
                            onEnabled={value -> historyTask { history.enabled=value }}, onDays={value -> historyTask { history.days=value }},
                            onFeedback={id,value -> historyTask { history.feedback(id,value) }}, onDelete={id ->
                                if (id == null) { diagnosticFrames.enable(false); clipConsent = false }
                                historyTask { if(id==null) { history.deleteAll(); diagnosticVault.clear() } else history.delete(id) }
                            },
                            onCache={historyTask { val root=cacheDir.canonicalFile; root.listFiles()?.forEach { child -> if(child.canonicalPath.startsWith(root.path+java.io.File.separator)) child.deleteRecursively() } }},
                            onExport={exportHistory.launch("vision-history.json")},onClose={showHistory=false})
                        if (showSummary) AlertDialog(onDismissRequest = { showSummary = false },
                            title = { Text("Session summary") }, text = { Text(lastSummary) },
                            confirmButton = { TextButton(onClick = { showSummary = false }) { Text("Close") } })
                        AndroidView(factory = { PreviewView(it).also { view -> preview = view } }, modifier = Modifier.weight(1f).fillMaxWidth())
                        Text("Do not use for navigation or safety. Camera frames stay within the local test connection. Recording is off by default.")
                    }
                }
            }
        }
    }

    private fun markDiagnostic(kind: String) {
        val markedAt = SystemClock.elapsedRealtimeNanos()
        val capture = selectedCapture ?: diagnosticCapture.get()
        val userSelected = selectedCapture != null
        val clip = if (capture != null && clipConsent) diagnosticFrames.snapshot(capture.sessionId, capture.sequence) else null
        historyTask {
            if (!history.enabled) {
                runOnUiThread { status = "Enable Save new events in History, then mark the event again." }
            } else {
                DiagnosticFrames.expire(applicationContext)
                val clipSaved = clip != null && diagnosticVault.load() == null
                if (clipSaved) diagnosticVault.save(checkNotNull(clip))
                history.record("USER_FEEDBACK", capture?.sessionId, kind, org.json.JSONObject()
                    .put("diagnostic_clip_saved", clipSaved)
                    .put("schema", "vision.field.marker.v1")
                    .put("candidate", "ALPHA_V1_1_DIAGNOSTICS")
                    .put("phone_monotonic_ns", markedAt.toString())
                    .put("clock_domain", "ANDROID_ELAPSED_REALTIME")
                    .put("lineage_status", if (capture == null) "UNLINKED_USER_MARKER" else if (userSelected) "USER_SELECTED_FRAME" else "LATEST_SUBMITTED_FRAME")
                    .put("source_sequence", capture?.sequence ?: org.json.JSONObject.NULL)
                    .put("source_camera_ns", capture?.cameraNs?.toString() ?: org.json.JSONObject.NULL)
                    .put("first_proven_loss_reason", "UNKNOWN"))
                runOnUiThread { savedClip = clipSaved || savedClip; status = if (clipSaved) "Feedback and encrypted clip saved. Export both the clip and History; match the session on the PC." else if (clip != null && !clipSaved) "Feedback saved. Existing clip protected; export or delete it before another capture." else "Feedback saved locally. Export it from History." }
            }
        }
    }

    private fun historyTask(action: () -> Unit) {
        try { historyExecutor.execute {
            try { action(); val rows=if (showHistory) history.entries() else emptyList(); val enabled=history.enabled; val days=history.days
                runOnUiThread { historyRows=rows; historyEnabled=enabled; historyDays=days }
            } catch (_: Exception) { runOnUiThread { status="Local history unavailable; inference settings unchanged." } }
        } } catch (_: java.util.concurrent.RejectedExecutionException) { /* Activity already closed. */ }
    }

    private fun pair(payload: String) {
        if (!occupied.compareAndSet(false, true)) return
        status = "Pairing with trusted PC…"
        transportExecutor.execute {
            try {
                val gateway = Pairing.exchange(payload)
                pairingVault.save(gateway.json().toString().toByteArray(Charsets.UTF_8))
                runOnUiThread { paired = gateway; address = gateway.endpoint; pairingPayload = ""; status = "Paired. Test camera and audio, then start." }
            } catch (_: Exception) { runOnUiThread { status = "Pairing failed. Check Wi-Fi, PC firewall and a fresh QR code." } }
            finally { occupied.set(false) }
        }
    }

    private fun testCamera() {
        if (occupied.get()) return
        val requestedGeneration = ++generation
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            if (requestedGeneration != generation || occupied.get() ||
                !lifecycle.currentState.isAtLeast(androidx.lifecycle.Lifecycle.State.STARTED)) return@addListener
            try {
                val cameraProvider = future.get(); provider = cameraProvider
                cameraProvider.unbindAll()
                val previewUseCase = Preview.Builder().build()
                previewUseCase.surfaceProvider = preview?.surfaceProvider
                cameraProvider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, previewUseCase)
                status = "Camera preview only. No frames sent to PC."
            } catch (_: Exception) { status = "Camera unavailable. Check camera permission." }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun testAudio(message: String = "VISION audio test") {
        if (!occupied.compareAndSet(false, true)) return
        val requestGeneration = generation
        status = if (message == "VISION audio test") "Testing local voice" else message
        transportExecutor.execute {
            val done = CountDownLatch(1)
            val speech = FieldSpeech(applicationContext) { kind, id, _ ->
                if (id == "local-audio-test" && kind in setOf("TTS_COMPLETED", "TTS_ERROR", "TTS_STOPPED")) done.countDown()
            }
            try {
                val ready = speech.awaitLocalVoice()
                val played = synchronized(sessionLock) {
                    if (requestGeneration == generation && ready) { activeSpeech = speech; speech.playAudioTest(message) }
                    else false
                }
                if (played) done.await(4, TimeUnit.SECONDS)
                runOnUiThread { if (requestGeneration == generation) status = if (played) {
                    if (message == "VISION audio test") "Audio test submitted" else message
                } else "Local voice unavailable" }
            } finally {
                synchronized(sessionLock) { activeSpeech = null; speech.close() }
                occupied.set(false)
            }
        }
    }

    @androidx.annotation.OptIn(androidx.camera.camera2.interop.ExperimentalCamera2Interop::class)
    private fun startCamera() {
        if (!occupied.compareAndSet(false, true)) return
        val requestedGeneration = ++generation
        val endpoint = address
        val secret = token
        val pairedGateway = paired
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            if (requestedGeneration != generation || isFinishing || isDestroyed || !lifecycle.currentState.isAtLeast(androidx.lifecycle.Lifecycle.State.STARTED)) {
                occupied.set(false)
                return@addListener
            }
            try {
                val cameraProvider = future.get()
                provider = cameraProvider
                val analysis = ImageAnalysis.Builder()
                    .setResolutionSelector(androidx.camera.core.resolutionselector.ResolutionSelector.Builder()
                        .setResolutionStrategy(androidx.camera.core.resolutionselector.ResolutionStrategy(android.util.Size(640,480), androidx.camera.core.resolutionselector.ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER)).build())
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
                val previewUseCase = Preview.Builder().build()
                previewUseCase.surfaceProvider = preview?.surfaceProvider
                cameraProvider.unbindAll()
                val camera = cameraProvider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, previewUseCase, analysis)
                val clock = Camera2CameraInfo.from(camera.cameraInfo).getCameraCharacteristic(CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE)
                check(clock == CameraCharacteristics.SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME) { "Camera clock unavailable: capture timing cannot be trusted" }
                sensors.start(Camera2CameraInfo.from(camera.cameraInfo).getCameraCharacteristic(CameraCharacteristics.SENSOR_ORIENTATION))
                running.set(true)
                var sequence = 0L
                analysis.setAnalyzer(cameraExecutor) { image ->
                    try {
                        if (running.get() && image.width <= 1280 && image.height <= 1280) {
                            val capture = SystemClock.elapsedRealtimeNanos()
                            val bytes = FrameEncoder.encode(image)
                            if (bytes != null) {
                                pending.offer(CameraFrame(sequence++, image.imageInfo.timestamp, capture, image.imageInfo.rotationDegrees, image.width, image.height, bytes, sensors.snapshot(image.imageInfo.timestamp)))
                            }
                        }
                    } catch (_: RuntimeException) { runOnUiThread { status = "Frame encoding failed" } }
                    finally { image.close() }
                }
                status = "Camera ready · connecting"
                transportExecutor.execute {
                    var transport: FieldTransport? = null
                      var connectionFailed = false
                    val events = ArrayBlockingQueue<SpeechEvent>(64)
                    val speech = FieldSpeech(applicationContext, spoken = { alert, age ->
                        historyTask { history.record("ALERT_PRESENTED",alert.sessionId,alert.text,org.json.JSONObject()
                            .put("alert_id",alert.alertId).put("source_age_upper_ms",age/1_000_000.0)
                            .put("reason_codes",org.json.JSONArray(alert.reasonCodes)).put("semantic_level",alert.semanticLevel)
                            .put("model_release_id",alert.releaseId).put("delivery_basis","APP_TTS_PLAYBACK_START_ESTIMATE_NOT_ACOUSTIC")) }
                    }) { kind, id, time ->
                        val outputs = getSystemService(AudioManager::class.java)?.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
                            ?.map { device -> when (device.type) {
                                AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "SPEAKER"
                                AudioDeviceInfo.TYPE_BLUETOOTH_A2DP, AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "BLUETOOTH"
                                AudioDeviceInfo.TYPE_WIRED_HEADPHONES, AudioDeviceInfo.TYPE_WIRED_HEADSET -> "WIRED"
                                AudioDeviceInfo.TYPE_USB_HEADSET, AudioDeviceInfo.TYPE_USB_DEVICE -> "USB"
                                else -> "OTHER"
                            } }?.distinct() ?: emptyList()
                        events.offer(SpeechEvent(kind, id, time, outputs))
                    }
                    var previousStatus: String? = null
                    try {
                        transport = FieldTransport(endpoint, pairedGateway?.let { Pairing.sessionToken(it) } ?: secret, pairedGateway?.fingerprint, pairedGateway?.certificate)
                        while (running.get()) {
                            val frame = pending.take()
                            if (frame == null) { Thread.sleep(10); continue }
                            if (transport.sessionId == null) {
                                transport.start(frame.width, frame.height, speech.awaitLocalVoice())
                                synchronized(sessionLock) {
                                    if (running.get()) {
                                        activeSpeech = speech
                                        speech.reset(transport.sessionId)
                                    }
                                }
                            }
                            if (!running.get()) break
                            diagnosticFrames.offer(frame)
                            transport.send(frame)
                            synchronized(sessionLock) {
                                if (running.get() && requestedGeneration == generation) {
                                    val submitted = DiagnosticCapture(checkNotNull(transport.sessionId), frame.sequence, frame.cameraNs)
                                    diagnosticCapture.set(submitted)
                                    recentCaptures.addLast(submitted)
                                    while (recentCaptures.size > 24) recentCaptures.removeFirst()
                                }
                            }
                            val worker = transport.receive(speech) { events.offer(it) }
                            while (running.get()) transport.speechEvent(events.poll() ?: break)
                            if (worker != previousStatus) {
                                previousStatus = worker
                                val historySession = transport.sessionId
                                historyTask { history.record("CAPABILITY_CHANGED",historySession,"Desktop engine: $worker") }
                                runOnUiThread { if (running.get()) status = "Desktop engine: $worker" }
                            }
                        }
                    } catch (error: Exception) {
                          connectionFailed = true
                        running.set(false)
                        val failedSession = transport?.sessionId
                        historyTask { history.record("CAPABILITY_CHANGED",failedSession,"Connection unavailable") }
                        runOnUiThread { sensors.stop(); provider?.unbindAll(); status = "Disconnected: ${error.javaClass.simpleName}" }
                    } finally {
                        synchronized(sessionLock) { activeSpeech = null; speech.close() }
                        diagnosticCapture.set(null)
                        pending.clear()
                        try { transport?.close() } catch (_: Exception) { /* Local state is still discarded. */ }
                        val accepted = transport?.acceptedFrames ?: 0
                        historyTask { history.record("SESSION_SUMMARY",null,"$accepted frames accepted by desktop",org.json.JSONObject().put("frames_accepted",accepted)) }
                        runOnUiThread { lastSummary = "$accepted frames accepted by the desktop." }
                        occupied.set(false)
                          if (connectionFailed) runOnUiThread {
                              if (requestedGeneration == generation && lifecycle.currentState.isAtLeast(androidx.lifecycle.Lifecycle.State.STARTED))
                                  testAudio("VISION disconnected. Guardian unavailable.")
                          }
                    }
                }
            } catch (error: Exception) {
                occupied.set(false); running.set(false); provider?.unbindAll()
                if (requestedGeneration == generation) testAudio("VISION camera unavailable.")
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun stopSession() {
        diagnosticFrames.enable(false)
        clipConsent = false
        synchronized(sessionLock) { generation++; running.set(false); diagnosticCapture.set(null); recentCaptures.clear(); activeSpeech?.reset(null) }
        sensors.stop()
        provider?.unbindAll()
        pending.clear()
        status = "Disconnected — Guardian disabled"
    }
    override fun onStop() { stopSession(); super.onStop() }
    override fun onDestroy() { stopSession(); cameraExecutor.shutdown(); transportExecutor.shutdown(); historyExecutor.shutdown(); super.onDestroy() }
}

private data class DiagnosticCapture(val sessionId: String, val sequence: Long, val cameraNs: Long)
