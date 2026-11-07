package dev.sentinel.field

import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import org.json.JSONArray
import org.json.JSONObject

/** Keep short histories because the latest sensor callback can be newer than the camera frame. */
class FieldSensors(private val manager: SensorManager?) : SensorEventListener {
    private data class Sample(val timestamp: Long, val values: List<Double>)
    private val gravity = ArrayDeque<Sample>()
    private val rotation = ArrayDeque<Sample>()
    private var mount: Int? = null

    @Synchronized fun start(mountDegrees: Int?) {
        stop()
        mount = mountDegrees?.takeIf { it in listOf(0, 90, 180, 270) } ?: return
        for (type in listOf(Sensor.TYPE_GRAVITY, Sensor.TYPE_ROTATION_VECTOR)) {
            manager?.getDefaultSensor(type)?.let { manager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }
        }
    }

    @Synchronized fun stop() {
        mount = null
        manager?.unregisterListener(this)
        gravity.clear()
        rotation.clear()
    }

    @Synchronized override fun onSensorChanged(event: SensorEvent) {
        if (mount == null || event.accuracy == SensorManager.SENSOR_STATUS_UNRELIABLE) return
        val history: ArrayDeque<Sample>
        val values: List<Double>
        if (event.sensor.type == Sensor.TYPE_GRAVITY && event.values.size >= 3) {
            history = gravity
            values = event.values.take(3).map { it.toDouble() }
        } else if (event.sensor.type == Sensor.TYPE_ROTATION_VECTOR && event.values.size >= 3) {
            history = rotation
            val q = FloatArray(4)
            SensorManager.getQuaternionFromVector(q, event.values)
            values = listOf(q[1], q[2], q[3], q[0]).map { it.toDouble() }
        } else return
        if (values.any { !it.isFinite() }) return
        if (history.size == 8) history.removeFirst()
        history.addLast(Sample(event.timestamp, values))
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    @Synchronized fun snapshot(cameraNs: Long): JSONObject? {
        val degrees = mount ?: return null
        val result = JSONObject().put("mount_clockwise_degrees", degrees)
        for ((history, stampKey, valueKey) in listOf(
            Triple(gravity, "gravity_ns", "gravity_device"), Triple(rotation, "rotation_ns", "rotation_xyzw")
        )) {
            val sample = history.lastOrNull { cameraNs - it.timestamp in 0L..100_000_000L } ?: continue
            result.put(stampKey, sample.timestamp.toString()).put(valueKey, JSONArray(sample.values))
        }
        return result
    }
}
