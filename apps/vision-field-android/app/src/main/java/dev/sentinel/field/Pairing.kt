package dev.sentinel.field

import org.json.JSONObject
import java.net.URI
import java.security.MessageDigest
import java.security.cert.X509Certificate
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.TrustManagerFactory
import java.security.KeyStore
import java.security.cert.CertificateFactory
import java.io.ByteArrayInputStream
import android.util.Base64

data class PairedGateway(val endpoint: String, val fingerprint: String, val deviceKey: String, val certificate: String) {
    fun json() = JSONObject().put("endpoint", endpoint).put("fingerprint", fingerprint).put("device_key", deviceKey).put("certificate", certificate)
}

object Pairing {
    fun socketFactory(fingerprint: String, certificate: String): SSLSocketFactory {
        require(Regex("[a-f0-9]{64}").matches(fingerprint)) { "Invalid certificate fingerprint" }
        val pin = fingerprint.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        require(certificate.length <= 2048)
        val der = Base64.decode(certificate, Base64.NO_WRAP)
        require(MessageDigest.isEqual(pin, MessageDigest.getInstance("SHA-256").digest(der))) { "Pairing certificate fingerprint mismatch" }
        val trusted = CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(der)) as X509Certificate
        trusted.checkValidity()
        val store = KeyStore.getInstance(KeyStore.getDefaultType()).apply { load(null); setCertificateEntry("scanned-gateway", trusted) }
        val managers = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()).apply { init(store) }.trustManagers
        return SSLContext.getInstance("TLS").apply { init(null, managers, null) }.socketFactory
    }

    fun exchange(payload: String): PairedGateway {
        require(payload.length <= 2048)
        val data = JSONObject(payload)
        require(data.getString("schema") == "VISION_PAIR_V1")
        val endpoint = gatewayOrigin(data.getString("endpoint")).toString().trimEnd('/')
        require(URI(endpoint).scheme == "https")
        val fingerprint = data.getString("fingerprint")
        val code = data.getString("code")
        require(code.length in 32..128)
        val certificate = data.getString("certificate")
        val result = request(endpoint, fingerprint, certificate, "/v1/pair", JSONObject().put("code", code))
        return PairedGateway(endpoint, fingerprint, result.getString("device_key"), certificate)
    }

    fun sessionToken(gateway: PairedGateway): String = request(gateway.endpoint, gateway.fingerprint, gateway.certificate, "/v1/session-token", JSONObject().put("device_key", gateway.deviceKey)).getString("token")

    private fun request(endpoint: String, pin: String, certificate: String, path: String, body: JSONObject): JSONObject {
        val connection = URI(endpoint).resolve(path).toURL().openConnection() as HttpsURLConnection
        // The default hostname verifier remains enabled. Only the scanned certificate is trusted.
        connection.sslSocketFactory = socketFactory(pin, certificate)
        connection.connectTimeout = 3000
        connection.readTimeout = 3000
        connection.instanceFollowRedirects = false
        try {
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            val bytes = body.toString().toByteArray(Charsets.UTF_8)
            connection.setFixedLengthStreamingMode(bytes.size)
            connection.outputStream.use { it.write(bytes) }
            check(connection.responseCode == 200) { "Pairing expired or revoked. Scan a fresh code." }
            val bytesIn = connection.inputStream.use { input ->
                val output = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(1024)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    check(output.size() + count <= 4096)
                    output.write(buffer, 0, count)
                }
                output.toByteArray()
            }
            return JSONObject(String(bytesIn, Charsets.UTF_8))
        } finally { connection.disconnect() }
    }
}
