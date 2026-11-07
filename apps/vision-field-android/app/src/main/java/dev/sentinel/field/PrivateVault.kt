package dev.sentinel.field

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** App-private, no-backup AES-GCM envelopes. Pairing and history have distinct keys. */
class PrivateVault(private val context: Context, private val purpose: String) {
    private val alias = "vision-v1-$purpose"
    @Synchronized private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build())
        }.generateKey()
    }
    fun encrypt(bytes: ByteArray): ByteArray = Envelope.encrypt(key(), bytes, purpose.toByteArray())
    fun decrypt(bytes: ByteArray): ByteArray = Envelope.decrypt(key(), bytes, purpose.toByteArray())
    private fun file() = AtomicFile(File(context.noBackupFilesDir, "$purpose.vault"))
    @Synchronized fun save(bytes: ByteArray) {
        val f = file(); val output = f.startWrite()
        try { output.write(encrypt(bytes)); f.finishWrite(output) } catch (e: Exception) { f.failWrite(output); throw e }
    }
    @Synchronized fun load(): ByteArray? = if (file().baseFile.exists()) decrypt(file().readFully()) else null
    @Synchronized fun clear() { file().delete(); KeyStore.getInstance("AndroidKeyStore").apply { load(null); deleteEntry(alias) } }
}

object Envelope {
    fun encrypt(key: SecretKey, bytes: ByteArray, aad: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key); cipher.updateAAD(aad)
        return byteArrayOf(1) + cipher.iv + cipher.doFinal(bytes)
    }
    fun decrypt(key: SecretKey, bytes: ByteArray, aad: ByteArray): ByteArray {
        require(bytes.size >= 29 && bytes[0] == 1.toByte())
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, bytes.copyOfRange(1, 13))); cipher.updateAAD(aad)
        return cipher.doFinal(bytes.copyOfRange(13, bytes.size))
    }
}
