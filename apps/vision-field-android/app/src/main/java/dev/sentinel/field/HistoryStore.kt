package dev.sentinel.field

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject
import androidx.core.content.edit
import androidx.core.database.sqlite.transaction
import java.util.UUID

object HistoryPolicy {
    const val MAX_ROWS = 1000
    const val MAX_BYTES = 8L * 1024 * 1024
    fun retentionDays(value: Int): Int { require(value in listOf(1, 7, 30, 90)); return value }
    fun expires(now: Long, days: Int): Long = Math.addExact(now, retentionDays(days) * 86_400_000L)
}

/** SQLite indexes contain only random IDs and retention times; all event content is AES-GCM encrypted. */
class HistoryStore(context: Context, namespace: String = "history") : SQLiteOpenHelper(context, databaseName(namespace), null, 2) {
    companion object {
        private fun databaseName(namespace: String): String {
            require(namespace.matches(Regex("history(?:-test-[a-z0-9]+)?")))
            return "vision-$namespace.db"
        }
    }
    private val vault = PrivateVault(context.applicationContext, namespace)
    private val preferences = context.getSharedPreferences("vision-$namespace-policy", Context.MODE_PRIVATE)
    var enabled: Boolean
        get() = preferences.getBoolean("enabled", false)
        set(value) { preferences.edit(commit = true) { putBoolean("enabled", value) } }
    var days: Int
        get() = preferences.getInt("days", 30)
        set(value) {
            val checked = HistoryPolicy.retentionDays(value)
            synchronized(this) {
                // Shortening retention applies to existing rows; extending never resurrects them.
                writableDatabase.execSQL("UPDATE records SET expires=MIN(expires,created+?)", arrayOf(checked * 86_400_000L))
                preferences.edit(commit = true) { putInt("days", checked) }
                cleanup()
            }
        }

    override fun onConfigure(db: SQLiteDatabase) { db.execSQL("PRAGMA secure_delete=ON"); db.setMaximumSize(HistoryPolicy.MAX_BYTES) }
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE records(id TEXT PRIMARY KEY, created INTEGER NOT NULL, expires INTEGER NOT NULL, payload BLOB NOT NULL)")
        db.execSQL("CREATE INDEX expiry ON records(expires)")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        check(oldVersion == 1 && newVersion == 2) { "Unsupported history migration" }
        db.execSQL("CREATE INDEX IF NOT EXISTS expiry ON records(expires)")
    }
    @Synchronized fun record(kind: String, session: String?, message: String, details: JSONObject = JSONObject()) {
        if (!enabled) return
        require(kind in setOf("ALERT_PRESENTED", "CAPABILITY_CHANGED", "SESSION_SUMMARY", "USER_FEEDBACK", "REVIEW_STATE"))
        require(message.length <= 256)
        val now = System.currentTimeMillis()
        val id = UUID.randomUUID().toString()
        val record = JSONObject().put("schema", "vision.history.event.v1").put("event_id", id)
            .put("session_id", session ?: JSONObject.NULL).put("event_time_utc_ms", now).put("type", kind)
            .put("short_message", message).put("details", details).put("review_state", "UNREVIEWED")
            .put("media_reference", JSONObject.NULL).put("training_consent", false)
        val bytes = record.toString().toByteArray(Charsets.UTF_8)
        require(bytes.size <= 4096)
        val db = writableDatabase
        db.transaction {
            cleanup(db, now)
            db.execSQL("DELETE FROM records WHERE id IN (SELECT id FROM records ORDER BY created DESC LIMIT -1 OFFSET ?)", arrayOf(HistoryPolicy.MAX_ROWS - 1))
            val retention = if (kind == "SESSION_SUMMARY") days else minOf(days, 7)
            db.insertOrThrow("records", null, ContentValues().apply { put("id", id); put("created", now); put("expires", HistoryPolicy.expires(now, retention)); put("payload", vault.encrypt(bytes)) })
        }
    }
    private fun cleanup(db: SQLiteDatabase, now: Long) { db.delete("records", "expires <= ?", arrayOf(now.toString())) }
    @Synchronized fun cleanup() { cleanup(writableDatabase, System.currentTimeMillis()) }
    @Synchronized fun entries(): List<JSONObject> {
        cleanup()
        return readableDatabase.rawQuery("SELECT payload FROM records ORDER BY created DESC LIMIT ?", arrayOf(HistoryPolicy.MAX_ROWS.toString())).use { cursor ->
            buildList { while (cursor.moveToNext()) add(JSONObject(String(vault.decrypt(cursor.getBlob(0)), Charsets.UTF_8))) }
        }
    }
    @Synchronized fun feedback(id: String, value: String) {
        require(value in setOf("USEFUL", "NOT_USEFUL", "UNSURE"))
        if (!enabled) return
        val db = writableDatabase
        db.transaction {
            val row = db.rawQuery("SELECT payload FROM records WHERE id=?", arrayOf(id)).use { if (it.moveToFirst()) it.getBlob(0) else null } ?: return
            val data = JSONObject(String(vault.decrypt(row), Charsets.UTF_8))
            data.put("review_state", "USER_RATED_NOT_GROUND_TRUTH").put("feedback", value)
            db.update("records", ContentValues().apply { put("payload", vault.encrypt(data.toString().toByteArray(Charsets.UTF_8))) }, "id=?", arrayOf(id))
        }
    }
    @Synchronized fun delete(id: String) {
        writableDatabase.delete("records", "id=?", arrayOf(id))
        writableDatabase.execSQL("VACUUM")
    }
    @Synchronized fun deleteAll() {
        writableDatabase.delete("records", null, null)
        writableDatabase.execSQL("VACUUM")
        vault.clear()
    }
    @Synchronized fun export(): String = JSONObject().put("schema", "vision.history.export.v1")
        .put("history_enabled", enabled).put("training_consent", false).put("events", JSONArray(entries())).toString(2)
}
